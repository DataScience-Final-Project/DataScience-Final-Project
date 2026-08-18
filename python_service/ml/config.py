# --- ML Pipeline Settings ---
TARGET_COL = 'log_change'

HORIZON_CONFIGS = {
    5: {
        "split_year": 2014,
        "model_save_path": "data/saved_models/xgb_real_estate_5yr_v1.json",
        "momentum_lookback_years": 3,
        "use_national_momentum": False,
    },
    10: {
        "split_year": 2009,
        "model_save_path": "data/saved_models/xgb_real_estate_10yr_v1.json",
        "momentum_lookback_years": 3,
        "use_national_momentum": True,
    }
}
COLS_TO_DROP = [
    'property_id',
    'snapshot_year',
    'horizon_years',
    'price_t0',
    'price_t1',
    'pct_change',
    'log_change',
    'lat',
    'lon',
]

# --- XGBoost Hyperparameters ---
XGB_PARAMS = {
    'n_estimators': 12000,
    'learning_rate': 0.04,
    'max_depth': 4,
    'min_child_weight': 8,
    'gamma': 0.1,            #minimum gain to make a split
    'subsample': 0.8,
    'colsample_bytree': 0.6,
    'enable_categorical': True,
    'random_state': 42,
    'alpha': 1,
    'lambda': 2,
    'n_jobs': -1,
    'early_stopping_rounds': 100,
    'eval_metric': 'mae'
}

# --- Metrics Logging ---
METRICS_LOG_PATH = "data/metrics_log.jsonl"

# --- Cross-Validation ---
CV_CONFIG = {
    "n_splits": 5,
}

# --- Hyperparameter Search Space (sampling distributions, kept separate
# from the currently-active XGB_PARAMS above) ---
SEARCH_SPACE = {
    'learning_rate': [0.01, 0.02, 0.03, 0.04, 0.06, 0.08],
    'max_depth': [3, 4, 5, 6],
    'min_child_weight': [1, 4, 8, 12, 20],
    'gamma': [0, 0.1, 0.2, 0.5, 1],
    'subsample': [0.6, 0.7, 0.8, 0.9, 1.0],
    'colsample_bytree': [0.4, 0.5, 0.6, 0.8, 1.0],
    'alpha': [0, 0.5, 1, 2, 5],
    'lambda': [1, 2, 3, 5, 10],
}

# --- city_room_price_ratio interaction feature ---
# Off by default — flip to True only after validate_outlier_filter-style CV
# comparison shows it helps (see ml/cv.py's use_city_room_ratio option).
USE_CITY_ROOM_RATIO = False
CITY_ROOM_MIN_GROUP_SIZE = 10
