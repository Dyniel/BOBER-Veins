"""
Experiments on improving the real-data rPPG baseline (UBFC-rPPG). NOT part of the baseline.

Protocol (fixed before running any variant):
* Same windows as the baseline 10 s / 2 s protocol, same reference (finger PPG, same filter + HR estimator),
  same exclusion rule (< 90 % valid samples).
* Split to avoid tuning on the test set: TUNE = DATASET_2 subjects with an even number (21 people);
  HOLDOUT = DATASET_2 odd subjects (21) + all of DATASET_1 (8 recordings). Variants are compared on TUNE;
  the chosen ones are confirmed on HOLDOUT. Unsupervised methods have few free parameters, but picking the
  best of many variants on one set is still optimistic, hence the split.
* Every run is appended to reports/experiments/rppg/runs.csv with its parameters.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import signal as sps

from vascushift.optical.benchmark import hr_bpm, reference_pulse, window_bounds

OUT = Path("reports/experiments/rppg")


def split_of(session_id: str, subset: str) -> str:
    if subset == "DATASET_1":
        return "holdout"
    m = re.search(r"subject(\d+)", session_id)
    return "tune" if m and int(m.group(1)) % 2 == 0 else "holdout"


def load_sessions(processed_dir: Path = Path("data/processed/rppg")) -> List[Dict]:
    from vascushift.data.preprocess import load_optical_index, load_optical_session

    idx = load_optical_index(processed_dir)
    out = []
    for _, r in idx.iterrows():
        s = load_optical_session(processed_dir / r["file"])
        s["split"] = split_of(s["session_id"], s["subset"])
        out.append(s)
    return out


from vascushift.optical.tracking import spectral_quality, viterbi_track, window_spectrum  # noqa: E402,F401


# ------------------------------------------------------------------------------- evaluation
def evaluate(sessions: List[Dict], pulse_fn: Callable[[Dict], np.ndarray], name: str,
             window: Tuple[float, float] = (10.0, 2.0), min_valid: float = 0.9, tracker: Optional[str] = None,
             tracker_kw: Optional[Dict] = None, params: Optional[Dict] = None, save: bool = True) -> pd.DataFrame:
    """Window table for one variant. ``tracker='viterbi'`` replaces per-window argmax by the Viterbi path."""
    rows = []
    for s in sessions:
        fs = float(s["fs"])
        pulse = pulse_fn(s)
        ref = reference_pulse(s["ref_bvp"], fs)
        valid = np.asarray(s["valid"], bool)
        wins = window_bounds(len(pulse), fs, window)
        est = [hr_bpm(pulse[a:b], fs) for a, b in wins]
        if tracker == "viterbi" and len(wins) > 1:
            est = list(viterbi_track([window_spectrum(pulse[a:b], fs) for a, b in wins], **(tracker_kw or {})))
        for (a, b), e in zip(wins, est):
            fv = float(valid[a:b].mean())
            r = hr_bpm(ref[a:b], fs)
            rows.append({"variant": name, "session_id": s["session_id"], "subset": s["subset"], "split": s["split"],
                         "t_start_s": a / fs, "hr_ref": r, "hr_est": float(e), "error": float(e) - r,
                         "quality": spectral_quality(pulse[a:b], fs), "included": fv >= min_valid})
    df = pd.DataFrame(rows)
    if save:
        summ = summarize(df)
        OUT.mkdir(parents=True, exist_ok=True)
        log = OUT / "runs.csv"
        summ.insert(0, "params", json.dumps(params or {}, sort_keys=True))
        summ.insert(0, "window", f"{window[0]:g}/{window[1]:g}")
        summ.insert(0, "time", time.strftime("%Y-%m-%d %H:%M"))
        summ.to_csv(log, mode="a", header=not log.exists(), index=False)
    return df


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    d = df[df["included"]]
    for (v, sp), g in d.groupby(["variant", "split"]):
        e = g["error"].abs()
        out.append({"variant": v, "split": sp, "n_sessions": g["session_id"].nunique(), "n_windows": len(g),
                    "mae": round(float(e.mean()), 3), "rmse": round(float(np.sqrt((g["error"] ** 2).mean())), 3),
                    "within5_pct": round(float((e <= 5).mean() * 100), 2),
                    "gross_gt10_pct": round(float((e > 10).mean() * 100), 2),
                    "median_ae": round(float(e.median()), 3)})
    return pd.DataFrame(out)


def coverage_curve(df: pd.DataFrame, quantiles=(0.0, 0.05, 0.1, 0.2, 0.3)) -> pd.DataFrame:
    """Abstain on the least confident windows: MAE vs share of windows kept (threshold set on TUNE only)."""
    d = df[df["included"]]
    tune = d[d["split"] == "tune"]
    rows = []
    for q in quantiles:
        thr = float(tune["quality"].quantile(q)) if q > 0 else -np.inf
        for sp, g in d.groupby("split"):
            k = g[g["quality"] >= thr]
            e = k["error"].abs()
            rows.append({"variant": d["variant"].iloc[0], "drop_quantile": q, "threshold": thr, "split": sp,
                         "kept_pct": round(len(k) / len(g) * 100, 1), "mae": round(float(e.mean()), 3),
                         "within5_pct": round(float((e <= 5).mean() * 100), 2)})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------- E4: more pulse methods
def _bp_norm(x: np.ndarray, fs: float) -> np.ndarray:
    from vascushift.optical.signal import bandpass_filter, normalize_signal

    return normalize_signal(bandpass_filter(sps.detrend(np.asarray(x, float)), fs=fs))


def method_lgi(rgb: np.ndarray, fs: float) -> np.ndarray:
    """Local Group Invariance (Pilz et al., CVPRW 2018), whole-signal projection."""
    X = (rgb / rgb.mean(axis=0)).T  # (3, N)
    U, _, _ = np.linalg.svd(X, full_matrices=False)
    s = U[:, :1]
    Y = (np.eye(3) - s @ s.T) @ X
    return _bp_norm(Y[1], fs)


def method_omit(rgb: np.ndarray, fs: float) -> np.ndarray:
    """Orthogonal Matrix Image Transformation (Casado & Lopez, 2023): QR instead of SVD."""
    X = (rgb / rgb.mean(axis=0)).T
    Q, _ = np.linalg.qr(X)
    s = Q[:, :1]
    Y = (np.eye(3) - s @ s.T) @ X
    return _bp_norm(Y[1], fs)


def method_pbv(rgb: np.ndarray, fs: float) -> np.ndarray:
    """Blood-volume pulse signature (de Haan & van Leest, Physiol Meas 2014), whole signal."""
    from vascushift.optical.signal import bandpass_filter

    C = rgb / rgb.mean(axis=0)
    C = np.column_stack([bandpass_filter(sps.detrend(C[:, k]), fs=fs) for k in range(3)]).T  # (3, N)
    pbv = C.std(axis=1) / np.sqrt((C.var(axis=1)).sum())
    Q = C @ C.T
    W = np.linalg.solve(Q + 1e-9 * np.eye(3), pbv)
    return _bp_norm(C.T @ W / (pbv @ W), fs)


def method_chrom_windowed(rgb: np.ndarray, fs: float, win_s: float = 1.6) -> np.ndarray:
    """CHROM as published (de Haan & Jeanne 2013): per-window alpha, Hann-weighted overlap-add (50 %)."""
    from vascushift.optical.signal import bandpass_filter

    n = len(rgb)
    w = int(round(win_s * fs))
    w += w % 2
    hann = np.hanning(w)
    out = np.zeros(n)
    for a in range(0, n - w + 1, w // 2):
        seg = rgb[a:a + w] / rgb[a:a + w].mean(axis=0)
        xs = 3 * seg[:, 0] - 2 * seg[:, 1]
        ys = 1.5 * seg[:, 0] + seg[:, 1] - 1.5 * seg[:, 2]
        xf, yf = bandpass_filter(xs, fs=fs), bandpass_filter(ys, fs=fs)
        alpha = xf.std() / (yf.std() + 1e-9)
        s = xf - alpha * yf
        out[a:a + w] += hann * (s - s.mean())
    return _bp_norm(out, fs)


def method_pos_win(rgb: np.ndarray, fs: float, win_s: float = 1.6) -> np.ndarray:
    from vascushift.optical.algorithms import rppg_pos

    return rppg_pos(rgb, fs=fs, window_sec=win_s)


# E6 sessions: built by vascushift.optical.improved.sessions_for_roi_variant
from vascushift.optical.improved import sessions_for_roi_variant  # noqa: E402,F401


# ------------------------------------------------------------------------------- E9: motion regression
def sessions_with_motion(variant: str = "interp15|fullbox", data_dir: Path = Path("data"),
                         only_split: Optional[str] = None) -> List[Dict]:
    """Sessions of one ROI variant plus face-box motion signals (cx, cy, w of the every-frame EMA track) on the same grid."""
    from vascushift.data.ubfc import align_to_uniform_grid, frame_clock, list_ubfc_sessions, video_info
    from vascushift.experiments.roi_variants import box_tracks

    base = {s["session_id"]: s for s in sessions_for_roi_variant(variant, data_dir, only_split)}
    for us in list_ubfc_sessions(data_dir / "raw" / "rppg" / "UBFC-rPPG"):
        if us.session_id not in base:
            continue
        z = np.load(data_dir / "interim" / "roi_variants" / f"{us.session_id}.npz")
        tr = box_tracks(z["raw_boxes"].astype(float))["every_ema"]
        mot = np.column_stack([tr[:, 0] + tr[:, 2] / 2, tr[:, 1] + tr[:, 3] / 2, tr[:, 2]])
        n = len(mot)
        t_all, keep, _ = frame_clock(us, n, video_info(us.video_path)["fps"])
        g = align_to_uniform_grid(t_all[keep], mot[keep], np.ones(keep.sum(), bool), t_all[keep], np.zeros(keep.sum()), fs_out=30.0)
        m = g["rgb"]
        s = base[us.session_id]
        k = min(len(m), len(s["rgb_traces"]))
        s["motion"] = m[:k]
        for key in ("rgb_traces", "ref_bvp", "valid", "face_found"):
            s[key] = s[key][:k]
    return list(base.values())


def pos_motion_regressed(s: Dict, lags=(0,)) -> np.ndarray:
    """POS on RGB with the band-passed face-box motion (and optional lagged copies) regressed out per channel."""
    from vascushift.optical.algorithms import rppg_pos
    from vascushift.optical.signal import bandpass_filter

    fs = s["fs"]
    rgb = np.asarray(s["rgb_traces"], float)
    mean = rgb.mean(axis=0)
    cn = rgb / mean - 1.0
    X = []
    for c in range(s["motion"].shape[1]):
        mv = bandpass_filter(sps.detrend(s["motion"][:, c]), fs=fs)
        for lag in lags:
            X.append(np.roll(mv, lag))
    X = np.column_stack(X + [np.ones(len(cn))])
    res = np.empty_like(cn)
    for c in range(3):
        y = bandpass_filter(sps.detrend(cn[:, c]), fs=fs)
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        res[:, c] = cn[:, c] - X[:, :-1] @ beta[:-1]
    return rppg_pos((1.0 + res) * mean, fs=fs)


# ------------------------------------------------------------------------------- E12: multi-region fusion
def evaluate_fused(region_sessions: Dict[str, List[Dict]], name: str, weighting: str = "quality",
                   tracker: Optional[str] = "viterbi", sigma_bpm: float = 10.0, window=(10.0, 2.0),
                   min_valid: float = 0.9, power: float = 2.0) -> pd.DataFrame:
    """POS per face region, window spectra combined (normalised, weighted by quality**power or equally), then HR."""
    from vascushift.optical.algorithms import rppg_pos

    regions = list(region_sessions)
    by_id = {r: {s["session_id"]: s for s in region_sessions[r]} for r in regions}
    rows = []
    for sid, s0 in by_id[regions[0]].items():
        fs = s0["fs"]
        pulses = {r: rppg_pos(by_id[r][sid]["rgb_traces"], fs=fs) for r in regions if sid in by_id[r]}
        ref = reference_pulse(s0["ref_bvp"], fs)
        n = min(len(p) for p in pulses.values())
        wins = window_bounds(n, fs, window)
        fused, quals = [], []
        for a, b in wins:
            acc, wsum, f = None, 0.0, None
            qs = []
            for p in pulses.values():
                f, pw = window_spectrum(p[a:b], fs)
                q = spectral_quality(p[a:b], fs)
                qs.append(q)
                w = q ** power if weighting == "quality" else 1.0
                pw = pw / (pw.sum() + 1e-12)
                acc = w * pw if acc is None else acc + w * pw
                wsum += w
            fused.append((f, acc / max(wsum, 1e-12)))
            quals.append(float(np.max(qs)))
        if tracker == "viterbi" and len(fused) > 1:
            est = viterbi_track(fused, sigma_bpm=sigma_bpm)
        else:
            est = [float(f[np.argmax(p)] * 60) for f, p in fused]
        for (a, b), e, q in zip(wins, est, quals):
            r = hr_bpm(ref[a:b], fs)
            rows.append({"variant": name, "session_id": sid, "subset": s0["subset"], "split": s0["split"],
                         "t_start_s": a / fs, "hr_ref": r, "hr_est": float(e), "error": float(e) - r, "quality": q,
                         "included": float(np.mean(s0["valid"][a:b])) >= min_valid})
    return pd.DataFrame(rows)
