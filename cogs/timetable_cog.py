import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import json
import os

from utils.api import SPYCAPI
from utils.embeds import create_timetable_embed, create_today_embed, create_events_embed, create_help_embed

USER_DATA_FILE = "user_data.json"

class TimetableCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api = SPYCAPI()
        self.user_data = self._load_user_data()

    def _load_user_data(self):
        """Load user class preferences"""
        if os.path.exists(USER_DATA_FILE):
            try:
                with open(USER_DATA_FILE, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_user_data(self):
        """Save user class preferences"""
        with open(USER_DATA_FILE, "w") as f:
            json.dump(self.user_data, f)

    def _get_user_class(self, user_id):
        """Get user's preferred class"""
        return self.user_data.get(str(user_id), {}).get("class", None)

    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        self.bot.loop.create_task(self.api.close())

    # ==================== SLASH COMMANDS ====================

    @app_commands.command(name="timetable", description="查詢時間表")
    @app_commands.describe(
        class_name="班別 (例如: 1A, 2B)",
        day="星期幾 (A/B/C/D/E，留空顯示全部)"
    )
    async def slash_timetable(self, interaction: discord.Interaction, class_name: str, day: str = None):
        await interaction.response.defer()

        class_name = class_name.upper()
        timetable = await self.api.fetch_timetable()

        if not timetable:
            await interaction.followup.send("❌ 無法連接到時間表伺服器，請稍後再試。")
            return

        if class_name not in timetable:
            classes = ", ".join(sorted(timetable.keys()))
            await interaction.followup.send(f"❌ 搵唔到 `{class_name}` 班。可用班別: {classes}")
            return

        if day:
            day = day.upper()
            if day not in timetable[class_name]:
                days = ", ".join(sorted(timetable[class_name].keys()))
                await interaction.followup.send(f"❌ 搵唔到 Day `{day}`。可用: {days}")
                return

            lessons = timetable[class_name][day]
            embed = create_timetable_embed(class_name, day, lessons)
            await interaction.followup.send(embed=embed)
        else:
            # Show all days
            embeds = []
            for d in sorted(timetable[class_name].keys()):
                lessons = timetable[class_name][d]
                embed = create_timetable_embed(class_name, d, lessons)
                embeds.append(embed)

            # Send first embed
            await interaction.followup.send(embed=embeds[0])

            # Send remaining embeds
            for embed in embeds[1:]:
                await interaction.followup.send(embed=embed)

    @app_commands.command(name="today", description="查詢今日時間表+活動")
    @app_commands.describe(class_name="班別 (例如: 1A, 2B，留空用預設)")
    async def slash_today(self, interaction: discord.Interaction, class_name: str = None):
        await interaction.response.defer()

        if class_name is None:
            class_name = self._get_user_class(interaction.user.id)
            if class_name is None:
                await interaction.followup.send("❌ 請提供班別，或者先用 `/setclass` 設定預設班別。")
                return

        class_name = class_name.upper()

        # Get today's cycle day from events
        today_info = await self.api.get_today_info()
        if not today_info:
            await interaction.followup.send("❌ 無法獲取今日循環週資訊。")
            return

        cycle_day = today_info.get("cycleDay", "")
        if not cycle_day:
            await interaction.followup.send("❌ 今日冇循環日資訊（可能係假期）。")
            return

        # Extract day letter (e.g., "Day A" -> "A")
        day = cycle_day.replace("Day ", "").strip()

        # Get timetable
        lessons = await self.api.get_class_timetable(class_name, day)

        embed = create_today_embed(class_name, lessons, today_info)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="events", description="查詢學校活動")
    @app_commands.describe(date="日期 (格式: D/M/YYYY，留空=今日)")
    async def slash_events(self, interaction: discord.Interaction, date: str = None):
        await interaction.response.defer()

        if date is None:
            date = datetime.now().strftime("%-d/%-m/%Y")

        events = await self.api.get_day_events(date)

        if not events:
            await interaction.followup.send(f"❌ 搵唔到 {date} 嘅活動數據。")
            return

        embed = create_events_embed(date, events)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="setclass", description="設定預設班別")
    @app_commands.describe(class_name="班別 (例如: 1A, 2B)")
    async def slash_setclass(self, interaction: discord.Interaction, class_name: str):
        class_name = class_name.upper()

        # Validate class exists
        timetable = await self.api.fetch_timetable()
        if timetable and class_name not in timetable:
            classes = ", ".join(sorted(timetable.keys()))
            await interaction.response.send_message(f"❌ 搵唔到 `{class_name}` 班。可用班別: {classes}")
            return

        self.user_data[str(interaction.user.id)] = {"class": class_name}
        self._save_user_data()

        await interaction.response.send_message(f"✅ 已設定預設班別為 **{class_name}**！之後用 `/today` 唔使再輸入班別。")

    @app_commands.command(name="myclass", description="顯示已設定班別")
    async def slash_myclass(self, interaction: discord.Interaction):
        user_class = self._get_user_class(interaction.user.id)
        if user_class:
            await interaction.response.send_message(f"📌 你嘅預設班別係 **{user_class}**。")
        else:
            await interaction.response.send_message("❌ 你未設定預設班別。用 `/setclass <班別>` 設定。")

    @app_commands.command(name="help", description="顯示使用指南")
    async def slash_help(self, interaction: discord.Interaction):
        embed = create_help_embed()
        await interaction.response.send_message(embed=embed)

    # ==================== MENTION COMMANDS ====================

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle mention commands (@Bot ...)"""
        if message.author.bot:
            return

        # Check if bot is mentioned
        if self.bot.user not in message.mentions:
            return

        # Remove mentions from content
        content = message.content
        for mention in message.mentions:
            content = content.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "")
        content = content.strip().lower()

        if not content:
            await message.reply("👋 你好！用 `@Bot help` 睇吓有咩指令可以用。")
            return

        args = content.split()
        command = args[0] if args else ""

        if command in ["timetable", "tt", "時間表"]:
            await self._handle_mention_timetable(message, args[1:])
        elif command in ["today", "今日"]:
            await self._handle_mention_today(message, args[1:])
        elif command in ["events", "活動"]:
            await self._handle_mention_events(message, args[1:])
        elif command in ["help", "幫助", "?"]:
            embed = create_help_embed()
            await message.reply(embed=embed)
        else:
            await message.reply("🤔 唔識呢個指令。用 `@Bot help` 睇吓有咩可以用。")

    async def _handle_mention_timetable(self, message, args):
        """Handle @Bot timetable <class> [day]"""
        if not args:
            await message.reply("❌ 用法: `@Bot timetable <班別> [Day]`\n例子: `@Bot timetable 1A A`")
            return

        class_name = args[0].upper()
        day = args[1].upper() if len(args) > 1 else None

        timetable = await self.api.fetch_timetable()
        if not timetable:
            await message.reply("❌ 無法連接到時間表伺服器。")
            return

        if class_name not in timetable:
            classes = ", ".join(sorted(timetable.keys()))
            await message.reply(f"❌ 搵唔到 `{class_name}` 班。可用班別: {classes}")
            return

        if day:
            if day not in timetable[class_name]:
                days = ", ".join(sorted(timetable[class_name].keys()))
                await message.reply(f"❌ 搵唔到 Day `{day}`。可用: {days}")
                return

            lessons = timetable[class_name][day]
            embed = create_timetable_embed(class_name, day, lessons)
            await message.reply(embed=embed)
        else:
            # Show all days
            for d in sorted(timetable[class_name].keys()):
                lessons = timetable[class_name][d]
                embed = create_timetable_embed(class_name, d, lessons)
                await message.reply(embed=embed)

    async def _handle_mention_today(self, message, args):
        """Handle @Bot today [class]"""
        if args:
            class_name = args[0].upper()
        else:
            class_name = self._get_user_class(message.author.id)
            if class_name is None:
                await message.reply("❌ 請提供班別，或者先用 `@Bot setclass <班別>` 設定預設班別。")
                return

        today_info = await self.api.get_today_info()
        if not today_info:
            await message.reply("❌ 無法獲取今日循環週資訊。")
            return

        cycle_day = today_info.get("cycleDay", "")
        if not cycle_day:
            await message.reply("❌ 今日冇循環日資訊（可能係假期）。")
            return

        day = cycle_day.replace("Day ", "").strip()
        lessons = await self.api.get_class_timetable(class_name, day)

        embed = create_today_embed(class_name, lessons, today_info)
        await message.reply(embed=embed)

    async def _handle_mention_events(self, message, args):
        """Handle @Bot events [date]"""
        if args:
            date = args[0]
        else:
            date = datetime.now().strftime("%-d/%-m/%Y")

        events = await self.api.get_day_events(date)
        if not events:
            await message.reply(f"❌ 搵唔到 {date} 嘅活動數據。")
            return

        embed = create_events_embed(date, events)
        await message.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(TimetableCog(bot))
