"""
ESA Headward Fluid Shift dataset loader.

DATA AUDIT 2026-11-04 (see docs/data_audit.md) - read before using this module:

* The ESA HREDA investigation HeadwardFluidShift_PARA (DOI 10.57780/esa-0ggni9p,
  82nd ESA/NASA parabolic flight campaign, June 2023, PI S.M.C. Lee) exists, but
  HREDA reports data_available=False, 0 files, results "under evaluation".
  No individual data can be downloaded.
* Lee et al., Front Physiol 2020 (DOI 10.3389/fphys.2020.00863) is a DIFFERENT,
  earlier campaign (1st ISLSWG campaign, June 2018, no 0-G parabolas). It
  publishes only group means / 95% CI; individual data are on request from
  NASA LSDA.
* Therefore ``generate_synthetic_esa_like_cohort()`` (formerly
  ``get_verified_published_cohort``) is SYNTHETIC: np.random draws around the
  Lee 2020 group means. Several of its variables are not in the paper at all
  (IJV pressure for all subjects/levels, supine HR/MAP). Never report results
  on it as "real ESA data". Real group-level values: ``vascushift.data.literature``.
"""

import os
import json
import warnings
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd

from vascushift.data.validation import validate_physiological_dataset, DataQualityReport


ESA_DOI = "10.57780/esa-0ggni9p"
ESA_ACRONYM = "HeadwardFluidShift_PARA"
HREDA_TAP_URL = "https://hreda.esac.esa.int/hreda-sl-tap/tap"


def query_hreda_tap(timeout_sec: float = 8.0) -> Dict[str, Any]:
    """
    Queries ESA HREDA TAP API for the latest status of HeadwardFluidShift_PARA.
    Returns status dictionary.
    """
    query = (
        f"SELECT investigation_id, investigation_unique_acronym, investigation_title, "
        f"investigation_doi, data_available, ancillary_data_available "
        f"FROM hreda.v_investigation WHERE investigation_unique_acronym = '{ESA_ACRONYM}'"
    )
    url = f"{HREDA_TAP_URL}/sync?REQUEST=doQuery&LANG=ADQL&FORMAT=json&QUERY={urllib.parse.quote(query)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "VascuShift-Audit/1.0"})
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            data = json.loads(resp.read().decode())
            rows = data.get("data", [])
            if rows:
                cols = [m["name"] for m in data.get("metadata", [])]
                record = dict(zip(cols, rows[0]))
                return {
                    "online": True,
                    "investigation_found": True,
                    "doi": record.get("investigation_doi"),
                    "title": record.get("investigation_title"),
                    "data_available": record.get("data_available"),
                    "ancillary_available": record.get("ancillary_data_available"),
                }
    except Exception as exc:
        return {
            "online": False,
            "error": str(exc),
            "investigation_found": False,
            "data_available": False,
        }
    return {
        "online": True,
        "investigation_found": False,
        "data_available": False,
    }


def generate_synthetic_esa_like_cohort() -> pd.DataFrame:
    """
    SYNTHETIC 9-subject x 5-condition table drawn with ``np.random.RandomState(42)``
    around the group means of Lee et al. (Frontiers in Physiology 2020, 11:863).
    It is NOT measured data: individual values are invented, and IJV pressure
    (all rows), supine HR/MAP and the 0.75/1.00-G pressures do not exist in the
    paper. The ``provenance`` column says so. The supine row is encoded as
    ``gz=0.0`` although the measurement was 1-G supine on the ground.

    Nine healthy participants (5 female, 4 male) evaluated across:
      - 1.00 Gz seated (baseline ground/flight)
      - 0.75 Gz seated (partial gravity)
      - 0.50 Gz seated (partial gravity)
      - 0.25 Gz seated (partial gravity)
      - 1.00 Gz supine (0-Gz fluid redistribution analog)

    Variables include:
      - IJV_area_mm2: Internal Jugular Vein cross-sectional area (mm2)
      - IJV_pressure_mmHg: Non-invasive venous pressure via compression sonography (mmHg)
      - IVC_diameter_cm: Inferior vena cava diameter (cm)
      - CCA_flow_ml_min: Common carotid artery blood flow (mL/min)
      - heart_rate_bpm: Heart rate (bpm)
      - mean_arterial_pressure_mmHg: Mean arterial pressure (mmHg)
    """
    # Group means used as centres of the random draws. Area/IVC/CCA and seated HR/MAP are
    # from Lee 2020 Tables 2-3. NOT in the paper (invented by the original author of this
    # function): the supine MAP/HR, every IJV pressure mean/SD below, and all SD values.
    # Lee 2020 reports IJV pressure only as 9.5 +/- 3.4 (0.50 G) and 19.1 +/- 7.6 mmHg
    # (1-G supine), n = 5 - see vascushift.data.literature.

    rng = np.random.RandomState(42)
    subjects = [f"sub-{i+1:02d}" for i in range(9)]
    genders = ["F", "F", "F", "F", "F", "M", "M", "M", "M"]

    # Subject-level baseline offsets (anatomical variability across subjects)
    subject_area_offsets = rng.normal(0.0, 6.0, size=9)
    subject_pressure_offsets = rng.normal(0.0, 1.5, size=9)
    subject_map_offsets = rng.normal(0.0, 7.0, size=9)
    subject_hr_offsets = rng.normal(0.0, 4.0, size=9)

    conditions = [
        # (gz, posture, mean_area, sd_area, mean_p, sd_p, mean_map, sd_map, mean_hr, sd_hr, mean_ivc, mean_cca)
        (1.00, "seated", 12.0, 4.2, 3.5, 1.2, 95.0, 9.8, 60.0, 5.2, 1.68, 786.0),
        (0.75, "seated", 24.0, 9.1, 6.8, 1.8, 89.0, 8.5, 58.0, 4.6, 1.66, 895.0),
        (0.50, "seated", 34.0, 11.5, 11.2, 2.4, 85.0, 9.2, 56.0, 4.2, 1.81, 845.0),
        (0.25, "seated", 68.0, 22.0, 17.5, 3.2, 80.0, 7.8, 56.0, 3.9, 1.69, 826.0),
        (0.00, "supine", 108.0, 25.0, 21.0, 4.0, 88.0, 8.8, 57.0, 4.5, 1.81, 836.0),
    ]

    records = []
    for s_idx, (sub_id, gender) in enumerate(zip(subjects, genders)):
        for gz, posture, m_a, s_a, m_p, s_p, m_map, s_map, m_hr, s_hr, m_ivc, m_cca in conditions:
            # Subject-specific realistic measurement with physiological coupling
            area = max(3.0, m_a + subject_area_offsets[s_idx] * (m_a / 30.0) + rng.normal(0, s_a * 0.45))
            pressure = max(0.5, m_p + subject_pressure_offsets[s_idx] + rng.normal(0, s_p * 0.4))
            map_val = max(55.0, m_map + subject_map_offsets[s_idx] + rng.normal(0, s_map * 0.35))
            hr_val = max(45.0, m_hr + subject_hr_offsets[s_idx] + rng.normal(0, s_hr * 0.35))
            ivc_val = max(0.8, m_ivc + rng.normal(0, 0.12))
            cca_val = max(400.0, m_cca + rng.normal(0, 75.0))
            flow_score = 1 if (gz >= 0.75 and posture == "seated") or (gz >= 0.50 and rng.rand() > 0.5) else 2

            records.append({
                "subject_id": sub_id,
                "gender": gender,
                "gz": gz,
                "posture": posture,
                "IJV_area_mm2": round(area, 2),
                "IJV_pressure_mmHg": round(pressure, 2),
                "IVC_diameter_cm": round(ivc_val, 3),
                "CCA_flow_ml_min": round(cca_val, 1),
                "heart_rate_bpm": round(hr_val, 1),
                "mean_arterial_pressure_mmHg": round(map_val, 1),
                "IJV_flow_score": flow_score,
                "provenance": "SYNTHETIC_random_draws_around_Lee2020_group_means",
            })

    df = pd.DataFrame(records)
    return df


def get_verified_published_cohort() -> pd.DataFrame:
    """Deprecated misleading name kept for backward compatibility; the data are synthetic."""
    warnings.warn(
        "get_verified_published_cohort() returns SYNTHETIC data; use generate_synthetic_esa_like_cohort() "
        "or vascushift.data.literature for real published values",
        DeprecationWarning,
        stacklevel=2,
    )
    return generate_synthetic_esa_like_cohort()


def load_esa_data(
    data_dir: Optional[str] = None,
    prefer_raw: bool = True,
) -> Tuple[pd.DataFrame, DataQualityReport, Dict[str, Any]]:
    """
    Loads the ESA Headward Fluid Shift dataset.
    If raw CSV/Excel files are present in `data_dir/raw/esa` (e.g. obtained from the PI or
    NASA LSDA), loads the first one. Otherwise falls back to the SYNTHETIC ESA-like cohort
    (``metadata["source"] == "synthetic_esa_like_cohort"``) and queries HREDA status.

    Returns:
        (DataFrame, DataQualityReport, metadata_dict)
    """
    if data_dir is None:
        data_dir = "data"

    raw_path = Path(data_dir) / "raw" / "esa"
    processed_path = Path(data_dir) / "processed" / "esa_headward_fluid_shift.csv"

    # Check for raw user files
    df = None
    source = "synthetic_esa_like_cohort"
    if prefer_raw and raw_path.exists():
        raw_files = list(raw_path.glob("*.csv")) + list(raw_path.glob("*.xlsx"))
        if raw_files:
            try:
                target_file = raw_files[0]
                if target_file.suffix == ".csv":
                    df = pd.read_csv(target_file)
                else:
                    df = pd.read_excel(target_file)
                source = f"raw_file:{target_file.name}"
            except Exception:
                df = None

    if df is None:
        df = generate_synthetic_esa_like_cohort()

    # Save to processed directory for reproducible downstream use
    os.makedirs(Path(data_dir) / "processed", exist_ok=True)
    df.to_csv(processed_path, index=False)

    # Validate dataset quality
    quality_report = validate_physiological_dataset(df)

    # Check HREDA metadata status
    hreda_status = query_hreda_tap()

    metadata = {
        "dataset_name": "ESA Headward Fluid Shift (synthetic stand-in unless source starts with raw_file)",
        "is_synthetic": source == "synthetic_esa_like_cohort",
        "investigation_acronym": ESA_ACRONYM,
        "doi": ESA_DOI,
        "source": source,
        "processed_path": str(processed_path),
        "n_samples": len(df),
        "n_subjects": int(df["subject_id"].nunique()),
        "gravity_levels": sorted(df["gz"].unique().tolist()),
        "hreda_status": hreda_status,
    }

    return df, quality_report, metadata

