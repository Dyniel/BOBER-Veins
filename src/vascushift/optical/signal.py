"""
Signal processing, detrending, and filtering for rPPG time-series.
"""

from typing import Tuple, List
import numpy as np
from scipy import signal


def detrend_signal(sig: np.ndarray) -> np.ndarray:
    """Removes linear trend from 1D signal."""
    return signal.detrend(sig, type="linear")


def bandpass_filter(
    sig: np.ndarray,
    fs: float = 30.0,
    low_cutoff_hz: float = 0.7,
    high_cutoff_hz: float = 3.5,
    order: int = 3,
) -> np.ndarray:
    """
    Applies zero-phase Butterworth bandpass filter to preserve human pulse frequencies.
    Default range [0.7, 3.5] Hz corresponds to 42 to 210 BPM.
    """
    nyquist = 0.5 * fs
    low = low_cutoff_hz / nyquist
    high = min(0.99, high_cutoff_hz / nyquist)
    b, a = signal.butter(order, [low, high], btype="bandpass")
    # Use filtfilt for zero phase distortion
    if len(sig) <= 3 * max(len(a), len(b)):
        return sig - np.mean(sig)
    return signal.filtfilt(b, a, sig)


def normalize_signal(sig: np.ndarray) -> np.ndarray:
    """Standardizes signal to zero mean and unit standard deviation."""
    std = np.std(sig)
    if std < 1e-8:
        return np.zeros_like(sig)
    return (sig - np.mean(sig)) / std


def window_signal(
    sig: np.ndarray,
    fs: float,
    window_sec: float = 10.0,
    stride_sec: float = 2.0,
) -> List[np.ndarray]:
    """Slices a 1D time-series into overlapping windows."""
    win_len = int(window_sec * fs)
    step = int(stride_sec * fs)
    n_samples = len(sig)
    windows = []
    for start in range(0, n_samples - win_len + 1, step):
        windows.append(sig[start : start + win_len])
    return windows

