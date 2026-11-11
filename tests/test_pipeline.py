"""
Tests for the common formats, preprocessing and the windowed rPPG benchmark.

Unit tests run on synthetic signals (no data needed); tests marked by ``needs_*`` use the real
preprocessed outputs and are skipped when they are absent.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from vascushift.data.schema import (
    COMMON_PHYSIO_COLUMNS,
    OPTICAL_SESSION_COLUMNS,
    RPPG_WINDOW_COLUMNS,
    conform_columns,
)

REPO = Path(__file__).resolve().parent.parent
PROCESSED = REPO / "data/processed/rppg"
needs_processed = pytest.mark.skipif(not (PROCESSED / "sessions.csv").exists(), reason="run `vascushift.cli preprocess`")


def test_conform_columns_orders_and_rejects_unknown_provenance():
    df = pd.DataFrame({"method": ["pos"], "provenance": ["raw_individual"]})
    out = conform_columns(df, RPPG_WINDOW_COLUMNS)
    assert list(out.columns) == RPPG_WINDOW_COLUMNS and out["dataset"].isna().all()
    with pytest.raises(ValueError):
        conform_columns(pd.DataFrame({"provenance": ["measured_probably"]}), RPPG_WINDOW_COLUMNS)


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
