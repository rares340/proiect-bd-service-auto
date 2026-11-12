from fastapi import APIRouter, Depends, HTTPException, status
from db import get_db
from schemas import UserLogin, UserResponse

router = APIRouter(prefix="/api", tags=["Autentificare"])


@router.post("/login", response_model=UserResponse)
def login(credentials: UserLogin, conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id_utilizator, nume_utilizator, rol, activ, id_angajat
            FROM utilizator
            WHERE nume_utilizator = %s AND parola = %s
            """,
            (credentials.nume_utilizator, credentials.parola),
        )
        user = cur.fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="nume sau parola incorecta",
            )

        if not user["activ"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="cont dezactivat",
            )

        return user