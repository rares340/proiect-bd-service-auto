import os
from contextlib import contextmanager
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from dotenv import load_dotenv


load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "service_auto")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "parola")
DB_PORT = os.getenv("DB_PORT", "5432")

conn_str = f"host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASS} port={DB_PORT}"

pool = ConnectionPool(
    conn_info=conn_str,
    open=True,
    kwargs={"row_factory": dict_row}
)

@contextmanager
def get_db():
    """
    Generator care oferă o conexiune din pool și o returnează automat la final.
    """
    with pool.connection() as conn:
        yield conn
