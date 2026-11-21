# rPPG improvement experiments (real UBFC-rPPG) — log

*Started 2026-11-05. These are experiments on top of the frozen baseline (`docs/rppg_baseline.md`); the
baseline numbers are not changed by anything here. Code: `src/vascushift/experiments/rppg_improvements.py`,
`src/vascushift/experiments/roi_variants.py`; raw results: `reports/experiments/rppg/` (every run appended
to `runs.csv` with its parameters).*

## Protocol (fixed before the first variant)

* Same 10 s / 2 s windows, same reference (finger PPG, same 0.7–3.5 Hz filter and HR estimator), same
  exclusion rule (< 90 % valid samples) as the baseline.
* **Split:** TUNE = DATASET_2 subjects with an even number (21 people, 608 windows); HOLDOUT = DATASET_2
  odd subjects (21) + all 8 DATASET_1 recordings (887 windows). Parameters and variants are chosen on TUNE
  only; HOLDOUT is looked at once per chosen variant.
* Metrics: MAE, RMSE, share of windows within ±5 bpm, share of gross errors > 10 bpm.

Baseline on this split (repo methods, unchanged):

| Variant | TUNE MAE | TUNE ≤5 bpm | HOLDOUT MAE | HOLDOUT ≤5 bpm |
|---|---|---|---|---|
| POS | 1.39 | 97.4 % | 1.74 | 94.5 % |
| CHROM (repo, global α) | 1.16 | 96.7 % | 1.96 | 94.3 % |
| Green | 11.15 | 73.2 % | 10.13 | 75.2 % |

## E1 — Does the frame-clock fix matter in the windowed protocol? **Yes.**

DATASET_2, all 42 people, 10 s windows; "old" = frames assumed uniform at the AVI header rate, reference
interpolated by time (what the code did before 2026-11-05).

| Method | Old timing MAE | Frame clock MAE | Old ≤5 bpm | New ≤5 bpm |
|---|---|---|---|---|
| POS | 1.89 | **1.29** (−32 %) | 95.8 % | 97.5 % |
| CHROM | 2.02 | **1.30** (−36 %) | 95.2 % | 97.0 % |
| POS, 12 sessions with frame holes > 0.25 s | 2.67 | **1.59** | 93.8 % | 97.4 % |
| CHROM, same 12 sessions | 2.00 | **0.80** | 94.4 % | 98.9 % |

File: `reports/experiments/rppg/E1_frame_clock_windows.csv`.

## E2 — HR tracking across windows (Viterbi)

Instead of the spectral peak of each window independently, a Viterbi path through consecutive window
spectra with a Gaussian penalty on HR changes (σ, bpm per 2 s step). Grid on TUNE: σ ∈ {3, 6, 10},
max jump ∈ {5, 8, 12} (the jump cut has no effect — the Gaussian dominates).

| Variant (σ chosen on TUNE) | TUNE MAE | HOLDOUT MAE | HOLDOUT ≤5 bpm | HOLDOUT > 10 bpm |
|---|---|---|---|---|
| POS baseline | 1.39 | 1.74 | 94.5 % | 4.3 % |
| POS + Viterbi σ = 10 | **0.65** | **1.44** | 95.2 % | 3.8 % |
| CHROM baseline | 1.16 | 1.96 | 94.3 % | 4.4 % |
| CHROM + Viterbi σ = 6 | 0.83 | 1.85 | 93.2 % | 5.5 % |

HOLDOUT split by subset: on held-out DATASET_2 people POS 1.19 → **0.68** bpm (gross errors 1.7 % → 0.5 %);
on DATASET_1 POS 2.87 → 3.01, CHROM 3.05 → 3.67. Tracking repairs isolated bad windows but locks onto a
**sustained** artefact (DATASET_1 `5-gt`). Biggest single gain: subject 41, POS 6.06 → 0.38 bpm.

## E3 — Abstain on uncertain windows (reference-free quality)

Quality = share of in-band power within ±0.1 Hz of the spectral peak and its harmonic (no reference
needed). Threshold = quantile of TUNE windows; applied unchanged to HOLDOUT.

| Variant | Windows dropped (TUNE quantile) | HOLDOUT kept | HOLDOUT MAE | HOLDOUT ≤5 bpm |
|---|---|---|---|---|
| POS | 0 | 100 % | 1.74 | 94.5 % |
| POS | 10 % | 86 % | **0.82** | 98.7 % |
| POS | 20 % | 76 % | **0.48** | 99.9 % |
| POS + Viterbi | 10 % | 86 % | 0.68 | 99.1 % |
| CHROM windowed (E4) | 10 % | 86 % | 0.64 | 99.2 % |

The confidence score transfers from TUNE to HOLDOUT. For a monitoring payload, "no reading" in ~10 % of
windows halves the error. File: `E3_quality_gating.csv`.

## E4 — Other pulse-extraction methods (TUNE only)

| Variant | TUNE MAE | TUNE ≤5 bpm | + Viterbi σ = 10 |
|---|---|---|---|
| CHROM as published (per-window α, 1.6 s Hann overlap-add) | **0.85** | 97.9 % | 0.82 |
| POS window 1.0 s | 1.18 | 97.5 % | **0.64** |
| POS window 1.6 s (repo) | 1.39 | 97.4 % | 0.65 |
| POS window 3.2 s | 1.58 | 96.7 % | 0.98 |
| OMIT (QR projection) | 2.36 | 94.6 % | 1.00 |
| LGI (SVD projection) | 2.58 | 93.9 % | 1.00 |
| PBV | 15.8 | 58.1 % | 15.6 |

The repo's CHROM uses one global α for the whole recording; the published windowed form is clearly
better (0.85 vs 1.16). PBV fails on this data (implementation follows rPPG-Toolbox's whole-signal form;
not pursued). File: `E4_methods.csv`.

## E7 — Why do some recordings fail? (diagnostics)

* Gross errors are almost always **under**-estimates (median estimate 58 bpm vs reference 80 bpm): a
  low-frequency component wins the spectral peak.
* DATASET_1 `5-gt` (−25 bpm in every method): more horizontal head motion than a clean recording
  (face-box centre σ 2.3 px vs 0.4 px in `6-gt`); colour channels change together (frame-to-frame
  correlation R–G 0.93), i.e. motion/illumination rather than pulse.
* **Face-box step artefact (found here):** the baseline box only moves on re-detection frames (every
  15th frame; mean jump 0.93 px, 0 px otherwise), which puts a spectral line at fps/15 ≈ 1.9–2.0 Hz
  (≈ 115–120 bpm, inside the HR band); the line is > 3× its neighbourhood in 7/50 recordings → E6.

## E5 — Window length (TUNE)

MAE [bpm] / share within ±5 bpm, stride 2 s:

| Window | POS | POS + Viterbi | CHROM windowed | CHROM windowed + Viterbi |
|---|---|---|---|---|
| 5 s | 1.95 / 96.9 % | 1.15 / 98.0 % | 1.50 / 97.6 % | 1.27 / 97.4 % |
| 8 s | 1.48 / 97.6 % | 0.76 / 98.9 % | 1.00 / 98.3 % | 0.91 / 98.1 % |
| **10 s** | 1.39 / 97.4 % | **0.65 / 98.9 %** | **0.85 / 97.9 %** | 0.82 / 97.7 % |
| 15 s | 1.67 / 93.9 % | 0.80 / 96.4 % | 1.16 / 94.4 % | 1.00 / 95.0 % |
| 20 s | 1.87 / 93.7 % | 1.21 / 93.5 % | 1.36 / 92.1 % | 1.31 / 92.5 % |
| 30 s | 2.12 / 94.8 % | 0.88 / 96.5 % | 1.35 / 94.3 % | 1.12 / 95.5 % |

The baseline's 10 s window is the best choice for every variant; longer windows average over real HR
changes (DATASET_2 subjects play a time-pressured math game). No change recommended. File: `E5_window_length.csv`.

## E8 — Independent optical dataset: PhysioNet videopulse (no tuning)

New loader `vascushift.data.videopulse` (40 recordings, 15 people, seated; stationary vs motion;
Logitech 15 fps = c1, GoPro 60 fps = c2; single-channel video pulse already extracted by the authors,
finger reference 1 kHz). The header's reference offset was verified by cross-correlation (38/40 within
0.5 s; the other two are motion recordings within 1.2 s). Settings were carried over from UBFC TUNE
unchanged: Viterbi σ = 10 bpm; abstention thresholds = UBFC TUNE quantiles. 10 s / 2 s windows, 1188
windows.

| Condition · camera | MAE peak | MAE Viterbi | ≤5 bpm peak → Viterbi | abstain 10 %: kept / MAE |
|---|---|---|---|---|
| stationary · c1 (15 fps) | 0.3 | 0.4 | 99.3 → 99.1 % | 98 % / 0.3 |
| stationary · c2 (60 fps) | 0.5 | 0.6 | 98.0 → 98.0 % | 92 % / 0.3 |
| motion · c1 | 0.4 | 0.4 | 99.5 → 99.8 % | 99 % / 0.3 |
| **motion · c2** | **1.7** | **1.0** | 92.7 → 95.5 % | 85 % / 0.7 |

The HR layer generalises: tracking helps where there are artefacts (motion, GoPro) and costs ~0.1 bpm
on clean signals; the UBFC-derived quality threshold drops few windows on clean recordings and more under
motion, as intended. Caveat: the pulse extraction here is the authors' own (not ours), so this tests only
the HR-estimation, tracking and abstention layers. Files: `E8_videopulse_windows.csv`, `E8_videopulse_summary.csv`.

## E6 — Face region and box tracking (TUNE)

Per-frame Haar detection on all 50 videos (`scripts/run_roi_variants.py`, ~5 min with 7 workers; face found
in 100 % of frames in 47 videos, ≥ 98.5 % in the other 3). `step15|central` reproduces the baseline traces
to 1e-5. MAE [bpm] on TUNE (none / + Viterbi σ = 10):

| Box \ region | central (baseline) | central, no skin mask | cheeks | forehead | full box |
|---|---|---|---|---|---|
| **POS** step15 (baseline box) | 1.39 / 0.65 | 1.19 / 0.64 | **0.90** / 0.69 | 2.14 / 2.01 | 1.21 / 0.62 |
| POS interp15 | 1.23 / 0.65 | 1.17 / 0.64 | 0.92 / 0.70 | 2.08 / 0.72 | 1.25 / **0.62** |
| POS every-frame EMA | 1.57 / 0.78 | 2.13 / 1.03 | 1.54 / 0.61 | 2.19 / 0.82 | 1.46 / 0.61 |
| POS fixed median box | 1.11 / 0.61 | 1.14 / 0.78 | 0.99 / 0.66 | 1.73 / 0.71 | 1.20 / 0.61 |
| **CHROM windowed** step15 | 0.85 / 0.82 | 0.81 / 0.77 | 0.78 / 0.75 | 1.80 / 1.87 | 0.69 / 0.64 |
| CHROM windowed interp15 | 0.83 / 0.78 | 0.75 / 0.74 | 0.75 / 0.68 | 1.86 / 2.28 | **0.66** / 0.64 |
| CHROM windowed every-frame EMA | 0.88 / 0.71 | 0.82 / 0.67 | 0.76 / 0.66 | 1.93 / 1.30 | 0.80 / 0.67 |
| CHROM windowed fixed | 0.83 / 0.68 | 0.80 / 0.69 | 0.67 / 0.65 | 1.38 / 0.79 | 0.68 / **0.60** |

* The forehead is the worst region everywhere (hair/fringe, small area).
* Interpolating the box between detections removes the fps/15 step artefact: POS central 1.39 → 1.23.
* Detecting on every frame is *worse* than every 15th frame for POS (detector jitter enters the ROI).
* A fixed box works on UBFC because people sit still — not a choice for a moving astronaut; not selected.
* With tracking, most sensible variants converge to 0.60–0.70 bpm; differences of that size are within
  noise for 21 people.

## Final confirmation on HOLDOUT (looked at once)

Chosen on TUNE only, preferring motion-robust options: ROI = **interpolated box + full face box with skin
mask**, HR = **Viterbi σ = 10**; methods POS (C2, TUNE 0.62) and published windowed CHROM (C1, TUNE 0.64).
File: `reports/experiments/rppg/FINAL_holdout_check.csv`.

| HOLDOUT (29 recordings, 887 windows) | MAE | RMSE | ≤ 5 bpm | > 10 bpm |
|---|---|---|---|---|
| Baseline POS | 1.74 | 6.15 | 94.5 % | 4.3 % |
| **C2: POS + interp15/full box + Viterbi** | **1.23** (−29 %) | **3.73** | 95.8 % | 3.4 % |
| Baseline CHROM (repo) | 1.96 | 7.16 | 94.3 % | 4.4 % |
| **C1: windowed CHROM + interp15/full box + Viterbi** | **1.24** (−37 %) | **3.49** | 95.5 % | 3.5 % |
| held-out DATASET_2 only: baseline POS → C2 | 1.19 → **0.65** | 5.26 → 1.26 | 97.7 → 99.3 % | 1.7 → 0.3 % |
| DATASET_1 only: baseline CHROM → C1 | 3.05 → 2.13 | 8.04 → 5.49 | 87.8 → 89.6 % | 9.7 → 7.6 % |
| C2 + abstain (TUNE 10 % threshold; keeps 82.5 % of HOLDOUT windows) | 0.58 | 1.76 | 99.6 % | 0.4 % |

Paired bootstrap over recordings (5000 resamples, identical windows; MAE of baseline minus variant):

| Comparison | Gain [bpm] | 95 % CI | share of resamples without a gain |
|---|---|---|---|
| E1 frame clock, POS, DATASET_2 (42) | 0.60 | 0.43 … 0.79 | 0 % |
| E1 frame clock, CHROM, DATASET_2 (42) | 0.72 | 0.51 … 0.95 | 0 % |
| Improved C2 vs baseline POS, HOLDOUT (29) | 0.51 | 0.08 … 1.03 | 0.6 % |
| — held-out DATASET_2 (21) | 0.55 | 0.03 … 1.20 | 1.4 % |
| — DATASET_1 (8) | 0.42 | −0.09 … 1.34 | 21 % (not significant) |

The improvement found on half of the people holds on the other half (significant for the held-out
DATASET_2 people; same direction but not significant on the 8 DATASET_1 recordings). DATASET_1 `5-gt`
remains the hard case (sustained artefact). C2 (POS, slightly better on TUNE) is promoted as the
"improved" optical track; the frozen baseline stays as reported.

## E9 — Regress face-box motion out of the RGB traces (after the final check; not adopted)

Band-passed face-box motion (centre x, y and size of the every-frame EMA track) regressed out of each
normalised colour channel before POS, on the improved ROI (interp15 / full box). TUNE:

| Variant | MAE | + Viterbi |
|---|---|---|
| POS | 1.26 | 0.62 |
| POS, motion regressed | 1.17 | 0.62 |
| POS, motion regressed with ±0.1 s lags | 1.37 | 0.70 |

No gain once tracking is on → not adopted. Diagnostic on the known failure (`5-gt`, HOLDOUT; looked at
for diagnosis only): box motion explains **35 %** of the green-channel variance in the pulse band
(8–11 % in other recordings), yet regressing it out does not help (16.9 → 18.1 bpm). The artefact is
motion-related but not a linear function of the box position — most likely shading changes as the head
turns. A landmark-based skin tracker (non-rigid, per-region) is the next thing to try; not done here.

## E12 — Fuse several face regions (TUNE; after the final check; not adopted)

POS on interp15 regions (full box, cheeks, central, forehead); per-window spectra normalised and averaged
(equal or quality² weights), then peak picking or Viterbi.

| Regions | MAE, no tracking (equal / quality) | MAE, Viterbi (equal / quality) |
|---|---|---|
| full box only | 1.26 / 1.26 | 0.62 / 0.62 |
| full box + cheeks | 0.95 / 0.99 | 0.60 / 0.60 |
| + central | 1.03 / 1.00 | 0.59 / 0.59 |
| + forehead | 0.96 / 0.92 | 0.60 / 0.60 |

Fusion cuts the error by ~25 % when HR tracking is not used (useful for a causal, zero-latency
estimator); with tracking the gain (0.62 → 0.59) is within noise → not added to the improved track.

## E14 — Optical features beyond heart rate (all 50 recordings; parameters fixed, no tuning)

Code: `src/vascushift/experiments/optical_features.py`. Pulse = POS on the improved ROI; systolic peaks with
sub-sample (parabolic) timing; face beats matched to finger beats within 150 ms after removing the median
delay (median match rate 97.7 %, 5019 matched beats).

| Feature | Agreement with the finger PPG | Verdict |
|---|---|---|
| Inter-beat interval (beat level) | MAE 30 ms (≈ one frame at 30 fps), median 20 ms, bias −0.6 ms, r = 0.951, 81 % within 50 ms | **usable** for beat-to-beat HR |
| RMSSD (short-term HRV) | face 60 ms vs finger 25 ms median (2.7× too high), Spearman 0.51 | **not usable** at 30 fps — peak-timing jitter dominates |
| SDNN | face 55 vs finger 39 ms (1.3×), Spearman 0.64 | weak; not for claims |
| Face → finger pulse delay | median −33 ms, IQR −58 … +225 ms; positive in only 34 % of recordings | **not interpretable** — the oximeter's internal processing delay is unknown |

Implication for the poster and the bridge: the only optical feature validated here is heart rate (also
beat-to-beat). Any "optical venous proxy" remains a modelled quantity. For HRV the payload camera would need
a higher frame rate and hardware timestamps (note for the hardware design). Files: `E14_features_*.csv`.

## E15 — How low can the camera frame rate go? (payload design input; fixed configuration, no tuning)

Real per-frame traces (improved ROI), keeping every k-th real frame on the true frame clock, then the same
30 Hz grid and POS (finger reference kept at full rate). MAE [bpm], 10 s windows:

| Effective frame rate | DATASET_2 (42) | DATASET_2 + Viterbi | ≤ 5 bpm (+ Viterbi) | DATASET_1 (8) + Viterbi |
|---|---|---|---|---|
| 29.5 fps (all frames) | 1.67 | **0.63** | 99.1 % | 2.46 |
| 14.8 fps | 2.23 | 0.83 | 97.8 % | 2.91 |
| 9.8 fps | 2.11 | **0.70** | 98.8 % | 2.43 |
| 7.4 fps | 2.96 | 1.83 | 94.3 % | 2.74 |
| 4.9 fps | 3.44 | 2.04 | 94.9 % | 2.34 |

Heart rate needs only **≈ 10 fps** with tracking (within 0.1–0.2 bpm of 30 fps); below that the error
rises sharply (at 7.4 fps the Nyquist limit, 3.7 Hz, sits close to the pulse harmonics). Short-term HRV
needs far more (E14). File: `E15_frame_rate.csv`.

## E16 — Quality-weighted Viterbi (TUNE; not adopted)

Emission log-powers scaled by (window quality / median quality)^γ, so low-quality windows lean on the
continuity prior: γ = 0 (plain) 0.622, γ = 0.5 0.630, γ = 1 0.602, γ = 2 0.611 bpm MAE. Within noise → not adopted.

## E17 — A learned colour projection instead of POS (TUNE, leave-one-person-out inside TUNE; not adopted)

One global linear combination of the normalised, band-passed R, G, B fitted by least squares to the finger
PPG (reference polarity aligned to POS first). Learned weights ≈ (−0.31, +0.83, −0.48), i.e. green minus red
and blue. MAE 1.53 bpm vs POS 1.26 on the same ROI without tracking: a fixed projection loses to POS, whose
projection adapts every 1.6 s. Supports keeping POS.

## E18 — Can UBFC show anything about the neck veins? (feasibility only; stopped)

Motivation: in microgravity the jugular veins distend, and camera-based jugular venous pulse imaging exists
in the literature; a 1 G seated baseline would be useful. Check on the first frame of every recording:
skin pixels in a strip below the face box (1.05–1.35 box heights, central 40 % of the width) — median
1290 px vs 7670 px in the face ROI, < 1000 px in 22 of 50 recordings; the strip mixes chin and upper neck
(subjects look down at a screen, collars cover the neck). Physiology also predicts no venous signal here:
seated at 1 G the IJV is collapsed (12–19 mm², `docs/physiology_first_analysis.md`). Any pulse found in
that strip would be arterial skin perfusion without a venous reference → stopped. **UBFC cannot test an
optical venous signal.** That needs a dedicated recording: exposed neck, lateral camera view, tilt or
LBNP to move the IJV between collapsed and distended, and ultrasound IJV area as the reference — the
experiment the bridge actually requires. File: `E18_neck_visibility.csv`.

## Addendum — how abstention behaves per recording (improved track, all 50 recordings)

Share of abstained windows per recording: median 7 % (IQR 0–17 %); above 50 % in 3 of 50 recordings
(DATASET_2 subject41 93 %, DATASET_1 `5-gt` 92 %, subject15 87 %). The abstention rate follows the
recording's error (Spearman 0.68), so it does flag the hard recordings, but it is conservative: 81 % of
abstained windows were in fact within ±5 bpm; gross errors are 6× more frequent among abstained windows
(14 %) than overall (2.3 %). In the dashboard the tracked line is drawn for every window and the
low-confidence windows are marked instead of hidden.

## Summary of what to keep

| Change | Evidence | Status |
|---|---|---|
| Real frame clock + 30 Hz grid | E1: −32 % / −36 % MAE (POS / CHROM) | **in the baseline loader** |
| Box interpolated between detections | E6: removes fps/15 artefact; POS central 1.39 → 1.23 | improved track |
| Whole-face ROI with skin mask (not forehead) | E6 | improved track |
| Viterbi HR tracking σ = 10 bpm | E2, E8 (independent data), HOLDOUT | improved track |
| Abstain below a reference-free quality score | E3, E8, HOLDOUT | improved track (reported separately) |
| Published windowed CHROM instead of the repo's global-α CHROM | E4, HOLDOUT C1 | recommended to the optical code owner |
| 10 s windows | E5 | unchanged |
| Multi-region spectral fusion | E12: −25 % without tracking, ≈ 0 with tracking | option for a zero-latency estimator |
| LGI / OMIT / PBV, every-frame detection, motion regression, longer windows, quality-weighted Viterbi, learned fixed projection | E4, E6, E9, E5, E16, E17 | rejected |
