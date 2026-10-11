"""
FastAPI endpoints for Medical Imaging & Diagnostic Computer Vision.
Provides Chest X-Ray Pneumonia Triage, Grad-CAM Explainability, and Model Metadata.
"""

import os
import sys
import json
import uuid
from typing import Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.rbac import get_current_user, require_staff, RoleChecker
from app.db.session import get_db
from app.models.auth import User
from app.schemas.imaging import (
    ChestXRayPredictResponse,
    ChestXRayModelMetaResponse,
    SampleCaseItem,
)

# Project root path setup
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

META_PATH = os.path.join(project_root, "models", "artifacts", "chest_xray_model_meta.json")
DATA_TEST_DIR = os.path.join(project_root, "models", "imaging", "data", "chest_xray", "test")

router = APIRouter()

def get_imaging_engine():
    try:
        from models.imaging.inference import get_inference_engine
        return get_inference_engine()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Chest X-Ray model engine not initialized or still training: {str(e)}"
        )

@router.get("/model", response_model=ChestXRayModelMetaResponse)
def get_model_metadata(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Returns architecture, validation metrics (Accuracy, Sensitivity, Specificity, ROC-AUC),
    and versioning details for the active Chest X-Ray deep learning model.
    """
    if os.path.exists(META_PATH):
        with open(META_PATH, "r", encoding="utf-8") as f:
            meta = json.load(f)
        return ChestXRayModelMetaResponse(
            model_name=meta.get("model_name", "ChestXRayPneumoniaClassifier"),
            model_type=meta.get("model_type", "DeepConvolutionalNeuralNetwork"),
            backbone=meta.get("backbone", "resnet18"),
            version=meta.get("version", "v1.0"),
            framework=meta.get("framework", "PyTorch / Torchvision"),
            task=meta.get("task", "pediatric_chest_radiograph_pneumonia_classification"),
            dataset_reference=meta.get("dataset_reference", "Guangzhou Chest X-Ray Cohort"),
            status="active",
            metrics=meta.get("metrics", {}),
            created_at=meta.get("created_at", datetime.now(timezone.utc).isoformat()),
        )
    
    # Query database as fallback
    db_row = db.execute(text("""
        SELECT model_name, model_type, version, framework, task, dataset_reference, status, metrics, created_at
        FROM ai.ai_model_versions
        WHERE model_name = 'ChestXRayPneumoniaClassifier'
        ORDER BY created_at DESC LIMIT 1
    """)).fetchone()

    if not db_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chest X-Ray model has not been trained or registered yet."
        )

    return ChestXRayModelMetaResponse(
        model_name=db_row[0],
        model_type=db_row[1],
        backbone="resnet18",
        version=db_row[2],
        framework=db_row[3],
        task=db_row[4],
        dataset_reference=db_row[5],
        status=db_row[6],
        metrics=json.loads(db_row[7]) if isinstance(db_row[7], str) else (db_row[7] or {}),
        created_at=str(db_row[8]),
    )

@router.get("/samples", response_model=List[SampleCaseItem])
def list_sample_test_cases(
    current_user: User = Depends(get_current_user),
    limit_per_class: int = Query(5, ge=1, le=20),
) -> Any:
    """
    Returns curated ground-truth test samples from the evaluation set for quick clinical triage testing.
    """
    samples = []
    if not os.path.exists(DATA_TEST_DIR):
        return samples

    for label in ["NORMAL", "PNEUMONIA"]:
        class_dir = os.path.join(DATA_TEST_DIR, label)
        if os.path.exists(class_dir):
            files = [f for f in os.listdir(class_dir) if f.lower().endswith((".jpeg", ".jpg", ".png"))][:limit_per_class]
            for f in files:
                rel_path = os.path.join("models", "imaging", "data", "chest_xray", "test", label, f).replace("\\", "/")
                sample_id = f"{label.lower()}_{os.path.splitext(f)[0]}"
                samples.append(SampleCaseItem(
                    filename=f,
                    relative_path=rel_path,
                    true_label=label,
                    split="test",
                    sample_id=sample_id,
                ))
    return samples

@router.post("/predict", response_model=ChestXRayPredictResponse)
def predict_chest_xray(
    file: Optional[UploadFile] = File(None),
    sample_path: Optional[str] = Form(None),
    patient_id: Optional[str] = Form(None),
    study_id: Optional[str] = Form(None),
    include_heatmap: bool = Form(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Evaluates a Chest X-Ray radiograph for signs of Pneumonia.
    Accepts either an uploaded image file or a relative server path to a test image.
    Generates prediction probabilities, urgent clinical triage flags, and Grad-CAM explainability heatmaps.
    Persists inference in ai.ai_predictions.
    """
    engine = get_imaging_engine()

    image_input = None
    if file is not None and file.filename:
        image_input = file.file.read()
    elif sample_path:
        # Resolve path
        full_path = os.path.normpath(os.path.join(project_root, sample_path)) if not os.path.isabs(sample_path) else sample_path
        if not os.path.exists(full_path):
            raise HTTPException(status_code=400, detail=f"Sample file not found at: {sample_path}")
        image_input = full_path
    else:
        raise HTTPException(status_code=400, detail="Must provide either an uploaded file or sample_path.")

    try:
        result = engine.predict(image_input, include_heatmap=include_heatmap)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

    # Retrieve registered model version id
    model_version_id = None
    try:
        row = db.execute(text("SELECT id, version FROM ai.ai_model_versions WHERE model_name = 'ChestXRayPneumoniaClassifier' ORDER BY created_at DESC LIMIT 1")).fetchone()
        if row:
            model_version_id = row[0]
            model_ver_str = row[1]
        else:
            model_ver_str = "v1.0"
    except Exception:
        model_ver_str = "v1.0"

    prediction_id = str(uuid.uuid4())
    # Persist in ai.ai_predictions
    try:
        db.execute(text("""
            INSERT INTO ai.ai_predictions (
                id, patient_id, model_version_id, prediction_type, input_reference,
                prediction, probability, explanation, is_reviewed_by_clinician, created_at
            ) VALUES (
                :id, :patient_id, :model_version_id, 'chest_xray_pneumonia', :input_ref,
                :prediction, :prob, :explanation, FALSE, NOW()
            )
        """), {
            "id": prediction_id,
            "patient_id": patient_id if patient_id else None,
            "model_version_id": model_version_id,
            "input_ref": json.dumps({"source": file.filename if file else sample_path, "study_id": study_id}),
            "prediction": json.dumps({
                "predicted_class": result["predicted_class"],
                "acuity_level": result["acuity_level"],
                "findings": result["clinical_findings"]
            }),
            "prob": result["confidence"],
            "explanation": json.dumps({
                "probability_pneumonia": result["probability_pneumonia"],
                "probability_normal": result["probability_normal"],
                "latency_ms": result["latency_ms"],
                "has_gradcam": bool(result.get("gradcam_heatmap_base64"))
            })
        })
        db.commit()
    except Exception as e:
        print(f"Warning: Failed to persist ai.ai_predictions: {e}")

    return ChestXRayPredictResponse(
        predicted_class=result["predicted_class"],
        confidence=result["confidence"],
        probability_pneumonia=result["probability_pneumonia"],
        probability_normal=result["probability_normal"],
        acuity_level=result["acuity_level"],
        clinical_findings=result["clinical_findings"],
        model_version=model_ver_str,
        prediction_id=prediction_id,
        patient_id=patient_id,
        study_id=study_id,
        latency_ms=result["latency_ms"],
        gradcam_heatmap_base64=result.get("gradcam_heatmap_base64"),
        image_size=result.get("image_size"),
    )
