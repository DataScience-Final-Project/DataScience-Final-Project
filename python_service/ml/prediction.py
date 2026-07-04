from typing import Iterable

import numpy as np
import pandas as pd

from ml.config import PREDICTION_TEXT_COLS
from ml.modeling import HorizonConfigProvider, ModelRegistry
from ml.preprocessing import FeatureEngineer


class PredictionService:
    def __init__(
        self,
        horizons: Iterable[int] = (5, 10),
        market_baselines: dict[int, float] | None = None,
        config_provider: HorizonConfigProvider | None = None,
        model_registry: ModelRegistry | None = None,
    ):
        self.horizons = list(horizons)
        self.market_baselines = market_baselines or {}
        self.config_provider = config_provider or HorizonConfigProvider()
        self.model_registry = model_registry or ModelRegistry(self.config_provider)
        self.models = {h: self.model_registry.load_model(h) for h in self.horizons}

    def predict_relative_log_growth(self, df: pd.DataFrame) -> dict[int, np.ndarray]:
        predictions = {}
        for horizon, model in self.models.items():
            config = self.config_provider.get(horizon)
            feature_engineer = FeatureEngineer(
                use_market_trend=config.get("use_market_trend", False),
                market_trend_area_col=config.get("market_trend_area_col", "city_name"),
            )
            expected_cols = model.get_booster().feature_names
            X = feature_engineer.prepare_prediction_features(
                df,
                expected_cols=expected_cols,
                passthrough_cols=[*PREDICTION_TEXT_COLS, 'lat', 'lon'],
            )
            predictions[horizon] = model.predict(X)

        return predictions

    def predict_log_growth(self, df: pd.DataFrame) -> dict[int, np.ndarray]:
        return {
            horizon: preds + self.market_baselines.get(horizon, 0.0)
            for horizon, preds in self.predict_relative_log_growth(df).items()
        }

    def predict_percent_growth(self, df: pd.DataFrame) -> dict[int, np.ndarray]:
        return {
            horizon: np.expm1(preds) * 100
            for horizon, preds in self.predict_log_growth(df).items()
        }
