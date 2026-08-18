import argparse
import json
import os
import uuid
from datetime import datetime, timezone

from sklearn.model_selection import ParameterSampler

from ml import cv, metrics_logger
from ml.config import (
    COLS_TO_DROP, CV_CONFIG, METRICS_LOG_PATH, SEARCH_SPACE, TARGET_COL, XGB_PARAMS, HORIZON_CONFIGS,
)
from ml.data_loader import load_snapshot_data
from ml.pipeline import clean_and_engineer_features

FIXED_PARAMS = {
    k: v for k, v in XGB_PARAMS.items()
    if k not in SEARCH_SPACE
}

RESULTS_DIR = "data/hyperparam_search_results"


def sample_param_grid(n_iter: int = 25, seed: int = 42) -> list:
    return list(ParameterSampler(SEARCH_SPACE, n_iter=n_iter, random_state=seed))


def run_search(horizon: int, n_iter: int = 25, n_splits: int = 5) -> dict:
    if horizon not in HORIZON_CONFIGS:
        raise ValueError(f"Horizon {horizon} not found in config.")

    print(f"Loading + cleaning data for {horizon}-year horizon...")
    horizon_config = HORIZON_CONFIGS[horizon]
    df = load_snapshot_data(horizon=horizon)
    cleaned = clean_and_engineer_features(
        df,
        momentum_lookback_years=horizon_config.get("momentum_lookback_years", 3),
        use_national_momentum=horizon_config.get("use_national_momentum", True),
    )
    cols_to_drop_safe = [c for c in COLS_TO_DROP if c in cleaned.columns]
    X = cleaned.drop(columns=cols_to_drop_safe)
    y = cleaned[TARGET_COL]
    snapshot_years = cleaned['snapshot_year']

    candidates = sample_param_grid(n_iter=n_iter)
    print(f"Evaluating {len(candidates)} candidate param sets with {n_splits}-fold walk-forward CV...")

    results = []
    for i, sampled in enumerate(candidates):
        params = {**FIXED_PARAMS, **sampled}
        print(f"  [{i + 1}/{len(candidates)}] {sampled}")
        cv_result = cv.run_cv(X, y, snapshot_years, params, n_splits=n_splits)
        results.append({"params": sampled, "cv_mean_mae": cv_result["mean_mae"],
                         "cv_mean_rmse": cv_result["mean_rmse"], "cv_mean_r2": cv_result["mean_r2"]})

    results.sort(key=lambda r: r["cv_mean_mae"])
    best = results[0]

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(RESULTS_DIR, f"{horizon}yr.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"horizon": horizon, "n_iter": n_iter, "n_splits": n_splits,
                    "best_params": best["params"], "best_cv_mae": best["cv_mean_mae"],
                    "candidates": results}, f, indent=2)

    metrics_logger.log_run({
        "run_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "experiment": "hyperparam_search",
        "horizon": horizon,
        "n_iter": n_iter,
        "best_params": best["params"],
        "best_cv_mae": best["cv_mean_mae"],
    }, path=METRICS_LOG_PATH)

    print(f"\nBest candidate (CV MAE={best['cv_mean_mae']:.4f}):")
    print(json.dumps(best["params"], indent=2))
    print(f"\nFull results written to {out_path}")
    print("Review and manually copy winning params into config.py's XGB_PARAMS if satisfied.")

    return {"best": best, "results": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon", type=int, required=True)
    parser.add_argument("--n-iter", type=int, default=25)
    parser.add_argument("--n-splits", type=int, default=CV_CONFIG["n_splits"])
    args = parser.parse_args()

    run_search(args.horizon, n_iter=args.n_iter, n_splits=args.n_splits)
