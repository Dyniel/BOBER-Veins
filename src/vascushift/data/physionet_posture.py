"""
Loaders for open PhysioNet posture / orthostatic datasets.

1. PRCP - Physiologic Response to Changes in Posture (Heldt et al.; DOI 10.13026/C2PC7R)
   10 healthy subjects, 250 Hz: ABP (Finapres, mmHg), ECG (mV) and tilt-table
   Angle (degrees, 0 = supine, ~75 = head-up). Protocol: supine rest, slow tilt
   (~50 s to 75 deg), rapid tilt (~2 s), stand-up, each repeated; events in the
   ``anI`` annotations, beat onsets in ``wabp``.

   The body-axis gravity component is ``gz_body = sin(angle)`` (0 supine, 0.97
   at 75 deg, 1.0 standing). Note: during "Stand up" the subject leaves the
   table, so the Angle channel stays ~0 - the posture state is taken from the
   event annotations, not from the angle.

2. cardioresp-response-orthostat (Eke, Mukli et al.; DOI 10.13026/73w7-x881)
   10 young adults (subject 05 excluded by the authors), ~3 Hz resampled CSV:
   MCA blood-flow velocity (TCD), ABP, respiration and 16-channel raw NIRS
   intensities at 730/805/850 nm; 30 min sitting rest, 1 min stand-up,
   1 min sit-down (markers in ``subjXX.marker.csv``).
   Audit note: the CSV header mislabels some NIRS columns (e.g. "i4_730",
   "i5_805", "i5_850" break the 850/730/805 pattern described in README.txt);
   ``load_orthostat_subject`` renames them by position following the README.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from vascushift.data.schema import conform

PRCP_DIR = Path("data/raw/physionet/prcp/1.0.0")
ORTHOSTAT_DIR = Path("data/raw/physionet/cardioresp-response-orthostat/1.0")


# --------------------------------------------------------------------------- #
# PRCP
# --------------------------------------------------------------------------- #
def list_prcp_records(root: Path = PRCP_DIR) -> List[str]:
    return [r.strip() for r in (Path(root) / "RECORDS").read_text().split() if r.strip()]


def _parse_demographics(comments: List[str]) -> Dict:
    out: Dict = {}
    for c in comments:
        if "<age>" not in c:
            continue
        parts = c.replace("<", " <").split("<")[1:]
        for p in parts:
            if ">:" in p:
                k, v = p.split(">:", 1)
                v = v.strip()
                try:
                    out[k.strip().lower()] = float(v)
                except ValueError:
                    out[k.strip().lower()] = v
    return out


def load_prcp_record(record: str, root: Path = PRCP_DIR) -> Dict:
    """Returns signals, fs, demographics and the event list of one PRCP record."""
    import wfdb

    base = str(Path(root) / record)
    rec = wfdb.rdrecord(base)
    sig = {name: rec.p_signal[:, i] for i, name in enumerate(rec.sig_name)}
    ann = wfdb.rdann(base, "anI")
    events = pd.DataFrame({
        "t_s": np.asarray(ann.sample) / rec.fs,
        "event": [a.strip() for a in ann.aux_note],
    })
    beats = wfdb.rdann(base, "wabp")
    return {
        "record": record,
        "fs": float(rec.fs),
        "abp_mmHg": sig["ABP"],
        "ecg_mV": sig["ECG"],
        "angle_deg": sig["Angle"],
        "demographics": _parse_demographics(rec.comments),
        "events": events,
        "beat_onsets": np.asarray([s for s, sym in zip(beats.sample, beats.symbol) if sym == "N"]),
    }


def event_kind(text: str) -> str:
    """
    Normalises PRCP event annotations, whose wording differs between records
    ("Initiate slow tilt up" / "Start slow tilt up" / "Initiation of rapid tilt up",
    "Stand up" / "Stand-up" / "Stand-up from supine", "Transition back to supine" /
    "Back to supine", typos such as "Conslusion").

    Returns one of: tilt_up_start, tilt_up_end, tilt_down_start, tilt_down_end,
    stand_up, back_to_supine, other.
    """
    # some notes carry a numeric prefix ("0 -1 0 \tStand up") or are truncated ("supin")
    e = re.sub(r"^[\d\s\-]+", "", text.lower()).replace("-", " ").strip()
    is_start = e.startswith(("initiat", "start"))
    is_end = e.startswith(("conclu", "conslu", "end"))
    after = e.split("tilt", 1)[1] if "tilt" in e else ""
    if re.search(r"\bup\b", after):
        return "tilt_up_start" if is_start else ("tilt_up_end" if is_end else "other")
    if re.search(r"\bdow", after):  # "down", truncated "dow"
        return "tilt_down_start" if is_start else ("tilt_down_end" if is_end else "other")
    if e.startswith("stand up"):
        return "stand_up"
    if "back to supin" in e:
        return "back_to_supine"
    return "other"


def _posture_timeline(events: pd.DataFrame, n_samples: int, fs: float) -> np.ndarray:
    """True where the subject is standing (between a stand-up and the return to supine)."""
    standing = np.zeros(n_samples, dtype=bool)
    start = None
    for t, ev in zip(events["t_s"], events["event"]):
        kind = event_kind(ev)
        if kind == "stand_up":
            start = int(t * fs)
        elif kind == "back_to_supine" and start is not None:
            standing[start:int(t * fs)] = True
            start = None
    return standing


def prcp_beat_table(record: str, root: Path = PRCP_DIR) -> pd.DataFrame:
    """
    Beat-by-beat table for one record: time, posture, table angle, gz_body,
    HR (from consecutive ABP pulse onsets) and SBP/DBP/MAP of each beat.

    Beats with implausible intervals (HR outside 30-200 bpm) or pressures
    (MAP outside 30-200 mmHg) are flagged in ``valid`` rather than dropped.
    """
    r = load_prcp_record(record, root)
    fs, abp, ang = r["fs"], r["abp_mmHg"], r["angle_deg"]
    standing = _posture_timeline(r["events"], len(abp), fs)
    on = r["beat_onsets"]
    rows = []
    for a, b in zip(on[:-1], on[1:]):
        seg = abp[a:b]
        if len(seg) < 2 or np.isnan(seg).any():
            continue
        mid = (a + b) // 2
        is_standing = bool(standing[mid])
        angle = 90.0 if is_standing else float(np.median(ang[a:b]))
        hr = 60.0 * fs / (b - a)
        mapp = float(seg.mean())
        rows.append({
            "record": record,
            "t_s": a / fs,
            "posture": "standing" if is_standing else ("tilted" if angle > 5 else "supine"),
            "tilt_deg": round(angle, 2),
            "gz_body": round(float(np.sin(np.deg2rad(max(angle, 0.0)))), 4),
            "hr_bpm": round(hr, 2),
            "sbp_mmHg": round(float(seg.max()), 2),
            "dbp_mmHg": round(float(seg.min()), 2),
            "map_mmHg": round(mapp, 2),
            "valid": bool(30 <= hr <= 200 and 30 <= mapp <= 200),
        })
    return pd.DataFrame(rows)


def prcp_condition_summary(root: Path = PRCP_DIR, plateau_s: float = 60.0) -> pd.DataFrame:
    """
    Steady-state summary per record and condition, in the common long format:

    * ``supine``   - the 60 s before each tilt / stand-up starts (angle < 5 deg)
    * ``hut75``    - last ``plateau_s`` seconds of each tilt plateau (angle > 70 deg)
    * ``standing`` - last ``plateau_s`` seconds of each stand-up period

    Values are medians over valid beats, averaged over repetitions.
    """
    out = []
    for rec in list_prcp_records(root):
        bt = prcp_beat_table(rec, root)
        bt = bt[bt["valid"]]
        r = load_prcp_record(rec, root)
        ev = r["events"]
        kinds = ev["event"].map(event_kind)
        windows = []  # (condition, t0, t1)
        for t in ev.loc[kinds.isin(["tilt_up_start", "stand_up"]), "t_s"]:
            windows.append(("supine", t - 60.0, t - 1.0))
        for t in ev.loc[kinds == "tilt_down_start", "t_s"]:
            windows.append(("hut75", t - plateau_s, t - 1.0))
        for t in ev.loc[kinds == "back_to_supine", "t_s"]:
            windows.append(("standing", t - plateau_s, t - 1.0))
        per_cond: Dict[str, List[pd.DataFrame]] = {}
        for cond, t0, t1 in windows:
            w = bt[(bt["t_s"] >= t0) & (bt["t_s"] < t1)]
            if cond == "supine":
                w = w[w["posture"] == "supine"]
            elif cond == "hut75":
                w = w[w["tilt_deg"] > 70]
            else:
                w = w[w["posture"] == "standing"]
            if len(w) >= 10:
                per_cond.setdefault(cond, []).append(w)
        demo = r["demographics"]
        for cond, ws in per_cond.items():
            meds = pd.DataFrame([w[["tilt_deg", "gz_body", "hr_bpm", "map_mmHg", "sbp_mmHg", "dbp_mmHg"]].median()
                                 for w in ws]).mean()
            for var, unit in [("heart_rate", "bpm"), ("mean_arterial_pressure", "mmHg"),
                              ("systolic_bp", "mmHg"), ("diastolic_bp", "mmHg")]:
                col = {"heart_rate": "hr_bpm", "mean_arterial_pressure": "map_mmHg",
                       "systolic_bp": "sbp_mmHg", "diastolic_bp": "dbp_mmHg"}[var]
                out.append({
                    "dataset": "physionet_prcp",
                    "subject_id": f"prcp-{rec}",
                    "sex": demo.get("sex"),
                    "condition": cond,
                    "environment": "ground_lab",
                    "posture": {"supine": "supine", "hut75": "supine_hut", "standing": "standing"}[cond],
                    "tilt_deg": round(float(meds["tilt_deg"]), 1),
                    "gz_platform": 1.0,
                    "gz_body": round(float(meds["gz_body"]), 3),
                    "lbnp_mmHg": 0.0,
                    "variable": var, "unit": unit,
                    "stat": "median_of_beats", "value": round(float(meds[col]), 2),
                    "n": int(sum(len(w) for w in ws)),
                    "provenance": "raw_individual",
                    "source": "PhysioNet PRCP 1.0.0, doi:10.13026/C2PC7R",
                    "notes": f"age {demo.get('age')}; finger (Finapres) BP - hand height not controlled",
                })
    return conform(pd.DataFrame(out))


# --------------------------------------------------------------------------- #
# cardioresp-response-orthostat
# --------------------------------------------------------------------------- #
def list_orthostat_subjects(root: Path = ORTHOSTAT_DIR) -> List[str]:
    return sorted(p.stem for p in Path(root).glob("subj??.csv"))


def load_orthostat_subject(subject: str, root: Path = ORTHOSTAT_DIR) -> Dict:
    """
    Returns ``{"data": DataFrame, "markers": DataFrame, "fs": float}``. NIRS
    columns are renamed by position (README order: 850, 730, 805 nm per channel).
    """
    root = Path(root)
    # header row contains non-UTF-8 bytes in some files
    df = pd.read_csv(root / f"{subject}.csv", encoding="latin-1")
    df = df.loc[:, [c for c in df.columns if not str(c).startswith("Unnamed")]]
    df.columns = [str(c).strip().strip('"') for c in df.columns]
    names = ["right_MCA_BFV", "left_MCA_BFV", "Blood_pressure", "resp_uncalibrated"]
    for ch in range(1, 17):
        names += [f"i{ch}_850", f"i{ch}_730", f"i{ch}_805"]
    names += ["Time"]
    if len(df.columns) != len(names):
        raise ValueError(f"{subject}: expected {len(names)} columns, got {len(df.columns)}")
    df.columns = names
    mk = pd.read_csv(root / f"{subject}.marker.csv", header=None, names=["code", "t_s"])
    fs = 1.0 / float(np.median(np.diff(df["Time"].to_numpy())))
    return {"data": df, "markers": mk, "fs": fs}
