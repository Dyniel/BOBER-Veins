#!/usr/bin/env python3
"""
Download the openly accessible datasets used by VascuShift into data/raw/.

Examples:
    python scripts/download_data.py --dataset physionet          # PRCP + videopulse + orthostat (~80 MB)
    python scripts/download_data.py --dataset github             # tilt IJV/IJVP + tilt/LBNP dose-response (<1 MB)
    python scripts/download_data.py --dataset ubfc --subjects subject1 subject3   # smoke test
    python scripts/download_data.py --dataset ubfc                # full UBFC-rPPG (~92 GB)
    python scripts/download_data.py --dataset hreda-snapshot     # refresh ESA HREDA metadata snapshot
    python scripts/download_data.py --dataset all

Restricted datasets (ESA HREDA files, NASA LSDA, PURE, MMPD, UBFC-Phys, ...) are
NOT downloaded here: they need a login or a signed agreement. See
docs/data_audit.md for the access route of each.
"""

import argparse
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

from vascushift.data.download import (  # noqa: E402
    download_github_repo_files,
    download_physionet_project,
    download_ubfc_rppg,
)
from vascushift.data.registry import GITHUB_DATA_REPOS, PHYSIONET_PROJECTS  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dataset", required=True, choices=["ubfc", "physionet", "github", "hreda-snapshot", "all"])
    p.add_argument("--data-dir", default=str(repo_root / "data"))
    p.add_argument("--subsets", nargs="+", default=["DATASET_2", "DATASET_1"], help="UBFC sub-datasets")
    p.add_argument("--subjects", nargs="*", default=None, help="UBFC subject folders to fetch (default: all)")
    p.add_argument("--gt-only", action="store_true", help="UBFC: fetch ground-truth files only, no videos")
    p.add_argument("--source", default="sharepoint", choices=["sharepoint", "gdrive"], help="UBFC mirror")
    args = p.parse_args()

    data_dir = Path(args.data_dir)

    if args.dataset in ("physionet", "all"):
        for slug, version in PHYSIONET_PROJECTS:
            print(f"[physionet] {slug}/{version} ...", flush=True)
            out = download_physionet_project(slug, version, data_dir / "raw" / "physionet")
            print(f"[physionet] {slug}/{version} -> {out}", flush=True)

    if args.dataset in ("github", "all"):
        for owner, repo in GITHUB_DATA_REPOS:
            out = download_github_repo_files(owner, repo, data_dir / "raw" / "github")
            print(f"[github] {owner}/{repo} -> {out}", flush=True)

    if args.dataset in ("hreda-snapshot", "all"):
        from vascushift.data.hreda import save_hreda_snapshot

        out = save_hreda_snapshot(data_dir / "external" / "hreda")
        print(f"[hreda] metadata snapshot -> {out}", flush=True)

    if args.dataset in ("ubfc", "all"):
        print("[ubfc] downloading UBFC-rPPG (~92 GB total; DATASET_2 ~75 GB) ...", flush=True)
        out = download_ubfc_rppg(
            data_dir / "raw" / "rppg" / "UBFC-rPPG",
            subsets=args.subsets,
            subjects=args.subjects,
            include_videos=not args.gt_only,
            source=args.source,
        )
        print(f"[ubfc] -> {out}", flush=True)


if __name__ == "__main__":
    main()
