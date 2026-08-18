from typing import List, Tuple

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit

from ml.pipeline import apply_city_room_price_ratio, fit_city_room_price_stats


def walk_forward_year_splits(
    snapshot_years: pd.Series, n_splits: int = 5
) -> List[Tuple[np.ndarray, np.ndarray]]:
    """Rolling-origin CV that respects the temporal nature of the data.

    Splits on unique snapshot_year values (not row order, since many rows
    share the same year) via TimeSeriesSplit, then maps each year-level
    split back to row-level positional indices.
    """
    unique_years = np.sort(snapshot_years.unique())
    n_splits = min(n_splits, len(unique_years) - 1)
    if n_splits < 1:
        raise ValueError(
            f"Not enough distinct snapshot_year values ({len(unique_years)}) for CV."
        )

    tscv = TimeSeriesSplit(n_splits=n_splits)
    positions = np.arange(len(snapshot_years))

    splits = []
    for train_year_idx, test_year_idx in tscv.split(unique_years):
        train_years = set(unique_years[train_year_idx])
        test_years = set(unique_years[test_year_idx])
        train_pos = positions[snapshot_years.isin(train_years)]
        test_pos = positions[snapshot_years.isin(test_years)]
        splits.append((train_pos, test_pos))

    return splits


def run_cv(
    X: pd.DataFrame,
    y: pd.Series,
    snapshot_years: pd.Series,
    xgb_params: dict,
    n_splits: int = 5,
    use_city_room_ratio: bool = False,
    city_room_min_group_size: int = 10,
) -> dict:
    """Fits one model per walk-forward fold, mirroring train.py's early
    stopping pattern (eval_set = that fold's own held-out data)."""
    splits = walk_forward_year_splits(snapshot_years, n_splits=n_splits)

    fold_scores = []
    for fold_i, (train_pos, test_pos) in enumerate(splits):
        X_train, y_train = X.iloc[train_pos].copy(), y.iloc[train_pos]
        X_test, y_test = X.iloc[test_pos].copy(), y.iloc[test_pos]
        train_years = snapshot_years.iloc[train_pos]
        test_years = snapshot_years.iloc[test_pos]

        if use_city_room_ratio:
            stats, global_median = fit_city_room_price_stats(X_train, min_group_size=city_room_min_group_size)
            X_train['city_room_price_ratio'] = apply_city_room_price_ratio(X_train, stats, global_median)
            X_test['city_room_price_ratio'] = apply_city_room_price_ratio(X_test, stats, global_median)

        model = xgb.XGBRegressor(**xgb_params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_train, y_train), (X_test, y_test)],
            verbose=False,
        )

        preds = model.predict(X_test)
        fold_scores.append({
            "fold": fold_i,
            "train_rows": len(X_train),
            "test_rows": len(X_test),
            "train_year_range": [int(train_years.min()), int(train_years.max())],
            "test_year_range": [int(test_years.min()), int(test_years.max())],
            "rmse": float(np.sqrt(mean_squared_error(y_test, preds))),
            "mae": float(mean_absolute_error(y_test, preds)),
            "r2": float(r2_score(y_test, preds)),
            "best_iteration": int(getattr(model, "best_iteration", model.get_params()["n_estimators"])),
        })

    weights = np.array([f["test_rows"] for f in fold_scores], dtype=float)
    return {
        "fold_scores": fold_scores,
        "mean_rmse": float(np.mean([f["rmse"] for f in fold_scores])),
        "std_rmse": float(np.std([f["rmse"] for f in fold_scores])),
        "mean_mae": float(np.mean([f["mae"] for f in fold_scores])),
        "std_mae": float(np.std([f["mae"] for f in fold_scores])),
        "mean_r2": float(np.mean([f["r2"] for f in fold_scores])),
        "median_r2": float(np.median([f["r2"] for f in fold_scores])),
        "weighted_mean_r2": float(np.average([f["r2"] for f in fold_scores], weights=weights)),
        "weighted_mean_rmse": float(np.average([f["rmse"] for f in fold_scores], weights=weights)),
    }
