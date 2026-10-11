"""
Dataset extraction and historical feature computation for appointment no-show prediction.
Week 3: Step 3.1
"""

import sys
import os
from datetime import datetime, timezone
from typing import Optional
import numpy as np
import pandas as pd
from sqlalchemy import text

# Ensure backend can be imported
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_path not in sys.path:
    sys.path.append(backend_path)

from app.db.session import engine


def extract_appointment_dataset(engine_or_conn=None) -> pd.DataFrame:
    """
    Extracts raw appointment cohort joined with patient demographics,
    department details, and clinical diagnosis aggregates.
    """
    conn_obj = engine_or_conn if engine_or_conn is not None else engine

    query = text("""
        SELECT 
            a.id as appointment_id,
            a.patient_id,
            a.doctor_id,
            a.scheduled_at,
            a.created_at as booked_at,
            a.status,
            a.reason,
            p.date_of_birth,
            COALESCE(p.gender, 'Other') as gender,
            COALESCE(dept.name, 'General Medicine') as department_name,
            COALESCE(doc.specialization, 'General Practice') as specialization,
            COALESCE(diag_cnt.total_diagnoses, 0) as existing_diagnoses_count,
            COALESCE(diag_cnt.chronic_flags, 0) as chronic_condition_count
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
        ) diag_cnt ON a.patient_id = diag_cnt.patient_id
        ORDER BY a.scheduled_at ASC
    """)

    with conn_obj.connect() if hasattr(conn_obj, 'connect') else conn_obj as conn:
        df = pd.read_sql(query, conn)

    # Sort strictly by scheduled_at for temporal integrity
    df["scheduled_at"] = pd.to_datetime(df["scheduled_at"])
    df["booked_at"] = pd.to_datetime(df["booked_at"])
    df["date_of_birth"] = pd.to_datetime(df["date_of_birth"])
    df = df.sort_values(by="scheduled_at").reset_index(drop=True)

    # Compute per-patient historical tracking temporally (strictly past appointments prior to this scheduled_at)
    patient_history = {}
    prior_appts_list = []
    prior_noshows_list = []
    prior_cancels_list = []
    prior_noshow_rate_list = []

    for _, row in df.iterrows():
        pid = row["patient_id"]
        status = row["status"]

        if pid not in patient_history:
            patient_history[pid] = {"total": 0, "no_shows": 0, "cancels": 0}

        hist = patient_history[pid]
        total_prev = hist["total"]
        noshow_prev = hist["no_shows"]
        cancel_prev = hist["cancels"]

        rate = (noshow_prev / total_prev) if total_prev > 0 else 0.0

        prior_appts_list.append(total_prev)
        prior_noshows_list.append(noshow_prev)
        prior_cancels_list.append(cancel_prev)
        prior_noshow_rate_list.append(round(rate, 4))

        # Update running history AFTER recording for current event
        hist["total"] += 1
        if status == "no_show":
            hist["no_shows"] += 1
        elif status == "cancelled":
            hist["cancels"] += 1

    df["prior_appointments"] = prior_appts_list
    df["prior_no_shows"] = prior_noshows_list
    df["prior_cancellations"] = prior_cancels_list
    df["prior_no_show_rate"] = prior_noshow_rate_list

    return df
