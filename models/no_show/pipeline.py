"""
Complete Training, Benchmark Evaluation, Calibration, and Serialization Pipeline.
Week 3: Steps 3.1, 3.2, 3.3
"""

import os
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    roc_curve,
    precision_recall_curve,
)
from sklearn.pipeline import Pipeline
from sqlalchemy import text

from .dataset import extract_appointment_dataset
from .features import (
    engineer_features,
    filter_training_cohort,
    build_preprocessor,
    ALL_FEATURE_COLUMNS,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
)
from .models import get_model_candidates
from .calibration import calibrate_and_compare
from .fairness import analyze_fairness

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ARTIFACTS_DIR = os.path.join(BASE_DIR, "models", "artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

MODEL_ARTIFACT_PATH = os.path.join(ARTIFACTS_DIR, "no_show_model.joblib")
META_ARTIFACT_PATH = os.path.join(ARTIFACTS_DIR, "no_show_model_meta.json")


def compute_evaluation_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> Dict[str, Any]:
    """
    Computes comprehensive binary classification metrics.
    """
    y_pred = (y_prob >= threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])

    # ROC Curve downsampled to 15 points
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    idx_roc = np.linspace(0, len(fpr) - 1, min(15, len(fpr)), dtype=int)
    roc_points = [{"fpr": round(float(fpr[i]), 4), "tpr": round(float(tpr[i]), 4)} for i in idx_roc]

    # PR Curve downsampled to 15 points
    prec, rec, _ = precision_recall_curve(y_true, y_prob)
    idx_pr = np.linspace(0, len(prec) - 1, min(15, len(prec)), dtype=int)
    pr_points = [{"precision": round(float(prec[i]), 4), "recall": round(float(rec[i]), 4)} for i in idx_pr]

    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4) if len(np.unique(y_true)) > 1 else 0.5,
        "pr_auc": round(float(average_precision_score(y_true, y_prob)), 4) if len(np.unique(y_true)) > 1 else 0.0,
        "brier_score": round(float(brier_score_loss(y_true, y_prob)), 4),
        "confusion_matrix": {
            "tn": int(cm[0, 0]),
            "fp": int(cm[0, 1]),
            "fn": int(cm[1, 0]),
            "tp": int(cm[1, 1]),
        },
        "roc_curve": roc_points,
        "pr_curve": pr_points,
    }


def register_model_in_database(
    model_name: str,
    version: str,
    metrics: Dict[str, Any],
    parameters: Dict[str, Any],
    artifact_uri: str,
    db_engine=None,
) -> str:
    """
    Registers model artifact and evaluation metrics in ai.ai_model_versions table.
    """
    if db_engine is None:
        from app.db.session import engine as db_engine

    model_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Deprecate prior active models for this task
    deprecate_query = text("""
        UPDATE ai.ai_model_versions
        SET status = 'deprecated', updated_at = :now
        WHERE model_name = :model_name AND status = 'active'
    """)

    query = text("""
        INSERT INTO ai.ai_model_versions (
            id, model_name, model_type, version, framework, task,
            dataset_reference, metrics, artifact_uri, parameters, status,
            created_at, updated_at
        ) VALUES (
            :id, :model_name, :model_type, :version, :framework, :task,
            :dataset_reference, :metrics, :artifact_uri, :parameters, :status,
            :created_at, :updated_at
        )
    """)

    params = {
        "id": model_id,
        "model_name": model_name,
        "model_type": "BinaryClassifier",
        "version": version,
        "framework": "scikit-learn",
        "task": "appointment_no_show_prediction",
        "dataset_reference": "hospital.appointments + clinical.patients (Cohort 2026)",
        "metrics": json.dumps(metrics),
        "artifact_uri": artifact_uri,
        "parameters": json.dumps(parameters),
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }

    try:
        with db_engine.connect() as conn:
            conn.execute(deprecate_query, {"model_name": model_name, "now": now})
            conn.execute(query, params)
            conn.commit()
    except Exception as e:
        print(f"Warning: Failed to record model in ai.ai_model_versions: {e}")

    return model_id


def train_and_evaluate_pipeline(split_method: str = "temporal") -> Dict[str, Any]:
    """
    Executes the entire end-to-end Week 3 Machine Learning pipeline.
    """
    print(f"\n--- [Week 3 ML] 1. Extracting data & engineering features ---")
    raw_df = extract_appointment_dataset()
    engineered_df = engineer_features(raw_df)
    cohort_df = filter_training_cohort(engineered_df)

    total_records = len(cohort_df)
    print(f"Cohort size: {total_records} appointments (completed/no-show)")

    # Features and labels
    X = cohort_df[ALL_FEATURE_COLUMNS]
    y = cohort_df["target_no_show"].values

    # Train / Test split
    if split_method == "temporal":
        split_idx = int(total_records * 0.8)
        X_train_df, X_test_df = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        test_cohort_df = cohort_df.iloc[split_idx:].copy()
    else:
        from sklearn.model_selection import train_test_split
        X_train_df, X_test_df, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        test_cohort_df = cohort_df.loc[X_test_df.index].copy()

    print(f"Train set: {len(X_train_df)} | Test set: {len(X_test_df)} (Split: {split_method})")

    # Fit preprocessor on X_train
    preprocessor = build_preprocessor()
    X_train_proc = preprocessor.fit_transform(X_train_df)
    X_test_proc = preprocessor.transform(X_test_df)

    feature_names = preprocessor.get_feature_names_out().tolist()

    # Train and Benchmark Candidate Models
    print("\n--- [Week 3 ML] 2. Training candidate models & benchmark comparison ---")
    candidates = get_model_candidates(random_state=42)
    benchmark_results = {}
    fitted_models = {}

    for name, model in candidates.items():
        model.fit(X_train_proc, y_train)
        fitted_models[name] = model

        # Probability scores
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(X_test_proc)[:, 1]
        else:
            probs = model.predict(X_test_proc).astype(float)

        metrics = compute_evaluation_metrics(y_test, probs)
        benchmark_results[name] = metrics
        print(f"  Model: {name:<22} | ROC-AUC: {metrics['roc_auc']:.4f} | PR-AUC: {metrics['pr_auc']:.4f} | Brier: {metrics['brier_score']:.4f}")

    # Extract Feature Importance & Logistic Regression Odds Ratios
    print("\n--- [Week 3 ML] 3. Extracting feature importance & odds ratios ---")
    log_reg = fitted_models["logistic_regression"]
    tree_model = fitted_models.get("xgboost_trees")

    feature_weights = []
    for idx, f_name in enumerate(feature_names):
        clean_name = f_name.replace("num__", "").replace("cat__", "")
        lr_coef = float(log_reg.coef_[0][idx])
        odds_ratio = float(np.exp(lr_coef))
        tree_importance = float(tree_model.feature_importances_[idx]) if tree_model is not None and hasattr(tree_model, "feature_importances_") else 0.0

        feature_weights.append({
            "feature": clean_name,
            "logistic_coef": round(lr_coef, 4),
            "odds_ratio": round(odds_ratio, 4),
            "tree_importance": round(tree_importance, 4),
        })

    # Sort by absolute coefficient impact
    feature_weights.sort(key=lambda x: abs(x["logistic_coef"]), reverse=True)

    # Best baseline model selection for calibration
    tree_roc = benchmark_results.get("xgboost_trees", {}).get("roc_auc", 0)
    lr_roc = benchmark_results.get("logistic_regression", {}).get("roc_auc", 0)
    best_candidate_name = "xgboost_trees" if tree_roc >= lr_roc else "logistic_regression"
    best_estimator = fitted_models[best_candidate_name]

    # Probability Calibration
    print("\n--- [Week 3 ML] 4. Calibrating probabilities & reliability diagrams ---")
    calibration_analysis = calibrate_and_compare(
        best_estimator,
        X_train_proc,
        y_train,
        X_test_proc,
        y_test,
    )
    print(f"  Uncalibrated Brier Score: {calibration_analysis['uncalibrated_brier']:.4f}")
    print(f"  Calibrated Brier Score:   {calibration_analysis['best_brier']:.4f} ({calibration_analysis['best_method']})")

    # Final Calibrated Model Pipeline
    best_calibrated_model = calibration_analysis["best_calibrated_model"]
    full_production_pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", best_calibrated_model),
    ])

    # Subgroup Fairness Analysis on Test Cohort
    print("\n--- [Week 3 ML] 5. Conducting subgroup fairness audit ---")
    final_test_probs = full_production_pipeline.predict_proba(X_test_df)[:, 1]
    final_test_preds = (final_test_probs >= 0.40).astype(int)  # 0.40 operational risk threshold
    fairness_audit = analyze_fairness(test_cohort_df, y_test, final_test_preds)

    # Serialize Artifacts
    print(f"\n--- [Week 3 ML] 6. Serializing model artifact to {MODEL_ARTIFACT_PATH} ---")
    joblib.dump(full_production_pipeline, MODEL_ARTIFACT_PATH)

    version_str = f"v1.{datetime.now().strftime('%Y%m%d%H%M%S')}"
    metadata_payload = {
        "model_name": "AppointmentNoShowPredictor",
        "version": version_str,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "split_method": split_method,
        "sample_size": total_records,
        "train_size": len(X_train_df),
        "test_size": len(X_test_df),
        "base_candidate": best_candidate_name,
        "calibration_method": calibration_analysis["best_method"],
        "benchmark_comparison": benchmark_results,
        "calibration": {
            "uncalibrated_brier": calibration_analysis["uncalibrated_brier"],
            "calibrated_brier": calibration_analysis["best_brier"],
            "uncalibrated_curve": calibration_analysis["uncalibrated_curve"],
            "calibrated_curve": calibration_analysis["best_curve"],
        },
        "feature_weights": feature_weights[:15],
        "fairness_audit": fairness_audit,
    }

    with open(META_ARTIFACT_PATH, "w") as f:
        json.dump(metadata_payload, f, indent=2)

    # Register in DB
    db_version_id = register_model_in_database(
        model_name="AppointmentNoShowPredictor",
        version=version_str,
        metrics={
            "roc_auc": benchmark_results[best_candidate_name]["roc_auc"],
            "pr_auc": benchmark_results[best_candidate_name]["pr_auc"],
            "brier_score": calibration_analysis["best_brier"],
            "f1_score": benchmark_results[best_candidate_name]["f1_score"],
        },
        parameters={
            "split_method": split_method,
            "base_candidate": best_candidate_name,
            "calibration_method": calibration_analysis["best_method"],
        },
        artifact_uri=MODEL_ARTIFACT_PATH,
    )
    metadata_payload["db_version_id"] = db_version_id

    print(f"Successfully registered model version {version_str} (ID: {db_version_id})")
    return metadata_payload


if __name__ == "__main__":
    train_and_evaluate_pipeline()
