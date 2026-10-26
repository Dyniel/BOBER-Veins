"""
Data preprocessing, cross-validation partitioning, and synthetic cohort generation.
"""

from typing import List, Tuple, Generator, Dict, Any, Optional
import numpy as np
import pandas as pd


def get_subject_grouped_splits(
    df: pd.DataFrame,
    subject_col: str = "subject_id",
) -> List[Tuple[pd.DataFrame, pd.DataFrame, str]]:
    """
    Generates Leave-One-Subject-Out (LOSO) cross-validation splits.
    Guarantees that no measurements from the test subject appear in the training split.

    Returns:
        List of tuples: (train_df, test_df, held_out_subject_id)
    """
    subjects = sorted(df[subject_col].unique())
    splits = []
    for held_out in subjects:
        train_df = df[df[subject_col] != held_out].copy().reset_index(drop=True)
        test_df = df[df[subject_col] == held_out].copy().reset_index(drop=True)
        splits.append((train_df, test_df, str(held_out)))
    return splits


def generate_synthetic_physiological_cohort(
    n_subjects: int = 30,
    gravity_levels: Optional[List[float]] = None,
    noise_sigma: float = 0.05,
    missing_rate: float = 0.0,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generates a controlled synthetic physiological cohort based on the two-compartment
    hydrostatic-collapsible vein physics model.
    Used for identifiability, parameter recoverability, and sensitivity analysis.

    Ground truth parameters per subject:
      - A0: Maximum jugular vein lumen area in microgravity (mm2) ~ [80, 140]
      - k: Venous compliance steepness (1/mmHg) ~ [0.20, 0.40]
      - P0: Transmural transition inflection pressure (mmHg) ~ [2.0, 5.0]
      - CVP: Central venous pressure (mmHg) ~ [4.0, 8.0]
      - delta_h: Heart to neck vertical distance (m) ~ [0.30, 0.40]
    """
    rng = np.random.RandomState(seed)
    if gravity_levels is None:
        gravity_levels = [0.0, 0.16, 0.25, 0.38, 0.50, 0.75, 1.0]

    rho = 1060.0  # kg/m3
    g0 = 9.80665  # m/s2
    pa_to_mmhg = 0.00750062

    records = []
    for s in range(n_subjects):
        sub_id = f"synth-{s+1:03d}"
        A0 = rng.uniform(85.0, 135.0)
        k = rng.uniform(0.20, 0.35)
        P0 = rng.uniform(2.5, 4.5)
        cvp = rng.uniform(4.5, 7.5)
        delta_h = rng.uniform(0.32, 0.38)
        Amin = rng.uniform(4.0, 8.0)

        for gz in gravity_levels:
            # Hydrostatic pressure drop: dP = rho * gz * g0 * delta_h (in mmHg)
            delta_P_hydro = (rho * (gz * g0) * delta_h) * pa_to_mmhg

            # Local venous pressure: P_ijv = max(0.5, cvp - delta_P_hydro * 0.75)
            # The 0.75 factor accounts for systemic venous return redistribution
            p_ijv_true = cvp - delta_P_hydro * 0.75
            p_ijv_meas = max(0.2, p_ijv_true + rng.normal(0, noise_sigma * 5.0))

            # Sigmoidal compliance law for collapsible vein:
            # Area = Amin + (A0 - Amin) / (1 + exp(-k * (P - P0)))
            area_true = Amin + (A0 - Amin) / (1.0 + np.exp(-k * (p_ijv_meas - P0)))
            area_meas = max(2.0, area_true * (1.0 + rng.normal(0, noise_sigma)))

            # Simulate optional missing values
            if missing_rate > 0.0 and rng.rand() < missing_rate:
                area_meas = np.nan

            records.append({
                "subject_id": sub_id,
                "gz": gz,
                "posture": "seated" if gz > 0.0 else "supine",
                "IJV_area_mm2": round(area_meas, 3) if not np.isnan(area_meas) else np.nan,
                "IJV_pressure_mmHg": round(p_ijv_meas, 3),
                "true_A0": round(A0, 3),
                "true_k": round(k, 4),
                "true_P0": round(P0, 3),
                "true_CVP": round(cvp, 3),
                "true_delta_h": round(delta_h, 3),
                "provenance": "synthetic_mechanistic_ground_truth",
            })

    return pd.DataFrame(records)

