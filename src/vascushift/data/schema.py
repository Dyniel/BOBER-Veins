"""
Common long ("tidy") format for physiological measurements across datasets.

One row = one value of one variable for one subject (or "group") in one
condition. Every loader that produces physiology returns these columns, so data
from parabolic flight, ISS, tilt, LBNP and PhysioNet can be stacked with
``pd.concat`` and filtered by ``provenance``.

Columns
-------
dataset       registry key (vascushift.data.registry.DATASETS)
subject_id    dataset-prefixed subject id, or "group" for published aggregates
sex           "F" / "M" / None
condition     dataset-specific condition label (e.g. "supine_tilt_-15", "iss_fd50")
environment   ground / parabolic_flight / iss / ...
posture       seated / supine / prone / standing / head_up_tilt / head_down_tilt / free_floating
tilt_deg      body-axis angle from horizontal (+90 upright, 0 horizontal, <0 head-down); None in 0 G
gz_platform   environment acceleration in g (1 ground, 0.25 parabola, 0 ISS)
gz_body       head-to-foot component = gz_platform * sin(tilt_deg)
lbnp_mmHg     lower-body negative pressure applied (0 = none)
variable      snake_case name, side suffix _left/_right where relevant
unit          SI-ish clinical unit (mm2, mmHg, bpm, mL, L/min, cm, fraction)
stat          value | mean_ci95 | mean_sd | median_of_beats | proportion
value, ci_low, ci_high, sd, n
provenance    raw_individual | published_aggregate | synthetic
source        citation with DOI / URL (and table or file)
notes         free text (errata, caveats)
"""

from __future__ import annotations

import math
from typing import Optional

import pandas as pd

COMMON_PHYSIO_COLUMNS = [
    "dataset", "subject_id", "sex", "condition", "environment", "posture", "tilt_deg",
    "gz_platform", "gz_body", "lbnp_mmHg", "variable", "unit", "stat", "value", "ci_low", "ci_high",
    "sd", "n", "provenance", "source", "notes",
]

PROVENANCE_LEVELS = ("raw_individual", "published_aggregate", "synthetic")


def gz_body_from_tilt(tilt_deg: Optional[float], gz_platform: float = 1.0) -> Optional[float]:
    if tilt_deg is None or (isinstance(tilt_deg, float) and math.isnan(tilt_deg)):
        return None
    return round(gz_platform * math.sin(math.radians(tilt_deg)), 4)


def conform(df: pd.DataFrame) -> pd.DataFrame:
    """Adds missing common columns (as None) and orders them; validates provenance."""
    df = df.copy()
    for c in COMMON_PHYSIO_COLUMNS:
        if c not in df.columns:
            df[c] = None
    bad = set(df["provenance"].dropna()) - set(PROVENANCE_LEVELS)
    if bad:
        raise ValueError(f"unknown provenance values: {bad}")
    return df[COMMON_PHYSIO_COLUMNS]


def load_all_physiology(data_dir="data", include_unlicensed: bool = True) -> pd.DataFrame:
    """
    Stacks every REAL physiology source that is available locally into the common
    long format: published aggregates (always) + PRCP + BHP-Lab tilt/LBNP data
    (if downloaded). Synthetic data are never included.

    ``include_unlicensed=False`` drops the public-but-unlicensed BHP-Lab
    tilt-dose-response and LBNP repositories (use for anything published).
    """
    from pathlib import Path

    from vascushift.data.literature import literature_aggregates

    data_dir = Path(data_dir)
    parts = [literature_aggregates()]
    prcp = data_dir / "raw" / "physionet" / "prcp" / "1.0.0"
    if prcp.exists():
        from vascushift.data.physionet_posture import prcp_condition_summary

        parts.append(prcp_condition_summary(prcp))
    gh = data_dir / "raw" / "github"
    if (gh / "carotid-jugular-characteristics").exists():
        from vascushift.data.bhp_lab import load_carotid_jugular

        parts.append(load_carotid_jugular(gh / "carotid-jugular-characteristics"))
    if include_unlicensed:
        from vascushift.data.bhp_lab import load_lbnp_dose_response, load_tilt_dose_response

        if (gh / "tilt-dose-response").exists():
            parts.append(load_tilt_dose_response(gh / "tilt-dose-response"))
        if (gh / "LBNP-Dose-Response").exists():
            parts.append(load_lbnp_dose_response(gh / "LBNP-Dose-Response"))
    return pd.concat(parts, ignore_index=True)


# =========================================================================== optical (rPPG) common format
#
# A preprocessed optical session is one ``.npz`` file whose arrays all live on ONE uniform time grid
# (``fs`` Hz, default 30), produced from the real frame clock of the recording (see
# ``vascushift.data.ubfc.load_ubfc_session``). Sessions are indexed by ``sessions.csv`` with the
# columns below. Waveforms are never committed to git (dataset agreements), only the index and the
# metrics derived from them.

OPTICAL_SESSION_ARRAYS = {
    "time": "s, uniform grid starting at 0",
    "rgb": "(N, 3) mean skin R, G, B in the face ROI, 0-255",
    "ref_ppg": "contact finger PPG on the same grid (arbitrary units)",
    "valid": "bool; False inside dropped-frame holes or before the first face detection",
    "face_found": "bool; face detector hit (or carried box) at that time",
}

OPTICAL_SESSION_COLUMNS = [
    "dataset", "session_id", "subject_id", "subset", "fs", "n_samples", "duration_s", "fraction_valid",
    "frame_clock", "fps_video_mean", "max_frame_step_s", "ref_hr_bpm", "hr_sensor_dropouts",
    "no_face_display", "provenance", "source", "file",
]

# One row = one HR estimate of one method in one time window of one session.
RPPG_WINDOW_COLUMNS = [
    "dataset", "session_id", "subset", "protocol", "method", "t_start_s", "t_end_s",
    "hr_ref_bpm", "hr_est_bpm", "error_bpm", "snr_db", "fraction_valid", "included", "exclusion_reason",
    "provenance",
]


def conform_columns(df: pd.DataFrame, columns) -> pd.DataFrame:
    """Adds missing columns (as None), orders them and validates ``provenance`` if present."""
    df = df.copy()
    for c in columns:
        if c not in df.columns:
            df[c] = None
    if "provenance" in df.columns:
        bad = set(df["provenance"].dropna()) - set(PROVENANCE_LEVELS)
        if bad:
            raise ValueError(f"unknown provenance values: {bad}")
    return df[list(columns)]
