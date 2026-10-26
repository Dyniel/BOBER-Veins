"""
Quantitative scientific evaluation metrics for regression, physical consistency, and rPPG.
"""

from typing import Dict, Any, Tuple, Optional
import numpy as np


def compute_regression_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> Dict[str, float]:
    """
    Computes standard regression evaluation metrics:
      - MAE: Mean Absolute Error
      - RMSE: Root Mean Squared Error
      - R2: Coefficient of determination
      - Pearson_r: Linear correlation coefficient
      - MAPE: Mean Absolute Percentage Error (%)
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = (~np.isnan(y_true)) & (~np.isnan(y_pred))
    yt = y_true[mask]
    yp = y_pred[mask]

    if len(yt) < 2:
        return {"mae": np.nan, "rmse": np.nan, "r2": np.nan, "pearson_r": np.nan, "mape": np.nan}

    err = yp - yt
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err**2)))

    ss_res = np.sum(err**2)
    ss_tot = np.sum((yt - np.mean(yt))**2)
    r2 = float(1.0 - (ss_res / (ss_tot + 1e-12)))

    # Pearson correlation
    std_t = np.std(yt)
    std_p = np.std(yp)
    if std_t > 1e-8 and std_p > 1e-8:
        corr = float(np.corrcoef(yt, yp)[0, 1])
    else:
        corr = 0.0

    # MAPE
    nonzero = np.abs(yt) > 1e-3
    if np.sum(nonzero) > 0:
        mape = float(np.mean(np.abs(err[nonzero] / yt[nonzero])) * 100.0)
    else:
        mape = np.nan

    return {
        "mae": round(mae, 3),
        "rmse": round(rmse, 3),
        "r2": round(r2, 4),
        "pearson_r": round(corr, 4),
        "mape": round(mape, 2),
    }


def compute_physical_constraint_violations(
    gz: np.ndarray,
    predicted_area: np.ndarray,
    predicted_pressure: Optional[np.ndarray] = None,
    min_area: float = 2.0,
    max_area: float = 250.0,
) -> Dict[str, Any]:
    """
    Quantifies violations of physical laws:
      1. Area non-negativity and bounds: A in [min_area, max_area]
      2. Pressure non-negativity: P >= 0
      3. Gravitational monotonicity: d(Area)/d(gz) <= 0 (in upright posture, area must decrease with G)
    """
    gz = np.asarray(gz, dtype=float)
    pred_a = np.asarray(predicted_area, dtype=float)

    bound_violations = int(np.sum((pred_a < min_area) | (pred_a > max_area)))

    press_violations = 0
    if predicted_pressure is not None:
        pred_p = np.asarray(predicted_pressure, dtype=float)
        press_violations = int(np.sum(pred_p < 0.0))

    # Monotonicity check
    monotonicity_violations = 0
    if len(gz) > 1:
        sort_idx = np.argsort(gz)
        sorted_a = pred_a[sort_idx]
        diffs = sorted_a[1:] - sorted_a[:-1]
        monotonicity_violations = int(np.sum(diffs > 1e-2))

    total_violations = bound_violations + press_violations + monotonicity_violations
    return {
        "total_violations": total_violations,
        "bound_violations": bound_violations,
        "press_violations": press_violations,
        "monotonicity_violations": monotonicity_violations,
        "is_physically_consistent": (total_violations == 0),
    }


def compute_relative_improvement(metric_model: float, metric_baseline: float) -> float:
    """Computes percentage improvement of model error relative to baseline."""
    if metric_baseline == 0.0:
        return 0.0
    return round(float((metric_baseline - metric_model) / metric_baseline * 100.0), 2)
