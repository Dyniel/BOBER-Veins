#!/usr/bin/env python3
"""E6: extract ROI/box-tracking variants for every UBFC video (parallel, resumable). See
src/vascushift/experiments/roi_variants.py. Output: data/interim/roi_variants/<session_id>.npz"""
import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

import numpy as np  # noqa: E402

from vascushift.data.ubfc import list_ubfc_sessions  # noqa: E402
from vascushift.experiments.roi_variants import extract_variants  # noqa: E402


def _one(video: str, out: str) -> str:
    t0 = time.time()
    r = extract_variants(Path(video))
    tmp = Path(out).with_suffix(".tmp.npz")
    np.savez_compressed(tmp, **r)
    tmp.replace(out)
    return f"{Path(out).stem}: {r['rgb'].shape} detect {float(r['detect_rate']):.3f} in {time.time() - t0:.0f} s"


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", default=str(repo_root / "data"))
    p.add_argument("--workers", type=int, default=6)
    a = p.parse_args()
    out_dir = Path(a.data_dir) / "interim" / "roi_variants"
    out_dir.mkdir(parents=True, exist_ok=True)
    todo = [s for s in list_ubfc_sessions(Path(a.data_dir) / "raw" / "rppg" / "UBFC-rPPG") if s.has_video
            and not (out_dir / f"{s.session_id}.npz").exists()]
    print(f"{len(todo)} videos to process", flush=True)
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(_one, str(s.video_path), str(out_dir / f"{s.session_id}.npz")) for s in todo]
        for i, f in enumerate(as_completed(futs), 1):
            try:
                print(f"[{i}/{len(todo)}] {f.result()}", flush=True)
            except Exception as e:
                print(f"[{i}/{len(todo)}] ERROR {e!r}", flush=True)
