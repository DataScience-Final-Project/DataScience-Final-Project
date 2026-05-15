# --- ML Pipeline Settings ---
TARGET_COL = 'log_change'

HORIZON_CONFIGS = {
    5: {
        "split_year": 2014,
        "model_save_path": "data/saved_models/xgb_real_estate_5yr_v1.json"
    },
    10: {
        "split_year": 2009,
        "model_save_path": "data/saved_models/xgb_real_estate_10yr_v1.json"
    }
}
COLS_TO_DROP = [
    'property_id', 
    'snapshot_year',
    'horizon_years',
    'price_t0', 
    'price_t1', 
    'pct_change', 
    'log_change' 
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
