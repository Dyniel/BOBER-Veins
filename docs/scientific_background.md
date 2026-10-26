# Scientific Background: BOBER Veins / VascuShift-GPINN

## 1. Problem Statement & Space Medicine Context
During terrestrial upright posture, the human body operates under a persistent $1.0\text{ }G_z$ longitudinal hydrostatic pressure gradient:
$$\Delta P_h = \rho g_0 \Delta h$$
For blood ($\rho \approx 1060\text{ kg/m}^3$) over a vertical heart-to-head column ($\Delta h \approx 0.35\text{ m}$), this produces a gravitational pressure drop of approximately $27.3\text{ mmHg}$. Consequently, cervical venous pressure at the jugular level drops near or below atmospheric/tissue reference ($0-5\text{ mmHg}$), inducing functional collapse of the internal jugular veins (IJV lumen area $\sim 10-15\text{ mm}^2$) while cerebral venous outflow predominantly drains through high-resistance vertebral venous plexuses.

Upon transition to microgravity ($0\text{-}G_z$) or partial gravity (Lunar $0.16\text{ }G_z$, Martian $0.38\text{ }G_z$), this hydrostatic gradient is abolished or attenuated. Cephalad fluid redistribution causes:
1. Marked jugular venous engorgement (cross-sectional area expanding to $70-120\text{ mm}^2$).
2. Elevation of cervical venous backpressure ($18-25\text{ mmHg}$).
3. Disturbance of venous hemodynamics, including venous blood flow stasis and non-pulsatile congestion.

These hemodynamic alterations represent a central physiological factor in **Spaceflight-Associated Neuro-ocular Syndrome (SANS)**, characterized by optic disc edema, posterior globe flattening, choroidal folds, and hyperopic refractive shifts in astronauts on long-duration orbital missions.

## 2. Hypothesis & Approach
Current orbital and terrestrial monitoring of venous hemodynamics relies on contact ultrasound sonography, requiring specialized equipment and trained operators. BOBER Veins investigates:
1. Whether an interpretable, physically constrained two-compartment model incorporating hydrostatic gradients and non-linear venous compliance can accurately predict gravity-dependent venous states from minimal observations.
2. Whether non-contact optical facial rPPG can reliably monitor vital cardiovascular pulsatile signals.
3. How a hypothetical multimodal observation bridge connects venous filling dynamics to optical proxy features without overstating experimental validity.

## 3. ISSSP 2026 Competition Relevance
Prepared for the **International Space Science and Scientific Payload Competition (ISSSP) 2026** (Finals in Hong Kong, November 2026). This repository provides reproducible scientific software, real experimental benchmark results on European Space Agency (ESA) Parabolic Flight Campaign data, and rigorous uncertainty bounds.

