"""
Optical rPPG Benchmarking Experiment.
Evaluates Green, CHROM, and POS against reference ground-truth PPG and heart rate.
"""

from typing import Dict, Any, List
import numpy as np

from vascushift.data.rppg_loader import load_rppg_benchmark_cohort
from vascushift.optical.algorithms import (
    rppg_green,
    rppg_chrom,
    rppg_pos,
    estimate_heart_rate,
)
from vascushift.optical.quality import compute_rppg_snr, evaluate_window_quality
from vascushift.evaluation.metrics import compute_regression_metrics


def run_rppg_benchmark_experiment(
    data_dir: str = "data",
    n_synthetic_subjects: int = 12,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Executes rPPG algorithm evaluation across Green, CHROM, and POS algorithms.
    """
    cohort = load_rppg_benchmark_cohort(
        data_dir=data_dir,
        n_synthetic_subjects=n_synthetic_subjects,
        seed=seed,
    )

    methods = ["green", "chrom", "pos"]
    method_funcs = {
        "green": rppg_green,
        "chrom": rppg_chrom,
        "pos": rppg_pos,
    }

    results = {m: {"est_hrs": [], "ref_hrs": [], "snrs": [], "valid_windows": 0, "total_windows": 0} for m in methods}
    sample_signals = {}

    for sess_idx, session in enumerate(cohort):
        fs = session["fs"]
        rgb = session["rgb_traces"]
        ref_hr = session["ref_hr_bpm"]

        for m in methods:
            func = method_funcs[m]
            pulse = func(rgb, fs=fs)
            est_hr, _, _ = estimate_heart_rate(pulse, fs=fs)
            is_valid, snr_db = evaluate_window_quality(pulse, hr_bpm=est_hr, fs=fs)

            results[m]["est_hrs"].append(est_hr)
            results[m]["ref_hrs"].append(ref_hr)
            results[m]["snrs"].append(snr_db)
            results[m]["total_windows"] += 1
            if is_valid:
                results[m]["valid_windows"] += 1

            if sess_idx == 0:
                sample_signals[m] = pulse[: int(fs * 10)].tolist()  # 10s sample

    # Reference signal for session 0
    ref_sample = cohort[0]["ref_bvp"][: int(cohort[0]["fs"] * 10)].tolist()

    benchmark_summary = {}
    for m in methods:
        refs = np.array(results[m]["ref_hrs"])
        ests = np.array(results[m]["est_hrs"])
        snrs = np.array(results[m]["snrs"])

        metrics = compute_regression_metrics(refs, ests)
        coverage = round(results[m]["valid_windows"] / results[m]["total_windows"] * 100.0, 1)

        benchmark_summary[m] = {
            "mae": metrics["mae"],
            "rmse": metrics["rmse"],
            "pearson_r": metrics["pearson_r"],
            "mean_snr_db": round(float(np.mean(snrs)), 2),
            "coverage_pct": coverage,
            "sample_signal": sample_signals.get(m, []),
            "ref_sample": ref_sample,
            "est_hrs": ests.tolist(),
            "ref_hrs": refs.tolist(),
        }

    return benchmark_summary

