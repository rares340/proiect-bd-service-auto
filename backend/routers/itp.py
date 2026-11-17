from fastapi import APIRouter, Depends, HTTPException, status

from db import get_db
from schemas import InspectieITPCreate, InspectieITPResponse
from security import require_role

router = APIRouter(prefix="/api/itp", tags=["ITP"])


@router.post("", response_model=InspectieITPResponse, status_code=status.HTTP_201_CREATED)
def register_itp(
    itp: InspectieITPCreate,
    user: dict = Depends(require_role("INSPECTOR")),
    conn=Depends(get_db),
):
    if user["id_angajat"] is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="contul nu are un angajat asociat")

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO inspectie_itp (km, emisii_co, eficienta_franare, convergenta,
                                       rezultat, id_vehicul, id_inspector)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                itp.km, itp.emisii_co, itp.eficienta_franare, itp.convergenta,
                itp.rezultat, itp.id_vehicul, user["id_angajat"],
            ),
        )
        new_itp = cur.fetchone()
        conn.commit()
        return new_itp