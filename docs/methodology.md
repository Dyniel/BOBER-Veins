# Scientific Methodology: VascuShift-GPINN

## 1. Two-Compartment Lumped Parameter Model
The vascular circuit is abstracted into two coupled anatomical compartments:
- **Compartment 1 ($C_1$, Cephalic / Jugular Vein)**:
  Lumen area $A_j$ and local pressure $P_j$.
- **Compartment 2 ($C_2$, Thoracic Central Venous Reservoir)**:
  Central venous pressure $P_c$ (CVP).

### 1.1 Hydrostatic Coupling
The longitudinal pressure gradient between the right atrium and mid-cervical IJV level is given by:
$$\Delta P_h(g_z, \theta) = \rho \cdot (g_z \cdot g_0) \cdot \Delta h \cdot \cos(\theta)$$
where:
- $\rho = 1060\text{ kg/m}^3$ (blood density)
- $g_0 = 9.80665\text{ m/s}^2$
- $\Delta h = 0.35\text{ m}$
- $\theta$ is body posture tilt ($0^\circ$ seated upright, $90^\circ$ supine horizontal).

Effective local venous transmural pressure is:
$$P_{tm}(g_z, \theta) = \max\left(0.5, \left[ P_c + \Delta P_{microg}(1 - g_z \cos\theta) \right] - \eta \Delta P_h(g_z, \theta) \right)$$
where $\eta \approx 0.75$ represents systemic venous return redistribution.

### 1.2 Non-linear Collapsible Compliance
Because thin-walled veins collapse at negative or low transmural pressures and stiffen at elevated pressures, luminal area obeys a sigmoidal law:
$$A_j(P_{tm}) = A_{min} + \frac{A_0 - A_{min}}{1 + \exp\left( -k \cdot (P_{tm} - P_0) \right)}$$
where $A_0$ is maximum distended area, $A_{min}$ is residual collapsed area, $k$ is compliance slope, and $P_0$ is transition pressure.

---

## 2. Physics-Informed Learning Objective
The Physics-Informed Neural Network (PINN) optimizes:
$$\mathcal{L}_{total} = \lambda_d \mathcal{L}_{data} + \lambda_p \mathcal{L}_{physics} + \lambda_c \mathcal{L}_{constraints}$$

1. **Data Loss ($\mathcal{L}_{data}$)**:
   $$\mathcal{L}_{data} = \frac{1}{N_{obs}} \sum_{i=1}^{N_{obs}} \left( \frac{\hat{A}_{j, i} - A_{j, i}^{obs}}{\sigma_A} \right)^2 + \frac{1}{2} \left( \frac{\hat{P}_{j, i} - P_{j, i}^{obs}}{\sigma_P} \right)^2$$
2. **Physics Loss ($\mathcal{L}_{physics}$)**:
   Penalizes residuals of both the compliance constitutive relation and hydrostatic conservation:
   $$\mathcal{R}_{comp} = \hat{A}_j - \left[ A_{min} + \frac{A_0 - A_{min}}{1 + \exp(-\hat{k} (\hat{P}_j - \hat{P}_0))} \right]$$
   $$\mathcal{R}_{hydro} = \hat{P}_j - P_{expected}(g_z, \theta)$$
   $$\mathcal{L}_{physics} = \frac{1}{N} \sum (\mathcal{R}_{comp}^2 + \mathcal{R}_{hydro}^2)$$
3. **Constraint Loss ($\mathcal{L}_{constraints}$)**:
   Enforces non-negativity ($\hat{A}_j \ge A_{min}$, $\hat{P}_j \ge 0$) and physical monotonicity:
   $$\frac{\partial A_j}{\partial g_z} \le 0 \quad (\text{for upright seated posture})$$

---

## 3. Optical rPPG Subsystem
Facial color fluctuations reflect arterial blood volume pulse (BVP). We implement and benchmark:
1. **Green-Channel Baseline**: Spatial averaging of green pixel intensity followed by bandpass filtering $[0.7, 3.5]\text{ Hz}$.
2. **CHROM (Chrominance-based, de Haan & Jeanne 2013)**: Orthogonal color differences $X_s = 3R_n - 2G_n$ and $Y_s = 1.5R_n + G_n - 1.5B_n$ weighted by standard deviation ratio $\alpha = \sigma(X_s)/\sigma(Y_s)$.
3. **POS (Plane-Orthogonal-to-Skin, Wang et al. 2017)**: Dynamic subspace projection eliminating specular reflections and illumination shifts.

Heart rate (HR in BPM) is derived using Welch Power Spectral Density with parabolic sub-bin frequency interpolation.

