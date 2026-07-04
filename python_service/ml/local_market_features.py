import numpy as np
import pandas as pd

from ml.historical_features import NEIGHBORHOOD_CELL_COL

LOCAL_CELL_COUNT_COL = 'local_cell_snapshot_count'
LOCAL_CELL_LOG_PRICE_MEAN_COL = 'local_cell_log_price_mean'
LOCAL_CELL_LOG_PRICE_STD_COL = 'local_cell_log_price_std'
LOCAL_CELL_PRICE_PER_ROOM_MEAN_COL = 'local_cell_price_per_room_mean'
LOCAL_CELL_PRICE_LEVEL_RATIO_COL = 'local_cell_price_level_ratio'
LOCAL_CELL_PRICE_PER_ROOM_RATIO_COL = 'local_cell_price_per_room_ratio'
LOCAL_CELL_PRICE_PERCENTILE_COL = 'local_cell_price_percentile'
LOCAL_CITY_COUNT_COL = 'local_city_snapshot_count'
LOCAL_CITY_LOG_PRICE_MEAN_COL = 'local_city_log_price_mean'
LOCAL_CITY_LOG_PRICE_STD_COL = 'local_city_log_price_std'
LOCAL_CITY_PRICE_PER_ROOM_MEAN_COL = 'local_city_price_per_room_mean'
LOCAL_CITY_PRICE_LEVEL_RATIO_COL = 'local_city_price_level_ratio'
LOCAL_CITY_PRICE_PER_ROOM_RATIO_COL = 'local_city_price_per_room_ratio'
LOCAL_CITY_PRICE_PERCENTILE_COL = 'local_city_price_percentile'
LOCAL_SIMILAR_COUNT_COL = 'local_similar_snapshot_count'
LOCAL_SIMILAR_LOG_PRICE_MEAN_COL = 'local_similar_log_price_mean'
LOCAL_SIMILAR_PRICE_LEVEL_RATIO_COL = 'local_similar_price_level_ratio'


class LocalMarketFeatureEngineer:
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        required_cols = {'snapshot_year', 'horizon_years', 'price_t0'}
        missing_cols = required_cols.difference(df.columns)
        if missing_cols:
            raise ValueError(f"Cannot add local market features: missing columns {sorted(missing_cols)}.")

        result = df.copy()
        result['_orig_index'] = result.index
        result['price_t0'] = pd.to_numeric(result['price_t0'], errors='coerce')
        result['_price_per_room'] = self._price_per_room(result)

        if NEIGHBORHOOD_CELL_COL in result.columns:
            result = self._merge_group_features(
                result,
                ['snapshot_year', 'horizon_years', NEIGHBORHOOD_CELL_COL],
                LOCAL_CELL_COUNT_COL,
                LOCAL_CELL_LOG_PRICE_MEAN_COL,
                LOCAL_CELL_LOG_PRICE_STD_COL,
                LOCAL_CELL_PRICE_PER_ROOM_MEAN_COL,
                LOCAL_CELL_PRICE_LEVEL_RATIO_COL,
                LOCAL_CELL_PRICE_PER_ROOM_RATIO_COL,
                LOCAL_CELL_PRICE_PERCENTILE_COL,
            )

        if 'city_name' in result.columns:
            result = self._merge_group_features(
                result,
                ['snapshot_year', 'horizon_years', 'city_name'],
                LOCAL_CITY_COUNT_COL,
                LOCAL_CITY_LOG_PRICE_MEAN_COL,
                LOCAL_CITY_LOG_PRICE_STD_COL,
                LOCAL_CITY_PRICE_PER_ROOM_MEAN_COL,
                LOCAL_CITY_PRICE_LEVEL_RATIO_COL,
                LOCAL_CITY_PRICE_PER_ROOM_RATIO_COL,
                LOCAL_CITY_PRICE_PERCENTILE_COL,
            )

        if {'city_name', 'num_rooms', 'property_type'}.issubset(result.columns):
            result = self._merge_similar_features(result)

        fallback_mean = np.log1p(result['price_t0'].clip(lower=0)).mean()
        for col in [LOCAL_CELL_LOG_PRICE_MEAN_COL, LOCAL_CITY_LOG_PRICE_MEAN_COL, LOCAL_SIMILAR_LOG_PRICE_MEAN_COL]:
            if col in result.columns:
                result[col] = result[col].fillna(fallback_mean)

        for col in result.columns:
            if col.startswith('local_'):
                result[col] = pd.to_numeric(result[col], errors='coerce').fillna(0)

        for col in ['city_name', 'location_accuracy', NEIGHBORHOOD_CELL_COL]:
            if col in result.columns:
                result[col] = result[col].astype(str).fillna('unknown').astype('category')

        result = result.set_index('_orig_index')
        result.index.name = None
        return result.drop(columns=['_price_per_room'], errors='ignore')

    def _price_per_room(self, df: pd.DataFrame) -> pd.Series:
        if 'num_rooms' not in df.columns:
            return pd.Series(np.nan, index=df.index)
        rooms = pd.to_numeric(df['num_rooms'], errors='coerce')
        return df['price_t0'] / rooms.where(rooms > 0)

    def _merge_group_features(
        self,
        df: pd.DataFrame,
        group_cols: list[str],
        count_col: str,
        log_price_mean_col: str,
        log_price_std_col: str,
        price_per_room_mean_col: str,
        price_ratio_col: str,
        price_per_room_ratio_col: str,
        percentile_col: str,
    ) -> pd.DataFrame:
        result = df.copy()
        for col in group_cols:
            if result[col].dtype.name == 'category' or result[col].dtype == object:
                result[col] = result[col].astype(str).fillna('unknown')

        group = result.groupby(group_cols, observed=True)
        log_price = np.log1p(result['price_t0'].clip(lower=0))
        stats = group.agg(
            _local_count=('price_t0', 'count'),
            _local_price_mean=('price_t0', 'mean'),
            _local_log_price_mean=('price_t0', lambda s: np.log1p(s.clip(lower=0)).mean()),
            _local_log_price_std=('price_t0', lambda s: np.log1p(s.clip(lower=0)).std()),
            _local_price_per_room_mean=('_price_per_room', 'mean'),
        ).reset_index()

        percentile = group['price_t0'].rank(pct=True).fillna(0.5)
        result = result.merge(stats, on=group_cols, how='left')
        result[count_col] = np.log1p(result['_local_count'].fillna(0))
        result[log_price_mean_col] = result['_local_log_price_mean']
        result[log_price_std_col] = result['_local_log_price_std'].fillna(0)
        result[price_per_room_mean_col] = result['_local_price_per_room_mean'].fillna(0)
        result[price_ratio_col] = np.log1p(result['price_t0'].clip(lower=0)) - result['_local_log_price_mean']
        result[price_per_room_ratio_col] = np.log1p(result['_price_per_room'].clip(lower=0)) - np.log1p(result['_local_price_per_room_mean'].clip(lower=0))
        result[percentile_col] = result['_orig_index'].map(percentile).fillna(0.5)

        return result.drop(columns=[
            '_local_count',
            '_local_price_mean',
            '_local_log_price_mean',
            '_local_log_price_std',
            '_local_price_per_room_mean',
        ])

    def _merge_similar_features(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        result['_rooms_bucket'] = pd.to_numeric(result['num_rooms'], errors='coerce').round().clip(lower=1, upper=8)
        group_cols = ['snapshot_year', 'horizon_years', 'city_name', '_rooms_bucket', 'property_type']
        for col in ['city_name']:
            result[col] = result[col].astype(str).fillna('unknown')

        stats = (
            result.groupby(group_cols, observed=True)
            .agg(
                _similar_count=('price_t0', 'count'),
                _similar_log_price_mean=('price_t0', lambda s: np.log1p(s.clip(lower=0)).mean()),
            )
            .reset_index()
        )
        result = result.merge(stats, on=group_cols, how='left')
        result[LOCAL_SIMILAR_COUNT_COL] = np.log1p(result['_similar_count'].fillna(0))
        result[LOCAL_SIMILAR_LOG_PRICE_MEAN_COL] = result['_similar_log_price_mean']
        result[LOCAL_SIMILAR_PRICE_LEVEL_RATIO_COL] = (
            np.log1p(result['price_t0'].clip(lower=0)) - result['_similar_log_price_mean']
        )
        return result.drop(columns=['_rooms_bucket', '_similar_count', '_similar_log_price_mean'])
