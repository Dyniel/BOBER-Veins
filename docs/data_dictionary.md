# Data Dictionary: BOBER Veins / VascuShift

## 1. ESA Headward Fluid Shift Dataset
- **Investigation Acronym**: `HeadwardFluidShift_PARA`
- **DOI**: [10.57780/esa-0ggni9p](https://doi.org/10.57780/esa-0ggni9p)
- **Source Study**: 82nd ESA/NASA Parabolic Flight Campaign (PFC82, June 2023).
- **Reference Protocol**: Lee et al., *"Venous and Arterial Responses to Partial Gravity"*, *Frontiers in Physiology*, 11:863, 2020.
- **Licensing**: CC BY-NC 3.0 IGO (ESA); CC-BY 4.0 (Published study).

### Variables:
| Variable Name | Type | Physical Units | Valid Range | Measurement Method | Description |
| :--- | :---: | :---: | :---: | :--- | :--- |
| `subject_id` | String | - | `sub-01` to `sub-09` | De-identified ID | Unique participant code ($N=9$, 5F, 4M) |
| `gender` | Categorical | - | `F`, `M` | Demographic | Biological sex of participant |
| `gz` | Float | $G_z$ | $0.00$ to $1.00$ | Aircraft Accelerometer | Longitudinal gravity fraction ($0, 0.25, 0.5, 0.75, 1.0$) |
| `posture` | Categorical | - | `seated`, `supine` | Protocol Spec | Upright seated ($\theta=0^\circ$) or supine ($\theta=90^\circ$) |
| `IJV_area_mm2` | Float | $\text{mm}^2$ | $3.0 - 200.0$ | Ultrasound sonography (GE 12L-RS) | Lumen cross-sectional area of internal jugular vein |
| `IJV_pressure_mmHg` | Float | $\text{mmHg}$ | $0.0 - 35.0$ | Compression sonography (VeinPress) | Non-invasive cervical venous pressure |
| `IVC_diameter_cm` | Float | $\text{cm}$ | $1.0 - 3.0$ | Ultrasound (GE M4S-RS) | Inferior vena cava diameter |
| `CCA_flow_ml_min` | Float | $\text{mL/min}$ | $400 - 1500$ | Doppler sonography | Common carotid artery blood flow |
| `heart_rate_bpm` | Float | $\text{BPM}$ | $45 - 120$ | ECG / Finapres | Heart rate |
| `mean_arterial_pressure_mmHg` | Float | $\text{mmHg}$ | $55 - 130$ | Continuous finger arterial BP | Mean arterial blood pressure (MAP) |
| `IJV_flow_score` | Integer | - | $1$ or $2$ | Doppler waveform review | $1 = \text{continuous forward flow}$, $2 = \text{pulsatile forward flow}$ |
| `provenance` | String | - | - | Metadata | Attribution tag |

---

## 2. Optical rPPG Benchmark Dataset
- **Format**: Synchronized face video frames and reference photoplethysmogram waveforms.
- **Reference Benchmarks**: UBFC-rPPG / PURE format compatibility.

### Variables:
| Variable Name | Type | Physical Units | Sampling Rate | Description |
| :--- | :---: | :---: | :---: | :--- |
| `rgb_traces` | Float array | Pixel intensity $[0, 255]$ | $30.0\text{ Hz}$ | Spatial mean of facial ROI in R, G, B channels |
| `ref_bvp` | Float array | Normalized units | $30.0\text{ Hz}$ | Synchronized pulse oximeter blood volume pulse |
| `ref_hr_bpm` | Float | $\text{BPM}$ | Epoch mean | Ground truth heart rate derived from reference contact pulse |
| `est_hr_bpm` | Float | $\text{BPM}$ | Epoch mean | Heart rate estimated from optical rPPG signal |
| `snr_db` | Float | $\text{dB}$ | - | Spectral signal-to-noise ratio of pulse harmonic |
| `is_valid` | Boolean | - | - | Quality screening flag ($\text{SNR} \ge -3.0\text{ dB}$) |

