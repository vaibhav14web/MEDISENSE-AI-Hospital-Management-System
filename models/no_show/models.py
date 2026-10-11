"""
Model definitions and candidate estimators for appointment no-show prediction.
Week 3: Step 3.2
"""

from typing import Dict, Any
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
import xgboost as xgb


def get_model_candidates(random_state: int = 42) -> Dict[str, Any]:
    """
    Returns candidate models for benchmark comparison.
    1. Baseline 1: Dummy Prior Baseline
    2. Model 1: Regularized Logistic Regression (interpretable odds ratios)
    3. Model 2: Tree-Based Gradient Boosted Decision Trees (XGBoost)
    """
    return {
        "dummy_prior": DummyClassifier(strategy="prior"),
        "logistic_regression": LogisticRegression(
            C=0.75,
            class_weight="balanced",
            max_iter=1000,
            solver="lbfgs",
            random_state=random_state,
        ),
        "xgboost_trees": xgb.XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="logloss",
            random_state=random_state,
            n_jobs=2,
        ),
    }
