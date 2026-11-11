# First analysis of real physiology vs the gravity vector

*2026-11-05 · HREDA fallback (see `docs/hreda_fallback_plan.md`) · real data only, no synthetic values.
Reproduce: `python -m vascushift.cli physiology-analysis` (or the full `pipeline`). Tables:
`reports/physiology_real/` (public sources) and `reports/physiology_real/internal/` (adds unlicensed
BHP-Lab data; git-ignored, team use only). Code: `vascushift.analysis.gravity_physiology`.*

## Data used

| Source | Licence | People | What |
|---|---|---|---|
| BHP-Lab carotid-jugular (Whittle & Diaz-Artiles, J Appl Physiol 2023) | MIT | 12 (IJV area 11) | IJV area, IJV pressure (compression sonography), L/R; tilt −45…+45° supine and prone, seated |
| BHP-Lab tilt-dose-response (Whittle et al., JAHA 2022) | none → internal | 24 (12 F / 12 M) | same protocol + HR, BP, SV, CO, intraocular pressure. **Contains the 12 people above** (960/976 values identical to 10⁻⁵) → never pooled with carotid-jugular |
| BHP-Lab LBNP-Dose-Response | none → internal | 24 | LBNP 0…−50 mmHg, supine and 15° head-down |
| PhysioNet PRCP | ODC-By | 10 | HR, BP: supine → 75° head-up tilt → standing |
| Lee 2020, Marshall-Goebel 2019, Martin 2016 | published tables | 5–11 per group | group means at partial gravity, ISS 0 G, parabolic 0 G |

Method: one value per person × condition (left/right averaged), median and IQR per condition;
within-person least-squares slope against gz_body = sin(tilt) over the seven tilt levels (ln scale for
area, linear for pressures and HR); paired ratios between conditions; 95 % CIs = bootstrap of the
median over people (5000 resamples). Implausible values (IJVP > 60 mmHg: 10 public / 29 internal,
mostly head-down; one HR of 16.5 bpm) are flagged; results are shown with all values and with flagged
values removed.

## Findings

### 1. IJV area falls steeply and in everyone as head-to-foot gravity grows (public data, n = 11)

| Posture | Slope of ln(area) per g | ≙ change per +0.5 g | People with a negative slope |
|---|---|---|---|
| Supine tilt | −1.98 (95 % CI −2.06 … −1.71) | **−63 %** (−64 … −57 %) | 11/11 |
| Prone tilt | −2.13 (−2.34 … −1.72) | −66 % (−69 … −58 %) | 10/10 |

Median area: supine −45° 183 mm², 0° 67 mm², +45° 17 mm²; seated 19 mm² (only 4 people had a
measurable seated IJV). Ratio −45° / +45° within a person: **9.4×** (6.1 … 13.9). The curve is
**sigmoid**, not exponential: it saturates at ≈ 190 mm² head-down (−30°/−45° equal) and at
≈ 15–20 mm² head-up — the collapsible-tube shape assumed by the compartment model. The log slope is a
summary, not a model.

Internal 24-person data reproduce it: −62 % per +0.5 g (−63 … −57 %), 23/23 supine.

### 2. IJV pressure follows the hydrostatic direction, steeper than a simple column

| Posture | Slope [mmHg per g], all values | flagged removed |
|---|---|---|
| Supine | −32.0 (−36.5 … −25.8) | −27.4 (−32.0 … −25.0) |
| Prone | −35.2 (−42.5 … −26.0) | −26.5 (−36.1 … −21.0) |

A rigid fluid column of 0.20–0.30 m (heart → mid-neck) gives ρ·g·h = 15.6–23.4 mmHg per g; the measured
slopes are steeper (compression-sonography IJVP overestimates at high pressures; venous tone and
cardiac filling also change with tilt). Supine 0°: 19.5 mmHg; seated: 6.2 mmHg (ratio within person
2.7×, 1.9 … 3.7).

### 3. Zero gravity is not the same as lying down (published ISS data)

Marshall-Goebel et al. 2019, same 11 crew, left IJV:

| Condition | IJV area [mm²] mean (95 % CI) | IJV pressure [mmHg] |
|---|---|---|
| Pre-flight seated, 1 G | 9.8 (−1.2 … 20.7) | 5.1 (2.5 … 7.8) |
| Pre-flight supine, 1 G (gz_body 0) | 80.7 (69.9 … 91.5) | 17.3 (14.8 … 19.8) |
| Pre-flight 15° head-down | 107.7 (96.7 … 118.7) | 20.7 (17.8 … 23.5) |
| **ISS flight day 50, 0 G** (gz_body 0) | **70.3 (59.3 … 81.2)** | **21.1 (18.5 … 23.7)** |
| ISS flight day 150 | 60.0 (48.8 … 71.2) | 15.8 (13.0 … 18.6) |
| ISS FD50 + LBNP 25 mmHg | 44.7 (33.2 … 56.2) | – |

Both supine and weightless have gz_body = 0, but in flight the area is *smaller* while the pressure on
day 50 is *higher* than supine on the ground. A model driven only by gz_body cannot reproduce this —
which is why the common format keeps `gz_platform`, `gz_body`, posture and LBNP separately.

### 4. Partial gravity in parabolic flight vs ground tilt at the same gz_body

Lee 2020 (right IJV, seated, parabolic flight): 68 / 34 / 24 / 12 mm² at 0.25 / 0.5 / 0.75 / 1 G.
BHP supine tilt, right IJV at gz_body 0.26 / 0.5 / 0.71: 32.6 / 17.6 / 19.4 mm²; seated 26.7 (n = 4).
Partial-gravity values are ≈ 1.2–2× the tilt values at matching gz_body, but the order reverses at
1 G seated. Different people, devices and postures (in tilt ≈ 1 g still acts across the body;
in a parabola it does not): **gz_body alone does not transfer between paradigms.** This is the
honest limit of using tilt as a microgravity analogue and an argument for keeping the transverse
component in the model.

### 5. Cardiovascular and eye responses (internal unless noted)

* **HR** (public, PRCP): +19 % at 75° head-up tilt vs supine (ratio 1.19, 1.12 … 1.39), 10/10 people;
  standing +19 %. Internal tilt: +14.3 bpm per g supine (10.3 … 17.4), 24/24 positive.
* **Intraocular pressure** (internal): −11.8 mmHg per g supine (−14.0 … −10.0); −45° vs +45° ratio
  2.16 (2.00 … 2.42). Head-down raises eye pressure — the SANS-relevant direction.
* **LBNP** (internal, n = 24): IJV area −19 % per −10 mmHg supine (−22 … −15 %) and −16 % at 15°
  head-down (−23 … −12 %); at −50 mmHg the area is 0.36× (supine) and 0.42× (head-down) of baseline —
  same direction as the ISS LBNP rows above (70 → 45 mm²).

### 6. Sensitivity (public data, `reports/physiology_real/sensitivity.csv`)

| Check | Result |
|---|---|
| Left and right IJV analysed separately | area slopes L −1.87 (−2.47 … −1.71) / R −2.03 (−2.66 … −1.69) ln-units per g supine; negative in every person on both sides; pressure −35 / −28 mmHg per g |
| Prone minus supine slope, within person | area −0.07 (−0.42 … +0.35), pressure +2.4 (−15 … +6) mmHg per g — no posture effect on the slope |
| Leave-one-person-out median slope (supine) | area −1.96 … −1.98, pressure −30.9 … −33.0 mmHg per g — no single person drives the result |

### 7. Where does the vein collapse? (descriptive curve fit; poorly constrained)

A 4-parameter logistic in gz_body fitted to the supine medians (public data, n = 11; bootstrap over people,
2000 resamples; files `reports/physiology_real/collapse_fit.json`, `collapse_bootstrap.csv`): plateau ≈ 189 mm² head-down,
≈ 21 mm² head-up, half-way point g50 = −0.08 g with a very steep transition (scale 0.08 g). The bootstrap
CI of g50 (−0.70 … +0.02) and of the upper plateau (111 … 360 mm²) hit the fit bounds: seven tilt levels
cannot pin the curve down. What is robust: on the **tilt analogue** almost all of the change happens
between −0.26 and +0.26 g, and at Moon-like (0.17) or Mars-like (0.38) gz_body the vein sits near its
collapsed plateau (filling 0–26 % and 0–10 % of the range). In **real partial gravity** (Lee 2020,
parabolic flight, seated) the IJV is much fuller at 0.25 G (68 mm²) and 0.5 G (34 mm²). The ground-tilt
analogue would therefore *underestimate* jugular filling on the Moon or Mars — the question the project
cares about cannot be answered from tilt data alone. This is a descriptive fit, not the project's model.

## What this means for the project

* The physiology/model layer can now be validated on **real individual data** (`real_ijv_cohort()`,
  12 people public / 24 internal) instead of the synthetic ESA-like table. For a hydrostatic model the
  inputs are `gz`, `posture_deg` (from vertical; cos = gz_body) and `family`; the current
  `experiments/physiology.py` derives the angle from the posture string only (seated → 0°, else 90°)
  and must read `posture_deg` to use tilt rows — flagged for Daniel, not changed here.
* External anchors for 0 G and partial gravity are the published means (§3–4), plotted with their CIs.
* Poster-safe figures: `reports/physiology_real/figures/ijv_area_vs_gz_body.png`,
  `ijv_pressure_vs_gz_body.png`, `prcp_hr_by_posture.png`. The LBNP figure is internal.
