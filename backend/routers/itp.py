from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from db import get_db
from schemas import InspectieITPCreate, InspectieITPResponse

router = APIRouter(prefix="/api/itp", tags=["ITP"])


@router.post("", response_model=InspectieITPResponse, status_code=status.HTTP_201_CREATED)
def register_itp(itp: InspectieITPCreate, conn=Depends(get_db)):
    rezultat = "ADMIS"

    if itp.eficienta_franare is not None and itp.eficienta_franare < 50.0:
        rezultat = "RESPINS"

    if itp.emisii_co is not None and itp.emisii_co > 3.5:
        rezultat = "RESPINS"

    data_inspectie = date.today()
    data_expirare = None

    if rezultat == "ADMIS":
        data_expirare = data_inspectie + timedelta(days=365 * 2)

    with conn.cursor() as cur:
        try:
            cur.execute(
                """
                INSERT INTO inspectie_itp (data_inspectie, km, emisii_co, eficienta_franare,
                                           convergenta, rezultat, data_expirare, id_vehicul, id_inspector)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    data_inspectie, itp.km, itp.emisii_co, itp.eficienta_franare,
                    itp.convergenta, rezultat, data_expirare, itp.id_vehicul, itp.id_inspector,
                ),
            )
            new_itp = cur.fetchone()
            conn.commit()
            return new_itp
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))