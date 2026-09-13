from __future__ import annotations

import cv2
import numpy as np

_original_hough_lines_p = cv2.HoughLinesP


def _hough_lines_p_compat(*args, **kwargs):
    """Normalize OpenCV HoughLinesP output to the legacy Nx1x4 shape.

    OpenCV builds can return either Nx1x4 or Nx4. The v0.6 extractor
    indexed the former directly, so Nx4 caused an IndexError on the
    user's Windows/OpenCV build. This shim keeps the extractor version-
    agnostic without changing its geometry logic.
    """
    raw = _original_hough_lines_p(*args, **kwargs)
    if raw is None:
        return None
    arr = np.asarray(raw)
    if arr.ndim == 2 and arr.shape[-1] == 4:
        return arr[:, None, :]
    if arr.ndim == 1 and arr.size == 4:
        return arr.reshape(1, 1, 4)
    return arr


cv2.HoughLinesP = _hough_lines_p_compat

from pdf_geometry_extractor import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
