from typing import List, Optional
from fastapi import APIRouter, Depends, status
from db import get_db
from schemas import ClientCreate, ClientResponse

router = APIRouter(prefix="/api/clienti", tags=["Clienti"])


@router.get("", response_model=List[ClientResponse])
def get_clienti(search: Optional[str] = None, conn=Depends(get_db)):
    with conn.cursor() as cur:
        if search:
            p = f"%{search}%"
            cur.execute(
                """
                SELECT id_client, nume, prenume, telefon, email
                FROM client
                WHERE nume ILIKE %s OR prenume ILIKE %s OR telefon ILIKE %s
                """,
                (p, p, p),
            )
        else:
            cur.execute("SELECT id_client, nume, prenume, telefon, email FROM client")
        return cur.fetchall()


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(client: ClientCreate, conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO client (nume, prenume, telefon, email)
            VALUES (%s, %s, %s, %s)
            RETURNING id_client, nume, prenume, telefon, email
            """,
            (client.nume, client.prenume, client.telefon, client.email),
        )
        new_client = cur.fetchone()
        conn.commit()
        return new_client