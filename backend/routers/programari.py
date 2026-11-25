from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from db import get_db
from schemas import ProgramareCreate, ProgramareStatusUpdate, ProgramareComanda
from security import require_role

router = APIRouter(
    prefix="/api/programari",
    tags=["Programări"],
    dependencies=[Depends(require_role("OPERATOR"))],
)

SELECT_PROGRAMARI = """
    SELECT p.id_programare, p.data_programare, p.durata_estimata_ore,
           p.descriere_problema, p.status, p.id_comanda,
           p.id_vehicul, v.nr_inmatriculare,
           v.marca || ' ' || v.model     AS marca_model,
           cl.nume || ' ' || cl.prenume  AS client_nume,
           lc.denumire                   AS lucrare
    FROM programare p
    JOIN vehicul v          ON v.id_vehicul = p.id_vehicul
    JOIN client cl          ON cl.id_client = v.id_client
    JOIN lucrare_catalog lc ON lc.id_lucrare_catalog = p.id_lucrare_catalog
"""


@router.get("")
def get_programari(data: Optional[date] = None, conn=Depends(get_db)):
    """Programarile unei zile (sau toate, daca nu se da data)."""
    with conn.cursor() as cur:
        if data:
            cur.execute(
                SELECT_PROGRAMARI + " WHERE p.data_programare::date = %s ORDER BY p.data_programare",
                (data,),
            )
        else:
            cur.execute(SELECT_PROGRAMARI + " ORDER BY p.data_programare")
        return cur.fetchall()


@router.get("/ocupare")
def get_ocupare(data: date, conn=Depends(get_db)):
    """Cate programari active si cate elevatoare libere are fiecare ora (08-17)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT to_char(h.ora, 'HH24:MI')                      AS ora,
                   COUNT(p.id_programare)                         AS programari,
                   fn_nr_elevatoare() - COUNT(p.id_programare)    AS elevatoare_libere
            FROM generate_series(%s::timestamp + interval '8 hours',
                                 %s::timestamp + interval '17 hours',
                                 interval '1 hour') AS h(ora)
            LEFT JOIN programare p
                   ON p.status = 'PROGRAMATA'
                  AND p.data_programare <= h.ora
                  AND p.data_programare + p.durata_estimata_ore * interval '1 hour' > h.ora
            GROUP BY h.ora
            ORDER BY h.ora
            """,
            (data, data),
        )
        return cur.fetchall()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_programare(prog: ProgramareCreate, conn=Depends(get_db)):
    # "nu in trecut" si "nu peste numarul de elevatoare" le verifica triggerul
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO programare (data_programare, durata_estimata_ore, descriere_problema,
                                    id_vehicul, id_lucrare_catalog)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id_programare
            """,
            (prog.data_programare, prog.durata_estimata_ore, prog.descriere_problema,
             prog.id_vehicul, prog.id_lucrare_catalog),
        )
        id_nou = cur.fetchone()["id_programare"]
        cur.execute(SELECT_PROGRAMARI + " WHERE p.id_programare = %s", (id_nou,))
        nou = cur.fetchone()
        conn.commit()
        return nou


@router.put("/{id_programare}/status")
def update_status(id_programare: int, data: ProgramareStatusUpdate, conn=Depends(get_db)):
    """Anulare sau marcare ca neprezentat (doar pentru programari inca active)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE programare SET status = %s
            WHERE id_programare = %s AND status = 'PROGRAMATA'
            RETURNING id_programare, status
            """,
            (data.status, id_programare),
        )
        rezultat = cur.fetchone()
        if not rezultat:
            raise HTTPException(400, detail="programarea nu exista sau nu mai este activa")
        conn.commit()
        return rezultat


@router.post("/{id_programare}/comanda", status_code=status.HTTP_201_CREATED)
def deschide_comanda(
    id_programare: int,
    data: ProgramareComanda,
    user: dict = Depends(require_role("OPERATOR")),
    conn=Depends(get_db),
):
    """Transforma programarea in comanda (procedura din baza de date)."""
    if user["id_angajat"] is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="contul nu are un angajat asociat")

    with conn.cursor() as cur:
        cur.execute(
            "CALL sp_deschide_comanda_din_programare(%s, %s, %s, NULL)",
            (id_programare, data.km_intrare, user["id_angajat"]),
        )
        rand = cur.fetchone()
        conn.commit()
    return {"id_comanda": next(iter(rand.values()))}