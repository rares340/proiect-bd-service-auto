from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from db import get_db
from schemas import (
    ComandaCreate, ComandaResponse, ComandaStatusUpdate,
    LucrareEfectuataCreate,
    PiesaComandaCreate, PiesaComandaResponse,
)
from security import require_role

router = APIRouter(
    prefix="/api/comenzi",
    tags=["Comenzi"],
    dependencies=[Depends(require_role("OPERATOR"))],
)


@router.get("", response_model=List[ComandaResponse])
def get_comenzi(status: Optional[str] = None, conn=Depends(get_db)):
    with conn.cursor() as cur:
        if status:
            cur.execute(
                "SELECT * FROM v_comanda_detaliu WHERE status = %s ORDER BY id_comanda DESC",
                (status,),
            )
        else:
            cur.execute("SELECT * FROM v_comanda_detaliu ORDER BY id_comanda DESC")
        return cur.fetchall()


@router.get("/{id_comanda}")
def get_comanda(id_comanda: int, conn=Depends(get_db)):
    """Comanda, lucrarile, piesele si devizul ei, intr-un singur raspuns."""
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM v_comanda_detaliu WHERE id_comanda = %s", (id_comanda,))
        comanda = cur.fetchone()
        if not comanda:
            raise HTTPException(404, detail="comanda inexistenta")

        cur.execute(
            """
            SELECT lc.denumire AS lucrare, a.nume AS mecanic, l.ore_lucrate,
                   l.tarif_orar_aplicat,
                   ROUND(l.ore_lucrate * l.tarif_orar_aplicat, 2) AS valoare
            FROM lucrare_efectuata l
            JOIN lucrare_catalog lc ON lc.id_lucrare_catalog = l.id_lucrare_catalog
            JOIN angajat a          ON a.id_angajat = l.id_mecanic
            WHERE l.id_comanda = %s
            ORDER BY l.id_lucrare_efectuata
            """,
            (id_comanda,),
        )
        lucrari = cur.fetchall()

        cur.execute(
            """
            SELECT p.cod, p.denumire, pc.cantitate, pc.pret_unitar_aplicat,
                   ROUND(pc.cantitate * pc.pret_unitar_aplicat, 2) AS valoare
            FROM piesa_comanda pc
            JOIN piesa p ON p.id_piesa = pc.id_piesa
            WHERE pc.id_comanda = %s
            ORDER BY p.denumire
            """,
            (id_comanda,),
        )
        piese = cur.fetchall()

        cur.execute("SELECT manopera, piese, total FROM v_deviz WHERE id_comanda = %s", (id_comanda,))
        deviz = cur.fetchone()

    return {"comanda": comanda, "lucrari": lucrari, "piese": piese, "deviz": deviz}


@router.post("", response_model=ComandaResponse, status_code=status.HTTP_201_CREATED)
def create_comanda(
    comanda: ComandaCreate,
    user: dict = Depends(require_role("OPERATOR")),
    conn=Depends(get_db),
):
    # operatorul este cel logat (CNF4), nu o valoare trimisa de client
    if user["id_angajat"] is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="contul nu are un angajat asociat")

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO comanda_reparatie (km_intrare, reclamatie, id_vehicul, id_operator)
            VALUES (%s, %s, %s, %s)
            RETURNING id_comanda
            """,
            (comanda.km_intrare, comanda.reclamatie, comanda.id_vehicul, user["id_angajat"]),
        )
        id_comanda = cur.fetchone()["id_comanda"]

        cur.execute("SELECT * FROM v_comanda_detaliu WHERE id_comanda = %s", (id_comanda,))
        detaliu = cur.fetchone()
        conn.commit()
        return detaliu


@router.put("/{id_comanda}/status")
def update_status(id_comanda: int, data: ComandaStatusUpdate, conn=Depends(get_db)):
    # tranzitiile permise le verifica triggerul din baza de date
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE comanda_reparatie SET status = %s
            WHERE id_comanda = %s
            RETURNING id_comanda, status, data_predare
            """,
            (data.status, id_comanda),
        )
        rezultat = cur.fetchone()
        if not rezultat:
            raise HTTPException(404, detail="comanda inexistenta")
        conn.commit()
        return rezultat


@router.post("/{id_comanda}/lucrari", status_code=status.HTTP_201_CREATED)
def add_lucrare(id_comanda: int, lucrare: LucrareEfectuataCreate, conn=Depends(get_db)):
    # tariful orar il copiaza triggerul din fisa mecanicului (CNF3)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO lucrare_efectuata
                (post_lucru, ore_lucrate, tarif_orar_aplicat, id_comanda, id_mecanic, id_lucrare_catalog)
            VALUES (%s, %s, NULL, %s, %s, %s)
            RETURNING id_lucrare_efectuata, tarif_orar_aplicat
            """,
            (lucrare.post_lucru, lucrare.ore_lucrate, id_comanda,
             lucrare.id_mecanic, lucrare.id_lucrare_catalog),
        )
        rezultat = cur.fetchone()
        conn.commit()
        return rezultat


@router.post("/{id_comanda}/piese", response_model=PiesaComandaResponse)
def add_piesa_to_comanda(id_comanda: int, piesa: PiesaComandaCreate, conn=Depends(get_db)):
    # stocul, pretul si verificarile sunt facute de triggere si de functia SQL
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM fn_adauga_piesa_comanda(%s, %s, %s)",
            (id_comanda, piesa.id_piesa, piesa.cantitate),
        )
        r = cur.fetchone()
        conn.commit()

    mesaj = None
    if r["sub_prag"]:
        mesaj = f"ATENȚIE: piesa '{r['denumire_piesa']}' a ajuns sub pragul minim (stoc: {r['stoc_ramas']})."

    return {
        "id_comanda": id_comanda,
        "id_piesa": piesa.id_piesa,
        "denumire": r["denumire_piesa"],
        "stoc_ramas": r["stoc_ramas"],
        "alerta_stoc_minim": r["sub_prag"],
        "mesaj": mesaj,
    }