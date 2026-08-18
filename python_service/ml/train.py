import json
import os
import uuid
from datetime import datetime, timezone

import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from ml import cv, metrics_logger
from ml.data_loader import load_snapshot_data
from ml.pipeline import clean_and_engineer_features, fit_city_room_price_stats, prepare_data
from ml.config import (
    CITY_ROOM_MIN_GROUP_SIZE, COLS_TO_DROP, CV_CONFIG, METRICS_LOG_PATH, TARGET_COL,
    USE_CITY_ROOM_RATIO, XGB_PARAMS, HORIZON_CONFIGS,
)

def train_model_for_horizon(horizon: int):
    """
    Executes the full training pipeline for a specific prediction horizon.
    """
    print(f"\n{'='*50}")
    print(f" STARTING PIPELINE FOR {horizon}-YEAR HORIZON")
    print(f"{'='*50}")
    
    # Get config for this specific horizon
    if horizon not in HORIZON_CONFIGS:
        print(f"❌ Error: Horizon {horizon} not found in config.")
        return None
        
    config = HORIZON_CONFIGS[horizon]
    split_year = config["split_year"]
    save_path = config["model_save_path"]
    
    # Load Data
    df = load_snapshot_data(horizon=horizon)
    if df.empty:
        print(f"❌ Error: No data retrieved for {horizon}-year horizon. Skipping.")
        return None

    momentum_lookback_years = config.get("momentum_lookback_years", 3)
    use_national_momentum = config.get("use_national_momentum", True)

    # Walk-forward CV first — used to pick a robust tree count (median
    # best_iteration across folds) for the final model below, instead of
    # letting the final model's own early stopping watch the holdout test
    # set (which would partially tune the model to the number we then
    # report as "blind" performance).
    print("\n--- 🔁 Walk-forward CV ---")
    cleaned_full = clean_and_engineer_features(
        df, momentum_lookback_years=momentum_lookback_years, use_national_momentum=use_national_momentum
    )
    cols_to_drop_safe = [c for c in COLS_TO_DROP if c in cleaned_full.columns]
    X_full = cleaned_full.drop(columns=cols_to_drop_safe)
    y_full = cleaned_full[TARGET_COL]
    cv_results = cv.run_cv(
        X_full, y_full, cleaned_full['snapshot_year'],
        XGB_PARAMS, n_splits=CV_CONFIG["n_splits"],
        use_city_room_ratio=USE_CITY_ROOM_RATIO,
        city_room_min_group_size=CITY_ROOM_MIN_GROUP_SIZE,
    )
    for fold in cv_results["fold_scores"]:
        print(f"  fold {fold['fold']}: RMSE={fold['rmse']:.4f} MAE={fold['mae']:.4f} R²={fold['r2']:.4f} "
              f"(train={fold['train_rows']} yrs={fold['train_year_range']}, "
              f"test={fold['test_rows']} yrs={fold['test_year_range']})")
    print(f"  mean RMSE: {cv_results['mean_rmse']:.4f} (+/- {cv_results['std_rmse']:.4f})")
    print(f"  mean MAE:  {cv_results['mean_mae']:.4f} (+/- {cv_results['std_mae']:.4f})")
    print(f"  mean R²:   {cv_results['mean_r2']:.4f}  median R²: {cv_results['median_r2']:.4f}  "
          f"weighted mean R²: {cv_results['weighted_mean_r2']:.4f}")

    robust_n_estimators = int(np.median([f["best_iteration"] for f in cv_results["fold_scores"]]))
    print(f"📐 Using n_estimators={robust_n_estimators} for the final model "
          f"(median best_iteration across the {len(cv_results['fold_scores'])} CV folds)")

    # Prepare Data — full training range (no carve-out): the tree count is
    # already fixed from CV above, so the final fit needs no early stopping
    # and never looks at the test set during training.
    X_train, X_test, y_train, y_test = prepare_data(
        df, split_year,
        use_city_room_ratio=USE_CITY_ROOM_RATIO,
        city_room_min_group_size=CITY_ROOM_MIN_GROUP_SIZE,
        momentum_lookback_years=momentum_lookback_years,
        use_national_momentum=use_national_momentum,
    )

    if X_train.empty or X_test.empty:
        print("❌ Cannot train model: Train or Test set is empty.")
        return None

    # Initialize Model
    print("\nInitializing XGBoost Regressor...")

    final_params = {**XGB_PARAMS, 'n_estimators': robust_n_estimators}
    final_params.pop('early_stopping_rounds', None)
    model = xgb.XGBRegressor(**final_params)

    # Train Model — fixed tree count from CV above, no early stopping, so the
    # test set is never touched until the evaluation step right below.
    print("Training started...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train)],
        verbose=1000 # Print evaluation metrics every 1000 trees
    )

    # Evaluate Performance
    print("\n--- 📈 Model Evaluation ---")
    print("\n--- train ---")
    predictions = model.predict(X_train)

    train_rmse = np.sqrt(mean_squared_error(y_train, predictions))
    train_mae = mean_absolute_error(y_train, predictions)
    train_r2 = r2_score(y_train, predictions)

    print(f"train RMSE (Log Return): {train_rmse:.4f}")
    print(f"train MAE  (Log Return): {train_mae:.4f}")
    print(f"train R²   (Log Return): {train_r2:.4f}")

    print("\n--- test ---")
    predictions = model.predict(X_test)

    test_rmse = np.sqrt(mean_squared_error(y_test, predictions))
    test_mae = mean_absolute_error(y_test, predictions)
    test_r2 = r2_score(y_test, predictions)

    print(f"Test RMSE (Log Return): {test_rmse:.4f}")
    print(f"Test MAE  (Log Return): {test_mae:.4f}")
    print(f"Test R²   (Log Return): {test_r2:.4f}")

    # Example: Convert log predictions back to standard percentages
    # (Taking the first item in the test set as an example)
    if len(predictions) > 0:
        actual_pct = (np.exp(y_test.iloc[0]) - 1) * 100
        pred_pct = (np.exp(predictions[0]) - 1) * 100
        print(f"\n🔍 Example Prediction (Test Row 0):")
        print(f"   Actual Price Growth: {actual_pct:.2f}%")
        print(f"   Predicted Growth:    {pred_pct:.2f}%")

    # 6. Save Model
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    model.save_model(save_path)
    print(f"\n Model successfully saved to: {save_path}")

    if USE_CITY_ROOM_RATIO:
        stats, global_median = fit_city_room_price_stats(X_train, min_group_size=CITY_ROOM_MIN_GROUP_SIZE)
        stats_path = save_path.replace('.json', '_city_room_stats.json')
        stats_records = [
            {"city_name": str(city), "num_rooms": float(rooms), "median_log_price_t0": float(median)}
            for (city, rooms), median in stats.items()
        ]
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump({"stats": stats_records, "global_median": float(global_median)}, f)
        print(f" City/room price stats saved to: {stats_path}")

    metrics_logger.log_run({
        "run_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "horizon": horizon,
        "split_year": split_year,
        "xgb_params": XGB_PARAMS,
        "train_rows": int(X_train.shape[0]),
        "test_rows": int(X_test.shape[0]),
        "train_rmse": train_rmse, "train_mae": train_mae, "train_r2": train_r2,
        "test_rmse": test_rmse, "test_mae": test_mae, "test_r2": test_r2,
        "best_iteration": robust_n_estimators,
        "cv_folds": cv_results["fold_scores"],
        "cv_mean_rmse": cv_results["mean_rmse"],
        "cv_mean_mae": cv_results["mean_mae"],
        "cv_mean_r2": cv_results["mean_r2"],
        "cv_median_r2": cv_results["median_r2"],
        "cv_weighted_mean_r2": cv_results["weighted_mean_r2"],
        "cv_weighted_mean_rmse": cv_results["weighted_mean_rmse"],
    }, path=METRICS_LOG_PATH)

    return model

if __name__ == "__main__":
    # Train both models sequentially
    for h in [5, 10]:
        train_model_for_horizon(h)