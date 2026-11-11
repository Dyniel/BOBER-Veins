"""
rPPG dataset loader and synthetic benchmark generator.

Real data: UBFC-rPPG via ``vascushift.data.ubfc`` (the previous loader looked for
``ground_truth.txt`` + a pre-computed ``rgb_traces.npy`` that nothing produced, so
it always fell back to synthetic data). Synthetic sessions are labelled
``is_real=False`` and must not be reported as measured.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd


def generate_synthetic_rppg_session(
    subject_id: str = "sub-opt-01",
    duration_sec: float = 60.0,
    fs: float = 30.0,
    heart_rate_bpm: float = 68.0,
    motion_noise_amplitude: float = 0.12,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Generates a deterministic synthetic optical rPPG recording with synchronized
    reference ground-truth PPG and true HR.

    Physiological components:
      - Systolic arterial pulse peak
      - Dicrotic notch reflection wave
      - Respiratory sinus arrhythmia (modulation at ~0.25 Hz)
      - Hemoglobin absorption difference (G channel strongest absorption, R moderate, B low)
      - Realistic motion artifacts and low-frequency baseline drift
    """
    rng = np.random.RandomState(seed)
    n_samples = int(duration_sec * fs)
    t = np.arange(n_samples) / fs

    f_hr = heart_rate_bpm / 60.0
    f_resp = 0.25  # 15 breaths / min

    # Physiological pulse waveform with dicrotic notch
    cardiac_phase = 2.0 * np.pi * f_hr * t + 0.15 * np.sin(2.0 * np.pi * f_resp * t)
    pulse_fund = -np.cos(cardiac_phase)
    pulse_dicrotic = 0.35 * -np.cos(2.0 * cardiac_phase - 0.7)
    clean_bvp = pulse_fund + pulse_dicrotic

    # Skin color DC baselines: typical fair-to-medium skin tone (R=175, G=125, B=105)
    R_base = 175.0
    G_base = 125.0
    B_base = 105.0

    # AC PPG modulation depth: Delta I / I is typically ~ 0.5% to 2.5%
    # Hemoglobin absorption is highest around 540-575nm (green channel)
    ac_g = 0.020 * clean_bvp
    ac_r = 0.008 * clean_bvp
    ac_b = 0.005 * clean_bvp

    # Motion and illumination drift
    motion = motion_noise_amplitude * np.sin(2.0 * np.pi * 0.45 * t + rng.rand())
    motion += (motion_noise_amplitude * 0.5) * rng.normal(0, 1, size=n_samples)
    drift = 0.03 * np.sin(2.0 * np.pi * 0.05 * t)

    r_trace = R_base * (1.0 + ac_r + motion * 0.8 + drift)
    g_trace = G_base * (1.0 - ac_g + motion * 1.0 + drift)  # Absorption reduces reflected green
    b_trace = B_base * (1.0 + ac_b + motion * 0.9 + drift)

    rgb_traces = np.column_stack([r_trace, g_trace, b_trace])

    return {
        "subject_id": subject_id,
        "fs": fs,
        "time": t,
        "rgb_traces": rgb_traces,
        "ref_bvp": clean_bvp,
        "ref_hr_bpm": heart_rate_bpm,
        "duration_sec": duration_sec,
    }


def load_rppg_benchmark_cohort(
    data_dir: Optional[str] = None,
    n_synthetic_subjects: int = 10,
    seed: int = 42,
    source: str = "auto",
    subsets: Tuple[str, ...] = ("DATASET_2",),
    max_sessions: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Loads an optical rPPG cohort for algorithm benchmarking.

    Args:
        source: ``"ubfc"`` - real UBFC-rPPG sessions (videos under
            ``data_dir/raw/rppg/UBFC-rPPG``; RGB traces are extracted once and
            cached in ``data_dir/interim/ubfc_rgb``); ``"synthetic"`` - the
            sinusoidal benchmark generator; ``"auto"`` (default) - UBFC if at
            least one video of the requested subsets is on disk, otherwise
            synthetic (with a warning). Every session carries ``is_real``.
        subsets: UBFC sub-datasets to use (DATASET_2 is the standard benchmark).
        max_sessions: optional cap on the number of real sessions.
    """
    import warnings

    data_dir = data_dir or "data"
    cohort: List[Dict[str, Any]] = []

    if source in ("auto", "ubfc"):
        from vascushift.data.ubfc import list_ubfc_sessions, load_ubfc_session

        root = Path(data_dir) / "raw" / "rppg" / "UBFC-rPPG"
        sessions = [s for s in list_ubfc_sessions(root, subsets=subsets) if s.has_video]
        if max_sessions is not None:
            sessions = sessions[:max_sessions]
        for s in sessions:
            cohort.append(load_ubfc_session(s, cache_dir=Path(data_dir) / "interim" / "ubfc_rgb"))
        if source == "ubfc" and not cohort:
            raise FileNotFoundError(
                f"No UBFC-rPPG videos for {subsets} under {root}; run scripts/download_data.py --dataset ubfc")

    if not cohort:
        if source == "auto":
            warnings.warn("No real rPPG videos found - falling back to the SYNTHETIC rPPG cohort", RuntimeWarning,
                          stacklevel=2)
        rng = np.random.RandomState(seed)
        hr_pool = rng.uniform(55.0, 88.0, size=n_synthetic_subjects)
        noise_pool = rng.uniform(0.08, 0.22, size=n_synthetic_subjects)
        for i in range(n_synthetic_subjects):
            sess = generate_synthetic_rppg_session(
                subject_id=f"opt-bench-{i+1:02d}",
                duration_sec=40.0,
                fs=30.0,
                heart_rate_bpm=round(float(hr_pool[i]), 1),
                motion_noise_amplitude=round(float(noise_pool[i]), 3),
                seed=seed + i,
            )
            sess["is_real"] = False
            cohort.append(sess)

    return cohort
