"""
Loaders for the public data of the Texas A&M Bioastronautics and Human Performance
Lab (A. Diaz-Artiles), fetched by ``scripts/download_data.py --dataset github``.

1. carotid-jugular-characteristics (MIT licence)
   Whittle RS, Diaz-Artiles A. Gravitational effects on carotid and jugular
   characteristics in graded head-up and head-down tilt. J Appl Physiol
   2023;134:217-229, doi:10.1152/japplphysiol.00248.2022.
   12 subjects (IJV area for 11), tilt +45 deg HUT -> -45 deg HDT in 15 deg steps,
   supine and prone, plus a seated baseline (orientation session).
   IJV / CCA cross-sectional area (mm2, Vscan Extend ultrasound), IJV pressure
   (mmHg, compression sonography), left (S) and right (D) side.

2. tilt-dose-response (public, NO licence -> internal analysis only)
   Whittle RS et al., Gravitational dose-response curves for acute cardiovascular
   hemodynamics and autonomic responses in a tilt paradigm. J Am Heart Assoc
   2022;11:e024175, doi:10.1161/JAHA.121.024175. 24 subjects (12F/12M), same
   tilt protocol; adds intraocular pressure, Finapres HR/BP/SV/CO and IJV/CCA data.
   The ``CVP`` column is a constant 4.6 (device default, not a measurement) and is ignored.

3. LBNP-Dose-Response (public, NO licence -> internal analysis only)
   LBNP 0 to -50 mmHg in 10 mmHg steps, supine (L0) and 15 deg HDT (L15), 24 subjects.

Index coding (README of repo 1): 0 seated, 1 45 HUT, 2 30 HUT, 3 15 HUT, 4 0 deg,
5 15 HDT, 6 30 HDT, 7 45 HDT. Side: D = dexter (right), S = sinister (left).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from vascushift.data.schema import conform, gz_body_from_tilt

GITHUB_DIR = Path("data/raw/github")
INDEX_TO_TILT = {0: 90.0, 1: 45.0, 2: 30.0, 3: 15.0, 4: 0.0, 5: -15.0, 6: -30.0, 7: -45.0}
SIDE = {"D": "right", "S": "left"}

CJ_SRC = ("Whittle & Diaz-Artiles, J Appl Physiol 2023;134:217, doi:10.1152/japplphysiol.00248.2022; "
          "github.com/BHP-Lab/carotid-jugular-characteristics (MIT)")
TILT_SRC = ("Whittle et al., J Am Heart Assoc 2022;11:e024175, doi:10.1161/JAHA.121.024175; "
            "github.com/BHP-Lab/tilt-dose-response (no licence)")
LBNP_SRC = "github.com/BHP-Lab/LBNP-Dose-Response (no licence; LBNP dose-response raw data)"

# column -> (variable, unit) for the wide 'master' tables
_WIDE_VARS = {
    "IJV.D": ("ijv_area_right", "mm2"), "IJV.S": ("ijv_area_left", "mm2"),
    "VPC.D": ("ijv_pressure_right", "mmHg"), "VPC.S": ("ijv_pressure_left", "mmHg"),
    "IOP.D": ("iop_right", "mmHg"), "IOP.S": ("iop_left", "mmHg"),
    "CCA.D": ("cca_area_right", "mm2"), "CCA.S": ("cca_area_left", "mm2"),
    "HR.ECG": ("heart_rate", "bpm"),
    "reMAP": ("mean_arterial_pressure", "mmHg"),
    "reSYS": ("systolic_bp", "mmHg"), "reDIA": ("diastolic_bp", "mmHg"),
    "SV.F": ("stroke_volume", "mL"), "CO.F": ("cardiac_output", "L/min"),
}


def _sex(v) -> Optional[str]:
    if isinstance(v, str) and v:
        return v.strip()[0].upper()
    return None


def _posture(face: str, tilt: float) -> str:
    f = face.lower()
    if f.startswith("seated") or f == "sb":
        return "seated"
    base = "prone" if f.startswith("p") else "supine"
    return base if tilt == 0 else f"{base}_{'hut' if tilt > 0 else 'hdt'}"


def load_carotid_jugular(root: Path = GITHUB_DIR / "carotid-jugular-characteristics") -> pd.DataFrame:
    """IJV area, IJV pressure and CCA area per subject/side/position/angle (common long format)."""
    root = Path(root)
    rows: List[Dict] = []
    face_map = {"S": "Supine", "P": "Prone", "SB": "Seated"}
    for fname, valcol, var, unit in [("IJV.csv", "IJV", "ijv_area", "mm2"),
                                     ("CCA.csv", "CCA", "cca_area", "mm2"),
                                     ("IJVP.csv", "VPC", "ijv_pressure", "mmHg")]:
        df = pd.read_csv(root / fname, index_col=0)
        for r in df.itertuples(index=False):
            idx = int(r.Index)
            tilt = INDEX_TO_TILT[idx]
            face = face_map.get(str(r.Face), str(r.Face))
            v = getattr(r, valcol)
            if pd.isna(v):
                continue
            rows.append({
                "dataset": "bhp_carotid_jugular", "subject_id": f"bhp-{r.ID}",
                "condition": "seated_baseline" if idx == 0 else f"{face.lower()}_tilt_{tilt:+.0f}",
                "environment": "ground_lab", "posture": _posture(face, tilt), "tilt_deg": tilt,
                "gz_platform": 1.0, "gz_body": gz_body_from_tilt(tilt), "lbnp_mmHg": 0.0,
                "variable": f"{var}_{SIDE[r.Side]}", "unit": unit, "stat": "value", "value": float(v), "n": 1,
                "provenance": "raw_individual", "source": f"{CJ_SRC}, {fname}",
                "notes": "seated baseline recorded in a separate orientation session" if idx == 0 else "",
            })
    return conform(pd.DataFrame(rows))


def _wide_to_long(df: pd.DataFrame, dataset: str, source: str, lbnp: bool) -> pd.DataFrame:
    rows: List[Dict] = []
    for r in df.to_dict(orient="records"):
        idx = int(r["Index"])
        if lbnp:
            face = str(r["Face"])
            if face == "Seated":
                tilt, lb, cond = 90.0, 0.0, "seated_baseline"
            else:
                tilt = 0.0 if face == "L0" else -15.0
                lb = float(str(r["Pressure"]).split()[0])
                cond = f"{'supine' if tilt == 0 else 'hdt15'}_lbnp_{lb:+.0f}"
            posture = "seated" if face == "Seated" else ("supine" if tilt == 0 else "supine_hdt")
        else:
            tilt, lb = INDEX_TO_TILT[idx], 0.0
            face = str(r["Face"])
            cond = "seated_baseline" if idx == 0 else f"{face.lower()}_tilt_{tilt:+.0f}"
            posture = _posture(face, tilt)
        for col, (var, unit) in _WIDE_VARS.items():
            v = r.get(col)
            if v is None or pd.isna(v):
                continue
            rows.append({
                "dataset": dataset, "subject_id": f"bhp-{r['ID']}", "sex": _sex(r.get("Sex")),
                "condition": cond, "environment": "ground_lab", "posture": posture, "tilt_deg": tilt,
                "gz_platform": 1.0, "gz_body": gz_body_from_tilt(tilt), "lbnp_mmHg": lb,
                "variable": var, "unit": unit, "stat": "value", "value": float(v), "n": 1,
                "provenance": "raw_individual", "source": source,
                "notes": "public data without licence - internal analysis only",
            })
    return conform(pd.DataFrame(rows))


def load_tilt_dose_response(root: Path = GITHUB_DIR / "tilt-dose-response") -> pd.DataFrame:
    """24-subject tilt dataset (HR, BP, SV, CO, IJV area/pressure, IOP, CCA) in long format."""
    df = pd.read_csv(Path(root) / "Tilt_Use.csv", encoding="latin-1")  # angle labels are mis-encoded; Index is used
    return _wide_to_long(df, "bhp_tilt_dose_response", f"{TILT_SRC}, Tilt_Use.csv", lbnp=False)


def load_lbnp_dose_response(root: Path = GITHUB_DIR / "LBNP-Dose-Response") -> pd.DataFrame:
    """24-subject LBNP dataset (supine and 15 deg HDT, 0 to -50 mmHg) in long format."""
    df = pd.read_csv(Path(root) / "LBNP-Raw_Data.csv", encoding="latin-1")
    return _wide_to_long(df, "bhp_lbnp_dose_response", f"{LBNP_SRC}, LBNP-Raw_Data.csv", lbnp=True)


def dose_response_table(df: pd.DataFrame, variable: str) -> pd.DataFrame:
    """Per-condition summary (n, mean, sd, median) of one variable, sorted by gz_body."""
    d = df[df["variable"] == variable]
    g = d.groupby(["posture", "tilt_deg", "gz_body", "lbnp_mmHg"])["value"]
    out = g.agg(n="count", mean="mean", sd="std", median="median").reset_index()
    return out.sort_values(["lbnp_mmHg", "gz_body"], ascending=[False, False]).round(2)
