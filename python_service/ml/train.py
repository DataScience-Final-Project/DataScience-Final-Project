import numpy as np

from ml.config import TARGET_COL
from ml.data_loader import load_snapshot_data
from ml.modeling import HorizonConfigProvider, ModelEvaluator, ModelRegistry
from ml.pipeline import prepare_train_val_test


class HorizonTrainer:
    def __init__(
        self,
        config_provider: HorizonConfigProvider | None = None,
        model_registry: ModelRegistry | None = None,
        evaluator: ModelEvaluator | None = None,
    ):
        self.config_provider = config_provider or HorizonConfigProvider()
        self.model_registry = model_registry or ModelRegistry(self.config_provider)
        self.evaluator = evaluator or ModelEvaluator()

    def train(self, horizon: int):
        print(f"\n{'=' * 50}")
        print(f" STARTING PIPELINE FOR {horizon}-YEAR HORIZON")
        print(f"{'=' * 50}")

        config = self.config_provider.get(horizon)
        df = load_snapshot_data(horizon=horizon)
        if df.empty:
            print(f"Error: No data retrieved for {horizon}-year horizon. Skipping.")
            return None

        prepared = prepare_train_val_test(df, config)
        if prepared.X_train.empty or prepared.X_val.empty or prepared.X_test.empty:
            print("Cannot train model: Train, validation, or test set is empty.")
            return None

        print("\nInitializing XGBoost Regressor...")
        model = self.model_registry.create_model(horizon)

        print("Training started...")
        model.fit(
            prepared.X_train,
            prepared.y_train,
            eval_set=[
                (prepared.X_train, prepared.y_train),
                (prepared.X_val, prepared.y_val),
            ],
            verbose=1000,
        )

        print("\n--- Model Evaluation ---")
        train_metrics = self.evaluator.evaluate(model, prepared.X_train, prepared.y_train)
        val_metrics = self.evaluator.evaluate(model, prepared.X_val, prepared.y_val)
        test_metrics = self.evaluator.evaluate(model, prepared.X_test, prepared.y_test)

        self.evaluator.print_metric_guide()
        self.evaluator.print_metrics("train", train_metrics)
        self.evaluator.print_metrics("validation", val_metrics)
        self.evaluator.print_metrics("test", test_metrics)
        self.evaluator.print_zero_baseline("test", prepared.y_test)
        self.evaluator.print_cluster_metrics(
            "test",
            prepared.split.test_df,
            TARGET_COL,
            test_metrics["predictions"],
        )

        self._print_example_prediction(prepared.y_test, test_metrics["predictions"])

        save_path = self.model_registry.save_model(horizon, model)
        print(f"\nModel successfully saved to: {save_path}")
        return model

    def _print_example_prediction(self, y_test, predictions) -> None:
        if len(predictions) == 0:
            return

        actual_pct = (np.exp(y_test.iloc[0]) - 1) * 100
        pred_pct = (np.exp(predictions[0]) - 1) * 100
        print("\nExample Prediction (Test Row 0):")
        print(f"   Actual Price Growth: {actual_pct:.2f}%")
        print(f"   Predicted Growth:    {pred_pct:.2f}%")


def train_model_for_horizon(horizon: int):
    return HorizonTrainer().train(horizon)


if __name__ == "__main__":
    trainer = HorizonTrainer()
    for h in trainer.config_provider.horizons():
        trainer.train(h)
