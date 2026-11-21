"""
PhysioNet "Video pulse signals in stationary and motion conditions" (videopulse 1.0.0, ODC-By).

Melchor Rodriguez & Ramos-Castro (UPC). 40 recordings, 15 volunteers (12 M / 3 F, 23-35 y), seated.
Record ``subj_<k>_<s|m>_<c1|c2>``: s = stationary, m = motion; c1 = Logitech camera (15 fps),
c2 = GoPro (60 fps). Each record has two WFDB files:

* ``*_vid``  single-channel *video pulse* signal already extracted by the authors (no RGB, so CHROM/POS
  cannot be applied; useful to test the HR-estimation / tracking / quality layers under motion)
* ``*_ref``  finger pulse sensor at 1 kHz, 50 s

The header comment ``reference offset time`` (tOffset, s) aligns the two: the reference starts tOffset
seconds after the start of the video signal (sign verified by cross-correlation on all 40 records, see
``offset_check``).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

import numpy as np
from scipy import signal as sps

DEFAULT_ROOT = Path("data/raw/physionet/videopulse/1.0.0")


def list_records(root: Path = DEFAULT_ROOT) -> List[str]:
    recs = (Path(root) / "RECORDS").read_text().split()
    return sorted({r.rsplit("_", 1)[0] for r in recs})


def _offset(header: Path) -> float:
    m = re.search(r"reference offset time:\s*([-\d.]+)", header.read_text())
    return float(m.group(1)) if m else 0.0


def load_record(name: str, root: Path = DEFAULT_ROOT, ref_fs_out: float = 100.0) -> Dict:
    """Video pulse + reference (decimated to ``ref_fs_out``) on the video time base."""
    import wfdb

    root = Path(root)
    vid = wfdb.rdrecord(str(root / f"{name}_vid"))
    ref = wfdb.rdrecord(str(root / f"{name}_ref"))
    off = _offset(root / f"{name}_vid.hea")
    x = vid.p_signal[:, 0].astype(float)
    r = ref.p_signal[:, 0].astype(float)
    q = int(round(ref.fs / ref_fs_out))
    r = sps.decimate(r, q, ftype="fir", zero_phase=True) if q > 1 else r
    _, k, cond, cam = name.split("_")
    return {"record": name, "subject": f"vp{int(k):02d}", "condition": {"s": "stationary", "m": "motion"}[cond],
            "camera": cam, "fs_vid": float(vid.fs), "vid": x, "t_vid": np.arange(len(x)) / vid.fs,
            "fs_ref": float(ref.fs) / q, "ref": r, "t_ref": off + np.arange(len(r)) / (ref.fs / q), "offset_s": off}


def offset_check(rec: Dict, max_lag_s: float = 20.0) -> float:
    """Lag (s) that best aligns the band-passed video pulse with the reference resampled to the video clock."""
    fs = rec["fs_vid"]
    b, a = sps.butter(3, [0.7 / (fs / 2), min(0.95, 3.5 / (fs / 2))], btype="band")
    v = sps.filtfilt(b, a, sps.detrend(rec["vid"]))
    t = rec["t_ref"] - rec["offset_s"]  # reference on its own clock starting at 0
    rr = np.interp(np.arange(0, t[-1], 1 / fs), t, rec["ref"])
    rr = sps.filtfilt(b, a, sps.detrend(rr))
    best, best_lag = -np.inf, 0.0
    for lag in np.arange(-max_lag_s, max_lag_s, 1 / fs):
        i = int(round(lag * fs))
        vv, rv = (v[i:], rr) if i >= 0 else (v, rr[-i:])
        n = min(len(vv), len(rv))
        if n < fs * 20:
            continue
        c = abs(np.corrcoef(vv[:n], rv[:n])[0, 1])
        if c > best:
            best, best_lag = c, lag
    return float(best_lag)
