# ==============================================================================
# PDF font utilities for CJK-safe rendering
# ==============================================================================

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional, Tuple

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

try:
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
except Exception:  # pragma: no cover - optional dependency behavior
    UnicodeCIDFont = None

FontCandidate = Tuple[str, str, Optional[int]]


def _iter_font_candidates(preferred_path: Optional[str] = None) -> Iterable[FontCandidate]:
    if preferred_path:
        yield ("CustomFont", preferred_path, 0)

    env_path = os.getenv("SAMA_PDF_FONT")
    if env_path:
        yield ("EnvFont", env_path, 0)

    repo_root = Path(__file__).resolve().parents[2]
    assets_dir = repo_root / "assets" / "fonts"
    if assets_dir.is_dir():
        yield ("NotoSansSC", str(assets_dir / "NotoSansSC-Regular.otf"), None)
        yield ("NotoSansCJK", str(assets_dir / "NotoSansCJK-Regular.ttc"), 0)

    if os.name == "nt":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        fonts_dir = os.path.join(windir, "Fonts")
        yield ("MicrosoftYaHei", os.path.join(fonts_dir, "msyh.ttc"), 0)
        yield ("SimSun", os.path.join(fonts_dir, "simsun.ttc"), 0)
        yield ("SimHei", os.path.join(fonts_dir, "simhei.ttf"), None)
        yield ("KaiTi", os.path.join(fonts_dir, "simkai.ttf"), None)
    else:
        yield ("PingFang", "/System/Library/Fonts/PingFang.ttc", 0)
        yield ("HiraginoSansGB", "/System/Library/Fonts/Hiragino Sans GB.ttc", 0)
        yield ("STHeiti", "/System/Library/Fonts/STHeiti Light.ttc", 0)
        yield ("NotoSansCJK", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0)
        yield ("NotoSansCJKsc", "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf", None)
        yield ("WenQuanYiMicroHei", "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 0)


def _register_font(name: str, path: str, subfont_index: Optional[int]) -> bool:
    try:
        if subfont_index is None:
            pdfmetrics.registerFont(TTFont(name, path))
        else:
            pdfmetrics.registerFont(TTFont(name, path, subfontIndex=subfont_index))
        pdfmetrics.registerFontFamily(
            name,
            normal=name,
            bold=name,
            italic=name,
            boldItalic=name,
        )
        return True
    except Exception:
        return False


def register_cjk_font(preferred_path: Optional[str] = None) -> str:
    """
    Register a CJK-capable font for ReportLab and return the font name.

    Falls back to a built-in CID font if no system font is available.
    """
    for name, path, subfont_index in _iter_font_candidates(preferred_path):
        if not path or not os.path.exists(path):
            continue
        if _register_font(name, path, subfont_index):
            return name

    if UnicodeCIDFont is not None:
        try:
            pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
            pdfmetrics.registerFontFamily(
                "STSong-Light",
                normal="STSong-Light",
                bold="STSong-Light",
                italic="STSong-Light",
                boldItalic="STSong-Light",
            )
            return "STSong-Light"
        except Exception:
            pass

    return "Helvetica"
