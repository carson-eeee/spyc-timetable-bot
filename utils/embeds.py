import discord
import re
from datetime import datetime

# ============================================================
# ⏰ 上堂時間（最新版）
# ============================================================
TIME_SLOTS = {
    "MA":    ("8:10",          "早會"),
    "L1":    ("8:35",  None),
    "L2":    ("9:15",  None),
    "L3":    ("9:55",  None),
    "BREAK": ("10:35 - 11:00", "小息"),
    "L4":    ("11:00", None),
    "L5":    ("11:40", None),
    "L6":    ("12:20", None),
    "LUNCH": ("13:00 - 14:20", "午膳"),
    "L7":    ("14:20", None),
    "L8":    ("15:00", None),
}

# ☕🍱 小息/午膳插喺邊堂之前
BREAK_BEFORE = {
    "L4": "BREAK",   # ☕ 小息（第4堂前）
    "L7": "LUNCH",   # 🍱 午膳（第7堂前）
}

# ============================================================
# 🎯 DSE 倒數設定
# DSE 2027 筆試：2027年4月8日 中國語文科率先開考
# ============================================================
DSE_EXAM_DATE = datetime(2027, 4, 8)

# S6 班別 (6A / 6B / 6C...)
S6_CLASS_RE = re.compile(r"^6[A-Z]$")

# 科目中英文對照
SUBJECT_NAMES = {
    "MATH": "數學", "ENG": "英國語文", "CHIN": "中國語文",
    "SCI": "科學", "PE": "體育", "HIST": "歷史",
    "GEOG": "地理", "VA": "視覺藝術", "MUS": "音樂",
    "RS": "宗教", "CHIS": "中史", "DE": "設計與科技",
    "ICT": "資訊與通訊科技", "CTP": "班主任課",
    "BAFS": "企業、會計與財務概論", "BIO": "生物",
    "CHEM": "化學", "PHY": "物理", "ECON": "經濟",
    "CS": "公民與社會", "CLIT": "中國文學", "TH": "旅遊與款待",
    "SCI.PHY": "物理", "SCI.CHEM": "化學", "SCI.BIO": "生物",
    "M1": "數學延伸1", "M2": "數學延伸2",
}

# 揀選修組別標記：[1X] / 1X 呢啲格式都認得
ELECTIVE_RE = re.compile(r"\[(\dX)\]|(?<!\w)(\dX)(?!\w)", re.IGNORECASE)

# ============================================================
# 🎯 DSE 倒數
# ============================================================
def dse_days_left():
    """距離 DSE 開考仲有幾多日（負數 = 已開考）"""
    today = datetime.now()
    return (DSE_EXAM_DATE.date() - today.date()).days

def _dse_countdown_text(class_name):
    """S6 班顯示 DSE 倒數，其他班 return None"""
    if not S6_CLASS_RE.match(class_name or ""):
        return None
    days = dse_days_left()
    date_str = f"{DSE_EXAM_DATE.day}/{DSE_EXAM_DATE.month}/{DSE_EXAM_DATE.year}"
    if days > 0:
        return f"🎯 **DSE 倒數：仲有 {days} 日開考**（{date_str} 中文科開考）"
    if days == 0:
        return "🎯 **今日就係 DSE 開考日，加油！**"
    if days > -30:
        return "🔥 **DSE 考試進行中，撐住呀！**"
    return None

def maybe_add_dse(embed, class_name):
    """S6 班嘅 embed 自動加 DSE 倒數行"""
    text = _dse_countdown_text(class_name)
    if text:
        embed.description = (embed.description or "") + f"\n\n{text}"
    return embed

# ============================================================
# 格式化 functions
# ============================================================
def _extract_elective_groups(subject_raw):
    """抽出選修組別標記 (1X / 2X / 3X)"""
    subject = str(subject_raw or "")
    if not subject:
        return []
    groups = []
    for m in ELECTIVE_RE.finditer(subject):
        g = (m.group(1) or m.group(2)).upper()
        if g and g not in groups:
            groups.append(g)
    return groups

def _fmt_subject(subject_raw):
    """格式化科目：選修淨係顯示組別 (1X/2X/3X)，其他加中文名"""
    subject = str(subject_raw or "").strip()

    groups = _extract_elective_groups(subject)
    if groups:
        return " / ".join(groups)

    if " / " in subject:
        parts = [p.strip() for p in subject.split(" / ")]
        unique = []
        for p in parts:
            if p not in unique:
                unique.append(p)
        subject = unique[0] if unique else subject

    cn = SUBJECT_NAMES.get(subject.upper(), "")
    if cn and cn != subject:
        return f"{cn} ({subject})"
    return subject

def _fmt_venue(venue_raw):
    """格式化地點，去重"""
    venue = str(venue_raw or "").strip()
    if " / " in venue:
        parts = [p.strip() for p in venue.split(" / ")]
        unique = []
        for p in parts:
            if p not in unique:
                unique.append(p)
        venue = " / ".join(unique)
    return venue

def _slot_time(i):
    """攞第 i 堂嘅開始時間"""
    slot = TIME_SLOTS.get(f"L{i}")
    return slot[0] if slot else f"L{i}"

def _build_schedule_text(lessons):
    """建立時間表文字（唔用 code block）"""
    lines = []

    ma_time, ma_name = TIME_SLOTS["MA"]
    lines.append(f"**{ma_time}** {ma_name}")

    for i, lesson in enumerate(lessons, 1):
        slot_key = f"L{i}"

        if slot_key in BREAK_BEFORE:
            break_key = BREAK_BEFORE[slot_key]
            bt, bn = TIME_SLOTS[break_key]
            emoji = "☕" if break_key == "BREAK" else "🍱"
            lines.append(f"{emoji} **{bt} {bn}**")

        time_str = _slot_time(i)
        raw = str(lesson.get("subject", "") or "")

        if _extract_elective_groups(raw):
            lines.append(f"**{time_str}** " + " / ".join(_extract_elective_groups(raw)))
        else:
            subject = _fmt_subject(raw or "N/A")
            venue = _fmt_venue(lesson.get("venue", "N/A"))
            lines.append(f"**{time_str}** {subject} · {venue}")

    return "\n".join(lines)

def _build_events_text(events_data):
    """建立 Events 文字"""
    if not events_data:
        return ""

    lines = []
    slots = events_data.get("slots", {})

    for slot_name, slot_data in slots.items():
        remarks = slot_data.get("remarks", [])
        admin_remarks = slot_data.get("admin_remarks", [])
        all_remarks = remarks + admin_remarks

        if all_remarks and any(r.strip() for r in all_remarks):
            val = ", ".join([r.strip() for r in all_remarks if r.strip()])
            if slot_name == "CTP":
                lines.append(f"**Class Teacher Period**: {val}")
            else:
                lines.append(f"**{slot_name}**: {val}")

    return "\n".join(lines)

# ============================================================
# Embed builders
# ============================================================
def create_timetable_embed(class_name, lessons, events_data=None, user=None,
                           date_obj=None, weather_text=None, weather_level=None):
    """Create timetable embed matching Siu Ying v2 style"""
    # 🌤️ 停課=紅 / 留意=金 / 正常=深灰
    if weather_level == "STOP":
        color = discord.Color.red()
    elif weather_level == "CAUTION":
        color = discord.Color.gold()
    else:
        color = discord.Color.dark_grey()
    embed = discord.Embed(color=color)

    icon_url = None
    if user and hasattr(user, 'display_avatar'):
        icon_url = user.display_avatar.url
    embed.set_author(name="SPYC Siu Ying", icon_url=icon_url)

    embed.title = f"📅 Timetable for {class_name}"

    if date_obj:
        dt = date_obj
    else:
        dt = datetime.now()

    day = "?"
    if events_data and events_data.get("cycleDay"):
        day = events_data.get("cycleDay").replace("Day ", "").strip()

    date_str = dt.strftime(f"%a, %d %b %Y (Day {day})")
    embed.description = f"**{date_str}**\n\n"

    if lessons:
        schedule = _build_schedule_text(lessons)
        embed.description += schedule
    else:
        embed.description += "❌ 搵唔到時間表數據"

    # 🌤️ 天氣（新加）
    if weather_text:
        embed.description += f"\n\n{weather_text}"

    # 🎯 S6 班自動加 DSE 倒數
    maybe_add_dse(embed, class_name)

    events_text = _build_events_text(events_data)
    if events_text:
        embed.add_field(name="Events", value=events_text, inline=False)

    if user and hasattr(user, 'display_name'):
        embed.set_footer(
            text=f"Requested by {user.display_name}",
            icon_url=user.display_avatar.url if hasattr(user, 'display_avatar') else None
        )

    return embed

def create_events_embed(date_str, events_data):
    """Create events embed"""
    embed = discord.Embed(
        title=f"📅 學校活動 - {date_str}",
        color=discord.Color.orange(),
        timestamp=datetime.now()
    )

    if not events_data:
        embed.description = "❌ 搵唔到活動數據"
        return embed

    cycle = events_data.get("cycle", "")
    cycle_day = events_data.get("cycleDay", "")

    if cycle:
        embed.add_field(name="🔄 循環週", value=cycle, inline=True)
    if cycle_day:
        embed.add_field(name="📆 循環日", value=cycle_day, inline=True)

    slots = events_data.get("slots", {})
    for slot_name, slot_data in slots.items():
        remarks = slot_data.get("remarks", [])
        admin_remarks = slot_data.get("admin_remarks", [])
        all_remarks = remarks + admin_remarks

        if all_remarks and any(r.strip() for r in all_remarks):
            value = "\n".join([f"• {r}" for r in all_remarks if r.strip()])
            embed.add_field(
                name=f"⏰ {slot_name}",
                value=value[:1024],
                inline=False
            )

    if len(embed.fields) <= 2:
        embed.add_field(
            name="📋 活動",
            value="今日冇特別活動",
            inline=False
        )

    return embed

def create_help_embed():
    """Create help embed"""
    embed = discord.Embed(
        title="🤖 SPYC 時間表 Bot 使用指南",
        description="幫你快速查詢沙田培英書院時間表！",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="📅 時間表",
        value=(
            "`/timetable <班別> [Day] [style]` - 查詢時間表\n"
            "`/today [班別] [style]` - 今日時間表+活動\n"
            "`/events [日期]` - 查詢學校活動\n"
            "`/dse` - DSE 倒數"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🌤️ 天氣",
        value=(
            "`/weather` - 現時天氣＋返學狀態\n"
            "`/hourly [小時]` - ⏰ 沙田逐小時預報\n"
            "`/forecast` - 📆 九日預報\n"
            "`/school` - 而家使唔使返學？"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🤖 AI & 其他",
        value=(
            "`/ask <問題>` - 問 AI 助手\n"
            "`/aimodels` - 📋 查看 AI 模型狀態\n"
            "`/qr <文字>` - 產生 QR code\n"
            "`/avatar [用戶]` - 查看頭像\n"
            "`/userinfo [用戶]` / `/serverinfo` - 用戶/伺服器資料"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚙️ 設定 & 意見",
        value=(
            "`/setclass <班別> [style]` - 設定班別＋顯示方式\n"
            "`/myclass` - 顯示設定\n"
            "`/feedback <意見>` - 📮 匿名意見箱\n"
            "`/help` - 顯示此幫助"
        ),
        inline=False
    )
    
    embed.set_footer(text="Made with ❤️ for SPYC students")
    return embed