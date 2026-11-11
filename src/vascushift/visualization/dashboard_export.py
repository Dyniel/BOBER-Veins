"""
Exports pipeline outputs for the static dashboard in demo/.

Two bundles, each written as JSON (for tools) and as a tiny JS file assigning a global (so the dashboard
also works when index.html is opened directly from disk, where fetch() of local files is blocked):

* ``demo/data/public/``  dashboard_data.json / .js  -> ``window.VASCU_PUBLIC``
  metrics and condition statistics derived from licensed sources only (UBFC-rPPG metrics, BHP
  carotid-jugular MIT, PhysioNet PRCP ODC-By, published tables) + the model sweep (labelled model).
* ``demo/data/local/``   dashboard_local.json / .js  -> ``window.VASCU_LOCAL``   (git-ignored)
  waveform excerpts (UBFC dataset agreement: no redistribution) and the internal BHP data (no licence).

Every block carries ``provenance``: "raw_individual" / "published_aggregate" / "model" / "synthetic".
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd


def _records(df: pd.DataFrame, cols=None, ndigits: int = 3):
    d = df[cols] if cols else df
    out = []
    for r in d.to_dict(orient="records"):
        rr = {}
        for k, v in r.items():
            if isinstance(v, (float, np.floating)):
                rr[k] = None if (v is None or math.isnan(v)) else round(float(v), ndigits)
            elif isinstance(v, (np.integer,)):
                rr[k] = int(v)
            elif isinstance(v, (np.bool_,)):
                rr[k] = bool(v)
            else:
                rr[k] = v
        out.append(rr)
    return out


def _datasets_block() -> list:
    from vascushift.data.registry import DATASETS

    rows = []
    for key, d in DATASETS.items():
        rows.append({"key": key, "name": d.get("name", key), "layer": d.get("layer"), "status": d.get("status"),
                     "subjects": d.get("subjects"), "license": d.get("license"), "access": d.get("access"),
                     "url": d.get("url"), "doi": d.get("doi")})
    return rows


def _model_sweep() -> Dict:
    """Daniel's forward simulator with its DEFAULT parameters, swept over gz_body (labelled as a model)."""
    try:
        from vascushift.physics.simulator import VenousHemodynamicSimulator
    except Exception as exc:  # model code not importable -> dashboard hides the overlay
        return {"available": False, "error": repr(exc)}
    sim = VenousHemodynamicSimulator()
    rows = []
    for gzb in np.round(np.linspace(-0.75, 1.0, 36), 3):
        post = float(np.degrees(np.arccos(np.clip(gzb, -1, 1))))  # cos(posture_deg) = gz_body at gz = 1
        r = sim.simulate_gravity_sweep(gravity_levels=[1.0], posture_deg=post).iloc[0]
        rows.append({"gz_body": float(gzb), "ijv_area": float(r["IJV_area_mm2"]),
                     "ijv_pressure": float(r["IJV_pressure_mmHg"])})
    seated = sim.simulate_gravity_sweep(gravity_levels=[0.0, 0.25, 0.5, 0.75, 1.0], posture_deg=0.0)
    return {"available": True, "provenance": "model",
            "label": "Compartment model, default parameters (NOT fitted to these data)",
            "tilt_equivalent": rows,
            "seated_partial_gravity": _records(seated.rename(columns={"IJV_area_mm2": "ijv_area",
                                                                       "IJV_pressure_mmHg": "ijv_pressure"}))}


def export_dashboard_data(data_dir: Path = Path("data"), reports_dir: Path = Path("reports"),
                          demo_dir: Path = Path("demo"), waveform_seconds: float = 8.0,
                          pipeline_info: Dict = None) -> Dict:
    data_dir, reports_dir, demo_dir = Path(data_dir), Path(reports_dir), Path(demo_dir)
    pub_dir, loc_dir = demo_dir / "data" / "public", demo_dir / "data" / "local"
    pub_dir.mkdir(parents=True, exist_ok=True)
    loc_dir.mkdir(parents=True, exist_ok=True)

    rb = reports_dir / "rppg_baseline"
    summary = pd.read_csv(rb / "summary.csv")
    windows = pd.read_csv(rb / "windows.csv")
    index = pd.read_csv(data_dir / "processed" / "rppg" / "sessions.csv")
    whole = windows[windows.protocol == "whole"].pivot_table(index="session_id", columns="method", values="error_bpm")
    imp_path = reports_dir / "rppg_improved" / "windows.csv"
    imp = pd.read_csv(imp_path) if imp_path.exists() else None
    sessions = []
    for _, s in index.iterrows():
        w = windows[(windows.session_id == s.session_id) & (windows.protocol == "w10s2")]
        series = {}
        for m, g in w.groupby("method"):
            g = g.sort_values("t_start_s")
            series[m] = {"t_mid_s": (g.t_start_s + 5.0).round(1).tolist(), "hr_est": g.hr_est_bpm.round(2).tolist(),
                         "included": g.included.astype(bool).tolist()}
        ref = w[w.method == "pos"].sort_values("t_start_s")
        sessions.append({
            "session_id": s.session_id, "subset": s.subset, "duration_s": float(s.duration_s),
            "fps_video_mean": float(s.fps_video_mean), "fraction_valid": float(s.fraction_valid),
            "max_frame_step_s": float(s.max_frame_step_s), "ref_hr_bpm": float(s.ref_hr_bpm),
            "no_face_display": bool(s.no_face_display),
            "whole_error_bpm": {m: (None if pd.isna(v) else round(float(v), 2)) for m, v in whole.loc[s.session_id].items()}
            if s.session_id in whole.index else {},
            "w10s2": {"t_mid_s": (ref.t_start_s + 5.0).round(1).tolist(), "hr_ref": ref.hr_ref_bpm.round(2).tolist(),
                      **{f"hr_{m}": v["hr_est"] for m, v in series.items()},
                      "included": ref.included.astype(bool).tolist()},
        })
        if imp is not None:
            g = imp[imp.session_id == s.session_id].sort_values("t_start_s")
            sessions[-1]["w10s2_improved"] = {"t_mid_s": (g.t_start_s + 5.0).round(1).tolist(),
                                              "hr": g.hr_est_bpm.round(2).tolist(),
                                              "abstain": g.abstain.astype(bool).tolist(),
                                              "included": g.included.astype(bool).tolist()}

    pr = reports_dir / "physiology_real"
    cs = pd.read_csv(pr / "condition_stats.csv")
    an = pd.read_csv(pr / "literature_anchors.csv")
    slopes = pd.read_csv(pr / "tilt_slopes_summary.csv")
    ratios = pd.read_csv(pr / "paired_ratios.csv")
    subj = pd.read_csv(pr / "subject_level.csv")
    prcp = subj[(subj.dataset == "physionet_prcp")]

    from vascushift.pipeline import _git_commit

    public = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "git_commit": _git_commit(),
        "rule": "Real data only, except the block 'model' (labelled). No dataset links face video to venous "
                "ground truth: the optical and physiology layers are validated separately.",
        "datasets": _datasets_block(),
        "rppg": {"provenance": "raw_individual", "dataset": "UBFC-rPPG (Bobbia et al. 2019)",
                 "summary": _records(summary), "sessions": sessions,
                 "protocol": "Whole-session Green/CHROM/POS on a 30 Hz frame-clock grid; HR = Welch peak 42–210 bpm; "
                             "reference = finger PPG with the same estimator; windows <90 % valid excluded."},
        "physiology": {
            "condition_stats": _records(cs[cs.variable.isin(["ijv_area", "ijv_pressure", "heart_rate"])]),
            "literature_anchors": _records(an.drop(columns=["notes"], errors="ignore")),
            "tilt_slopes": _records(slopes), "paired_ratios": _records(ratios),
            "prcp_subjects": _records(prcp[["subject_id", "condition", "variable", "value"]]),
            "sources": {"bhp_carotid_jugular": "Whittle & Diaz-Artiles, J Appl Physiol 2023 (MIT)",
                        "physionet_prcp": "PhysioNet PRCP (ODC-By)",
                        "lee2020_partial_gravity": "Lee et al., Front Physiol 2020",
                        "marshall_goebel2019_iss_ijv": "Marshall-Goebel et al., JAMA Netw Open 2019",
                        "martin2016_parabolic_ijvp": "Martin et al. 2016"},
        },
        "model": _model_sweep(),
        "quality": _quality_block(index, summary, pr),
        "rppg_improved": _improved_block(reports_dir / "rppg_improved"),
        "pipeline": pipeline_info or {},
    }
    _write_bundle(pub_dir, "dashboard_data", "VASCU_PUBLIC", public)

    # ------------------------------------------------------------------ local-only bundle (git-ignored)
    local = {"generated_utc": public["generated_utc"], "waveforms": {}, "physiology_internal": None,
             "note": "LOCAL ONLY: UBFC waveforms (dataset agreement) and unlicensed BHP data. Never commit or publish."}
    try:
        from vascushift.data.preprocess import load_optical_session
        from vascushift.optical.algorithms import rppg_chrom, rppg_green, rppg_pos
        from vascushift.optical.benchmark import reference_pulse

        for _, s in index.iterrows():
            d = load_optical_session(data_dir / "processed" / "rppg" / s.file)
            fs = d["fs"]
            n = int(waveform_seconds * fs)
            a = max(0, len(d["time"]) // 2 - n // 2)  # excerpt from the middle of the recording
            sl = slice(a, a + n)
            ref = reference_pulse(d["ref_bvp"], fs)

            def z(x, sl=sl):
                x = np.asarray(x, float)[sl]
                return np.round((x - x.mean()) / (x.std() + 1e-9), 3).tolist()

            local["waveforms"][s.session_id] = {
                "t0_s": round(a / fs, 2), "fs": fs, "ref": z(ref), "pos": z(rppg_pos(d["rgb_traces"], fs)),
                "chrom": z(rppg_chrom(d["rgb_traces"], fs)), "green": z(rppg_green(d["rgb_traces"], fs)),
                "valid": d["valid"][sl].astype(bool).tolist()}
    except Exception as exc:
        local["waveforms_error"] = repr(exc)
    internal = pr / "internal"
    if (internal / "condition_stats.csv").exists():
        csi = pd.read_csv(internal / "condition_stats.csv")
        local["physiology_internal"] = {
            "provenance": "raw_individual", "license": "none - team use only",
            "condition_stats": _records(csi),
            "tilt_slopes": _records(pd.read_csv(internal / "tilt_slopes_summary.csv")),
            "lbnp_slopes": _records(pd.read_csv(internal / "lbnp_slopes.csv")) if (internal / "lbnp_slopes.csv").exists() else []}
    _write_bundle(loc_dir, "dashboard_local", "VASCU_LOCAL", local)
    return {"public": str(pub_dir / "dashboard_data.js"), "local": str(loc_dir / "dashboard_local.js"),
            "n_sessions": len(sessions), "n_waveforms": len(local["waveforms"])}


def _quality_block(index: pd.DataFrame, summary: pd.DataFrame, phys_dir: Path) -> Dict:
    """Known data problems, surfaced instead of hidden (all numbers computed, nothing hand-typed)."""
    d2 = index[index.subset == "DATASET_2"]
    excl = summary[summary.method == "pos"].groupby(["subset", "protocol"])["n_excluded"].first().reset_index()
    phys = json.loads((phys_dir / "summary.json").read_text()) if (phys_dir / "summary.json").exists() else {}
    cs = pd.read_csv(phys_dir / "condition_stats.csv") if (phys_dir / "condition_stats.csv").exists() else pd.DataFrame()
    flagged = cs[cs.n_implausible > 0][["variable", "condition", "n_implausible", "n_subjects"]] if len(cs) else pd.DataFrame()
    return {
        "ubfc": {
            "n_sessions": int(len(index)),
            "fps_min": round(float(d2.fps_video_mean.min()), 2) if len(d2) else None,
            "fps_max": round(float(d2.fps_video_mean.max()), 2) if len(d2) else None,
            "sessions_with_frame_holes_over_0p25s": int((index.max_frame_step_s > 0.25).sum()),
            "longest_frame_hole_s": round(float(index.max_frame_step_s.max()), 3),
            "sessions_with_sensor_hr_dropouts": int((index.hr_sensor_dropouts > 0).sum()),
            "no_face_display_sessions": index.loc[index.no_face_display, "session_id"].tolist(),
            "excluded_windows": _records(excl),
        },
        "physiology": {
            "n_implausible_values": phys.get("n_implausible_values"),
            "flagged_conditions": _records(flagged) if len(flagged) else [],
            "notes": ["carotid-jugular (MIT, 12 people) is a subset of tilt-dose-response (24): never pooled",
                      "IJV pressure by compression sonography: values > 60 mmHg flagged, robust statistics used",
                      _seated_note(cs)],
        },
    }


def _improved_block(d: Path) -> Dict:
    f = d / "summary.json"
    if not f.exists():
        return {"available": False}
    r = json.loads(f.read_text())
    return {"available": True, "status": r.get("status"), "config": r.get("config"),
            "abstain_quality_threshold": r.get("abstain_quality_threshold"), "summary": r.get("summary"),
            "baseline_pos_summary": r.get("baseline_pos_summary"),
            "provenance": "raw_individual"}


def _seated_note(cs: pd.DataFrame) -> str:
    if cs.empty:
        return ""
    a = cs[(cs.dataset == "bhp_carotid_jugular") & (cs.variable == "ijv_area")]
    seated = a[a.family == "seated"]["n_subjects"]
    tilt = a[a.family == "supine"]["n_subjects"]
    if seated.empty or tilt.empty:
        return ""
    return (f"seated IJV area is present for only {int(seated.iloc[0])} of {int(tilt.max())} people in the public file "
            "(the seated point has wide uncertainty)")


def _write_bundle(out_dir: Path, stem: str, global_name: str, payload: Dict) -> None:
    txt = json.dumps(payload, separators=(",", ":"), default=str, allow_nan=False)
    (out_dir / f"{stem}.json").write_text(txt)
    (out_dir / f"{stem}.js").write_text(f"window.{global_name} = {txt};\n")
