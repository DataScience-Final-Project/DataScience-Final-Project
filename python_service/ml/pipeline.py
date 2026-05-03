import pandas as pd
from typing import Tuple
from sklearn.model_selection import train_test_split
from ml.config import TARGET_COL, COLS_TO_DROP

def prepare_data(df: pd.DataFrame, split_year: int) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    # השארנו את split_year בחתימת הפונקציה כדי לא לשבור את קובץ ה-train, 
    # למרות שעכשיו אנחנו פשוט מתעלמים ממנו ועושים פיצול אקראי!
    
    print("Preparing data pipeline (Random Split 80/20)...")
    
    # ==========================================
    # 1. Type Casting & Cleanup
    # ==========================================
    
    # Drop columns that are 100% missing values (prevents the 0-category bug)
    df = df.dropna(axis=1, how='all')

    # ==========================================
    # 0. Outlier Removal (הסרת עסקאות מסחריות, טעויות ומשפחה)
    # ==========================================
    initial_len = len(df)
    
    # 1. מסנן אבסולוטי: מחירים בין חצי מיליון ל-15 מיליון (מסנן משרדי ענק וטעויות)
    valid_price_mask = (
        (df['price_t0'] >= 500000) & (df['price_t0'] <= 15000000) &
        (df['price_t1'] >= 500000) & (df['price_t1'] <= 15000000)
    )
    df = df[valid_price_mask].copy()
    
    # how much did the price change
    price_ratio = df['price_t1'] / df['price_t0']
    
    # removes anomalies where price changed by more than 4x or less than 0.6x 
    logical_ratio_mask = (price_ratio >= 0.6) & (price_ratio <= 4.0)
    df = df[logical_ratio_mask].copy()
    
    print(f"🧹 Removed {initial_len - len(df)} extreme price outliers (Commercial/Family/Typos).")
    
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

    # ==========================================
        
    # Quick Data Analysis
    future_cols = [col for col in df.columns if 'future' in col]
    has_future_infra = (df[future_cols] > 0).any(axis=1)
    print(f"📊 Data Sparsity: {has_future_infra.sum()} out of {len(df)} properties had new infrastructure built nearby.")
        
    # ==========================================
    # 2. Random Split (השיטה החדשה שלנו!)
    # ==========================================
    
    # קודם כל מפרידים את המטרה (y) מהמאפיינים (X)
    cols_to_drop_safe = [c for c in COLS_TO_DROP if c in df.columns]
    X = df.drop(columns=cols_to_drop_safe)
    y = df[TARGET_COL]
    
    # מבצעים את הפיצול האקראי - 80% לאימון, 20% למבחן
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print(f"✅ Train set: {X_train.shape[0]} rows")
    print(f"✅ Test set:  {X_test.shape[0]} rows")
    
    return X_train, X_test, y_train, y_test