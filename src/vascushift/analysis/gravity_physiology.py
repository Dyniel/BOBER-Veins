"""
First analysis of REAL physiology vs the gravity vector (ESA HREDA fallback, see docs/hreda_fallback_plan.md).

The ESA HREDA "Headward Fluid Shift" investigation has no released data, so the questions it was meant
to answer are asked of the real substitutes in the common long format:

* individual-level ground tilt (BHP-Lab, Whittle & Diaz-Artiles): gz_body from -0.71 to +1.0,
  supine and prone, IJV cross-sectional area and pressure, HR (+ IOP, BP, SV, CO internally);
* LBNP dose-response (internal only): does negative pressure on the legs reverse the headward shift?
* PhysioNet PRCP: HR / BP in supine -> 75 deg head-up tilt -> standing (10 people, beat-to-beat);
* published group means: parabolic flight (Lee 2020), ISS (Marshall-Goebel 2019), Martin 2016.

Everything here is descriptive: condition medians/IQR, within-subject slopes with bootstrap CIs over
subjects, paired contrasts. Model fitting (compartment model / PINN) stays in Daniel's code.

Licensing: ``public`` outputs use only carotid-jugular (MIT), PRCP (ODC-By) and published aggregates;
``internal`` outputs add the unlicensed tilt-dose-response and LBNP repositories and are written under
``.../internal/`` (git-ignored). carotid-jugular is the 12-person subset of tilt-dose-response (same
measurements, verified): internal tables use tilt-dose-response only, so nobody is counted twice.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Tuple

import numpy as np
import pandas as pd

FAMILY = {"supine": "supine", "supine_hut": "supine", "supine_hdt": "supine",
          "prone": "prone", "prone_hut": "prone", "prone_hdt": "prone", "seated": "seated"}
# plausibility windows: values outside are flagged; the analysis reports robust statistics on all values
# and a sensitivity variant without the flagged ones
PLAUSIBLE = {"heart_rate": (30.0, 220.0), "ijv_pressure": (0.0, 60.0), "ijv_area": (1.0, 400.0),
             "iop": (5.0, 60.0), "mean_arterial_pressure": (40.0, 160.0), "cca_area": (5.0, 150.0)}
RAW_DATASETS_PUBLIC = ("bhp_carotid_jugular", "physionet_prcp")
RAW_DATASETS_INTERNAL = ("bhp_tilt_dose_response", "bhp_lbnp_dose_response", "physionet_prcp")


def _base(variable: str) -> str:
    return variable.replace("_left", "").replace("_right", "")


def subject_level(df: pd.DataFrame, base_variable: str, datasets: Iterable[str]) -> pd.DataFrame:
    """
    One value per dataset x subject x condition for ``base_variable`` (left/right averaged when both
    sides exist), with posture family, gz_body, LBNP and a plausibility flag.
    """
    d = df[df["dataset"].isin(list(datasets)) & (df["provenance"] == "raw_individual")].copy()
    d = d[d["variable"].map(_base) == base_variable]
    if d.empty:
        return pd.DataFrame()
    keys = ["dataset", "subject_id", "condition", "posture", "tilt_deg", "gz_body", "lbnp_mmHg"]
    d["sex"] = d["sex"].fillna("?")
    out = d.groupby(keys + ["sex"], dropna=False).agg(value=("value", "mean"), n_sides=("value", "size")).reset_index()
    out["family"] = out["posture"].map(FAMILY).fillna(out["posture"])
    lo, hi = PLAUSIBLE.get(base_variable, (-np.inf, np.inf))
    out["plausible"] = out["value"].between(lo, hi)
    out["variable"] = base_variable
    return out


def condition_stats(sub: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for key, g in sub.groupby(["dataset", "family", "condition", "gz_body", "lbnp_mmHg"], dropna=False):
        v, vp = g["value"], g.loc[g["plausible"], "value"]
        rows.append({**dict(zip(["dataset", "family", "condition", "gz_body", "lbnp_mmHg"], key)),
                     "variable": g["variable"].iloc[0], "n_subjects": int(g["subject_id"].nunique()),
                     "median": float(v.median()), "q1": float(v.quantile(0.25)), "q3": float(v.quantile(0.75)),
                     "mean": float(v.mean()), "sd": float(v.std(ddof=1)) if len(v) > 1 else np.nan,
                     "n_implausible": int((~g["plausible"]).sum()),
                     "median_plausible_only": float(vp.median()) if len(vp) else np.nan})
    return pd.DataFrame(rows).sort_values(["dataset", "family", "lbnp_mmHg", "gz_body"])


def _boot_median_ci(x: np.ndarray, n_boot: int = 5000, seed: int = 0) -> Tuple[float, float]:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    meds = np.median(x[rng.integers(0, len(x), size=(n_boot, len(x)))], axis=1)
    return float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))


def tilt_slopes(sub: pd.DataFrame, log: bool, min_levels: int = 5, plausible_only: bool = False) -> pd.DataFrame:
    """
    Within-subject OLS slope of value (or ln value) on gz_body over the tilt conditions (-45..+45 deg) of
    each posture family (seated and LBNP conditions excluded). Returns one row per subject and family.
    """
    d = sub[sub["family"].isin(["supine", "prone"]) & (sub["lbnp_mmHg"].fillna(0) == 0)]
    if plausible_only:
        d = d[d["plausible"]]
    rows = []
    for (ds, fam, sid), g in d.groupby(["dataset", "family", "subject_id"]):
        g = g[g["value"] > 0] if log else g
        if g["gz_body"].nunique() < min_levels:
            continue
        y = np.log(g["value"]) if log else g["value"]
        slope, icpt = np.polyfit(g["gz_body"].astype(float), y.astype(float), 1)
        rows.append({"dataset": ds, "family": fam, "subject_id": sid, "sex": g["sex"].iloc[0],
                     "n_levels": int(g["gz_body"].nunique()), "slope": float(slope), "intercept": float(icpt)})
    return pd.DataFrame(rows)


def summarize_slopes(slopes: pd.DataFrame, log: bool) -> pd.DataFrame:
    rows = []
    for (ds, fam), g in slopes.groupby(["dataset", "family"]):
        s = g["slope"].to_numpy()
        lo, hi = _boot_median_ci(s)
        row = {"dataset": ds, "family": fam, "n_subjects": len(s), "median_slope": float(np.median(s)),
               "ci_low": lo, "ci_high": hi, "fraction_negative": float((s < 0).mean())}
        if log:  # multiplicative change of the variable for gz_body -1 -> +1 ... reported per +0.5 g
            row.update({"pct_change_per_0p5g": float((np.exp(0.5 * np.median(s)) - 1) * 100),
                        "pct_ci_low": float((np.exp(0.5 * lo) - 1) * 100), "pct_ci_high": float((np.exp(0.5 * hi) - 1) * 100)})
        rows.append(row)
    return pd.DataFrame(rows)


def lbnp_slopes(sub: pd.DataFrame) -> pd.DataFrame:
    """Within-subject slope of ln(value) per -10 mmHg LBNP, separately for supine and 15 deg HDT."""
    d = sub[sub["condition"].str.contains("lbnp", na=False)].copy()
    # series = baseline posture of the LBNP ramp ("supine" or "hdt15"); NOT the posture family, which maps
    # both to "supine" and would mix two baselines in one regression
    d["family"] = d["condition"].str.split("_lbnp").str[0]
    rows = []
    for (fam, sid), g in d.groupby(["family", "subject_id"]):
        g = g[g["value"] > 0]
        if g["lbnp_mmHg"].nunique() < 4:
            continue
        slope = np.polyfit(-g["lbnp_mmHg"].astype(float) / 10.0, np.log(g["value"].astype(float)), 1)[0]
        rows.append({"family": fam, "subject_id": sid, "slope_ln_per_10mmHg": float(slope)})
    s = pd.DataFrame(rows)
    out = []
    for fam, g in s.groupby("family"):
        lo, hi = _boot_median_ci(g["slope_ln_per_10mmHg"])
        m = float(g["slope_ln_per_10mmHg"].median())
        out.append({"family": fam, "n_subjects": len(g), "median_pct_per_10mmHg": (np.exp(m) - 1) * 100,
                    "pct_ci_low": (np.exp(lo) - 1) * 100, "pct_ci_high": (np.exp(hi) - 1) * 100,
                    "fraction_negative": float((g["slope_ln_per_10mmHg"] < 0).mean())})
    return pd.DataFrame(out)


def paired_ratio(sub: pd.DataFrame, cond_a: str, cond_b: str, dataset: str) -> Dict:
    """Per-subject ratio value(cond_a)/value(cond_b): median and bootstrap CI over subjects."""
    d = sub[sub["dataset"] == dataset].pivot_table(index="subject_id", columns="condition", values="value")
    if cond_a not in d or cond_b not in d:
        return {}
    r = (d[cond_a] / d[cond_b]).replace([np.inf, -np.inf], np.nan).dropna()
    lo, hi = _boot_median_ci(r.to_numpy())
    return {"dataset": dataset, "a": cond_a, "b": cond_b, "n_subjects": int(len(r)),
            "median_ratio": float(r.median()), "ci_low": lo, "ci_high": hi, "fraction_a_gt_b": float((r > 1).mean())}


def sensitivity(df: pd.DataFrame, slopes_subject: pd.DataFrame, tilt_dataset: str) -> pd.DataFrame:
    """Per-side slopes, prone-minus-supine slope within person, leave-one-person-out range of the median."""
    rows = []
    cj = df[(df["dataset"] == tilt_dataset) & (df["provenance"] == "raw_individual")].copy()
    for side in ("left", "right"):
        for var, log in (("ijv_area", True), ("ijv_pressure", False)):
            d = cj[cj["variable"] == f"{var}_{side}"].copy()
            if d.empty:
                continue
            d["family"] = d["posture"].map(FAMILY).fillna(d["posture"])
            d["sex"], d["plausible"] = "?", True
            sl = tilt_slopes(d, log=log)
            for fam, g in sl.groupby("family"):
                lo, hi = _boot_median_ci(g["slope"].to_numpy())
                rows.append({"analysis": "per_side", "variable": var, "side": side, "family": fam, "n": len(g),
                             "median": float(g["slope"].median()), "ci_low": lo, "ci_high": hi,
                             "fraction_negative": float((g["slope"] < 0).mean())})
    sl = slopes_subject[(slopes_subject["dataset"] == tilt_dataset) & (~slopes_subject["plausible_only"])]
    for var in ("ijv_area", "ijv_pressure"):
        piv = sl[sl["variable"] == var].pivot_table(index="subject_id", columns="family", values="slope")
        if {"prone", "supine"} <= set(piv.columns):
            diff = (piv["prone"] - piv["supine"]).dropna().to_numpy()
            lo, hi = _boot_median_ci(diff)
            rows.append({"analysis": "prone_minus_supine", "variable": var, "side": "mean", "family": "paired",
                         "n": len(diff), "median": float(np.median(diff)), "ci_low": lo, "ci_high": hi,
                         "fraction_negative": float((diff < 0).mean())})
        sup = sl[(sl["variable"] == var) & (sl["family"] == "supine")].set_index("subject_id")["slope"]
        if len(sup) > 2:
            loo = [sup.drop(k).median() for k in sup.index]
            rows.append({"analysis": "leave_one_out_median_range", "variable": var, "side": "mean", "family": "supine",
                         "n": len(sup), "median": float(sup.median()), "ci_low": float(min(loo)), "ci_high": float(max(loo)),
                         "fraction_negative": float((sup < 0).mean())})
    return pd.DataFrame(rows)


def _logistic(x, amin, amax, g50, scale):
    return amin + (amax - amin) / (1 + np.exp((x - g50) / scale))


def collapse_curve(sub: pd.DataFrame, dataset: str, family: str = "supine", n_boot: int = 2000, seed: int = 0) -> Dict:
    """
    Descriptive 4-parameter logistic of IJV area vs gz_body fitted to per-level medians, bootstrap over people.
    Seven tilt levels constrain it poorly: report the CIs, and the filling fraction at chosen gz_body values.
    """
    from scipy.optimize import curve_fit

    d = sub[(sub["dataset"] == dataset) & (sub["variable"] == "ijv_area") & (sub["family"] == family)]
    piv = d.pivot_table(index="subject_id", columns="gz_body", values="value")
    if piv.shape[1] < 5:
        return {}
    g = piv.columns.to_numpy(float)
    lb, ub = [0, 20, -0.7, 0.02], [60, 400, 0.7, 0.6]

    def fit(med):
        p, _ = curve_fit(_logistic, g, med, p0=[med.min(), med.max(), 0.0, 0.15], bounds=(lb, ub), maxfev=20000)
        return p

    p = fit(piv.median().to_numpy())
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        m = piv.iloc[rng.integers(0, len(piv), len(piv))].median().to_numpy()
        if np.isnan(m).any():
            continue
        try:
            boots.append(fit(m))
        except (RuntimeError, ValueError):
            continue
    B = np.array(boots)
    names = ["amin", "amax", "g50", "scale"]
    out = {"dataset": dataset, "family": family, "n_people": int(len(piv)), "levels": g.round(3).tolist(),
           "fit": dict(zip(names, np.round(p, 3).tolist())),
           "ci95": {k: np.percentile(B[:, i], [2.5, 97.5]).round(3).tolist() for i, k in enumerate(names)},
           "ci_hits_bounds": bool(np.any(np.isclose(B, lb, atol=1e-3)) or np.any(np.isclose(B, ub, atol=1e-3))),
           "filling_fraction": {}}
    for label, gz in (("moon_like_0.165", 0.165), ("mars_like_0.38", 0.38)):
        fr = [(_logistic(gz, *b) - b[0]) / (b[1] - b[0]) for b in B]
        out["filling_fraction"][label] = {"point": round(float((_logistic(gz, *p) - p[0]) / (p[1] - p[0])), 3),
                                          "ci95": np.percentile(fr, [2.5, 97.5]).round(3).tolist()}
    out["bootstrap"] = B
    return out


def literature_anchors(df: pd.DataFrame, base_variables=("ijv_area", "ijv_pressure", "heart_rate")) -> pd.DataFrame:
    d = df[df["provenance"] == "published_aggregate"].copy()
    d["base"] = d["variable"].map(_base)
    d = d[d["base"].isin(base_variables)]
    return d[["dataset", "condition", "environment", "posture", "gz_platform", "gz_body", "lbnp_mmHg", "variable",
              "base", "stat", "value", "ci_low", "ci_high", "sd", "n", "source", "notes"]]


def _analyse(df: pd.DataFrame, raw_datasets: Tuple[str, ...]) -> Dict[str, pd.DataFrame]:
    out = {}
    subs = {v: subject_level(df, v, raw_datasets) for v in ("ijv_area", "ijv_pressure", "heart_rate", "iop",
                                                             "mean_arterial_pressure")}
    subs = {k: v for k, v in subs.items() if not v.empty}
    out["subject_level"] = pd.concat(subs.values(), ignore_index=True)
    out["condition_stats"] = pd.concat([condition_stats(v) for v in subs.values()], ignore_index=True)
    slope_rows, slope_summ = [], []
    for v, sub in subs.items():
        log = v == "ijv_area"
        for plaus in (False, True):
            s = tilt_slopes(sub, log=log, plausible_only=plaus)
            if s.empty:
                continue
            s["variable"], s["scale"], s["plausible_only"] = v, "ln" if log else "linear", plaus
            slope_rows.append(s)
            ss = summarize_slopes(s, log)
            ss["variable"], ss["scale"], ss["plausible_only"] = v, "ln" if log else "linear", plaus
            slope_summ.append(ss)
    out["tilt_slopes_subject"] = pd.concat(slope_rows, ignore_index=True) if slope_rows else pd.DataFrame()
    out["tilt_slopes_summary"] = pd.concat(slope_summ, ignore_index=True) if slope_summ else pd.DataFrame()
    pairs = []
    for v, sub in subs.items():
        for ds in sub["dataset"].unique():
            for a, b in (("supine_tilt_-45", "supine_tilt_+45"), ("supine_tilt_+0", "seated_baseline"),
                         ("prone_tilt_-45", "prone_tilt_+45"), ("supine_tilt_+0", "prone_tilt_+0"),
                         ("hut75", "supine"), ("standing", "supine"),
                         ("supine_lbnp_-50", "supine_lbnp_+0"), ("hdt15_lbnp_-50", "hdt15_lbnp_+0")):
                r = paired_ratio(sub, a, b, ds)
                if r:
                    pairs.append({"variable": v, **r})
    out["paired_ratios"] = pd.DataFrame(pairs)
    if "ijv_area" in subs and subs["ijv_area"]["condition"].str.contains("lbnp").any():
        out["lbnp_slopes"] = lbnp_slopes(subs["ijv_area"])
    out["literature_anchors"] = literature_anchors(df)
    tilt_ds = next((d for d in ("bhp_tilt_dose_response", "bhp_carotid_jugular") if d in raw_datasets), None)
    if tilt_ds and not out["tilt_slopes_subject"].empty:
        out["sensitivity"] = sensitivity(df, out["tilt_slopes_subject"], tilt_ds)
    if tilt_ds and "ijv_area" in subs:
        cc = collapse_curve(subs["ijv_area"], tilt_ds)
        if cc:
            out["collapse_bootstrap"] = pd.DataFrame(cc.pop("bootstrap"), columns=["amin", "amax", "g50", "scale"])
            out["_collapse_fit"] = cc
    return out


def run_gravity_physiology_analysis(data_dir: Path = Path("data"),
                                    out_dir: Path = Path("reports/physiology_real"),
                                    internal: bool = True, verbose: bool = True) -> Dict:
    from vascushift.data.schema import load_all_physiology

    data_dir, out_dir = Path(data_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {}
    variants = [("public", out_dir, False, RAW_DATASETS_PUBLIC)]
    if internal:
        variants.append(("internal", out_dir / "internal", True, RAW_DATASETS_INTERNAL))
    for name, odir, unlicensed, raw in variants:
        odir.mkdir(parents=True, exist_ok=True)
        df = load_all_physiology(data_dir, include_unlicensed=unlicensed)
        tables = _analyse(df, raw)
        cfit = tables.pop("_collapse_fit", None)
        if cfit:
            (odir / "collapse_fit.json").write_text(json.dumps(cfit, indent=2))
        for k, t in tables.items():
            t.to_csv(odir / f"{k}.csv", index=False)
        summ = tables["tilt_slopes_summary"]
        result[name] = {
            "datasets_raw": list(raw),
            "n_subjects": {ds: int(g["subject_id"].nunique()) for ds, g in tables["subject_level"].groupby("dataset")},
            "tilt_slopes": summ.to_dict(orient="records"),
            "paired_ratios": tables["paired_ratios"].to_dict(orient="records"),
            "lbnp": tables.get("lbnp_slopes", pd.DataFrame()).to_dict(orient="records"),
            "n_implausible_values": int((~tables["subject_level"]["plausible"]).sum()),
        }
        (odir / "summary.json").write_text(json.dumps(result[name], indent=2, default=float))
        if verbose:
            print(f"[physiology:{name}] subjects {result[name]['n_subjects']}, "
                  f"implausible values flagged {result[name]['n_implausible_values']} -> {odir}")
    return result
