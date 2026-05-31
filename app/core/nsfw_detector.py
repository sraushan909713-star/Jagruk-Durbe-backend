# app/core/nsfw_detector.py
# ─────────────────────────────────────────────────────────────
# NSFW image classifier wrapper using NudeNet.
# Loads the ONNX model lazily (first use), then reuses singleton.
# Exposes `is_image_safe(image_bytes)` → (bool, str|None).
# Fails closed: on any processing error, returns unsafe.
# ─────────────────────────────────────────────────────────────

import os
import tempfile
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Lazy-loaded singleton (avoid loading the ONNX model at import time
# so server startup stays fast in dev).
_detector = None

# Detection classes that flag as NSFW, each with its own minimum confidence.
# Different categories get different thresholds:
#   - Explicit exposure: low threshold (we're confident any detection is bad)
#   - Implied exposure (genitalia/anus "covered"): medium threshold
#   - Visible contour (breast/buttocks "covered"): high threshold
#     (to avoid false positives on normal clothing)
# Full class list: https://github.com/notAI-tech/NudeNet
UNSAFE_RULES = {
    # Explicit exposure
    "FEMALE_BREAST_EXPOSED":      0.30,
    "FEMALE_GENITALIA_EXPOSED":   0.30,
    "MALE_GENITALIA_EXPOSED":     0.30,
    "ANUS_EXPOSED":               0.30,
    "BUTTOCKS_EXPOSED":           0.40,
    # Implied exposure
    "FEMALE_GENITALIA_COVERED":   0.50,
    "ANUS_COVERED":               0.50,
    # Visible contour (lingerie / swimsuit / very tight clothing)
    "FEMALE_BREAST_COVERED":      0.70,
    "BUTTOCKS_COVERED":           0.70,
}

# NudeNet returns scores 0.0–1.0. 0.5 is a balanced threshold;
# tune up to be stricter, down to be more permissive.
UNSAFE_THRESHOLD = 0.5


def _get_detector():
    """Lazy-load the NudeNet detector on first use."""
    global _detector
    if _detector is None:
        from nudenet import NudeDetector
        logger.info("Loading NudeNet detector (first run may download ~90MB model)...")
        _detector = NudeDetector()
        logger.info("NudeNet detector ready.")
    return _detector


def is_image_safe(image_bytes: bytes) -> Tuple[bool, Optional[str]]:
    """
    Run NSFW detection on raw image bytes.
    Returns (is_safe, triggering_class_or_None).
    Fails closed: any exception → not safe.
    """
    detector = _get_detector()
    tmp_path = None

    try:
        # NudeNet's detect() accepts a file path. Write bytes to a temp file.
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name

        detections = detector.detect(tmp_path)

        for det in detections:
            cls = det.get("class")
            score = det.get("score", 0.0)
            threshold = UNSAFE_RULES.get(cls)
            if threshold is not None and score >= threshold:
                logger.warning(f"Image rejected: class={cls} score={score:.2f}")
                return False, cls

        return True, None

    except Exception as e:
        logger.error(f"NSFW detection failed with exception: {e}")
        return False, "processing_error"

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def warmup_detector():
    """Trigger model load explicitly — call at app startup if you want
    to avoid the slow first request."""
    _get_detector()