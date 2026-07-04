import numpy as np
import pandas as pd
import h3

from ml.config import RAW_TARGET_COL

H3_RESOLUTION = 8
RECENT_WINDOW_YEARS = 5
HISTORICAL_GLOBAL_GROWTH_COL = 'hist_global_growth_mean'
HISTORICAL_GLOBAL_COUNT_COL = 'hist_global_growth_count'
HISTORICAL_CITY_GROWTH_COL = 'hist_city_growth_mean'
HISTORICAL_CITY_COUNT_COL = 'hist_city_growth_count'
HISTORICAL_NEIGHBORHOOD_GROWTH_COL = 'hist_neighborhood_growth_mean'
HISTORICAL_NEIGHBORHOOD_COUNT_COL = 'hist_neighborhood_growth_count'
HISTORICAL_SIMILAR_GROWTH_COL = 'hist_similar_growth_mean'
HISTORICAL_SIMILAR_COUNT_COL = 'hist_similar_growth_count'
RECENT_GLOBAL_GROWTH_COL = 'recent_global_growth_mean'
RECENT_GLOBAL_COUNT_COL = 'recent_global_growth_count'
RECENT_CITY_GROWTH_COL = 'recent_city_growth_mean'
RECENT_CITY_COUNT_COL = 'recent_city_growth_count'
RECENT_NEIGHBORHOOD_GROWTH_COL = 'recent_neighborhood_growth_mean'
RECENT_NEIGHBORHOOD_COUNT_COL = 'recent_neighborhood_growth_count'
RECENT_SIMILAR_GROWTH_COL = 'recent_similar_growth_mean'
RECENT_SIMILAR_COUNT_COL = 'recent_similar_growth_count'
NEIGHBORHOOD_CELL_COL = 'neighborhood_cell'
HISTORICAL_FEATURE_COLS = [
    HISTORICAL_GLOBAL_GROWTH_COL,
    HISTORICAL_GLOBAL_COUNT_COL,
    HISTORICAL_CITY_GROWTH_COL,
    HISTORICAL_CITY_COUNT_COL,
    HISTORICAL_NEIGHBORHOOD_GROWTH_COL,
    HISTORICAL_NEIGHBORHOOD_COUNT_COL,
    HISTORICAL_SIMILAR_GROWTH_COL,
    HISTORICAL_SIMILAR_COUNT_COL,
    RECENT_GLOBAL_GROWTH_COL,
    RECENT_GLOBAL_COUNT_COL,
    RECENT_CITY_GROWTH_COL,
    RECENT_CITY_COUNT_COL,
    RECENT_NEIGHBORHOOD_GROWTH_COL,
    RECENT_NEIGHBORHOOD_COUNT_COL,
    RECENT_SIMILAR_GROWTH_COL,
    RECENT_SIMILAR_COUNT_COL,
]


class HistoricalMomentumFeatureEngineer:
    def __init__(
        self,
        h3_resolution: int = H3_RESOLUTION,
        recent_window_years: int | None = RECENT_WINDOW_YEARS,
    ):
        self.h3_resolution = h3_resolution
        self.recent_window_years = recent_window_years

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        required_cols = {'snapshot_year', 'horizon_years', RAW_TARGET_COL}
        missing_cols = required_cols.difference(df.columns)
        if missing_cols:
            raise ValueError(f"Cannot add historical momentum features: missing columns {sorted(missing_cols)}.")

        df = df.copy()
        df[NEIGHBORHOOD_CELL_COL] = self._h3_cells(df)
        df[NEIGHBORHOOD_CELL_COL] = df[NEIGHBORHOOD_CELL_COL].astype('category')
        df['_orig_index'] = df.index
        df['_row_id'] = np.arange(len(df))
        df['_outcome_year'] = df['snapshot_year'] + df['horizon_years']

        result = df
        result = self._merge_global_history(result)
        result = self._merge_group_history(result, ['city_name'], HISTORICAL_CITY_GROWTH_COL, HISTORICAL_CITY_COUNT_COL)
        result = self._merge_group_history(
            result,
            [NEIGHBORHOOD_CELL_COL],
            HISTORICAL_NEIGHBORHOOD_GROWTH_COL,
            HISTORICAL_NEIGHBORHOOD_COUNT_COL,
        )
        result = self._merge_group_history(
            result,
            ['city_name', 'num_rooms', 'property_type'],
            HISTORICAL_SIMILAR_GROWTH_COL,
            HISTORICAL_SIMILAR_COUNT_COL,
        )

        recent_pairs = []
        if self.recent_window_years is not None:
            result = self._merge_global_recent_history(result)
            result = self._merge_group_recent_history(result, ['city_name'], RECENT_CITY_GROWTH_COL, RECENT_CITY_COUNT_COL)
            result = self._merge_group_recent_history(
                result,
                [NEIGHBORHOOD_CELL_COL],
                RECENT_NEIGHBORHOOD_GROWTH_COL,
                RECENT_NEIGHBORHOOD_COUNT_COL,
            )
            result = self._merge_group_recent_history(
                result,
                ['city_name', 'num_rooms', 'property_type'],
                RECENT_SIMILAR_GROWTH_COL,
                RECENT_SIMILAR_COUNT_COL,
            )
            recent_pairs = [
                (RECENT_CITY_GROWTH_COL, RECENT_CITY_COUNT_COL),
                (RECENT_NEIGHBORHOOD_GROWTH_COL, RECENT_NEIGHBORHOOD_COUNT_COL),
                (RECENT_SIMILAR_GROWTH_COL, RECENT_SIMILAR_COUNT_COL),
            ]

        for mean_col, count_col in [
            (HISTORICAL_CITY_GROWTH_COL, HISTORICAL_CITY_COUNT_COL),
            (HISTORICAL_NEIGHBORHOOD_GROWTH_COL, HISTORICAL_NEIGHBORHOOD_COUNT_COL),
            (HISTORICAL_SIMILAR_GROWTH_COL, HISTORICAL_SIMILAR_COUNT_COL),
            *recent_pairs,
        ]:
            fallback_col = RECENT_GLOBAL_GROWTH_COL if mean_col.startswith('recent_') else HISTORICAL_GLOBAL_GROWTH_COL
            result[mean_col] = result[mean_col].fillna(result[fallback_col])
            result[count_col] = result[count_col].fillna(0)

        for count_col in [
            HISTORICAL_GLOBAL_COUNT_COL,
            HISTORICAL_CITY_COUNT_COL,
            HISTORICAL_NEIGHBORHOOD_COUNT_COL,
            HISTORICAL_SIMILAR_COUNT_COL,
        ]:
            result[count_col] = np.log1p(result[count_col].fillna(0))

        if self.recent_window_years is not None:
            for count_col in [
                RECENT_GLOBAL_COUNT_COL,
                RECENT_CITY_COUNT_COL,
                RECENT_NEIGHBORHOOD_COUNT_COL,
                RECENT_SIMILAR_COUNT_COL,
            ]:
                result[count_col] = np.log1p(result[count_col].fillna(0))

        for col in ['num_rooms', 'property_type', 'lat', 'lon']:
            if col in result.columns:
                result[col] = pd.to_numeric(result[col], errors='coerce')

        for col in ['city_name', 'location_accuracy', NEIGHBORHOOD_CELL_COL]:
            if col in result.columns:
                result[col] = result[col].astype(str).fillna('unknown').astype('category')

        result = result.sort_values('_row_id').set_index('_orig_index')
        result.index.name = None
        return result.drop(columns=['_row_id', '_outcome_year'])

    def _h3_cells(self, df: pd.DataFrame) -> pd.Series:
        if 'lat' not in df.columns or 'lon' not in df.columns:
            return pd.Series('unknown', index=df.index)

        cells = []
        for lat, lon in zip(df['lat'], df['lon']):
            if pd.isna(lat) or pd.isna(lon):
                cells.append('unknown')
            else:
                cells.append(h3.latlng_to_cell(float(lat), float(lon), self.h3_resolution))
        return pd.Series(cells, index=df.index)

    def _merge_global_history(self, df: pd.DataFrame) -> pd.DataFrame:
        yearly = (
            df.dropna(subset=[RAW_TARGET_COL])
            .groupby('_outcome_year', observed=True)[RAW_TARGET_COL]
            .agg(['sum', 'count'])
            .reset_index()
            .sort_values('_outcome_year')
        )
        yearly['_cum_sum'] = yearly['sum'].cumsum()
        yearly['_cum_count'] = yearly['count'].cumsum()
        yearly[HISTORICAL_GLOBAL_GROWTH_COL] = yearly['_cum_sum'] / yearly['_cum_count']
        yearly[HISTORICAL_GLOBAL_COUNT_COL] = yearly['_cum_count']

        merged = pd.merge_asof(
            df.sort_values('snapshot_year'),
            yearly[['_outcome_year', HISTORICAL_GLOBAL_GROWTH_COL, HISTORICAL_GLOBAL_COUNT_COL]],
            left_on='snapshot_year',
            right_on='_outcome_year',
            direction='backward',
        ).drop(columns=['_outcome_year_y']).rename(columns={'_outcome_year_x': '_outcome_year'})
        merged[HISTORICAL_GLOBAL_GROWTH_COL] = merged[HISTORICAL_GLOBAL_GROWTH_COL].fillna(0.0)
        merged[HISTORICAL_GLOBAL_COUNT_COL] = merged[HISTORICAL_GLOBAL_COUNT_COL].fillna(0)
        return merged.sort_values('_row_id')

    def _merge_global_recent_history(self, df: pd.DataFrame) -> pd.DataFrame:
        yearly = self._yearly_cumulative(df, [])
        upper = self._asof_cumulative(df, yearly, 'snapshot_year')
        lower = df[['_row_id', 'snapshot_year']].copy()
        lower['_lower_year'] = lower['snapshot_year'] - self.recent_window_years
        lower = self._asof_cumulative(lower, yearly, '_lower_year')

        lower_sum = lower.set_index('_row_id')['_cum_sum'].reindex(upper['_row_id']).fillna(0).to_numpy()
        lower_count = lower.set_index('_row_id')['_cum_count'].reindex(upper['_row_id']).fillna(0).to_numpy()
        recent_sum = upper['_cum_sum'].fillna(0).to_numpy() - lower_sum
        recent_count = upper['_cum_count'].fillna(0).to_numpy() - lower_count

        result = df.copy()
        result[RECENT_GLOBAL_COUNT_COL] = np.maximum(recent_count, 0)
        result[RECENT_GLOBAL_GROWTH_COL] = np.divide(
            recent_sum,
            result[RECENT_GLOBAL_COUNT_COL],
            out=np.zeros(len(result), dtype=float),
            where=result[RECENT_GLOBAL_COUNT_COL].to_numpy() > 0,
        )
        return result

    def _merge_group_history(
        self,
        df: pd.DataFrame,
        group_cols: list[str],
        mean_col: str,
        count_col: str,
    ) -> pd.DataFrame:
        if not all(col in df.columns for col in group_cols):
            df[mean_col] = np.nan
            df[count_col] = 0
            return df

        source = df.dropna(subset=[RAW_TARGET_COL]).copy()
        for col in group_cols:
            source[col] = source[col].astype(str).fillna('unknown')
            df[col] = df[col].astype(str).fillna('unknown')

        yearly = (
            source.groupby([*group_cols, '_outcome_year'], observed=True)[RAW_TARGET_COL]
            .agg(['sum', 'count'])
            .reset_index()
            .sort_values([*group_cols, '_outcome_year'])
        )
        yearly['_cum_sum'] = yearly.groupby(group_cols, observed=True)['sum'].cumsum()
        yearly['_cum_count'] = yearly.groupby(group_cols, observed=True)['count'].cumsum()
        yearly[mean_col] = yearly['_cum_sum'] / yearly['_cum_count']
        yearly[count_col] = yearly['_cum_count']

        merged_parts = []
        history_cols = [*group_cols, '_outcome_year', mean_col, count_col]
        for _, target_group in df.groupby(group_cols, observed=True, sort=False):
            key_values = target_group.iloc[0][group_cols].to_dict()
            history = yearly
            for col, value in key_values.items():
                history = history[history[col] == value]

            if history.empty:
                target_group = target_group.copy()
                target_group[mean_col] = np.nan
                target_group[count_col] = 0
                merged_parts.append(target_group)
                continue

            merged = pd.merge_asof(
                target_group.sort_values('snapshot_year'),
                history[history_cols].sort_values('_outcome_year'),
                left_on='snapshot_year',
                right_on='_outcome_year',
                direction='backward',
                suffixes=('', '_history'),
            )
            drop_cols = [col for col in merged.columns if col.endswith('_history') or col == '_outcome_year_history']
            merged = merged.drop(columns=drop_cols, errors='ignore')
            if '_outcome_year_y' in merged.columns:
                merged = merged.drop(columns=['_outcome_year_y']).rename(columns={'_outcome_year_x': '_outcome_year'})
            merged_parts.append(merged)

        return pd.concat(merged_parts, ignore_index=True).sort_values('_row_id')

    def _merge_group_recent_history(
        self,
        df: pd.DataFrame,
        group_cols: list[str],
        mean_col: str,
        count_col: str,
    ) -> pd.DataFrame:
        if not all(col in df.columns for col in group_cols):
            df[mean_col] = np.nan
            df[count_col] = 0
            return df

        source = df.dropna(subset=[RAW_TARGET_COL]).copy()
        target = df.copy()
        for col in group_cols:
            source[col] = source[col].astype(str).fillna('unknown')
            target[col] = target[col].astype(str).fillna('unknown')

        yearly = self._yearly_cumulative(source, group_cols)
        merged_parts = []
        history_cols = [*group_cols, '_outcome_year', '_cum_sum', '_cum_count']

        for _, target_group in target.groupby(group_cols, observed=True, sort=False):
            key_values = target_group.iloc[0][group_cols].to_dict()
            history = yearly
            for col, value in key_values.items():
                history = history[history[col] == value]

            target_group = target_group.copy()
            if history.empty:
                target_group[mean_col] = np.nan
                target_group[count_col] = 0
                merged_parts.append(target_group)
                continue

            upper = self._asof_cumulative(target_group, history[history_cols], 'snapshot_year')
            lower_target = target_group[['_row_id', 'snapshot_year']].copy()
            lower_target['_lower_year'] = lower_target['snapshot_year'] - self.recent_window_years
            lower = self._asof_cumulative(lower_target, history[history_cols], '_lower_year')

            lower_sum = lower.set_index('_row_id')['_cum_sum'].reindex(upper['_row_id']).fillna(0).to_numpy()
            lower_count = lower.set_index('_row_id')['_cum_count'].reindex(upper['_row_id']).fillna(0).to_numpy()
            recent_sum = upper['_cum_sum'].fillna(0).to_numpy() - lower_sum
            recent_count = upper['_cum_count'].fillna(0).to_numpy() - lower_count

            target_group[count_col] = np.maximum(recent_count, 0)
            target_group[mean_col] = np.divide(
                recent_sum,
                target_group[count_col],
                out=np.full(len(target_group), np.nan, dtype=float),
                where=target_group[count_col].to_numpy() > 0,
            )
            merged_parts.append(target_group)

        return pd.concat(merged_parts, ignore_index=True).sort_values('_row_id')

    def _yearly_cumulative(self, df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
        groupby_cols = [*group_cols, '_outcome_year'] if group_cols else ['_outcome_year']
        yearly = (
            df.dropna(subset=[RAW_TARGET_COL])
            .groupby(groupby_cols, observed=True)[RAW_TARGET_COL]
            .agg(['sum', 'count'])
            .reset_index()
            .sort_values(groupby_cols)
        )
        if group_cols:
            yearly['_cum_sum'] = yearly.groupby(group_cols, observed=True)['sum'].cumsum()
            yearly['_cum_count'] = yearly.groupby(group_cols, observed=True)['count'].cumsum()
        else:
            yearly['_cum_sum'] = yearly['sum'].cumsum()
            yearly['_cum_count'] = yearly['count'].cumsum()
        return yearly

    def _asof_cumulative(self, target: pd.DataFrame, history: pd.DataFrame, left_on: str) -> pd.DataFrame:
        return pd.merge_asof(
            target.sort_values(left_on),
            history[['_outcome_year', '_cum_sum', '_cum_count']].sort_values('_outcome_year'),
            left_on=left_on,
            right_on='_outcome_year',
            direction='backward',
        )
