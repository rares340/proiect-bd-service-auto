from fastapi import APIRouter, Depends, HTTPException, status

from db import get_db
from schemas import (
    ComandaCreate, ComandaResponse,
    PiesaComandaCreate, PiesaComandaResponse,
)
from security import require_role

router = APIRouter(prefix="/api/comenzi", tags=["Comenzi"])


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


@router.post("/{id_comanda}/piese", response_model=PiesaComandaResponse,
             dependencies=[Depends(require_role("OPERATOR"))])
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