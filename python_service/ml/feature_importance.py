import argparse

import pandas as pd
import xgboost as xgb

from ml.config import HORIZON_CONFIGS
from ml.data_loader import load_snapshot_data
from ml.pipeline import prepare_data


def compute_gain_importance(model: xgb.XGBRegressor) -> pd.Series:
    scores = model.get_booster().get_score(importance_type='gain')
    return pd.Series(scores).sort_values(ascending=False)


def compute_shap_importance(model: xgb.XGBRegressor, X_sample: pd.DataFrame, max_rows: int = 2000) -> pd.Series:
    import shap

    sample = X_sample.sample(min(max_rows, len(X_sample)), random_state=42)
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(sample)
    mean_abs_shap = pd.Series(abs(shap_values).mean(axis=0), index=sample.columns)
    return mean_abs_shap.sort_values(ascending=False)


def main(horizon: int, top_n: int = 20, use_shap: bool = False):
    config = HORIZON_CONFIGS[horizon]
    model = xgb.XGBRegressor(enable_categorical=True)
    model.load_model(config["model_save_path"])

    df = load_snapshot_data(horizon=horizon)
    _, X_test, _, _ = prepare_data(df, config["split_year"])

    gain_importance = compute_gain_importance(model)
    print(f"\n--- Gain Importance (top {top_n}) ---")
    print(gain_importance.head(top_n).to_string())

    low_value = gain_importance[gain_importance < 0.01 * gain_importance.iloc[0]]
    if len(low_value) > 0:
        print(f"\nPruning candidates (gain < 1% of top feature): {list(low_value.index)}")

    out_df = gain_importance.rename("gain").to_frame()

    if use_shap:
        shap_importance = compute_shap_importance(model, X_test)
        print(f"\n--- SHAP Importance (top {top_n}) ---")
        print(shap_importance.head(top_n).to_string())
        out_df = out_df.join(shap_importance.rename("mean_abs_shap"), how="outer")

    out_path = f"data/feature_importance_{horizon}yr.csv"
    out_df.to_csv(out_path)
    print(f"\nWritten to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon", type=int, required=True)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--shap", action="store_true")
    args = parser.parse_args()

    main(args.horizon, top_n=args.top_n, use_shap=args.shap)
