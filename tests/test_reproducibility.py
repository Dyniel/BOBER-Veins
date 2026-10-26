"""
End-to-end reproducibility and determinism tests.
"""

import numpy as np
import pytest

from vascushift.data.esa_loader import get_verified_published_cohort
from vascushift.physics.simulator import VenousHemodynamicSimulator
from vascushift.models.physics_informed import VascuShiftPINN


def test_deterministic_cohort_generation():
    """Generating cohort twice with same seed must yield identical dataframes."""
    df1 = get_verified_published_cohort()
    df2 = get_verified_published_cohort()
    assert df1.equals(df2)


def test_deterministic_pinn_predictions():
    """PINN with fixed seed must yield identical predictions."""
    gz = np.array([0.0, 0.5, 1.0])
    area = np.array([108.0, 34.0, 12.0])

    m1 = VascuShiftPINN(epochs=20, seed=999).fit(gz, area)
    p1 = m1.predict(gz)

    m2 = VascuShiftPINN(epochs=20, seed=999).fit(gz, area)
    p2 = m2.predict(gz)

    assert np.allclose(p1, p2, atol=1e-5)

