import discord  # type: ignore[reportMissingImports]
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import json
import os

from utils.api import SPYCAPI, _fmt_date
from utils.embeds import create_timetable_embed, create_events_embed, create_help_embed

USER_DATA_FILE = "user_data.json"

# ============================================================
# 導航按鈕 View
# ============================================================
class TimetableView(discord.ui.View):
    def __init__(self, api, class_name, current_date, user):
        super().__init__(timeout=180)  # 3分鐘後過期
        self.api = api
        self.class_name = class_name
        self.current_date = current_date
        self.user = user

    def _update_buttons(self):
        """更新按鈕顯示日期"""
        date_str = self.current_date.strftime("%d/%m")
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.custom_id == "date_label":
                child.label = date_str

    @discord.ui.button(label="⬅", style=discord.ButtonStyle.primary, custom_id="prev")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_date -= timedelta(days=1)
        await self._update_message(interaction)

    @discord.ui.button(label="05/09", style=discord.ButtonStyle.secondary, disabled=True, custom_id="date_label")
    async def date_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass  # Disabled button, just for display

    @discord.ui.button(label="➡", style=discord.ButtonStyle.primary, custom_id="next")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_date += timedelta(days=1)
        await self._update_message(interaction)

    @discord.ui.button(label="今日", style=discord.ButtonStyle.success, custom_id="today")
    async def today_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_date = datetime.now()
        await self._update_message(interaction)

    async def _update_message(self, interaction):
        """更新訊息內容"""
        date_str = _fmt_date(self.current_date)
        events_data = await self.api.get_date_info(date_str)

        if not events_data:
            await interaction.edit_original_response(
                content=f"❌ 搵唔到 {date_str} 嘅數據。",
                embed=None,
                view=self
            )
            self._update_buttons()
            return

        cycle_day = events_data.get("cycleDay", "")
        if not cycle_day:
            # 冇課（假期/周末）
            embed = discord.Embed(
                title=f"📅 Timetable for {self.class_name}",
                description=f"**{self.current_date.strftime('%a, %d %b %Y')}**\n\n🏖️ 今日冇課（假期 / 周末）",
                color=discord.Color.dark_grey()
            )
            icon_url = self.user.display_avatar.url if hasattr(self.user, 'display_avatar') else None
            embed.set_author(name="SPYC Siu Ying", icon_url=icon_url)
            embed.set_footer(text=f"Requested by {self.user.display_name}", icon_url=icon_url)

            await interaction.edit_original_response(content=None, embed=embed, view=self)
            self._update_buttons()
            return

        day = cycle_day.replace("Day ", "").strip()
        lessons = await self.api.get_class_timetable(self.class_name, day)

        embed = create_timetable_embed(
            self.class_name, lessons,
            events_data=events_data,
            user=self.user,
            date_obj=self.current_date
        )

        await interaction.edit_original_response(content=None, embed=embed, view=self)
        self._update_buttons()


class TimetableCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api = SPYCAPI()
        self.user_data = self._load_user_data()

    def _load_user_data(self):
        if os.path.exists(USER_DATA_FILE):
            try:
                with open(USER_DATA_FILE, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_user_data(self):
        with open(USER_DATA_FILE, "w") as f:
            json.dump(self.user_data, f, indent=2)

    def _get_user_class(self, user_id):
        return self.user_data.get(str(user_id), {}).get("class", None)

    async def cog_unload(self):
        await self.api.close()

    # ==================== SLASH COMMANDS ====================

    @app_commands.command(name="timetable", description="查詢時間表")
    @app_commands.describe(
        class_name="班別 (例如: 1A, 2B)",
        day="星期幾 (A/B/C/D/E，留空=今日)"
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
            # 指定 Day，唔使按鈕
            day = day.upper()
            if day not in timetable[class_name]:
                days = ", ".join(sorted(timetable[class_name].keys()))
                await interaction.followup.send(f"❌ 搵唔到 Day `{day}`。可用: {days}")
                return

            lessons = timetable[class_name][day]
            embed = create_timetable_embed(class_name, lessons, user=interaction.user)
            await interaction.followup.send(embed=embed)
        else:
            # 冇指定 Day，顯示今日 + 按鈕
            today = datetime.now()
            date_str = _fmt_date(today)
            events_data = await self.api.get_date_info(date_str)

            if not events_data:
                await interaction.followup.send("❌ 無法獲取今日資訊。")
                return

            cycle_day = events_data.get("cycleDay", "")
            if not cycle_day:
                # 冇課
                embed = discord.Embed(
                    title=f"📅 Timetable for {class_name}",
                    description=f"**{today.strftime('%a, %d %b %Y')}**\n\n🏖️ 今日冇課（假期 / 周末）",
                    color=discord.Color.dark_grey()
                )
                icon_url = interaction.user.display_avatar.url if hasattr(interaction.user, 'display_avatar') else None
                embed.set_author(name="SPYC Siu Ying", icon_url=icon_url)
                embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=icon_url)

                view = TimetableView(self.api, class_name, today, interaction.user)
                view._update_buttons()
                await interaction.followup.send(embed=embed, view=view)
                return

            day = cycle_day.replace("Day ", "").strip()
            lessons = await self.api.get_class_timetable(class_name, day)

            embed = create_timetable_embed(
                class_name, lessons,
                events_data=events_data,
                user=interaction.user,
                date_obj=today
            )

            view = TimetableView(self.api, class_name, today, interaction.user)
            view._update_buttons()
            await interaction.followup.send(embed=embed, view=view)

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
        today = datetime.now()
        date_str = _fmt_date(today)
        events_data = await self.api.get_date_info(date_str)

        if not events_data:
            await interaction.followup.send("❌ 無法獲取今日資訊。")
            return

        cycle_day = events_data.get("cycleDay", "")
        if not cycle_day:
            embed = discord.Embed(
                title=f"📅 Timetable for {class_name}",
                description=f"**{today.strftime('%a, %d %b %Y')}**\n\n🏖️ 今日冇課（假期 / 周末）",
                color=discord.Color.dark_grey()
            )
            icon_url = interaction.user.display_avatar.url if hasattr(interaction.user, 'display_avatar') else None
            embed.set_author(name="SPYC Siu Ying", icon_url=icon_url)
            embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=icon_url)

            view = TimetableView(self.api, class_name, today, interaction.user)
            view._update_buttons()
            await interaction.followup.send(embed=embed, view=view)
            return

        day = cycle_day.replace("Day ", "").strip()
        lessons = await self.api.get_class_timetable(class_name, day)

        embed = create_timetable_embed(
            class_name, lessons,
            events_data=events_data,
            user=interaction.user,
            date_obj=today
        )

        view = TimetableView(self.api, class_name, today, interaction.user)
        view._update_buttons()
        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name="events", description="查詢學校活動")
    @app_commands.describe(date="日期 (格式: D/M/YYYY，留空=今日)")
    async def slash_events(self, interaction: discord.Interaction, date: str = None):
        await interaction.response.defer()

        if date is None:
            date = _fmt_date(datetime.now())

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

        # 驗證班別係咪存在
        timetable = await self.api.fetch_timetable()
        if timetable and class_name not in timetable:
            classes = ", ".join(sorted(timetable.keys()))
            await interaction.response.send_message(f"❌ 搵唔到 `{class_name}` 班。可用班別: {classes}")
            return

        user_id = str(interaction.user.id)
        if user_id not in self.user_data:
            self.user_data[user_id] = {}
        self.user_data[user_id]["class"] = class_name
        self._save_user_data()

        await interaction.response.send_message(f"✅ 已設定你嘅預設班別為 `{class_name}`！")

    @app_commands.command(name="myclass", description="顯示已設定嘅班別")
    async def slash_myclass(self, interaction: discord.Interaction):
        user_class = self._get_user_class(interaction.user.id)
        if user_class:
            await interaction.response.send_message(f"📚 你嘅預設班別係 `{user_class}`。")
        else:
            await interaction.response.send_message("❌ 你仲未設定班別，用 `/setclass <班別>` 設定。")

    @app_commands.command(name="help", description="顯示幫助")
    async def slash_help(self, interaction: discord.Interaction):
        embed = create_help_embed()
        await interaction.response.send_message(embed=embed)


# ============================================================
# 呢個係最重要嘅部分！冇咗佢就會 NoEntryPointError
# ============================================================
async def setup(bot):
    await bot.add_cog(TimetableCog(bot))