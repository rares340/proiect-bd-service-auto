from db import pool
from security import hash_parola, verifica_parola

PAROLE = {
    "admin": "parola123",
    "Admin": "parola123",
    "operator1": "parola123",
    "itp_inspector": "parola123",
}

with pool.connection() as conn:
    for nume, parola in PAROLE.items():
        cur = conn.execute(
            "UPDATE utilizator SET parola=%s, activ=true WHERE nume_utilizator=%s",
            (hash_parola(parola), nume),
        )
        print(f"{nume}: {cur.rowcount} rand modificat")

    print()
    for r in conn.execute("SELECT nume_utilizator, parola FROM utilizator ORDER BY id_utilizator"):
        ok = verifica_parola(PAROLE.get(r["nume_utilizator"], ""), r["parola"])
        print(f"{r['nume_utilizator']}: parola merge = {ok}")

pool.close()