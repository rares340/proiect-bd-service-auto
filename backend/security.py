import secrets
from typing import Optional

import bcrypt
from fastapi import Depends, Header, HTTPException, status

# token -> datele utilizatorului logat (se pierd la repornirea serverului)
SESSIONS: dict = {}


def hash_parola(parola: str) -> str:
    return bcrypt.hashpw(parola.encode(), bcrypt.gensalt()).decode()


def verifica_parola(parola: str, hash_salvat: str) -> bool:
    try:
        return bcrypt.checkpw(parola.encode(), hash_salvat.encode())
    except ValueError:
        return False


def creeaza_token(user: dict) -> str:
    token = secrets.token_hex(32)
    SESSIONS[token] = {
        "id_utilizator": user["id_utilizator"],
        "nume_utilizator": user["nume_utilizator"],
        "rol": user["rol"],
        "id_angajat": user["id_angajat"],
    }
    return token


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Citește header-ul 'Authorization: Bearer <token>' și returnează utilizatorul."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="autentificare necesara")
    user = SESSIONS.get(authorization[7:])
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="token invalid")
    return user


def require_role(*roluri: str):
    """Folosire: Depends(require_role('OPERATOR', 'ADMINISTRATOR'))"""
    def verifica(user: dict = Depends(get_current_user)) -> dict:
        if user["rol"] not in roluri:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="nu aveti dreptul sa faceti aceasta actiune")
        return user
    return verifica