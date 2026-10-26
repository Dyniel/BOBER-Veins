# Scientific Assumptions and Limitations: BOBER Veins

## 1. Scientific Status and Scope
**BOBER Veins / VascuShift-GPINN** is an academic research software prototype and scientific feasibility demonstrator developed for the **International Space Science and Scientific Payload Competition (ISSSP) 2026**.
- It is **not** a certified medical diagnostic device.
- It is **not** a flight-qualified space hardware payload.
- All conclusions presented are intended to inform payload sensor design, physical hypothesis testing, and computational modeling for future space medicine initiatives.

---

## 2. Dataset Unpairedness & Synthetic Bridge Boundary
A critical scientific principle of this investigation:
> **The optical facial video dataset and the gravitational venous dataset are completely unpaired.**

- Module A evaluates real human physiological measurements from the ESA/NASA 82nd Parabolic Flight Campaign.
- Module C independently evaluates non-contact photoplethysmography (rPPG) from RGB facial video recordings.
- Because synchronized optical face video and venous catheterization/ultrasound were not acquired simultaneously on the same astronauts in microgravity, **no end-to-end optical-to-internal-venous-state estimator can be claimed as experimentally validated**.
- Module D implements an explicitly synthetic observation proxy model:
  $$y_{proxy} = h(x_{venous}, \theta) + \epsilon$$
  This model serves exclusively to analyze mathematical parameter identifiability, noise tolerance, and sensor sensitivity under hypothetical optical proxy formulations.

---

## 3. Sample Size and Statistical Power
- The human physiological dataset comprises $N = 9$ subjects (5 female, 4 male).
- Although $N = 9$ provides complete coverage across five gravitational levels ($0.0, 0.25, 0.50, 0.75, 1.00\text{ }G_z$), statistical conclusions regarding astronaut population variance and demographic stratification (e.g., sex-specific differences in venous compliance) remain constrained by sample size.
- Grouped Leave-One-Subject-Out (LOSO) cross-validation was strictly implemented to prevent overly optimistic variance estimates.

---

## 4. Physiological Modeling Assumptions
1. **Lumped-Parameter Two-Compartment Abstraction**:
   The human venous circulation is represented by two coupled compartments (cephalic/IJV vs thoracic/central reservoir). This simplifies 3D spatial geometry, collapsible vein elliptical cross-sections, and distributed bifurcations (e.g., facial, thyroid, and vertebral veins) into effective equivalent compliance and resistance parameters.
2. **Quasi-Steady Equilibrium**:
   The baseline model predicts quasi-steady venous filling during sustained gravitational phases (such as the $\sim 20\text{ s}$ plateaus of parabolic flight). Instantaneous respiratory oscillations (intrathoracic pressure drops during inspiration) are treated as zero-mean perturbations.
3. **Hydrostatic Column Length ($\Delta h$)**:
   Vertical heart-to-neck separation is modeled with nominal anatomical height $\Delta h = 0.35\text{ m}$. In reality, participant seated height varies between $0.30\text{ m}$ and $0.42\text{ m}$.

---

## 5. Machine Learning vs Mechanistic Models on Small Data
Our empirical evaluations demonstrate that on small physiological cohorts ($N=9$ subjects), the **pure mechanistic parameter estimator (Baseline 2, $R^2 = 0.8422$, MAE = $12.59\text{ mm}^2$)** substantially outperforms unconstrained neural networks and complex architectures. Neural optimizers suffer from small-sample overfitting and soft loss balancing instability. Incorporating physics constraints into neural networks (Model 3b) mitigates unphysical oscillations, but classical mechanistic modeling remains the scientifically superior choice for small-sample space physiological estimation.

