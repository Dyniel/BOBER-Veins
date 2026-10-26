"""
Model 3 — Physics-Informed Neural Network (VascuShift-PINN).
Integrates hydrostatic pressure columns and nonlinear venous compliance into the learning loss.
"""

from typing import Dict, Any, Optional, Tuple, List
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from vascushift.physics.hydrostatic import RHO_BLOOD_KG_M3, G_EARTH_M_S2, PA_TO_MMHG


class PINNSubsystem(nn.Module):
    """Multi-layer perceptron predicting venous states and compliance parameters."""

    def __init__(self, input_dim: int = 2, hidden_dim: int = 32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 4),  # [raw_A, raw_P, raw_k, raw_P0]
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        out = self.net(x)
        # Bounded, physically plausible transformations
        area = torch.clamp(torch.relu(out[:, 0]) + 3.0, max=250.0)      # A_ijv > 3 mm2
        pressure = torch.clamp(torch.relu(out[:, 1]) + 0.1, max=50.0)   # P_ijv > 0.1 mmHg
        k_param = torch.sigmoid(out[:, 2]) * 0.6 + 0.05                  # k in [0.05, 0.65]
        p0_param = torch.tanh(out[:, 3]) * 8.0 + 3.5                     # P0 in [-4.5, 11.5]
        return area, pressure, k_param, p0_param


class VascuShiftPINN:
    """
    Physics-Informed Estimator training wrapper with configurable loss weights:
        L = lambda_data * L_data + lambda_physics * L_physics + lambda_constraints * L_constraints
    """

    def __init__(
        self,
        lambda_data: float = 1.0,
        lambda_physics: float = 1.0,
        lambda_constraints: float = 2.0,
        epochs: int = 600,
        lr: float = 0.005,
        device: str = "cpu",
        seed: int = 42,
    ):
        self.lambda_data = lambda_data
        self.lambda_physics = lambda_physics
        self.lambda_constraints = lambda_constraints
        self.epochs = epochs
        self.lr = lr
        self.device = torch.device(device)
        self.seed = seed
        self.model: Optional[PINNSubsystem] = None
        self.history_: Dict[str, List[float]] = {
            "loss_total": [],
            "loss_data": [],
            "loss_physics": [],
            "loss_constraints": [],
        }

    def _prepare_inputs(self, gz: np.ndarray, posture_deg: np.ndarray) -> torch.Tensor:
        cos_theta = np.cos(np.radians(posture_deg))
        features = np.column_stack([gz, cos_theta])
        return torch.tensor(features, dtype=torch.float32, device=self.device)

    def fit(
        self,
        gz: np.ndarray,
        area_obs: np.ndarray,
        posture_deg: Optional[np.ndarray] = None,
        pressure_obs: Optional[np.ndarray] = None,
    ) -> "VascuShiftPINN":
        torch.manual_seed(self.seed)
        np.random.seed(self.seed)

        gz = np.asarray(gz, dtype=float)
        area_obs = np.asarray(area_obs, dtype=float)
        if posture_deg is None:
            posture_deg = np.where(gz > 0.0, 0.0, 90.0)
        else:
            posture_deg = np.asarray(posture_deg, dtype=float)

        X = self._prepare_inputs(gz, posture_deg)
        y_area = torch.tensor(area_obs, dtype=torch.float32, device=self.device)

        has_pressure = pressure_obs is not None and not np.all(np.isnan(pressure_obs))
        if has_pressure:
            y_press = torch.tensor(
                np.nan_to_num(pressure_obs, nan=0.0), dtype=torch.float32, device=self.device
            )
            press_mask = torch.tensor(~np.isnan(pressure_obs), dtype=torch.bool, device=self.device)

        self.model = PINNSubsystem().to(self.device)
        optimizer = optim.Adam(self.model.parameters(), lr=self.lr, weight_decay=1e-5)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=self.epochs, eta_min=1e-4)

        # Physiological constants for mechanistic equation residual
        rho = RHO_BLOOD_KG_M3
        g0 = G_EARTH_M_S2
        c_p = PA_TO_MMHG
        delta_h_nominal = 0.35
        A0_nominal = 115.0
        Amin_nominal = 6.0
        CVP_nominal = 5.5

        for ep in range(self.epochs):
            optimizer.zero_grad()
            pred_area, pred_pressure, pred_k, pred_p0 = self.model(X)

            # 1. Data loss (normalized)
            l_data = torch.mean(((pred_area - y_area) / 30.0) ** 2)
            if has_pressure and torch.sum(press_mask) > 0:
                l_data = l_data + 0.5 * torch.mean(((pred_pressure[press_mask] - y_press[press_mask]) / 5.0) ** 2)

            # 2. Physics loss (Mechanistic compliance law + hydrostatic balance)
            # Collapsible vein compliance residual: Area = Amin + (A0 - Amin)/(1 + exp(-k * (P - P0)))
            exp_term = torch.clamp(-pred_k * (pred_pressure - pred_p0), min=-40.0, max=40.0)
            target_area_mech = Amin_nominal + (A0_nominal - Amin_nominal) / (1.0 + torch.exp(exp_term))
            res_compliance = torch.mean(((pred_area - target_area_mech) / 30.0) ** 2)

            # Hydrostatic balance residual: P_ijv = max(0.5, CVP + 15*(1-gz*cos) - rho * gz * g0 * delta_h * cos * c_p * 0.75)
            gz_t = X[:, 0]
            cos_t = X[:, 1]
            dP_h_t = (rho * (gz_t * g0) * delta_h_nominal * cos_t) * c_p
            p_expected = torch.clamp(CVP_nominal + 15.0 * (1.0 - torch.clamp(gz_t * cos_t, max=1.0)) - dP_h_t * 0.75, min=0.5)
            res_hydro = torch.mean(((pred_pressure - p_expected) / 5.0) ** 2)

            l_physics = res_compliance + res_hydro

            # 3. Constraints loss (monotonicity with gravity, non-negativity)
            # Physics rule: as gravity gz increases upright, area should decrease (non-positive derivative)
            l_constraints = torch.tensor(0.0, device=self.device)
            if len(gz) > 1:
                # Pairwise penalty for area increasing when gravity increases
                idx_sort = torch.argsort(gz_t)
                sorted_area = pred_area[idx_sort]
                # High gravity should correspond to low area: sorted_area[i+1] <= sorted_area[i]
                diffs = sorted_area[1:] - sorted_area[:-1]
                l_constraints = torch.mean(torch.relu(diffs))

            total_loss = (
                self.lambda_data * l_data
                + self.lambda_physics * l_physics
                + self.lambda_constraints * l_constraints
            )

            total_loss.backward()
            optimizer.step()
            scheduler.step()

            self.history_["loss_total"].append(float(total_loss.item()))
            self.history_["loss_data"].append(float(l_data.item()))
            self.history_["loss_physics"].append(float(l_physics.item()))
            self.history_["loss_constraints"].append(float(l_constraints.item()))

        return self

    def predict(
        self,
        gz: np.ndarray,
        posture_deg: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        if self.model is None:
            raise ValueError("Model is not fitted.")
        self.model.eval()
        gz = np.asarray(gz, dtype=float)
        if posture_deg is None:
            posture_deg = np.where(gz > 0.0, 0.0, 90.0)
        else:
            posture_deg = np.asarray(posture_deg, dtype=float)

        X = self._prepare_inputs(gz, posture_deg)
        with torch.no_grad():
            pred_area, _, _, _ = self.model(X)
        return pred_area.cpu().numpy()

    def predict_states(
        self,
        gz: np.ndarray,
        posture_deg: Optional[np.ndarray] = None,
    ) -> Dict[str, np.ndarray]:
        """Returns predictions for both area and local venous pressure."""
        if self.model is None:
            raise ValueError("Model is not fitted.")
        self.model.eval()
        gz = np.asarray(gz, dtype=float)
        if posture_deg is None:
            posture_deg = np.where(gz > 0.0, 0.0, 90.0)
        else:
            posture_deg = np.asarray(posture_deg, dtype=float)

        X = self._prepare_inputs(gz, posture_deg)
        with torch.no_grad():
            area, press, k, p0 = self.model(X)
        return {
            "IJV_area_mm2": area.cpu().numpy(),
            "IJV_pressure_mmHg": press.cpu().numpy(),
            "k_param": k.cpu().numpy(),
            "p0_param": p0.cpu().numpy(),
        }

