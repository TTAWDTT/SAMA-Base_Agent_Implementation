# ==============================================================================
# Encoding utilities
# ==============================================================================

from __future__ import annotations

import locale
import os
from typing import Iterable, List


def _dedupe_encodings(encodings: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for enc in encodings:
        if not enc:
            continue
        key = enc.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(enc)
    return ordered


def _preferred_encoding() -> str:
    override = os.getenv("SAMA_OUTPUT_ENCODING")
    if override:
        return override
    return locale.getpreferredencoding(False) or "utf-8"


def decode_output_bytes(data: bytes) -> str:
    """
    Decode subprocess output bytes using a resilient encoding strategy.
    """
    if not data:
        return ""

    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig", errors="replace")

    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16", errors="replace")

    if b"\x00" in data:
        for enc in ("utf-16-le", "utf-16-be"):
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue

    preferred = _preferred_encoding()
    encodings = [preferred]
    if preferred.lower() not in ("utf-8", "utf8"):
        encodings.append("utf-8")

    if os.name == "nt":
        encodings.extend(["gb18030", "gbk", "cp936"])

    for enc in _dedupe_encodings(encodings):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue

    return data.decode(preferred or "utf-8", errors="replace")
