import os
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine

load_dotenv()
    
def load_snapshot_data(horizon: int) -> pd.DataFrame:
    print(f"Loading data from database (Horizon: {horizon} years)...")
    db_url = f"postgresql://{os.getenv('PGUSER')}:{os.getenv('PGPASSWORD')}@{os.getenv('PGHOST', '127.0.0.1')}:{os.getenv('PGPORT', '5432')}/{os.getenv('PGDATABASE')}"
    engine = create_engine(db_url)

    query = f"""
        SELECT * FROM property_features_snapshot
        WHERE horizon_years = {horizon}
          AND price_t0 IS NOT NULL 
          AND price_t1 IS NOT NULL
          AND log_change IS NOT NULL;
    """
    
    df = pd.read_sql_query(query, engine)
   
    
    print(f" Loaded {len(df)} property snapshots from DB.")
    return df