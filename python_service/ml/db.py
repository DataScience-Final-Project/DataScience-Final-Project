import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()


class DatabaseClient:
    def __init__(self):
        self.engine = create_engine(self._db_url())

    def read_sql(self, query: str) -> pd.DataFrame:
        return pd.read_sql_query(query, self.engine)

    def write_table(
        self,
        df: pd.DataFrame,
        table_name: str,
        if_exists: str = "replace",
        chunksize: int = 5000,
    ) -> None:
        df.to_sql(
            table_name,
            self.engine,
            if_exists=if_exists,
            index=False,
            method='multi',
            chunksize=chunksize,
        )

    def _db_url(self) -> str:
        return (
            f"postgresql://{os.getenv('PGUSER')}:{os.getenv('PGPASSWORD')}"
            f"@{os.getenv('PGHOST', '127.0.0.1')}:{os.getenv('PGPORT', '5432')}"
            f"/{os.getenv('PGDATABASE')}"
        )
