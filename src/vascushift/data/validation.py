"""
Data validation and physiological range checks.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd


PHYSIOLOGICAL_BOUNDS = {
    "gz": (0.0, 2.0),
    "IJV_area_mm2": (1.0, 250.0),
    "IJV_pressure_mmHg": (-5.0, 45.0),
    "IVC_diameter_cm": (0.5, 3.5),
    "CCA_flow_ml_min": (200.0, 1800.0),
    "CCA_csa_cm2": (0.15, 0.70),
    "heart_rate_bpm": (35.0, 180.0),
    "mean_arterial_pressure_mmHg": (45.0, 160.0),
}


class DataQualityReport:
    """Stores data validation results and summaries."""

    def __init__(self, is_valid: bool, issues: List[str], stats: Dict[str, Any]):
        self.is_valid = is_valid
        self.issues = issues
        self.stats = stats

    def summary(self) -> str:
        status_str = "VALID" if self.is_valid else "INVALID / WARNINGS FOUND"
        lines = [f"Data Quality Status: {status_str}"]
        if self.issues:
            lines.append("Issues Identified:")
            for issue in self.issues:
                lines.append(f"  - {issue}")
        else:
            lines.append("No out-of-range anomalies identified.")
        lines.append("\nSummary Statistics:")
        for var, s in self.stats.items():
            lines.append(
                f"  {var}: N={s['count']}, mean={s['mean']:.2f}, std={s['std']:.2f}, "
                f"min={s['min']:.2f}, max={s['max']:.2f}, missing={s['missing']}"
            )
        return "\n".join(lines)


def validate_physiological_dataset(
    df: pd.DataFrame,
    strict: bool = False,
) -> DataQualityReport:
    """
    Validates a physiological venous/gravity dataset against known physical ranges
    and structure requirements.
    """
    issues = []
    stats = {}

    # Required column checks
    required_cols = ["subject_id", "gz", "posture"]
    for col in required_cols:
        if col not in df.columns:
            issues.append(f"Missing mandatory column: '{col}'")

    # Range and statistics checks
    for col in df.columns:
        if col in ["subject_id", "posture", "notes", "provenance"]:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            series = df[col].dropna()
            cnt = int(len(series))
            missing = int(df[col].isna().sum())
            if cnt > 0:
                mean_val = float(series.mean())
                std_val = float(series.std()) if cnt > 1 else 0.0
                min_val = float(series.min())
                max_val = float(series.max())
            else:
                mean_val = std_val = min_val = max_val = np.nan

            stats[col] = {
                "count": cnt,
                "missing": missing,
                "mean": mean_val,
                "std": std_val,
                "min": min_val,
                "max": max_val,
            }

            if col in PHYSIOLOGICAL_BOUNDS and cnt > 0:
                low_b, high_b = PHYSIOLOGICAL_BOUNDS[col]
                if min_val < low_b:
                    issues.append(
                        f"Variable '{col}' has value {min_val:.2f} below expected lower bound {low_b}"
                    )
                if max_val > high_b:
                    issues.append(
                        f"Variable '{col}' has value {max_val:.2f} above expected upper bound {high_b}"
                    )

    # Subject group check
    if "subject_id" in df.columns:
        n_subjects = df["subject_id"].nunique()
        if n_subjects < 2:
            issues.append(
                f"Cohort has only {n_subjects} participant(s). Multi-subject validation requires >= 2."
            )

    is_valid = len(issues) == 0 if strict else True
    return DataQualityReport(is_valid=is_valid, issues=issues, stats=stats)

