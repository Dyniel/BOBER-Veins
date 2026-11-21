"""
"Improved" optical track (EXPERIMENTAL): the best rPPG variant found in docs/experiments_rppg.md, chosen on
half of UBFC DATASET_2 (TUNE) and confirmed once on the other half + DATASET_1 (HOLDOUT).

    ROI      face box re-detected every 15 frames but linearly INTERPOLATED between detections (removes the
             fps/15 step artefact of the baseline box), whole box with the YCrCb skin mask
             -> needs the per-frame ROI cache from ``scripts/run_roi_variants.py`` (~5 min for 50 videos)
    pulse    POS (repo implementation, 1.6 s windows)
    HR       Viterbi tracking over 10 s / 2 s window spectra, sigma = 10 bpm per step
    quality  reference-free spectral quality; ``abstain`` = below the TUNE 10 % quantile

The frozen baseline (vascushift.optical.benchmark) is NOT changed by this module.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from vascushift.optical.algorithms import rppg_pos
from vascushift.optical.benchmark import hr_bpm, reference_pulse, window_bounds
from vascushift.optical.tracking import spectral_quality, viterbi_track, window_spectrum

CONFIG = {"roi_variant": "interp15|fullbox", "method": "pos", "tracker": "viterbi", "sigma_bpm": 10.0,
          "window_s": 10.0, "stride_s": 2.0, "min_valid": 0.9, "abstain_tune_quantile": 0.10}


def split_of(session_id: str, subset: str) -> str:
    """TUNE = DATASET_2 even subject numbers; HOLDOUT = DATASET_2 odd + all DATASET_1 (docs/experiments_rppg.md)."""
    if subset == "DATASET_1":
        return "holdout"
    m = re.search(r"subject(\d+)", session_id)
    return "tune" if m and int(m.group(1)) % 2 == 0 else "holdout"


def sessions_for_roi_variant(variant: str, data_dir: Path = Path("data"), only_split: Optional[str] = None) -> List[Dict]:
    """Uniform-grid sessions built from the E6 per-frame traces of one ROI variant (same alignment as the loader)."""
    from vascushift.data.ubfc import align_to_uniform_grid, frame_clock, list_ubfc_sessions, load_ubfc_ground_truth, video_info

    out = []
    for us in list_ubfc_sessions(data_dir / "raw" / "rppg" / "UBFC-rPPG"):
        sp = split_of(us.session_id, us.subset)
        if only_split and sp != only_split:
            continue
        f = data_dir / "interim" / "roi_variants" / f"{us.session_id}.npz"
        if not f.exists():
            continue
        z = np.load(f)
        names = list(z["names"])
        rgb = z["rgb"][:, names.index(variant), :].astype(float)
        n = len(rgb)
        t_all, keep, clock = frame_clock(us, n, video_info(us.video_path)["fps"])
        face = np.all(np.isfinite(rgb), axis=1)
        if clock == "gt_frame_clock":
            ppg = np.loadtxt(us.gt_path)[0][:n][keep]
            t_ppg = t_all[keep]
        else:
            gt = load_ubfc_ground_truth(us)
            t_ppg, ppg = gt.t, gt.ppg
        g = align_to_uniform_grid(t_all[keep], rgb[keep], face[keep], t_ppg, ppg, fs_out=30.0)
        out.append({"session_id": us.session_id, "subset": us.subset, "split": sp, "fs": 30.0, "rgb_traces": g["rgb"],
                    "ref_bvp": g["ppg"], "valid": g["valid"], "face_found": g["face_found"]})
    return out


def run_rppg_improved(data_dir: Path = Path("data"), out_dir: Path = Path("reports/rppg_improved"),
                      config: Optional[Dict] = None, verbose: bool = True) -> Dict:
    cfg = {**CONFIG, **(config or {})}
    data_dir, out_dir = Path(data_dir), Path(out_dir)
    cache = data_dir / "interim" / "roi_variants"
    if not cache.exists() or not any(cache.glob("*.npz")):
        msg = "ROI cache missing - run `python scripts/run_roi_variants.py` (~5 min) to enable the improved track"
        if verbose:
            print(f"  [rppg_improved] skipped: {msg}")
        return {"available": False, "reason": msg}
    sessions = sessions_for_roi_variant(cfg["roi_variant"], data_dir)
    rows = []
    for s in sessions:
        fs = s["fs"]
        pulse = rppg_pos(s["rgb_traces"], fs=fs)
        ref = reference_pulse(s["ref_bvp"], fs)
        wins = window_bounds(len(pulse), fs, (cfg["window_s"], cfg["stride_s"]))
        base_est = [hr_bpm(pulse[a:b], fs) for a, b in wins]
        est = viterbi_track([window_spectrum(pulse[a:b], fs) for a, b in wins], sigma_bpm=cfg["sigma_bpm"]) \
            if len(wins) > 1 else base_est
        for (a, b), e, e0 in zip(wins, est, base_est):
            r = hr_bpm(ref[a:b], fs)
            rows.append({"dataset": "ubfc_rppg", "session_id": s["session_id"], "subset": s["subset"], "split": s["split"],
                         "t_start_s": round(a / fs, 3), "hr_ref_bpm": round(r, 3), "hr_est_bpm": round(float(e), 3),
                         "error_bpm": round(float(e) - r, 3), "hr_est_untracked_bpm": round(float(e0), 3),
                         "quality": round(spectral_quality(pulse[a:b], fs), 4),
                         "fraction_valid": round(float(np.mean(s["valid"][a:b])), 4),
                         "provenance": "raw_individual"})
    w = pd.DataFrame(rows)
    w["included"] = w["fraction_valid"] >= cfg["min_valid"]
    thr = float(w[w.included & (w.split == "tune")]["quality"].quantile(cfg["abstain_tune_quantile"]))
    w["abstain"] = w["quality"] < thr
    out_dir.mkdir(parents=True, exist_ok=True)
    w.to_csv(out_dir / "windows.csv", index=False)

    def stats(g: pd.DataFrame) -> Dict:
        e = g["error_bpm"].abs()
        return {"n_sessions": int(g.session_id.nunique()), "n_windows": int(len(g)), "mae_bpm": round(float(e.mean()), 3),
                "rmse_bpm": round(float(np.sqrt((g.error_bpm ** 2).mean())), 3),
                "within5_pct": round(float((e <= 5).mean() * 100), 2), "gross10_pct": round(float((e > 10).mean() * 100), 2)}

    inc = w[w.included]
    summary = []
    for key, g in [("all", inc), *[(f"split={k}", v) for k, v in inc.groupby("split")],
                   *[(f"subset={k}", v) for k, v in inc.groupby("subset")],
                   *[(f"holdout,subset={k}", v) for k, v in inc[inc.split == "holdout"].groupby("subset")]]:
        kept = g[~g.abstain]
        summary.append({"group": key, **stats(g), "abstain_kept_pct": round(len(kept) / len(g) * 100, 1),
                        **{f"abstain_{k}": v for k, v in stats(kept).items() if k in ("mae_bpm", "within5_pct", "gross10_pct")}})
    baseline_summary = []
    bw = Path(out_dir).parent / "rppg_baseline" / "windows.csv"
    if bw.exists():  # same groups, frozen baseline POS, for a like-for-like comparison
        b = pd.read_csv(bw)
        b = b[(b.protocol == "w10s2") & (b.method == "pos") & b.included].copy()
        b["split"] = [split_of(x, sub) for x, sub in zip(b.session_id, b.subset)]
        for key, g in [("all", b), *[(f"split={k}", v) for k, v in b.groupby("split")],
                       *[(f"subset={k}", v) for k, v in b.groupby("subset")],
                       *[(f"holdout,subset={k}", v) for k, v in b[b.split == "holdout"].groupby("subset")]]:
            baseline_summary.append({"group": key, **stats(g)})
    res = {"available": True, "status": "EXPERIMENTAL - chosen on TUNE half, confirmed on HOLDOUT (docs/experiments_rppg.md)",
           "config": cfg, "abstain_quality_threshold": round(thr, 4), "summary": summary,
           "baseline_pos_summary": baseline_summary}
    (out_dir / "summary.json").write_text(json.dumps(res, indent=2))
    pd.DataFrame(summary).to_csv(out_dir / "summary.csv", index=False)
    if verbose:
        print(pd.DataFrame(summary).to_string(index=False))
    return res
