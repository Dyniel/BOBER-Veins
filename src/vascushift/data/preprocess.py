"""
Preprocessing of the REAL datasets into the common formats of ``vascushift.data.schema``.

Optical (UBFC-rPPG)
    raw AVI + ground truth  ->  per-frame face RGB (cache, ``data/interim/ubfc_rgb``)
    ->  frame clock + uniform 30 Hz grid  ->  ``data/processed/rppg/sessions/<session_id>.npz``
    plus the index ``data/processed/rppg/sessions.csv`` (``OPTICAL_SESSION_COLUMNS``).

Physiology
    literature aggregates + PhysioNet PRCP + BHP-Lab tilt/LBNP  ->  common long format
    ``data/processed/physiology_long.csv`` (only sources whose licence allows redistribution) and
    ``data/processed/internal/physiology_long_all.csv`` (adds the public-but-unlicensed BHP-Lab
    repositories; git-ignored, team use only).

Everything here is deterministic and idempotent: re-running without ``force`` reuses outputs whose
inputs did not change (the session ``.npz`` stores the parameters it was built with).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Optional

import numpy as np
import pandas as pd

from vascushift.data.schema import (
    COMMON_PHYSIO_COLUMNS,
    OPTICAL_SESSION_COLUMNS,
    conform_columns,
)

UBFC_SOURCE = "Bobbia et al., Pattern Recognit. Lett. 124:82-90 (2019), UBFC-rPPG"
PREPROCESS_VERSION = "1"  # bump when the grid/ROI logic changes so cached sessions are rebuilt


def _session_params(fs_out: float, max_interp_gap_s: float) -> Dict:
    return {"version": PREPROCESS_VERSION, "fs_out": float(fs_out), "max_interp_gap_s": float(max_interp_gap_s)}


def preprocess_ubfc(
    data_dir: Path = Path("data"),
    out_dir: Optional[Path] = None,
    subsets: Iterable[str] = ("DATASET_2", "DATASET_1"),
    fs_out: float = 30.0,
    max_interp_gap_s: float = 0.25,
    force: bool = False,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Builds the uniform-grid session files for every downloaded UBFC-rPPG video and returns the index.

    Videos without a cached RGB trace are decoded once (~7 s each, see
    ``scripts/extract_ubfc_traces.py`` for the parallel version).
    """
    from vascushift.data.ubfc import list_ubfc_sessions, load_ubfc_ground_truth, load_ubfc_session

    data_dir = Path(data_dir)
    out_dir = Path(out_dir) if out_dir else data_dir / "processed" / "rppg"
    sess_dir = out_dir / "sessions"
    sess_dir.mkdir(parents=True, exist_ok=True)
    root = data_dir / "raw" / "rppg" / "UBFC-rPPG"
    params = _session_params(fs_out, max_interp_gap_s)

    rows = []
    for s in list_ubfc_sessions(root, subsets=tuple(subsets)):
        if not s.has_video:
            continue
        f = sess_dir / f"{s.session_id}.npz"
        meta = None
        if f.exists() and not force:
            with np.load(f, allow_pickle=False) as z:
                old = json.loads(str(z["meta_json"]))
            if old.get("params") == params:
                meta = old
        if meta is None:
            d = load_ubfc_session(s, cache_dir=data_dir / "interim" / "ubfc_rgb",
                                  fs_out=fs_out, max_interp_gap_s=max_interp_gap_s)
            gt = load_ubfc_ground_truth(s)
            fr = d["frames"]
            steps = np.diff(fr["t"])
            meta = {
                "dataset": "ubfc_rppg",
                "session_id": s.session_id,
                # UBFC gives no cross-recording identity; DATASET_2 folders are distinct people,
                # DATASET_1 recordings may repeat a person -> the session is the statistical unit.
                "subject_id": s.session_id,
                "subset": s.subset,
                "fs": float(fs_out),
                "n_samples": int(len(d["time"])),
                "duration_s": round(float(d["time"][-1]), 3),
                "fraction_valid": round(float(d["valid"].mean()), 4),
                "frame_clock": fr["clock"],
                "fps_video_mean": round((len(fr["t"]) - 1) / float(fr["t"][-1]), 3),
                "max_frame_step_s": round(float(steps.max()), 3),
                "ref_hr_bpm": round(float(d["ref_hr_bpm"]), 2),
                "hr_sensor_dropouts": int(gt.n_hr_dropouts),
                "no_face_display": bool(s.no_face_display),
                "provenance": "raw_individual",
                "source": UBFC_SOURCE,
                "params": params,
            }
            tmp = f.with_suffix(".tmp.npz")
            np.savez_compressed(
                tmp, time=d["time"].astype(np.float64), rgb=d["rgb_traces"].astype(np.float32),
                ref_ppg=d["ref_bvp"].astype(np.float32), valid=d["valid"], face_found=d["face_found"],
                meta_json=np.array(json.dumps(meta)),
            )
            tmp.replace(f)
            if verbose:
                print(f"  [preprocess] {s.session_id}: {meta['n_samples']} samples @ {fs_out:g} Hz, "
                      f"valid {meta['fraction_valid']:.3f}, ref HR {meta['ref_hr_bpm']} bpm", flush=True)
        rows.append({**{k: v for k, v in meta.items() if k != "params"},
                     "file": str(f.relative_to(out_dir))})

    index = conform_columns(pd.DataFrame(rows), OPTICAL_SESSION_COLUMNS) if rows else \
        pd.DataFrame(columns=OPTICAL_SESSION_COLUMNS)
    index.to_csv(out_dir / "sessions.csv", index=False)
    return index


def load_optical_session(path: Path) -> Dict:
    """
    Reads one preprocessed session. Returns the dict layout used by the rPPG code:
    ``fs``, ``time``, ``rgb_traces``, ``ref_bvp``, ``valid``, ``face_found`` and the metadata keys.
    """
    with np.load(Path(path), allow_pickle=False) as z:
        meta = json.loads(str(z["meta_json"]))
        out = {"time": z["time"], "rgb_traces": z["rgb"].astype(float), "ref_bvp": z["ref_ppg"].astype(float),
               "valid": z["valid"].astype(bool), "face_found": z["face_found"].astype(bool)}
    out.update({k: v for k, v in meta.items() if k != "params"})
    out["fs"] = float(meta["fs"])
    out["is_real"] = meta.get("provenance") == "raw_individual"
    return out


def load_optical_index(processed_dir: Path = Path("data/processed/rppg")) -> pd.DataFrame:
    p = Path(processed_dir) / "sessions.csv"
    if not p.exists():
        raise FileNotFoundError(f"{p} missing - run `python -m vascushift.cli preprocess` first")
    return pd.read_csv(p)


def preprocess_physiology(data_dir: Path = Path("data"), out_dir: Optional[Path] = None) -> Dict[str, Path]:
    """
    Writes the stacked physiology tables (common long format):

    * ``physiology_long.csv`` - published aggregates + PRCP (ODC-By) + BHP carotid-jugular (MIT)
    * ``internal/physiology_long_all.csv`` - the above + BHP tilt/LBNP dose-response (no licence)
    """
    from vascushift.data.schema import load_all_physiology

    data_dir = Path(data_dir)
    out_dir = Path(out_dir) if out_dir else data_dir / "processed"
    (out_dir / "internal").mkdir(parents=True, exist_ok=True)
    public = conform_columns(load_all_physiology(data_dir, include_unlicensed=False), COMMON_PHYSIO_COLUMNS)
    full = conform_columns(load_all_physiology(data_dir, include_unlicensed=True), COMMON_PHYSIO_COLUMNS)
    if (full["provenance"] == "synthetic").any():  # never happens by construction; keep the guard explicit
        raise AssertionError("synthetic rows leaked into the physiology table")
    paths = {"public": out_dir / "physiology_long.csv", "internal": out_dir / "internal" / "physiology_long_all.csv"}
    public.to_csv(paths["public"], index=False)
    full.to_csv(paths["internal"], index=False)
    return paths
