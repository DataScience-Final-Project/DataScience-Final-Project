import pandas as pd
from ml.db import DatabaseClient

def load_snapshot_data(horizon: int) -> pd.DataFrame:
    print(f"Loading data from database (Horizon: {horizon} years)...")

    query = f"""
        SELECT s.*, p.lat, p.lon
        FROM property_features_snapshot s
        JOIN properties p ON s.property_id = p.property_id
        WHERE s.horizon_years = {horizon}
          AND s.price_t0 IS NOT NULL 
          AND s.price_t1 IS NOT NULL
          AND s.log_change IS NOT NULL;
    """
    
    df = DatabaseClient().read_sql(query)
   
    
    print(f" Loaded {len(df)} property snapshots from DB.")
    return df
