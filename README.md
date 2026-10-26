# BOBER Veins / VascuShift-GPINN

[![ISSSP 2026](https://img.shields.io/badge/ISSSP-2026_Finals_Hong_Kong-0284c7.svg)](https://isssp.org.cn)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![ESA Dataset](https://img.shields.io/badge/ESA_DOI-10.57780%2Fesa--0ggni9p-orange.svg)](https://doi.org/10.57780/esa-0ggni9p)

> **Physics-Informed Modeling of Venous Fluid Redistribution and Optical rPPG under Altered Gravitational Loads.**  
> Developed for the **International Space Science and Scientific Payload Competition (ISSSP) 2026** (Finals in Hong Kong, November 2026).

---

## 1. Project Overview & Scientific Mission
Human exposure to altered gravity eliminates the normal hydrostatic pressure gradient ($\Delta P_h = \rho g \Delta h$), causing substantial cephalad fluid redistribution. In microgravity ($0\text{-}G_z$) and partial gravity (Moon $0.16\text{ }G_z$, Mars $0.38\text{ }G_z$), central venous pressure and volume pool in the neck and head. This leads to internal jugular vein (IJV) engorgement, elevated venous backpressure, and disturbed outflow hemodynamics, which are central physical contributors to **Spaceflight-Associated Neuro-ocular Syndrome (SANS)** and upper-body venous thrombosis risks.

**BOBER Veins** introduces an interpretable, physically constrained computational modeling framework (**VascuShift**) paired with an independent non-contact optical photoplethysmography (**rPPG**) subsystem.

### Scientific Scope & Boundaries:
- **Demonstrator, Not Certified Medical Device:** This repository is an academic research software prototype and scientific feasibility demonstrator, not a certified clinical or flight-qualified medical device.
- **Unpaired Datasets:** Optical face video recordings and internal jugular vein ultrasound measurements were not acquired simultaneously on the same astronauts. The optical-to-venous connection is an explicitly synthetic observation model ($y_{proxy} = h(x_{venous}, \theta) + \epsilon$). No end-to-end optical-to-venous estimator is claimed as experimentally validated on humans.

---

## 2. Key Scientific Results

### Result A: Real ESA Parabolic Flight Ground-Truth
Evaluated on verified human physiological measurements from the ESA/NASA 82nd Parabolic Flight Campaign (PFC82, DOI: [10.57780/esa-0ggni9p](https://doi.org/10.57780/esa-0ggni9p), $N=9$ participants):
- **$1.00\text{ }G_z$ Seated**: IJV Area $= 12.0\text{ mm}^2$ (Venous collapse under $27.3\text{ mmHg}$ hydrostatic column)
- **$0.75\text{ }G_z$ Seated**: IJV Area $= 24.0\text{ mm}^2$ ($+100\%$)
- **$0.50\text{ }G_z$ Seated**: IJV Area $= 34.0\text{ mm}^2$ ($+183\%$)
- **$0.25\text{ }G_z$ Seated**: IJV Area $= 68.0\text{ mm}^2$ ($+467\%$)
- **$0.00\text{ }G_z$ Supine Analog**: IJV Area $= 108.0\text{ mm}^2$ ($+800\%$ Expansion; Pressure rises from $3.5\text{ mmHg} \to 21.0\text{ mmHg}$)

### Result B: Leave-One-Subject-Out (LOSO) Model Benchmark
Matched 9-fold LOSO cross-validation on real human data:

| Model | Class | LOSO MAE ($\text{mm}^2$) | LOSO RMSE ($\text{mm}^2$) | $R^2$ Score | Monotonicity Violations | Error Reduction vs Baseline 0 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Baseline 0** | Constant Mean | 35.42 | 41.69 | -0.014 | 20 | 0.0% |
| **Baseline 1a** | OLS Linear Regression | 14.78 | 18.75 | 0.795 | 22 | +58.3% |
| **Baseline 1b** | Ridge Regression ($L_2$) | 16.22 | 21.49 | 0.731 | 21 | +54.2% |
| **Baseline 2** | **Mechanistic 2-Compartment** | **12.59** | **16.45** | **0.842** | **21** | **+64.5% (Best Generalization)** |
| **Model 3a** | Unconstrained Neural Net | 33.29 | 48.42 | -0.368 | 25 | +6.0% |
| **Model 3b** | VascuShift-PINN | 40.56 | 55.55 | -0.800 | 19 | -14.5% |

> **Small-Sample Space Medicine Finding:** On small physiological cohorts ($N=9$), the pure mechanistic model substantially outperforms neural networks by avoiding small-sample overfitting while preserving exact physical bounds.

### Result C: Identifiability & Sensitivity
Synthetic parameter recovery across noise levels ($\sigma \in [0\%, 20\%]$) demonstrates:
- Structural lumen capacity $A_0$ is highly identifiable ($6.38\% - 8.91\%$ error).
- Wall compliance $k$ and transition pressure $P_0$ display parameter compensation ambiguity, showing that optical proxy observations alone cannot infer wall elasticity without pressure synchronization.

### Result D: Optical rPPG Subsystem
Evaluated on an independent subject cohort ($N = 12$ sessions):
- **POS (Plane-Orthogonal-to-Skin)**: $\text{HR MAE} = 0.03\text{ BPM}$, Pearson $r = 1.000$, $\text{SNR} = +10.5\text{ dB}$, 100% coverage.
- **CHROM**: $\text{HR MAE} = 0.06\text{ BPM}$, Pearson $r = 1.000$, $\text{SNR} = +6.6\text{ dB}$, 100% coverage.
- **Green Channel**: $\text{HR MAE} = 0.40\text{ BPM}$, $\text{SNR} = -2.4\text{ dB}$, 66.7% coverage.

---

## 3. Repository Architecture
```
BOBER-Veins/
├── pyproject.toml              # Build & dependency declarations
├── configs/                    # YAML execution configurations
│   ├── data.yaml
│   ├── physiology.yaml
│   ├── physics_model.yaml
│   ├── rppg.yaml
│   └── experiments.yaml
├── data/
│   ├── README.md               # Dataset documentation & licensing
│   ├── raw/                    # Raw external datasets (git-ignored)
│   ├── processed/              # Processed experimental cohorts
│   └── synthetic/              # Controlled synthetic benchmarks
├── src/vascushift/
│   ├── data/                   # ESA loader, validation, preprocessing
│   ├── physics/                # Hydrostatic column, 2-compartment simulator
│   ├── models/                 # Baselines, mechanistic estimator, PINN
│   ├── optical/                # Facial ROI, filtering, Green, CHROM, POS
│   ├── experiments/            # LOSO CV, ablations, identifiability, rPPG
│   ├── evaluation/             # Metrics, bootstrapping, markdown reporting
│   └── visualization/          # Figures 1-7 generation, web dashboard
├── scripts/                    # Command-line entry points
│   ├── audit_data.py
│   ├── run_physiology.py
│   ├── run_rppg.py
│   ├── run_ablations.py
│   ├── generate_figures.py
│   ├── generate_poster.py
│   └── launch_demo.py
├── tests/                      # 17 automated unit & reproducibility tests
├── notebooks/                  # 3 exploratory analysis notebooks
├── docs/                       # Scientific background, methodology, dictionary
├── reports/
│   ├── results/                # Master results JSON and Markdown
│   ├── figures/                # High-res publication figures & 60x90 poster
│   └── isssp/                  # Work report, poster content, slide outline
└── demo/                       # Interactive local web dashboard
```

---

## 4. Quickstart & Reproducibility Guide

### Installation
```bash
git clone https://github.com/Dyniel/BOBER-Veins.git
cd BOBER-Veins
pip install -e .
```

### Run Tests
```bash
pytest tests/
```

### Execute Standard Commands
```bash
# 1. Audit real ESA HREDA data availability and local files
python -m vascushift.cli data-audit --config configs/data.yaml

# 2. Forward venous hemodynamic simulation across gravity levels
python -m vascushift.cli simulate --config configs/physics_model.yaml

# 3. Train and evaluate physics-informed model on verified ESA cohort
python -m vascushift.cli train-physics --config configs/physiology.yaml

# 4. Run optical rPPG algorithm benchmarks
python -m vascushift.cli run-rppg --config configs/rppg.yaml

# 5. Run full scientific evaluation (LOSO CV, ablations, identifiability)
python -m vascushift.cli evaluate --config configs/experiments.yaml

# 6. Generate all publication figures (Figures 1 - 7)
python -m vascushift.cli figures --config configs/experiments.yaml

# 7. Generate official 60x90cm ISSSP scientific poster
python scripts/generate_poster.py

# 8. Launch local interactive web demonstrator
python -m vascushift.cli demo --port 8501
```

---

## 5. Team Roles (ISSSP 2026)
- **Daniel — Science Lead**: Scientific hypothesis, physiological interpretation, identifiability bounds, pitch & presentation.
- **Natalia — Data & Sensor Concept**: ESA dataset audit, schema validation, payload optical concept, data dictionary.
- **Michał — Physics & AI**: Two-compartment simulator, inverse optimization, PINN loss formulation, ablations, uncertainty.
- **Jakub — Optical & Software**: rPPG algorithms, SNR and quality assessment, web demonstrator, integration.

---

## 6. Citation & Licensing
- **Software License**: MIT License (see [LICENSE](LICENSE)).
- **ESA Dataset Rights**: CC BY-NC 3.0 IGO.
- **Citation**:
```bibtex
@inproceedings{bober_veins_isssp2026,
  author = {Daniel and Natalia and Micha{\l} and Jakub},
  title = {Physics-Informed Modeling of Venous Fluid Redistribution in Altered Gravity},
  booktitle = {International Space Science and Scientific Payload Competition (ISSSP 2026)},
  year = {2026},
  doi = {10.57780/esa-0ggni9p}
}
```

