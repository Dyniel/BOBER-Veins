#!/usr/bin/env python3
"""
Decode every downloaded UBFC-rPPG video once and cache per-frame face RGB traces.

Writes ``<data-dir>/interim/ubfc_rgb/<session_id>.npz`` (the cache read by
``vascushift.data.ubfc.load_ubfc_session``) and a per-video log
``<data-dir>/interim/ubfc_rgb/_extraction_log.csv`` with frame count, face
detection rate and decode time. Sessions already cached are skipped unless
``--force``; the run can be interrupted and restarted.

    python scripts/extract_ubfc_traces.py                    # all 50 sessions, 4 workers
    python scripts/extract_ubfc_traces.py --subsets DATASET_2 --workers 6
"""

import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from vascushift.data.ubfc import extract_face_rgb_traces, list_ubfc_sessions  # noqa: E402


def _extract(video_path: str, out_path: str) -> dict:
    t0 = time.time()
    tr = extract_face_rgb_traces(Path(video_path))
    tmp = Path(out_path).with_suffix(".tmp.npz")
    np.savez_compressed(tmp, **tr)
    tmp.replace(out_path)
    return {"n_frames": len(tr["rgb"]), "face_found_rate": round(float(tr["face_found"].mean()), 4),
            "frames_before_first_face": int(np.argmax(tr["face_found"])) if tr["face_found"].any() else -1,
            "decode_s": round(time.time() - t0, 1)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-dir", default=str(repo_root / "data"))
    p.add_argument("--subsets", nargs="+", default=["DATASET_2", "DATASET_1"])
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--force", action="store_true", help="re-extract sessions that are already cached")
    a = p.parse_args()

    root = Path(a.data_dir) / "raw" / "rppg" / "UBFC-rPPG"
    out_dir = Path(a.data_dir) / "interim" / "ubfc_rgb"
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "_extraction_log.csv"
    log = pd.read_csv(log_path) if log_path.exists() else pd.DataFrame()

    sessions = [s for s in list_ubfc_sessions(root, subsets=tuple(a.subsets)) if s.has_video]
    todo = [s for s in sessions if a.force or not (out_dir / f"{s.session_id}.npz").exists()]
    print(f"[ubfc-rgb] {len(sessions)} sessions with video, {len(todo)} to extract, {a.workers} workers")

    rows = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(_extract, str(s.video_path), str(out_dir / f"{s.session_id}.npz")): s for s in todo}
        for i, f in enumerate(as_completed(futs), 1):
            s = futs[f]
            try:
                r = {"session_id": s.session_id, **f.result(), "error": ""}
            except Exception as e:  # keep going; the failure is logged and the session stays uncached
                r = {"session_id": s.session_id, "error": repr(e)}
            rows.append(r)
            print(f"  [{i}/{len(todo)}] {s.session_id}: {r}", flush=True)

    logged = set(log["session_id"]) if len(log) else set()
    for s in sessions:  # caches made earlier (e.g. by load_ubfc_session) but missing from the log
        npz = out_dir / f"{s.session_id}.npz"
        if npz.exists() and s.session_id not in logged and s.session_id not in {r["session_id"] for r in rows}:
            ff = np.load(npz)["face_found"]
            rows.append({"session_id": s.session_id, "n_frames": len(ff), "face_found_rate": round(float(ff.mean()), 4),
                         "frames_before_first_face": int(np.argmax(ff)) if ff.any() else -1,
                         "decode_s": np.nan, "error": ""})

    if rows:
        new = pd.DataFrame(rows)
        log = pd.concat([log[~log["session_id"].isin(new["session_id"])] if len(log) else log, new], ignore_index=True)
        log.sort_values("session_id").to_csv(log_path, index=False)
    print(f"[ubfc-rgb] log -> {log_path}")


if __name__ == "__main__":
    main()
