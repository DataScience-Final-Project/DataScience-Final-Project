# ml/inspect_anomalies.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import pandas as pd
from ml.config import HORIZON_CONFIGS
from ml.data_loader import load_snapshot_data
from ml.pipeline import prepare_data

def inspect_anomalies(horizon: int, threshold_pct: float = -60.0):
    """
    Finds and prints test-set properties that lost more than 'threshold_pct' of their value.
    """
    print(f"\n{'='*60}")
    print(f"🔍 INSPECTING WEIRD DATA FOR {horizon}-YEAR HORIZON")
    print(f"{'='*60}")
    
    if horizon not in HORIZON_CONFIGS:
        return
        
    config = HORIZON_CONFIGS[horizon]
    split_year = config["split_year"]
    
    # 1. Load Data
    df = load_snapshot_data(horizon=horizon)
    if df.empty:
        return
        
    # 2. Run Pipeline (to get the exact Test set we evaluated)
    X_train, X_test, y_train, y_test = prepare_data(df, split_year)
    
    # 3. Convert Log Return back to Normal Percentage
    actual_growth_pct = (np.exp(y_test) - 1) * 100
    
    # 4. Filter for massive drops
    anomaly_indices = actual_growth_pct[actual_growth_pct < threshold_pct].index
    
    print(f"\n🚨 Found {len(anomaly_indices)} properties in the test set with > {abs(threshold_pct)}% price drop.")
    
    if len(anomaly_indices) > 0:
        # Extract the original un-dropped data for these specific rows
        anomalies_df = df.loc[anomaly_indices].copy()
        anomalies_df['actual_growth_pct'] = actual_growth_pct.loc[anomaly_indices]
        
        # Format the prices to look like normal money (e.g., 2,000,000)
        pd.options.display.float_format = '{:,.2f}'.format
        
        # Select the most readable columns
        display_cols = [
            'city_name', 'snapshot_year', 'num_rooms', 
            'price_t0', 'price_t1', 'actual_growth_pct'
        ]
        
        # Sort to see the absolute craziest drops first
        worst_drops = anomalies_df.sort_values('actual_growth_pct').head(15)
        
        print("\nTop 15 most extreme price drops:")
        print("-" * 60)
        print(worst_drops[display_cols].to_string(index=False))

if __name__ == "__main__":
    # Suppress the pipeline prints so our output is clean
    import sys, os
    
    for h in [5, 10]:
        inspect_anomalies(h)