"""
Inference engine and risk categorization for appointment no-show prediction.
Week 3: Integration & Inference
"""

import os
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import joblib
import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ARTIFACTS_DIR = os.path.join(BASE_DIR, "models", "artifacts")
MODEL_ARTIFACT_PATH = os.path.join(ARTIFACTS_DIR, "no_show_model.joblib")
META_ARTIFACT_PATH = os.path.join(ARTIFACTS_DIR, "no_show_model_meta.json")

# Dynamic Risk Cutoff Configuration (Default aligned to empirical 23.3% pre-AI baseline)
try:
    from app.core.config import settings
    DEFAULT_HIGH_THRESHOLD = float(settings.ML_NO_SHOW_HIGH_THRESHOLD)
    DEFAULT_MEDIUM_THRESHOLD = float(settings.ML_NO_SHOW_MEDIUM_THRESHOLD)
except Exception:
    DEFAULT_HIGH_THRESHOLD = float(os.getenv("ML_NO_SHOW_HIGH_THRESHOLD", 0.245))
    DEFAULT_MEDIUM_THRESHOLD = float(os.getenv("ML_NO_SHOW_MEDIUM_THRESHOLD", 0.220))


class NoShowPredictor:
    """
    Production inference engine for real-time no-show probability prediction.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        meta_path: Optional[str] = None,
        high_threshold: Optional[float] = None,
        medium_threshold: Optional[float] = None,
    ):
        self.model_path = model_path or MODEL_ARTIFACT_PATH
        self.meta_path = meta_path or META_ARTIFACT_PATH
        self.high_threshold = high_threshold if high_threshold is not None else DEFAULT_HIGH_THRESHOLD
        self.medium_threshold = medium_threshold if medium_threshold is not None else DEFAULT_MEDIUM_THRESHOLD
        self.model = None
        self.meta = {}
        self._load()

    def _load(self):
        if not os.path.exists(self.model_path):
            try:
                from .pipeline import train_and_evaluate_pipeline
                train_and_evaluate_pipeline()
            except Exception as e:
                pass
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
        if os.path.exists(self.meta_path):
            with open(self.meta_path, "r") as f:
                self.meta = json.load(f)

    def is_ready(self) -> bool:
        return self.model is not None

    def predict_risk(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates calibrated risk probability, risk tier, contributing drivers,
        and recommended clinical/operational action.
        """
        if not self.is_ready():
            self._load()
            if not self.is_ready():
                raise RuntimeError("No-show prediction model artifact not found. Please train model first.")

        # Prepare single row DataFrame
        dow = int(data.get("day_of_week", 2))
        hod = int(data.get("hour_of_day", 11))
        row = {
            "age": int(data.get("age", 42)),
            "gender": str(data.get("gender", "Female")),
            "lead_time_days": float(data.get("lead_time_days", 7.0)),
            "day_of_week": dow,
            "hour_of_day": hod,
            "is_weekend": int(dow in [5, 6]),
            "is_afternoon": int(hod >= 13),
            "prior_appointments": int(data.get("prior_appointments", 2)),
            "prior_no_shows": int(data.get("prior_no_shows", 0)),
            "prior_cancellations": int(data.get("prior_cancellations", 0)),
            "prior_no_show_rate": float(data.get("prior_no_show_rate", 0.0)),
            "existing_diagnoses_count": int(data.get("existing_diagnoses_count", 1)),
            "chronic_condition_count": int(data.get("chronic_condition_count", 1)),
            "department_name": str(data.get("department_name", "General Medicine")),
        }

        # Auto-compute prior_no_show_rate if missing or 0
        if row["prior_appointments"] > 0 and row["prior_no_show_rate"] == 0.0:
            row["prior_no_show_rate"] = round(row["prior_no_shows"] / row["prior_appointments"], 4)

        df = pd.DataFrame([row])

        # Inference
        probs = self.model.predict_proba(df)[0]
        prob_no_show = float(probs[1])

        # Categorize Risk Tier (Hospital Pre-AI baseline is 23.3%)
        if prob_no_show >= self.high_threshold:
            risk_tier = "HIGH"
            tier_color = "red"
            recommended_action = "Dispatch 24h & 2h prior SMS alerts. Flag slot for dynamic overbooking buffer."
        elif prob_no_show >= self.medium_threshold:
            risk_tier = "MEDIUM"
            tier_color = "amber"
            recommended_action = "Dispatch automated SMS confirmation request 24h prior."
        else:
            risk_tier = "LOW"
            tier_color = "green"
            recommended_action = "Standard slot allocation. Regular clinical intake."

        # Compute Top Contributing Drivers
        drivers = []
        if row["prior_no_shows"] >= 2:
            drivers.append(f"Frequent historical no-show record ({row['prior_no_shows']} past no-shows)")
        elif row["prior_no_shows"] == 1:
            drivers.append("Single past appointment absence recorded")

        if row["lead_time_days"] > 14:
            drivers.append(f"Extended lead time booking ({int(row['lead_time_days'])} days in advance)")
        elif row["lead_time_days"] <= 2:
            drivers.append("Short lead time booking (typically higher attendance)")

        if row["is_afternoon"]:
            drivers.append("Afternoon appointment slot (higher clinic backlog attrition)")

        if row["prior_appointments"] == 0:
            drivers.append("First-time clinic attendee (no historical baseline)")

        if not drivers:
            drivers.append("Standard demographic and routine follow-up profile")

        return {
            "no_show_probability": round(prob_no_show, 4),
            "no_show_percentage": f"{round(prob_no_show * 100, 1)}%",
            "attendance_probability": round(1.0 - prob_no_show, 4),
            "risk_tier": risk_tier,
            "risk_color": tier_color,
            "recommended_action": recommended_action,
            "top_contributing_factors": drivers[:3],
            "input_features": row,
            "model_version": self.meta.get("version", "v1.0"),
        }

    def predict_for_appointment(
        self,
        appointment_id: str,
        db: Session,
        persist_prediction: bool = True,
    ) -> Dict[str, Any]:
        """
        Extracts features for a specific DB appointment, computes risk,
        and optionally records into ai.ai_predictions.
        """
        query = text("""
            SELECT 
                a.id, a.patient_id, a.scheduled_at, a.created_at as booked_at,
                p.date_of_birth, p.gender,
                dept.name as department_name,
                COALESCE(diag.total_diagnoses, 0) as existing_diagnoses_count,
                COALESCE(diag.chronic_flags, 0) as chronic_condition_count
            FROM hospital.appointments a
            JOIN clinical.patients p ON a.patient_id = p.id
            LEFT JOIN hospital.doctors doc ON a.doctor_id = doc.id
            LEFT JOIN hospital.departments dept ON doc.department_id = dept.id
            LEFT JOIN (
                SELECT 
                    patient_id,
                    count(*) as total_diagnoses,
                    count(case when lower(diagnosis_name) SIMILAR TO '%(hypertension|diabetes|asthma|cardio|heart|chronic|arthritis)%' then 1 end) as chronic_flags
                FROM clinical.diagnoses
                GROUP BY patient_id
            ) diag ON a.patient_id = diag.patient_id
            WHERE a.id = :appt_id
        """)

        row = db.execute(query, {"appt_id": appointment_id}).mappings().first()
        if not row:
            raise ValueError(f"Appointment {appointment_id} not found")

        # Query patient's prior appointment history
        hist_query = text("""
            SELECT
                count(*) as total_prior,
                count(case when status = 'no_show' then 1 end) as prior_noshow,
                count(case when status = 'cancelled' then 1 end) as prior_cancel
            FROM hospital.appointments
            WHERE patient_id = :patient_id
              AND scheduled_at < :sched_time
        """)
        hist_row = db.execute(hist_query, {
            "patient_id": row["patient_id"],
            "sched_time": row["scheduled_at"],
        }).mappings().first()

        prior_appts = hist_row["total_prior"] or 0
        prior_noshows = hist_row["prior_noshow"] or 0
        prior_cancels = hist_row["prior_cancel"] or 0
        prior_rate = (prior_noshows / prior_appts) if prior_appts > 0 else 0.0

        # Timing & age
        sched_at = row["scheduled_at"]
        booked_at = row["booked_at"]
        dob = row["date_of_birth"]
        age = int((sched_at.date() - dob).days // 365.25)
        lead_time = max(0.5, (sched_at - booked_at).total_seconds() / 86400.0)

        feature_input = {
            "age": age,
            "gender": row["gender"] or "Other",
            "lead_time_days": round(lead_time, 2),
            "day_of_week": sched_at.weekday(),
            "hour_of_day": sched_at.hour,
            "prior_appointments": prior_appts,
            "prior_no_shows": prior_noshows,
            "prior_cancellations": prior_cancels,
            "prior_no_show_rate": round(prior_rate, 4),
            "existing_diagnoses_count": row["existing_diagnoses_count"],
            "chronic_condition_count": row["chronic_condition_count"],
            "department_name": row["department_name"] or "General Medicine",
        }

        result = self.predict_risk(feature_input)
        result["appointment_id"] = str(appointment_id)
        result["patient_id"] = str(row["patient_id"])

        if persist_prediction:
            pred_id = str(uuid.uuid4())
            model_ver_id = self.meta.get("db_version_id")
            
            # If no version ID in meta, fetch latest from DB
            if not model_ver_id:
                ver_row = db.execute(text("SELECT id FROM ai.ai_model_versions ORDER BY created_at DESC LIMIT 1")).first()
                if ver_row:
                    model_ver_id = str(ver_row[0])

            if model_ver_id:
                ins_query = text("""
                    INSERT INTO ai.ai_predictions (
                        id, patient_id, model_version_id, prediction_type,
                        input_reference, prediction, probability, explanation,
                        is_reviewed_by_clinician, created_at
                    ) VALUES (
                        :id, :patient_id, :model_version_id, :prediction_type,
                        :input_reference, :prediction, :probability, :explanation,
                        false, :created_at
                    )
                """)
                db.execute(ins_query, {
                    "id": pred_id,
                    "patient_id": row["patient_id"],
                    "model_version_id": model_ver_id,
                    "prediction_type": "no_show_risk",
                    "input_reference": json.dumps(feature_input),
                    "prediction": json.dumps({"risk_tier": result["risk_tier"]}),
                    "probability": result["no_show_probability"],
                    "explanation": json.dumps({"factors": result["top_contributing_factors"]}),
                    "created_at": datetime.now(timezone.utc),
                })
                db.commit()
                result["prediction_id"] = pred_id

        return result
