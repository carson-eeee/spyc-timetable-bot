import discord
from datetime import datetime

# ============================================================
# 時間表設定 - 你可以改呢度啲時間
# ============================================================
TIME_SLOTS = {
    "MA":    ("8:10",  "早會"),
    "L1":    ("8:40",  None),
    "L2":    ("9:35",  None),
    "BREAK": ("10:30", "小息"),
    "L3":    ("10:45", None),
    "L4":    ("11:40", None),
    "LUNCH": ("12:35", "午膳"),
    "L5":    ("13:50", None),
    "L6":    ("14:45", None),
    "L7":    ("15:35", None),
    "L8":    ("16:30", None),
}

# 科目中英文對照
SUBJECT_NAMES = {
    "MATH": "數學", "ENG": "英國語文", "CHIN": "中國語文",
    "SCI": "科學", "PE": "體育", "HIST": "歷史",
    "GEOG": "地理", "VA": "視覺藝術", "MUS": "音樂",
    "RS": "宗教", "CHIS": "中史", "DE": "設計與科技",
    "ICT": "資訊與通訊科技", "CTP": "班主任課",
    "BAFS": "企業、會計與財務概論", "BIO": "生物",
    "CHEM": "化學", "PHY": "物理", "ECON": "經濟",
    "CS": "電腦", "CES": "公民與社會教育",
    "CLIT": "中國文學", "TH": "旅遊與款待",
    "SCI.PHY": "物理", "SCI.CHEM": "化學", "SCI.BIO": "生物",
    "M1": "數學延伸1", "M2": "數學延伸2",
}

def _fmt_subject(subject_raw):
    """格式化科目：選修淨顯示 [nX]，其他加中文名"""
    subject = subject_raw.strip()
    
    # 提取 [nX] 選修標記
    if subject.startswith("[") and "]" in subject:
        end = subject.index("]") + 1
        return subject[:end]  # 淨係 return [nX]
    
    # 如果包含 /，表示分組上課，攞第一個
    if " / " in subject:
        parts = [p.strip() for p in subject.split(" / ")]
        unique = []
        for p in parts:
            if p not in unique:
                unique.append(p)
        subject = unique[0] if unique else subject
    
    # 搵中文名
    cn = SUBJECT_NAMES.get(subject.upper(), "")
    if cn and cn != subject:
        return f"{cn} ({subject})"
    return subject

def _fmt_venue(venue_raw):
    """格式化地點，去重"""
    venue = venue_raw.strip()
    if " / " in venue:
        parts = [p.strip() for p in venue.split(" / ")]
        unique = []
        for p in parts:
            if p not in unique:
                unique.append(p)
        venue = " / ".join(unique)
    return venue

def _build_schedule_text(lessons):
    """建立時間表文字"""
    lines = []
    
    # 早會
    ma_time, ma_name = TIME_SLOTS["MA"]
    lines.append(f"------{ma_time} {ma_name}------")
    
    for i, lesson in enumerate(lessons, 1):
        # 檢查係咪要插入小息 / 午膳
        if i == 3:
            bt, bn = TIME_SLOTS["BREAK"]
            lines.append(f"------{bt} {bn}------")
        elif i == 5:
            lt, ln = TIME_SLOTS["LUNCH"]
            lines.append(f"------{lt} {ln}------")
        
        # 課堂時間
        slot_key = f"L{i}"
        if slot_key in TIME_SLOTS:
            time_str, _ = TIME_SLOTS[slot_key]
        else:
            time_str = f"L{i}"
        
        subject = _fmt_subject(lesson.get("subject", "N/A"))
        venue = _fmt_venue(lesson.get("venue", "N/A"))
        
        lines.append(f"{time_str} {subject} {venue}")
    
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

def create_timetable_embed(class_name, lessons, events_data=None, user=None, date_obj=None):
    """Create timetable embed matching Siu Ying v2 style"""
    embed = discord.Embed(color=discord.Color.dark_grey())
    
    # Author
    icon_url = None
    if user and hasattr(user, 'display_avatar'):
        icon_url = user.display_avatar.url
    embed.set_author(name="SPYC Siu Ying", icon_url=icon_url)
    
    # Title
    embed.title = f"📅 Timetable for {class_name}"
    
    # Date + Day
    if date_obj:
        dt = date_obj
    else:
        dt = datetime.now()
    
    day = "?"
    if events_data and events_data.get("cycleDay"):
        day = events_data.get("cycleDay").replace("Day ", "").strip()
    
    date_str = dt.strftime(f"%a, %d %b %Y (Day {day})")
    embed.description = f"**{date_str}**\n\n"
    
    # 時間表內容
    if lessons:
        schedule = _build_schedule_text(lessons)
        embed.description += f"```{schedule}```"
    else:
        embed.description += "❌ 搵唔到時間表數據"
    
    # Events
    events_text = _build_events_text(events_data)
    if events_text:
        embed.add_field(name="Events", value=events_text, inline=False)
    
    # Footer
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
        name="📌 Slash Commands",
        value=(
            "`/timetable <班別>` - 查詢今日時間表\n"
            "`/timetable <班別> <Day>` - 查詢指定日時間表\n"
            "`/today [班別]` - 查詢今日時間表+活動\n"
            "`/events [日期]` - 查詢學校活動\n"
            "`/setclass <班別>` - 設定預設班別\n"
            "`/myclass` - 顯示已設定班別\n"
            "`/help` - 顯示此幫助"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📝 例子",
        value=(
            "`/timetable 1A` - 查詢1A班今日\n"
            "`/timetable 1A A` - 查詢1A班Day A\n"
            "`/today 2B` - 查詢2B班今日\n"
            "`/setclass 1A` - 設定預設班別為1A"
        ),
        inline=False
    )
    
    embed.set_footer(text="Made with ❤️ for SPYC students")
    return embed