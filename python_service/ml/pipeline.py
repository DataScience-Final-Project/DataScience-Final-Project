import numpy as np
import pandas as pd
from typing import Tuple
from ml.config import TARGET_COL, COLS_TO_DROP

def _tukey_bounds(s: pd.Series, k: float = 1.5) -> Tuple[float, float]:
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    return q1 - k * iqr, q3 + k * iqr

def _tukey_mask_by_group(values: pd.Series, group: pd.Series, k: float = 1, min_group_size: int = 30) -> pd.Series:
    """Tukey fences computed per group (e.g. per city), falling back to the
    global fences for groups too small to estimate quartiles reliably."""
    global_lower, global_upper = _tukey_bounds(values, k)

    q1 = values.groupby(group).transform(lambda s: s.quantile(0.25))
    q3 = values.groupby(group).transform(lambda s: s.quantile(0.75))
    lower = q1 - k * (q3 - q1)
    upper = q3 + k * (q3 - q1)

    too_small = group.map(group.value_counts()) < min_group_size
    lower = lower.where(~too_small, global_lower).fillna(global_lower)
    upper = upper.where(~too_small, global_upper).fillna(global_upper)

    return values.between(lower, upper)

H3_MOMENTUM_RESOLUTION = 7
H3_MOMENTUM_MIN_GROUP_SIZE = 5

def _trailing_momentum(df: pd.DataFrame, group_col: str, lookback_years: int) -> pd.Series:
    """Trailing avg YoY change in median log_price_t0 within each group, using
    only years strictly before each row's own snapshot_year. Backward-looking
    by construction, so it's leak-free in both the train/test split and CV
    folds regardless of a group's split assignment."""
    group_year = (
        df.groupby([group_col, 'snapshot_year'])['log_price_t0']
        .median()
        .rename('median_log_price')
        .reset_index()
        .sort_values([group_col, 'snapshot_year'])
    )
    group_year['yoy_change'] = group_year.groupby(group_col)['median_log_price'].diff()
    group_year['momentum'] = group_year.groupby(group_col)['yoy_change'].transform(
        lambda s: s.shift(1).rolling(lookback_years, min_periods=1).mean()
    )
    momentum_map = group_year.set_index([group_col, 'snapshot_year'])['momentum']
    keys = pd.MultiIndex.from_arrays([df[group_col], df['snapshot_year']])
    return pd.Series(momentum_map.reindex(keys).to_numpy(), index=df.index)


def compute_national_momentum(df: pd.DataFrame, lookback_years: int = 3) -> pd.Series:
    """Trailing avg YoY change in the nationwide median log_price_t0, using
    only years strictly before each row's own snapshot_year. Same leak-free
    construction as _trailing_momentum, with a constant group key so it
    captures the countrywide trend rather than any one city/hex — a
    real-estate-specific stand-in for general inflation, inferred from our
    own data instead of an external CPI source."""
    national = df.assign(_national='ALL')
    return _trailing_momentum(national, '_national', lookback_years).fillna(0.0)


def compute_price_momentum(
    df: pd.DataFrame,
    lookback_years: int = 3,
    h3_resolution: int = H3_MOMENTUM_RESOLUTION,
    h3_min_group_size: int = H3_MOMENTUM_MIN_GROUP_SIZE,
) -> pd.Series:
    """Trailing price momentum computed at H3-hex granularity (matching the
    map's display resolution), falling back to the city-level trend where a
    hex/year has too few sales to estimate one reliably. Isolates local
    market trend from the infra-delta features."""
    city_momentum = _trailing_momentum(df, 'city_name', lookback_years)

    if 'lat' not in df.columns or 'lon' not in df.columns:
        return city_momentum.fillna(0.0)

    import h3

    has_coords = df['lat'].notna() & df['lon'].notna()
    hex_index = pd.Series(pd.NA, index=df.index, dtype='object')
    hex_index[has_coords] = [
        h3.latlng_to_cell(lat, lon, h3_resolution)
        for lat, lon in zip(df.loc[has_coords, 'lat'], df.loc[has_coords, 'lon'])
    ]
    df_with_hex = df.assign(_h3_index=hex_index)

    hex_year_size = df_with_hex.groupby(['_h3_index', 'snapshot_year'])['log_price_t0'].transform('size')
    hex_momentum = _trailing_momentum(df_with_hex, '_h3_index', lookback_years)
    hex_momentum = hex_momentum.where(hex_year_size >= h3_min_group_size)

    return hex_momentum.combine_first(city_momentum).fillna(0.0)


def clean_and_engineer_features(
    df: pd.DataFrame,
    apply_outlier_filter: bool = True,
    price_group_k: float = 1.0,
    price_group_min_size: int = 30,
    ratio_k: float = 1.5,
    momentum_lookback_years: int = 3,
    use_national_momentum: bool = True,
) -> pd.DataFrame:
    # ==========================================
    # Type Casting & Cleanup
    # ==========================================

    # Drop columns that are 100% missing values (prevents the 0-category bug)
    df = df.dropna(axis=1, how='all')

    # ==========================================
    # Outlier Removal (הסרת עסקאות מסחריות, טעויות ומשפחה)
    # ==========================================
    initial_len = len(df)

    # Prices must be positive to take a log
    df = df[(df['price_t0'] > 0) & (df['price_t1'] > 0)].copy()

    if apply_outlier_filter:
        # Price-level outliers: Tukey fences on log(price), per city.
        # Log scale because prices are right-skewed; per-city because a "normal"
        # price in Tel Aviv is a mansion-tier outlier in a periphery town.
        log_price_t0 = np.log(df['price_t0'])
        price_mask = _tukey_mask_by_group(
            log_price_t0, df['city_name'], k=price_group_k, min_group_size=price_group_min_size
        )
        after_price = len(df[price_mask])
        df = df[price_mask].copy()

        # Price-change outliers: Tukey fences on the log price ratio.
        # Catches family transfers / discounted or fabricated sales regardless of city.
        log_ratio = np.log(df['price_t1'] / df['price_t0'])
        ratio_mask = log_ratio.between(*_tukey_bounds(log_ratio, k=ratio_k))
        df = df[ratio_mask].copy()

        print(f"🧹 Removed {initial_len - after_price} price-level outliers and "
              f"{after_price - len(df)} price-change outliers "
              f"({initial_len - len(df)} total, Commercial/Family/Typos).")
    else:
        print("🧹 Outlier filter disabled (apply_outlier_filter=False) — skipping Tukey filtering.")

    # Convert known categorical columns
    categorical_cols = ['city_name', 'location_accuracy']
    for col in categorical_cols:
        if col in df.columns:
            df[col] = df[col].astype('category')

    # Safely convert health scores to numeric
    numeric_cols = ['health_score_now', 'health_score_future']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    # THE NEW SAFETY NET: Drop any remaining text ('object') columns.
    object_cols = df.select_dtypes(include=['object']).columns
    if len(object_cols) > 0:
        print(f"🧹 Dropping unhandled text columns to prevent crashes: {list(object_cols)}")
        df = df.drop(columns=object_cols)

    poi_types = ['school', 'train', 'health', 'park', 'supermarket', 'mall',
             'hotel', 'kindergarten', 'light_rail', 'bus', 'hospital', 'clinic']
    for poi in poi_types:
        now_col = f'{poi}_score_now'
        future_col = f'{poi}_score_future'
        if now_col in df.columns and future_col in df.columns:
            df[f'{poi}_score_delta'] = df[future_col] - df[now_col]
    df['log_price_t0'] = np.log(df['price_t0'])
    df['price_momentum'] = compute_price_momentum(df, lookback_years=momentum_lookback_years)
    if use_national_momentum:
        df['national_price_momentum'] = compute_national_momentum(df, lookback_years=momentum_lookback_years)

    # Aggregate POI scores across all types — a single "how well-served is
    # this property overall" signal alongside the per-type deltas.
    poi_now_cols = [f'{poi}_score_now' for poi in poi_types if f'{poi}_score_now' in df.columns]
    poi_future_cols = [f'{poi}_score_future' for poi in poi_types if f'{poi}_score_future' in df.columns]
    poi_delta_cols = [f'{poi}_score_delta' for poi in poi_types if f'{poi}_score_delta' in df.columns]
    if poi_now_cols:
        df['total_poi_score_now'] = df[poi_now_cols].sum(axis=1)
    if poi_future_cols:
        df['total_poi_score_future'] = df[poi_future_cols].sum(axis=1)
    if poi_delta_cols:
        df['total_poi_score_delta'] = df[poi_delta_cols].sum(axis=1)

    if 'num_rooms' in df.columns:
        df['price_per_room'] = np.where(df['num_rooms'] > 0, df['price_t0'] / df['num_rooms'], np.nan)

    # ==========================================

    # Quick Data Analysis
    future_cols = [col for col in df.columns if 'future' in col]
    has_future_infra = (df[future_cols] > 0).any(axis=1)
    print(f"📊 Data Sparsity: {has_future_infra.sum()} out of {len(df)} properties had new infrastructure built nearby.")

    return df


def fit_city_room_price_stats(
    X_train: pd.DataFrame, min_group_size: int = 10
) -> Tuple[pd.Series, float]:
    """Median log_price_t0 per (city_name, num_rooms), fit on TRAIN rows
    only (groups with <min_group_size rows are dropped so the caller falls
    back to the global median for them, avoiding leakage/noise)."""
    global_median = X_train['log_price_t0'].median()
    grouped = X_train.groupby(['city_name', 'num_rooms'])['log_price_t0']
    medians = grouped.median()[grouped.size() >= min_group_size]
    return medians, global_median


def apply_city_room_price_ratio(
    df: pd.DataFrame, stats: pd.Series, global_median: float
) -> pd.Series:
    """log_price_t0 minus the (city, num_rooms) median fit on train,
    falling back to the global median for unseen/too-small combos."""
    keys = pd.MultiIndex.from_arrays([df['city_name'], df['num_rooms']])
    looked_up = pd.Series(stats.reindex(keys).to_numpy(), index=df.index)
    return df['log_price_t0'] - looked_up.fillna(global_median)


def prepare_data(
    df: pd.DataFrame,
    split_year: int,
    use_city_room_ratio: bool = False,
    city_room_min_group_size: int = 10,
    **clean_kwargs
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    print(f"Preparing data pipeline (Temporal Split at {split_year})...")
    df = clean_and_engineer_features(df, **clean_kwargs)

    # ==========================================
    # 2. Temporal Split (train on the past, test on "present")
    # ==========================================

    # קודם כל מפרידים את המטרה (y) מהמאפיינים (X)
    cols_to_drop_safe = [c for c in COLS_TO_DROP if c in df.columns]
    X = df.drop(columns=cols_to_drop_safe)
    y = df[TARGET_COL]

    train_mask = df['snapshot_year'] < split_year
    test_mask = df['snapshot_year'] >= split_year

    X_train = X[train_mask].copy()
    y_train = y[train_mask].copy()
    X_test = X[test_mask].copy()
    y_test = y[test_mask].copy()

    if use_city_room_ratio:
        stats, global_median = fit_city_room_price_stats(X_train, min_group_size=city_room_min_group_size)
        X_train['city_room_price_ratio'] = apply_city_room_price_ratio(X_train, stats, global_median)
        X_test['city_room_price_ratio'] = apply_city_room_price_ratio(X_test, stats, global_median)

    print(f"✅ Train set: {X_train.shape[0]} rows")
    print(f"✅ Test set:  {X_test.shape[0]} rows")

    return X_train, X_test, y_train, y_test