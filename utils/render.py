import io
import hashlib
from PIL import Image, ImageDraw, ImageFont

from utils.embeds import (
    TIME_SLOTS, BREAK_BEFORE, _slot_time,
    _extract_elective_groups, _fmt_subject, _fmt_venue,
    _build_events_text, _dse_countdown_text,
)

# ---------- 顏色（Discord dark theme）----------
BG       = (23, 25, 28)
PANEL    = (36, 38, 43)
CARD     = (44, 47, 54)
ACCENT   = (114, 137, 218)
TEXT     = (240, 242, 245)
SUBTLE   = (168, 172, 178)
BREAK_BG = (52, 56, 66)
BORDER   = (58, 62, 72)

PALETTE = [
    (88, 101, 242), (235, 69, 158), (255, 159, 64),
    (26, 188, 156), (46, 204, 113), (241, 196, 15),
    (155, 89, 182), (52, 152, 219), (231, 76, 60),
    (127, 140, 141),
]

# Windows / Linux 中文字體
FONTS = [
    "C:/Windows/Fonts/msyh.ttc",      # 微軟雅黑
    "C:/Windows/Fonts/msjh.ttc",      # 微軟正黑
    "C:/Windows/Fonts/arialuni.ttf",  # Arial Unicode
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _font(size):
    for p in FONTS:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _fit(draw, text, size, max_w, min_size=18):
    """字太大就自動縮細到啱位"""
    f = _font(size)
    while size > min_size and draw.textlength(text, font=f) > max_w:
        size -= 1
        f = _font(size)
    return f


def _trunc(draw, text, font, max_w):
    """縮到最細都放唔落就刪字加 …"""
    if draw.textlength(text, font=font) <= max_w:
        return text
    while text and draw.textlength(text + "…", font=font) > max_w:
        text = text[:-1]
    return text + "…"


def _subj_color(s):
    h = hashlib.md5(s.encode("utf-8")).hexdigest()
    return PALETTE[int(h[:2], 16) % len(PALETTE)]


def render_timetable(class_name, lessons, date_str, day_label,
                     weather_text="", events_text="", user_name=""):
    """畫時間表 PNG（大字清晰版），return io.BytesIO"""

    # ---------- ① 先行計高度（layout pass）----------
    W = 1300
    pad = 56
    head_h = 156
    row_h, brk_h = 116, 66

    dse_text = (_dse_countdown_text(class_name) or "").replace("**", "")

    ev_lines = []
    if events_text:
        ev_lines = [l.replace("**", "").strip()
                    for l in events_text.split("\n") if l.strip()][:5]

    n_breaks = sum(1 for i in range(1, len(lessons) + 1) if f"L{i}" in BREAK_BEFORE)

    weather_h = 70 if weather_text else 0
    dse_h = 70 if dse_text else 0
    ma_h = 60
    ev_block = (18 + 46 + 36 * len(ev_lines) + 14) if ev_lines else 0
    footer_h = 64

    H = (pad + head_h + 18 + weather_h + dse_h + 10 + ma_h + 12
         + row_h * len(lessons) + brk_h * n_breaks
         + ev_block + footer_h + pad)

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # ---------- Header ----------
    d.rounded_rectangle([pad, pad, W - pad, pad + head_h], 20, fill=PANEL)
    d.rounded_rectangle([pad, pad, pad + 16, pad + head_h], 8, fill=ACCENT)

    d.text((pad + 44, pad + 26), class_name, font=_font(56), fill=TEXT)
    d.text((pad + 46, pad + 98), date_str, font=_font(26), fill=SUBTLE)

    # Day 徽章（右上角藍色 pill）
    if day_label:
        badge = f"Day {day_label}"
        f_b = _font(30)
        bw = d.textlength(badge, font=f_b)
        bx1 = W - pad - 44 - bw
        d.rounded_rectangle([bx1 - 22, pad + 30, W - pad - 22, pad + 82], 26, fill=ACCENT)
        d.text((bx1, pad + 38), badge, font=f_b, fill=(255, 255, 255))

    y = pad + head_h + 18

    # ---------- 天氣 banner ----------
    if weather_text:
        d.rounded_rectangle([pad, y, W - pad, y + weather_h - 16], 27, fill=(52, 48, 34))
        f = _fit(d, weather_text, 27, W - 2 * pad - 56)
        d.text((pad + 28, y + 16), weather_text, font=f, fill=(255, 222, 120))
        y += weather_h

    # ---------- DSE banner ----------
    if dse_text:
        d.rounded_rectangle([pad, y, W - pad, y + dse_h - 16], 27, fill=(58, 28, 32))
        f = _fit(d, dse_text, 27, W - 2 * pad - 56)
        d.text((pad + 28, y + 16), dse_text, font=f, fill=(255, 165, 165))
        y += dse_h

    y += 10

    # ---------- 早會 ----------
    ma_time, ma_name = TIME_SLOTS["MA"]
    d.rounded_rectangle([pad, y, W - pad, y + ma_h - 18], 21, fill=BREAK_BG)
    label = f"{ma_name}  {ma_time}"
    f = _font(25)
    tw = d.textlength(label, font=f)
    d.text(((W - tw) / 2, y + 10), label, font=f, fill=SUBTLE)
    y += ma_h + 12

    # ---------- 每一堂 ----------
    x0 = pad + 150   # 堂卡左邊界（時間列右邊）

    for i, lesson in enumerate(lessons, 1):
        if f"L{i}" in BREAK_BEFORE:
            bk = BREAK_BEFORE[f"L{i}"]
            bt, bn = TIME_SLOTS[bk]
            emo = "☕" if bk == "BREAK" else "🍱"
            d.rounded_rectangle([pad + 90, y, W - pad - 90, y + brk_h - 14], 26, fill=BREAK_BG)
            label = f"{emo} {bn}  {bt}"
            f = _font(25)
            tw = d.textlength(label, font=f)
            d.text(((W - tw) / 2, y + 12), label, font=f, fill=SUBTLE)
            y += brk_h

        # 時間（左邊）
        d.text((pad + 6, y + row_h // 2 - 20), _slot_time(i), font=_font(28), fill=SUBTLE)

        # 卡
        d.rounded_rectangle([x0, y, W - pad, y + row_h - 16], 18,
                           fill=CARD, outline=BORDER)

        raw = str(lesson.get("subject", "") or "")
        groups = _extract_elective_groups(raw)
        card_h = row_h - 16

        if groups:
            # 選修堂：大隻字顯示組別
            text = " / ".join(groups)
            f = _fit(d, text, 36, (W - pad) - (x0 + 44) - 40)
            d.text((x0 + 44, y + card_h // 2 - 24), text, font=f, fill=TEXT)
        else:
            subj = _fmt_subject(raw or "N/A")
            venue = _fmt_venue(lesson.get("venue", "N/A"))

            # 左邊色條（每科唔同色）
            color = _subj_color(raw or "?")
            d.rounded_rectangle([x0 + 1, y + 1, x0 + 15, y + card_h - 1], 8, fill=color)

            # venue（右對齊）
            f_v = _fit(d, venue, 26, 300)
            venue = _trunc(d, venue, f_v, 300)
            vw = d.textlength(venue, font=f_v)
            d.text((W - pad - 28 - vw, y + card_h // 2 - 16), venue, font=f_v, fill=SUBTLE)

            # subject（大隻字，避開 venue）
            max_subj_w = (W - pad - 28 - vw - 24) - (x0 + 44)
            f_s = _fit(d, subj, 33, max_subj_w)
            subj = _trunc(d, subj, f_s, max_subj_w)
            d.text((x0 + 44, y + card_h // 2 - 20), subj, font=f_s, fill=TEXT)

        y += row_h

    # ---------- Events ----------
    if ev_lines:
        y += 18
        d.text((pad + 8, y), "📌 Events", font=_font(28), fill=(255, 222, 120))
        y += 46
        for ln in ev_lines:
            f = _fit(d, ln, 24, W - 2 * pad - 36)
            d.text((pad + 16, y), _trunc(d, ln, f, W - 2 * pad - 36), font=f, fill=SUBTLE)
            y += 36
        y += 14

    # ---------- Footer ----------
    ft = f"Requested by {user_name} · SPYC Siu Ying"
    f = _font(20)
    fw = d.textlength(ft, font=f)
    d.text(((W - fw) / 2, H - pad - 30), ft, font=f, fill=SUBTLE)

    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return buf