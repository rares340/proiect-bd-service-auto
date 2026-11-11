from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import date, timedelta
import psycopg

from db import get_db
from schemas import (
    UserLogin, UserResponse,
    ClientCreate, ClientResponse,
    VehiculCreate, VehiculResponse,
    ComandaCreate, ComandaResponse,
    InspectieITPCreate, InspectieITPResponse
)

app = FastAPI(
    title="Service Auto & ITP API",
    version="1.0.0",
    description="Backend pentru gestionarea service-ului auto și a stației ITP."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "API-ul ruleaza cu succes"}

@app.post("/api/login", response_model=UserResponse)
def login(credentials: UserLogin, conn = Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id_utilizator, nume_utilizator, rol, activ, id_angajat 
            FROM utilizator 
            WHERE nume_utilizator = %s AND parola = %s
            """,
            (credentials.nume_utilizator, credentials.parola)
        )
        user = cur.fetchone()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="nume sau parola incorecta"
            )
        
        if not user["activ"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="cont dezactivat"
            )
            
        return user

@app.get("/api/clienti", response_model=List[ClientResponse])
def get_clienti(search: Optional[str] = None, conn = Depends(get_db)):
    with conn.cursor() as cur:
        if search:
            query = """
                SELECT id_client, nume, prenume, telefon, email 
                FROM client 
                WHERE nume ILIKE %s OR prenume ILIKE %s OR telefon ILIKE %s
            """
            search_pattern = f"%{search}%"
            cur.execute(query, (search_pattern, search_pattern, search_pattern))
        else:
            cur.execute("SELECT id_client, nume, prenume, telefon, email FROM client")
        return cur.fetchall()

@app.post("/api/clienti", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(client: ClientCreate, conn = Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO client (nume, prenume, telefon, email)
            VALUES (%s, %s, %s, %s)
            RETURNING id_client, nume, prenume, telefon, email
            """,
            (client.nume, client.prenume, client.telefon, client.email)
        )
        new_client = cur.fetchone()
        conn.commit()
        return new_client

@app.get("/api/vehicule", response_model=List[VehiculResponse])
def get_vehicule(id_client: Optional[int] = None, nr_inmatriculare: Optional[str] = None, conn = Depends(get_db)):
    with conn.cursor() as cur:
        if id_client:
            cur.execute(
                "SELECT * FROM vehicul WHERE id_client = %s",
                (id_client,)
            )
        elif nr_inmatriculare:
            cur.execute(
                "SELECT * FROM vehicul WHERE nr_inmatriculare ILIKE %s",
                (f"%{nr_inmatriculare}%",)
            )
        else:
            cur.execute("SELECT * FROM vehicul")
        return cur.fetchall()

@app.post("/api/vehicule", response_model=VehiculResponse, status_code=status.HTTP_201_CREATED)
def create_vehicul(vehicul: VehiculCreate, conn = Depends(get_db)):
    with conn.cursor() as cur:
        try:
            cur.execute(
                """
                INSERT INTO vehicul (serie_sasiu, nr_inmatriculare, marca, model, motorizare, combustibil, an_fabricatie, norma_poluare, id_client)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    vehicul.serie_sasiu, vehicul.nr_inmatriculare, vehicul.marca,
                    vehicul.model, vehicul.motorizare, vehicul.combustibil,
                    vehicul.an_fabricatie, vehicul.norma_poluare, vehicul.id_client
                )
            )
            new_vehicul = cur.fetchone()
            conn.commit()
            return new_vehicul
        except psycopg.errors.UniqueViolation:
            conn.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="exista deja un vehicul inregistrat cu aceasta serie de sasiu sau numar de inmatriculare"
            )
        
@app.post("/api/comenzi", response_model=ComandaResponse, status_code=status.HTTP_201_CREATED)
def create_comanda(comanda: ComandaCreate, conn = Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO comanda_reparatie (km_intrare, reclamatie, id_vehicul, id_operator, status)
            VALUES (%s, %s, %s, %s, 'DESCHISA')
            RETURNING id_comanda, data_intrare, data_predare, km_intrare, status, reclamatie, id_vehicul, id_operator
            """,
            (comanda.km_intrare, comanda.reclamatie, comanda.id_vehicul, comanda.id_operator)
        )
        new_comanda = cur.fetchone()
        conn.commit()
        return new_comanda

@app.post("/api/comenzi/{id_comanda}/piese")
def add_piesa_to_comanda(id_comanda: int, id_piesa: int, cantitate: int, conn = Depends(get_db)):
    if cantitate <= 0:
        raise HTTPException(status_code=400, detail="cantitatea trebuie sa fie mai mare ca 0")
    
    with conn.cursor() as cur:
        cur.execute("SELECT stoc_curent, prag_minim, pret_vanzare FROM piesa WHERE id_piesa = %s", (id_piesa,))
        piesa = cur.fetchone()
        if not piesa:
            raise HTTPException(status_code=404, detail="piesa negasita")
        
        if piesa["stoc_curent"] < cantitate:
            raise HTTPException(status_code=400, detail=f"Stoc insuficient! Stoc disponibil: {piesa['stoc_curent']}")
        
        pret_unitar = piesa["pret_vanzare"]

        try:
            cur.execute(
                """
                INSERT INTO piesa_comanda (id_comanda, id_piesa, cantitate, pret_unitar_aplicat)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id_comanda, id_piesa) 
                DO UPDATE SET cantitate = piesa_comanda.cantitate + EXCLUDED.cantitate
                """,
                (id_comanda, id_piesa, cantitate, pret_unitar)
            )

            cur.execute(
                """
                UPDATE piesa 
                SET stoc_curent = stoc_curent - %s 
                WHERE id_piesa = %s
                RETURNING stoc_curent, prag_minim, denumire
                """,
                (cantitate, id_piesa)
            )
            updated_piesa = cur.fetchone()
            conn.commit()

            alerta = None
            if updated_piesa["stoc_curent"] <= updated_piesa["prag_minim"]:
                alerta = f"ATENȚIE: Piesa '{updated_piesa['denumire']}' a ajuns sub pragul minim (Stoc: {updated_piesa['stoc_curent']})."

            return {
                "message": "Piesa a fost adăugată cu succes la comandă și stocul a fost actualizat.",
                "stoc_ramas": updated_piesa["stoc_curent"],
                "alerta": alerta
            }

        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/itp", response_model=InspectieITPResponse, status_code=status.HTTP_201_CREATED)
def register_itp(itp: InspectieITPCreate, conn = Depends(get_db)):
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
                INSERT INTO inspectie_itp (data_inspectie, km, emisii_co, eficienta_franare, convergenta, rezultat, data_expirare, id_vehicul, id_inspector)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    data_inspectie, itp.km, itp.emisii_co, itp.eficienta_franare,
                    itp.convergenta, rezultat, data_expirare, itp.id_vehicul, itp.id_inspector
                )
            )
            new_itp = cur.fetchone()
            conn.commit()
            return new_itp
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))
