import os
import psycopg2
from dotenv import load_dotenv
from etl.common.paths import PSVC

load_dotenv(PSVC / ".env")  # always loads python_service/.env

def get_conn():
    return psycopg2.connect(
        host=os.getenv("PGHOST", "127.0.0.1"),
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
    )