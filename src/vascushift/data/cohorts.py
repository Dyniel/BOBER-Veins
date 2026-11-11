"""
Real-data cohorts in the column layout of the (synthetic) ESA table, for the model code.

``real_ijv_cohort()`` is the drop-in replacement candidate for
``esa_loader.generate_synthetic_esa_like_cohort()``: one row per subject x condition with IJV area and
pressure measured in REAL people (BHP-Lab ground tilt, Whittle & Diaz-Artiles), plus the gravity
geometry needed by a hydrostatic model.

Geometry columns (read before using):

* ``gz``              platform gravity [g] - always 1.0 here (ground lab), like ``gz`` of the ESA table
* ``tilt_deg``        body long axis from horizontal (+45 head-up ... -45 head-down, 90 seated)
* ``posture_deg``     angle of the body axis from VERTICAL = 90 - tilt_deg (0 seated, 90 supine,
                      135 = 45 deg head-down). The model code uses dP = rho * gz * g0 * dh * cos(posture_deg),
                      so cos(posture_deg) = sin(tilt_deg) = gz_body. NOTE: experiments/physiology.py currently
                      derives the angle from the ``posture`` string (seated -> 0, else 90); to use tilt rows
                      it must read ``posture_deg`` instead.
* ``gz_body``         head-to-foot component = gz * sin(tilt_deg)
* ``family``          supine / prone / seated (prone puts the neck veins on the other side of the heart
                      in the anterior-posterior direction - keep it as a covariate or analyse separately)

``include_unlicensed=False`` (default) uses only the MIT-licensed 12-person carotid-jugular set;
``True`` uses the 24-person tilt-dose-response set (no licence: team-internal use only).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

COHORT_COLUMNS = ["subject_id", "gender", "dataset", "condition", "family", "posture", "gz", "tilt_deg",
                  "posture_deg", "gz_body", "IJV_area_mm2", "IJV_pressure_mmHg", "heart_rate_bpm",
                  "plausible_pressure", "provenance"]


def real_ijv_cohort(data_dir: Path = Path("data"), include_unlicensed: bool = False) -> pd.DataFrame:
    from vascushift.analysis.gravity_physiology import subject_level
    from vascushift.data.schema import load_all_physiology

    df = load_all_physiology(Path(data_dir), include_unlicensed=include_unlicensed)
    ds = "bhp_tilt_dose_response" if include_unlicensed else "bhp_carotid_jugular"
    keys = ["subject_id", "condition", "family", "posture", "tilt_deg", "gz_body", "sex"]
    area = subject_level(df, "ijv_area", [ds])
    press = subject_level(df, "ijv_pressure", [ds])
    out = area[keys + ["value"]].rename(columns={"value": "IJV_area_mm2"}).merge(
        press[keys + ["value", "plausible"]].rename(columns={"value": "IJV_pressure_mmHg", "plausible": "plausible_pressure"}),
        on=keys, how="outer")
    hr = subject_level(df, "heart_rate", [ds])
    if not hr.empty:
        out = out.merge(hr[keys + ["value"]].rename(columns={"value": "heart_rate_bpm"}), on=keys, how="left")
    else:
        out["heart_rate_bpm"] = np.nan
    out = out[out["condition"].str.contains("tilt|seated", na=False)]
    out["gender"] = out.pop("sex").replace("?", None)
    out["dataset"] = ds
    out["gz"] = 1.0
    out["posture_deg"] = 90.0 - out["tilt_deg"].astype(float)
    out["provenance"] = "raw_individual"
    return out[COHORT_COLUMNS].sort_values(["subject_id", "family", "tilt_deg"]).reset_index(drop=True)


def export_real_cohorts(data_dir: Path = Path("data")) -> dict:
    data_dir = Path(data_dir)
    paths = {"public": data_dir / "processed" / "ijv_gravity_cohort_real.csv",
             "internal": data_dir / "processed" / "internal" / "ijv_gravity_cohort_real_24.csv"}
    paths["internal"].parent.mkdir(parents=True, exist_ok=True)
    real_ijv_cohort(data_dir, include_unlicensed=False).to_csv(paths["public"], index=False)
    real_ijv_cohort(data_dir, include_unlicensed=True).to_csv(paths["internal"], index=False)
    return paths
