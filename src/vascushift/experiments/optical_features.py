"""
E14 - optical features beyond heart rate, validated against the finger PPG (UBFC-rPPG, real data).

Parameters fixed before running (no tuning): pulse = POS on the improved ROI (interp15 box, whole face with
skin mask); both signals band-passed 0.7-3.5 Hz on the 30 Hz grid; systolic peaks by scipy find_peaks with a
minimum distance of 0.6 x the session's median beat period and prominence > 0.3 SD, refined by parabolic
interpolation (sub-sample timing); beats matched to the nearest finger beat within 150 ms after removing the
median face-finger delay. Only beats whose neighbourhood is fully valid (no dropped-frame hole) are used.

Features:
* IBI (inter-beat interval) agreement, beat level
* HRV: RMSSD and SDNN per recording (rPPG vs finger), artefact-rejected IBIs (300-1500 ms, |dIBI| < 25 %)
* face-to-finger pulse delay: lag of maximal cross-correlation (positive = face pulse arrives first)
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd
from scipy import signal as sps

from vascushift.optical.signal import bandpass_filter


def _peaks(x: np.ndarray, fs: float) -> np.ndarray:
    x = (x - x.mean()) / (x.std() + 1e-12)
    f, p = sps.welch(x, fs=fs, nperseg=min(len(x), int(fs * 10)), nfft=4096)
    m = (f >= 0.7) & (f <= 3.5)
    period = 1.0 / f[m][np.argmax(p[m])]
    idx, _ = sps.find_peaks(x, distance=max(1, int(0.6 * period * fs)), prominence=0.3)
    t = []
    for i in idx:
        if 0 < i < len(x) - 1:
            a, b, c = x[i - 1], x[i], x[i + 1]
            den = a - 2 * b + c
            t.append((i + (0.5 * (a - c) / den if abs(den) > 1e-12 else 0.0)) / fs)
    return np.asarray(t)


def _clean_ibi(t: np.ndarray) -> np.ndarray:
    ibi = np.diff(t) * 1000.0
    ok = (ibi > 300) & (ibi < 1500)
    rel = np.abs(np.diff(ibi, prepend=ibi[:1])) / np.maximum(ibi, 1)
    return ibi[ok & (rel < 0.25)]


def hrv(t_peaks: np.ndarray) -> Dict[str, float]:
    ibi = _clean_ibi(t_peaks)
    if len(ibi) < 10:
        return {"rmssd_ms": np.nan, "sdnn_ms": np.nan, "n_ibi": len(ibi)}
    return {"rmssd_ms": float(np.sqrt(np.mean(np.diff(ibi) ** 2))), "sdnn_ms": float(np.std(ibi, ddof=1)), "n_ibi": len(ibi)}


def face_finger_delay(face: np.ndarray, finger: np.ndarray, fs: float, max_lag_s: float = 0.5) -> float:
    """Lag (s) maximising the correlation of face pulse vs finger pulse; positive = finger lags the face."""
    L = int(max_lag_s * fs)
    best, lag = -np.inf, 0
    for k in range(-L, L + 1):
        a, b = (face[: len(face) - k], finger[k:]) if k >= 0 else (face[-k:], finger[: len(finger) + k])
        c = np.corrcoef(a, b)[0, 1]
        if c > best:
            best, lag = c, k
    return lag / fs, float(best)


def evaluate_features(sessions: List[Dict], pulse_fn) -> Dict[str, pd.DataFrame]:
    sess_rows, beat_rows = [], []
    for s in sessions:
        fs = s["fs"]
        face = bandpass_filter(pulse_fn(s), fs=fs)
        finger = bandpass_filter(sps.detrend(np.asarray(s["ref_bvp"], float)), fs=fs)
        # the oximeter waveform polarity is arbitrary: flip it to correlate positively with the face pulse
        if np.corrcoef(face, finger)[0, 1] < 0 and abs(np.corrcoef(face, -finger)[0, 1]) > 0:
            lag0, c0 = face_finger_delay(face, finger, fs)
            lag1, c1 = face_finger_delay(face, -finger, fs)
            if c1 > c0:
                finger = -finger
        delay, corr = face_finger_delay(face, finger, fs)
        tf, tr = _peaks(face, fs), _peaks(finger, fs)
        valid = np.asarray(s["valid"], bool)
        ok_f = np.array([valid[max(0, int(t * fs) - 15): int(t * fs) + 15].all() for t in tf]) if len(tf) else np.array([], bool)
        tf = tf[ok_f] if len(tf) else tf
        # beat matching after removing the median delay
        matched = []
        for t in tf:
            j = np.argmin(np.abs(tr - (t + delay))) if len(tr) else None
            if j is not None and abs(tr[j] - (t + delay)) < 0.15:
                matched.append((t, tr[j]))
        m = np.array(matched)
        if len(m) > 3:
            ibi_f, ibi_r = np.diff(m[:, 0]) * 1000, np.diff(m[:, 1]) * 1000
            good = (ibi_r > 300) & (ibi_r < 1500) & (np.abs(np.diff(m[:, 1], prepend=m[0, 1])[1:] * 1000 - ibi_r) < 1e-6)
            for a, b in zip(ibi_f[good], ibi_r[good]):
                beat_rows.append({"session_id": s["session_id"], "subset": s["subset"], "ibi_face_ms": a, "ibi_finger_ms": b})
        hf, hr = hrv(tf), hrv(tr)
        sess_rows.append({"session_id": s["session_id"], "subset": s["subset"], "delay_face_to_finger_ms": delay * 1000,
                          "xcorr_max": corr, "n_face_beats": len(tf), "n_finger_beats": len(tr),
                          "match_rate": len(m) / max(1, len(tr)),
                          "rmssd_face_ms": hf["rmssd_ms"], "rmssd_finger_ms": hr["rmssd_ms"],
                          "sdnn_face_ms": hf["sdnn_ms"], "sdnn_finger_ms": hr["sdnn_ms"]})
    return {"sessions": pd.DataFrame(sess_rows), "beats": pd.DataFrame(beat_rows)}
