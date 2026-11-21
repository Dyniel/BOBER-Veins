# VascuShift — results ready for the presentation (data & pipeline part)

*Prepared 2026-11-05 by the data/dashboard work stream (Michał). Every number below is produced by
`python -m vascushift.cli pipeline` from real recordings or transcribed published tables; nothing is
synthetic unless the row says so. Source files are named so each number can be traced.*

## 1. The story in three sentences

1. **Optical layer (real):** an ordinary RGB camera recovers heart rate from the face within ~1 bpm in
   the typical case (POS, 42 people, 10 s windows), with a quantified failure tail.
2. **Physiology layer (real):** the jugular vein fills steeply and consistently as head-to-foot gravity
   falls (−63 % area per +0.5 g, all 11 people), and real ISS data show that weightlessness is *not*
   the same as lying down.
3. **Bridge (model, not validated):** no dataset links face video to venous state, so the link between
   the two layers is a model — shown as a model, never as a measurement.

## 2. Headline numbers

| Claim | Number | Provenance | Source file |
|---|---|---|---|
| Face-video HR error, POS, DATASET 2, 10 s windows | **MAE 1.29 bpm** (95 % CI 0.77–1.93), r = 0.948, 97.5 % of windows within ±5 bpm, n = 42 people / 1207 windows | real (UBFC-rPPG) | `reports/rppg_baseline/summary.csv` |
| Same, CHROM / Green | 1.30 / 10.47 bpm | real | same |
| Same, harder subset (DATASET 1, motion, 8 recordings) | POS 2.87 bpm (0.41–7.69) | real | same |
| Whole-recording HR, POS, DATASET 2 | 0.70 bpm (0.39–1.09) | real | same |
| IJV area vs head-to-foot gravity, supine tilt | **−63 % per +0.5 g** (−64 … −57 %), 11/11 people | real (BHP-Lab, MIT) | `reports/physiology_real/tilt_slopes_summary.csv` |
| IJV area 45° head-down vs 45° head-up | **9.4×** within person (6.1–13.9), n = 10 | real | `reports/physiology_real/paired_ratios.csv` |
| IJV pressure slope | −32 mmHg per g (−37 … −26); −27 without flagged outliers | real | `tilt_slopes_summary.csv` |
| HR at 75° head-up tilt vs supine | **+19 %** (+12 … +39 %), 10/10 people | real (PhysioNet PRCP) | `paired_ratios.csv` |
| 0 G ≠ lying down (same 11 crew) | IJV area ISS FD50 **70.3 mm²** (59.3–81.2) vs ground supine **80.7** (69.9–91.5); IJV pressure 21.1 vs 17.3 mmHg | published (Marshall-Goebel 2019) | `data/external/literature_aggregates.csv` |
| Partial gravity, parabolic flight (right IJV, seated) | 68 / 34 / 24 / 12 mm² at 0.25 / 0.5 / 0.75 / 1 G | published (Lee 2020, June 2018 campaign) | same |
| EXPERIMENTAL improved optical track (box interpolation + whole-face ROI + HR tracking), held-out half | POS MAE 1.74 → **1.23 bpm** (gain 0.51, paired 95 % CI 0.08–1.03; RMSE 6.15 → 3.73); held-out DATASET 2 people 1.19 → **0.65**; with abstention (no reading in ~17 % of windows) **0.58** | real; variant chosen on the other half | `reports/rppg_improved/summary.json`, `docs/experiments_rppg.md` |
| Same layer on an independent dataset (PhysioNet videopulse, 15 people, stationary/motion) | HR MAE 0.3–0.5 bpm; motion + 60 fps camera 1.7 → 1.0 bpm with tracking | real (ODC-By) | `reports/experiments/rppg/E8_videopulse_summary.csv` |
| ESA HREDA HeadwardFluidShift | **0 files, data_available = False** (checked live 2026-11-05) | metadata | `reports/pipeline_manifest.json` |
| Team-only (no licence, do not publish): IOP, LBNP | IOP −11.8 mmHg per g; LBNP −19 % IJV area per −10 mmHg | real, internal | `reports/physiology_real/internal/` |

## 3. Figures (licence-safe unless marked)

| File | Use | Caption suggestion |
|---|---|---|
| `reports/figures/data/poster_two_layers.png` (300 dpi) | **poster, results panel** | "Both layers on real data, validated separately. A: face-video heart rate vs finger oximeter, 42 people. B: jugular vein cross-section vs head-to-foot gravity: ground tilt (n = 11), parabolic flight and ISS group means." |
| `reports/rppg_improved/figures/rppg_improvement_holdout.png` | slides, optical (label EXPERIMENTAL) | "On people not used for tuning, interpolating the face box and tracking heart rate across windows cut the error by 29 %; abstaining on the least confident windows halves it again." |
| `reports/rppg_baseline/figures/rppg_mae_by_protocol.png` | slides, optical | "Heart-rate error per method and window length; whiskers: 95 % CI over people." |
| `reports/rppg_baseline/figures/rppg_bland_altman_pos_d2_w10s2.png` | slides / backup | "Agreement of POS with the finger sensor (Bland–Altman)." |
| `reports/rppg_baseline/figures/rppg_session_errors_whole.png` | backup (failure analysis) | "Every recording, every method — failures are concentrated in a few recordings." |
| `reports/physiology_real/figures/ijv_area_vs_gz_body.png` | slides, physiology | "Individual tilt data (left) and published flight/ISS means (right) on one axis." |
| `reports/physiology_real/figures/ijv_pressure_vs_gz_body.png` | slides / backup | "IJV pressure vs head-to-foot gravity." |
| `reports/physiology_real/figures/prcp_hr_by_posture.png` | backup | "Heart rate rises with head-up tilt (PhysioNet PRCP)." |
| `reports/physiology_real/internal/figures/ijv_area_vs_lbnp_INTERNAL.png` | **team only** | do not publish (no licence) until A. Diaz-Artiles agrees |
| Dashboard `demo/` (`python -m vascushift.cli demo`) | live demo at the stand | shows the same numbers, signals only (no video frames) |

Do not show any face image of UBFC subject 27 (dataset consent). The dashboard and figures show signals only.

## 4. Claims in the current materials that must be replaced

These claims rest on the synthetic ESA-like table or on synthetic rPPG sinusoids (see `docs/data_audit.md`).
The files belong to their owners; the replacement text is a suggestion.

| Where | Current claim | Replace with |
|---|---|---|
| `README.md` Result A (l. 33–39) | "verified human measurements from … PFC82, N = 9" | Lee 2020 group means (June 2018 campaign) + BHP tilt individual data (§2); PFC82 has no released data |
| `README.md` Result B (l. 41–53) | LOSO MAE/R² on "N = 9 real ESA subjects" | re-run LOSO on `data/processed/ijv_gravity_cohort_real.csv` (12 people, MIT) — needs `posture_deg` (see §5) |
| `README.md` Result D (l. 60–66) | POS MAE 0.03 bpm, r = 1.000, CHROM 0.06, Green 0.40 | POS 1.29 bpm (0.77–1.93), CHROM 1.30, Green 10.47 on 42 real people (§2) |
| `reports/isssp/poster_content.md` l. 28, 48 | "ESA/NASA PFC data … N = 9", "Dose-Response Profile (ESA Data)" | "Lee et al. 2020 parabolic-flight group means" — the 12/24/34/68 mm² values are real Lee 2020 means, only the label is wrong |
| `reports/isssp/poster_content.md` l. 65; `presentation_outline.md` l. 77; `work_report.md` l. 28, 79 | POS 0.03 bpm, r = 1.000, SNR +10.5 dB, 100 % coverage | POS 1.29 bpm MAE, r = 0.948, 97.5 % within ±5 bpm (UBFC-rPPG, 42 people) |
| `reports/isssp/work_report.md` l. 18, 56, 91; `presentation_outline.md` l. 39 | "actual human measurements from … PFC82", "verified ESA parabolic flight data" | "ESA HREDA PFC82 data are not released (0 files); analyses use real tilt data and published flight/ISS means" |
| `demo/` (old version) | "ESA PFC82 Measured Mean", synthetic waveform | **done** — dashboard now reads pipeline outputs only |

## 5. Hand-over notes

**Daniel (model & science)**
* Real per-person cohort: `vascushift.data.cohorts.real_ijv_cohort()` → columns `gz, tilt_deg,
  posture_deg, gz_body, family, IJV_area_mm2, IJV_pressure_mmHg` (12 people MIT; 24 internal).
  `experiments/physiology.py` builds the angle from the `posture` string (seated → 0°, else 90°); to use
  tilt rows it must read `posture_deg` (cos(posture_deg) = gz_body). Prone vs supine differ in the
  anterior-posterior geometry — keep `family` as a covariate or fit separately.
* The IJV-area curve is sigmoid (plateau ≈ 190 mm² head-down, ≈ 15–20 mm² head-up) — the collapsible-tube
  shape of the compartment model. With default parameters the simulator predicts 114 mm² at gz_body ≤ 0
  and 39 mm² at +1 g; the real tilt medians are ≈ 67 (flat) to ≈ 190 (head-down) and ≈ 17 (+45°) — a
  fit is needed before any model number is shown.
* gz_body alone does not transfer between paradigms (tilt vs parabolic flight vs ISS, §4 of
  `docs/physiology_first_analysis.md`): consider the transverse component / environment as inputs.
* `visualization/figures.py:375` assumes 30 Hz for the rPPG time axis — correct for the new 30 Hz grid.
  `run_rppg_benchmark_experiment` now loads real UBFC sessions automatically (README Result D will change).

* What would turn the synthetic bridge into a measurement: a recording with the neck exposed (lateral
  camera), tilt or LBNP to move the jugular vein between collapsed and distended, and ultrasound IJV
  area as reference. No public dataset has this; UBFC cannot (neck hidden, seated = vein collapsed; E18).

**Natalia (poster & visuals)**
* Use `poster_two_layers.png` for the results panel and the captions above; the replacement table in §4
  lists every sentence on the poster draft that needs new numbers.
* Badge language that matches the dashboard: REAL (measured individuals), PUBLISHED (group means from
  papers), MODEL (simulation, not validated end-to-end).

**Jakub (hardware)**
* Lesson from UBFC: the camera dropped frames (holes up to 1 s, 23–30 fps instead of a fixed 30). Log a
  hardware timestamp for every frame on the payload; 30 fps is enough for heart rate if timestamps are
  exact. Record a contact PPG reference in parallel during any test, as UBFC did.
* 30 fps is *not* enough for short-term heart-rate variability: beat timing from the face has ~30 ms
  error and RMSSD comes out 2.7× too high (E14 in `docs/experiments_rppg.md`); if HRV matters, plan for
  ≥ 60 fps and a better SNR (larger skin area, stable lighting).
* For heart rate alone, ≈ 10 fps is enough (MAE 0.70 bpm at 9.8 fps vs 0.63 at 29.5 fps on 42 people, E15);
  below 10 fps the error triples — a useful margin for power/bandwidth budgets.

## 6. What we can and cannot claim

Can: a working, reproducible pipeline from public real data to a dashboard; heart rate from face video
(~1 bpm typical error on 42 people); a quantified, real gravity dose-response of the neck veins on the
ground; published evidence that 0 G differs from lying down.

Cannot: any measurement of venous state from the camera; heart-rate variability (RMSSD) or pulse-delay
features from the 30 fps face video (tested, not valid — E14); any result "on ESA parabolic flight data";
any per-person result in true microgravity; publication of the unlicensed BHP data (24-person tilt,
LBNP, IOP) before the authors agree.

## 7. Reproduce

```bash
python scripts/download_data.py --dataset all
python -m vascushift.cli pipeline --online      # ~30 s once the video cache exists
python -m vascushift.cli demo --open-browser
```
