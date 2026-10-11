"""
Demographic and Subgroup Fairness Evaluation.
Week 3: Step 3.3
Evaluates error rates (FPR, FNR, selection rate) across age brackets and genders.
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix


def assign_age_bracket(age: int) -> str:
    if age < 18:
        return "< 18"
    elif age <= 35:
        return "18 - 35"
    elif age <= 50:
        return "36 - 50"
    elif age <= 65:
        return "51 - 65"
    else:
        return "65+"


def evaluate_subgroup_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
    """
    Computes confusion matrix rates for a single subgroup.
    """
    total = len(y_true)
    if total == 0:
        return {
            "count": 0,
            "actual_no_show_rate": 0.0,
            "selection_rate": 0.0,
            "fpr": 0.0,
            "fnr": 0.0,
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
        }

    actual_positives = int(np.sum(y_true == 1))
    predicted_positives = int(np.sum(y_pred == 1))
    actual_negatives = total - actual_positives

    # TN, FP, FN, TP
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    fpr = (fp / actual_negatives) if actual_negatives > 0 else 0.0
    fnr = (fn / actual_positives) if actual_positives > 0 else 0.0
    precision = (tp / predicted_positives) if predicted_positives > 0 else 0.0
    recall = (tp / actual_positives) if actual_positives > 0 else 0.0
    accuracy = (tp + tn) / total

    return {
        "count": total,
        "actual_no_show_rate": round(actual_positives / total, 4),
        "selection_rate": round(predicted_positives / total, 4),
        "fpr": round(fpr, 4),
        "fnr": round(fnr, 4),
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
    }


def analyze_fairness(
    test_df: pd.DataFrame,
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> Dict[str, Any]:
    """
    Performs comprehensive subgroup fairness audit across age brackets and genders.
    """
    df = test_df.copy()
    df["y_true"] = y_true
    df["y_pred"] = y_pred

    # Age brackets
    df["age_bracket"] = df["age"].apply(assign_age_bracket)
    age_brackets_order = ["< 18", "18 - 35", "36 - 50", "51 - 65", "65+"]
    age_analysis = []
    
    for bracket in age_brackets_order:
        sub = df[df["age_bracket"] == bracket]
        if len(sub) > 0:
            metrics = evaluate_subgroup_metrics(sub["y_true"].values, sub["y_pred"].values)
            metrics["group"] = bracket
            age_analysis.append(metrics)

    # Gender brackets
    gender_analysis = []
    for g in df["gender"].unique():
        sub = df[df["gender"] == g]
        if len(sub) > 0:
            metrics = evaluate_subgroup_metrics(sub["y_true"].values, sub["y_pred"].values)
            metrics["group"] = str(g)
            gender_analysis.append(metrics)

    # Calculate Disparities
    # Demographic Parity Ratio (min selection rate / max selection rate)
    sel_rates_gender = [g["selection_rate"] for g in gender_analysis if g["count"] >= 5]
    sel_rates_age = [a["selection_rate"] for a in age_analysis if a["count"] >= 5]

    def calc_ratio(rates):
        if not rates or max(rates) == 0:
            return 1.0
        return round(min(rates) / max(rates), 4)

    # Equalized Odds: max FPR difference
    fprs_gender = [g["fpr"] for g in gender_analysis if g["count"] >= 5]
    fnrs_gender = [g["fnr"] for g in gender_analysis if g["count"] >= 5]

    return {
        "age_subgroups": age_analysis,
        "gender_subgroups": gender_analysis,
        "summary": {
            "gender_demographic_parity_ratio": calc_ratio(sel_rates_gender),
            "age_demographic_parity_ratio": calc_ratio(sel_rates_age),
            "gender_fpr_disparity": round(max(fprs_gender) - min(fprs_gender), 4) if fprs_gender else 0.0,
            "gender_fnr_disparity": round(max(fnrs_gender) - min(fnrs_gender), 4) if fnrs_gender else 0.0,
        }
    }
