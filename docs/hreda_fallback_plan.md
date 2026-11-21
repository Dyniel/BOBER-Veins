# ESA HREDA: status and fallback plan

*Owner: data (Michał). Status checked 2026-11-05 via the public HREDA TAP service; the check re-runs on
every `python -m vascushift.cli pipeline --online` and the result lands in
`reports/data_audit/audit_summary.json`.*

## 1. Status

| Item | Finding |
|---|---|
| Investigation | *Headward Fluid Shift* (`HeadwardFluidShift_PARA`, DOI 10.57780/esa-0ggni9p), ESA parabolic flight campaign PFC82, June 2023, 9 subjects, 0 / 0.25 / 0.5 / 0.75 G + ground |
| Files | **0** (`data_available = False`, results "under evaluation") |
| Access | any HREDA download requires an account (anonymous → HTTP 403); this does not help while there are no files |
| Related HREDA items with files | Drain Brain (ISS) and bed-rest studies list only *data blank books* (PDF descriptions), raw data on request; EPO Uznański videos (30.5 GB, login) have no physiological ground truth |

Conclusion: the sprint cannot rely on HREDA. Per the sprint plan (*"jeśli nie – ustalony plan
zastępczy bez blokowania reszty"*) the work continues on the substitutes below. Nothing waits for ESA.

## 2. What HREDA would have answered, and the substitute for each question

| Question (HeadwardFluidShift design) | Real substitute in the repo | Coverage / limits |
|---|---|---|
| How does IJV cross-sectional area change with the gravity level along the body axis? | **BHP-Lab tilt** (Whittle & Diaz-Artiles 2023, MIT): individual IJV area L/R, 12 people, gz_body −0.71…+1.0, supine + prone (`data/processed/ijv_gravity_cohort_real.csv`) | ground tilt, not reduced gravity: the transverse component stays ≈ 1 g; individual data → LOSO possible |
| Same at true partial gravity | **Lee et al. 2020** group means (right IJV, seated, 0.25/0.5/0.75/1 G parabolic + supine) | aggregates only (n = 8); IJVP only at 0.5 G and supine (n = 5) |
| What happens at 0 G? | **Marshall-Goebel et al. 2019** ISS means (left IJV area, IJVP, flight days 50 and 150, ± LBNP 25 mmHg) and **Martin et al. 2016** (IJVP at 0 G in parabolic flight) | aggregates; shows that 0 G ≠ 1 G supine |
| IJV pressure vs gravity | BHP-Lab compression sonography (individual, 12 → 24 internal) + the three papers above | compression IJVP has outliers (> 60 mmHg in head-down prone): flagged, robust statistics |
| Cardiovascular context (HR, BP, SV, CO) | **PhysioNet PRCP** (10 people, supine → 75° tilt → standing, beat-to-beat ABP/ECG, ODC-By); BHP tilt Finapres data (internal) | ground posture only |
| Does a countermeasure reverse the shift? | **BHP-Lab LBNP** dose-response (internal) + ISS LBNP rows of Marshall-Goebel | LBNP repo has no licence → internal use |
| Eye / SANS link | BHP tilt **intraocular pressure** (internal) | no licence → internal |

## 3. Decision rules

1. **Model calibration and LOSO evaluation** use `real_ijv_cohort()` (`vascushift.data.cohorts`) —
   real individual data with the gravity geometry columns (`gz`, `tilt_deg`, `posture_deg`, `gz_body`,
   `family`). The synthetic ESA-like table stays available only as a clearly labelled synthetic
   benchmark (`generate_synthetic_esa_like_cohort`, provenance `SYNTHETIC_…`).
2. **Partial-gravity and 0 G claims** use the published means as external anchors (never as
   individual data, never with invented SDs).
3. **Anything for the poster** uses only licensed sources (MIT / ODC-By / published tables). The
   unlicensed BHP repositories (24-person tilt, LBNP, IOP) stay internal until A. Diaz-Artiles
   agrees (request draft in `docs/data_audit.md` §6).
4. **If HREDA releases files**: register an account, run `python scripts/download_data.py --dataset
   hreda-snapshot` to see the file list, write a loader to the common long format
   (`vascushift.data.schema.COMMON_PHYSIO_COLUMNS`, `provenance = raw_individual`), and add it to
   `load_all_physiology()`. Nothing else in the pipeline needs to change.

## 4. Requests that would upgrade the substitutes

| Request | Gives | Effort / time |
|---|---|---|
| A. Diaz-Artiles (adartiles@tamu.edu): permission for tilt + LBNP repos | 24 people, both sexes, IOP, LBNP → publishable | e-mail; days |
| NASA LSDA: individual data of Lee 2020 / Marshall-Goebel 2019 | true partial gravity / 0 G individual data | formal request; weeks–months |
| ESA HREDA account + contact to the HeadwardFluidShift PI | the original target data, when released | unknown |
