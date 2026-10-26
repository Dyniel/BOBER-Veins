"""
Baseline 2 — Pure Mechanistic Parameter Estimator (Physics-Only, No Neural Networks).
Inverts physiological parameters from observed venous responses using nonlinear optimization.
"""

from typing import Dict, Any, Optional, Tuple, List
import numpy as np
from scipy.optimize import minimize, Bounds

from vascushift.physics.compartments import (
    VenousCompartmentParameters,
    evaluate_compartment_equilibrium_numpy,
)


class MechanisticParameterEstimator:
    """
    Fits physiological parameters (A0, k, P0, delta_h) of the two-compartment
    collapsible vein model to observed data using bounded nonlinear least squares.
    """

    def __init__(
        self,
        bounds: Optional[Dict[str, Tuple[float, float]]] = None,
        max_iter: int = 500,
    ):
        self.bounds_dict = bounds or {
            "A0": (40.0, 180.0),
            "k": (0.05, 0.80),
            "P0": (-2.0, 12.0),
            "CVP": (2.0, 12.0),
            "delta_h": (0.28, 0.42),
        }
        self.max_iter = max_iter
        self.fitted_params_: Optional[VenousCompartmentParameters] = None
        self.residual_loss_: float = np.inf
        self.success_: bool = False

    def fit(
        self,
        gz: np.ndarray,
        area_obs: np.ndarray,
        posture_deg: Optional[np.ndarray] = None,
        pressure_obs: Optional[np.ndarray] = None,
    ) -> "MechanisticParameterEstimator":
        gz = np.asarray(gz, dtype=float)
        area_obs = np.asarray(area_obs, dtype=float)
        if posture_deg is None:
            posture_deg = np.where(gz > 0.0, 0.0, 90.0)
        else:
            posture_deg = np.asarray(posture_deg, dtype=float)

        # Parameter vector: theta = [A0, k, P0, CVP, delta_h]
        p_names = ["A0", "k", "P0", "CVP", "delta_h"]
        x0 = [115.0, 0.28, 3.5, 5.5, 0.35]
        lower_bounds = [self.bounds_dict[p][0] for p in p_names]
        upper_bounds = [self.bounds_dict[p][1] for p in p_names]

        def objective(theta: np.ndarray) -> float:
            A0, k, P0, cvp, dh = theta
            p = VenousCompartmentParameters(
                A0=A0, k=k, P0=P0, CVP=cvp, delta_h=dh
            )
            sim = evaluate_compartment_equilibrium_numpy(
                gz=gz, posture_deg=posture_deg, params=p
            )
            pred_area = sim["IJV_area_mm2"]
            loss = np.mean((pred_area - area_obs) ** 2)
            if pressure_obs is not None:
                valid_mask = ~np.isnan(pressure_obs)
                if np.sum(valid_mask) > 0:
                    pred_p = sim["IJV_pressure_mmHg"]
                    loss += 0.5 * np.mean((pred_p[valid_mask] - pressure_obs[valid_mask]) ** 2)
            return float(loss)

        res = minimize(
            objective,
            x0=x0,
            bounds=Bounds(lower_bounds, upper_bounds),
            method="L-BFGS-B",
            options={"maxiter": self.max_iter, "ftol": 1e-7},
        )

        self.success_ = res.success
        self.residual_loss_ = float(res.fun)
        A0, k, P0, cvp, dh = res.x
        self.fitted_params_ = VenousCompartmentParameters(
            A0=A0, k=k, P0=P0, CVP=cvp, delta_h=dh
        )
        return self

    def predict(
        self,
        gz: np.ndarray,
        posture_deg: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        if self.fitted_params_ is None:
            raise ValueError("Model is not fitted.")
        gz = np.asarray(gz, dtype=float)
        if posture_deg is None:
            posture_deg = np.where(gz > 0.0, 0.0, 90.0)
        else:
            posture_deg = np.asarray(posture_deg, dtype=float)

        sim = evaluate_compartment_equilibrium_numpy(
            gz=gz, posture_deg=posture_deg, params=self.params
        )
        return sim["IJV_area_mm2"]

    @property
    def params(self) -> VenousCompartmentParameters:
        if self.fitted_params_ is None:
            raise ValueError("Model is not fitted.")
        return self.fitted_params_

