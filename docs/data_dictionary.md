# Data Dictionary: BOBER Veins / VascuShift

## 0. Common physiology long format (all real sources)
Defined in `src/vascushift/data/schema.py`; produced by `load_all_physiology()`. One row = one value of
one variable for one subject (or `group`) in one condition.

| Column | Meaning |
| :--- | :--- |
| `dataset`, `subject_id`, `sex` | registry key, dataset-prefixed subject id (`group` for published aggregates) |
| `condition`, `environment`, `posture` | e.g. `supine_tilt_-15`, `ground_lab` / `parabolic_flight` / `iss`, `supine_hdt` |
| `tilt_deg` | body-axis angle from horizontal (+90 upright, 0 horizontal, < 0 head-down) |
| `gz_platform` | environment acceleration in g (1 ground, 0.25 parabola, 0 ISS) |
| `gz_body` | head-to-foot component `gz_platform * sin(tilt_deg)`; 1-G supine and 0 G both give 0 but are different states |
| `lbnp_mmHg` | lower-body negative pressure (0 = none) |
| `variable`, `unit` | e.g. `ijv_area_right` [mm2], `ijv_pressure_left` [mmHg], `iop_right` [mmHg], `heart_rate` [bpm] |
| `stat`, `value`, `ci_low`, `ci_high`, `sd`, `n` | `value` (individual) / `mean_ci95` / `mean_sd` / `median_of_beats` / `proportion` |
| `provenance` | `raw_individual` / `published_aggregate` / `synthetic` |
| `source`, `notes` | citation with DOI and table/file; errata and caveats |

Files: `data/processed/physiology_long.csv` (licensed sources only) and
`data/processed/internal/physiology_long_all.csv` (adds the unlicensed BHP tilt/LBNP repos; git-ignored).
Note: `bhp_carotid_jugular` (12 people) is a subset of `bhp_tilt_dose_response` (24 people) — same
measurements; never pool the two.

## 0b. Real IJV cohort for the model code (`vascushift.data.cohorts.real_ijv_cohort`)
One row per person × condition, in the column style of the legacy ESA table, from real tilt data.
File: `data/processed/ijv_gravity_cohort_real.csv` (MIT, 12 people; internal 24-person version in
`processed/internal/`).

| Column | Meaning |
| :--- | :--- |
| `subject_id`, `gender`, `dataset`, `condition` | `bhp-omniNNN`, F/M (internal file only), source, e.g. `supine_tilt_-30` |
| `family`, `posture` | `supine` / `prone` / `seated`; detailed posture (`supine_hdt`, ...) |
| `gz` | platform gravity [g] — always 1.0 (ground lab) |
| `tilt_deg` | body axis from horizontal (+45 head-up … −45 head-down, 90 seated) |
| `posture_deg` | body axis from **vertical** = 90 − `tilt_deg`; a hydrostatic model with `cos(posture_deg)` gets `gz_body` |
| `gz_body` | `gz · sin(tilt_deg)` |
| `IJV_area_mm2`, `IJV_pressure_mmHg` | left/right mean per person and condition (NaN where not measured) |
| `heart_rate_bpm` | internal file only (Finapres/ECG) |
| `plausible_pressure` | False if IJVP outside 0–60 mmHg (compression-sonography outliers; kept, flagged) |
| `provenance` | `raw_individual` |

## 0c. Optical session (common optical format)
Built by `vascushift.data.preprocess.preprocess_ubfc`; read with `load_optical_session(path)`.
Each `data/processed/rppg/sessions/<session_id>.npz` holds arrays on **one uniform grid** (`fs` = 30 Hz):

| Array | Meaning |
| :--- | :--- |
| `time` | s from the first frame |
| `rgb` | (N, 3) mean skin R, G, B in the face ROI (0–255) |
| `ref_ppg` | finger PPG on the same grid (DATASET_2: per-frame GT rows; DATASET_1: 62 Hz log) |
| `valid` | False inside dropped-frame holes > 0.25 s or before the first face detection |
| `face_found` | face detector hit (or carried box) |
| `meta_json` | the index row below + build parameters (`version`, `fs_out`, `max_interp_gap_s`) |

Index `data/processed/rppg/sessions.csv` (`OPTICAL_SESSION_COLUMNS`): `dataset, session_id, subject_id,
subset, fs, n_samples, duration_s, fraction_valid, frame_clock, fps_video_mean, max_frame_step_s,
ref_hr_bpm, hr_sensor_dropouts, no_face_display, provenance, source, file`.

## 0d. rPPG window table (`RPPG_WINDOW_COLUMNS`)
`reports/rppg_baseline/windows.csv` — one row per session × protocol × method × window:
`dataset, session_id, subset, protocol (whole | w30s15 | w10s2), method (green | chrom | pos), t_start_s,
t_end_s, hr_ref_bpm, hr_est_bpm, error_bpm (= est − ref), snr_db (power at the reference HR and its
harmonic vs the rest of 0.7–3.5 Hz), fraction_valid, included, exclusion_reason, provenance`.
Summary metrics per subset × protocol × method: `reports/rppg_baseline/summary.csv` (MAE with session
bootstrap CI, RMSE, MAPE, Pearson r, Bland–Altman bias and limits, share within ±5 bpm, median SNR).

## 0d'. Improved rPPG track (EXPERIMENTAL)
`reports/rppg_improved/windows.csv` — 10 s windows of the promoted variant: `session_id, subset, split
(tune | holdout), t_start_s, hr_ref_bpm, hr_est_bpm (Viterbi-tracked), error_bpm, hr_est_untracked_bpm,
quality (reference-free, 0–1), fraction_valid, included, abstain, provenance`; `summary.json` holds the
configuration, the abstention threshold (TUNE 10 % quantile) and metrics per group next to the frozen
baseline on the same windows.

## 0e. Dashboard bundles
`demo/data/public/dashboard_data.{json,js}` (`window.VASCU_PUBLIC`): metrics and condition statistics from
licensed sources + the labelled model sweep + data-quality and pipeline blocks.
`demo/data/local/dashboard_local.{json,js}` (`window.VASCU_LOCAL`, git-ignored): 8 s waveform excerpts and
the internal BHP statistics.

## 1. Legacy ESA Headward Fluid Shift table (SYNTHETIC stand-in)
- **Investigation Acronym**: `HeadwardFluidShift_PARA`, DOI [10.57780/esa-0ggni9p](https://doi.org/10.57780/esa-0ggni9p)
  (82nd ESA/NASA PFC, June 2023) - **no data files in HREDA** (`data_available = False`).
- The table below is produced by `generate_synthetic_esa_like_cohort()`: random draws around group means of
  Lee et al., *Front Physiol* 11:863, 2020 (a different campaign, June 2018, without 0-G parabolas).
  Rows coded `gz = 0.0, supine` were measured at **1 G supine** on the ground. `IJV_pressure_mmHg`
  (all rows), supine `heart_rate_bpm` / `mean_arterial_pressure_mmHg` and all spreads are invented.
  Use it only as a synthetic test fixture. Details: `docs/data_audit.md`.

### Variables:
| Variable Name | Type | Physical Units | Valid Range | Measurement Method | Description |
| :--- | :---: | :---: | :---: | :--- | :--- |
| `subject_id` | String | - | `sub-01` to `sub-09` | Synthetic ID | Synthetic participant code (paper: $N=9$, 5F, 4M; IJV area $n=8$) |
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
| `provenance` | String | - | - | Metadata | `SYNTHETIC_random_draws_around_Lee2020_group_means` |

---

## 2. Optical rPPG session (UBFC-rPPG or synthetic)
- **Real data**: UBFC-rPPG via `vascushift.data.ubfc.load_ubfc_session()` (finger PPG CMS50E as reference).
  Frames are timed with their real clock: DATASET_2 GT has one row per frame (irregular, 23–30 fps, holes up to
  1 s); DATASET_1 runs at a constant 28.67 fps. All top-level arrays are then resampled to one uniform grid,
  `fs = 30.0` Hz by default (`fs_out`). Sessions of DATASET_2 subjects 21/27 carry `no_face_display = True`
  (no face images in any publication; subject21 is not in the release).
- **Synthetic**: `generate_synthetic_rppg_session()`, `is_real = False`.
- Extra keys of real sessions: `time`, `face_found`, `valid` (False inside frame holes > 0.25 s),
  `frames` (per-frame `t`, `rgb`, `face_found`, `clock`), `gt_quality` (duplicated / gapped stamps, sensor HR
  dropouts, `fraction_valid`), `video` (header fps, frames, codec), `no_face_display`, `is_real`.

### Variables:
| Variable Name | Type | Physical Units | Sampling Rate | Description |
| :--- | :---: | :---: | :---: | :--- |
| `rgb_traces` | Float array | Pixel intensity $[0, 255]$ | `fs` (30 Hz grid) | Mean skin RGB in the central face box (Haar detection + YCrCb skin mask), resampled from the frame clock |
| `ref_bvp` | Float array | Oximeter units | `fs` (30 Hz grid) | Finger PPG on the same grid (DATASET_2: per-frame rows; DATASET_1: 62 Hz log) |
| `valid` | Bool array | - | `fs` (30 Hz grid) | False where the grid falls inside a dropped-frame hole > 0.25 s (interpolated, not measured) |
| `ref_hr_bpm` | Float | $\text{BPM}$ | Session | HR from the PPG waveform (Welch peak), NOT the oximeter HR column |
| `est_hr_bpm` | Float | $\text{BPM}$ | Epoch mean | Heart rate estimated from optical rPPG signal |
| `snr_db` | Float | $\text{dB}$ | - | Spectral signal-to-noise ratio of pulse harmonic |
| `is_valid` | Boolean | - | - | Quality screening flag ($\text{SNR} \ge -3.0\text{ dB}$) |

