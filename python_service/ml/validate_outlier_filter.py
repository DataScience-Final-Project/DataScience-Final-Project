import argparse
import uuid
from datetime import datetime, timezone

from ml import cv, metrics_logger
from ml.config import COLS_TO_DROP, CV_CONFIG, METRICS_LOG_PATH, TARGET_COL, XGB_PARAMS, HORIZON_CONFIGS
from ml.data_loader import load_snapshot_data
from ml.pipeline import clean_and_engineer_features

CONFIGS = {
    "no_filter": dict(apply_outlier_filter=False),
    "current": dict(apply_outlier_filter=True, price_group_k=1.0, ratio_k=1.5),
    "looser": dict(apply_outlier_filter=True, price_group_k=1.5, ratio_k=2.0),
    "stricter": dict(apply_outlier_filter=True, price_group_k=0.75, ratio_k=1.0),
}


def run(horizon: int, n_splits: int = 5):
    if horizon not in HORIZON_CONFIGS:
        raise ValueError(f"Horizon {horizon} not found in config.")

    print(f"Loading raw data for {horizon}-year horizon...")
    horizon_config = HORIZON_CONFIGS[horizon]
    momentum_kwargs = dict(
        momentum_lookback_years=horizon_config.get("momentum_lookback_years", 3),
        use_national_momentum=horizon_config.get("use_national_momentum", True),
    )
    raw_df = load_snapshot_data(horizon=horizon)

    print(f"\n{'name':<10} {'rows_removed':>12} {'mean_rmse':>10} {'mean_mae':>10} {'mean_r2':>10}")
    for name, cfg in CONFIGS.items():
        cleaned = clean_and_engineer_features(raw_df.copy(), **cfg, **momentum_kwargs)
        rows_removed = len(raw_df) - len(cleaned)

        cols_to_drop_safe = [c for c in COLS_TO_DROP if c in cleaned.columns]
        X = cleaned.drop(columns=cols_to_drop_safe)
        y = cleaned[TARGET_COL]

        cv_result = cv.run_cv(X, y, cleaned['snapshot_year'], XGB_PARAMS, n_splits=n_splits)

        print(f"{name:<10} {rows_removed:>12} {cv_result['mean_rmse']:>10.4f} "
              f"{cv_result['mean_mae']:>10.4f} {cv_result['mean_r2']:>10.4f}")

        metrics_logger.log_run({
            "run_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "experiment": "tukey_ablation",
            "horizon": horizon,
            "config_name": name,
            "config": cfg,
            "rows_removed": rows_removed,
            "cv_mean_rmse": cv_result["mean_rmse"],
            "cv_mean_mae": cv_result["mean_mae"],
            "cv_mean_r2": cv_result["mean_r2"],
        }, path=METRICS_LOG_PATH)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon", type=int, required=True)
    parser.add_argument("--n-splits", type=int, default=CV_CONFIG["n_splits"])
    args = parser.parse_args()

    run(args.horizon, n_splits=args.n_splits)
