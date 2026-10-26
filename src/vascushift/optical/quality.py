"""
Signal Quality Index (SQI) and SNR evaluation for rPPG waveforms.
"""

from typing import Tuple
import numpy as np
from scipy import signal


def compute_rppg_snr(
    sig: np.ndarray,
    peak_freq_hz: float,
    fs: float = 30.0,
    harmonic_delta_hz: float = 0.12,
) -> float:
    """
    Computes Signal-to-Noise Ratio (SNR in dB) of the pulse fundamental and 1st harmonic.
    SNR = 10 * log10( P_signal / P_noise )
    """
    freqs, psd = signal.welch(sig, fs=fs, nperseg=min(len(sig), int(fs * 10)), nfft=2048)
    in_band = (freqs >= 0.7) & (freqs <= 3.5)

    if np.sum(in_band) == 0:
        return -20.0

    # Fundamental peak region (f0 +/- delta)
    f0 = peak_freq_hz
    f1 = 2.0 * peak_freq_hz  # 1st harmonic

    sig_mask = (np.abs(freqs - f0) <= harmonic_delta_hz) | (np.abs(freqs - f1) <= harmonic_delta_hz)
    sig_mask = sig_mask & in_band
    noise_mask = in_band & (~sig_mask)

    p_sig = np.sum(psd[sig_mask])
    p_noise = np.sum(psd[noise_mask])

    if p_noise < 1e-12:
        return 30.0
    if p_sig < 1e-12:
        return -30.0

    snr_db = 10.0 * np.log10(p_sig / p_noise)
    return float(snr_db)


def evaluate_window_quality(
    sig: np.ndarray,
    hr_bpm: float,
    fs: float = 30.0,
    snr_threshold_db: float = -3.0,
) -> Tuple[bool, float]:
    """
    Evaluates whether an rPPG window meets quality thresholds for clinical reporting.
    """
    snr_db = compute_rppg_snr(sig, peak_freq_hz=hr_bpm / 60.0, fs=fs)
    is_valid = snr_db >= snr_threshold_db
    return is_valid, snr_db

