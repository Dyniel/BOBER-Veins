# Data Directory - BOBER Veins / VascuShift

Full audit, provenance and access routes: [`docs/data_audit.md`](../docs/data_audit.md).
Machine-readable registry: `src/vascushift/data/registry.py`.

## Directory structure

| Path | Content | In git? |
|---|---|---|
| `raw/physionet/<slug>/<version>/` | PhysioNet PRCP, videopulse, cardioresp-response-orthostat (SHA-256 verified) | no |
| `raw/github/<repo>/` | BHP-Lab tilt / jugular / LBNP data (pinned commit in `_download_manifest.json`) | no |
| `raw/rppg/UBFC-rPPG/` | UBFC-rPPG videos + ground truth (~92 GB) | no |
| `raw/esa/` | place for ESA / NASA LSDA files if ever obtained (currently empty) | no |
| `interim/` | caches (e.g. `ubfc_rgb/*.npz` face RGB traces), download logs | no |
| `external/literature_aggregates.csv` | group means/CI transcribed from Lee 2020, Marshall-Goebel 2019, Martin 2016 | yes |
| `external/hreda/hreda_snapshot.json` | ESA HREDA metadata snapshot (availability, file lists) | yes |
| `processed/rppg/sessions.csv` | index of preprocessed optical sessions (`OPTICAL_SESSION_COLUMNS`: frame clock, fps, valid fraction, reference HR, display flag) | yes |
| `processed/rppg/sessions/<id>.npz` | per-session RGB + finger PPG on a uniform 30 Hz grid (`time, rgb, ref_ppg, valid, face_found`) — **waveforms, UBFC agreement** | **no** |
| `processed/physiology_long.csv` | all licensed physiology in the common long format (literature + PRCP + BHP carotid-jugular MIT) | yes |
| `processed/ijv_gravity_cohort_real.csv` | real per-person IJV area/pressure cohort with gravity geometry (`gz, tilt_deg, posture_deg, gz_body, family`) for the model code — 12 people, MIT | yes |
| `processed/internal/` | the same tables incl. unlicensed BHP tilt (24 people) and LBNP data — **team use only** | **no** |
| `processed/esa_headward_fluid_shift.csv` | **SYNTHETIC** 9 x 5 stand-in written by `load_esa_data()` (see below) | yes |
| `synthetic/` | controlled synthetic benchmarks | - |

Download everything that is openly available, then build all processed outputs, reports and the dashboard:

```bash
python scripts/download_data.py --dataset all   # PhysioNet + GitHub + HREDA snapshot + UBFC (92 GB)
python scripts/extract_ubfc_traces.py --workers 6   # optional: parallel face-RGB cache (~1 min for 50 videos)
python -m vascushift.cli pipeline               # check -> audit -> preprocess -> rppg -> physiology -> figures -> dashboard -> manifest
```

Formats are defined in `src/vascushift/data/schema.py` and described in `docs/data_dictionary.md`.

## Fluid-shift / gravity physiology

* **ESA HREDA `HeadwardFluidShift_PARA`** (DOI [10.57780/esa-0ggni9p](https://doi.org/10.57780/esa-0ggni9p),
  82nd ESA/NASA parabolic flight campaign, June 2023, N = 9): catalogue entry only -
  `data_available = False`, no files, results under evaluation.
* **Lee et al. 2020** ([10.3389/fphys.2020.00863](https://doi.org/10.3389/fphys.2020.00863)) - a different,
  earlier campaign (June 2018, no 0-G parabolas). Group means/95 % CI in `external/literature_aggregates.csv`;
  individual data only via NASA LSDA request.
* **Marshall-Goebel et al. 2019** (ISS, n = 11) and **Martin et al. 2016** (parabolic 0 G, n = 11):
  group values in the same CSV.
* **Whittle & Diaz-Artiles** tilt data (GitHub, BHP-Lab): per-subject IJV area/pressure, IOP and
  haemodynamics from +45 deg head-up to -45 deg head-down tilt, plus LBNP. Only
  `carotid-jugular-characteristics` is MIT-licensed; the other two repositories carry no licence
  (internal analysis only until the authors agree).
* **PhysioNet PRCP**: ECG, ABP and tilt angle, 10 subjects.

`processed/esa_headward_fluid_shift.csv` is **not measured data**: it is drawn with `np.random`
around Lee 2020 group means (`provenance = SYNTHETIC_random_draws_around_Lee2020_group_means`).
IJV pressure for all rows and supine HR/MAP in that file do not exist in the paper.

## Optical rPPG

* **UBFC-rPPG** (Bobbia et al., Pattern Recognit. Lett. 2019): 42 + 8 uncompressed videos with
  finger-PPG ground truth. DATASET_2 subjects 21 and 27: facial images must not be shown in any
  publication, presentation or report.
* **PhysioNet videopulse**: pre-extracted video pulse signals only (no RGB video).

## Licensing

| Source | Licence |
|---|---|
| ESA HREDA metadata | CC BY-NC 3.0 IGO |
| Lee 2020, Marshall-Goebel 2019, Martin 2016 (transcribed values) | CC BY (open-access articles) |
| BHP-Lab `carotid-jugular-characteristics` | MIT |
| BHP-Lab `tilt-dose-response`, `LBNP-Dose-Response` | none stated (all rights reserved) |
| PhysioNet PRCP, videopulse | ODC-By 1.0 |
| PhysioNet cardioresp-response-orthostat | PhysioNet Contributor Review Health Data License 1.5.0 |
| UBFC-rPPG | research use with citation; per-subject image restrictions |
