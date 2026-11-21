# Data audit — what we really have (VascuShift, sprint task of Michał)

*Audit date: 2026-11-04. Every statement below was checked against the source itself (ESA HREDA TAP
service, DOI/DataCite records, full texts via Europe PMC/PMC, the downloaded files). Re-run the
machine part with `python -m vascushift.cli data-audit` (outputs in `reports/data_audit/`).*

## TL;DR

1. **The ESA HREDA "Headward Fluid Shift" dataset has no data.** The investigation exists
   (DOI 10.57780/esa-0ggni9p, 82nd ESA/NASA parabolic flight campaign, 12–15 June 2023, N = 9,
   PI S. M. C. Lee), but HREDA reports `data_available = False`, **0 files**, results *"under
   evaluation"*. Nothing can be downloaded, with or without an account.
2. **The "verified ESA cohort" in the repo was synthetic.** `esa_loader.get_verified_published_cohort()`
   drew the 9 × 5 table with `np.random` around published group means; IJV pressure for all 45 rows
   and supine HR/MAP do not exist in any paper. README "Result A/B" (LOSO on "real ESA data") were
   computed on this synthetic table. It is now relabelled (`generate_synthetic_esa_like_cohort`,
   `provenance = SYNTHETIC_…`); numbers unchanged so Daniel's runs stay reproducible.
3. **Lee et al. 2020 is not PFC82.** It is an earlier campaign (June 2018), **without 0-G parabolas**;
   IJV pressure exists only for 5 subjects at 0.50 G and 1-G supine; one subject has no IJV area.
   Individual data only on request (NASA LSDA).
4. **We found real, downloadable, individual-level jugular data vs gravity vector:** Whittle &
   Diaz-Artiles (Texas A&M) tilt studies on GitHub — IJV area L/R, IJV pressure, intraocular pressure,
   HR/BP/SV/CO in 12–24 subjects at body-axis Gz from +1.0 (seated) through +0.71 … −0.71
   (±45° tilt), plus an LBNP dose-response set (0 to −50 mmHg). This is now our main physiology GT.
5. **Optical layer: UBFC-rPPG is openly downloadable** (92 GB, 50 videos with finger-PPG GT, all
   downloaded and checksum-verified); loaders work end-to-end on all 50: the windowed baseline gives
   POS HR MAE 1.29 bpm on DATASET_2 (10 s windows, `docs/rppg_baseline.md`; the 0.94 bpm in §3.1 is an
   earlier whole-recording loader check). DATASET_2 frames are irregular (23–30 fps, holes up to 1 s); the
   loader now uses the real frame timestamps (§3.1). The old rPPG
   benchmark (README "Result D", MAE 0.03 bpm) ran on synthetic sinusoids — the old loader could
   never read real data.
6. **No dataset pairs face video with jugular/fluid-shift ground truth.** Per the sprint rule we show
   (a) a validated optical layer on UBFC, (b) a validated physiology/model layer on tilt + flight +
   ISS data, (c) a synthetic bridge between them — clearly labelled.

## 1. Inventory

| Key (registry) | Layer | What / ground truth | N | Gravity / posture coverage | Access | Licence | Status |
|---|---|---|---|---|---|---|---|
| `esa_hreda_headward_fluid_shift` | physiology | IJV area, flow, pressure (planned) | 9 | 0, 0.25, 0.5, 0.75 G + ground seated/supine | HREDA: **no files** | CC BY-NC 3.0 IGO (metadata) | metadata only |
| `lee2020_partial_gravity` | physiology | right IJV area, IVC, CCA flow/area, flow grade, HR, MAP; IJVP n=5 | 9 (IJV n=8) | seated 1.0/0.75/0.5/0.25 G (flight), 1-G supine | group means transcribed; raw via NASA LSDA request | CC BY 4.0 | transcribed |
| `marshall_goebel2019_iss_ijv` | physiology | left IJV area & pressure, SV, CO, HR, BP | 11 | **real 0 G (ISS FD50/FD150)**, ±LBNP, seated/supine/HDT15 pre & post | group means transcribed; raw via LSDA | CC BY | transcribed |
| `martin2016_parabolic_ijvp` | physiology | IJV pressure | 11 | 1-G supine, 0 G seated (flight) | transcribed (mean ± SD) | CC BY | transcribed |
| `bhp_carotid_jugular` | physiology | **per-subject** IJV area L/R, IJVP L/R, CCA area | 12 (IJV 11) | seated; supine & prone tilt +45…−45° (gz_body +0.71…−0.71) | GitHub, pinned commit | **MIT** | downloaded |
| `bhp_tilt_dose_response` | physiology | per-subject HR, BP, SV, CO, IJV area/pressure, **IOP**, CCA | 24 (12F/12M) | same tilt grid | GitHub | **none stated** → internal use, ask authors | downloaded |
| `bhp_lbnp_dose_response` | physiology | same variables under LBNP | 24 | supine & HDT15 × LBNP 0…−50 mmHg | GitHub | **none stated** | downloaded |
| `physionet_prcp` | physiology | ECG, finger ABP, **table angle** (250 Hz) | 10 | supine, slow/fast tilt to 75°, standing | open | ODC-By 1.0 | downloaded |
| `physionet_cardioresp_orthostat` | physiology | ABP, MCA velocity (TCD), resp., raw 16-ch NIRS | 10 | sitting → standing → sitting | open | PhysioNet CR Health Data 1.5.0 | downloaded |
| `hreda_drain_brain` | physiology | ISS jugular plethysmography (Taibi 2017) | 1 astronaut | ISS vs ground | HREDA login; only a Data Blank Book is listed; medical-sensitive | ESA | login required |
| `hreda_bed_rest_blank_books` | physiology | HDT bed-rest variable catalogues (Cocktail, MNX, NUC, BRAG, RSL) | – | −6° HDT bed rest | HREDA login, raw data by request | ESA | login required |
| `ubfc_rppg` | optical | 640×480 uncompressed RGB video + CMS50E finger PPG & HR (DATASET_1 adds SpO2) | 42 + 8 videos | – | public mirrors (OneDrive used) | research use, cite; **subjects 21/27 no face images** | downloaded (92 GB) |
| `physionet_videopulse` | optical | pre-extracted 1-channel video pulse + finger pulse | 15 (40 rec.) | – | open | ODC-By 1.0 | downloaded |
| `hreda_epo_uznanski_videos` | optical | astronaut (S. Uznański) face video **in microgravity**, no physiological GT | – | real 0 G | HREDA login (public files) | ESA EPO terms | login required |
| `pure`, `ubfc_phys`, `mmpd` | optical | video + PPG GT | 10–33 | – | request / signed agreement | research only | request required |
| `synthetic_esa_like_cohort`, `synthetic_rppg_cohort` | both | generated in code | – | – | – | – | **synthetic** |

Considered and rejected: NASA OSDR OSD-679/680/681 ("Head-down tilt as a model for ICP/IOP") —
rat hindlimb-suspension data, not human; PhysioNet `cves`, `cded`, `cerebral-vasoreg-diabetes` —
tilt data in elderly / diabetic cohorts, 3–190 GB, far from the astronaut population.

## 2. Physiology / fluid-shift ground truth

### 2.1 ESA HREDA (checked live through the public TAP service)

| Investigation | data_available | files visible | note |
|---|---|---|---|
| `HeadwardFluidShift_PARA` (PFC82, 2023) | **False** | 0 | results "under evaluation"; procedure: 9 subjects, ground supine + seated, flight 0/0.25/0.50/0.75 G, IJV area, flow pattern, pressure |
| `Drain_Brain_ISS` | True | 1 PDF (blank book) | medical-sensitive → data request |
| `Cocktail/MNX/NUC/BRAG/RSL_BRIM` (bed rest) | True | 1–2 PDFs each | variable catalogues only |
| `Hemo_BRIM` (BRACE 2023) | True | 0 | flag says True but nothing is listed |
| `EPO_UznanskiVideos_ignis_ISS` | True | 182 (30.5 GB MOV/MP4/JPG) | public, login needed |

* Any download (even public files) needs an ESA/HREDA login: anonymous calls to
  `hreda-sl-tap/data?retrieval_type=PRODUCT` return **403 "Anonymous users cannot download data"**.
* The old `HREDA_TAP_URL` in `.env.example` is correct; the snapshot of the relevant records is
  committed at `data/external/hreda/hreda_snapshot.json` (`python scripts/download_data.py --dataset hreda-snapshot`).

### 2.2 Lee et al. 2020 (Front Physiol 11:863) — facts that contradict the repo

* Campaign: **1st International Space Life Sciences Working Group campaign, June 2018**, Novespace —
  *not* PFC82 / 2023. "Weightless parabolas (0-G) were not included in this parabolic flight campaign."
* 9 subjects (5F/4M), seated in flight at 0.25/0.50/0.75 G and 1.00 G level flight; **1-G supine on
  the ground** before flight as "0-G analog". The repo encodes this supine row as `gz = 0.0`.
* IJV area: one subject unusable at all levels (**n = 8**). Table 3: 12 (9–16), 24 (13–35),
  34 (21–46), 68 (40–97) mm² seated at 1.00/0.75/0.50/0.25 G; supine 108 (74–131)
  *(the abstract prints 103 (75–131))*.
* **IJV pressure**: none usable seated at 0.75 and 1.00 G; only 9.5 ± 3.4 mmHg (0.50 G) vs
  19.1 ± 7.6 mmHg (supine), n = 5. The synthetic table had pressure for all 45 rows.
* Finger BP missing for 3 subject-days; supine HR/MAP not reported at all.
* Data availability statement: "Requests … should be directed to NASA's Life Sciences Data Archive".
* Table 3 prints the CCA area unit as "cm" (values are cm²).

### 2.3 Real microgravity anchors (ISS, parabolic 0 G)

Marshall-Goebel 2019 (11 ISS crew, **left** IJV): area 9.8 mm² seated → 80.7 supine → 107.7 HDT15
pre-flight; **70.3 on flight day 50, 60.0 on day 150**; LBNP −25 mmHg lowers it to 44.7/42.7.
IJV pressure 5.1 → 17.3 → 20.7 mmHg pre-flight; 21.1 (FD50), 15.8 (FD150) in flight.
Martin 2016: parabolic 0 G IJVP 23.9 ± 5.6 vs 9.9 ± 5.1 mmHg supine (n = 11).
Table erratum kept: HR at FD150 + LBNP printed as "7" (CI 68–76) → stored as missing.

**Modelling consequence:** 1-G supine and 0 G both have zero head-to-foot gravity (`gz_body = 0`),
but they are *not* the same state (ISS 70 mm² < supine 81 mm² in the same crew). All data therefore
carry both `gz_platform` (environment) and `gz_body = gz_platform · sin(tilt)` — do not collapse them.

### 2.4 BHP-Lab tilt and LBNP data (main individual-level GT)

* `carotid-jugular-characteristics` (MIT) — Whittle & Diaz-Artiles, J Appl Physiol 2023,
  doi:10.1152/japplphysiol.00248.2022. Coding from the repo README: Index 0 seated, 1–7 = 45/30/15°
  HUT, 0°, 15/30/45° HDT; Side D = right, S = left; Face S = supine, P = prone, SB = seated.
  Units (paper): area mm², IJVP mmHg. Seated baseline IJV area only n = 4 (separate session).
* `tilt-dose-response` — 24 subjects incl. 12 women, adds IOP (SANS-relevant) and Finapres
  haemodynamics. The `CVP` column is a constant 4.6 (device default) → ignored. Angle labels are
  mis-encoded (`45� HUT`) → the loader uses `Index`.
* `LBNP-Dose-Response` — supine and 15° HDT with LBNP 0…−50 mmHg; IJV flow, CCA PSV/EDV and OPP
  columns are not mapped yet (units undocumented).
* **Licence:** only the first repo is MIT. The other two are public without a licence: fine for
  internal analysis; e-mail the authors before putting per-subject values or derived figures on the
  poster (draft in §6). `load_all_physiology(include_unlicensed=False)` gives the publication-safe set.

Group medians, right IJV area (supine series, `reports/data_audit/internal/ijv_area_vs_gravity_incl_unlicensed.csv`; the committed `ijv_area_vs_gravity.csv` contains licensed sources only):
~19 mm² at +45° → 71 at 0° → 185 at −15° → ~197 at −45°; LBNP at HDT15 reduces it from 102 to 51 mm².

### 2.5 PhysioNet

* **PRCP** (10 subjects): ABP/ECG/angle at 250 Hz; HR 66 → 81 bpm supine → 75° HUT (every subject
  rises). Event annotations use 6+ different spellings ("Initiate"/"Start"/"Initiation", "Stand-up from
  supine", truncated "dow"/"supin", numeric prefixes) → normalised by `event_kind()`. During
  "Stand up" the angle channel stays ~0° (subject leaves the table) → posture taken from events.
  Finger BP: hand height not controlled — MAP differences across postures partly hydrostatic.
* **cardioresp-response-orthostat** (10 subjects): ~3.3 Hz CSV. Header mislabels several NIRS
  columns (e.g. `i4_730`, `i5_805` out of order) → renamed by position per README; header contains
  non-UTF-8 bytes; **subj10 ABP median −95 mmHg** (calibration problem); subj05 excluded by the
  authors (no TCD window) but present in the files.

## 3. Optical / rPPG

### 3.1 UBFC-rPPG (Bobbia et al. 2017)

* Size **92.1 GB**: DATASET_2 75.0 GB (42 videos, 1.1–3.1 GB each), DATASET_1 17.1 GB (8 videos).
  Uncompressed `rawvideo bgr24` AVI, 640×480.
* Mirrors: the Google Drive folder returns *"Too many users have viewed or downloaded this file
  recently"* for videos → the downloader uses the authors' OneDrive/SharePoint guest link with
  HTTP-Range resume. Manifest with SHA-256: `data/raw/rppg/UBFC-rPPG/_download_manifest.json`.
* All 50 videos downloaded (104 files, every one matches the SHA-256 and size in the manifest).
* **Frame rate is not 30 fps, and in DATASET_2 it is not even constant**
  (`reports/data_audit/ubfc_inventory.csv`):
  * DATASET_1: constant 28.67 fps (one video 28.64). GT is a separate 62 Hz log; video and GT spans
    agree within ~0.1 s.
  * DATASET_2: **`ground_truth.txt` has exactly one row per video frame in all 42 sessions**, so its
    time column is the frame clock. That clock is irregular: median step 33–43 ms, mean rate
    23.2–30.0 fps per video (subjects 25, 26, 27 ≈ 23.3 fps); 34/42 sessions have at least one step
    > 0.1 s and 12/42 have dropped-frame holes > 0.25 s (17 holes; longest 1.0 s in subject23,
    0.95 s subject24 with 4 holes, 0.88 s subject15, 0.75 s subject9). Nine files repeat a stamp
    (Δt = 0, never backwards).
  * Consequence: `fs = 30` gives ~29 % HR error for subjects 25–27, and even the per-video header
    fps (an average) misplaces every frame after a hole by up to 1 s relative to the PPG.
    `load_ubfc_session` now uses the GT time column as frame timestamps (`frame_clock`), drops
    duplicate-stamp frames, and resamples RGB and PPG onto one uniform 30 Hz grid
    (`align_to_uniform_grid`); grid samples inside holes > 0.25 s get `valid = False`. Per-frame data
    stays available under `session["frames"]`.
* Oximeter HR column drops to 1 bpm in subjects 11, 18, 20, 24 → reference HR comes from the PPG
  waveform (the dataset readme says the authors did the same) — `reference_hr_from_ppg()`.
* **Consent restrictions** (readme + Agreement.xlsx): DATASET_2 subjects 21 and 27 — facial images
  must not appear in any publication, presentation or report. The release has no `subject21` folder,
  so in practice this is **subject27**; the flag also covers 21 defensively. Sessions carry
  `no_face_display=True`; the dashboard and poster must respect it.
* Tooling: OpenCV 5 dropped the Haar face cascades (→ `opencv-python-headless<5`), and the FFMPEG
  backend bundled in the OpenCV wheel segfaults on these raw AVIs → frames are decoded with a system
  `ffmpeg` pipe.
* Face RGB extraction ran on **all 50 videos** (`scripts/extract_ubfc_traces.py`, ~7 s per video,
  cache 2.2 MB in `data/interim/ubfc_rgb/`, log `_extraction_log.csv`): Haar face found from the first
  frame in every video, in ≥ 99.9 % of frames (lowest: subject14 and subject11, 99.9 %).
* **Loader check, not the baseline** (one HR estimate per whole recording with the repo's Green /
  CHROM / POS, reference HR from the contact PPG; the windowed benchmark is the next task):

  | Subset | Method | MAE [bpm], frame clock (new) | MAE, uniform header fps (old) | \|err\| < 3 bpm (new) |
  |---|---|---|---|---|
  | DATASET_2 (42) | POS | **0.94** | 1.53 | 90.5 % |
  | DATASET_2 (42) | CHROM | 2.58 | 2.57 | 85.7 % |
  | DATASET_2 (42) | Green | 13.67 | 13.28 | 61.9 % |
  | DATASET_1 (8) | POS / CHROM / Green | 4.07 / 4.19 / 11.41 | same (constant fps) | 75 / 75 / 62.5 % |

  The frame clock matters exactly where frames were dropped: POS error subject9 −1.80 → +0.35,
  subject15 −1.99 → −0.13, subject24 −1.85 → +0.15, subject25 (23 fps) −1.52 → −0.27 bpm. Known
  failures for the baseline task: DATASET_1 `5-gt` (all methods ≈ −26 bpm with the old and the new
  timing), subject23 (−6 bpm), Green on subject11 (−68 bpm, low-frequency peak).

### 3.2 Others

* `videopulse` contains only already-extracted single-channel "video pulse" signals (15/60 fps) and a
  1 kHz finger pulse — no RGB, so CHROM/POS cannot be tested on it; HR-only cross-check.
* Restricted datasets worth requesting only if UBFC is not enough: PURE (motion, e-mail),
  UBFC-Phys (stress, form), MMPD (skin tones/mobile, signed agreement).
* HREDA EPO Uznański videos: real microgravity faces (and a Polish astronaut), no HR ground truth →
  usable only for a qualitative "the pipeline runs on ISS footage" demo; check ESA terms first.

## 4. Problems found in the existing repository

| Where | Problem | Done now |
|---|---|---|
| `src/vascushift/data/esa_loader.py` | synthetic table presented as "verified published cohort"; provenance `Lee_et_al_2020_Frontiers_PFC82`; comments claim "exact individual statistics" | renamed + deprecated alias, provenance `SYNTHETIC_…`, `metadata["is_synthetic"]`; values unchanged |
| same | supine row encoded `gz = 0.0`; invented IJV pressure / supine HR-MAP / all SDs | documented; real values in `vascushift.data.literature` |
| same | `load_esa_data()` overwrites `data/processed/esa_headward_fluid_shift.csv` on every call | documented (Daniel's pipeline depends on it) |
| `src/vascushift/data/rppg_loader.py` | real-data branch needed `rgb_traces.npy` that nothing produced → always synthetic | now loads UBFC via `vascushift.data.ubfc` (`source="auto"/"ubfc"/"synthetic"`, `is_real` flag) |
| `src/vascushift/experiments/rppg.py`, optical code | `fs = 30.0` defaults; uniform frame spacing assumed | UBFC sessions are resampled on their real frame clock to a uniform grid and carry `fs` + a `valid` mask; experiments pass `session["fs"]` (they do). `visualization/figures.py:375` still hard-codes `/ 30.0` for the time axis — correct for the 30 Hz grid, flag for Daniel if the grid changes |
| `demo/app.js` | hard-coded `ESA_GROUND_TRUTH` incl. invented pressure means/SDs, supine labelled "0G" | **not changed** — dashboard task (next) |
| `README.md`, `docs/*`, `data/README.md` | "verified human measurements", "PFC82, June 2023 (Lee 2020)", rPPG "N = 12 sessions" (synthetic) | data docs corrected; README results left to Daniel (flagged at the top) |
| `pyproject.toml` | `opencv-python` unpinned (5.x breaks Haar), no data extras | `cv`/`data` extras with `opencv-python-headless>=4.8,<5`, `gdown`, `wfdb`, `openpyxl` |

## 5. How to reproduce

```bash
uv venv .venv --python 3.12 && source .venv/bin/activate
uv pip install -e ".[dev,data]" && uv pip install torch --index-url https://download.pytorch.org/whl/cpu
# system ffmpeg/ffprobe required for UBFC video decoding

python scripts/download_data.py --dataset physionet       # ~80 MB, SHA-256 verified
python scripts/download_data.py --dataset github          # <1 MB, pinned commits
python scripts/download_data.py --dataset hreda-snapshot  # metadata only
python scripts/download_data.py --dataset ubfc --gt-only  # 50 GT files, seconds
python scripts/download_data.py --dataset ubfc            # 92 GB videos, resumable
python scripts/extract_ubfc_traces.py --workers 6         # face RGB cache -> data/interim/ubfc_rgb/

python -m vascushift.cli data-audit                       # -> reports/data_audit/
pytest tests/
```

Python entry points:

```python
from vascushift.data.schema import load_all_physiology          # every REAL physiology row, common long format
from vascushift.data.literature import literature_aggregates    # Lee 2020, Marshall-Goebel 2019, Martin 2016
from vascushift.data.bhp_lab import load_carotid_jugular, load_tilt_dose_response, load_lbnp_dose_response
from vascushift.data.physionet_posture import prcp_beat_table, prcp_condition_summary, load_orthostat_subject
from vascushift.data.ubfc import list_ubfc_sessions, load_ubfc_session, ubfc_inventory
from vascushift.data.rppg_loader import load_rppg_benchmark_cohort  # source="ubfc" for real data
from vascushift.data.registry import DATASETS                    # this inventory as code
```

## 6. Access requests to send (drafts — someone from the team must send them)

1. **NASA Life Sciences Data Archive** (https://lsda.jsc.nasa.gov/, data request form): individual
   de-identified data of Lee et al. 2020 (doi:10.3389/fphys.2020.00863) and Marshall-Goebel et al.
   2019 (doi:10.1001/jamanetworkopen.2019.15011): IJV area, IJV pressure, flow grade, HR, MAP per
   subject and condition; purpose: student ISSSP 2026 modelling project, non-commercial.
   Expect weeks — not on the critical path.
2. **PI of HeadwardFluidShift_PARA (Stuart M. C. Lee, KBR / NASA JSC)** — ask whether PFC82
   (2023, includes 0 G) group-level results can be shared or when they will be published.
3. **Ana Diaz-Artiles (adartiles@tamu.edu)** — permission to show figures/derived results from the
   `tilt-dose-response` and `LBNP-Dose-Response` repositories on an ISSSP poster with citation.
   *(Most valuable request: fast, and it unlocks 24 subjects incl. women and IOP.)*
4. **ESA HREDA account** (free registration via the HREDA site) — needed for the Data Blank Books
   and the EPO microgravity videos; a team member must register personally.
5. Optional: PURE / UBFC-Phys / MMPD request forms if we want motion or skin-tone robustness.

## 7. What this means for the sprint plan

* **HREDA fallback (plan 23–25.10) is now concrete:** model fitting and validation on BHP-Lab tilt
  data (individual, continuous `gz_body`), with Lee 2020 parabolic means and Marshall-Goebel ISS means
  as *external* validation points (different side of the neck: right vs left IJV — keep separate).
* Daniel: the README LOSO claim on "N = 9 real ESA subjects" cannot stand; the natural replacement
  is LOSO on the 11–23 BHP subjects, then compare predictions with the flight/ISS aggregates.
* Optical baseline (19–22.10): run Green/CHROM/POS on all 42 DATASET_2 videos with the real `fs`;
  report per-video MAE/RMSE/r against PPG-derived HR.
* Dashboard: replace `ESA_GROUND_TRUTH` in `demo/app.js` with `reports/data_audit/ijv_area_vs_gravity.csv`
  / pipeline outputs; never show faces of UBFC subjects 21/27.
* Common format (next task): the physiology long format is already defined in
  `src/vascushift/data/schema.py`; the optical session dict is defined by `load_ubfc_session`.

### 7.1 Status update 2026-11-05 (follow-up tasks done)

* Optical baseline: done on all 50 recordings with the real frame clock — `docs/rppg_baseline.md`
  (POS 1.29 bpm MAE in 10 s windows on DATASET_2).
* HREDA fallback: written down (`docs/hreda_fallback_plan.md`) and executed
  (`docs/physiology_first_analysis.md`); the real per-person cohort for the model is
  `data/processed/ijv_gravity_cohort_real.csv` (`vascushift.data.cohorts.real_ijv_cohort`).
* Common formats: physiology long table, real IJV cohort, optical session `.npz` + index, rPPG window
  table — all defined in `src/vascushift/data/schema.py` / `cohorts.py` and documented in
  `docs/data_dictionary.md`.
* Dashboard: `demo/` now reads only pipeline outputs (`python -m vascushift.cli pipeline`); the
  hard-coded `ESA_GROUND_TRUTH` and the synthetic waveform are gone; signals only, no video frames.
