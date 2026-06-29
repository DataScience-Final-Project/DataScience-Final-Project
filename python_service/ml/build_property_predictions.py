import pandas as pd
import xgboost as xgb
import numpy as np
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

from ml.config import COLS_TO_DROP

load_dotenv()


def build_and_save_property_predictions():
    print("Starting Per-Property Prediction Generation...")

    engine = create_engine(f"postgresql://{os.getenv('PGUSER')}:{os.getenv('PGPASSWORD')}@{os.getenv('PGHOST')}:{os.getenv('PGPORT')}/{os.getenv('PGDATABASE')}")

    print("Loading Machine Learning Models...")
    model_5y = xgb.XGBRegressor(enable_categorical=True)
    model_5y.load_model("data/saved_models/xgb_real_estate_5yr_v1.json")

    model_10y = xgb.XGBRegressor(enable_categorical=True)
    model_10y.load_model("data/saved_models/xgb_real_estate_10yr_v1.json")

    print("Loading all 2014 property snapshots from Database...")
    query = """
        SELECT s.*, p.lat, p.lon
        FROM property_features_snapshot s
        JOIN properties p ON s.property_id = p.property_id
        WHERE s.snapshot_year = 2014
          AND s.price_t0 BETWEEN 500000 AND 15000000
    """
    df_all = pd.read_sql_query(query, engine)

    df_all = df_all.replace(r'^\s*$', np.nan, regex=True)
    df_all = df_all.replace(['NULL', 'null', 'None'], np.nan)

    cols_to_keep_as_text = ['city_name', 'street', 'property_key', 'house_number']
    for col in df_all.columns:
        if col not in cols_to_keep_as_text and col not in ['lat', 'lon']:
            df_all[col] = pd.to_numeric(df_all[col], errors='coerce')

    poi_types = ['school', 'train', 'health', 'park', 'supermarket', 'mall',
                 'hotel', 'kindergarten', 'light_rail', 'bus', 'hospital', 'clinic']
    for poi in poi_types:
        now_col = f'{poi}_score_now'
        future_col = f'{poi}_score_future'
        if now_col in df_all.columns and future_col in df_all.columns:
            df_all[f'{poi}_score_delta'] = df_all[future_col] - df_all[now_col]

    df_all['log_price_t0'] = np.log(df_all['price_t0'])

    expected_cols = model_5y.get_booster().feature_names

    print("Predicting 5-year and 10-year growth for each property...")
    X = df_all[[c for c in expected_cols if c in df_all.columns]].copy()

    if 'num_rooms' in X.columns:
        X['num_rooms'] = X['num_rooms'].fillna(3)

    if 'location_accuracy' not in X.columns:
        X['location_accuracy'] = 1
    X['location_accuracy'] = X['location_accuracy'].fillna(1).astype('category')

    if 'city_name' in X.columns:
        X['city_name'] = X['city_name'].fillna(X['city_name'].mode()[0]).astype('category')

    for col in expected_cols:
        if col not in X.columns:
            X[col] = np.nan

    X = X[expected_cols]

    raw_5y = model_5y.predict(X)
    raw_10y = model_10y.predict(X)

    rows_5y = pd.DataFrame({
        'property_id':        df_all['property_id'].values,
        'horizon_years':      5,
        'log_change':         raw_5y,
        'percent_change':     np.round(np.expm1(raw_5y) * 100, 2),
        'price_at_snapshot':  df_all['price_t0'].round(0).astype('Int64').values,
    })
    rows_10y = pd.DataFrame({
        'property_id':        df_all['property_id'].values,
        'horizon_years':      10,
        'log_change':         raw_10y,
        'percent_change':     np.round(np.expm1(raw_10y) * 100, 2),
        'price_at_snapshot':  df_all['price_t0'].round(0).astype('Int64').values,
    })

    output_df = pd.concat([rows_5y, rows_10y], ignore_index=True)

    print(f"Writing {len(output_df)} property predictions to DB...")
    output_df.to_sql(
        'property_predictions',
        engine,
        if_exists='replace',
        index=False,
        method='multi',
        chunksize=5000,
    )
    print(f"Done. {len(output_df)} rows written to property_predictions.")


if __name__ == "__main__":
    build_and_save_property_predictions()