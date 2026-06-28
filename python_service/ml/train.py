import os
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from ml.data_loader import load_snapshot_data
from ml.pipeline import prepare_data
from ml.config import XGB_PARAMS, HORIZON_CONFIGS

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

    # Prepare Data
    X_train, X_test, y_train, y_test = prepare_data(df, split_year)
    
    if X_train.empty or X_test.empty:
        print("❌ Cannot train model: Train or Test set is empty.")
        return None

    # Initialize Model
    print("\nInitializing XGBoost Regressor...")

    model = xgb.XGBRegressor(**XGB_PARAMS)
    
    # Train Model
    print("Training started...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        verbose=1000 # Print evaluation metrics every 1000 trees
    )
    
    # Evaluate Performance
    print("\n--- 📈 Model Evaluation ---")
    print("\n--- train ---")
    predictions = model.predict(X_train)
    
    rmse = np.sqrt(mean_squared_error(y_train, predictions))
    mae = mean_absolute_error(y_train, predictions)
    r2 = r2_score(y_train, predictions)
    
    print(f"train RMSE (Log Return): {rmse:.4f}")
    print(f"train MAE  (Log Return): {mae:.4f}")
    print(f"train R²   (Log Return): {r2:.4f}")

    print("\n--- test ---")
    predictions = model.predict(X_test)
    
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    mae = mean_absolute_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)

    print(f"Test RMSE (Log Return): {rmse:.4f}")
    print(f"Test MAE  (Log Return): {mae:.4f}")
    print(f"Test R²   (Log Return): {r2:.4f}")
    
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
    
    return model

if __name__ == "__main__":
    # Train both models sequentially
    for h in [5, 10]:
        train_model_for_horizon(h)