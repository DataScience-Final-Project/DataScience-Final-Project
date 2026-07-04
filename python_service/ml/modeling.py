import os
from typing import Dict

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.cluster import DBSCAN

from ml.config import HORIZON_CONFIGS, XGB_PARAMS
from ml.clustering import DBSCAN_EPS_KM, DBSCAN_MIN_SAMPLES, EARTH_RADIUS_KM


class HorizonConfigProvider:
    def __init__(self, configs: Dict[int, dict] | None = None):
        self.configs = configs or HORIZON_CONFIGS

    def get(self, horizon: int) -> dict:
        if horizon not in self.configs:
            raise ValueError(f"Horizon {horizon} not found in config.")
        return self.configs[horizon]

    def horizons(self) -> list[int]:
        return list(self.configs.keys())

    def xgb_params(self, horizon: int) -> dict:
        config = self.get(horizon)
        params = XGB_PARAMS.copy()
        params.update(config.get("xgb_params", {}))
        return params


class ModelRegistry:
    def __init__(self, config_provider: HorizonConfigProvider | None = None):
        self.config_provider = config_provider or HorizonConfigProvider()

    def create_model(self, horizon: int) -> xgb.XGBRegressor:
        return xgb.XGBRegressor(**self.config_provider.xgb_params(horizon))

    def load_model(self, horizon: int) -> xgb.XGBRegressor:
        model = xgb.XGBRegressor(enable_categorical=True)
        model.load_model(self.model_path(horizon))
        return model

    def save_model(self, horizon: int, model: xgb.XGBRegressor) -> str:
        path = self.model_path(horizon)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        model.save_model(path)
        return path

    def model_path(self, horizon: int) -> str:
        return self.config_provider.get(horizon)["model_save_path"]


class ModelEvaluator:
    def evaluate(self, model: xgb.XGBRegressor, X: pd.DataFrame, y: pd.Series) -> dict:
        predictions = model.predict(X)
        top_decile_cutoff = np.quantile(predictions, 0.9) if len(predictions) else np.nan
        top_decile_mask = predictions >= top_decile_cutoff if len(predictions) else np.array([])
        y_sign = np.sign(y)
        pred_sign = np.sign(predictions)
        return {
            "predictions": predictions,
            "rmse": np.sqrt(mean_squared_error(y, predictions)),
            "mae": mean_absolute_error(y, predictions),
            "r2": r2_score(y, predictions),
            "spearman": pd.Series(y.to_numpy()).corr(pd.Series(predictions), method="spearman"),
            "directional_accuracy": float((y_sign == pred_sign).mean()),
            "top_decile_actual_mean": float(y.to_numpy()[top_decile_mask].mean()) if top_decile_mask.any() else np.nan,
            "top_decile_lift": (
                float(y.to_numpy()[top_decile_mask].mean() - y.mean())
                if top_decile_mask.any()
                else np.nan
            ),
        }

    def print_metrics(self, label: str, metrics: dict) -> None:
        print(f"\n--- {label} ---")
        print(f"{label} RMSE (Log Return): {metrics['rmse']:.4f}")
        print(f"{label} MAE  (Log Return): {metrics['mae']:.4f}")
        print(f"{label} R^2   (Log Return): {metrics['r2']:.4f}")
        print(f"{label} Spearman Rank:   {metrics['spearman']:.4f}")
        print(f"{label} Direction Acc.:  {metrics['directional_accuracy']:.4f}")
        print(f"{label} Top 10% Lift:    {metrics['top_decile_lift']:.4f}")
        print(f"{label} Top 10% Actual:  {metrics['top_decile_actual_mean']:.4f}")

    def print_metric_guide(self) -> None:
        print("\n--- Metric Guide (property-level real-estate growth is noisy) ---")
        print("R^2: >0.05 useful, >0.15 good, >0.30 strong for individual properties.")
        print("Spearman Rank: >0.10 weak/useful, >0.20 useful, >0.40 strong for hotspot ranking.")
        print("Direction Accuracy: >0.50 beats chance, >0.55 useful, >0.60 strong.")
        print("Top 10% Lift: should be positive; >0.02 log points useful, >0.05 strong.")
        print("MAE/RMSE: lower is better; compare against the zero-relative baseline.")

    def print_zero_baseline(self, label: str, y: pd.Series) -> None:
        predictions = np.zeros(len(y))
        print(f"\n--- {label} zero-relative baseline ---")
        print(f"{label} baseline RMSE: {np.sqrt(mean_squared_error(y, predictions)):.4f}")
        print(f"{label} baseline MAE:  {mean_absolute_error(y, predictions):.4f}")
        print(f"{label} baseline R^2:   {r2_score(y, predictions):.4f}")

    def print_cluster_metrics(self, label: str, df: pd.DataFrame, y_col: str, predictions: np.ndarray) -> None:
        required_cols = {'lat', 'lon', y_col}
        if not required_cols.issubset(df.columns):
            print(f"\n--- {label} cluster metrics skipped: missing {sorted(required_cols.difference(df.columns))} ---")
            return

        cluster_df = df[['lat', 'lon', y_col]].copy()
        cluster_df['prediction'] = predictions
        cluster_df = cluster_df.dropna(subset=['lat', 'lon', y_col, 'prediction'])
        if len(cluster_df) < DBSCAN_MIN_SAMPLES:
            print(f"\n--- {label} cluster metrics skipped: not enough rows ---")
            return

        coords_rad = np.radians(cluster_df[['lat', 'lon']].values)
        labels = DBSCAN(
            eps=DBSCAN_EPS_KM / EARTH_RADIUS_KM,
            min_samples=DBSCAN_MIN_SAMPLES,
            metric='haversine',
        ).fit_predict(coords_rad)
        cluster_df['cluster'] = labels
        cluster_df = cluster_df[cluster_df['cluster'] != -1]
        if cluster_df['cluster'].nunique() < 2:
            print(f"\n--- {label} cluster metrics skipped: fewer than 2 clusters ---")
            return

        grouped = cluster_df.groupby('cluster', observed=True).agg(
            actual=(y_col, 'mean'),
            predicted=('prediction', 'mean'),
            property_count=(y_col, 'size'),
        )
        rmse = np.sqrt(mean_squared_error(grouped['actual'], grouped['predicted']))
        mae = mean_absolute_error(grouped['actual'], grouped['predicted'])
        r2 = r2_score(grouped['actual'], grouped['predicted'])
        spearman = grouped['actual'].corr(grouped['predicted'], method='spearman')
        top_cutoff = grouped['predicted'].quantile(0.9)
        top_actual = grouped[grouped['predicted'] >= top_cutoff]['actual'].mean()
        lift = top_actual - grouped['actual'].mean()

        print(f"\n--- {label} DBSCAN cluster metrics ---")
        print("Cluster R^2: >0.20 useful, >0.40 good, >0.60 strong for hotspot polygons.")
        print("Cluster Spearman: >0.30 useful, >0.50 good, >0.70 strong for hotspot ordering.")
        print(f"{label} clusters:        {len(grouped)}")
        print(f"{label} clustered rows:  {int(grouped['property_count'].sum())}")
        print(f"{label} cluster RMSE:    {rmse:.4f}")
        print(f"{label} cluster MAE:     {mae:.4f}")
        print(f"{label} cluster R^2:     {r2:.4f}")
        print(f"{label} cluster Spearman:{spearman:.4f}")
        print(f"{label} cluster Top10 Lift: {lift:.4f}")
