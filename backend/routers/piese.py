from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from db import get_db
from schemas import PiesaCreate, StocUpdate, FurnizorCreate
from security import require_role

router = APIRouter(
    prefix="/api",
    tags=["Piese și furnizori"],
    dependencies=[Depends(require_role("OPERATOR"))],
)


# ------------------------------------------------------------------ Piese
@router.get("/piese")
def get_piese(categorie: Optional[str] = None, doar_sub_prag: bool = False, conn=Depends(get_db)):
    sql = """
        SELECT p.id_piesa, p.cod, p.denumire, p.categorie, p.pret_vanzare,
               p.stoc_curent, p.prag_minim, p.id_furnizor,
               f.denumire AS furnizor,
               (p.stoc_curent <= p.prag_minim) AS sub_prag
        FROM piesa p
        JOIN furnizor f ON f.id_furnizor = p.id_furnizor
        WHERE 1 = 1
    """
    params = []
    if categorie:
        sql += " AND p.categorie = %s"
        params.append(categorie)
    if doar_sub_prag:
        sql += " AND p.stoc_curent <= p.prag_minim"
    sql += " ORDER BY p.categorie, p.denumire"

    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


@router.get("/piese/sub-prag")
def get_piese_sub_prag(conn=Depends(get_db)):
    """Alertele de stoc minim (CF8), din vederea v_piese_sub_prag."""
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM v_piese_sub_prag ORDER BY deficit DESC, denumire")
        return cur.fetchall()


@router.get("/piese/categorii")
def get_categorii(conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT categorie FROM piesa ORDER BY categorie")
        return [r["categorie"] for r in cur.fetchall()]


@router.post("/piese", status_code=status.HTTP_201_CREATED)
def create_piesa(piesa: PiesaCreate, conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO piesa (cod, denumire, categorie, pret_vanzare, stoc_curent, prag_minim, id_furnizor)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id_piesa, cod, denumire, categorie, pret_vanzare, stoc_curent, prag_minim, id_furnizor
            """,
            (piesa.cod, piesa.denumire, piesa.categorie, piesa.pret_vanzare,
             piesa.stoc_curent, piesa.prag_minim, piesa.id_furnizor),
        )
        nou = cur.fetchone()
        conn.commit()
        return nou


@router.put("/piese/{id_piesa}/stoc")
def aproviziona(id_piesa: int, data: StocUpdate, conn=Depends(get_db)):
    """Aprovizionare: creste stocul cu cantitatea primita."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE piesa SET stoc_curent = stoc_curent + %s
            WHERE id_piesa = %s
            RETURNING id_piesa, stoc_curent
            """,
            (data.cantitate, id_piesa),
        )
        rezultat = cur.fetchone()
        if not rezultat:
            raise HTTPException(404, detail="piesa inexistenta")
        conn.commit()
        return rezultat


# -------------------------------------------------------------- Furnizori
@router.get("/furnizori")
def get_furnizori(conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute("SELECT id_furnizor, denumire, cui, telefon FROM furnizor ORDER BY denumire")
        return cur.fetchall()


@router.post("/furnizori", status_code=status.HTTP_201_CREATED)
def create_furnizor(furnizor: FurnizorCreate, conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO furnizor (denumire, cui, telefon)
            VALUES (%s, %s, %s)
            RETURNING id_furnizor, denumire, cui, telefon
            """,
            (furnizor.denumire, furnizor.cui, furnizor.telefon),
        )
        nou = cur.fetchone()
        conn.commit()
        return nou