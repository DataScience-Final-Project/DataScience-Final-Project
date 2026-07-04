import os

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

from ml.clustering import build_growth_clusters, save_growth_clusters
from ml.config import PREDICTION_BASELINE_YEAR, PREDICTION_TEXT_COLS, RAW_TARGET_COL
from ml.historical_features import HistoricalMomentumFeatureEngineer
from ml.local_market_features import LocalMarketFeatureEngineer
from ml.modeling import HorizonConfigProvider, ModelRegistry
from ml.preprocessing import FeatureEngineer

load_dotenv()


def build_and_save_property_predictions():
    print("Starting Per-Property Prediction Generation...")

    engine = create_engine(_db_url())
    config_provider = HorizonConfigProvider()
    model_registry = ModelRegistry(config_provider)

    prediction_frames = []
    cluster_frames = []

    for horizon in config_provider.horizons():
        print(f"\nGenerating {horizon}-year property predictions...")
        model = model_registry.load_model(horizon)
        full_df = _load_horizon_snapshots(engine, horizon)
        df = _prediction_rows(full_df)
        if df.empty:
            print(f"No prediction snapshots found for {horizon}-year horizon. Skipping.")
            continue

        baseline = _cohort_baseline(df, horizon)
        relative_log_change = _predict_relative_log_change(full_df, df.index, model, config_provider.get(horizon))
        raw_log_change = relative_log_change + baseline

        prediction_frames.append(pd.DataFrame({
            'property_id': df['property_id'].values,
            'horizon_years': horizon,
            'log_change': raw_log_change,
            'percent_change': np.round(np.expm1(raw_log_change) * 100, 2),
            'price_at_snapshot': df['price_t0'].round(0).astype('Int64').values,
        }))

        cluster_frames.append(pd.DataFrame({
            'property_id': df['property_id'].values,
            'horizon_years': horizon,
            'log_change': raw_log_change,
            'lat': df['lat'].values,
            'lon': df['lon'].values,
        }))

    if not prediction_frames:
        print("No predictions generated. Nothing to save.")
        return

    output_df = pd.concat(prediction_frames, ignore_index=True)

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

    cluster_input = pd.concat(cluster_frames, ignore_index=True)
    clusters = build_growth_clusters(cluster_input)
    print(f"Writing {len(clusters)} DBSCAN clusters to growth_clusters...")
    save_growth_clusters(engine, clusters)
    print(f"Done. {len(clusters)} rows written to growth_clusters.")


def _db_url() -> str:
    return (
        f"postgresql://{os.getenv('PGUSER')}:{os.getenv('PGPASSWORD')}"
        f"@{os.getenv('PGHOST')}:{os.getenv('PGPORT')}/{os.getenv('PGDATABASE')}"
    )


def _load_horizon_snapshots(engine, horizon: int) -> pd.DataFrame:
    print(f"Loading snapshots for {horizon}-year horizon...")
    query = f"""
        SELECT s.*, p.lat, p.lon
        FROM property_features_snapshot s
        JOIN properties p ON s.property_id = p.property_id
        WHERE s.horizon_years = {horizon}
          AND s.price_t0 IS NOT NULL
    """
    df = pd.read_sql_query(query, engine)
    print(f"Loaded {len(df)} rows for {horizon}-year feature history.")
    return df


def _prediction_rows(df: pd.DataFrame) -> pd.DataFrame:
    mask = (
        (df['snapshot_year'] == PREDICTION_BASELINE_YEAR)
        & (df['price_t0'].between(500000, 15000000))
    )
    result = df.loc[mask].copy()
    print(f"Selected {len(result)} baseline rows for prediction.")
    return result


def _cohort_baseline(df: pd.DataFrame, horizon: int) -> float:
    if RAW_TARGET_COL not in df.columns:
        print(f"No {RAW_TARGET_COL} column found. Using 0 baseline for {horizon}-year horizon.")
        return 0.0

    baseline = pd.to_numeric(df[RAW_TARGET_COL], errors='coerce').mean()
    if not np.isfinite(baseline):
        print(f"No valid cohort baseline found. Using 0 baseline for {horizon}-year horizon.")
        return 0.0

    print(f"Using {horizon}-year cohort baseline log growth: {baseline:.4f}")
    return float(baseline)


def _predict_relative_log_change(
    full_df: pd.DataFrame,
    prediction_index: pd.Index,
    model,
    horizon_config: dict,
) -> np.ndarray:
    feature_engineer = FeatureEngineer(
        use_market_trend=horizon_config.get('use_market_trend', False),
        market_trend_area_col=horizon_config.get('market_trend_area_col', 'city_name'),
    )
    historical_feature_engineer = HistoricalMomentumFeatureEngineer(
        recent_window_years=horizon_config.get('recent_window_years')
    )
    local_market_feature_engineer = LocalMarketFeatureEngineer()
    expected_cols = model.get_booster().feature_names

    passthrough_cols = {*PREDICTION_TEXT_COLS, 'lat', 'lon'}
    cleaned = feature_engineer._clean_raw_prediction_values(full_df, passthrough_cols)
    transformed = feature_engineer.transform(cleaned)
    transformed = historical_feature_engineer.transform(transformed)
    transformed = local_market_feature_engineer.transform(transformed)
    prediction_df = transformed.loc[prediction_index]

    X = prediction_df[[c for c in expected_cols if c in prediction_df.columns]].copy()
    for col in expected_cols:
        if col not in X.columns:
            X[col] = np.nan
    X = X[expected_cols]
    return model.predict(X)


if __name__ == "__main__":
    build_and_save_property_predictions()