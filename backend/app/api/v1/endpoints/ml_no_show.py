"""
FastAPI endpoints for Machine Learning (Appointment No-Show Prediction).
Week 3: Steps 3.1, 3.2, 3.3
"""

import os
import json
from typing import Any, List, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.rbac import get_current_user, require_staff, RoleChecker
from app.db.session import get_db
from app.models.auth import User
from app.schemas.ml import (
    NoShowPredictRequest,
    NoShowPredictResponse,
    ModelsOverviewResponse,
    FeatureWeightItem,
    CalibrationResponse,
    FairnessAuditResponse,
)

# Import ML inference and pipeline
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

from models.no_show.predict import NoShowPredictor, META_ARTIFACT_PATH
from models.no_show.pipeline import train_and_evaluate_pipeline

router = APIRouter()
predictor = NoShowPredictor()


def get_metadata() -> Dict[str, Any]:
    if not os.path.exists(META_ARTIFACT_PATH):
        # Auto-train if first run
        train_and_evaluate_pipeline()
    with open(META_ARTIFACT_PATH, "r") as f:
        return json.load(f)


@router.get("/models", response_model=ModelsOverviewResponse)
def get_models_overview(
    current_user: User = Depends(require_staff),
) -> Any:
    """
    Returns benchmark comparison of all candidate models (Dummy Prior,
    Logistic Regression, and XGBoost Trees), including ROC-AUC, PR-AUC,
    Brier Score, and training metadata.
    """
    meta = get_metadata()
    return ModelsOverviewResponse(
        model_name=meta.get("model_name", "AppointmentNoShowPredictor"),
        version=meta.get("version", "v1.0"),
        trained_at=meta.get("trained_at", ""),
        split_method=meta.get("split_method", "temporal"),
        sample_size=meta.get("sample_size", 0),
        train_size=meta.get("train_size", 0),
        test_size=meta.get("test_size", 0),
        base_candidate=meta.get("base_candidate", "xgboost_trees"),
        calibration_method=meta.get("calibration_method", "Platt Scaling (Sigmoid)"),
        benchmark_comparison=meta.get("benchmark_comparison", {}),
        db_version_id=meta.get("db_version_id"),
    )


@router.get("/feature-importance", response_model=List[FeatureWeightItem])
def get_feature_importance(
    current_user: User = Depends(require_staff),
) -> Any:
    """
    Returns ranked feature importance attributes:
    - Logistic Regression coefficients & Odds Ratios (interpretable multiplicative effect)
    - Tree-based Gini / gain importance scores
    """
    meta = get_metadata()
    weights = meta.get("feature_weights", [])
    return [FeatureWeightItem(**w) for w in weights]


@router.get("/calibration", response_model=CalibrationResponse)
def get_probability_calibration(
    current_user: User = Depends(require_staff),
) -> Any:
    """
    Returns probability calibration evaluation:
    - Brier score reduction
    - Empirical vs predicted probability coordinates for reliability curves
    """
    meta = get_metadata()
    cal = meta.get("calibration", {})
    return CalibrationResponse(
        uncalibrated_brier=cal.get("uncalibrated_brier", 0.0),
        calibrated_brier=cal.get("calibrated_brier", 0.0),
        calibration_method=meta.get("calibration_method", "Platt Scaling (Sigmoid)"),
        uncalibrated_curve=cal.get("uncalibrated_curve", []),
        calibrated_curve=cal.get("calibrated_curve", []),
    )


@router.get("/fairness", response_model=FairnessAuditResponse)
def get_subgroup_fairness_audit(
    current_user: User = Depends(require_staff),
) -> Any:
    """
    Returns algorithmic fairness and demographic parity audit:
    - Age bracket breakdown (<18, 18-35, 36-50, 51-65, 65+)
    - Gender demographics
    - False Positive Rate (FPR), False Negative Rate (FNR), and selection rate disparities
    """
    meta = get_metadata()
    audit = meta.get("fairness_audit", {})
    return FairnessAuditResponse(
        age_subgroups=audit.get("age_subgroups", []),
        gender_subgroups=audit.get("gender_subgroups", []),
        summary=audit.get("summary", {}),
    )


@router.post("/predict", response_model=NoShowPredictResponse)
def predict_no_show_risk(
    payload: NoShowPredictRequest,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Simulates or predicts no-show risk for arbitrary patient/appointment features.
    Outputs calibrated probability, risk tier (LOW/MEDIUM/HIGH), risk drivers,
    and actionable clinical intervention suggestions.
    """
    try:
        result = predictor.predict_risk(payload.model_dump())
        return NoShowPredictResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error: {str(e)}",
        )


@router.post("/predict-appointment/{appointment_id}", response_model=NoShowPredictResponse)
def predict_for_database_appointment(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> Any:
    """
    Evaluates real-time no-show risk for an existing database appointment.
    Extracts chronological patient history, scores calibrated probability,
    and registers the prediction event in ai.ai_predictions.
    """
    try:
        result = predictor.predict_for_appointment(str(appointment_id), db, persist_prediction=True)
        return NoShowPredictResponse(**result)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Prediction failed: {str(e)}")


@router.post("/retrain")
def retrain_ml_pipeline(
    split_method: str = "temporal",
    current_user: User = Depends(RoleChecker(["ADMIN"])),
) -> Any:
    """
    Triggers end-to-end retraining of models, probability calibration,
    fairness auditing, artifact serialization, and registration in ai.ai_model_versions.
    Restricted to Administrator role.
    """
    try:
        new_meta = train_and_evaluate_pipeline(split_method=split_method)
        # Reload predictor with latest model
        predictor._load()
        return {
            "status": "success",
            "message": "Retrained and serialized no-show predictive pipeline successfully",
            "model_version": new_meta.get("version"),
            "db_version_id": new_meta.get("db_version_id"),
            "benchmark_summary": {
                k: {
                    "roc_auc": v.get("roc_auc"),
                    "pr_auc": v.get("pr_auc"),
                    "brier_score": v.get("brier_score"),
                }
                for k, v in new_meta.get("benchmark_comparison", {}).items()
            },
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Retraining failed: {str(e)}")
