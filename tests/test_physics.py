"""
Unit tests for hydrostatic calculations and compartment physics.
"""

import numpy as np
import pytest

from vascushift.physics.hydrostatic import (
    compute_hydrostatic_pressure_drop,
    RHO_BLOOD_KG_M3,
    G_EARTH_M_S2,
    PA_TO_MMHG,
)
from vascushift.physics.compartments import (
    VenousCompartmentParameters,
    collapsible_vein_area_numpy,
    evaluate_compartment_equilibrium_numpy,
)
from vascushift.physics.simulator import VenousHemodynamicSimulator


def test_hydrostatic_pressure_upright_1g():
    """In upright 1G, hydrostatic pressure drop should be ~ 27.3 mmHg."""
    gz = 1.0
    dh = 0.35  # m
    dPh = compute_hydrostatic_pressure_drop(gz=gz, delta_h=dh, posture_angle_deg=0.0)
    # Expected: 1060 * 9.80665 * 0.35 * 0.00750062 = 27.28 mmHg
    assert 25.0 <= dPh <= 30.0


def test_hydrostatic_pressure_microgravity_0g():
    """In microgravity (0G), hydrostatic gradient must strictly be 0."""
    dPh = compute_hydrostatic_pressure_drop(gz=0.0, delta_h=0.35, posture_angle_deg=0.0)
    assert dPh == 0.0


def test_hydrostatic_pressure_supine():
    """In horizontal supine posture (theta = 90 deg), vertical column drop is 0."""
    dPh = compute_hydrostatic_pressure_drop(gz=1.0, delta_h=0.35, posture_angle_deg=90.0)
    assert np.isclose(dPh, 0.0, atol=1e-5)


def test_collapsible_vein_compliance_monotonicity():
    """Venous area must monotonically increase with transmural pressure."""
    p_range = np.linspace(-5.0, 30.0, 50)
    areas = collapsible_vein_area_numpy(p_range, A0=115.0, Amin=6.0, k=0.28, P0=3.5)
    diffs = np.diff(areas)
    assert np.all(diffs > 0)
    assert areas[0] >= 6.0
    assert areas[-1] <= 115.0


def test_compartment_equilibrium_gravity_sweep():
    """Higher gravity should produce smaller IJV area due to venous collapse."""
    sim = VenousHemodynamicSimulator()
    res = sim.simulate_gravity_sweep(gravity_levels=[0.0, 0.5, 1.0])
    areas = res["IJV_area_mm2"].values
    assert areas[0] > areas[1] > areas[2]

