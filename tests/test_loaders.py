"""
Tests for the dataset registry and the real-data loaders (UBFC-rPPG, PhysioNet
posture datasets, transcribed literature values).

Tests that need downloaded raw data are skipped when the files are absent
(run ``python scripts/download_data.py --dataset physionet`` / ``--dataset ubfc``).
"""

from vascushift.data.registry import DATASETS


# --------------------------------------------------------------------------- registry
def test_registry_status_vocabulary():
    allowed = {"downloaded", "transcribed", "metadata_only", "login_required", "request_required", "synthetic"}
    for key, meta in DATASETS.items():
        assert meta["status"] in allowed, key
        assert meta.get("layer") in {"physiology", "optical"}, key


def test_registry_flags_synthetic_and_unavailable_esa():
    assert DATASETS["esa_hreda_headward_fluid_shift"]["status"] == "metadata_only"
    assert DATASETS["synthetic_esa_like_cohort"]["status"] == "synthetic"
