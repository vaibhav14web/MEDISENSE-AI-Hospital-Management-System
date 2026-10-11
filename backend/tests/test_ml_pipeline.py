"""
Unit and Integration Tests for Week 3 Machine Learning Deliverables:
1. Feature Engineering & Preprocessing Pipeline
2. Model Training & Benchmark Comparison (Dummy, Logistic Regression, XGBoost)
3. Metric Integrity (ROC-AUC, PR-AUC, F1, Accuracy)
4. Probability Calibration (Brier Score, Reliability Curves)
5. Subgroup Fairness Audit (Age brackets, Gender parity)
6. Real-time Inference Engine & Operational Risk Tiers
7. REST API Endpoints & RBAC Protection
"""

import os
import pytest
from fastapi.testclient import TestClient

from app.main import app

# Ensure project root is imported
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

from models.no_show.dataset import extract_appointment_dataset
from models.no_show.features import engineer_features, filter_training_cohort, build_preprocessor, ALL_FEATURE_COLUMNS
from models.no_show.models import get_model_candidates
from models.no_show.predict import NoShowPredictor

client = TestClient(app)


@pytest.fixture(scope="module")
def admin_token():
    resp = client.post("/api/v1/auth/login", json={"email": "admin@hospital.com", "password": "Admin@123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def patient_token():
    resp = client.post("/api/v1/auth/login", json={"email": "patient@hospital.com", "password": "Patient@123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_feature_engineering_pipeline():
    """Step 3.1: Verify dataset extraction and feature transformations."""
    raw_df = extract_appointment_dataset()
    assert len(raw_df) > 100
    assert "scheduled_at" in raw_df.columns
    assert "patient_id" in raw_df.columns

    # Engineer features
    feat_df = engineer_features(raw_df)
    assert "age" in feat_df.columns
    assert "lead_time_days" in feat_df.columns
    assert "day_of_week" in feat_df.columns
    assert "prior_appointments" in feat_df.columns
    assert "prior_no_shows" in feat_df.columns
    assert "target_no_show" in feat_df.columns

    # Filter to finalized outcomes
    cohort_df = filter_training_cohort(feat_df)
    assert len(cohort_df) > 0
    # Every row must be completed or no_show
    assert set(cohort_df["status"].unique()).issubset({"completed", "no_show"})

    # Preprocessor transform
    preprocessor = build_preprocessor()
    X = cohort_df[ALL_FEATURE_COLUMNS]
    X_proc = preprocessor.fit_transform(X)
    assert X_proc.shape[0] == len(cohort_df)
    assert X_proc.shape[1] > 10


def test_model_candidates_and_training():
    """Step 3.2: Verify candidate model definitions and benchmark fitting."""
    candidates = get_model_candidates(random_state=42)
    assert "dummy_prior" in candidates
    assert "logistic_regression" in candidates
    assert "xgboost_trees" in candidates

    # Train on small sample
    raw_df = extract_appointment_dataset()
    cohort_df = filter_training_cohort(engineer_features(raw_df))
    X = cohort_df[ALL_FEATURE_COLUMNS]
    y = cohort_df["target_no_show"].values

    preproc = build_preprocessor()
    X_proc = preproc.fit_transform(X)

    for name, model in candidates.items():
        model.fit(X_proc, y)
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(X_proc)[:, 1]
            assert probs.min() >= 0.0
            assert probs.max() <= 1.0


def test_inference_engine_risk_tiers():
    """Step 3.3: Verify calibrated probability scoring and risk tiers."""
    predictor = NoShowPredictor()
    assert predictor.is_ready()

    # Scenario 1: Low risk (short lead time, 0 past no-shows, morning slot)
    low_risk_input = {
        "age": 45,
        "lead_time_days": 1.0,
        "day_of_week": 1,
        "hour_of_day": 9,
        "prior_appointments": 5,
        "prior_no_shows": 0,
        "department_name": "General Medicine",
    }
    low_res = predictor.predict_risk(low_risk_input)
    assert 0.0 <= low_res["no_show_probability"] <= 1.0
    assert "risk_tier" in low_res
    assert "recommended_action" in low_res

    # Scenario 2: High risk (long lead time, 4 past no-shows, afternoon slot)
    high_risk_input = {
        "age": 28,
        "lead_time_days": 45.0,
        "day_of_week": 4,
        "hour_of_day": 16,
        "prior_appointments": 6,
        "prior_no_shows": 4,
        "department_name": "General Medicine",
    }
    high_res = predictor.predict_risk(high_risk_input)
    assert high_res["no_show_probability"] > low_res["no_show_probability"]
    assert len(high_res["top_contributing_factors"]) > 0


def test_ml_api_models_endpoint(admin_token, patient_token):
    """Verify GET /api/v1/ml/no-show/models endpoint & RBAC."""
    # Patient role blocked
    res = client.get("/api/v1/ml/no-show/models", headers={"Authorization": f"Bearer {patient_token}"})
    assert res.status_code == 403

    # Staff allowed
    res = client.get("/api/v1/ml/no-show/models", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["model_name"] == "AppointmentNoShowPredictor"
    assert "benchmark_comparison" in data
    bench = data["benchmark_comparison"]
    assert "dummy_prior" in bench
    assert "logistic_regression" in bench
    assert "xgboost_trees" in bench
    # Check ROC-AUC exists
    assert "roc_auc" in bench["xgboost_trees"]


def test_ml_api_feature_importance_endpoint(admin_token):
    """Verify GET /api/v1/ml/no-show/feature-importance endpoint."""
    res = client.get("/api/v1/ml/no-show/feature-importance", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    weights = res.json()
    assert len(weights) > 0
    first = weights[0]
    assert "feature" in first
    assert "logistic_coef" in first
    assert "odds_ratio" in first
    assert "tree_importance" in first


def test_ml_api_calibration_endpoint(admin_token):
    """Verify GET /api/v1/ml/no-show/calibration endpoint."""
    res = client.get("/api/v1/ml/no-show/calibration", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["uncalibrated_brier"] > 0
    assert data["calibrated_brier"] > 0
    assert len(data["calibrated_curve"]) > 0


def test_ml_api_fairness_endpoint(admin_token):
    """Verify GET /api/v1/ml/no-show/fairness endpoint."""
    res = client.get("/api/v1/ml/no-show/fairness", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["age_subgroups"]) > 0
    assert len(data["gender_subgroups"]) > 0
    assert "gender_demographic_parity_ratio" in data["summary"]


def test_ml_api_predict_endpoint(admin_token):
    """Verify POST /api/v1/ml/no-show/predict endpoint."""
    payload = {
        "age": 35,
        "gender": "Male",
        "lead_time_days": 10.0,
        "day_of_week": 3,
        "hour_of_day": 14,
        "prior_appointments": 4,
        "prior_no_shows": 1,
        "department_name": "Orthopedics",
    }
    res = client.post("/api/v1/ml/no-show/predict", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert 0.0 <= data["no_show_probability"] <= 1.0
    assert data["risk_tier"] in ["LOW", "MEDIUM", "HIGH"]
    assert len(data["top_contributing_factors"]) > 0


def test_ml_api_predict_database_appointment(admin_token):
    """Verify POST /api/v1/ml/no-show/predict-appointment/{id} live scoring & logging."""
    from app.db.session import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    try:
        appt = db.execute(text("SELECT id FROM hospital.appointments WHERE status = 'scheduled' LIMIT 1")).first()
        assert appt is not None, "Need at least one scheduled appointment"
        appt_id = str(appt[0])
    finally:
        db.close()

    res = client.post(f"/api/v1/ml/no-show/predict-appointment/{appt_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["appointment_id"] == appt_id
    assert data["prediction_id"] is not None
    assert 0.0 <= data["no_show_probability"] <= 1.0
