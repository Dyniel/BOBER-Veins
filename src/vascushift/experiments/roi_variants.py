"""
E6 - face ROI / box-tracking variants for rPPG (experiment, not the baseline extractor).

Finding that motivated it: the baseline box (Haar every 15 frames, smoothed) only moves on detection
frames, so the ROI jumps every 15th frame and puts a spectral line at fps/15 (~1.9-2.0 Hz, inside the
HR band) into the RGB traces; clearly visible in 7/50 UBFC sessions.

Pass 1 detects the face on EVERY frame (raw boxes). Box strategies are then derived offline:
    step15      baseline: detection every 15 frames, EMA 0.7/0.3 on hits, box held in between
    interp15    the same detections, box linearly interpolated between detection frames (no steps)
    every_ema   detection every frame, EMA with alpha = 0.15 on hits
    fixed       median box of the whole recording (UBFC subjects are mostly still)
Pass 2 decodes the video again and averages RGB inside regions of each box:
    central     15-85 % width, 10-60 % height (baseline region) + YCrCb skin mask
    central_nm  same region, no skin mask
    forehead    25-75 % width, 3-25 % height + skin mask
    cheeks      10-40 % and 60-90 % width, 45-70 % height + skin mask
    fullbox     whole detector box + skin mask
Output: data/interim/roi_variants/<session_id>.npz with ``rgb`` (n_frames, n_variants, 3) and ``names``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import numpy as np

STRATEGIES = ["step15", "interp15", "every_ema", "fixed"]
REGIONS = {
    "central": ((0.15, 0.85), (0.10, 0.60), True),
    "central_nm": ((0.15, 0.85), (0.10, 0.60), False),
    "forehead": ((0.25, 0.75), (0.03, 0.25), True),
    "cheeks": (((0.10, 0.40), (0.60, 0.90)), (0.45, 0.70), True),
    "fullbox": ((0.0, 1.0), (0.0, 1.0), True),
}


def detect_all(video_path: Path) -> np.ndarray:
    """Raw largest-face Haar box per frame (x, y, w, h), NaN where nothing is found."""
    import cv2

    from vascushift.data.ubfc import iter_video_frames_rgb

    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    out = []
    for frame in iter_video_frames_rgb(video_path):
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
        out.append(np.array(max(faces, key=lambda f: f[2] * f[3]), float) if len(faces) else np.full(4, np.nan))
    return np.vstack(out)


def _ffill(b: np.ndarray) -> np.ndarray:
    b = b.copy()
    first = np.where(~np.isnan(b[:, 0]))[0]
    if not len(first):
        return b
    b[: first[0]] = b[first[0]]
    for i in range(1, len(b)):
        if np.isnan(b[i, 0]):
            b[i] = b[i - 1]
    return b


def box_tracks(raw: np.ndarray, every: int = 15, alpha_every: float = 0.15) -> Dict[str, np.ndarray]:
    n = len(raw)
    # step15: reproduce the baseline (detect at i % 15 == 0 or while no box yet; EMA 0.7 old / 0.3 new)
    step = np.full((n, 4), np.nan)
    box = None
    det_idx, det_box = [], []
    for i in range(n):
        if box is None or i % every == 0:
            if not np.isnan(raw[i, 0]):
                box = raw[i].copy() if box is None else 0.7 * box + 0.3 * raw[i]
                det_idx.append(i)
                det_box.append(box.copy())
        if box is not None:
            step[i] = box
    step = _ffill(step)
    # interp15: same detection sequence, linear interpolation between detection frames
    if len(det_idx) >= 2:
        di = np.array(det_idx, float)
        db = np.vstack(det_box)
        interp = np.column_stack([np.interp(np.arange(n), di, db[:, k]) for k in range(4)])
    else:
        interp = step.copy()
    # every_ema
    ema = np.full((n, 4), np.nan)
    box = None
    for i in range(n):
        if not np.isnan(raw[i, 0]):
            box = raw[i].copy() if box is None else (1 - alpha_every) * box + alpha_every * raw[i]
        if box is not None:
            ema[i] = box
    ema = _ffill(ema)
    fixed = np.tile(np.nanmedian(raw, axis=0), (n, 1))
    return {"step15": step, "interp15": interp, "every_ema": ema, "fixed": fixed}


def _region_mean(frame: np.ndarray, box: np.ndarray, spec, skin_fn) -> np.ndarray:
    if np.isnan(box[0]):
        return np.full(3, np.nan)
    x, y, w, h = box
    xs, (y0f, y1f), use_mask = spec
    xs = xs if isinstance(xs[0], tuple) else (xs,)
    y0, y1 = int(y + y0f * h), int(y + y1f * h)
    pix = []
    for x0f, x1f in xs:
        x0, x1 = int(x + x0f * w), int(x + x1f * w)
        roi = frame[max(0, y0):max(0, y1), max(0, x0):max(0, x1)]
        if roi.size == 0:
            continue
        if use_mask:
            m = skin_fn(roi).astype(bool)
            px = roi[m] if m.sum() > 100 else roi.reshape(-1, 3)
        else:
            px = roi.reshape(-1, 3)
        pix.append(px)
    if not pix:
        return np.full(3, np.nan)
    return np.concatenate(pix).mean(axis=0)


def extract_variants(video_path: Path) -> Dict[str, np.ndarray]:
    from vascushift.data.ubfc import iter_video_frames_rgb
    from vascushift.optical.roi import extract_skin_mask

    raw = detect_all(video_path)
    tracks = box_tracks(raw)
    names: List[str] = [f"{s}|{r}" for s in STRATEGIES for r in REGIONS]
    out = []
    for i, frame in enumerate(iter_video_frames_rgb(video_path)):
        if i >= len(raw):
            break
        out.append([_region_mean(frame, tracks[s][i], REGIONS[r], extract_skin_mask) for s in STRATEGIES for r in REGIONS])
    return {"rgb": np.asarray(out, dtype=np.float32), "names": np.array(names), "raw_boxes": raw.astype(np.float32),
            "detect_rate": np.array(float(np.mean(~np.isnan(raw[:, 0]))))}
