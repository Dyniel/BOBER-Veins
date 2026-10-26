"""
Physiological Venous Simulator across Gravitational Conditions.
"""

from typing import Dict, Any, List, Optional, Union
import numpy as np
import pandas as pd

from vascushift.physics.compartments import (
    VenousCompartmentParameters,
    evaluate_compartment_equilibrium_numpy,
)


class VenousHemodynamicSimulator:
    """
    Simulates internal jugular vein (IJV) hemodynamics across gravity levels
    and posture angles using a physically constrained two-compartment model.
    """

    def __init__(self, params: Optional[VenousCompartmentParameters] = None):
        self.params = params if params is not None else VenousCompartmentParameters()

    def simulate_gravity_sweep(
        self,
        gravity_levels: Optional[List[float]] = None,
        posture_deg: float = 0.0,
    ) -> pd.DataFrame:
        """
        Runs a forward simulation across an array of gravity levels (e.g. 0.0 to 1.0 Gz).
        """
        if gravity_levels is None:
            gravity_levels = [0.0, 0.16, 0.25, 0.38, 0.50, 0.75, 1.00]

        gz_arr = np.array(gravity_levels, dtype=float)
        res = evaluate_compartment_equilibrium_numpy(
            gz=gz_arr,
            posture_deg=posture_deg,
            params=self.params,
        )

        df = pd.DataFrame({
            "gz": gz_arr,
            "posture_deg": posture_deg,
            "IJV_pressure_mmHg": np.round(res["IJV_pressure_mmHg"], 2),
            "IJV_area_mm2": np.round(res["IJV_area_mm2"], 2),
            "hydrostatic_drop_mmHg": np.round(res["hydrostatic_drop_mmHg"], 2),
        })
        return df

    def compute_sensitivity(
        self,
        param_name: str,
        param_values: List[float],
        gz_eval: float = 0.50,
        posture_deg: float = 0.0,
    ) -> pd.DataFrame:
        """
        Computes model sensitivity to a chosen physiological parameter.
        """
        records = []
        base_dict = vars(self.params).copy()
        for val in param_values:
            mod_dict = base_dict.copy()
            mod_dict[param_name] = val
            p = VenousCompartmentParameters(**mod_dict)
            res = evaluate_compartment_equilibrium_numpy(
                gz=np.array([gz_eval]),
                posture_deg=posture_deg,
                params=p,
            )
            records.append({
                "param_name": param_name,
                "param_value": val,
                "gz": gz_eval,
                "IJV_pressure_mmHg": float(res["IJV_pressure_mmHg"][0]),
                "IJV_area_mm2": float(res["IJV_area_mm2"][0]),
            })
        return pd.DataFrame(records)

