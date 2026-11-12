from fastapi import APIRouter, Depends, HTTPException, status
from db import get_db
from schemas import ComandaCreate, ComandaResponse

router = APIRouter(prefix="/api/comenzi", tags=["Comenzi"])


@router.post("", response_model=ComandaResponse, status_code=status.HTTP_201_CREATED)
def create_comanda(comanda: ComandaCreate, conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO comanda_reparatie (km_intrare, reclamatie, id_vehicul, id_operator, status)
            VALUES (%s, %s, %s, %s, 'DESCHISA')
            RETURNING id_comanda, data_intrare, data_predare, km_intrare, status,
                      reclamatie, id_vehicul, id_operator
            """,
            (comanda.km_intrare, comanda.reclamatie, comanda.id_vehicul, comanda.id_operator),
        )
        new_comanda = cur.fetchone()
        conn.commit()
        return new_comanda


@router.post("/{id_comanda}/piese")
def add_piesa_to_comanda(id_comanda: int, id_piesa: int, cantitate: int, conn=Depends(get_db)):
    if cantitate <= 0:
        raise HTTPException(status_code=400, detail="cantitatea trebuie sa fie mai mare ca 0")

    with conn.cursor() as cur:
        cur.execute(
            "SELECT stoc_curent, prag_minim, pret_vanzare FROM piesa WHERE id_piesa = %s",
            (id_piesa,),
        )
        piesa = cur.fetchone()
        if not piesa:
            raise HTTPException(status_code=404, detail="piesa negasita")

        if piesa["stoc_curent"] < cantitate:
            raise HTTPException(
                status_code=400,
                detail=f"Stoc insuficient! Stoc disponibil: {piesa['stoc_curent']}",
            )

        pret_unitar = piesa["pret_vanzare"]

        try:
            cur.execute(
                """
                INSERT INTO piesa_comanda (id_comanda, id_piesa, cantitate, pret_unitar_aplicat)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id_comanda, id_piesa)
                DO UPDATE SET cantitate = piesa_comanda.cantitate + EXCLUDED.cantitate
                """,
                (id_comanda, id_piesa, cantitate, pret_unitar),
            )

            cur.execute(
                """
                UPDATE piesa
                SET stoc_curent = stoc_curent - %s
                WHERE id_piesa = %s
                RETURNING stoc_curent, prag_minim, denumire
                """,
                (cantitate, id_piesa),
            )
            updated_piesa = cur.fetchone()
            conn.commit()

            alerta = None
            if updated_piesa["stoc_curent"] <= updated_piesa["prag_minim"]:
                alerta = (
                    f"ATENȚIE: Piesa '{updated_piesa['denumire']}' a ajuns sub pragul minim "
                    f"(Stoc: {updated_piesa['stoc_curent']})."
                )

            return {
                "message": "Piesa a fost adăugată cu succes la comandă și stocul a fost actualizat.",
                "stoc_ramas": updated_piesa["stoc_curent"],
                "alerta": alerta,
            }

        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))