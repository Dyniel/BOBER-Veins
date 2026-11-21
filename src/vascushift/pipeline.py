"""
One-command real-data pipeline: raw data -> common formats -> baselines/analyses -> figures -> dashboard data.

    python -m vascushift.cli pipeline                 # all stages, offline audit
    python -m vascushift.cli pipeline --online        # + live ESA HREDA status query
    python -m vascushift.cli pipeline --stages rppg figures

Stages (each idempotent; the expensive video decoding is cached in data/interim/ubfc_rgb):

    check        raw inputs present? (prints what to download, never downloads by itself)
    audit        dataset registry + local files (+ HREDA TAP if --online)      -> reports/data_audit/
    preprocess   UBFC -> 30 Hz sessions, physiology long tables, real cohorts  -> data/processed/
    rppg         windowed Green/CHROM/POS benchmark (frozen baseline)          -> reports/rppg_baseline/
    rppg_improved  EXPERIMENTAL best variant (ROI interp + POS + Viterbi + abstain), skipped without
                 the ROI cache of scripts/run_roi_variants.py                  -> reports/rppg_improved/
    physiology   IJV / IJVP / HR / IOP vs gravity vector, LBNP                 -> reports/physiology_real/
    figures      static PNGs of the two layers                                 -> reports/*/figures/
    dashboard    JSON for demo/ (public + local-only)                          -> demo/data/
    manifest     what ran, versions, input/output checksums                    -> reports/pipeline_manifest.json

The pipeline never generates synthetic data. Synthetic benchmarks stay in Daniel's experiment code
and are labelled there.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

STAGES = ["check", "audit", "preprocess", "rppg", "rppg_improved", "physiology", "figures", "dashboard", "manifest"]


@dataclass
class PipelineContext:
    data_dir: Path = Path("data")
    reports_dir: Path = Path("reports")
    demo_dir: Path = Path("demo")
    online: bool = False
    force: bool = False
    verbose: bool = True
    results: Dict[str, Dict] = field(default_factory=dict)


def _sha256(path: Path, limit_mb: int = 64) -> Optional[str]:
    p = Path(path)
    if not p.is_file() or p.stat().st_size > limit_mb * 2 ** 20:
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stage_check(ctx: PipelineContext) -> Dict:
    raw = ctx.data_dir / "raw"
    need = {
        "ubfc_rppg_videos": (raw / "rppg" / "UBFC-rPPG", "python scripts/download_data.py --dataset ubfc"),
        "physionet": (raw / "physionet" / "prcp", "python scripts/download_data.py --dataset physionet"),
        "bhp_github": (raw / "github" / "carotid-jugular-characteristics", "python scripts/download_data.py --dataset github"),
    }
    status = {}
    for k, (p, cmd) in need.items():
        ok = p.exists() and (k != "ubfc_rppg_videos" or any(p.glob("DATASET_*/*/vid.avi")))
        status[k] = {"present": ok, "path": str(p), "how_to_get": None if ok else cmd}
        if ctx.verbose and not ok:
            print(f"  [check] MISSING {k}: {p}  ->  {cmd}")
    return status


def stage_audit(ctx: PipelineContext) -> Dict:
    from vascushift.data.audit import run_data_audit

    s = run_data_audit(data_dir=ctx.data_dir, out_dir=ctx.reports_dir / "data_audit", online=ctx.online)
    live = s.get("hreda_live") if isinstance(s, dict) else None
    hfs = None
    if isinstance(live, list):
        hfs = next((r for r in live if r.get("investigation_unique_acronym") == "HeadwardFluidShift_PARA"), None)
        if hfs and (hfs.get("data_available") or hfs.get("n_files")) and ctx.verbose:
            print("  [audit] !!! ESA HREDA HeadwardFluidShift now lists data - see docs/hreda_fallback_plan.md §3.4")
    return {"out": str(ctx.reports_dir / "data_audit"), "online": ctx.online,
            "hreda_headward_fluid_shift": None if hfs is None else
            {k: hfs.get(k) for k in ("data_available", "n_files", "last_update_date")},
            "hreda_error": live.get("error") if isinstance(live, dict) else None}


def stage_preprocess(ctx: PipelineContext) -> Dict:
    from vascushift.data.cohorts import export_real_cohorts
    from vascushift.data.preprocess import preprocess_physiology, preprocess_ubfc

    idx = preprocess_ubfc(data_dir=ctx.data_dir, force=ctx.force, verbose=ctx.verbose)
    phys = preprocess_physiology(data_dir=ctx.data_dir)
    cohorts = export_real_cohorts(ctx.data_dir)
    return {"ubfc_sessions": int(len(idx)), "physiology": {k: str(v) for k, v in phys.items()},
            "cohorts": {k: str(v) for k, v in cohorts.items()}}


def stage_rppg(ctx: PipelineContext) -> Dict:
    from vascushift.optical.benchmark import run_rppg_baseline

    r = run_rppg_baseline(processed_dir=ctx.data_dir / "processed" / "rppg",
                          out_dir=ctx.reports_dir / "rppg_baseline", verbose=False)
    pos = [s for s in r["summary"] if s["method"] == "pos" and s["protocol"] == "w10s2"]
    return {"n_sessions": r["data"]["n_sessions"], "pos_w10s2": pos}


def stage_rppg_improved(ctx: PipelineContext) -> Dict:
    from vascushift.optical.improved import run_rppg_improved

    r = run_rppg_improved(data_dir=ctx.data_dir, out_dir=ctx.reports_dir / "rppg_improved", verbose=False)
    if not r.get("available"):
        if ctx.verbose:
            print(f"  [rppg_improved] skipped: {r.get('reason')}")
        return {"available": False}
    hold = next((g for g in r["summary"] if g["group"] == "split=holdout"), None)
    return {"available": True, "holdout": hold}


def stage_physiology(ctx: PipelineContext) -> Dict:
    from vascushift.analysis.gravity_physiology import run_gravity_physiology_analysis

    r = run_gravity_physiology_analysis(data_dir=ctx.data_dir, out_dir=ctx.reports_dir / "physiology_real",
                                        internal=True, verbose=ctx.verbose)
    return {"public_subjects": r["public"]["n_subjects"], "internal_subjects": r.get("internal", {}).get("n_subjects")}


def stage_figures(ctx: PipelineContext) -> Dict:
    from vascushift.visualization.data_figures import make_physiology_figures, make_rppg_figures

    out = {**make_rppg_figures(ctx.reports_dir / "rppg_baseline"),
           **make_physiology_figures(ctx.reports_dir / "physiology_real")}
    return {k: str(v) for k, v in out.items()}


def stage_dashboard(ctx: PipelineContext) -> Dict:
    from vascushift.visualization.dashboard_export import export_dashboard_data

    prev = {}
    mpath = ctx.reports_dir / "pipeline_manifest.json"
    if mpath.exists():  # stages not run in this invocation keep their last recorded timing
        try:
            prev = {k: v.get("seconds") for k, v in json.loads(mpath.read_text()).get("stages", {}).items()}
        except (ValueError, AttributeError):
            prev = {}
    info = {"stages_seconds": {**prev, **{k: v.get("seconds") for k, v in ctx.results.items()}},
            "git_commit": _git_commit(), "git_dirty": _git_dirty(),
            "command": "python -m vascushift.cli pipeline" + (" --online" if ctx.online else ""),
            "hreda_headward_fluid_shift": ctx.results.get("audit", {}).get("hreda_headward_fluid_shift")}
    return export_dashboard_data(data_dir=ctx.data_dir, reports_dir=ctx.reports_dir, demo_dir=ctx.demo_dir,
                                 pipeline_info=info)


def _git_commit() -> Optional[str]:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None


def _git_dirty() -> Optional[bool]:
    try:
        out = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True).stdout
        return bool(out.strip())
    except Exception:
        return None


def stage_manifest(ctx: PipelineContext) -> Dict:
    import numpy
    import pandas
    import scipy

    outputs = []
    for base in (ctx.reports_dir / "rppg_baseline", ctx.reports_dir / "rppg_improved", ctx.reports_dir / "physiology_real",
                 ctx.reports_dir / "data_audit",
                 ctx.data_dir / "processed", ctx.demo_dir / "data"):
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file() and "/sessions/" not in str(p) and p.suffix in (".csv", ".json", ".md", ".png"):
                outputs.append({"path": str(p), "bytes": p.stat().st_size, "sha256": _sha256(p),
                                "internal": "internal" in p.parts or "local" in p.parts})
    inputs = []
    for m in sorted((ctx.data_dir / "raw").rglob("_download_manifest.json")) if (ctx.data_dir / "raw").exists() else []:
        inputs.append({"manifest": str(m), "sha256": _sha256(m)})
    manifest = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": _git_commit(), "git_dirty": _git_dirty(),
        "python": sys.version.split()[0], "platform": platform.platform(),
        "packages": {"numpy": numpy.__version__, "pandas": pandas.__version__, "scipy": scipy.__version__},
        "stages": {k: v for k, v in ctx.results.items() if k != "manifest"},
        "input_manifests": inputs, "outputs": outputs,
        "rule": "real data only; synthetic data never produced by this pipeline",
    }
    path = ctx.reports_dir / "pipeline_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, default=str))
    return {"path": str(path), "n_outputs": len(outputs)}


STAGE_FUNCS: Dict[str, Callable[[PipelineContext], Dict]] = {
    "check": stage_check, "audit": stage_audit, "preprocess": stage_preprocess, "rppg": stage_rppg,
    "rppg_improved": stage_rppg_improved,
    "physiology": stage_physiology, "figures": stage_figures, "dashboard": stage_dashboard, "manifest": stage_manifest,
}


def run_pipeline(stages: Optional[List[str]] = None, ctx: Optional[PipelineContext] = None) -> PipelineContext:
    ctx = ctx or PipelineContext()
    todo = stages or STAGES
    unknown = set(todo) - set(STAGES)
    if unknown:
        raise ValueError(f"unknown stages {unknown}; valid: {STAGES}")
    for name in [s for s in STAGES if s in todo]:  # always canonical order
        t0 = time.time()
        if ctx.verbose:
            print(f"[pipeline] {name} ...", flush=True)
        res = STAGE_FUNCS[name](ctx)
        res = res if isinstance(res, dict) else {"result": res}
        res["seconds"] = round(time.time() - t0, 2)
        ctx.results[name] = res
        if ctx.verbose:
            print(f"[pipeline] {name} done in {res['seconds']} s", flush=True)
    return ctx
