import argparse
import json

import pandas as pd
import xgboost as xgb
import numpy as np
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

from ml.config import COLS_TO_DROP, HORIZON_CONFIGS
from ml.pipeline import apply_city_room_price_ratio, compute_national_momentum, compute_price_momentum

load_dotenv()


def build_and_save_property_predictions(dry_run: bool = False):
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

    poi_now_cols = [f'{poi}_score_now' for poi in poi_types if f'{poi}_score_now' in df_all.columns]
    poi_future_cols = [f'{poi}_score_future' for poi in poi_types if f'{poi}_score_future' in df_all.columns]
    poi_delta_cols = [f'{poi}_score_delta' for poi in poi_types if f'{poi}_score_delta' in df_all.columns]
    if poi_now_cols:
        df_all['total_poi_score_now'] = df_all[poi_now_cols].sum(axis=1)
    if poi_future_cols:
        df_all['total_poi_score_future'] = df_all[poi_future_cols].sum(axis=1)
    if poi_delta_cols:
        df_all['total_poi_score_delta'] = df_all[poi_delta_cols].sum(axis=1)

    df_all['log_price_t0'] = np.log(df_all['price_t0'])

    if 'num_rooms' in df_all.columns:
        df_all['price_per_room'] = np.where(
            df_all['num_rooms'] > 0, df_all['price_t0'] / df_all['num_rooms'], np.nan
        )

    print("Loading historical price trend data for momentum features...")
    history_query = """
        SELECT DISTINCT ON (s.property_id, s.snapshot_year)
            s.snapshot_year, s.city_name, s.price_t0, p.lat, p.lon
        FROM property_features_snapshot s
        JOIN properties p ON s.property_id = p.property_id
        WHERE s.snapshot_year < 2014
          AND s.price_t0 > 0
        ORDER BY s.property_id, s.snapshot_year
    """
    history_df = pd.read_sql_query(history_query, engine)
    history_df['log_price_t0'] = np.log(history_df['price_t0'])
    momentum_cols = ['snapshot_year', 'city_name', 'log_price_t0', 'lat', 'lon']
    n_history = len(history_df)

    print("Predicting 5-year and 10-year growth for each property...")
    models = {5: model_5y, 10: model_10y}
    predictions = {}

    for horizon, model in models.items():
        h_config = HORIZON_CONFIGS[horizon]
        lookback_years = h_config.get("momentum_lookback_years", 3)
        use_national_momentum = h_config.get("use_national_momentum", True)

        # Momentum is backward-looking (only uses years strictly before each
        # row's own snapshot_year), so combining historical price data with
        # the "as of 2014" batch and computing over the combined frame gives
        # each 2014 row the correct trailing trend — same construction as
        # pipeline.py's clean_and_engineer_features during training.
        combined = pd.concat(
            [history_df[momentum_cols], df_all[momentum_cols]],
            ignore_index=True,
        )
        df_h = df_all.copy()
        df_h['price_momentum'] = compute_price_momentum(
            combined, lookback_years=lookback_years
        ).iloc[n_history:].to_numpy()
        if use_national_momentum:
            df_h['national_price_momentum'] = compute_national_momentum(
                combined, lookback_years=lookback_years
            ).iloc[n_history:].to_numpy()

        expected_cols = model.get_booster().feature_names
        X = df_h[[c for c in expected_cols if c in df_h.columns]].copy()

        # Structural fallback only — creates the column if entirely absent
        # from the query result. Missing values within an existing column
        # are left as NaN so XGBoost's native NaN routing handles them,
        # matching training.
        if 'location_accuracy' not in X.columns:
            X['location_accuracy'] = 1
        X['location_accuracy'] = X['location_accuracy'].astype('category')

        if 'city_name' in X.columns:
            X['city_name'] = X['city_name'].astype('category')

        if 'city_room_price_ratio' in expected_cols:
            stats_path = h_config["model_save_path"].replace('.json', '_city_room_stats.json')
            if os.path.exists(stats_path):
                with open(stats_path, "r", encoding="utf-8") as f:
                    stats_payload = json.load(f)
                stats = pd.Series(
                    {(r["city_name"], r["num_rooms"]): r["median_log_price_t0"] for r in stats_payload["stats"]}
                )
                df_h['city_room_price_ratio'] = apply_city_room_price_ratio(
                    df_h, stats, stats_payload["global_median"]
                )
                X['city_room_price_ratio'] = df_h['city_room_price_ratio']
            else:
                print(f"⚠️ city_room_price_ratio expected but stats file not found at {stats_path}; leaving as NaN.")

        for col in expected_cols:
            if col not in X.columns:
                X[col] = df_h[col] if col in df_h.columns else np.nan

        X = X[expected_cols]
        predictions[horizon] = model.predict(X)

    raw_5y = predictions[5]
    raw_10y = predictions[10]

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

    if dry_run:
        print(f"[dry-run] Would write {len(output_df)} rows to property_predictions. Sample:")
        print(output_df.sample(min(10, len(output_df)), random_state=42).to_string(index=False))
        return output_df

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
    return output_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Skip the DB write; print a sample instead.")
    args = parser.parse_args()

    build_and_save_property_predictions(dry_run=args.dry_run)