"""
Hydrostatic pressure calculations for altered gravity environments.
"""

import numpy as np
from typing import Union


RHO_BLOOD_KG_M3 = 1060.0       # Standard whole blood density (kg/m3)
G_EARTH_M_S2 = 9.80665         # Standard gravitational acceleration (m/s2)
PA_TO_MMHG = 0.00750062        # 1 Pascal to mmHg conversion


def compute_hydrostatic_pressure_drop(
    gz: Union[float, np.ndarray],
    delta_h: Union[float, np.ndarray] = 0.35,
    posture_angle_deg: Union[float, np.ndarray] = 0.0,
    rho: float = RHO_BLOOD_KG_M3,
) -> Union[float, np.ndarray]:
    """
    Computes the hydrostatic pressure gradient between the central thoracic reservoir
    and the cervical level (IJV):
        Delta P_h = rho * (gz * g0) * delta_h * cos(posture_angle)

    Args:
        gz: Gravitational factor along body z-axis (e.g. 0.0 for 0G, 1.0 for 1G).
        delta_h: Vertical anatomical distance in meters (heart to mid-IJV, nominal 0.35m).
        posture_angle_deg: Angle relative to vertical (0 deg = seated upright, 90 deg = supine).
        rho: Fluid density in kg/m3.

    Returns:
        Hydrostatic pressure drop in mmHg.
    """
    theta_rad = np.radians(posture_angle_deg)
    g_eff = gz * G_EARTH_M_S2
    delta_p_pa = rho * g_eff * delta_h * np.cos(theta_rad)
    return delta_p_pa * PA_TO_MMHG


def effective_gravity_components(
    gz: float,
    pitch_angle_deg: float = 0.0,
) -> float:
    """
    Computes the effective longitudinal z-axis gravitational acceleration
    taking into account aircraft or bed tilt pitch angle.
    """
    return gz * np.cos(np.radians(pitch_angle_deg))

