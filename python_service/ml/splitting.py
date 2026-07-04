from dataclasses import dataclass
from typing import Tuple

import pandas as pd


@dataclass
class TemporalSplitResult:
    train_df: pd.DataFrame
    val_df: pd.DataFrame
    test_df: pd.DataFrame
    relevant_year: int
    train_pct: float
    val_pct: float
    test_pct: float


class OutcomeYearSplitter:
    def __init__(self, target_train_ratio: float = 0.8, validation_ratio: float = 0.15):
        if not 0 < target_train_ratio < 1:
            raise ValueError("target_train_ratio must be between 0 and 1.")
        if not 0 <= validation_ratio < 1:
            raise ValueError("validation_ratio must be between 0 and 1.")

        self.target_train_ratio = target_train_ratio
        self.validation_ratio = validation_ratio

    def split(self, df: pd.DataFrame) -> TemporalSplitResult:
        self._validate_columns(df)
        outcome_year = self._outcome_year(df)
        relevant_year = self._find_relevant_year(outcome_year, len(df))

        train_val_mask = outcome_year < relevant_year
        test_mask = ~train_val_mask

        train_val_df = df.loc[train_val_mask].copy()
        test_df = df.loc[test_mask].copy()
        train_df, val_df = self._split_validation(train_val_df)

        total = len(df)
        return TemporalSplitResult(
            train_df=train_df,
            val_df=val_df,
            test_df=test_df,
            relevant_year=relevant_year,
            train_pct=len(train_df) / total * 100,
            val_pct=len(val_df) / total * 100,
            test_pct=len(test_df) / total * 100,
        )

    def split_features(
        self,
        df: pd.DataFrame,
        target_col: str,
        cols_to_drop: list[str],
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series, TemporalSplitResult]:
        split = self.split(df)
        cols_to_drop_safe = [c for c in cols_to_drop if c in df.columns]

        X_train = split.train_df.drop(columns=cols_to_drop_safe)
        y_train = split.train_df[target_col]
        X_val = split.val_df.drop(columns=cols_to_drop_safe)
        y_val = split.val_df[target_col]
        X_test = split.test_df.drop(columns=cols_to_drop_safe)
        y_test = split.test_df[target_col]

        return X_train, X_val, X_test, y_train, y_val, y_test, split

    def _find_relevant_year(self, outcome_year: pd.Series, total_rows: int) -> int:
        candidate_years = range(int(outcome_year.min()) + 1, int(outcome_year.max()) + 1)
        split_candidates = [
            (abs((outcome_year < year).mean() - self.target_train_ratio), year)
            for year in candidate_years
            if 0 < (outcome_year < year).sum() < total_rows
        ]
        if not split_candidates:
            raise ValueError("Cannot create temporal train/test split: no year leaves both train and test rows.")

        _, relevant_year = min(split_candidates)
        return relevant_year

    def _split_validation(self, train_val_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        if self.validation_ratio == 0:
            return train_val_df, train_val_df.iloc[0:0].copy()

        outcome_year = self._outcome_year(train_val_df)
        validation_rows = max(1, round(len(train_val_df) * self.validation_ratio))
        sorted_index = outcome_year.sort_values().index
        val_index = sorted_index[-validation_rows:]
        train_index = sorted_index[:-validation_rows]

        if len(train_index) == 0:
            raise ValueError("Cannot create validation split: validation_ratio leaves no training rows.")

        return train_val_df.loc[train_index].copy(), train_val_df.loc[val_index].copy()

    def _outcome_year(self, df: pd.DataFrame) -> pd.Series:
        return df['snapshot_year'] + df['horizon_years']

    def _validate_columns(self, df: pd.DataFrame) -> None:
        required_cols = ['snapshot_year', 'horizon_years']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Cannot create temporal split: missing columns {missing_cols}.")
