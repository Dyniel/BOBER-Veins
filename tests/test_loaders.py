"""
Tests for the dataset registry and the real-data loaders (UBFC-rPPG, PhysioNet
posture datasets, transcribed literature values).

Tests that need downloaded raw data are skipped when the files are absent
(run ``python scripts/download_data.py --dataset physionet`` / ``--dataset ubfc``).
"""

from pathlib import Path

import pandas as pd
import pytest

from vascushift.data.literature import COMMON_PHYSIO_COLUMNS, literature_aggregates
from vascushift.data.physionet_posture import event_kind
from vascushift.data.registry import DATASETS

REPO = Path(__file__).resolve().parent.parent
PRCP = REPO / "data/raw/physionet/prcp/1.0.0"
ORTHO = REPO / "data/raw/physionet/cardioresp-response-orthostat/1.0"


# --------------------------------------------------------------------------- registry
def test_registry_status_vocabulary():
    allowed = {"downloaded", "transcribed", "metadata_only", "login_required", "request_required", "synthetic"}
    for key, meta in DATASETS.items():
        assert meta["status"] in allowed, key
        assert meta.get("layer") in {"physiology", "optical"}, key


def test_registry_flags_synthetic_and_unavailable_esa():
    assert DATASETS["esa_hreda_headward_fluid_shift"]["status"] == "metadata_only"
    assert DATASETS["synthetic_esa_like_cohort"]["status"] == "synthetic"


# --------------------------------------------------------------------------- literature
def test_literature_table_schema_and_provenance():
    df = literature_aggregates()
    assert list(df.columns) == COMMON_PHYSIO_COLUMNS
    assert (df["provenance"] == "published_aggregate").all()
    assert df["source"].str.contains("doi:").all()


@pytest.mark.parametrize("dataset,condition,variable,value", [
    ("lee2020_partial_gravity", "seated_1.00G", "ijv_area_right", 12),       # Table 3
    ("lee2020_partial_gravity", "seated_0.25G", "ijv_area_right", 68),       # Table 3
    ("lee2020_partial_gravity", "supine_1.00G", "ijv_area_right", 108),      # Table 3 (abstract: 103)
    ("lee2020_partial_gravity", "seated_0.50G", "mean_arterial_pressure", 85),  # Table 2
    ("lee2020_partial_gravity", "seated_0.50G", "ijv_pressure", 9.5),        # Results text
    ("marshall_goebel2019_iss_ijv", "iss_fd50", "ijv_area_left", 70.3),
    ("marshall_goebel2019_iss_ijv", "preflight_supine", "ijv_pressure", 17.3),
    ("marshall_goebel2019_iss_ijv", "preflight_seated", "stroke_volume", 69),
    ("martin2016_parabolic_ijvp", "seated_0G", "ijv_pressure", 23.9),
])
def test_literature_spot_values(dataset, condition, variable, value):
    df = literature_aggregates()
    row = df[(df.dataset == dataset) & (df.condition == condition) & (df.variable == variable)]
    assert len(row) == 1
    assert row["value"].iloc[0] == pytest.approx(value)


def test_literature_gravity_semantics():
    df = literature_aggregates()
    supine = df[(df.dataset == "lee2020_partial_gravity") & (df.condition == "supine_1.00G")].iloc[0]
    assert supine.gz_platform == 1.0 and supine.gz_body == 0.0  # 1-G supine is NOT 0 G
    hdt = df[df.condition == "preflight_hdt15"].iloc[0]
    assert hdt.gz_body == pytest.approx(-0.259, abs=1e-3)
    iss = df[df.condition == "iss_fd50"].iloc[0]
    assert iss.gz_platform == 0.0 and iss.gz_body == 0.0
    # the 0.75 / 1.00 G seated IJV pressures do not exist in Lee 2020
    lee_p = df[(df.dataset == "lee2020_partial_gravity") & (df.variable == "ijv_pressure")]
    assert set(lee_p.condition) == {"seated_0.50G", "supine_1.00G"}


def test_literature_typo_kept_as_missing():
    df = literature_aggregates()
    row = df[(df.condition == "iss_fd150_lbnp25") & (df.variable == "heart_rate")].iloc[0]
    assert pd.isna(row["value"]) and "typo" in row["notes"]


# --------------------------------------------------------------------------- PRCP
@pytest.mark.parametrize("text,kind", [
    ("Initiate slow tilt up", "tilt_up_start"),
    ("Start fast tilt up", "tilt_up_start"),
    ("Initiation of rapid tilt down", "tilt_down_start"),
    ("Conclude slow tilt dow", "tilt_down_end"),
    ("Conslusion of slow tilt down", "tilt_down_end"),
    ("0 -1 0 \tStand up", "stand_up"),
    ("Stand-up from supine", "stand_up"),
    ("Transition back to supin", "back_to_supine"),
    ("Back to supine", "back_to_supine"),
    ("Failed attempt to tilt rapidly", "other"),
    ("Switched off Finapres", "other"),
])
def test_prcp_event_normalisation(text, kind):
    assert event_kind(text) == kind


@pytest.mark.skipif(not PRCP.exists(), reason="PRCP not downloaded")
def test_prcp_condition_summary_real_data():
    from vascushift.data.physionet_posture import prcp_condition_summary

    df = prcp_condition_summary(PRCP)
    assert df["subject_id"].nunique() == 10
    assert set(df["condition"]) == {"supine", "hut75", "standing"}
    hr = df[df.variable == "heart_rate"].pivot(index="subject_id", columns="condition", values="value")
    # orthostatic tachycardia: HR higher at 75 deg head-up tilt than supine in every subject
    assert (hr["hut75"] > hr["supine"]).all()
    gz = df[df.condition == "hut75"]["gz_body"]
    assert gz.between(0.93, 0.98).all()  # sin(70..78 deg)


@pytest.mark.skipif(not ORTHO.exists(), reason="orthostat dataset not downloaded")
def test_orthostat_loader_real_data():
    from vascushift.data.physionet_posture import list_orthostat_subjects, load_orthostat_subject

    subs = list_orthostat_subjects(ORTHO)
    assert len(subs) == 10
    d = load_orthostat_subject("subj01", ORTHO)
    assert d["data"].shape[1] == 53 and 3.0 < d["fs"] < 3.5
    assert "i16_805" in d["data"].columns


# --------------------------------------------------------------------------- BHP-Lab (GitHub)
GH = REPO / "data/raw/github"


@pytest.mark.skipif(not (GH / "carotid-jugular-characteristics").exists(), reason="BHP-Lab data not downloaded")
def test_bhp_carotid_jugular_real_data():
    from vascushift.data.bhp_lab import dose_response_table, load_carotid_jugular
    from vascushift.data.schema import COMMON_PHYSIO_COLUMNS

    df = load_carotid_jugular(GH / "carotid-jugular-characteristics")
    assert list(df.columns) == COMMON_PHYSIO_COLUMNS
    assert df["subject_id"].nunique() == 12
    assert set(df["gz_body"].round(2)) == {1.0, 0.71, 0.5, 0.26, 0.0, -0.26, -0.5, -0.71}
    tab = dose_response_table(df[df.posture.str.startswith("supine")], "ijv_area_right").set_index("tilt_deg")
    # jugular filling increases monotonically from head-up to head-down tilt (group medians)
    assert tab.loc[45.0, "median"] < tab.loc[0.0, "median"] < tab.loc[-15.0, "median"]


@pytest.mark.skipif(not (GH / "LBNP-Dose-Response").exists(), reason="LBNP data not downloaded")
def test_bhp_lbnp_reduces_ijv_area():
    from vascushift.data.bhp_lab import load_lbnp_dose_response

    df = load_lbnp_dose_response(GH / "LBNP-Dose-Response")
    d = df[(df.variable == "ijv_area_right") & (df.tilt_deg == -15.0)]
    med = d.groupby("lbnp_mmHg")["value"].median()
    assert med.loc[-50.0] < med.loc[0.0]


def test_load_all_physiology_never_contains_synthetic():
    from vascushift.data.schema import load_all_physiology

    df = load_all_physiology(REPO / "data")
    assert "synthetic" not in set(df["provenance"])
    assert {"lee2020_partial_gravity", "marshall_goebel2019_iss_ijv"} <= set(df["dataset"])
