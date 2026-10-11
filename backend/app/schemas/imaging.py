"""
Pydantic schemas for Imaging (Chest X-Ray) endpoints and diagnostic triage.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ChestXRayPredictResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    predicted_class: str = Field(..., description="'NORMAL' or 'PNEUMONIA'")
    confidence: float = Field(..., description="Prediction confidence score [0.0 - 1.0]")
    probability_pneumonia: float = Field(..., description="Estimated probability of pneumonia")
    probability_normal: float = Field(..., description="Estimated probability of normal radiograph")
    acuity_level: str = Field(..., description="'URGENT_TRIAGE' or 'ROUTINE'")
    clinical_findings: str = Field(..., description="Actionable clinical decision support findings")
    model_version: str = Field(..., description="Registered model version")
    prediction_id: Optional[str] = None
    patient_id: Optional[str] = None
    study_id: Optional[str] = None
    latency_ms: float = Field(..., description="Execution latency in milliseconds")
    gradcam_heatmap_base64: Optional[str] = Field(None, description="Base64 encoded JPEG overlay of Grad-CAM heatmap")
    image_size: Optional[List[int]] = None

class ChestXRayModelMetaResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    model_name: str
    model_type: str
    backbone: str
    version: str
    framework: str
    task: str
    dataset_reference: str
    status: str
    metrics: Dict[str, Any]
    created_at: str

class SampleCaseItem(BaseModel):
    filename: str
    relative_path: str
    true_label: str
    split: str
    sample_id: str
