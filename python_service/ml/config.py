# --- ML Pipeline Settings ---
RAW_TARGET_COL = 'log_change'
COHORT_BASELINE_COL = 'cohort_mean_log_change'
TARGET_COL = 'relative_log_change'
TARGET_TRAIN_RATIO = 0.8
VALIDATION_RATIO = 0.15
PREDICTION_BASELINE_YEAR = 2014

POI_TYPES = [
    'school',
    'train',
    'health',
    'park',
    'supermarket',
    'mall',
    'hotel',
    'kindergarten',
    'light_rail',
    'bus',
    'hospital',
    'clinic',
]

CATEGORICAL_COLS = ['city_name', 'location_accuracy', 'neighborhood_cell']
NUMERIC_COLS = ['health_score_now', 'health_score_future']
PREDICTION_TEXT_COLS = ['city_name', 'street', 'property_key', 'house_number']

HORIZON_CONFIGS = {
    5: {
        "split_year": 2014,
        "target_train_ratio": TARGET_TRAIN_RATIO,
        "validation_ratio": VALIDATION_RATIO,
        "recent_window_years": 5,
        "use_market_trend": False,
        "market_trend_area_col": "city_name",
        "model_save_path": "data/saved_models/xgb_real_estate_5yr_v1.json",
        "xgb_params": {
            "n_estimators": 6000,
            "learning_rate": 0.025,
            "max_depth": 3,
            "min_child_weight": 25,
            "gamma": 0.2,
            "subsample": 0.85,
            "colsample_bytree": 0.75,
            "alpha": 2,
            "lambda": 6,
        },
    },
    10: {
        "split_year": 2014,
        "target_train_ratio": TARGET_TRAIN_RATIO,
        "validation_ratio": VALIDATION_RATIO,
        "recent_window_years": None,
        "use_market_trend": False,
        "market_trend_area_col": "city_name",
        "model_save_path": "data/saved_models/xgb_real_estate_10yr_v1.json",
        "xgb_params": {},
    }
}
COLS_TO_DROP = [
    'property_id', 
    'snapshot_year',
    'horizon_years',
    'price_t0', 
    'price_t1', 
    'pct_change', 
    RAW_TARGET_COL,
    COHORT_BASELINE_COL,
    TARGET_COL,
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
