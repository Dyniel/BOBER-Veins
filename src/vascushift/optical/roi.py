"""
Facial Region of Interest (ROI) selection and skin pixel segmentation.
"""

from typing import Tuple, Optional
import numpy as np
import cv2


def extract_skin_mask(frame_rgb: np.ndarray) -> np.ndarray:
    """
    Extracts binary skin mask in YCrCb color space.
    Skin tones cluster in Cr in [133, 173] and Cb in [77, 127].
    """
    frame_ycrcb = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2YCrCb)
    cr = frame_ycrcb[:, :, 1]
    cb = frame_ycrcb[:, :, 2]
    skin_mask = (cr >= 133) & (cr <= 173) & (cb >= 77) & (cb <= 127)
    return skin_mask.astype(np.uint8)


def get_facial_roi(
    frame_rgb: np.ndarray,
    roi_bbox: Optional[Tuple[int, int, int, int]] = None,
    use_skin_filter: bool = True,
) -> Tuple[float, float, float]:
    """
    Extracts mean RGB values from the facial region of interest (ROI).

    Args:
        frame_rgb: RGB frame (H, W, 3).
        roi_bbox: Optional bounding box (x, y, w, h). If None, uses central 50% forehead/cheek region.
        use_skin_filter: If True, applies skin mask within the ROI.

    Returns:
        (mean_R, mean_G, mean_B)
    """
    h, w, _ = frame_rgb.shape
    if roi_bbox is None:
        # Default forehead/malar region (upper-central region of face)
        x = int(0.30 * w)
        y = int(0.20 * h)
        bw = int(0.40 * w)
        bh = int(0.35 * h)
    else:
        x, y, bw, bh = roi_bbox

    roi = frame_rgb[y : y + bh, x : x + bw]
    if use_skin_filter:
        mask = extract_skin_mask(roi)
        if np.sum(mask) > 50:
            r = np.mean(roi[:, :, 0][mask == 1])
            g = np.mean(roi[:, :, 1][mask == 1])
            b = np.mean(roi[:, :, 2][mask == 1])
            return float(r), float(g), float(b)

    # Fallback to direct ROI mean
    return float(np.mean(roi[:, :, 0])), float(np.mean(roi[:, :, 1])), float(np.mean(roi[:, :, 2]))

