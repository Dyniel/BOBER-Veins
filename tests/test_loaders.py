"""
Tests for the dataset registry and the real-data loaders (UBFC-rPPG, PhysioNet
posture datasets, transcribed literature values).

Tests that need downloaded raw data are skipped when the files are absent
(run ``python scripts/download_data.py --dataset physionet`` / ``--dataset ubfc``).
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from vascushift.data.literature import COMMON_PHYSIO_COLUMNS, literature_aggregates
from vascushift.data.physionet_posture import event_kind
from vascushift.data.registry import DATASETS
from vascushift.data.ubfc import (
    UbfcSession,
    list_ubfc_sessions,
    load_ubfc_ground_truth,
    reference_hr_from_ppg,
)

REPO = Path(__file__).resolve().parent.parent
PRCP = REPO / "data/raw/physionet/prcp/1.0.0"
ORTHO = REPO / "data/raw/physionet/cardioresp-response-orthostat/1.0"
UBFC = REPO / "data/raw/rppg/UBFC-rPPG"


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


# --------------------------------------------------------------------------- UBFC format (fixtures)
def _session(tmp_path, subset, name, text):
    folder = tmp_path / subset / name
    folder.mkdir(parents=True)
    gt = folder / ("ground_truth.txt" if subset == "DATASET_2" else "gtdump.xmp")
    gt.write_text(text)
    return UbfcSession(subset=subset, subject=name, folder=folder, video_path=folder / "vid.avi", gt_path=gt)


def test_ubfc_dataset2_gt_cleaning(tmp_path):
    t = np.array([0.0, 0.033, 0.033, 0.066, 0.9, 0.933])  # duplicate stamp + 0.834 s gap
    ppg = np.arange(6, dtype=float)
    hr = np.array([80, 80, 80, 1, 81, 81], dtype=float)  # sensor dropout
    text = "\n".join(" ".join(f"{v:.6e}" for v in row) for row in (ppg, hr, t))
    s = _session(tmp_path, "DATASET_2", "subject1", text)
    gt = load_ubfc_ground_truth(s)
    assert gt.n_raw_samples == 6 and gt.n_duplicate_t == 1
    assert np.all(np.diff(gt.t) > 0)
    assert gt.max_gap_s == pytest.approx(0.834, abs=1e-6)
    assert gt.n_hr_dropouts == 1


def test_ubfc_dataset1_gt_parsing(tmp_path):
    lines = [f"{i * 16},{75},{98},{100 + i}" for i in range(50)]  # t[ms], HR, SpO2, PPG
    s = _session(tmp_path, "DATASET_1", "5-gt", "\n".join(lines))
    gt = load_ubfc_ground_truth(s)
    assert gt.spo2 is not None and gt.spo2.mean() == 98
    assert gt.mean_fs == pytest.approx(62.5, rel=1e-6)


def test_reference_hr_from_ppg_recovers_sine():
    fs = 30.0
    t = np.arange(0, 40, 1 / fs)
    ppg = np.sin(2 * np.pi * (72 / 60) * t) + 0.1 * np.random.RandomState(0).randn(len(t))
    assert reference_hr_from_ppg(ppg, fs) == pytest.approx(72, abs=1.0)
    win = reference_hr_from_ppg(ppg, fs, window_s=10, stride_s=5)
    assert len(win) == 7 and np.allclose(win, 72, atol=1.5)


def test_align_to_uniform_grid_irregular_frame_clock():
    from vascushift.data.ubfc import align_to_uniform_grid

    rng = np.random.RandomState(1)
    # ~29.5 fps with jitter and one 0.8 s dropped-frame hole at t = 20 s
    steps = 1 / 29.5 + rng.uniform(-0.004, 0.004, 1800)
    steps[600] = 0.8
    t = np.cumsum(np.concatenate([[0.0], steps]))
    hr_hz = 84 / 60
    pulse = np.sin(2 * np.pi * hr_hz * t)
    rgb = np.column_stack([100 + 0.2 * pulse, 120 + 0.5 * pulse, 90 + 0.1 * pulse])
    face = np.ones(len(t), dtype=bool)
    face[:5] = False
    rgb[:5] = np.nan  # no face box yet
    g = align_to_uniform_grid(t, rgb, face, t, pulse, fs_out=30.0)

    assert np.allclose(np.diff(g["time"]), 1 / 30)
    assert len(g["time"]) == len(g["rgb"]) == len(g["ppg"]) == len(g["valid"])
    assert np.isfinite(g["rgb"]).all()
    hole = (g["time"] > t[600]) & (g["time"] < t[601])
    assert hole.sum() >= 20 and not g["valid"][hole].any()
    assert g["valid"][g["time"] > 1.0].mean() > 0.95
    # the true PPG on the frame clock stays phase-locked to the grid: PPG at grid time == sin(grid time)
    ok = g["valid"]
    assert np.max(np.abs(g["ppg"][ok] - np.sin(2 * np.pi * hr_hz * g["time"][ok]))) < 0.05
    assert reference_hr_from_ppg(g["ppg"], 30.0) == pytest.approx(84, abs=1.0)


def test_frame_clock_dataset2_uses_gt_rows(tmp_path):
    from vascushift.data.ubfc import frame_clock

    t = np.array([5.0, 5.033, 5.033, 5.07, 6.0, 6.033])
    text = "\n".join(" ".join(f"{v:.6e}" for v in row) for row in (np.arange(6.0), np.full(6, 80.0), t))
    s = _session(tmp_path, "DATASET_2", "subject3", text)
    tf, keep, clock = frame_clock(s, 6, 29.0)
    assert clock == "gt_frame_clock"
    assert np.allclose(tf, t - 5.0) and keep.tolist() == [True, True, False, True, True, True]
    tf, keep, clock = frame_clock(s, 4, 29.0)  # max_frames < rows
    assert clock == "gt_frame_clock" and len(tf) == 4
    s1 = _session(tmp_path, "DATASET_1", "5-gt", "0,80,98,1\n16,80,98,2")
    tf, keep, clock = frame_clock(s1, 3, 28.67)
    assert clock == "uniform_header_fps" and np.allclose(tf, np.arange(3) / 28.67)


def test_list_ubfc_sessions_marks_display_restrictions(tmp_path):
    _session(tmp_path, "DATASET_2", "subject27", "1 2\n80 80\n0 0.03")
    _session(tmp_path, "DATASET_2", "subject3", "1 2\n80 80\n0 0.03")
    sess = list_ubfc_sessions(tmp_path, subsets=("DATASET_2",))
    assert [s.subject for s in sess] == ["subject3", "subject27"]  # natural order
    assert [s.no_face_display for s in sess] == [False, True]


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


# --------------------------------------------------------------------------- UBFC real
@pytest.mark.skipif(not UBFC.exists(), reason="UBFC-rPPG not downloaded")
def test_ubfc_real_ground_truth_inventory():
    sessions = list_ubfc_sessions(UBFC)
    assert sum(s.subset == "DATASET_2" for s in sessions) == 42
    assert sum(s.subset == "DATASET_1" for s in sessions) == 8
    for s in sessions:
        gt = load_ubfc_ground_truth(s)
        assert 40 < gt.duration_s < 125


@pytest.mark.skipif(not any(UBFC.glob("DATASET_*/*/vid.avi")), reason="no UBFC video downloaded")
def test_ubfc_real_video_session_smoke():
    from vascushift.data.ubfc import load_ubfc_session

    for s in [next((s for s in list_ubfc_sessions(UBFC, subsets=(sub,)) if s.has_video), None)
              for sub in ("DATASET_2", "DATASET_1")]:
        if s is None:
            continue
        d = load_ubfc_session(s, cache_dir=None, max_frames=300)
        assert d["frames"]["n_decoded"] == 300
        assert d["frames"]["clock"] == ("gt_frame_clock" if s.subset == "DATASET_2" else "uniform_header_fps")
        assert d["fs"] == 30.0
        n = len(d["time"])
        assert d["rgb_traces"].shape == (n, 3) and len(d["ref_bvp"]) == n == len(d["valid"])
        assert 250 < n < 400  # ~300 frames at 23-30 fps -> 10-13 s on a 30 Hz grid
        assert d["face_found"].mean() > 0.9


@pytest.mark.skipif(not any(UBFC.glob("DATASET_2/*/vid.avi")), reason="no UBFC DATASET_2 video downloaded")
def test_ubfc_dataset2_gt_rows_match_video_frames():
    """The fact the frame clock relies on: one GT row per video frame in every DATASET_2 session."""
    from vascushift.data.ubfc import video_info

    for s in list_ubfc_sessions(UBFC, subsets=("DATASET_2",)):
        if s.has_video:
            assert load_ubfc_ground_truth(s).n_raw_samples == video_info(s.video_path)["n_frames"], s.session_id


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


VP = REPO / "data/raw/physionet/videopulse/1.0.0"


@pytest.mark.skipif(not VP.exists(), reason="videopulse not downloaded")
def test_videopulse_loader_and_offset_sign():
    from vascushift.data.videopulse import list_records, load_record, offset_check

    recs = list_records(VP)
    assert len(recs) == 40
    r = load_record("subj_10_s_c1", VP)
    assert r["fs_vid"] == 15.0 and r["condition"] == "stationary" and r["camera"] == "c1"
    assert r["t_ref"][0] == pytest.approx(r["offset_s"])
    assert offset_check(r) == pytest.approx(r["offset_s"], abs=0.5)  # header offset = reference start on video clock


def test_align_to_uniform_grid_holds_last_row_when_face_lost_mid_recording():
    from vascushift.data.ubfc import align_to_uniform_grid

    t = np.arange(0, 20, 1 / 30.0)
    rgb = np.column_stack([np.full(len(t), 100.0), 120 + np.sin(2 * np.pi * 1.2 * t), np.full(len(t), 90.0)])
    face = np.ones(len(t), bool)
    rgb[300:330] = np.nan  # face lost for 1 s in the middle
    face[300:330] = False
    g = align_to_uniform_grid(t, rgb, face, t, np.sin(2 * np.pi * 1.2 * t), fs_out=30.0)
    assert np.isfinite(g["rgb"]).all()
    lost = (g["time"] > 10.05) & (g["time"] < 10.95)
    assert not g["valid"][lost].any() and g["valid"][g["time"] < 9.5].all()
