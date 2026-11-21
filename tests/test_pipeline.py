"""
Tests for the common formats, preprocessing and the windowed rPPG benchmark.

Unit tests run on synthetic signals (no data needed); tests marked by ``needs_*`` use the real
preprocessed outputs and are skipped when they are absent.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from vascushift.data.rppg_loader import generate_synthetic_rppg_session
from vascushift.data.schema import (
    COMMON_PHYSIO_COLUMNS,
    OPTICAL_SESSION_COLUMNS,
    RPPG_WINDOW_COLUMNS,
    conform_columns,
)
from vascushift.optical.benchmark import evaluate_session, summarize, window_bounds

REPO = Path(__file__).resolve().parent.parent
PROCESSED = REPO / "data/processed/rppg"
needs_processed = pytest.mark.skipif(not (PROCESSED / "sessions.csv").exists(), reason="run `vascushift.cli preprocess`")


def test_conform_columns_orders_and_rejects_unknown_provenance():
    df = pd.DataFrame({"method": ["pos"], "provenance": ["raw_individual"]})
    out = conform_columns(df, RPPG_WINDOW_COLUMNS)
    assert list(out.columns) == RPPG_WINDOW_COLUMNS and out["dataset"].isna().all()
    with pytest.raises(ValueError):
        conform_columns(pd.DataFrame({"provenance": ["measured_probably"]}), RPPG_WINDOW_COLUMNS)


def test_window_bounds():
    assert window_bounds(300, 30.0, None) == [(0, 300)]
    b = window_bounds(900, 30.0, (10.0, 2.0))
    assert b[0] == (0, 300) and b[1] == (60, 360) and b[-1][1] <= 900 and len(b) == 11


@pytest.mark.parametrize("hr", [55.0, 72.0, 118.0])
def test_benchmark_recovers_known_hr_on_synthetic_session(hr):
    s = generate_synthetic_rppg_session(heart_rate_bpm=hr, duration_sec=60, motion_noise_amplitude=0.02, seed=3)
    s["is_real"] = False
    rows = pd.DataFrame(evaluate_session(s))
    assert set(rows["provenance"]) == {"synthetic"}  # never labelled as real
    for proto in ("whole", "w30s15", "w10s2"):
        r = rows[(rows.protocol == proto) & (rows.method == "pos")]
        assert np.abs(r["hr_ref_bpm"] - hr).max() < 2.5, proto
        assert r["error_bpm"].abs().median() < 2.0, proto


def test_window_with_dropped_frames_is_excluded():
    s = generate_synthetic_rppg_session(heart_rate_bpm=70, duration_sec=40, seed=1)
    s["valid"] = np.ones(len(s["time"]), bool)
    s["valid"][100:140] = False  # 1.33 s hole (13 %) inside the first 10 s window [0, 300)
    rows = pd.DataFrame(evaluate_session(s, protocols={"w10s2": (10.0, 2.0)}))
    first = rows[rows.t_start_s == 0.0]
    assert (~first["included"]).all() and (first["exclusion_reason"] == "dropped_frames_or_no_face").all()
    assert rows["included"].mean() > 0.5


def test_summarize_cluster_bootstrap_and_bland_altman():
    rng = np.random.default_rng(0)
    rows = []
    for s in range(6):
        for _w in range(10):
            e = rng.normal(0.5, 1.0)
            rows.append({"subset": "A", "protocol": "p", "method": "m", "session_id": f"s{s}",
                         "hr_ref_bpm": 70 + s, "hr_est_bpm": 70 + s + e, "error_bpm": e, "snr_db": 3.0, "included": True})
    summ = summarize(pd.DataFrame(rows)).iloc[0]
    assert summ.n_sessions == 6 and summ.n_windows == 60
    assert summ.mae_ci_low <= summ.mae_bpm <= summ.mae_ci_high
    assert summ.loa_low_bpm < summ.bias_bpm < summ.loa_high_bpm


@needs_processed
def test_preprocessed_index_and_session_files():
    from vascushift.data.preprocess import load_optical_index, load_optical_session

    idx = load_optical_index(PROCESSED)
    assert list(idx.columns) == OPTICAL_SESSION_COLUMNS
    assert set(idx["provenance"]) == {"raw_individual"}
    assert (idx["fs"] == 30.0).all() and idx["session_id"].is_unique
    d2 = idx[idx.subset == "DATASET_2"]
    if len(d2):
        assert (d2["frame_clock"] == "gt_frame_clock").all()
        assert d2.loc[d2.session_id == "ubfc-d2-subject27", "no_face_display"].all()
    first = PROCESSED / idx["file"].iloc[0]
    if not first.exists():
        pytest.skip("session waveforms are not in git (UBFC agreement); run `vascushift.cli preprocess`")
    s = load_optical_session(first)
    n = len(s["time"])
    assert s["rgb_traces"].shape == (n, 3) and len(s["ref_bvp"]) == len(s["valid"]) == n
    assert np.allclose(np.diff(s["time"]), 1 / 30.0)


@pytest.mark.skipif(not (REPO / "data/processed/physiology_long.csv").exists(), reason="run preprocess")
def test_public_physiology_table_has_only_licensed_sources():
    df = pd.read_csv(REPO / "data/processed/physiology_long.csv")
    assert list(df.columns) == COMMON_PHYSIO_COLUMNS
    assert not df["dataset"].isin(["bhp_tilt_dose_response", "bhp_lbnp_dose_response"]).any()
    assert "synthetic" not in set(df["provenance"])


# --------------------------------------------------------------------------- physiology analysis (unit)
def _toy_tilt(n_subj=6, seed=0):
    """Toy long table: ln(area) falls linearly with gz_body, pressure linear; values are synthetic test fixtures."""
    rng = np.random.default_rng(seed)
    rows = []
    for s in range(n_subj):
        for fam in ("supine", "prone"):
            for tilt in (-45, -30, -15, 0, 15, 30, 45):
                gzb = float(np.sin(np.radians(tilt)))
                post = fam if tilt == 0 else f"{fam}_{'hut' if tilt > 0 else 'hdt'}"
                base = {"dataset": "toy", "subject_id": f"t{s}", "sex": None, "condition": f"{fam}_tilt_{tilt:+d}",
                        "posture": post, "tilt_deg": float(tilt), "gz_body": gzb, "lbnp_mmHg": 0.0,
                        "provenance": "raw_individual"}
                area = 60 * np.exp(-2.0 * gzb) * np.exp(rng.normal(0, 0.05))
                rows.append({**base, "variable": "ijv_area_left", "value": area * 0.9})
                rows.append({**base, "variable": "ijv_area_right", "value": area * 1.1})
                rows.append({**base, "variable": "ijv_pressure_left", "value": 25 - 20 * gzb + rng.normal(0, 1)})
    return pd.DataFrame(rows)


def test_subject_level_averages_sides_and_flags_implausible():
    from vascushift.analysis.gravity_physiology import subject_level

    df = _toy_tilt()
    df.loc[df.index[2], "value"] = 150.0  # an IJVP far above 60 mmHg
    sub = subject_level(df, "ijv_area", ["toy"])
    assert (sub["n_sides"] == 2).all()
    one = sub[(sub.subject_id == "t0") & (sub.condition == "supine_tilt_+0")]["value"].iloc[0]
    raw = df[(df.subject_id == "t0") & (df.condition == "supine_tilt_+0") & df.variable.str.startswith("ijv_area")]["value"].mean()
    assert one == pytest.approx(raw)
    press = subject_level(df, "ijv_pressure", ["toy"])
    assert (~press["plausible"]).sum() == 1


def test_tilt_slopes_recover_known_log_slope():
    from vascushift.analysis.gravity_physiology import subject_level, summarize_slopes, tilt_slopes

    sub = subject_level(_toy_tilt(), "ijv_area", ["toy"])
    s = tilt_slopes(sub, log=True)
    summ = summarize_slopes(s, log=True)
    for _, r in summ.iterrows():
        assert r.median_slope == pytest.approx(-2.0, abs=0.1)
        assert r.ci_low <= r.median_slope <= r.ci_high and r.fraction_negative == 1.0
        assert r.pct_change_per_0p5g == pytest.approx((np.exp(-1.0) - 1) * 100, abs=4)


def test_lbnp_slopes_keep_supine_and_hdt_series_apart():
    from vascushift.analysis.gravity_physiology import lbnp_slopes

    rows = []
    for s in range(5):
        for ser, base, fam_posture in (("supine", 50.0, "supine"), ("hdt15", 100.0, "supine_hdt")):
            for lb in (0, -10, -20, -30, -40, -50):
                rows.append({"subject_id": f"s{s}", "condition": f"{ser}_lbnp_{lb:+d}", "family": "supine",
                             "posture": fam_posture, "lbnp_mmHg": float(lb), "value": base * 0.9 ** (-lb / 10)})
    out = lbnp_slopes(pd.DataFrame(rows)).set_index("family")
    assert set(out.index) == {"supine", "hdt15"}
    assert out.loc["supine", "median_pct_per_10mmHg"] == pytest.approx(-10.0, abs=0.01)


# --------------------------------------------------------------------------- real outputs (skipped if absent)
REPORTS = REPO / "reports"


@pytest.mark.skipif(not (REPO / "data/processed/ijv_gravity_cohort_real.csv").exists(), reason="run pipeline")
def test_real_ijv_cohort_geometry_columns():
    df = pd.read_csv(REPO / "data/processed/ijv_gravity_cohort_real.csv")
    assert df["subject_id"].nunique() == 12 and set(df["provenance"]) == {"raw_individual"}
    assert np.allclose(np.cos(np.radians(df["posture_deg"])), df["gz_body"], atol=1e-3)
    assert set(df["dataset"]) == {"bhp_carotid_jugular"}  # public file: MIT data only


@pytest.mark.skipif(not (REPORTS / "physiology_real/tilt_slopes_summary.csv").exists(), reason="run pipeline")
def test_real_ijv_area_decreases_with_gz_body_in_everyone():
    s = pd.read_csv(REPORTS / "physiology_real/tilt_slopes_summary.csv")
    area = s[(s.variable == "ijv_area") & (~s.plausible_only)]
    assert len(area) == 2 and (area["ci_high"] < 0).all() and (area["fraction_negative"] == 1.0).all()


DASH_PUBLIC = REPO / "demo/data/public/dashboard_data.json"


@pytest.mark.skipif(not DASH_PUBLIC.exists(), reason="run pipeline")
def test_public_dashboard_bundle_has_no_waveforms_or_unlicensed_data():
    import json

    txt = DASH_PUBLIC.read_text()
    d = json.loads(txt)  # strict JSON: allow_nan=False at export, so no NaN/Infinity tokens
    assert "waveforms" not in d and "NaN" not in txt
    assert "bhp_tilt_dose_response" not in json.dumps(d["physiology"])
    assert "bhp_lbnp_dose_response" not in json.dumps(d["physiology"])
    assert d["model"].get("provenance") in ("model", None)
    assert len(d["rppg"]["sessions"]) == len(pd.read_csv(REPO / "data/processed/rppg/sessions.csv"))
    js = (REPO / "demo/data/public/dashboard_data.js").read_text()
    assert js.startswith("window.VASCU_PUBLIC = ")


def test_pipeline_rejects_unknown_stage():
    from vascushift.pipeline import run_pipeline

    with pytest.raises(ValueError):
        run_pipeline(stages=["preprocess", "train_rocket"])


def test_preprocess_ubfc_is_idempotent_and_rebuilds_on_param_change(tmp_path, monkeypatch):
    """Second run reuses the session files; a different grid rate forces a rebuild (no real data needed)."""
    import vascushift.data.ubfc as ubfc
    from vascushift.data.preprocess import load_optical_index, preprocess_ubfc

    root = tmp_path / "raw" / "rppg" / "UBFC-rPPG" / "DATASET_2" / "subject3"
    root.mkdir(parents=True)
    (root / "vid.avi").write_bytes(b"x")
    gt = root / "ground_truth.txt"
    t = np.arange(0, 20, 1 / 30.0)
    gt.write_text("\n".join(" ".join(f"{v:.6e}" for v in row) for row in (np.sin(2 * np.pi * 1.2 * t), np.full(len(t), 72.0), t)))
    calls = {"n": 0}

    def fake_load(session, cache_dir=None, max_frames=None, fs_out=30.0, max_interp_gap_s=0.25):
        calls["n"] += 1
        tt = np.arange(0, 20, 1 / fs_out)
        return {"time": tt, "rgb_traces": np.ones((len(tt), 3)), "ref_bvp": np.sin(2 * np.pi * 1.2 * tt),
                "valid": np.ones(len(tt), bool), "face_found": np.ones(len(tt), bool), "ref_hr_bpm": 72.0,
                "frames": {"t": t, "clock": "gt_frame_clock"}}

    monkeypatch.setattr(ubfc, "load_ubfc_session", fake_load)
    preprocess_ubfc(data_dir=tmp_path, verbose=False)
    preprocess_ubfc(data_dir=tmp_path, verbose=False)
    assert calls["n"] == 1  # reused
    preprocess_ubfc(data_dir=tmp_path, fs_out=25.0, verbose=False)
    assert calls["n"] == 2  # parameters changed -> rebuilt
    idx = load_optical_index(tmp_path / "processed" / "rppg")
    assert idx["fs"].iloc[0] == 25.0 and idx["session_id"].iloc[0] == "ubfc-d2-subject3"


# --------------------------------------------------------------------------- improved optical track
def test_viterbi_repairs_isolated_artefact_window():
    from vascushift.optical.tracking import viterbi_track, window_spectrum

    fs, rng = 30.0, np.random.default_rng(0)
    spectra, truth = [], []
    for k in range(20):
        hr = 75 + 0.3 * k
        t = np.arange(0, 10, 1 / fs)
        x = np.sin(2 * np.pi * hr / 60 * t) + 0.3 * rng.normal(size=len(t))
        if k == 10:  # one window where a strong 52 bpm artefact dominates
            x = x + 3.0 * np.sin(2 * np.pi * 52 / 60 * t)
        spectra.append(window_spectrum(x, fs))
        truth.append(hr)
    peaks = np.array([f[np.argmax(p)] * 60 for f, p in spectra])
    path = viterbi_track(spectra, sigma_bpm=10.0)
    assert abs(peaks[10] - 52) < 2  # independent peak picking is fooled
    assert np.max(np.abs(path - np.array(truth))) < 2.5  # tracking is not


def test_spectral_quality_separates_clean_from_noise():
    from vascushift.optical.tracking import spectral_quality

    fs, t = 30.0, np.arange(0, 10, 1 / 30.0)
    rng = np.random.default_rng(1)
    clean = np.sin(2 * np.pi * 1.3 * t) + 0.1 * rng.normal(size=len(t))
    noise = rng.normal(size=len(t))
    q_clean, q_noise = spectral_quality(clean, fs), spectral_quality(noise, fs)
    assert 0 <= q_noise < q_clean <= 1 and q_clean > 0.5


def test_split_assignment_and_improved_track_skips_without_cache(tmp_path):
    from vascushift.optical.improved import run_rppg_improved, split_of

    assert split_of("ubfc-d2-subject12", "DATASET_2") == "tune"
    assert split_of("ubfc-d2-subject13", "DATASET_2") == "holdout"
    assert split_of("ubfc-d1-12-gt", "DATASET_1") == "holdout"
    r = run_rppg_improved(data_dir=tmp_path, out_dir=tmp_path / "out", verbose=False)
    assert r["available"] is False and "run_roi_variants" in r["reason"]


@pytest.mark.skipif(not (REPO / "reports/rppg_improved/summary.json").exists(), reason="improved track not run")
def test_improved_track_beats_baseline_on_holdout():
    import json

    r = json.loads((REPO / "reports/rppg_improved/summary.json").read_text())
    imp = {g["group"]: g for g in r["summary"]}["split=holdout"]
    base = {g["group"]: g for g in r["baseline_pos_summary"]}["split=holdout"]
    assert imp["n_windows"] == base["n_windows"]
    assert imp["mae_bpm"] < base["mae_bpm"] and imp["rmse_bpm"] < base["rmse_bpm"]
