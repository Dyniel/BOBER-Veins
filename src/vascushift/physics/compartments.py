"""
Two-compartment lumped-parameter vascular model with collapsible venous compliance.
"""

from dataclasses import dataclass
from typing import Dict, Any, Union, Optional
import numpy as np
import torch

from vascushift.physics.hydrostatic import compute_hydrostatic_pressure_drop


@dataclass
class VenousCompartmentParameters:
    """Parameters for the two-compartment cephalic-central venous model."""
    A0: float = 115.0            # Maximum engorged lumen area in microgravity (mm2)
    Amin: float = 6.0            # Minimum collapsed lumen area (mm2)
    k: float = 0.28              # Compliance slope parameter (1/mmHg)
    P0: float = 3.5              # Transition inflection transmural pressure (mmHg)
    CVP: float = 5.5             # Baseline Central Venous Pressure (mmHg)
    delta_h: float = 0.35        # Anatomical heart-to-neck vertical distance (m)
    R_ref: float = 0.05          # Reference venous resistance (mmHg*s/mL)
    Q_inflow: float = 12.0       # Cerebral venous return flow (mL/s, ~720 mL/min)


def collapsible_vein_area_numpy(
    P_tm: Union[float, np.ndarray],
    A0: float,
    Amin: float,
    k: float,
    P0: float,
) -> Union[float, np.ndarray]:
    """
    Sigmoidal pressure-area relationship for a collapsible vein (NumPy).
    A(P_tm) = Amin + (A0 - Amin) / (1 + exp(-k * (P_tm - P0)))
    """
    exponent = -k * (P_tm - P0)
    exponent = np.clip(exponent, -50.0, 50.0)
    return Amin + (A0 - Amin) / (1.0 + np.exp(exponent))


def collapsible_vein_area_torch(
    P_tm: torch.Tensor,
    A0: Union[float, torch.Tensor],
    Amin: Union[float, torch.Tensor],
    k: Union[float, torch.Tensor],
    P0: Union[float, torch.Tensor],
) -> torch.Tensor:
    """
    Differentiable sigmoidal pressure-area relationship for collapsible vein (PyTorch).
    """
    exponent = torch.clamp(-k * (P_tm - P0), min=-50.0, max=50.0)
    return Amin + (A0 - Amin) / (1.0 + torch.exp(exponent))


def evaluate_compartment_equilibrium_numpy(
    gz: Union[float, np.ndarray],
    posture_deg: Union[float, np.ndarray] = 0.0,
    params: Optional[VenousCompartmentParameters] = None,
) -> Dict[str, np.ndarray]:
    """
    Evaluates static hemodynamic equilibrium for a given gravity level and posture.

    Returns:
        Dict with keys:
          - 'IJV_pressure_mmHg': local cervical venous pressure
          - 'IJV_area_mm2': predicted internal jugular vein lumen area
          - 'hydrostatic_drop_mmHg': Delta P_h
    """
    if params is None:
        params = VenousCompartmentParameters()

    delta_P_h = compute_hydrostatic_pressure_drop(
        gz=gz,
        delta_h=params.delta_h,
        posture_angle_deg=posture_deg,
    )

    # In altered gravity, systemic venous return redistributes:
    # effective cervical pressure balances central pressure minus hydrostatic column
    # with microgravity fluid shift compensation factor eta ~ 0.65 - 0.85
    eta = 0.75
    # When supine or in microgravity (0G), venous pressure rises to 18-22 mmHg
    # When seated in 1G, delta_P_h ~ 27 mmHg, driving P_ijv down to ~ 1-4 mmHg
    P_cervical = np.maximum(0.5, (params.CVP + 15.0 * (1.0 - np.minimum(1.0, gz * np.cos(np.radians(posture_deg))))) - delta_P_h * eta)
    A_ijv = collapsible_vein_area_numpy(
        P_tm=P_cervical,
        A0=params.A0,
        Amin=params.Amin,
        k=params.k,
        P0=params.P0,
    )

    return {
        "IJV_pressure_mmHg": P_cervical,
        "IJV_area_mm2": A_ijv,
        "hydrostatic_drop_mmHg": delta_P_h,
    }
