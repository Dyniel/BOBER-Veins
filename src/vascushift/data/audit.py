"""
Data audit: what do we really have locally, with which variables / ground truth,
and what is its provenance. Used by ``python -m vascushift.cli data-audit``.

Outputs (``reports/data_audit/``):
    audit_summary.json        - registry + local status + live HREDA status
    ubfc_inventory.csv        - one row per UBFC-rPPG session (GT quality, video format)
    prcp_conditions.csv       - PRCP steady-state HR/BP per subject and posture (real, individual)
    ijv_area_vs_gravity.csv   - IJV area by dataset / posture / gz_body / LBNP, licensed real sources only
    internal/                 - same incl. unlicensed BHP-Lab repos (git-ignored, team use only)
    literature_aggregates.csv - copy of the transcribed published group values
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Dict

import pandas as pd

from vascushift.data.registry import DATASETS, GITHUB_DATA_REPOS, PHYSIONET_PROJECTS


def _dir_size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file()) if path.exists() else 0


def local_status(data_dir: Path) -> Dict[str, Dict]:
    """Presence, size and manifest of every downloadable dataset under data/raw."""
    data_dir = Path(data_dir)
    out: Dict[str, Dict] = {}
    for slug, version in PHYSIONET_PROJECTS:
        d = data_dir / "raw" / "physionet" / slug / version
        m = d / "_download_manifest.json"
        man = json.loads(m.read_text()) if m.exists() else {}
        out[f"physionet_{slug.replace('-', '_')}"] = {
            "path": str(d), "present": d.exists(), "bytes": _dir_size(d),
            "manifest_files": man.get("n_files"), "checksum_verified": man.get("checksum_verified"),
            "retrieved_utc": man.get("retrieved_utc"),
        }
    for _owner, repo in GITHUB_DATA_REPOS:
        d = data_dir / "raw" / "github" / repo
        m = d / "_download_manifest.json"
        man = json.loads(m.read_text()) if m.exists() else {}
        out[f"github_{repo}"] = {
            "path": str(d), "present": d.exists(), "bytes": _dir_size(d),
            "commit": (man.get("commit") or "")[:12], "license": man.get("license"),
            "retrieved_utc": man.get("retrieved_utc"),
        }
    u = data_dir / "raw" / "rppg" / "UBFC-rPPG"
    m = u / "_download_manifest.json"
    man = json.loads(m.read_text()) if m.exists() else {}
    vids = list(u.glob("DATASET_*/*/vid.avi"))
    out["ubfc_rppg"] = {
        "path": str(u), "present": u.exists(), "bytes": _dir_size(u),
        "videos_complete": len(vids), "videos_expected": 50,
        "partial_downloads": len(list(u.rglob("*.part"))),
        "manifest_files": man.get("n_files"), "retrieved_utc": man.get("retrieved_utc"),
    }
    esa = data_dir / "raw" / "esa"
    out["esa_raw_files"] = {"path": str(esa), "present": esa.exists(),
                            "files": sorted(p.name for p in esa.glob("*")) if esa.exists() else []}
    return out


def run_data_audit(data_dir: Path = Path("data"), out_dir: Path = Path("reports/data_audit"),
                   online: bool = True) -> Dict:
    data_dir, out_dir = Path(data_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary: Dict = {
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "registry": DATASETS,
        "local": local_status(data_dir),
    }

    if online:
        try:
            from vascushift.data.hreda import investigation_status

            summary["hreda_live"] = investigation_status()
        except Exception as exc:  # offline / service down
            summary["hreda_live"] = {"error": repr(exc)}

    from vascushift.data.literature import export_literature_aggregates

    summary["literature_csv"] = str(export_literature_aggregates(out_dir / "literature_aggregates.csv"))

    ubfc_root = data_dir / "raw" / "rppg" / "UBFC-rPPG"
    if ubfc_root.exists():
        from vascushift.data.ubfc import ubfc_inventory

        inv = ubfc_inventory(ubfc_root)
        inv.to_csv(out_dir / "ubfc_inventory.csv", index=False)
        summary["ubfc"] = {
            "sessions_with_gt": int(len(inv)),
            "sessions_with_video": int(inv["video_present"].sum()),
            "gt_with_duplicate_timestamps": int((inv["gt_duplicate_t"] > 0).sum()),
            "gt_with_gap_over_0p5s": int((inv["gt_max_gap_s"] > 0.5).sum()),
            "sessions_with_sensor_hr_dropouts": inv.loc[inv["hr_sensor_dropouts"] > 0, "session_id"].tolist(),
            "no_face_display": inv.loc[inv["no_face_display"], "session_id"].tolist(),
        }

    prcp_root = data_dir / "raw" / "physionet" / "prcp" / "1.0.0"
    if prcp_root.exists():
        from vascushift.data.physionet_posture import prcp_condition_summary

        pc = prcp_condition_summary(prcp_root)
        pc.to_csv(out_dir / "prcp_conditions.csv", index=False)
        piv = pc.pivot_table(index="condition", columns="variable", values="value", aggfunc="mean").round(1)
        summary["prcp"] = {"subjects": int(pc["subject_id"].nunique()),
                           "group_means_by_condition": piv.to_dict(orient="index")}

    from vascushift.data.schema import load_all_physiology

    def _ijv_table(df: pd.DataFrame) -> pd.DataFrame:
        ijv = df[df["variable"].str.startswith("ijv_area")]
        return (ijv.groupby(["dataset", "provenance", "variable", "condition", "environment", "posture", "gz_platform", "gz_body",
                             "lbnp_mmHg"], dropna=False)["value"]
                .agg(n_rows="count", mean="mean", median="median").reset_index().round(2))

    # publication-safe (licensed sources only) -> committed; full table -> internal/ (git-ignored)
    _ijv_table(load_all_physiology(data_dir, include_unlicensed=False)).to_csv(
        out_dir / "ijv_area_vs_gravity.csv", index=False)
    phys = load_all_physiology(data_dir, include_unlicensed=True)
    (out_dir / "internal").mkdir(exist_ok=True)
    _ijv_table(phys).to_csv(out_dir / "internal" / "ijv_area_vs_gravity_incl_unlicensed.csv", index=False)
    summary["physiology_long"] = {
        "rows": int(len(phys)),
        "by_dataset": phys.groupby("dataset")["subject_id"].nunique().to_dict(),
        "variables": sorted(phys["variable"].unique().tolist()),
    }

    (out_dir / "audit_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    return summary


def format_audit(summary: Dict) -> str:
    lines = ["=== VascuShift DATA AUDIT ===", f"generated: {summary['generated_utc']}", ""]
    lines.append(f"{'dataset':38s} {'layer':11s} {'status':17s} access")
    for k, v in summary["registry"].items():
        lines.append(f"{k:38s} {v.get('layer', ''):11s} {v.get('status', ''):17s} {str(v.get('access', ''))[:90]}")
    lines.append("")
    lines.append("--- local files (data/raw) ---")
    for k, v in summary["local"].items():
        size = v.get("bytes")
        extra = {kk: vv for kk, vv in v.items() if kk not in ("path", "bytes")}
        lines.append(f"{k:38s} {size / 1e9 if size else 0:8.2f} GB  {extra}")
    hl = summary.get("hreda_live")
    if isinstance(hl, list):
        lines.append("")
        lines.append("--- ESA HREDA (live TAP query) ---")
        for r in hl:
            lines.append(f"{r['investigation_unique_acronym']:32s} data_available={r['data_available']!s:5s} "
                         f"files={r['n_files']:4d} medical_sensitive={r['medical_sensitive']}")
    elif hl:
        lines.append(f"HREDA query failed: {hl}")
    if "ubfc" in summary:
        lines.append("")
        lines.append(f"--- UBFC-rPPG --- {summary['ubfc']}")
    if "prcp" in summary:
        lines.append("")
        lines.append(f"--- PhysioNet PRCP ({summary['prcp']['subjects']} subjects, group means of per-subject medians) ---")
        lines.append(pd.DataFrame(summary["prcp"]["group_means_by_condition"]).T.to_string())
    return "\n".join(lines)
