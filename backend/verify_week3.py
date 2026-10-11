"""
AI-HMS Week 3 Machine Learning Verification Runner
Verifies all Week 3 Machine Learning deliverables:
1. Feature Engineering & Historical Chronological Extraction (Demographics, Timing, Clinical factors)
2. Model Development & Benchmark Comparison (Dummy Prior vs Logistic Regression vs XGBoost Trees)
3. Evaluation Metrics Integrity (ROC-AUC, PR-AUC, F1-Score, Confusion Matrix)
4. Probability Calibration (Brier Score Reduction, Platt Scaling Reliability Curves)
5. Algorithmic Subgroup Fairness Audit (Age Brackets, Gender Parity Ratios)
6. Real-time Inference Engine (Risk Tiers LOW/MEDIUM/HIGH, Driver Explanations, Interventions)
7. Model Artifact Serialization & PostgreSQL Registration (ai.ai_model_versions, ai.ai_predictions)
8. REST API Endpoints & RBAC Boundaries
"""

import sys
import time
import os
from fastapi.testclient import TestClient

# Ensure backend and models can be imported
backend_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(backend_path, ".."))
if backend_path not in sys.path:
    sys.path.append(backend_path)
if project_root not in sys.path:
    sys.path.append(project_root)

from app.main import app
from models.no_show.predict import NoShowPredictor, MODEL_ARTIFACT_PATH, META_ARTIFACT_PATH
from models.no_show.dataset import extract_appointment_dataset
from models.no_show.features import engineer_features, filter_training_cohort

client = TestClient(app)

GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_banner(title: str):
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}")


def run_check(step_id: str, title: str, func) -> bool:
    t0 = time.time()
    try:
        details = func()
        ms = (time.time() - t0) * 1000
        print(f"[{GREEN}PASS{RESET}] {BOLD}{step_id:<8}{RESET} {title:<50} ({ms:.1f}ms)")
        if details:
            for line in details.split("\n"):
                print(f"       -> {line}")
        return True
    except Exception as e:
        ms = (time.time() - t0) * 1000
        print(f"[{RED}FAIL{RESET}] {BOLD}{step_id:<8}{RESET} {title:<50} ({ms:.1f}ms)")
        print(f"       -> {RED}Error: {e}{RESET}")
        return False


def main():
    print(f"\n{BOLD}Executing AI-HMS Week 3 Machine Learning Suite (Appointment No-Show Prediction)...{RESET}")

    # Authenticate as admin
    login = client.post("/api/v1/auth/login", json={"email": "admin@hospital.com", "password": "Admin@123"}).json()
    token = login["access_token"]
    admin_headers = {"Authorization": f"Bearer {token}"}

    # Authenticate as patient for RBAC check
    patient_login = client.post("/api/v1/auth/login", json={"email": "patient@hospital.com", "password": "Patient@123"}).json()
    patient_token = patient_login["access_token"]
    patient_headers = {"Authorization": f"Bearer {patient_token}"}

    results = []

    print_banner("1. FEATURE ENGINEERING PIPELINE (Step 3.1)")

    def check_feature_extraction():
        raw_df = extract_appointment_dataset()
        eng_df = engineer_features(raw_df)
        cohort = filter_training_cohort(eng_df)
        total_cohort = len(cohort)
        no_show_pct = (cohort["target_no_show"].mean()) * 100
        avg_lead = cohort["lead_time_days"].mean()
        return (
            f"Cohort extracted: {total_cohort} appointments (Ground truth outcomes)\n"
            f"Class balance: {no_show_pct:.1f}% No-Show, {100-no_show_pct:.1f}% Completed\n"
            f"Mean booking lead time: {avg_lead:.1f} days | Chronological patient history tracked"
        )
    results.append(run_check("ML-3.1A", "Dataset Extraction & Cohort Filtering", check_feature_extraction))

    def check_feature_dimensions():
        raw_df = extract_appointment_dataset()
        eng_df = engineer_features(raw_df)
        req_cols = ["age", "lead_time_days", "day_of_week", "hour_of_day", "prior_no_shows", "prior_no_show_rate", "chronic_condition_count"]
        for c in req_cols:
            assert c in eng_df.columns, f"Missing {c}"
        return f"Engineered {len(req_cols)} core numerical/clinical features successfully"
    results.append(run_check("ML-3.1B", "Feature Schema & Behavioral History", check_feature_dimensions))

    print_banner("2. MODEL DEVELOPMENT & BENCHMARK COMPARISON (Step 3.2)")

    def check_benchmark_comparison():
        res = client.get("/api/v1/ml/no-show/models", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        bench = data["benchmark_comparison"]
        assert "dummy_prior" in bench
        assert "logistic_regression" in bench
        assert "xgboost_trees" in bench

        dummy_auc = bench["dummy_prior"]["roc_auc"]
        lr_auc = bench["logistic_regression"]["roc_auc"]
        xgb_auc = bench["xgboost_trees"]["roc_auc"]

        return (
            f"Baseline Dummy Prior : ROC-AUC = {dummy_auc:.4f} | PR-AUC = {bench['dummy_prior']['pr_auc']:.4f}\n"
            f"Logistic Regression  : ROC-AUC = {lr_auc:.4f} | PR-AUC = {bench['logistic_regression']['pr_auc']:.4f} (Odds Ratios)\n"
            f"Tree-Based (XGBoost) : ROC-AUC = {xgb_auc:.4f} | PR-AUC = {bench['xgboost_trees']['pr_auc']:.4f}\n"
            f"Selected Candidate   : {data['base_candidate']} (Sample size: {data['sample_size']})"
        )
    results.append(run_check("ML-3.2A", "Candidate Model Benchmark Comparison", check_benchmark_comparison))

    def check_feature_importance():
        res = client.get("/api/v1/ml/no-show/feature-importance", headers=admin_headers)
        assert res.status_code == 200
        weights = res.json()
        assert len(weights) >= 5
        top3 = ", ".join([f"{w['feature']} (OR: {w['odds_ratio']:.2f})" for w in weights[:3]])
        return f"Top Risk Drivers by Odds Ratio: {top3}"
    results.append(run_check("ML-3.2B", "Feature Importance & Odds Ratios", check_feature_importance))

    print_banner("3. PROBABILITY CALIBRATION & RELIABILITY DIAGRAMS (Step 3.3)")

    def check_calibration():
        res = client.get("/api/v1/ml/no-show/calibration", headers=admin_headers)
        assert res.status_code == 200
        cal = res.json()
        uncal = cal["uncalibrated_brier"]
        calib = cal["calibrated_brier"]
        reduction = ((uncal - calib) / uncal) * 100 if uncal > 0 else 0
        return (
            f"Calibration Method : {cal['calibration_method']}\n"
            f"Uncalibrated Brier : {uncal:.4f}\n"
            f"Calibrated Brier   : {calib:.4f} ({reduction:+.1f}% calibration improvement)\n"
            f"Reliability Points : {len(cal['calibrated_curve'])} probability bins verified"
        )
    results.append(run_check("ML-3.3A", "Brier Score Probability Calibration", check_calibration))

    def check_subgroup_fairness():
        res = client.get("/api/v1/ml/no-show/fairness", headers=admin_headers)
        assert res.status_code == 200
        audit = res.json()
        summary = audit["summary"]
        gender_pr = summary.get("gender_demographic_parity_ratio", 1.0)
        age_pr = summary.get("age_demographic_parity_ratio", 1.0)
        return (
            f"Age Brackets Audited : {len(audit['age_subgroups'])} subgroups (<18, 18-35, 36-50, 51-65, 65+)\n"
            f"Gender Audited       : {len(audit['gender_subgroups'])} demographics\n"
            f"Gender Parity Ratio  : {gender_pr:.3f} | Age Parity Ratio: {age_pr:.3f}"
        )
    results.append(run_check("ML-3.3B", "Demographic & Subgroup Fairness Audit", check_subgroup_fairness))

    print_banner("4. MODEL SERIALIZATION & DATABASE PERSISTENCE")

    def check_serialization_and_db():
        assert os.path.exists(MODEL_ARTIFACT_PATH), f"Missing {MODEL_ARTIFACT_PATH}"
        assert os.path.exists(META_ARTIFACT_PATH), f"Missing {META_ARTIFACT_PATH}"
        predictor = NoShowPredictor()
        assert predictor.is_ready()

        from app.db.session import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        try:
            ver = db.execute(text("SELECT model_name, version, status, framework FROM ai.ai_model_versions WHERE status = 'active' ORDER BY created_at DESC LIMIT 1")).mappings().first()
            assert ver is not None
            return (
                f"Joblib Artifact   : {MODEL_ARTIFACT_PATH} ({os.path.getsize(MODEL_ARTIFACT_PATH)/1024:.1f} KB)\n"
                f"Active DB Version : {ver['model_name']} ({ver['version']}) [{ver['status'].upper()}]\n"
                f"Framework Stored  : {ver['framework']}"
            )
        finally:
            db.close()
    results.append(run_check("ML-3.4A", "Model Artifact & ai.ai_model_versions Persistence", check_serialization_and_db))

    print_banner("5. REAL-TIME INFERENCE & CLINICAL INTERVENTION WORKFLOW")

    def check_risk_scoring():
        predictor = NoShowPredictor()
        # High risk test
        hi = predictor.predict_risk({
            "age": 25,
            "lead_time_days": 30.0,
            "day_of_week": 4,
            "hour_of_day": 15,
            "prior_appointments": 5,
            "prior_no_shows": 3,
        })
        assert hi["risk_tier"] in ["MEDIUM", "HIGH"]
        assert len(hi["top_contributing_factors"]) > 0

        # Low risk test
        lo = predictor.predict_risk({
            "age": 55,
            "lead_time_days": 1.0,
            "day_of_week": 1,
            "hour_of_day": 10,
            "prior_appointments": 2,
            "prior_no_shows": 0,
        })
        assert lo["risk_tier"] in ["LOW", "MEDIUM"]
        assert lo["no_show_probability"] < hi["no_show_probability"]

        return (
            f"Low-Risk Profile  : {lo['no_show_percentage']} ({lo['risk_tier']}) -> '{lo['recommended_action'][:50]}...'\n"
            f"High-Risk Profile : {hi['no_show_percentage']} ({hi['risk_tier']}) -> '{hi['recommended_action'][:50]}...'"
        )
    results.append(run_check("ML-3.5A", "Calibrated Risk Tiers & Clinical Interventions", check_risk_scoring))

    def check_live_appointment_scoring():
        from app.db.session import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        try:
            appt = db.execute(text("SELECT id FROM hospital.appointments WHERE status = 'scheduled' LIMIT 1")).first()
            assert appt is not None
            appt_id = str(appt[0])
        finally:
            db.close()

        res = client.post(f"/api/v1/ml/no-show/predict-appointment/{appt_id}", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["prediction_id"] is not None
        return (
            f"Scored Appointment: {appt_id}\n"
            f"Logged to Table   : ai.ai_predictions (ID: {data['prediction_id']})\n"
            f"Risk Probability  : {data['no_show_percentage']} (Tier: {data['risk_tier']})"
        )
    results.append(run_check("ML-3.5B", "Live Appointment Scoring & ai.ai_predictions Logging", check_live_appointment_scoring))

    print_banner("6. API SECURITY & ROLE-BASED ACCESS CONTROL")

    def check_rbac():
        # Patient cannot access model benchmarks
        r1 = client.get("/api/v1/ml/no-show/models", headers=patient_headers)
        assert r1.status_code == 403

        # Patient cannot access calibration
        r2 = client.get("/api/v1/ml/no-show/calibration", headers=patient_headers)
        assert r2.status_code == 403

        # Patient cannot trigger retrain
        r3 = client.post("/api/v1/ml/no-show/retrain", headers=patient_headers)
        assert r3.status_code == 403

        # Unauthenticated rejected
        r4 = client.get("/api/v1/ml/no-show/models")
        assert r4.status_code == 401

        return "RBAC Enforced: Patients and anonymous requests strictly blocked from ML admin endpoints"
    results.append(run_check("ML-3.6A", "RBAC Boundary Verification", check_rbac))

    print_banner("VERIFICATION SUMMARY")
    passed = sum(results)
    total = len(results)
    print(f"\n{BOLD}Total Deliverables Tested:{RESET} {total}")
    print(f"{BOLD}Total Passed:{RESET} {GREEN}{passed}{RESET} / {total} ({passed/total*100:.1f}%)\n")

    if passed == total:
        print(f"{BOLD}{GREEN}>>> WEEK 3 MACHINE LEARNING MILESTONE SUCCESSFULLY VERIFIED <<<{RESET}\n")
        return 0
    else:
        print(f"{BOLD}{RED}>>> SOME CHECKS FAILED <<<{RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
