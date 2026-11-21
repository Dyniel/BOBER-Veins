"""
Windowed rPPG benchmark on preprocessed REAL sessions (common optical format).

Protocol (fixed before looking at the results, see docs/rppg_baseline.md):

1. Each method (Green, CHROM, POS) is applied to the whole session RGB trace on the uniform 30 Hz
   grid (filters see the full signal, as in rPPG-Toolbox's unsupervised evaluation).
2. The reference is the contact finger PPG of the same session, detrended and band-passed with the
   same 0.7-3.5 Hz filter. Reference and estimate go through the SAME HR estimator
   (``estimate_heart_rate``: Welch peak in 42-210 bpm + parabolic refinement), so estimator bias
   cancels.
3. HR is compared per window. Protocols: ``whole`` (one window = the whole recording), ``w30s15``
   (30 s windows, 15 s stride) and ``w10s2`` (10 s / 2 s, the repo's configs/rppg.yaml).
4. A window is excluded if less than ``min_valid`` (90 %) of its samples are measured (dropped-frame
   holes, no face). Exclusions are kept in the table with a reason.
5. Statistics are reported per subset (UBFC DATASET_1 and DATASET_2 differ in protocol) with a
   session-level cluster bootstrap 95 % CI for MAE (windows of one session are not independent).

The output never mixes synthetic and real sessions: ``provenance`` is carried on every row.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

from vascushift.data.schema import RPPG_WINDOW_COLUMNS, conform_columns
from vascushift.optical.algorithms import estimate_heart_rate, rppg_chrom, rppg_green, rppg_pos
from vascushift.optical.quality import compute_rppg_snr
from vascushift.optical.signal import bandpass_filter, detrend_signal

METHODS: Dict[str, Callable] = {"green": rppg_green, "chrom": rppg_chrom, "pos": rppg_pos}
PROTOCOLS: Dict[str, Optional[Tuple[float, float]]] = {"whole": None, "w30s15": (30.0, 15.0), "w10s2": (10.0, 2.0)}
HR_RANGE_BPM = (42.0, 210.0)


def reference_pulse(ppg: np.ndarray, fs: float) -> np.ndarray:
    return bandpass_filter(detrend_signal(np.asarray(ppg, dtype=float)), fs=fs)


def hr_bpm(x: np.ndarray, fs: float) -> float:
    return estimate_heart_rate(x, fs=fs, low_hr_bpm=HR_RANGE_BPM[0], high_hr_bpm=HR_RANGE_BPM[1])[0]


def window_bounds(n: int, fs: float, spec: Optional[Tuple[float, float]]) -> List[Tuple[int, int]]:
    if spec is None:
        return [(0, n)]
    w, st = int(round(spec[0] * fs)), int(round(spec[1] * fs))
    return [(a, a + w) for a in range(0, n - w + 1, st)]


def evaluate_session(
    session: Dict,
    methods: Dict[str, Callable] = METHODS,
    protocols: Dict[str, Optional[Tuple[float, float]]] = PROTOCOLS,
    min_valid: float = 0.9,
) -> List[Dict]:
    """All window rows (``RPPG_WINDOW_COLUMNS``) of one session for every method x protocol."""
    fs = float(session["fs"])
    rgb = np.asarray(session["rgb_traces"], dtype=float)
    valid = np.asarray(session.get("valid", np.ones(len(rgb), bool)), dtype=bool)
    ref = reference_pulse(session["ref_bvp"], fs)
    pulses = {m: f(rgb, fs=fs) for m, f in methods.items()}
    base = {"dataset": session.get("dataset"), "session_id": session.get("session_id", session.get("subject_id")),
            "subset": session.get("subset"),
            "provenance": "raw_individual" if session.get("is_real", False) else "synthetic"}
    rows = []
    for proto, spec in protocols.items():
        for a, b in window_bounds(len(rgb), fs, spec):
            fv = float(valid[a:b].mean())
            hr_ref = hr_bpm(ref[a:b], fs)
            reason = "" if fv >= min_valid else "dropped_frames_or_no_face"
            for m, p in pulses.items():
                hr_est = hr_bpm(p[a:b], fs)
                rows.append({**base, "protocol": proto, "method": m, "t_start_s": round(a / fs, 3),
                             "t_end_s": round(b / fs, 3), "hr_ref_bpm": round(hr_ref, 3),
                             "hr_est_bpm": round(hr_est, 3), "error_bpm": round(hr_est - hr_ref, 3),
                             "snr_db": round(compute_rppg_snr(p[a:b], hr_ref / 60.0, fs=fs), 3),
                             "fraction_valid": round(fv, 4), "included": not reason, "exclusion_reason": reason})
    return rows


def _cluster_bootstrap_mae(df: pd.DataFrame, n_boot: int = 2000, seed: int = 0) -> Tuple[float, float]:
    """95 % CI of window MAE, resampling whole sessions (windows within a session are correlated)."""
    per = df.groupby("session_id")["error_bpm"].agg(lambda e: (np.abs(e).sum(), len(e)))
    sums = np.array([v[0] for v in per])
    counts = np.array([v[1] for v in per])
    if len(sums) < 2:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(sums), size=(n_boot, len(sums)))
    maes = sums[idx].sum(1) / counts[idx].sum(1)
    return float(np.percentile(maes, 2.5)), float(np.percentile(maes, 97.5))


def summarize(windows: pd.DataFrame, group_cols=("subset", "protocol", "method")) -> pd.DataFrame:
    """Metrics per group over included windows: MAE (+ session-bootstrap CI), RMSE, MAPE, r, bias, LoA, acc@5."""
    out = []
    for key, g in windows.groupby(list(group_cols)):
        inc = g[g["included"]]
        e = inc["error_bpm"].to_numpy(float)
        ref = inc["hr_ref_bpm"].to_numpy(float)
        est = inc["hr_est_bpm"].to_numpy(float)
        lo, hi = _cluster_bootstrap_mae(inc)
        bias, sd = (float(e.mean()), float(e.std(ddof=1))) if len(e) > 1 else (float("nan"), float("nan"))
        out.append({**dict(zip(group_cols, key)),
                    "n_sessions": int(inc["session_id"].nunique()), "n_windows": int(len(inc)),
                    "n_excluded": int((~g["included"]).sum()),
                    "mae_bpm": round(float(np.abs(e).mean()), 3), "mae_ci_low": round(lo, 3), "mae_ci_high": round(hi, 3),
                    "rmse_bpm": round(float(np.sqrt((e ** 2).mean())), 3),
                    "mape_pct": round(float((np.abs(e) / ref).mean() * 100), 2),
                    "pearson_r": round(float(np.corrcoef(ref, est)[0, 1]), 4) if len(e) > 2 and est.std() > 0 else float("nan"),
                    "bias_bpm": round(bias, 3), "loa_low_bpm": round(bias - 1.96 * sd, 3), "loa_high_bpm": round(bias + 1.96 * sd, 3),
                    "acc_within_5bpm_pct": round(float((np.abs(e) <= 5).mean() * 100), 1),
                    "median_snr_db": round(float(inc["snr_db"].median()), 2)})
    return pd.DataFrame(out)


def run_rppg_baseline(
    processed_dir: Path = Path("data/processed/rppg"),
    out_dir: Path = Path("reports/rppg_baseline"),
    methods: Dict[str, Callable] = METHODS,
    protocols: Dict[str, Optional[Tuple[float, float]]] = PROTOCOLS,
    min_valid: float = 0.9,
    subsets: Iterable[str] = ("DATASET_2", "DATASET_1"),
    verbose: bool = True,
) -> Dict:
    """Runs the benchmark over every preprocessed session and writes windows.csv, summary.csv/.json/.md."""
    from vascushift.data.preprocess import load_optical_index, load_optical_session

    processed_dir, out_dir = Path(processed_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    index = load_optical_index(processed_dir)
    index = index[index["subset"].isin(list(subsets))]
    rows = []
    for _, r in index.iterrows():
        rows += evaluate_session(load_optical_session(processed_dir / r["file"]), methods, protocols, min_valid)
    windows = conform_columns(pd.DataFrame(rows), RPPG_WINDOW_COLUMNS)
    windows.to_csv(out_dir / "windows.csv", index=False)
    summary = summarize(windows)
    summary.to_csv(out_dir / "summary.csv", index=False)

    whole = windows[(windows["protocol"] == "whole")].pivot_table(
        index=["session_id", "subset"], columns="method", values="error_bpm").reset_index()
    whole = whole.merge(index[["session_id", "ref_hr_bpm", "fraction_valid", "fps_video_mean", "max_frame_step_s",
                               "no_face_display"]], on="session_id", how="left")
    whole.to_csv(out_dir / "sessions_whole_recording_errors.csv", index=False)

    result = {
        "protocol": {"methods": list(methods), "protocols": {k: v for k, v in protocols.items()},
                     "min_valid_fraction": min_valid, "hr_range_bpm": HR_RANGE_BPM,
                     "reference": "contact PPG, same band-pass and HR estimator as rPPG", "grid_fs_hz": 30.0},
        "data": {"dataset": "UBFC-rPPG", "n_sessions": int(index.shape[0]),
                 "sessions_per_subset": index["subset"].value_counts().to_dict(), "provenance": "raw_individual"},
        "summary": summary.to_dict(orient="records"),
    }
    (out_dir / "summary.json").write_text(json.dumps(result, indent=2, default=float))
    (out_dir / "summary.md").write_text(format_summary_md(summary))
    if verbose:
        print(format_summary_md(summary))
    return result


def format_summary_md(summary: pd.DataFrame) -> str:
    lines = ["| Subset | Protocol | Method | Sessions | Windows (excl.) | MAE [bpm] (95% CI) | RMSE | MAPE % | r | Bias [LoA] | ≤5 bpm % | SNR dB |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in summary.sort_values(["subset", "protocol", "mae_bpm"]).iterrows():
        lines.append(f"| {r.subset} | {r.protocol} | {r.method} | {r.n_sessions} | {r.n_windows} ({r.n_excluded}) | "
                     f"{r.mae_bpm:.2f} ({r.mae_ci_low:.2f}–{r.mae_ci_high:.2f}) | {r.rmse_bpm:.2f} | {r.mape_pct:.1f} | "
                     f"{r.pearson_r:.3f} | {r.bias_bpm:+.2f} [{r.loa_low_bpm:+.1f}, {r.loa_high_bpm:+.1f}] | "
                     f"{r.acc_within_5bpm_pct:.1f} | {r.median_snr_db:.1f} |")
    return "\n".join(lines) + "\n"
