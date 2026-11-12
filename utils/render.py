"""Pillow renderer for the SPYC timetable card.

The output is a fixed 900x1000 RGBA PNG that mirrors the SVG timetable card.
It is returned as an in-memory stream so callers can send it as a raw
Discord attachment (no embed required).
"""

from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from utils.embeds import TIME_SLOTS, _fmt_subject, _fmt_venue, _slot_time

W, H = 900, 1000

BG = (37, 37, 37, 255)
PANEL = (255, 255, 255, 255)
HEADER = (116, 127, 195, 255)
BREAK = (136, 139, 151, 255)
ROW = (151, 157, 186, 255)
ROW_LEFT = (172, 180, 224, 255)
WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)
SESSION = (31, 31, 31, 255)
VENUE = (243, 251, 255, 255)

ROW_YS = (220, 290, 360, 480, 550, 620, 740, 810)
BREAK_YS = (170, 430, 690)

FONT_FILE = Path(__file__).resolve().parent.parent / "assets" / "GoogleSansFlex.ttf"

# CJK fallback fonts, in the same order used by the old renderer.
CJK_FONTS = (
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msjh.ttc",
    "C:/Windows/Fonts/arialuni.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)


@lru_cache(maxsize=128)
def _latin_font(size: int, weight: int = 500) -> ImageFont.FreeTypeFont:
    """Google Sans Flex at the card's weight, or a CJK font as fallback."""
    try:
        font = ImageFont.truetype(str(FONT_FILE), size)
        try:
            # Axis order: optical size, width, weight, roundness, slant.
            font.set_variation_by_axes([18, 100, weight, 0, 0])
        except Exception:
            pass
        return font
    except Exception:
        return _cjk_font(size)


@lru_cache(maxsize=128)
def _cjk_font(size: int) -> ImageFont.FreeTypeFont:
    for path in CJK_FONTS:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _runs(text: str) -> list[tuple[str, str]]:
    """Split text into Latin (ASCII) and non-ASCII runs."""
    runs: list[tuple[str, str]] = []
    for char in text:
        kind = "latin" if char.isascii() else "cjk"
        if runs and runs[-1][0] == kind:
            runs[-1] = (kind, runs[-1][1] + char)
        else:
            runs.append((kind, char))
    return runs


def _measure(draw: ImageDraw.ImageDraw, runs, fonts) -> float:
    return sum(draw.textlength(part, font=fonts[kind]) for kind, part in runs)


def _draw_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    center_x: float,
    baseline_y: float,
    size: int,
    weight: int,
    fill,
    max_width: float,
    min_size: int = 16,
) -> None:
    """Centre mixed Latin/CJK text on a baseline, shrinking to fit."""
    text = str(text or "").replace("\n", " ").strip()
    if not text:
        return

    while True:
        fonts = {
            "latin": _latin_font(size, weight),
            "cjk": _cjk_font(size),
        }
        runs = _runs(text)
        width = _measure(draw, runs, fonts)
        if width <= max_width or size <= min_size:
            break
        size -= 1

    if width > max_width:
        # Last resort: trim and add ASCII dots (the Latin subset is ASCII-only).
        while text:
            text = text[:-1].rstrip()
            candidate = text + "..." if text else "..."
            runs = _runs(candidate)
            width = _measure(draw, runs, fonts)
            if width <= max_width:
                text = candidate
                break
        else:
            text = "..."
            runs = _runs(text)
            width = _measure(draw, runs, fonts)

    x = center_x - width / 2
    for kind, part in runs:
        font = fonts[kind]
        draw.text((x, baseline_y), part, font=font, fill=fill, anchor="ls")
        x += draw.textlength(part, font=font)


def _header_text(date_str, day_label) -> str:
    date_text = str(date_str or "").strip()
    day_text = f"Day {str(day_label).strip()}" if day_label else ""
    if day_text and date_text.lower().startswith("day "):
        return date_text
    if date_text and day_text:
        return f"{date_text} / {day_text}"
    return date_text or day_text


def _lesson_title(raw) -> str:
    raw = str(raw or "").strip()
    if not raw or raw.upper() in {"N/A", "NA", "NONE"}:
        return ""
    return _fmt_subject(raw)


def _lesson_venue(raw) -> str:
    raw = str(raw or "").strip()
    if not raw or raw.upper() in {"N/A", "NA", "NONE"}:
        return ""
    return _fmt_venue(raw)


def render_timetable(
    class_name,
    lessons,
    date_str,
    day_label,
    weather_text="",
    events_text="",
    user_name="",
):
    """Draw the fixed 8-lesson card and return a seekable PNG stream.

    ``weather_text``, ``events_text`` and ``user_name`` are accepted for
    compatibility with the previous renderer; the new card does not use them.
    """
    lessons = list(lessons or [])
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Outer dark card, then white content panel and header.
    draw.rounded_rectangle((0, 0, W - 1, H - 1), 32, fill=BG)
    draw.rounded_rectangle((40, 140, 860, 940), 12, fill=PANEL)
    draw.rounded_rectangle((40, 40, 635, 120), 12, fill=HEADER)
    draw.rounded_rectangle((660, 40, 860, 120), 12, fill=PANEL)

    for y in BREAK_YS:
        draw.rounded_rectangle((70, y, 830, y + 40), 12, fill=BREAK)

    for y in ROW_YS:
        draw.rounded_rectangle((70, y, 830, y + 60), 12, fill=ROW)
        draw.rounded_rectangle((70, y, 552, y + 60), 12, fill=ROW_LEFT)

    _draw_text(
        draw,
        _header_text(date_str, day_label),
        337.5,
        96.7,
        48,
        500,
        WHITE,
        535,
        min_size=32,
    )
    _draw_text(
        draw,
        str(class_name or "").upper(),
        760,
        96.0,
        48,
        500,
        BLACK,
        160,
        min_size=28,
    )

    break_labels = (
        " ".join(TIME_SLOTS["MA"]),
        " ".join(TIME_SLOTS["BREAK"]),
        " ".join(TIME_SLOTS["LUNCH"]),
    )
    for y, label in zip(BREAK_YS, break_labels):
        _draw_text(draw, label, 450, y + 28.4, 24, 500, WHITE, 720, min_size=16)

    for index, y in enumerate(ROW_YS):
        lesson = lessons[index] if index < len(lessons) else {}
        if isinstance(lesson, dict):
            raw_subject = lesson.get("subject", "")
            raw_venue = lesson.get("venue", "")
        else:
            raw_subject = ""
            raw_venue = ""

        title = _lesson_title(raw_subject)
        venue = _lesson_venue(raw_venue)
        _draw_text(
            draw,
            f"{_slot_time(index + 1)} {title}".strip(),
            311,
            y + 44.7,
            40,
            500,
            SESSION,
            440,
            min_size=20,
        )
        _draw_text(draw, venue, 691, y + 38.4, 24, 500, VENUE, 260, min_size=16)

    _draw_text(draw, "SPYC Siu Ying", 450, 913.4, 24, 400, BLACK, 760, min_size=16)

    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.name = "timetable.png"
    buf.seek(0)
    return buf
