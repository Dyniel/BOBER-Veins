# ISSSP 2026 Scientific Poster Content (60 cm × 90 cm Portrait)

**Competition:** International Space Science and Scientific Payload Competition (ISSSP) 2026 &middot; Hong Kong Finals  
**Format:** 1 Portrait Poster, 60 cm × 90 cm, 300 DPI, English, <10 MB  

---

## [HEADER BAR]
### Title: BOBER Veins / VascuShift-GPINN
#### Subtitle: Physics-Informed Modeling of Venous Fluid Redistribution and Optical rPPG under Altered Gravitational Loads
**Authors:** Daniel (1*), Natalia (1), Michał (1), Jakub (1)  
**Affiliations:** (1) BOBER Veins Research Consortium / Space Medicine Payload Group  
*Corresponding Author / Presenter: Daniel (bober-veins@isssp2026.org)

---

## [PANEL 1: SCIENTIFIC MOTIVATION & BACKGROUND]
- **The Microgravity Problem**: Upright $1\text{ }G_z$ posture on Earth produces a vertical hydrostatic pressure drop ($\Delta P_h \approx 27.3\text{ mmHg}$) across the cervical column, causing low jugular venous pressures ($0-5\text{ mmHg}$) and physiological vessel collapse.
- In microgravity ($0\text{-}G_z$) and partial gravity (Moon $0.16\text{ }G_z$, Mars $0.38\text{ }G_z$), elimination of this gradient drives a massive cephalad fluid shift.
- **Pathological Consequences**: Severe jugular engorgement, flow stasis, internal jugular vein thrombosis, and elevated intracranial pressure linked to Spaceflight-Associated Neuro-ocular Syndrome (SANS).
- **Current Limitation**: Orbital monitoring requires contact ultrasound sonography with skilled sonographers.
- **Mission Goal**: Establish the foundational physics and non-contact optical sensing feasibility for autonomous long-duration astronaut monitoring.

---

## [PANEL 2: SYSTEM ARCHITECTURE & BOUNDARIES]
*(Insert Figure 1: System Architecture)*
- **Module A**: ESA/NASA Parabolic Flight Campaign data audit and physiological baseline characterization ($N=9$ subjects).
- **Module B**: Mechanistic two-compartment lumped parameter model with non-linear collapsible venous compliance.
- **Module C**: Independently evaluated non-contact optical facial rPPG extracting pulse signals and heart rate.
- **Module D**: Synthetic observation bridge evaluating mathematical identifiability under controlled observation noise.
- **Clear Scientific Boundary**: The optical and venous datasets are unpaired. The bridge is explicitly labeled as a synthetic proxy model.

---

## [PANEL 3: PHYSIOLOGICAL MODEL & GOVERNING EQUATIONS]
- **Hydrostatic Differential**:
  $$\Delta P_h(g_z, \theta) = \rho g_z g_0 \Delta h \cos(\theta)$$
- **Collapsible Vein Compliance Law**:
  $$A_j(P_{tm}) = A_{min} + \frac{A_0 - A_{min}}{1 + \exp\left( -k \cdot (P_{tm} - P_0) \right)}$$
- **Total Physics-Informed Objective**:
  $$\mathcal{L} = \lambda_d \mathcal{L}_{data} + \lambda_p \mathcal{L}_{physics} + \lambda_c \mathcal{L}_{constraints}$$

---

## [PANEL 4: RESULTS — REAL PHYSIOLOGICAL EVALUATION]
*(Insert Figure 2: Gravity-Dependent Physiology & Figure 3: Baseline Comparison)*
- **Dose-Response Profile (ESA Data)**:
  - Seated $1.0\text{ }G_z$: Area $= 12.0\text{ mm}^2$ (Collapsible baseline)
  - $0.75\text{ }G_z$: Area $= 24.0\text{ mm}^2$ ($+100\%$)
  - $0.50\text{ }G_z$: Area $= 34.0\text{ mm}^2$ ($+183\%$)
  - $0.25\text{ }G_z$: Area $= 68.0\text{ mm}^2$ ($+467\%$)
  - $0.00\text{ }G_z$ (Supine): Area $= 108.0\text{ mm}^2$ ($+800\%$ Expansion)
- **Leave-One-Subject-Out CV Comparison**:
  - Baseline 0 (Mean): $\text{MAE} = 35.42\text{ mm}^2$, $R^2 = -0.01$
  - Baseline 1a (Linear): $\text{MAE} = 14.78\text{ mm}^2$, $R^2 = 0.795$
  - **Baseline 2 (Mechanistic 2-Compartment)**: **$\text{MAE} = 12.59\text{ mm}^2$**, **$R^2 = 0.842$** (**Best Generalization, $+64.5\%$ Improvement**)
  - Model 3b (VascuShift-PINN): Enforces physical bounds and monotonicity, avoiding unphysical oscillations.

---

## [PANEL 5: OPTICAL rPPG & IDENTIFIABILITY BENCHMARKS]
*(Insert Figure 4: Synthetic Parameter Recovery & Figure 5: rPPG Signal Validation)*
- **Optical Benchmarks (Subject-Independent)**:
  - **POS Method**: $\text{HR MAE} = 0.03\text{ BPM}$, Pearson $r = 1.000$, $\text{SNR} = +10.5\text{ dB}$, 100% coverage.
  - **CHROM**: $\text{HR MAE} = 0.06\text{ BPM}$, Pearson $r = 1.000$, $\text{SNR} = +6.6\text{ dB}$, 100% coverage.
  - **Green Channel**: $\text{HR MAE} = 0.40\text{ BPM}$, $\text{SNR} = -2.4\text{ dB}$, 66.7% coverage.
- **Identifiability Findings**:
  - Maximum distension capacity ($A_0$) is highly recoverable ($6.38\%$ relative error).
  - Wall stiffness $k$ and transition pressure $P_0$ display parameter compensation ambiguity, showing that optical proxies cannot infer wall elasticity without pressure synchronization.

---

## [PANEL 6: INNOVATION, DEMONSTRATOR & FUTURE PAYLOAD]
*(Insert Figure 7: Demonstrator Overview)*
- **Interactive Demonstrator**: Operational local dashboard providing real-time exploration of G-levels from 0G to 1G.
- **Future Hardware Concept**: Compact multi-wavelength optical sensor with dual NIR/RGB illumination for automated astronaut health monitoring.

---

## [FOOTER & ACKNOWLEDGMENTS]
- Supported by ESA HREDA data investigation `HeadwardFluidShift_PARA` (DOI: 10.57780/esa-0ggni9p) and published study by Lee et al. (*Frontiers in Physiology* 2020).
- Open-Source Scientific Code: https://github.com/Dyniel/BOBER-Veins

