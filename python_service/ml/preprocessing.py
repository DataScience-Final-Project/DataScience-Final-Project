from dataclasses import dataclass
from typing import Dict, Iterable, Optional

import numpy as np
import pandas as pd

from ml.config import CATEGORICAL_COLS, NUMERIC_COLS, POI_TYPES, RAW_TARGET_COL


@dataclass
class TukeyBounds:
    lower: float
    upper: float


class TukeyOutlierRemover:
    def __init__(self, columns: Iterable[str], k: float = 1.5):
        self.columns = list(columns)
        self.k = k
        self.bounds_: Dict[str, TukeyBounds] = {}

    def fit(self, df: pd.DataFrame) -> "TukeyOutlierRemover":
        self.bounds_.clear()
        for col in self.columns:
            if col not in df.columns:
                continue

            series = df[col].dropna()
            if series.empty:
                continue

            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            self.bounds_[col] = TukeyBounds(
                lower=q1 - self.k * iqr,
                upper=q3 + self.k * iqr,
            )

        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        mask = pd.Series(True, index=df.index)
        for col, bounds in self.bounds_.items():
            mask &= df[col].between(bounds.lower, bounds.upper, inclusive='both')
        return df[mask].copy()


class FeatureEngineer:
    def __init__(
        self,
        poi_types: Optional[Iterable[str]] = None,
        categorical_cols: Optional[Iterable[str]] = None,
        numeric_cols: Optional[Iterable[str]] = None,
        use_market_trend: bool = False,
        market_trend_area_col: str = "city_name",
    ):
        self.poi_types = list(poi_types or POI_TYPES)
        self.categorical_cols = list(categorical_cols or CATEGORICAL_COLS)
        self.numeric_cols = list(numeric_cols or NUMERIC_COLS)
        self.use_market_trend = use_market_trend
        self.market_trend_area_col = market_trend_area_col

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = df.dropna(axis=1, how='all')
        df = self._add_poi_deltas(df)
        df = self._add_log_price(df)
        df = self._add_market_trend(df)
        df = self._cast_known_columns(df)
        df = self._drop_unhandled_text_columns(df)
        return df

    def prepare_prediction_features(
        self,
        df: pd.DataFrame,
        expected_cols: Iterable[str],
        passthrough_cols: Optional[Iterable[str]] = None,
    ) -> pd.DataFrame:
        passthrough = set(passthrough_cols or [])
        df = self._clean_raw_prediction_values(df, passthrough)
        df = self.transform(df)

        expected_cols = list(expected_cols)
        X = df[[c for c in expected_cols if c in df.columns]].copy()

        if 'num_rooms' in X.columns:
            X['num_rooms'] = X['num_rooms'].fillna(3)

        if 'location_accuracy' not in X.columns:
            X['location_accuracy'] = 1
        X['location_accuracy'] = X['location_accuracy'].fillna(1).astype('category')

        if 'city_name' in X.columns:
            mode = X['city_name'].mode(dropna=True)
            fill_value = mode.iloc[0] if not mode.empty else 'unknown'
            X['city_name'] = X['city_name'].fillna(fill_value).astype('category')

        for col in expected_cols:
            if col not in X.columns:
                X[col] = np.nan

        return X[expected_cols]

    def _clean_raw_prediction_values(self, df: pd.DataFrame, passthrough_cols: set[str]) -> pd.DataFrame:
        df = df.copy()
        df = df.replace(r'^\s*$', np.nan, regex=True)
        df = df.replace(['NULL', 'null', 'None'], np.nan)

        for col in df.columns:
            if col not in passthrough_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    def _add_poi_deltas(self, df: pd.DataFrame) -> pd.DataFrame:
        for poi in self.poi_types:
            now_col = f'{poi}_score_now'
            future_col = f'{poi}_score_future'
            if now_col in df.columns and future_col in df.columns:
                df[f'{poi}_score_delta'] = df[future_col] - df[now_col]
        return df

    def _add_log_price(self, df: pd.DataFrame) -> pd.DataFrame:
        if 'price_t0' in df.columns:
            df['log_price_t0'] = np.log(df['price_t0'])
        return df

    def _add_market_trend(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self.use_market_trend:
            return df

        required_cols = {self.market_trend_area_col, 'snapshot_year', 'horizon_years', RAW_TARGET_COL}
        if not required_cols.issubset(df.columns):
            df['market_trend_prior_growth'] = np.nan
            return df

        area_col = self.market_trend_area_col
        trend_df = df[[area_col, 'snapshot_year', 'horizon_years', RAW_TARGET_COL]].copy()
        trend_df['_outcome_year'] = trend_df['snapshot_year'] + trend_df['horizon_years']

        yearly = (
            trend_df
            .groupby([area_col, '_outcome_year'], observed=True)[RAW_TARGET_COL]
            .agg(['sum', 'count'])
            .reset_index()
            .sort_values([area_col, '_outcome_year'])
        )
        yearly['_prior_sum'] = yearly.groupby(area_col, observed=True)['sum'].cumsum() - yearly['sum']
        yearly['_prior_count'] = yearly.groupby(area_col, observed=True)['count'].cumsum() - yearly['count']
        yearly['market_trend_prior_growth'] = yearly['_prior_sum'] / yearly['_prior_count']

        global_yearly = (
            trend_df
            .groupby('_outcome_year')[RAW_TARGET_COL]
            .agg(['sum', 'count'])
            .reset_index()
            .sort_values('_outcome_year')
        )
        global_yearly['_prior_sum'] = global_yearly['sum'].cumsum() - global_yearly['sum']
        global_yearly['_prior_count'] = global_yearly['count'].cumsum() - global_yearly['count']
        global_yearly['_global_market_trend'] = global_yearly['_prior_sum'] / global_yearly['_prior_count']

        trend_df = trend_df.merge(
            yearly[[area_col, '_outcome_year', 'market_trend_prior_growth']],
            on=[area_col, '_outcome_year'],
            how='left',
        )
        trend_df = trend_df.merge(
            global_yearly[['_outcome_year', '_global_market_trend']],
            on='_outcome_year',
            how='left',
        )
        trend_df['market_trend_prior_growth'] = trend_df['market_trend_prior_growth'].fillna(
            trend_df['_global_market_trend']
        )

        df['market_trend_prior_growth'] = trend_df['market_trend_prior_growth'].values
        return df

    def _cast_known_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in self.categorical_cols:
            if col in df.columns:
                df[col] = df[col].astype('category')

        for col in self.numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    def _drop_unhandled_text_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        object_cols = df.select_dtypes(include=['object']).columns
        if len(object_cols) > 0:
            print(f"Dropping unhandled text columns to prevent crashes: {list(object_cols)}")
            df = df.drop(columns=object_cols)
        return df
