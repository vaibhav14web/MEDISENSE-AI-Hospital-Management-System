"""
Pydantic schemas for Machine Learning (No-Show Prediction) endpoints.
Week 3 Deliverable
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NoShowPredictRequest(BaseModel):
    age: int = Field(default=42, ge=0, le=120, description="Patient age in years")
    gender: str = Field(default="Female", description="Gender (Female, Male, Other)")
    lead_time_days: float = Field(default=7.0, ge=0.0, description="Days between appointment booking and scheduled time")
    day_of_week: int = Field(default=2, ge=0, le=6, description="Day of week (0=Monday, 6=Sunday)")
    hour_of_day: int = Field(default=11, ge=7, le=20, description="Hour of the appointment (24h format)")
    prior_appointments: int = Field(default=2, ge=0, description="Total historical appointments attended/booked")
    prior_no_shows: int = Field(default=0, ge=0, description="Total past no-show absences")
    prior_cancellations: int = Field(default=0, ge=0, description="Total past patient cancellations")
    prior_no_show_rate: Optional[float] = Field(default=0.0, ge=0.0, le=1.0, description="Historical no-show percentage")
    existing_diagnoses_count: int = Field(default=1, ge=0, description="Count of active diagnoses on record")
    chronic_condition_count: int = Field(default=1, ge=0, description="Count of chronic conditions (e.g. HTN, Diabetes)")
    department_name: str = Field(default="General Medicine", description="Hospital clinic or department name")


class NoShowPredictResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    no_show_probability: float
    no_show_percentage: str
    attendance_probability: float
    risk_tier: str  # LOW, MEDIUM, HIGH
    risk_color: str
    recommended_action: str
    top_contributing_factors: List[str]
    input_features: Optional[Dict[str, Any]] = None
    model_version: str
    appointment_id: Optional[str] = None
    patient_id: Optional[str] = None
    prediction_id: Optional[str] = None


class ModelBenchmarkMetrics(BaseModel):
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    roc_auc: float
    pr_auc: float
    brier_score: float
    confusion_matrix: Dict[str, int]
    roc_curve: List[Dict[str, float]]
    pr_curve: List[Dict[str, float]]


class FeatureWeightItem(BaseModel):
    feature: str
    logistic_coef: float
    odds_ratio: float
    tree_importance: float


class ReliabilityBinItem(BaseModel):
    bin: int
    mean_predicted_prob: float
    empirical_fraction_positive: float


class SubgroupFairnessItem(BaseModel):
    group: str
    count: int
    actual_no_show_rate: float
    selection_rate: float
    fpr: float
    fnr: float
    accuracy: float
    precision: float
    recall: float


class FairnessAuditResponse(BaseModel):
    age_subgroups: List[SubgroupFairnessItem]
    gender_subgroups: List[SubgroupFairnessItem]
    summary: Dict[str, float]


class CalibrationResponse(BaseModel):
    uncalibrated_brier: float
    calibrated_brier: float
    calibration_method: str
    uncalibrated_curve: List[ReliabilityBinItem]
    calibrated_curve: List[ReliabilityBinItem]


class ModelsOverviewResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    model_name: str
    version: str
    trained_at: str
    split_method: str
    sample_size: int
    train_size: int
    test_size: int
    base_candidate: str
    calibration_method: str
    benchmark_comparison: Dict[str, ModelBenchmarkMetrics]
    db_version_id: Optional[str] = None
