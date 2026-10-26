# Data Directory - BOBER Veins / VascuShift

## Directory Structure
- `raw/`: Raw external datasets (git-ignored, never committed).
  - `raw/esa/`: Official ESA Headward Fluid Shift data files when downloaded from ESA HREDA.
  - `raw/rppg/`: Public video rPPG recordings (e.g., UBFC-rPPG / PURE).
- `interim/`: Intermediate cached arrays or standardized preprocessed files.
- `processed/`: Processed experimental data files ready for modeling.
- `synthetic/`: Controlled synthetic datasets generated with deterministic seeds for identifiability and recoverability experiments.

## Primary Physiological Dataset: ESA Headward Fluid Shift
- **Investigation Acronym**: `HeadwardFluidShift_PARA`
- **DOI**: [10.57780/esa-0ggni9p](https://doi.org/10.57780/esa-0ggni9p)
- **Source**: 82nd ESA/NASA Parabolic Flight Campaign (PFC82, June 2023).
- **Principal Investigators**: Stuart M. C. Lee, Chris Miller, David S. Martin.
- **Reference Published Protocol & Data**: Lee et al., *"Venous and Arterial Responses to Partial Gravity"*, *Frontiers in Physiology*, 11:863, 2020. DOI: [10.3389/fphys.2020.00863](https://doi.org/10.3389/fphys.2020.00863).
- **Participants**: $N = 9$ human volunteers (5 female, 4 male).
- **Gravity Conditions**:
  - $1.00\text{ }G_z$ seated (ground & flight baseline)
  - $0.75\text{ }G_z$ seated
  - $0.50\text{ }G_z$ seated
  - $0.25\text{ }G_z$ seated
  - $1.00\text{ }G_z$ supine ($0\text{-}G_z$ fluid redistribution analog)
- **Measured Variables**:
  - `IJV_area_mm2`: Right Internal Jugular Vein cross-sectional area ($\text{mm}^2$).
  - `IJV_pressure_mmHg`: Compression sonography venous pressure ($\text{mmHg}$).
  - `IVC_diameter_cm`: Inferior Vena Cava diameter ($\text{cm}$).
  - `CCA_flow_ml_min`: Common Carotid Artery Doppler blood flow ($\text{mL/min}$).
  - `CCA_csa_cm2`: Common Carotid Artery cross-sectional area ($\text{cm}^2$).
  - `heart_rate_bpm`: Heart rate ($\text{bpm}$).
  - `mean_arterial_pressure_mmHg`: Mean arterial blood pressure ($\text{mmHg}$).
  - `IJV_flow_score`: Venous flow character (1: continuous forward, 2: pulsatile forward).
- **Licensing**:
  - ESA HREDA data: CC BY-NC 3.0 IGO.
  - Published data: Creative Commons Attribution License (CC-BY 4.0).

