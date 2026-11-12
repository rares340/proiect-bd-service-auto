from typing import List, Optional
import psycopg
from fastapi import APIRouter, Depends, HTTPException, status
from db import get_db
from schemas import VehiculCreate, VehiculResponse

router = APIRouter(prefix="/api/vehicule", tags=["Vehicule"])


@router.get("", response_model=List[VehiculResponse])
def get_vehicule(
    id_client: Optional[int] = None,
    nr_inmatriculare: Optional[str] = None,
    conn=Depends(get_db),
):
    with conn.cursor() as cur:
        if id_client:
            cur.execute("SELECT * FROM vehicul WHERE id_client = %s", (id_client,))
        elif nr_inmatriculare:
            cur.execute(
                "SELECT * FROM vehicul WHERE nr_inmatriculare ILIKE %s",
                (f"%{nr_inmatriculare}%",),
            )
        else:
            cur.execute("SELECT * FROM vehicul")
        return cur.fetchall()


@router.post("", response_model=VehiculResponse, status_code=status.HTTP_201_CREATED)
def create_vehicul(vehicul: VehiculCreate, conn=Depends(get_db)):
    with conn.cursor() as cur:
        try:
            cur.execute(
                """
                INSERT INTO vehicul (serie_sasiu, nr_inmatriculare, marca, model, motorizare,
                                     combustibil, an_fabricatie, norma_poluare, id_client)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    vehicul.serie_sasiu, vehicul.nr_inmatriculare, vehicul.marca,
                    vehicul.model, vehicul.motorizare, vehicul.combustibil,
                    vehicul.an_fabricatie, vehicul.norma_poluare, vehicul.id_client,
                ),
            )
            new_vehicul = cur.fetchone()
            conn.commit()
            return new_vehicul
        except psycopg.errors.UniqueViolation:
            conn.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="exista deja un vehicul inregistrat cu aceasta serie de sasiu sau numar de inmatriculare",
            )