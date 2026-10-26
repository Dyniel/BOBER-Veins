"""
Parameter Identifiability Analysis and Synthetic Optical Observation Bridge.
Evaluates parameter recoverability across noise levels and tests the hypothetical optical proxy model.
"""

from typing import Dict, Any, List, Tuple, Optional
import numpy as np

from vascushift.data.preprocessing import generate_synthetic_physiological_cohort
from vascushift.models.inverse_model import MechanisticParameterEstimator


def run_synthetic_identifiability_experiment(
    noise_levels: Optional[List[float]] = None,
    n_trials_per_noise: int = 15,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Evaluates whether known physiological ground-truth parameters (A0, k, P0, CVP)
    can be uniquely and stably recovered from noisy measurements across gravity levels.
    """
    if noise_levels is None:
        noise_levels = [0.00, 0.02, 0.05, 0.10, 0.15, 0.20]

    recovery_summary = {}

    for noise_idx, sigma in enumerate(noise_levels):
        a0_rel_errors = []
        k_rel_errors = []
        p0_abs_errors = []
        cvp_abs_errors = []

        synth_df = generate_synthetic_physiological_cohort(
            n_subjects=n_trials_per_noise,
            noise_sigma=sigma,
            seed=seed + int(sigma * 1000),
        )

        for sub_id in synth_df["subject_id"].unique():
            sdf = synth_df[synth_df["subject_id"] == sub_id]
            gz = sdf["gz"].values
            area = sdf["IJV_area_mm2"].values
            press = sdf["IJV_pressure_mmHg"].values

            true_a0 = sdf["true_A0"].iloc[0]
            true_k = sdf["true_k"].iloc[0]
            true_p0 = sdf["true_P0"].iloc[0]
            true_cvp = sdf["true_CVP"].iloc[0]

            estimator = MechanisticParameterEstimator(max_iter=350)
            try:
                estimator.fit(gz=gz, area_obs=area, pressure_obs=press)
                rec = estimator.params

                a0_rel_errors.append(abs(rec.A0 - true_a0) / true_a0 * 100.0)
                k_rel_errors.append(abs(rec.k - true_k) / true_k * 100.0)
                p0_abs_errors.append(abs(rec.P0 - true_p0))
                cvp_abs_errors.append(abs(rec.CVP - true_cvp))
            except Exception:
                continue

        recovery_summary[f"noise_{sigma:.2f}"] = {
            "noise_sigma": sigma,
            "A0_rel_err_pct": round(float(np.mean(a0_rel_errors)), 2) if a0_rel_errors else np.nan,
            "k_rel_err_pct": round(float(np.mean(k_rel_errors)), 2) if k_rel_errors else np.nan,
            "P0_abs_err": round(float(np.mean(p0_abs_errors)), 2) if p0_abs_errors else np.nan,
            "CVP_abs_err": round(float(np.mean(cvp_abs_errors)), 2) if cvp_abs_errors else np.nan,
            "n_successful_trials": len(a0_rel_errors),
        }

    return recovery_summary


def simulate_synthetic_optical_bridge(
    venous_area: np.ndarray,
    venous_pressure: np.ndarray,
    noise_sigma: float = 0.05,
    seed: int = 42,
) -> Dict[str, np.ndarray]:
    """
    Synthetic Observation Bridge (Module D).
    Hypothetical proxy relation: y_proxy = h(x_venous, theta) + epsilon
    Connects simulated venous filling to synthetic optical proxy features (e.g. facial perfusion index).

    IMPORTANT: This is explicitly labeled as a synthetic proxy model, NOT experimentally calibrated.
    """
    rng = np.random.RandomState(seed)
    A_norm = venous_area / 100.0
    P_norm = venous_pressure / 15.0

    # Hypothetical non-linear optical proxy function:
    # Perfusion pulsatility changes as venous backpressure increases
    h_optical = 0.20 + 0.65 * np.tanh(0.8 * A_norm + 0.4 * P_norm)
    noise = rng.normal(0, noise_sigma, size=len(venous_area))
    y_proxy = np.clip(h_optical + noise, 0.0, 1.5)

    return {
        "y_proxy": y_proxy,
        "clean_proxy": h_optical,
        "noise_sigma": noise_sigma,
    }

