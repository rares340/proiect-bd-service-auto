import sys

from db import pool
from security import hash_parola


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return
    nume, parola, rol = sys.argv[1:4]
    id_angajat = int(sys.argv[4]) if len(sys.argv) > 4 else None

    with pool.connection() as conn:
        conn.execute(
            "INSERT INTO utilizator (nume_utilizator, parola, rol, id_angajat) VALUES (%s, %s, %s, %s)",
            (nume, hash_parola(parola), rol, id_angajat),
        )
    pool.close()
    print(f"Utilizator '{nume}' creat cu rolul {rol}.")


if __name__ == "__main__":
    main()