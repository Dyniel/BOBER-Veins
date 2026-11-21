"""
UBFC-rPPG loader (Bobbia et al., Pattern Recognit. Lett. 124:82-90, 2019; online 2017).

Layout after ``scripts/download_data.py --dataset ubfc``::

    data/raw/rppg/UBFC-rPPG/
        readme.txt, Agreement.xlsx, ubfcrppg_data_processor.{m,py}
        DATASET_1/<5-gt|...|12-gt|after-exercise>/{vid.avi, gtdump.xmp}
        DATASET_2/subject<k>/{vid.avi, ground_truth.txt}

Ground truth (from the dataset readme):
    DATASET_1  gtdump.xmp (CSV): time [ms], HR [bpm], SpO2 [%], PPG
    DATASET_2  ground_truth.txt: line 1 PPG, line 2 HR [bpm], line 3 time [s]

Audit notes (checked on all 50 real sessions, see docs/data_audit.md):
  * DATASET_2: ``ground_truth.txt`` has exactly one row per video frame (42/42
    sessions), so its time line is the *frame clock*. That clock is irregular:
    median frame step 33-43 ms, single gaps up to 1.0 s (dropped frames), mean
    rate 23.2-30.0 fps (subjects 25-27 ~23.3 fps), and a few duplicated stamps
    (dt = 0, never backwards). The AVI header fps is only the average rate.
    ``load_ubfc_session`` therefore uses the GT time line as frame timestamps and
    resamples RGB + PPG onto a uniform grid, masking long gaps (``valid``).
  * DATASET_1: GT is logged on its own clock at ~62 Hz; the video runs at a
    constant 28.67 fps (no per-frame stamps; video and GT spans agree to ~0.1 s).
  * The pulse-oximeter HR column contains dropouts (values of 1 bpm in subjects
    11, 18, 20, 24). The dataset authors evaluate against HR computed from the
    PPG waveform, not this column; ``reference_hr_from_ppg`` does that.
  * Subjects 21 and 27 of DATASET_2: facial images must not appear in any
    publication, presentation or report (the release has no subject21 folder, so
    in practice this is subject27). ``UbfcSession.no_face_display`` carries that
    flag - dashboards and posters must respect it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import signal as sps

DEFAULT_ROOT = Path("data/raw/rppg/UBFC-rPPG")
NO_FACE_DISPLAY = {("DATASET_2", "subject21"), ("DATASET_2", "subject27")}


@dataclass
class UbfcGroundTruth:
    t: np.ndarray            # seconds, starting at 0, strictly increasing (duplicates dropped)
    ppg: np.ndarray          # raw finger PPG (arbitrary units)
    hr_sensor: np.ndarray    # oximeter HR column (contains dropouts; do not use as reference)
    spo2: Optional[np.ndarray] = None
    n_raw_samples: int = 0
    n_duplicate_t: int = 0
    max_gap_s: float = 0.0
    n_hr_dropouts: int = 0   # samples with sensor HR < 30 bpm

    @property
    def duration_s(self) -> float:
        return float(self.t[-1] - self.t[0]) if len(self.t) > 1 else 0.0

    @property
    def mean_fs(self) -> float:
        return (len(self.t) - 1) / self.duration_s if self.duration_s > 0 else float("nan")


@dataclass
class UbfcSession:
    subset: str              # DATASET_1 / DATASET_2
    subject: str             # folder name, e.g. "subject12" or "8-gt"
    folder: Path
    video_path: Path
    gt_path: Path
    no_face_display: bool = False
    meta: Dict = field(default_factory=dict)

    @property
    def session_id(self) -> str:
        return f"ubfc-{'d1' if self.subset == 'DATASET_1' else 'd2'}-{self.subject}"

    @property
    def has_video(self) -> bool:
        return self.video_path.exists() and self.video_path.stat().st_size > 0


def list_ubfc_sessions(root: Path = DEFAULT_ROOT, subsets=("DATASET_2", "DATASET_1")) -> List[UbfcSession]:
    """Lists sessions that have a ground-truth file (videos may still be downloading)."""
    root = Path(root)
    sessions = []
    for subset in subsets:
        sdir = root / subset
        if not sdir.is_dir():
            continue
        for folder in sorted(p for p in sdir.iterdir() if p.is_dir()):
            gt = folder / ("ground_truth.txt" if subset == "DATASET_2" else "gtdump.xmp")
            if not gt.exists():
                continue
            sessions.append(UbfcSession(
                subset=subset,
                subject=folder.name,
                folder=folder,
                video_path=folder / "vid.avi",
                gt_path=gt,
                no_face_display=(subset, folder.name) in NO_FACE_DISPLAY,
            ))
    sessions.sort(key=lambda s: (s.subset, _natural_key(s.subject)))
    return sessions


def _natural_key(name: str):
    digits = "".join(ch for ch in name if ch.isdigit())
    return (int(digits) if digits else 10**6, name)


def load_ubfc_ground_truth(session: UbfcSession) -> UbfcGroundTruth:
    """Parses and cleans the GT file of a session (both DATASET_1 and DATASET_2 formats)."""
    if session.subset == "DATASET_2":
        raw = np.loadtxt(session.gt_path)
        if raw.ndim != 2 or raw.shape[0] != 3:
            raise ValueError(f"{session.gt_path}: expected 3 rows (PPG, HR, time), got {raw.shape}")
        ppg, hr, t = raw[0], raw[1], raw[2]
        spo2 = None
    else:
        raw = pd.read_csv(session.gt_path, header=None).to_numpy(dtype=float)
        if raw.shape[1] < 4:
            raise ValueError(f"{session.gt_path}: expected 4 columns (t_ms, HR, SpO2, PPG), got {raw.shape}")
        t, hr, spo2, ppg = raw[:, 0] / 1000.0, raw[:, 1], raw[:, 2], raw[:, 3]

    n_raw = len(t)
    order = np.argsort(t, kind="stable")
    t, ppg, hr = t[order], ppg[order], hr[order]
    spo2 = spo2[order] if spo2 is not None else None
    keep = np.concatenate([[True], np.diff(t) > 0])
    n_dup = int((~keep).sum())
    t, ppg, hr = t[keep], ppg[keep], hr[keep]
    spo2 = spo2[keep] if spo2 is not None else None
    t = t - t[0]
    gaps = np.diff(t)
    return UbfcGroundTruth(
        t=t, ppg=ppg, hr_sensor=hr, spo2=spo2,
        n_raw_samples=n_raw, n_duplicate_t=n_dup,
        max_gap_s=float(gaps.max()) if len(gaps) else 0.0,
        n_hr_dropouts=int((hr < 30).sum()),
    )


def resample_ppg(gt: UbfcGroundTruth, t_target: np.ndarray) -> np.ndarray:
    """Linearly interpolates the GT PPG onto arbitrary timestamps (e.g. video frame times)."""
    return np.interp(t_target, gt.t, gt.ppg)


def reference_hr_from_ppg(
    ppg: np.ndarray,
    fs: float,
    window_s: Optional[float] = None,
    stride_s: float = 1.0,
    hr_range_bpm: Tuple[float, float] = (40.0, 200.0),
) -> np.ndarray | float:
    """
    Reference HR from the contact PPG waveform (Welch peak in the HR band).

    With ``window_s=None`` returns one value for the whole signal, otherwise an
    array with one value per sliding window (start at 0, step ``stride_s``).
    """
    lo, hi = hr_range_bpm[0] / 60.0, hr_range_bpm[1] / 60.0
    b, a = sps.butter(3, [lo / (fs / 2), min(0.99, hi / (fs / 2))], btype="band")
    x = sps.filtfilt(b, a, sps.detrend(np.asarray(ppg, dtype=float)))

    def _peak(seg: np.ndarray) -> float:
        f, p = sps.welch(seg, fs=fs, nperseg=min(len(seg), int(fs * 8)), nfft=8192)
        m = (f >= lo) & (f <= hi)
        return float(f[m][np.argmax(p[m])] * 60.0)

    if window_s is None:
        return _peak(x)
    w, s = int(window_s * fs), max(1, int(stride_s * fs))
    return np.array([_peak(x[i:i + w]) for i in range(0, len(x) - w + 1, s)])


def _ffprobe(video_path: Path) -> Dict:
    import json as _json
    import subprocess

    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=codec_name,pix_fmt,width,height,avg_frame_rate,nb_frames:format=duration",
         "-of", "json", str(video_path)],
        check=True, capture_output=True, text=True,
    ).stdout
    d = _json.loads(out)
    st = d["streams"][0]
    num, den = (st.get("avg_frame_rate") or "0/1").split("/")
    fps = float(num) / float(den) if float(den) else 0.0
    n = int(st.get("nb_frames") or 0)
    if not n and fps:
        n = int(round(float(d.get("format", {}).get("duration", 0)) * fps))
    return {"fps": fps, "n_frames": n, "width": int(st["width"]), "height": int(st["height"]),
            "codec": st.get("codec_name"), "pix_fmt": st.get("pix_fmt")}


def video_info(video_path: Path) -> Dict:
    """
    Frame rate / count / size. Uses ffprobe (UBFC AVIs are uncompressed bgr24;
    their real frame rate is NOT exactly 30 fps, e.g. 28.67 fps for DATASET_1/10-gt).
    """
    import shutil as _sh

    if _sh.which("ffprobe"):
        return _ffprobe(Path(video_path))
    import cv2

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise IOError(f"cannot open {video_path}")
    info = {"fps": float(cap.get(cv2.CAP_PROP_FPS)), "n_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "codec": None, "pix_fmt": None}
    cap.release()
    return info


def iter_video_frames_rgb(video_path: Path, max_frames: Optional[int] = None) -> Iterator[np.ndarray]:
    """
    Yields RGB uint8 frames (H, W, 3).

    Decoding goes through a system ``ffmpeg`` pipe: the FFMPEG backend bundled in
    the opencv-python wheels segfaults on the uncompressed UBFC AVIs (observed
    with opencv-python-headless 4.14 on Linux). OpenCV is used only as a fallback.
    """
    import shutil as _sh
    import subprocess

    video_path = Path(video_path)
    if not _sh.which("ffmpeg"):
        import cv2

        cap = cv2.VideoCapture(str(video_path))
        n = 0
        try:
            while max_frames is None or n < max_frames:
                ok, bgr = cap.read()
                if not ok:
                    break
                n += 1
                yield cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        finally:
            cap.release()
        return

    info = video_info(video_path)
    w, h = info["width"], info["height"]
    frame_bytes = w * h * 3
    cmd = ["ffmpeg", "-v", "error", "-i", str(video_path)]
    if max_frames is not None:
        cmd += ["-frames:v", str(int(max_frames))]
    cmd += ["-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=frame_bytes * 4)
    try:
        while True:
            buf = proc.stdout.read(frame_bytes)
            if len(buf) < frame_bytes:
                break
            yield np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 3)
    finally:
        proc.stdout.close()
        proc.kill()
        proc.wait()


def extract_face_rgb_traces(
    video_path: Path,
    detect_every: int = 15,
    max_frames: Optional[int] = None,
) -> Dict[str, np.ndarray]:
    """
    Mean skin RGB inside a face box per frame.

    Face box: OpenCV Haar cascade, re-detected every ``detect_every`` frames and
    exponentially smoothed; the ROI is the central part of the box (forehead +
    cheeks, without the hair line and mouth) combined with the YCrCb skin mask
    of ``vascushift.optical.roi``. Frames without a detection reuse the last box.

    Returns ``{"rgb": (N, 3) float, "face_found": (N,) bool, "bbox": (N, 4) int}``.
    """
    import cv2

    from vascushift.optical.roi import extract_skin_mask

    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    rgb, found, boxes = [], [], []
    box = None
    for i, frame in enumerate(iter_video_frames_rgb(video_path, max_frames=max_frames)):
        hit = False
        if box is None or i % detect_every == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
            if len(faces):
                new = np.array(max(faces, key=lambda f: f[2] * f[3]), dtype=float)
                box = new if box is None else 0.7 * box + 0.3 * new
                hit = True
        if box is None:
            rgb.append([np.nan] * 3)
            found.append(False)
            boxes.append([0, 0, 0, 0])
            continue
        x, y, w, h = box
        # central face region: 15-85 % width, 10-60 % height (forehead + cheeks)
        x0, x1 = int(x + 0.15 * w), int(x + 0.85 * w)
        y0, y1 = int(y + 0.10 * h), int(y + 0.60 * h)
        roi = frame[max(0, y0):y1, max(0, x0):x1]
        mask = extract_skin_mask(roi).astype(bool)
        px = roi[mask] if mask.sum() > 200 else roi.reshape(-1, 3)
        rgb.append(px.mean(axis=0))
        found.append(hit or i % detect_every != 0)
        boxes.append([x0, y0, x1 - x0, y1 - y0])
    return {"rgb": np.asarray(rgb, dtype=float), "face_found": np.asarray(found), "bbox": np.asarray(boxes, dtype=int)}


def frame_clock(session: UbfcSession, n_frames: int, fps_header: float) -> Tuple[np.ndarray, np.ndarray, str]:
    """
    Capture times [s] of the first ``n_frames`` video frames.

    Returns ``(t_frames, keep, clock)`` where ``keep`` marks frames whose stamp is
    strictly later than every earlier one (duplicated stamps are dropped) and
    ``clock`` is ``"gt_frame_clock"`` (DATASET_2: GT has one row per frame) or
    ``"uniform_header_fps"`` (DATASET_1, or a DATASET_2 file whose row count does
    not cover the frames - never observed, kept as a guarded fallback).
    """
    if session.subset == "DATASET_2":
        t_raw = np.loadtxt(session.gt_path)[2]
        if len(t_raw) >= n_frames:
            t = t_raw[:n_frames] - t_raw[0]
            prev_max = np.maximum.accumulate(t)
            keep = np.concatenate([[True], t[1:] > prev_max[:-1]])
            return t, keep, "gt_frame_clock"
    fps = fps_header if fps_header > 0 else 30.0
    return np.arange(n_frames) / fps, np.ones(n_frames, dtype=bool), "uniform_header_fps"


def align_to_uniform_grid(
    t_frames: np.ndarray,
    rgb: np.ndarray,
    face_found: np.ndarray,
    t_ppg: np.ndarray,
    ppg: np.ndarray,
    fs_out: float = 30.0,
    max_interp_gap_s: float = 0.25,
) -> Dict[str, np.ndarray]:
    """
    Resamples per-frame RGB traces and the contact PPG onto one uniform time grid.

    ``t_frames`` must be strictly increasing (see ``frame_clock``). The grid
    starts at 0 and ends at the earlier of the last frame and the last PPG
    sample. A grid sample is ``valid`` unless it lies inside a frame gap longer
    than ``max_interp_gap_s`` (linear interpolation across a dropped-frame hole
    would invent a straight line where the pulse should be) or before the first
    face detection.
    """
    t_frames = np.asarray(t_frames, dtype=float)
    rgb = np.asarray(rgb, dtype=float)
    face_found = np.asarray(face_found, dtype=bool)
    if len(t_frames) < 2 or np.any(np.diff(t_frames) <= 0):
        raise ValueError("t_frames must be strictly increasing with >= 2 samples")
    t_end = min(t_frames[-1], float(t_ppg[-1]))
    t_u = np.arange(0.0, t_end + 1e-9, 1.0 / fs_out)

    face_ok = face_found & np.all(np.isfinite(rgb), axis=1)
    if face_ok.any():
        # rows without a usable face box: before the first detection take the first valid row, later ones
        # hold the last valid row (no NaN may reach np.interp); those samples end up valid = False anyway
        first = int(np.argmax(face_ok))
        rgb = rgb.copy()
        rgb[:first] = rgb[first]
        bad = ~np.all(np.isfinite(rgb), axis=1)
        if bad.any():
            last_ok = np.maximum.accumulate(np.where(~bad, np.arange(len(rgb)), 0))
            rgb[bad] = rgb[last_ok[bad]]
    rgb_u = np.column_stack([np.interp(t_u, t_frames, rgb[:, c]) for c in range(rgb.shape[1])])
    ppg_u = np.interp(t_u, t_ppg, ppg)

    seg = np.clip(np.searchsorted(t_frames, t_u, side="right") - 1, 0, len(t_frames) - 2)
    in_gap = (t_frames[seg + 1] - t_frames[seg]) > max_interp_gap_s
    face_u = np.interp(t_u, t_frames, face_ok.astype(float)) > 0.5
    return {"time": t_u, "rgb": rgb_u, "ppg": ppg_u, "face_found": face_u, "valid": ~in_gap & face_u}


def load_ubfc_session(
    session: UbfcSession,
    cache_dir: Optional[Path] = Path("data/interim/ubfc_rgb"),
    max_frames: Optional[int] = None,
    fs_out: float = 30.0,
    max_interp_gap_s: float = 0.25,
) -> Dict:
    """
    Loads one session in the dict format used by ``vascushift.experiments.rppg``.

    Everything returned at the top level (``time``, ``rgb_traces``, ``ref_bvp``,
    ``face_found``, ``valid``) lives on one uniform grid at ``fs`` = ``fs_out``
    Hz, built from the real frame timestamps (see ``frame_clock``). ``ref_hr_bpm``
    is the HR of the contact PPG waveform. Per-frame data before resampling is
    kept under ``frames``.

    RGB traces are cached per frame as ``<cache_dir>/<session_id>.npz`` because
    decoding a 1-3 GB uncompressed AVI takes ~30-60 s; the cache does not depend
    on ``fs_out``.
    """
    if not session.has_video:
        raise FileNotFoundError(f"{session.video_path} not downloaded yet")
    info = video_info(session.video_path)

    cache = Path(cache_dir) / f"{session.session_id}.npz" if cache_dir else None
    if cache is not None and cache.exists() and max_frames is None:
        z = np.load(cache)
        traces = {k: z[k] for k in z.files}
    else:
        traces = extract_face_rgb_traces(session.video_path, max_frames=max_frames)
        if cache is not None and max_frames is None:
            cache.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(cache, **traces)

    n = len(traces["rgb"])
    t_all, keep, clock = frame_clock(session, n, info["fps"])
    t_frames = t_all[keep]
    gt = load_ubfc_ground_truth(session)
    if clock == "gt_frame_clock":  # PPG row i belongs to frame i: same time line, same duplicates dropped
        ppg_frames = np.loadtxt(session.gt_path)[0][:n][keep]
        t_ppg, ppg = t_frames, ppg_frames
    else:
        t_ppg, ppg = gt.t, gt.ppg
    g = align_to_uniform_grid(t_frames, traces["rgb"][keep], traces["face_found"][keep], t_ppg, ppg,
                              fs_out=fs_out, max_interp_gap_s=max_interp_gap_s)
    steps = np.diff(t_frames)
    return {
        "dataset": "UBFC-rPPG",
        "subject_id": session.session_id,
        "fs": float(fs_out),
        "time": g["time"],
        "rgb_traces": g["rgb"],
        "face_found": g["face_found"],
        "valid": g["valid"],
        "ref_bvp": g["ppg"],
        "ref_hr_bpm": reference_hr_from_ppg(g["ppg"], fs_out),
        "frames": {
            "t": t_frames, "rgb": traces["rgb"][keep], "face_found": traces["face_found"][keep],
            "clock": clock, "n_decoded": n, "n_dropped_duplicate_stamps": int((~keep).sum()),
        },
        "gt_quality": {
            "n_duplicate_t": gt.n_duplicate_t,
            "max_gap_s": gt.max_gap_s,
            "n_hr_dropouts": gt.n_hr_dropouts,
            "gt_duration_s": gt.duration_s,
            "video_duration_s": float(t_frames[-1]),
            "max_frame_step_s": float(steps.max()) if len(steps) else 0.0,
            "n_frame_gaps_over_max_interp": int((steps > max_interp_gap_s).sum()),
            "fraction_valid": float(g["valid"].mean()),
        },
        "video": info,
        "no_face_display": session.no_face_display,
        "is_real": True,
    }


def ubfc_inventory(root: Path = DEFAULT_ROOT, with_video_info: bool = True) -> pd.DataFrame:
    """One row per session: GT statistics, video presence/format and display restrictions."""
    rows = []
    for s in list_ubfc_sessions(root):
        gt = load_ubfc_ground_truth(s)
        row = {
            "session_id": s.session_id,
            "subset": s.subset,
            "subject": s.subject,
            "gt_samples": gt.n_raw_samples,
            "gt_duration_s": round(gt.duration_s, 2),
            "gt_mean_fs": round(gt.mean_fs, 2),
            "gt_duplicate_t": gt.n_duplicate_t,
            "gt_max_gap_s": round(gt.max_gap_s, 3),
            "hr_sensor_dropouts": gt.n_hr_dropouts,
            "hr_ref_from_ppg_bpm": round(reference_hr_from_ppg(np.interp(
                np.arange(0, gt.t[-1], 1 / 30.0), gt.t, gt.ppg), 30.0), 1),
            "hr_sensor_median_bpm": float(np.median(gt.hr_sensor[gt.hr_sensor >= 30])) if (gt.hr_sensor >= 30).any() else np.nan,
            "video_present": s.has_video,
            "no_face_display": s.no_face_display,
        }
        if with_video_info and s.has_video:
            try:
                vi = video_info(s.video_path)
                row.update({
                    "video_bytes": s.video_path.stat().st_size,
                    "fps": vi["fps"], "n_frames": vi["n_frames"],
                    "resolution": f"{vi['width']}x{vi['height']}", "codec": vi["codec"], "pix_fmt": vi["pix_fmt"],
                    "video_duration_s": round(vi["n_frames"] / vi["fps"], 2) if vi["fps"] else np.nan,
                })
                t_f, keep, clock = frame_clock(s, vi["n_frames"], vi["fps"])
                steps = np.diff(t_f[keep])
                row.update({
                    "frame_clock": clock,
                    "frame_step_median_ms": round(1000 * float(np.median(steps)), 1),
                    "frame_step_max_s": round(float(steps.max()), 3),
                    "frame_gaps_over_0p25s": int((steps > 0.25).sum()),
                })
            except IOError:
                row["video_present"] = False
        rows.append(row)
    return pd.DataFrame(rows)
