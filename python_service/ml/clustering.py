import numpy as np
import pandas as pd
from shapely.geometry import MultiPoint
from sqlalchemy import text
from sklearn.cluster import DBSCAN

DBSCAN_EPS_KM = 0.75
DBSCAN_MIN_SAMPLES = 8
EARTH_RADIUS_KM = 6371.0


def build_growth_clusters(
    predictions: pd.DataFrame,
    eps_km: float = DBSCAN_EPS_KM,
    min_samples: int = DBSCAN_MIN_SAMPLES,
) -> pd.DataFrame:
    required_cols = {'property_id', 'horizon_years', 'log_change', 'lat', 'lon'}
    missing_cols = required_cols.difference(predictions.columns)
    if missing_cols:
        raise ValueError(f"Cannot cluster predictions: missing columns {sorted(missing_cols)}.")

    cluster_rows = []
    cluster_seq = 0

    for horizon in sorted(predictions['horizon_years'].dropna().unique()):
        horizon_df = predictions[predictions['horizon_years'] == horizon].copy()
        horizon_df = horizon_df.dropna(subset=['lat', 'lon', 'log_change'])
        if horizon_df.empty:
            print(f"No valid rows to cluster for {int(horizon)}-year horizon.")
            continue

        horizon_df['pred_growth'] = np.exp(horizon_df['log_change'] / horizon) - 1.0
        coords_rad = np.radians(horizon_df[['lat', 'lon']].values)
        labels = DBSCAN(
            eps=eps_km / EARTH_RADIUS_KM,
            min_samples=min_samples,
            metric='haversine',
        ).fit_predict(coords_rad)
        horizon_df['cluster_label'] = labels

        global_std = horizon_df['pred_growth'].std() or 1e-9
        n_clusters = 0

        for label in sorted(set(labels)):
            if label == -1:
                continue

            members = horizon_df[horizon_df['cluster_label'] == label]
            points = MultiPoint(list(zip(members['lon'], members['lat'])))
            polygon = points.convex_hull
            if polygon.geom_type != 'Polygon':
                polygon = polygon.buffer(0.0005)

            agreement = float(np.clip(1 - members['pred_growth'].std(skipna=True) / global_std, 0, 1))
            if np.isnan(agreement):
                agreement = 1.0
            support = min(1.0, len(members) / 20.0)
            certainty = round(0.6 * agreement + 0.4 * support, 4)

            cluster_rows.append({
                'cluster_id': cluster_seq,
                'horizon_years': int(horizon),
                'avg_growth': round(float(members['pred_growth'].mean()), 6),
                'certainty': certainty,
                'property_count': int(len(members)),
                'wkt': polygon.wkt,
            })
            cluster_seq += 1
            n_clusters += 1

        print(f"Built {n_clusters} DBSCAN growth clusters for {int(horizon)}-year horizon.")

    return pd.DataFrame(cluster_rows)


def save_growth_clusters(engine, clusters: pd.DataFrame) -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.growth_clusters (
                id SERIAL PRIMARY KEY,
                cluster_id INTEGER,
                horizon_years INTEGER,
                avg_growth FLOAT8,
                certainty FLOAT8,
                geom GEOMETRY(Polygon, 4326),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.execute(text("ALTER TABLE public.growth_clusters ADD COLUMN IF NOT EXISTS horizon_years INTEGER;"))
        conn.execute(text("ALTER TABLE public.growth_clusters ADD COLUMN IF NOT EXISTS property_count INTEGER;"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_growth_clusters_geom ON public.growth_clusters USING GIST(geom);"))
        conn.execute(text("TRUNCATE TABLE public.growth_clusters;"))

        if clusters.empty:
            return

        conn.execute(
            text("""
                INSERT INTO public.growth_clusters (
                    cluster_id,
                    horizon_years,
                    avg_growth,
                    certainty,
                    property_count,
                    geom
                )
                VALUES (
                    :cluster_id,
                    :horizon_years,
                    :avg_growth,
                    :certainty,
                    :property_count,
                    ST_GeomFromText(:wkt, 4326)
                );
            """),
            clusters.to_dict(orient='records'),
        )
