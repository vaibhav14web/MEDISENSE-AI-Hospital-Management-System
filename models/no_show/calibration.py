"""
Probability calibration, Brier score evaluation, and reliability curve generation.
Week 3: Step 3.3
"""

from typing import Dict, Any, List, Tuple
import numpy as np
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import brier_score_loss


def compute_reliability_curve(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 8) -> List[Dict[str, float]]:
    """
    Computes empirical bin statistics for a reliability diagram.
    """
    prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=n_bins, strategy="uniform")
    
    # Calculate sample counts per bin
    bin_edges = np.linspace(0, 1, n_bins + 1)
    bin_assignments = np.digitize(y_prob, bin_edges) - 1
    bin_assignments = np.clip(bin_assignments, 0, n_bins - 1)
    
    curve_data = []
    for i in range(len(prob_true)):
        curve_data.append({
            "bin": i + 1,
            "mean_predicted_prob": round(float(prob_pred[i]), 4),
            "empirical_fraction_positive": round(float(prob_true[i]), 4),
        })
    return curve_data


def calibrate_and_compare(
    estimator,
    X_train,
    y_train,
    X_test,
    y_test,
) -> Dict[str, Any]:
    """
    Fits and compares Platt scaling (Sigmoid) and Isotonic regression calibrations.
    Returns metrics and calibrated models.
    """
    # Uncalibrated baseline on test set
    raw_probs = estimator.predict_proba(X_test)[:, 1] if hasattr(estimator, "predict_proba") else estimator.predict(X_test)
    raw_brier = brier_score_loss(y_test, raw_probs)
    raw_curve = compute_reliability_curve(y_test, raw_probs)

    # Sigmoid (Platt Scaling)
    cal_sigmoid = CalibratedClassifierCV(estimator=estimator, method="sigmoid", cv=5)
    cal_sigmoid.fit(X_train, y_train)
    sig_probs = cal_sigmoid.predict_proba(X_test)[:, 1]
    sig_brier = brier_score_loss(y_test, sig_probs)
    sig_curve = compute_reliability_curve(y_test, sig_probs)

    # Isotonic Regression
    cal_isotonic = CalibratedClassifierCV(estimator=estimator, method="isotonic", cv=5)
    cal_isotonic.fit(X_train, y_train)
    iso_probs = cal_isotonic.predict_proba(X_test)[:, 1]
    iso_brier = brier_score_loss(y_test, iso_probs)
    iso_curve = compute_reliability_curve(y_test, iso_probs)

    # Pick best based on lowest Brier score
    if sig_brier <= iso_brier:
        best_name = "Platt Scaling (Sigmoid)"
        best_calibrator = cal_sigmoid
        best_brier = sig_brier
        best_curve = sig_curve
    else:
        best_name = "Isotonic Regression"
        best_calibrator = cal_isotonic
        best_brier = iso_brier
        best_curve = iso_curve

    return {
        "uncalibrated_brier": round(float(raw_brier), 4),
        "uncalibrated_curve": raw_curve,
        "sigmoid_brier": round(float(sig_brier), 4),
        "sigmoid_curve": sig_curve,
        "isotonic_brier": round(float(iso_brier), 4),
        "isotonic_curve": iso_curve,
        "best_method": best_name,
        "best_brier": round(float(best_brier), 4),
        "best_curve": best_curve,
        "best_calibrated_model": best_calibrator,
    }
