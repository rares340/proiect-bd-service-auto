from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from db import get_db
from schemas import (
    UtilizatorCreate, UtilizatorAdminResponse, ActivUpdate, ParolaUpdate,
    AngajatCreate, AngajatResponse, StatisticaAngajat,
)
from security import SESSIONS, hash_parola, require_role

router = APIRouter(
    prefix="/api/admin",
    tags=["Administrare"],
    dependencies=[Depends(require_role("ADMINISTRATOR"))],
)

SELECT_UTILIZATORI = """
    SELECT u.id_utilizator, u.nume_utilizator, u.rol, u.activ, u.data_creare,
           u.id_angajat, a.nume AS angajat_nume
    FROM utilizator u
    LEFT JOIN angajat a ON a.id_angajat = u.id_angajat
"""


# ------------------------------------------------------------ Utilizatori
@router.get("/utilizatori", response_model=List[UtilizatorAdminResponse])
def get_utilizatori(conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute(SELECT_UTILIZATORI + " ORDER BY u.id_utilizator")
        return cur.fetchall()


@router.post("/utilizatori", response_model=UtilizatorAdminResponse,
             status_code=status.HTTP_201_CREATED)
def create_utilizator(data: UtilizatorCreate, conn=Depends(get_db)):
    # potrivirea rol <-> functia angajatului o verifica triggerul din baza de date
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO utilizator (nume_utilizator, parola, rol, id_angajat)
            VALUES (%s, %s, %s, %s)
            RETURNING id_utilizator
            """,
            (data.nume_utilizator, hash_parola(data.parola), data.rol, data.id_angajat),
        )
        id_nou = cur.fetchone()["id_utilizator"]
        cur.execute(SELECT_UTILIZATORI + " WHERE u.id_utilizator = %s", (id_nou,))
        nou = cur.fetchone()
        conn.commit()
        return nou


@router.put("/utilizatori/{id_utilizator}/activ")
def set_activ(id_utilizator: int, data: ActivUpdate,
              user: dict = Depends(require_role("ADMINISTRATOR")),
              conn=Depends(get_db)):
    with conn.cursor() as cur:
        if not data.activ:
            if id_utilizator == user["id_utilizator"]:
                raise HTTPException(400, detail="nu iti poti dezactiva propriul cont")

            cur.execute("SELECT rol FROM utilizator WHERE id_utilizator = %s", (id_utilizator,))
            tinta = cur.fetchone()
            if not tinta:
                raise HTTPException(404, detail="utilizator inexistent")

            if tinta["rol"] == "ADMINISTRATOR":
                cur.execute(
                    """
                    SELECT COUNT(*) AS n FROM utilizator
                    WHERE rol = 'ADMINISTRATOR' AND activ AND id_utilizator <> %s
                    """,
                    (id_utilizator,),
                )
                if cur.fetchone()["n"] == 0:
                    raise HTTPException(400, detail="trebuie sa ramana cel putin un administrator activ")

        cur.execute(
            "UPDATE utilizator SET activ = %s WHERE id_utilizator = %s RETURNING id_utilizator",
            (data.activ, id_utilizator),
        )
        if not cur.fetchone():
            raise HTTPException(404, detail="utilizator inexistent")
        conn.commit()

    # un cont dezactivat pierde imediat sesiunile deschise
    if not data.activ:
        for token in [t for t, u in SESSIONS.items() if u["id_utilizator"] == id_utilizator]:
            del SESSIONS[token]

    return {"message": "cont activat" if data.activ else "cont dezactivat"}


@router.put("/utilizatori/{id_utilizator}/parola")
def reset_parola(id_utilizator: int, data: ParolaUpdate, conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE utilizator SET parola = %s WHERE id_utilizator = %s RETURNING id_utilizator",
            (hash_parola(data.parola), id_utilizator),
        )
        if not cur.fetchone():
            raise HTTPException(404, detail="utilizator inexistent")
        conn.commit()
    return {"message": "parola a fost schimbata"}


# --------------------------------------------------------------- Angajati
@router.get("/angajati", response_model=List[AngajatResponse])
def get_angajati(functie: Optional[str] = None, fara_cont: bool = False, conn=Depends(get_db)):
    sql = "SELECT a.id_angajat, a.nume, a.functie, a.tarif_orar FROM angajat a WHERE 1 = 1"
    params = []
    if functie:
        sql += " AND a.functie = %s"
        params.append(functie)
    if fara_cont:
        sql += " AND NOT EXISTS (SELECT 1 FROM utilizator u WHERE u.id_angajat = a.id_angajat)"
    sql += " ORDER BY a.functie, a.nume"

    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


@router.post("/angajati", response_model=AngajatResponse, status_code=status.HTTP_201_CREATED)
def create_angajat(data: AngajatCreate, conn=Depends(get_db)):
    if data.functie == "MECANIC" and data.tarif_orar is None:
        raise HTTPException(400, detail="mecanicul trebuie sa aiba tarif orar")

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO angajat (nume, functie, tarif_orar)
            VALUES (%s, %s, %s)
            RETURNING id_angajat, nume, functie, tarif_orar
            """,
            (data.nume, data.functie, data.tarif_orar),
        )
        nou = cur.fetchone()
        conn.commit()
        return nou


@router.get("/statistici", response_model=List[StatisticaAngajat])
def statistici_angajati(start: date, end: date, conn=Depends(get_db)):
    """Activitatea fiecarui angajat in perioada [start, end]."""
    if start > end:
        raise HTTPException(400, detail="data de inceput e dupa data de sfarsit")

    with conn.cursor() as cur:
        cur.execute(
            """
            WITH lucrari AS (
                SELECT l.id_mecanic                                AS id_angajat,
                       COUNT(DISTINCT l.id_comanda)                AS nr_comenzi,
                       SUM(l.ore_lucrate)                          AS ore,
                       SUM(l.ore_lucrate * l.tarif_orar_aplicat)   AS venit
                FROM lucrare_efectuata l
                JOIN comanda_reparatie c ON c.id_comanda = l.id_comanda
                WHERE c.data_intrare BETWEEN %(start)s AND %(end)s
                GROUP BY l.id_mecanic
            ),
            comenzi AS (
                SELECT id_operator AS id_angajat, COUNT(*) AS nr_comenzi
                FROM comanda_reparatie
                WHERE data_intrare BETWEEN %(start)s AND %(end)s
                GROUP BY id_operator
            ),
            inspectii AS (
                SELECT id_inspector AS id_angajat,
                       COUNT(*)                                   AS nr_inspectii,
                       COUNT(*) FILTER (WHERE rezultat = 'RESPINS') AS nr_respinse
                FROM inspectie_itp
                WHERE data_inspectie BETWEEN %(start)s AND %(end)s
                GROUP BY id_inspector
            )
            SELECT a.id_angajat, a.nume, a.functie,
                   COALESCE(c.nr_comenzi, 0)          AS nr_comenzi_deschise,
                   COALESCE(l.nr_comenzi, 0)          AS nr_comenzi_lucrate,
                   COALESCE(l.ore, 0)                 AS ore_lucrate,
                   ROUND(COALESCE(l.venit, 0), 2)     AS venit_manopera,
                   COALESCE(i.nr_inspectii, 0)        AS nr_inspectii,
                   COALESCE(i.nr_respinse, 0)         AS nr_respinse
            FROM angajat a
            LEFT JOIN lucrari   l ON l.id_angajat = a.id_angajat
            LEFT JOIN comenzi   c ON c.id_angajat = a.id_angajat
            LEFT JOIN inspectii i ON i.id_angajat = a.id_angajat
            ORDER BY a.functie, a.nume
            """,
            {"start": start, "end": end},
        )
        return cur.fetchall()