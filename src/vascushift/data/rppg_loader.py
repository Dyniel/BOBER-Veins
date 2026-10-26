"""
rPPG Dataset Loader and Benchmarking Dataset Generator.
Supports public UBFC-rPPG / PURE formats and deterministic synthetic pulse recordings.
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
) -> List[Dict[str, Any]]:
    """
    Loads or generates an optical rPPG cohort for algorithm benchmarking.
    If real UBFC-rPPG folders exist in `data_dir/raw/rppg/`, parses them.
    Otherwise, generates a standardized subject-independent benchmark cohort.
    """
    cohort = []
    rppg_path = Path(data_dir or "data") / "raw" / "rppg"

    # Check for real datasets
    if rppg_path.exists():
        sub_dirs = [d for d in rppg_path.iterdir() if d.is_dir()]
        for sd in sub_dirs:
            # Check for UBFC-rPPG format: vid.avi + ground_truth.txt
            gt_file = sd / "ground_truth.txt"
            if gt_file.exists():
                try:
                    # UBFC ground_truth.txt has 3 rows: Trace, HR, Time
                    gt_data = np.loadtxt(gt_file)
                    if gt_data.ndim == 2 and gt_data.shape[0] >= 2:
                        ref_bvp = gt_data[0]
                        ref_hr = float(np.mean(gt_data[1]))
                        # If RGB traces cached:
                        rgb_file = sd / "rgb_traces.npy"
                        if rgb_file.exists():
                            rgb_traces = np.load(rgb_file)
                            cohort.append({
                                "subject_id": sd.name,
                                "fs": 30.0,
                                "rgb_traces": rgb_traces,
                                "ref_bvp": ref_bvp,
                                "ref_hr_bpm": ref_hr,
                                "is_real": True,
                            })
                except Exception:
                    pass

    # If no real data found, generate reproducible benchmark cohort
    if len(cohort) == 0:
        rng = np.random.RandomState(seed)
        # Rates from 52 to 92 BPM covering physiological resting and elevated HR
        hr_pool = rng.uniform(55.0, 88.0, size=n_synthetic_subjects)
        noise_pool = rng.uniform(0.08, 0.22, size=n_synthetic_subjects)

        for i in range(n_synthetic_subjects):
            sub_id = f"opt-bench-{i+1:02d}"
            sess = generate_synthetic_rppg_session(
                subject_id=sub_id,
                duration_sec=40.0,
                fs=30.0,
                heart_rate_bpm=round(float(hr_pool[i]), 1),
                motion_noise_amplitude=round(float(noise_pool[i]), 3),
                seed=seed + i,
            )
            sess["is_real"] = False
            cohort.append(sess)

    return cohort

