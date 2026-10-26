"""
Established Classical rPPG Algorithms: Green, CHROM, POS, and HR estimation.
"""

from typing import Dict, Any, Tuple
import numpy as np
from scipy import signal

from vascushift.optical.signal import bandpass_filter, normalize_signal, detrend_signal


def rppg_green(rgb_traces: np.ndarray, fs: float = 30.0) -> np.ndarray:
    """
    Green-channel baseline rPPG algorithm.
    Extracts blood volume pulse predominantly from green hemoglobin absorption.

    Args:
        rgb_traces: Array of shape (N_frames, 3) representing [R, G, B].
        fs: Sampling frame rate in Hz.

    Returns:
        1D filtered rPPG pulse signal.
    """
    g = rgb_traces[:, 1]
    g_norm = (g / (np.mean(g) + 1e-8)) - 1.0
    g_detrend = detrend_signal(g_norm)
    g_filtered = bandpass_filter(g_detrend, fs=fs)
    return normalize_signal(g_filtered)


def rppg_chrom(rgb_traces: np.ndarray, fs: float = 30.0) -> np.ndarray:
    """
    Chrominance-based rPPG method (de Haan & Jeanne, IEEE TBME 2013).
    Constructs color difference signals Xs and Ys to cancel specular motion artifacts.

    Xs = 3 * Rn - 2 * Gn
    Ys = 1.5 * Rn + Gn - 1.5 * Bn
    S = Xs - (std(Xs) / std(Ys)) * Ys
    """
    R = rgb_traces[:, 0]
    G = rgb_traces[:, 1]
    B = rgb_traces[:, 2]

    # Temporal normalization
    Rn = R / (np.mean(R) + 1e-8)
    Gn = G / (np.mean(G) + 1e-8)
    Bn = B / (np.mean(B) + 1e-8)

    Xs = 3.0 * Rn - 2.0 * Gn
    Ys = 1.5 * Rn + Gn - 1.5 * Bn

    Xs_filt = bandpass_filter(detrend_signal(Xs), fs=fs)
    Ys_filt = bandpass_filter(detrend_signal(Ys), fs=fs)

    std_y = np.std(Ys_filt)
    alpha = np.std(Xs_filt) / (std_y + 1e-8)
    pulse = Xs_filt - alpha * Ys_filt
    return normalize_signal(pulse)


def rppg_pos(
    rgb_traces: np.ndarray,
    fs: float = 30.0,
    window_sec: float = 1.6,
) -> np.ndarray:
    """
    Plane-Orthogonal-to-Skin (POS) method (Wang et al., IEEE TBME 2017).
    Projects normalized RGB into plane orthogonal to skin-tone vector.
    """
    N = len(rgb_traces)
    win_len = int(window_sec * fs)
    if win_len % 2 != 0:
        win_len += 1

    H = np.zeros(N)
    for m in range(0, N - win_len + 1):
        C = rgb_traces[m : m + win_len, :]
        mean_C = np.mean(C, axis=0) + 1e-8
        Cn = C / mean_C  # Shape (win_len, 3)

        # Projections
        S1 = Cn[:, 1] - Cn[:, 2]                       # G - B
        S2 = Cn[:, 1] + Cn[:, 2] - 2.0 * Cn[:, 0]      # G + B - 2R

        std_s2 = np.std(S2)
        alpha = np.std(S1) / (std_s2 + 1e-8)
        h = S1 + alpha * S2
        h_norm = h - np.mean(h)
        H[m : m + win_len] += h_norm

    pulse = bandpass_filter(H, fs=fs)
    return normalize_signal(pulse)


def estimate_heart_rate(
    rppg_sig: np.ndarray,
    fs: float = 30.0,
    low_hr_bpm: float = 42.0,
    high_hr_bpm: float = 210.0,
) -> Tuple[float, float, Tuple[np.ndarray, np.ndarray]]:
    """
    Estimates dominant pulse frequency (BPM) from rPPG time-series using Welch PSD
    and parabolic sub-bin interpolation.

    Returns:
        (hr_bpm, peak_power, (frequencies_hz, psd))
    """
    nperseg = min(len(rppg_sig), int(fs * 10))
    freqs, psd = signal.welch(rppg_sig, fs=fs, nperseg=nperseg, nfft=2048)

    # Convert physiological HR limits to Hz
    f_min = low_hr_bpm / 60.0
    f_max = high_hr_bpm / 60.0

    mask = (freqs >= f_min) & (freqs <= f_max)
    if np.sum(mask) == 0:
        return 72.0, 0.0, (freqs, psd)

    sub_freqs = freqs[mask]
    sub_psd = psd[mask]

    peak_idx = np.argmax(sub_psd)
    best_freq = sub_freqs[peak_idx]

    # Parabolic sub-bin interpolation for frequency refinement
    if 0 < peak_idx < len(sub_psd) - 1:
        alpha = sub_psd[peak_idx - 1]
        beta = sub_psd[peak_idx]
        gamma = sub_psd[peak_idx + 1]
        denom = 2.0 * (2.0 * beta - alpha - gamma)
        if abs(denom) > 1e-12:
            delta = (gamma - alpha) / denom
            df = sub_freqs[1] - sub_freqs[0]
            best_freq += delta * df

    hr_bpm = best_freq * 60.0
    peak_power = float(sub_psd[peak_idx])
    return float(hr_bpm), peak_power, (freqs, psd)

