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

def prepare_data(df: pd.DataFrame, split_year: int) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    
    print(f"Preparing data pipeline (Temporal Split at {split_year})...")
    
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

    # Price-level outliers: Tukey fences on log(price), per city.
    # Log scale because prices are right-skewed; per-city because a "normal"
    # price in Tel Aviv is a mansion-tier outlier in a periphery town.
    log_price_t0 = np.log(df['price_t0'])
    price_mask = (
        _tukey_mask_by_group(log_price_t0, df['city_name'])
    )
    after_price = len(df[price_mask])
    df = df[price_mask].copy()

    # Price-change outliers: Tukey fences on the log price ratio.
    # Catches family transfers / discounted or fabricated sales regardless of city.
    log_ratio = np.log(df['price_t1'] / df['price_t0'])
    ratio_mask = log_ratio.between(*_tukey_bounds(log_ratio))
    df = df[ratio_mask].copy()

    print(f"🧹 Removed {initial_len - after_price} price-level outliers and "
          f"{after_price - len(df)} price-change outliers "
          f"({initial_len - len(df)} total, Commercial/Family/Typos).")
    
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

    # ==========================================
        
    # Quick Data Analysis
    future_cols = [col for col in df.columns if 'future' in col]
    has_future_infra = (df[future_cols] > 0).any(axis=1)
    print(f"📊 Data Sparsity: {has_future_infra.sum()} out of {len(df)} properties had new infrastructure built nearby.")
        
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
    
    print(f"✅ Train set: {X_train.shape[0]} rows")
    print(f"✅ Test set:  {X_test.shape[0]} rows")
    
    return X_train, X_test, y_train, y_test