"""
Published group-level measurements of jugular / systemic haemodynamics across
gravity levels and postures, transcribed from open-access papers.

These are REAL measured values, but only group summaries (mean with 95% CI or
SD). They are the only fluid-shift ground truth we can use today, because the
individual data are not public (ESA HREDA: no files; NASA LSDA: on request).

Every number below was copied from the cited table / paragraph (full texts read
via Europe PMC on 2026-11-04). Known errata of the papers are kept as notes and
never "corrected" silently.

Gravity semantics used across VascuShift data:
    gz_platform : acceleration of the environment in g (1 on ground, 0.25 in a
                  0.25-G parabola, 0 on the ISS)
    gz_body     : component along the head-to-foot body axis
                  = gz_platform * sin(tilt), tilt = 90 deg upright, 0 supine,
                  -15 deg head-down tilt (gz_body < 0).
    NB: 1-G supine has gz_body = 0 like microgravity, but it is NOT weightless
    (the chest is still loaded antero-posteriorly) - Marshall-Goebel 2019 shows
    ISS IJV area (70 mm2) below 1-G supine (81 mm2). Keep both columns.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from vascushift.data.schema import COMMON_PHYSIO_COLUMNS, conform  # noqa: F401  (re-exported)

LEE2020 = "lee2020_partial_gravity"
LEE2020_SRC = "Lee SMC et al., Front Physiol 2020;11:863, doi:10.3389/fphys.2020.00863"
MG2019 = "marshall_goebel2019_iss_ijv"
MG2019_SRC = "Marshall-Goebel K et al., JAMA Netw Open 2019;2(11):e1915011, doi:10.1001/jamanetworkopen.2019.15011"
MARTIN2016 = "martin2016_parabolic_ijvp"
MARTIN2016_SRC = "Martin DS et al., Physiol Rep 2016;4(24):e13068, doi:10.14814/phy2.13068"


def _cond(name, environment, posture, tilt_deg, gz_platform):
    gz_body = None if tilt_deg is None else round(gz_platform * math.sin(math.radians(tilt_deg)), 3)
    return {"condition": name, "environment": environment, "posture": posture,
            "tilt_deg": tilt_deg, "gz_platform": gz_platform, "gz_body": gz_body}


# --------------------------------------------------------------------------- #
# Lee et al. 2020 - 1st ISLSWG parabolic flight campaign, June 2018, N = 9 (5F/4M)
# Right IJV. No 0-G parabolas were flown in this campaign.
# --------------------------------------------------------------------------- #
_LEE_COND = {
    "seated_1.00G": _cond("seated_1.00G", "parabolic_flight_level", "seated", 90, 1.00),
    "seated_0.75G": _cond("seated_0.75G", "parabolic_flight", "seated", 90, 0.75),
    "seated_0.50G": _cond("seated_0.50G", "parabolic_flight", "seated", 90, 0.50),
    "seated_0.25G": _cond("seated_0.25G", "parabolic_flight", "seated", 90, 0.25),
    "supine_1.00G": _cond("supine_1.00G", "ground_preflight", "supine", 0, 1.00),
}
_LEE_ORDER = ["seated_1.00G", "seated_0.75G", "seated_0.50G", "seated_0.25G", "supine_1.00G"]

# variable -> (unit, n, location, [(mean, ci_low, ci_high) per _LEE_ORDER], note)
_LEE_TABLES = {
    "heart_rate": ("bpm", None, "Table 2", [(60, 51, 68), (58, 51, 66), (56, 49, 63), (56, 49, 62), None],
                   "n not stated; supine HR not reported"),
    "mean_arterial_pressure": ("mmHg", None, "Table 2", [(95, 79, 111), (89, 74, 103), (85, 66, 103), (80, 66, 94), None],
                               "finger BP missing for 2 subjects on day 1 and 1 on day 2; supine MAP not reported"),
    "ijv_area_right": ("mm2", 8, "Table 3", [(12, 9, 16), (24, 13, 35), (34, 21, 46), (68, 40, 97), (108, 74, 131)],
                       "one subject without adequate IJV images at all levels; abstract gives supine 103 (75-131), Table 3 gives 108 (74-131)"),
    "ivc_diameter": ("cm", None, "Table 3", [(1.68, 1.45, 1.92), (1.66, 1.44, 1.88), (1.81, 1.61, 2.02), (1.69, 1.46, 1.91), (1.81, 1.57, 2.05)], ""),
    "cca_flow": ("mL/min", None, "Table 3", [(786, 635, 837), (895, 686, 1103), (845, 650, 1039), (826, 688, 963), (836, 783, 891)], ""),
    "cca_area": ("cm2", None, "Table 3", [(0.33, 0.31, 0.35), (0.33, 0.31, 0.35), (0.33, 0.30, 0.36), (0.34, 0.31, 0.36), (0.32, 0.29, 0.34)],
                 "Table 3 header prints the unit as 'cm'; values are cross-sectional areas (cm2)"),
}

# IJV flow grade 2 (pulsatile) counts, Results 'Vascular Responses' + Figure 4
_LEE_FLOW = {
    "seated_1.00G": (1, 8), "seated_0.75G": (1, 8), "seated_0.50G": (4, 9),
    "seated_0.25G": (5, 8), "supine_1.00G": (7, 8),
}

# IJV pressure, compression sonography (VeinPress), Results text, mean +/- SD, n = 5
_LEE_IJVP = {"seated_0.50G": (9.5, 3.4, 5), "supine_1.00G": (19.1, 7.6, 5)}

# --------------------------------------------------------------------------- #
# Marshall-Goebel et al. 2019 - ISS, N = 11 crew (10 on flight day 150), LEFT IJV
# --------------------------------------------------------------------------- #
_MG_COND = {
    "preflight_seated": _cond("preflight_seated", "ground_preflight", "seated", 90, 1.0),
    "preflight_supine": _cond("preflight_supine", "ground_preflight", "supine", 0, 1.0),
    "preflight_hdt15": _cond("preflight_hdt15", "ground_preflight", "head_down_tilt", -15, 1.0),
    "iss_fd50": _cond("iss_fd50", "iss", "free_floating", None, 0.0),
    "iss_fd50_lbnp25": _cond("iss_fd50_lbnp25", "iss_lbnp_25mmHg", "free_floating", None, 0.0),
    "iss_fd150": _cond("iss_fd150", "iss", "free_floating", None, 0.0),
    "iss_fd150_lbnp25": _cond("iss_fd150_lbnp25", "iss_lbnp_25mmHg", "free_floating", None, 0.0),
    "postflight_seated": _cond("postflight_seated", "ground_postflight_40d", "seated", 90, 1.0),
    "postflight_supine": _cond("postflight_supine", "ground_postflight_40d", "supine", 0, 1.0),
    "postflight_hdt15": _cond("postflight_hdt15", "ground_postflight_40d", "head_down_tilt", -15, 1.0),
}
for _k in ("iss_fd50", "iss_fd50_lbnp25", "iss_fd150", "iss_fd150_lbnp25"):
    _MG_COND[_k]["gz_body"] = 0.0
_MG_TABLE_ORDER = ["preflight_seated", "preflight_supine", "preflight_hdt15", "iss_fd50", "iss_fd50_lbnp25",
                   "iss_fd150", "iss_fd150_lbnp25", "postflight_seated", "postflight_supine", "postflight_hdt15"]

_MG_TABLE = {  # 'Table. Cardiovascular Measurements Preflight, During Spaceflight, and Postflight'
    "stroke_volume": ("mL", [(69, 63, 75), (89, 82, 95), (87, 81, 93), (86, 80, 92), (60, 53, 66), (85, 79, 92),
                             (57, 50, 63), (66, 60, 73), (82, 76, 89), (91, 84, 97)]),
    "cardiac_output": ("L/min", [(4.2, 3.7, 4.8), (4.8, 4.2, 5.4), (4.7, 4.1, 5.3), (5.0, 4.4, 5.5), (4.2, 3.6, 4.8),
                                 (5.1, 4.5, 5.7), (3.8, 3.3, 4.4), (4.0, 3.4, 4.6), (4.8, 4.3, 5.4), (5.2, 4.6, 5.7)]),
    "heart_rate": ("bpm", [(61, 58, 65), (54, 51, 58), (54, 50, 57), (60, 57, 64), (70, 66, 74), (59, 55, 62),
                           (None, 68, 76), (61, 57, 64), (56, 52, 60), (56, 52, 60)]),
    "mean_arterial_pressure": ("mmHg", [(91, 85, 97), (87, 81, 93), (88, 82, 94), (94, 88, 100), (80, 74, 86), (90, 84, 96),
                                        (80, 74, 87), (89, 83, 95), (85, 79, 91), (87, 81, 93)]),
    "systolic_bp": ("mmHg", [(119, 112, 126), (116, 109, 122), (119, 113, 126), (123, 116, 130), (119, 112, 127),
                             (121, 114, 127), (116, 108, 123), (116, 109, 123), (115, 108, 122), (119, 112, 126)]),
    "diastolic_bp": ("mmHg", [(77, 71, 82), (72, 67, 78), (73, 67, 78), (79, 73, 84), (61, 55, 66), (75, 69, 81),
                              (62, 56, 69), (76, 70, 82), (69, 64, 75), (71, 65, 77)]),
}
_MG_TEXT = {  # Results text (Figure 2): left IJV area and pressure, mean (95% CI)
    "ijv_area_left": ("mm2", {
        "preflight_seated": (9.8, -1.2, 20.7), "preflight_supine": (80.7, 69.9, 91.5), "preflight_hdt15": (107.7, 96.7, 118.7),
        "iss_fd50": (70.3, 59.3, 81.2), "iss_fd150": (60.0, 48.8, 71.2),
        "iss_fd50_lbnp25": (44.7, 33.2, 56.2), "iss_fd150_lbnp25": (42.7, 30.5, 54.8)}),
    "ijv_pressure": ("mmHg", {
        "preflight_seated": (5.1, 2.5, 7.8), "preflight_supine": (17.3, 14.8, 19.8), "preflight_hdt15": (20.7, 17.8, 23.5),
        "iss_fd50": (21.1, 18.5, 23.7), "iss_fd150": (15.8, 13.0, 18.6)}),
}

# --------------------------------------------------------------------------- #
# Martin et al. 2016 - parabolic flight, N = 11 (3M/8F), IJV pressure (VeinPress)
# In flight subjects sat on the cabin floor, legs horizontal (trunk upright).
# --------------------------------------------------------------------------- #
_MARTIN_COND = {
    "supine_1G_preflight": _cond("supine_1G_preflight", "ground_preflight", "supine", 0, 1.0),
    "seated_0G": _cond("seated_0G", "parabolic_flight", "long_sitting", 90, 0.0),
}


def _row(dataset, cond, variable, unit, stat, value, source, *, ci=None, sd=None, n=None, notes=""):
    r = {"dataset": dataset, "subject_id": "group", **cond, "variable": variable, "unit": unit, "stat": stat,
         "value": value, "ci_low": ci[0] if ci else None, "ci_high": ci[1] if ci else None, "sd": sd, "n": n,
         "provenance": "published_aggregate", "source": source, "notes": notes}
    return r


def literature_aggregates() -> pd.DataFrame:
    """All transcribed group-level values in the common long physiology format."""
    rows: List[Dict] = []
    for var, (unit, n, loc, vals, note) in _LEE_TABLES.items():
        for cname, v in zip(_LEE_ORDER, vals):
            if v is None:
                continue
            rows.append(_row(LEE2020, _LEE_COND[cname], var, unit, "mean_ci95", v[0], f"{LEE2020_SRC}, {loc}",
                             ci=(v[1], v[2]), n=n, notes=note))
    for cname, (k, n) in _LEE_FLOW.items():
        rows.append(_row(LEE2020, _LEE_COND[cname], "ijv_flow_grade2_fraction", "fraction", "proportion",
                         round(k / n, 4), f"{LEE2020_SRC}, Results 'Vascular Responses' / Fig. 4", n=n,
                         notes=f"{k} of {n} subjects with pulsatile (grade 2) flow; Fig. 4 caption gives n=9 for supine"
                         if cname == "supine_1.00G" else f"{k} of {n} subjects with pulsatile (grade 2) flow"))
    for cname, (m, sd, n) in _LEE_IJVP.items():
        rows.append(_row(LEE2020, _LEE_COND[cname], "ijv_pressure", "mmHg", "mean_sd", m,
                         f"{LEE2020_SRC}, Results 'Vascular Responses'", sd=sd, n=n,
                         notes="paired difference 9.6 (95% CI 5.0-14.1) mmHg; no usable IJV pressure seated at 0.75/1.00 G"))

    for var, (unit, vals) in _MG_TABLE.items():
        for cname, v in zip(_MG_TABLE_ORDER, vals):
            n = 10 if cname.startswith("iss_fd150") else 11
            note = ""
            if var == "heart_rate" and cname == "iss_fd150_lbnp25":
                note = "Table prints the mean as '7' (typo); value left empty, 95% CI 68-76"
            rows.append(_row(MG2019, _MG_COND[cname], var, unit, "mean_ci95", v[0], f"{MG2019_SRC}, Table",
                             ci=(v[1], v[2]), n=n, notes=note))
    for var, (unit, per) in _MG_TEXT.items():
        for cname, v in per.items():
            n = 10 if cname.startswith("iss_fd150") else 11
            rows.append(_row(MG2019, _MG_COND[cname], var, unit, "mean_ci95", v[0], f"{MG2019_SRC}, Results (Fig. 2)",
                             ci=(v[1], v[2]), n=n,
                             notes="left IJV; CI lower bound < 0 as published" if v[1] < 0 else "left IJV"))

    rows.append(_row(MARTIN2016, _MARTIN_COND["supine_1G_preflight"], "ijv_pressure", "mmHg", "mean_sd", 9.9,
                     f"{MARTIN2016_SRC}, Abstract/Results", sd=5.1, n=11))
    rows.append(_row(MARTIN2016, _MARTIN_COND["seated_0G"], "ijv_pressure", "mmHg", "mean_sd", 23.9,
                     f"{MARTIN2016_SRC}, Abstract/Results", sd=5.6, n=11,
                     notes="0.17 G and 0.29 G measured in only 2 subjects (figure only, not transcribed)"))

    df = pd.DataFrame(rows)
    df["lbnp_mmHg"] = 0.0
    df.loc[df["environment"] == "iss_lbnp_25mmHg", "lbnp_mmHg"] = -25.0
    return conform(df)


def export_literature_aggregates(path: Path = Path("data/external/literature_aggregates.csv")) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    literature_aggregates().to_csv(path, index=False)
    return path


def ijv_area_vs_gravity(dataset: Optional[str] = None) -> pd.DataFrame:
    """Convenience view: IJV area (left or right) per condition with CI, sorted by gz_body."""
    df = literature_aggregates()
    df = df[df["variable"].str.startswith("ijv_area")]
    if dataset:
        df = df[df["dataset"] == dataset]
    return df.sort_values(["dataset", "gz_body"])[
        ["dataset", "condition", "environment", "gz_platform", "gz_body", "variable", "value", "ci_low", "ci_high", "n"]]
