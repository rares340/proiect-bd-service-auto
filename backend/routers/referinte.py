"""Liste mici folosite de interfata pentru combo-uri (mecanici, lucrari, piese)."""
from typing import Optional

from fastapi import APIRouter, Depends

from db import get_db
from security import require_role

router = APIRouter(
    prefix="/api",
    tags=["Liste de referinta"],
    dependencies=[Depends(require_role("OPERATOR"))],
)


@router.get("/mecanici")
def get_mecanici(conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id_angajat, nume FROM angajat WHERE functie = 'MECANIC' ORDER BY nume"
        )
        return cur.fetchall()


@router.get("/lucrari-catalog")
def get_lucrari_catalog(conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id_lucrare_catalog, denumire, durata_ore FROM lucrare_catalog ORDER BY denumire"
        )
        return cur.fetchall()


@router.get("/piese")
def get_piese(categorie: Optional[str] = None, conn=Depends(get_db)):
    with conn.cursor() as cur:
        if categorie:
            cur.execute(
                """
                SELECT id_piesa, cod, denumire, categorie, pret_vanzare, stoc_curent
                FROM piesa WHERE categorie = %s ORDER BY denumire
                """,
                (categorie,),
            )
        else:
            cur.execute(
                """
                SELECT id_piesa, cod, denumire, categorie, pret_vanzare, stoc_curent
                FROM piesa ORDER BY denumire
                """
            )
        return cur.fetchall()