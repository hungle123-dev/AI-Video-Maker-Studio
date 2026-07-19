"""Canonical video aspect ratios accepted by project and renderer code."""

from __future__ import annotations


VALID_ASPECT_RATIOS = frozenset({"9:16", "16:9", "1:1"})
DEFAULT_ASPECT_RATIO = "9:16"


def normalize_aspect_ratio(value: object) -> str:
    """Return a safe persisted value, falling back for legacy/bad metadata."""

    return value if isinstance(value, str) and value in VALID_ASPECT_RATIOS else DEFAULT_ASPECT_RATIO


def require_aspect_ratio(value: object) -> str:
    """Return a supported ratio or reject an untrusted renderer argument."""

    if isinstance(value, str) and value in VALID_ASPECT_RATIOS:
        return value
    choices = ", ".join(sorted(VALID_ASPECT_RATIOS))
    raise ValueError(f"Tỉ lệ khung hình không hợp lệ. Chỉ hỗ trợ: {choices}.")
