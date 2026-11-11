# rPPG baseline on real data (UBFC-rPPG) — optical layer v1

*Status 2026-11-05. All numbers are from real recordings (UBFC-rPPG, 50 sessions); nothing here is
synthetic. Reproduce with `python -m vascushift.cli preprocess && python -m vascushift.cli rppg-baseline`
(≈15 s once the RGB cache exists; ≈1 min to build the cache from the 92 GB of video).*

## 1. What is measured

Heart rate from a face video (remote photoplethysmography) against heart rate from a finger
pulse oximeter worn at the same time. This is the **optical layer** of VascuShift: it shows that the
camera pipeline extracts a correct cardiac signal. It does **not** measure jugular filling or fluid
shift — no public dataset pairs face video with venous ground truth (see `docs/data_audit.md`).

## 2. Pipeline

```
vid.avi (640×480 raw, 23–30 fps)                ground_truth.txt / gtdump.xmp
   │ ffmpeg pipe                                    │
   ▼                                                ▼
Haar face box (every 15 frames, smoothed)       PPG + time stamps
   → central ROI (15–85 % w, 10–60 % h)             │  (DATASET_2: one row per frame = frame clock)
   → YCrCb skin mask → mean R,G,B per frame         │
   └──────────────► frame clock ◄───────────────────┘
                    → uniform 30 Hz grid, `valid` = False in frame holes > 0.25 s
                    → data/processed/rppg/sessions/<id>.npz   (common optical format, schema.py)
                                     │
            Green / CHROM / POS on the whole session (repo implementations, unchanged)
                                     │
      windows: whole recording · 30 s / 15 s stride · 10 s / 2 s stride
                                     │
      HR = Welch peak in 42–210 bpm (+ parabolic refinement), SAME estimator for rPPG and PPG
```

Rules fixed before looking at the numbers: windows with < 90 % measured samples are excluded and
listed (4 of 1211 ten-second DATASET_2 windows); statistics are per subset because DATASET_1
(8 recordings, some with motion, one after exercise) and DATASET_2 (42 people, a math game, mostly
still) differ in protocol; the 95 % CI of MAE is a bootstrap **over sessions**, because windows of
one recording are not independent.

## 3. Results

| Subset | Protocol | Method | Sessions | Windows | MAE [bpm] (95 % CI) | RMSE | r | Bias [95 % LoA] | ≤ 5 bpm |
|---|---|---|---|---|---|---|---|---|---|
| DATASET_2 | 10 s windows | **POS** | 42 | 1207 | **1.29** (0.77–1.93) | 5.86 | 0.948 | −0.68 [−12.1, +10.7] | 97.5 % |
| DATASET_2 | 10 s windows | CHROM | 42 | 1207 | 1.30 (0.78–1.94) | 5.70 | 0.951 | −0.61 [−11.7, +10.5] | 97.0 % |
| DATASET_2 | 10 s windows | Green | 42 | 1207 | 10.47 (6.73–14.92) | 22.32 | 0.547 | −9.50 [−49.1, +30.1] | 75.3 % |
| DATASET_2 | 30 s windows | POS | 42 | 123 | 1.63 (0.67–2.86) | 6.80 | 0.933 | −1.34 [−14.5, +11.8] | 95.9 % |
| DATASET_2 | whole recording | POS | 42 | 42 | 0.70 (0.39–1.09) | 1.41 | 0.997 | −0.44 [−3.1, +2.2] | 97.6 % |
| DATASET_2 | whole recording | CHROM | 42 | 42 | 2.44 (0.59–5.57) | 9.77 | 0.866 | −1.58 [−20.7, +17.6] | 92.9 % |
| DATASET_1 | 10 s windows | POS | 8 | 288 | 2.87 (0.41–7.69) | 7.67 | 0.909 | −1.92 [−16.5, +12.7] | 87.8 % |
| DATASET_1 | 10 s windows | CHROM | 8 | 288 | 3.05 (0.44–8.14) | 8.04 | 0.902 | −2.03 [−17.3, +13.2] | 87.8 % |
| DATASET_1 | 10 s windows | Green | 8 | 288 | 10.85 (3.88–17.41) | 21.56 | 0.276 | −8.96 [−47.5, +29.5] | 70.5 % |

Full table (all 18 combinations, MAPE, SNR): `reports/rppg_baseline/summary.md`; every window:
`reports/rppg_baseline/windows.csv`; per-session whole-recording errors:
`reports/rppg_baseline/sessions_whole_recording_errors.csv`.

Figures (`reports/rppg_baseline/figures/`): `rppg_mae_by_protocol.png` (MAE + CI per method and
protocol), `rppg_scatter_d2_w10s2.png` (estimate vs reference), `rppg_bland_altman_pos_d2_w10s2.png`,
`rppg_session_errors_whole.png` (every session, every method).

## 4. Reading the numbers

* **POS ≈ CHROM ≫ Green.** Green alone locks onto low-frequency noise in a quarter of the windows.
* **The typical error is small, the tail is not.** POS MAE 1.3 bpm, but RMSE 5.9 bpm and LoA ±11 bpm
  on DATASET_2: ~2.5 % of windows are gross failures, almost all *under*-estimates (median estimate
  58 bpm vs. reference 80 bpm) — the spectral peak jumps to a low-frequency artefact (motion,
  illumination) instead of the pulse.
* **Failures concentrate in a few recordings.** Half of the POS failure windows (33 of 65) come from
  one recording, DATASET_1 `5-gt` (whole-recording error −25 bpm for every method). The DATASET_1 CIs
  are wide because there are only 8 recordings.
* **Whole recording vs. windows.** One HR per ~68 s recording averages failures away (POS 0.70 bpm),
  but it hides HR changes during the task; the 10 s protocol is the honest one for a monitoring use
  case.
* **Not comparable 1:1 with published tables.** Published unsupervised POS/CHROM/Green MAEs on UBFC-rPPG
  range from ~4 to ~10 bpm depending on protocol (test split, window, ROI, reference HR definition;
  e.g. [PhysNeXt 2026](https://arxiv.org/pdf/2603.19752): CHROM 4.06 / POS 4.08;
  [RF-BayesPhysNet 2025](https://arxiv.org/pdf/2504.03915): POS 8.35 / CHROM 8.20). Our protocol uses
  all 42 DATASET_2 videos, a skin-masked central ROI, the real frame clock, and the same HR estimator
  for reference and estimate — each of those lowers the error. Report our numbers with this protocol,
  not as a leaderboard claim.

## 5. What this does and does not support (for the poster)

Supports: "the optical layer of the pipeline recovers heart rate from ordinary RGB video with a
median-case error of about 1 bpm on 42 real subjects (UBFC-rPPG, POS, 10 s windows), with a failure
tail we quantify."

Does **not** support: anything about jugular veins, fluid shift, microgravity or a camera-based venous
measurement. The link from the optical signal to venous state stays a clearly labelled synthetic
bridge (sprint rule: *nie udajemy pełnej walidacji end-to-end*).

## 6. Caveats

* UBFC is a lab dataset: indoor light, one camera, mostly still young adults, limited skin-tone range.
* DATASET_2 subject 27: no face images in any output (the dashboard shows signals only, never frames).
* The reference is a finger pulse oximeter (CMS50E), itself noisy; its HR column has dropouts and is
  not used.
* Bland–Altman limits of agreement are computed over all windows; windows of one person are repeated
  measurements, and the limits are not corrected for that (Bland & Altman, 2007) — they are likely a
  little too narrow. The MAE confidence intervals do account for it (bootstrap over sessions).
* The Green/CHROM/POS implementations are the repository's own (CHROM uses one global α instead of the
  original windowed overlap-add). Improvements are tracked as experiments, not folded into this
  baseline silently.

## 7. Improvements (experimental track)

`docs/experiments_rppg.md` reports eight experiments run on top of this frozen baseline with a fixed
tune/hold-out split. The promoted variant — face box interpolated between detections, whole-face ROI with
skin mask, POS, Viterbi HR tracking, optional abstention — lowers the held-out POS MAE from 1.74 to
1.23 bpm (0.65 on held-out DATASET_2 people; 0.58 with abstention). It runs as the separate pipeline stage
`rppg_improved` (needs `python scripts/run_roi_variants.py` once, ~5 min) and writes
`reports/rppg_improved/`; the baseline numbers above are unchanged.
