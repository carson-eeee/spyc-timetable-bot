import discord
from datetime import datetime

def create_timetable_embed(class_name, day, lessons, events_data=None):
    """Create a beautiful embed for timetable display"""
    embed = discord.Embed(
        title=f"📚 {class_name} 時間表 - Day {day}",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    if not lessons:
        embed.description = "❌ 搵唔到時間表數據"
        return embed
    
    # Build timetable text
    timetable_text = ""
    for i, lesson in enumerate(lessons, 1):
        subject = lesson.get("subject", "N/A")
        venue = lesson.get("venue", "N/A")
        
        # Format subject and venue
        subject = subject.replace(" / ", "\n   ├ ")
        venue = venue.replace(" / ", "\n   ├ ")
        
        timetable_text += f"**第{i}堂**\n"
        timetable_text += f"📖 {subject}\n"
        timetable_text += f"📍 {venue}\n\n"
    
    embed.description = timetable_text
    
    # Add events info if available
    if events_data:
        cycle = events_data.get("cycle", "")
        cycle_day = events_data.get("cycleDay", "")
        if cycle and cycle_day:
            embed.set_footer(text=f"{cycle} | {cycle_day}")
    
    return embed

def create_today_embed(class_name, lessons, events_data):
    """Create embed for today's combined view"""
    embed = discord.Embed(
        title=f"📅 今日時間表 - {class_name}",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    
    today = datetime.now().strftime("%Y年%m月%d日")
    embed.set_author(name=today)
    
    if events_data:
        cycle = events_data.get("cycle", "")
        cycle_day = events_data.get("cycleDay", "")
        if cycle and cycle_day:
            embed.add_field(
                name="🔄 循環週",
                value=f"{cycle} - {cycle_day}",
                inline=False
            )
        
        # Add special events/remarks
        slots = events_data.get("slots", {})
        special_events = []
        
        for slot_name, slot_data in slots.items():
            remarks = slot_data.get("remarks", [])
            if remarks and any(r.strip() for r in remarks):
                special_events.append(f"**{slot_name}**: {', '.join(remarks)}")
        
        if special_events:
            embed.add_field(
                name="📢 特別事項",
                value="\n".join(special_events[:5]),
                inline=False
            )
    
    # Timetable
    if lessons:
        timetable_text = ""
        for i, lesson in enumerate(lessons, 1):
            subject = lesson.get("subject", "N/A")
            venue = lesson.get("venue", "N/A")
            timetable_text += f"**L{i}**: {subject} @ {venue}\n"
        
        embed.add_field(
            name="📚 課堂",
            value=timetable_text[:1024],
            inline=False
        )
    else:
        embed.add_field(
            name="📚 課堂",
            value="今日冇課堂數據",
            inline=False
        )
    
    return embed

def create_events_embed(date_str, events_data):
    """Create embed for events display"""
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
            "`/timetable <班別> [Day]` - 查詢時間表\n"
            "`/today <班別>` - 查詢今日時間表+活動\n"
            "`/events [日期]` - 查詢學校活動\n"
            "`/setclass <班別>` - 設定預設班別\n"
            "`/myclass` - 顯示已設定班別\n"
            "`/help` - 顯示此幫助"
        ),
        inline=False
    )
    
    embed.add_field(
        name="💬 Mention Commands",
        value=(
            "`@Bot timetable <班別> [Day]` - 查詢時間表\n"
            "`@Bot today <班別>` - 查詢今日\n"
            "`@Bot events [日期]` - 查詢活動\n"
            "`@Bot help` - 顯示幫助"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📝 例子",
        value=(
            "`/timetable 1A A` - 查詢1A班Day A\n"
            "`/today 2B` - 查詢2B班今日\n"
            "`/setclass 1A` - 設定預設班別為1A"
        ),
        inline=False
    )
    
    embed.set_footer(text="Made with ❤️ for SPYC students")
    return embed