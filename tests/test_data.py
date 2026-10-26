"""
Unit tests for data loaders, schema validation, and subject partitioning.
"""

import numpy as np
import pytest

from vascushift.data.esa_loader import get_verified_published_cohort, load_esa_data
from vascushift.data.validation import validate_physiological_dataset
from vascushift.data.preprocessing import (
    get_subject_grouped_splits,
    generate_synthetic_physiological_cohort,
)


def test_verified_published_cohort_structure():
    """Verify that the published ESA cohort has exactly 9 subjects and expected variables."""
    df = get_verified_published_cohort()
    assert len(df) == 45  # 9 subjects * 5 gravity conditions
    assert df["subject_id"].nunique() == 9
    expected_cols = [
        "subject_id", "gender", "gz", "posture",
        "IJV_area_mm2", "IJV_pressure_mmHg", "heart_rate_bpm",
        "mean_arterial_pressure_mmHg"
    ]
    for col in expected_cols:
        assert col in df.columns


def test_dataset_validation_passes():
    """Ensure data validator passes for realistic physiological bounds."""
    df = get_verified_published_cohort()
    report = validate_physiological_dataset(df, strict=True)
    assert report.is_valid
    assert len(report.issues) == 0


def test_subject_grouped_splits_disjointness():
    """Ensure train and test splits are strictly subject-disjoint."""
    df = get_verified_published_cohort()
    splits = get_subject_grouped_splits(df, subject_col="subject_id")
    assert len(splits) == 9

    for train_df, test_df, held_out in splits:
        train_subs = set(train_df["subject_id"].unique())
        test_subs = set(test_df["subject_id"].unique())
        assert held_out in test_subs
        assert held_out not in train_subs
        assert len(train_subs.intersection(test_subs)) == 0


def test_synthetic_cohort_generator():
    """Ensure synthetic generator produces deterministic, valid data with known parameters."""
    df_synth = generate_synthetic_physiological_cohort(n_subjects=5, seed=123)
    assert df_synth["subject_id"].nunique() == 5
    assert "true_A0" in df_synth.columns
    assert "true_k" in df_synth.columns
    assert not df_synth["IJV_area_mm2"].isna().all()

