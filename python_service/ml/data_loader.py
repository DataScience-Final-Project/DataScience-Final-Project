import pandas as pd
import psycopg2
from etl.common.db import get_conn

def load_snapshot_data(horizon: int) -> pd.DataFrame:
    print(f"Loading data from database (Horizon: {horizon} years)...")
    conn = get_conn()
    
    query = f"""
        SELECT * FROM property_features_snapshot
        WHERE horizon_years = {horizon}
          AND price_t0 IS NOT NULL 
          AND price_t1 IS NOT NULL
          AND log_change IS NOT NULL;
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    print(f" Loaded {len(df)} property snapshots from DB.")
    return df