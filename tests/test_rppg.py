"""
Unit tests for optical rPPG algorithms, signal filtering, and heart-rate estimation.
"""

import numpy as np
import pytest

from vascushift.data.rppg_loader import generate_synthetic_rppg_session
from vascushift.optical.algorithms import (
    rppg_green,
    rppg_chrom,
    rppg_pos,
    estimate_heart_rate,
)
from vascushift.optical.quality import compute_rppg_snr


def test_rppg_heart_rate_recovery():
    """Ensure CHROM and POS recover true synthetic heart rate within +/- 3 BPM."""
    true_hr = 66.0
    session = generate_synthetic_rppg_session(
        duration_sec=30.0,
        fs=30.0,
        heart_rate_bpm=true_hr,
        motion_noise_amplitude=0.05,
        seed=42,
    )
    rgb = session["rgb_traces"]
    fs = session["fs"]

    pulse_chrom = rppg_chrom(rgb, fs=fs)
    est_hr_chrom, _, _ = estimate_heart_rate(pulse_chrom, fs=fs)

    pulse_pos = rppg_pos(rgb, fs=fs)
    est_hr_pos, _, _ = estimate_heart_rate(pulse_pos, fs=fs)

    assert abs(est_hr_chrom - true_hr) < 3.5
    assert abs(est_hr_pos - true_hr) < 3.5


def test_rppg_snr_metric():
    """Ensure clean synthetic pulse signal has positive SNR in dB."""
    session = generate_synthetic_rppg_session(
        duration_sec=20.0,
        fs=30.0,
        heart_rate_bpm=70.0,
        motion_noise_amplitude=0.02,
        seed=42,
    )
    pulse = rppg_pos(session["rgb_traces"], fs=30.0)
    snr_db = compute_rppg_snr(pulse, peak_freq_hz=70.0 / 60.0, fs=30.0)
    assert snr_db > 0.0

