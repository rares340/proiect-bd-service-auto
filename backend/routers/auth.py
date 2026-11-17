from fastapi import APIRouter, Depends, HTTPException, status
from db import get_db
from schemas import UserLogin, LoginResponse, UserResponse
from security import verifica_parola, creeaza_token, get_current_user

router = APIRouter(prefix="/api", tags=["Autentificare"])


@router.post("/login", response_model=LoginResponse)
def login(credentials: UserLogin, conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id_utilizator, nume_utilizator, parola, rol, activ, id_angajat
            FROM utilizator
            WHERE nume_utilizator = %s
            """,
            (credentials.nume_utilizator,),
        )
        user = cur.fetchone()

    if not user or not verifica_parola(credentials.parola, user["parola"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="nume sau parola incorecta",
        )

    if not user["activ"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="cont dezactivat",
        )

    return {
        "id_utilizator": user["id_utilizator"],
        "nume_utilizator": user["nume_utilizator"],
        "rol": user["rol"],
        "id_angajat": user["id_angajat"],
        "token": creeaza_token(user),
    }


@router.get("/me", response_model=UserResponse)
def me(user: dict = Depends(get_current_user)):
    """Util pentru test: arată cine este logat pe baza tokenului."""
    return user