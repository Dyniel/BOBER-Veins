"""
HR tracking and reference-free signal quality for rPPG (used by the "improved" optical track).

* ``window_spectrum`` - Welch spectrum restricted to the HR band
* ``spectral_quality`` - share of in-band power within ±0.1 Hz of the peak and its harmonic (0..1), no
  reference needed; used to abstain on uncertain windows
* ``viterbi_track`` - most likely HR path through consecutive window spectra with a Gaussian penalty on
  HR changes between windows (repairs isolated windows where an artefact wins the spectral peak)

Validated in docs/experiments_rppg.md (E2, E3, E8): tuned on half of UBFC DATASET_2, confirmed on the
other half, DATASET_1 and PhysioNet videopulse.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np
from scipy import signal as sps


def window_spectrum(x: np.ndarray, fs: float, f_lo: float = 0.7, f_hi: float = 3.5, nfft: int = 4096):
    f, p = sps.welch(x, fs=fs, nperseg=min(len(x), int(fs * 10)), nfft=nfft)
    m = (f >= f_lo) & (f <= f_hi)
    return f[m], p[m]


def spectral_quality(x: np.ndarray, fs: float) -> float:
    """Reference-free quality: share of in-band power within ±0.1 Hz of the spectral peak (and its harmonic)."""
    f, p = window_spectrum(x, fs)
    if p.sum() <= 0:
        return 0.0
    k = int(np.argmax(p))
    f0 = f[k]
    near = (np.abs(f - f0) <= 0.1) | (np.abs(f - 2 * f0) <= 0.1)
    return float(p[near].sum() / p.sum())


def viterbi_track(spectra: List[Tuple[np.ndarray, np.ndarray]], max_jump_bpm_per_step: float = 8.0,
                  sigma_bpm: float = 6.0) -> np.ndarray:
    """
    HR path through consecutive window spectra maximising sum(log normalised power) - jump penalty.
    Transition score: Gaussian in the HR change between windows (sigma_bpm), hard cut beyond 3x max jump.
    """
    f = spectra[0][0]
    hr_grid = f * 60.0
    n = len(spectra)
    emis = np.array([np.log(p / (p.sum() + 1e-12) + 1e-9) for _, p in spectra])  # (n, K)
    d = hr_grid[:, None] - hr_grid[None, :]
    trans = -0.5 * (d / sigma_bpm) ** 2
    trans[np.abs(d) > 3 * max_jump_bpm_per_step] = -1e9
    score = emis[0].copy()
    back = np.zeros((n, len(hr_grid)), dtype=int)
    for t in range(1, n):
        cand = score[None, :] + trans  # (to, from)
        back[t] = np.argmax(cand, axis=1)
        score = cand[np.arange(len(hr_grid)), back[t]] + emis[t]
    path = np.zeros(n, dtype=int)
    path[-1] = int(np.argmax(score))
    for t in range(n - 1, 0, -1):
        path[t - 1] = back[t, path[t]]
    return hr_grid[path]
