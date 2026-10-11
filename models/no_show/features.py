"""
Feature engineering transformations and preprocessor pipeline.
Week 3: Step 3.1
"""

from typing import List, Tuple
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

NUMERIC_FEATURES = [
    "age",
    "lead_time_days",
    "day_of_week",
    "hour_of_day",
    "is_weekend",
    "is_afternoon",
    "prior_appointments",
    "prior_no_shows",
    "prior_cancellations",
    "prior_no_show_rate",
    "existing_diagnoses_count",
    "chronic_condition_count",
]

CATEGORICAL_FEATURES = [
    "gender",
    "department_name",
]

ALL_FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforms raw dataframe into feature-complete tabular matrix.
    """
    df = df.copy()

    # Normalize datetime timezone awareness
    sched = pd.to_datetime(df["scheduled_at"])
    if getattr(sched.dt, "tz", None) is not None:
        sched = sched.dt.tz_localize(None)

    dob = pd.to_datetime(df["date_of_birth"])
    if getattr(dob.dt, "tz", None) is not None:
        dob = dob.dt.tz_localize(None)

    booked = pd.to_datetime(df["booked_at"])
    if getattr(booked.dt, "tz", None) is not None:
        booked = booked.dt.tz_localize(None)

    # Calculate Patient Age at time of scheduled appointment
    df["age"] = ((sched - dob).dt.days // 365.25).fillna(40).astype(int)
    df["age"] = df["age"].clip(lower=0, upper=115)

    # Lead time in days
    lead_time = (sched - booked).dt.total_seconds() / 86400.0
    df["lead_time_days"] = lead_time.clip(lower=0.25, upper=120.0).round(2)

    # Timing features
    df["day_of_week"] = sched.dt.dayofweek
    df["hour_of_day"] = sched.dt.hour
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    df["is_afternoon"] = (df["hour_of_day"] >= 13).astype(int)

    # Normalizing categoricals
    df["gender"] = df["gender"].fillna("Other").astype(str)
    df["department_name"] = df["department_name"].fillna("General Medicine").astype(str)

    # Target: 1 for no_show, 0 for completed
    if "status" in df.columns:
        df["target_no_show"] = (df["status"] == "no_show").astype(int)

    return df


def filter_training_cohort(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filters appointments to finalized outcomes (completed or no_show).
    Excludes active scheduled appointments and cancelled appointments
    to ensure strict ground-truth outcome labeling.
    """
    return df[df["status"].isin(["completed", "no_show"])].copy().reset_index(drop=True)


def build_preprocessor() -> ColumnTransformer:
    """
    Returns standard scikit-learn ColumnTransformer.
    """
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )
