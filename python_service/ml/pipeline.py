from dataclasses import dataclass
from typing import Tuple

import pandas as pd

from ml.config import COHORT_BASELINE_COL, COLS_TO_DROP, RAW_TARGET_COL, TARGET_COL
from ml.historical_features import HistoricalMomentumFeatureEngineer
from ml.local_market_features import LocalMarketFeatureEngineer
from ml.preprocessing import FeatureEngineer, TukeyOutlierRemover
from ml.splitting import OutcomeYearSplitter, TemporalSplitResult


@dataclass
class PreparedData:
    X_train: pd.DataFrame
    X_val: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_val: pd.Series
    y_test: pd.Series
    split: TemporalSplitResult


class DataPipeline:
    def __init__(self, horizon_config: dict):
        self.horizon_config = horizon_config
        self.feature_engineer = FeatureEngineer(
            use_market_trend=horizon_config.get("use_market_trend", False),
            market_trend_area_col=horizon_config.get("market_trend_area_col", "city_name"),
        )
        self.historical_feature_engineer = HistoricalMomentumFeatureEngineer(
            recent_window_years=horizon_config.get("recent_window_years")
        )
        self.local_market_feature_engineer = LocalMarketFeatureEngineer()
        self.splitter = OutcomeYearSplitter(
            target_train_ratio=horizon_config.get("target_train_ratio", 0.8),
            validation_ratio=horizon_config.get("validation_ratio", 0.15),
        )

    def prepare(self, df: pd.DataFrame) -> PreparedData:
        print("Preparing data pipeline (temporal train/validation/test split)...")
        df = self._remove_invalid_prices(df)
        df = self.feature_engineer.transform(df)
        df = self.historical_feature_engineer.transform(df)
        df = self.local_market_feature_engineer.transform(df)
        df = self._add_relative_target(df)

        split = self.splitter.split(df)
        train_df = self._remove_train_outliers(split.train_df)
        val_df = self._keep_valid_prices(split.val_df)
        test_df = self._keep_valid_prices(split.test_df)

        X_train, y_train = self._split_xy(train_df)
        X_val, y_val = self._split_xy(val_df)
        X_test, y_test = self._split_xy(test_df)

        print(f"Temporal split year: {split.relevant_year}")
        print(f"Train set: {X_train.shape[0]} rows")
        print(f"Validation set: {X_val.shape[0]} rows")
        print(f"Test set: {X_test.shape[0]} rows")

        return PreparedData(
            X_train=X_train,
            X_val=X_val,
            X_test=X_test,
            y_train=y_train,
            y_val=y_val,
            y_test=y_test,
            split=split,
        )

    def _remove_invalid_prices(self, df: pd.DataFrame) -> pd.DataFrame:
        initial_len = len(df)
        df = self._keep_valid_prices(df)
        removed = initial_len - len(df)
        if removed:
            print(f"Removed {removed} rows with non-positive prices.")
        return df

    def _keep_valid_prices(self, df: pd.DataFrame) -> pd.DataFrame:
        return df[(df['price_t0'] > 0) & (df['price_t1'] > 0)].copy()

    def _add_relative_target(self, df: pd.DataFrame) -> pd.DataFrame:
        required_cols = {'horizon_years', 'snapshot_year', RAW_TARGET_COL}
        missing_cols = required_cols.difference(df.columns)
        if missing_cols:
            raise ValueError(f"Cannot create relative target: missing columns {sorted(missing_cols)}.")

        df = df.copy()
        df[COHORT_BASELINE_COL] = (
            df.groupby(['horizon_years', 'snapshot_year'], observed=True)[RAW_TARGET_COL]
            .transform('mean')
        )
        df[TARGET_COL] = df[RAW_TARGET_COL] - df[COHORT_BASELINE_COL]
        return df

    def _remove_train_outliers(self, train_df: pd.DataFrame) -> pd.DataFrame:
        train_df = train_df.copy()
        train_df['_price_ratio'] = train_df['price_t1'] / train_df['price_t0']

        remover = TukeyOutlierRemover(columns=['price_t0', 'price_t1', '_price_ratio'])
        filtered_train = remover.fit(train_df).transform(train_df)
        filtered_train = filtered_train.drop(columns=['_price_ratio'])

        removed = len(train_df) - len(filtered_train)
        print(f"Removed {removed} train outliers using Tukey's IQR method.")
        return filtered_train

    def _split_xy(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        cols_to_drop_safe = [c for c in COLS_TO_DROP if c in df.columns]
        X = df.drop(columns=cols_to_drop_safe)
        y = df[TARGET_COL]
        return X.copy(), y.copy()


def prepare_data(
    df: pd.DataFrame,
    split_year: int | None = None,
    horizon_config: dict | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    config = horizon_config or {}
    prepared = DataPipeline(config).prepare(df)
    return prepared.X_train, prepared.X_test, prepared.y_train, prepared.y_test


def prepare_train_val_test(df: pd.DataFrame, horizon_config: dict) -> PreparedData:
    return DataPipeline(horizon_config).prepare(df)
