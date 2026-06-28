import pandas as pd
import geopandas as gpd
from shapely.geometry import  MultiPolygon, Polygon
import xgboost as xgb
import numpy as np
from sqlalchemy import create_engine
import os
import h3
from dotenv import load_dotenv

from ml.config import COLS_TO_DROP

load_dotenv()

def build_and_save_heatmap_data():
    print("Starting H3 Hexagonal Heatmap Data Generation...")

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

    # Compute derived features to match what pipeline.py builds during training
    poi_types = ['school', 'train', 'health', 'park', 'supermarket', 'mall',
                 'hotel', 'kindergarten', 'light_rail', 'bus', 'hospital', 'clinic']
    for poi in poi_types:
        now_col = f'{poi}_score_now'
        future_col = f'{poi}_score_future'
        if now_col in df_all.columns and future_col in df_all.columns:
            df_all[f'{poi}_score_delta'] = df_all[future_col] - df_all[now_col]

    df_all['log_price_t0'] = np.log(df_all['price_t0'])

    expected_cols = model_5y.get_booster().feature_names

    # ==========================================
    # Predict per individual property (vectorized)
    # ==========================================
    print("Predicting 5-year and 10-year growth for each property...")
    X = df_all[[c for c in expected_cols if c in df_all.columns]].copy()

    if 'num_rooms' in X.columns:
        X['num_rooms'] = X['num_rooms'].fillna(3)

    if 'location_accuracy' not in X.columns:
        X['location_accuracy'] = 1
    X['location_accuracy'] = X['location_accuracy'].fillna(1).astype('category')

    if 'city_name' in X.columns:
        X['city_name'] = X['city_name'].fillna(X['city_name'].mode()[0]).astype('category')

    # Ensure all expected columns are present (fill missing ones with NaN)
    for col in expected_cols:
        if col not in X.columns:
            X[col] = np.nan

    X = X[expected_cols]

    df_all['growth_5y'] = np.expm1(model_5y.predict(X)) * 100
    df_all['growth_10y'] = np.expm1(model_10y.predict(X)) * 100

    # ==========================================
    # Map coordinates to H3 hexagons (vectorized)
    # ==========================================
    print("Mapping coordinates to H3 Hexagons (Resolution 8)...")
    RESOLUTION = 8
    df_all['h3_index'] = [
        h3.latlng_to_cell(lat, lon, RESOLUTION)
        for lat, lon in zip(df_all['lat'], df_all['lon'])
    ]

    # ==========================================
    # Aggregate predictions (not features) by hex
    # ==========================================
    print(f"Aggregating {len(df_all)} property predictions into distinct Hexagons...")
    hex_data = df_all.groupby('h3_index').agg(
        growth_5y_pct=('growth_5y', 'mean'),
        growth_10y_pct=('growth_10y', 'mean'),
        city_name=('city_name', 'first'),
        price_now=('price_t0', 'mean'),
    ).reset_index()

    hex_data['growth_5y_pct'] = hex_data['growth_5y_pct'].round(2)
    hex_data['growth_10y_pct'] = hex_data['growth_10y_pct'].round(2)
    hex_data['price_now'] = hex_data['price_now'].round(0).astype('Int64')

    # ==========================================
    # Build polygon geometry from H3 index
    # cell_to_boundary returns (lat, lon); Shapely needs (lon, lat)
    # ==========================================
    hex_data['geom'] = [
        Polygon([(lon, lat) for lat, lon in h3.cell_to_boundary(h3_id)])
        for h3_id in hex_data['h3_index']
    ]

    hex_data['neighborhood_name'] = 'Hex ' + hex_data['h3_index']
    hex_data['baseline_year'] = 2014

    # ==========================================
    # Save to PostGIS
    # ==========================================
    print("\nSaving H3 Heatmap Polygons to Database...")
    output_gdf = gpd.GeoDataFrame(
        hex_data[['city_name', 'neighborhood_name', 'baseline_year', 'growth_5y_pct', 'growth_10y_pct', 'price_now', 'geom']],
        geometry='geom',
        crs="EPSG:4326"
    )
    output_gdf['geom'] = output_gdf['geom'].apply(lambda x: MultiPolygon([x]) if x.geom_type == 'Polygon' else x)
    output_gdf.to_postgis('neighborhood_predictions', engine, if_exists='replace', index=False)

    print("H3 Grid Heatmap successfully saved. Ready for UI consumption.")

if __name__ == "__main__":
    build_and_save_heatmap_data()
