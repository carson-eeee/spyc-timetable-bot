import discord  # type: ignore[reportMissingImports]
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import json
import os

from utils.api import SPYCAPI, _fmt_date
from utils.embeds import (
    create_timetable_embed, create_events_embed, create_help_embed,
    maybe_add_dse, dse_days_left, DSE_EXAM_DATE, _build_events_text,
)
from utils.weather import get_summary
from utils.render import render_timetable

USER_DATA_FILE = "user_data.json"

# ⭐ 文字排第一 = 預設；圖片照樣揀得，但唔係 default
STYLE_CHOICES = [
    app_commands.Choice(name="📝 文字", value="text"),
    app_commands.Choice(name="🖼️ 圖片", value="image"),
]


# ============================================================
# 導航按鈕 View
# ============================================================
class TimetableView(discord.ui.View):
    def __init__(self, api, class_name, current_date, user, image=False):
        super().__init__(timeout=180)  # 3分鐘後過期
        self.api = api
        self.class_name = class_name
        self.current_date = current_date
        self.user = user
        self.image = image

    def _update_buttons(self):
        """更新按鈕顯示日期"""
        date_str = f"{self.current_date.day}/{self.current_date.month}"
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.custom_id == "date_label":
                child.label = date_str

    @discord.ui.button(label="⬅", style=discord.ButtonStyle.primary, custom_id="prev")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_date -= timedelta(days=1)
        await self._update_message(interaction)

    @discord.ui.button(label="📅", style=discord.ButtonStyle.secondary, disabled=True, custom_id="date_label")
    async def date_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass  # Disabled button，淨係用嚟顯示日期

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
        self._update_buttons()

        date_str = _fmt_date(self.current_date)
        events_data = await self.api.get_date_info(date_str)

        if not events_data:
            await interaction.edit_original_response(
                content=f"❌ 搵唔到 {date_str} 嘅數據。", embed=None, view=self)
            return

        icon_url = self.user.display_avatar.url if hasattr(self.user, 'display_avatar') else None
        cycle_day = events_data.get("cycleDay", "")
        if not cycle_day:
            embed = discord.Embed(
                title=f"📅 Timetable for {self.class_name}",
                description=f"**{self.current_date.strftime('%a, %d %b %Y')}**\n\n🏖️ 今日冇課（假期 / 周末）",
                color=discord.Color.dark_grey()
            )
            embed.set_author(name="SPYC Siu Ying", icon_url=icon_url)
            embed.set_footer(text=f"Requested by {self.user.display_name}", icon_url=icon_url)
            maybe_add_dse(embed, self.class_name)
            await interaction.edit_original_response(content=None, embed=embed, view=self)
            return

        day = cycle_day.replace("Day ", "").strip()
        lessons = await self.api.get_class_timetable(self.class_name, day)

        # 🌤️ 天氣
        weather_text = None
        weather_plain = ""
        weather_level = None
        try:
            w = await get_summary()
            weather_level = w["level"]
            weather_text = w["line"] if w["level"] == "OK" else f"{w['line']}\n{w['emoji']} **{w['title']}** — {w['detail']}"
            weather_plain = f"{w['plain']} · {w['title']}"
        except Exception:
            pass

        if self.image:
            buf = render_timetable(
                self.class_name, lessons,
                date_str=self.current_date.strftime("%a, %d %b %Y"),
                day_label=day,
                weather_text=weather_plain,
                events_text=_build_events_text(events_data),
                user_name=self.user.display_name if hasattr(self.user, "display_name") else str(self.user),
            )
            embed = discord.Embed(color=discord.Color.dark_grey())
            embed.set_author(name="SPYC Siu Ying", icon_url=icon_url)
            embed.description = f"**{self.current_date.strftime('%a, %d %b %Y')} (Day {day})**"
            if weather_text:
                embed.description += f"\n\n{weather_text}"
            maybe_add_dse(embed, self.class_name)
            embed.set_image(url="attachment://timetable.png")
            embed.set_footer(text=f"Requested by {self.user.display_name}", icon_url=icon_url)
            await interaction.edit_original_response(
                content=None, embed=embed, view=self,
                attachments=[discord.File(buf, filename="timetable.png")]
            )
        else:
            embed = create_timetable_embed(
                self.class_name, lessons,
                events_data=events_data,
                user=self.user,
                date_obj=self.current_date,
                weather_text=weather_text,
                weather_level=weather_level,
            )
            await interaction.edit_original_response(content=None, embed=embed, view=self)


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

    def _get_user_style(self, user_id):
        """⭐ 文字係預設；user 用 /setclass 揀過就用返佢嗰個"""
        return self.user_data.get(str(user_id), {}).get("style", "text")

    async def cog_unload(self):
        await self.api.close()

    # ==================== SLASH COMMANDS ====================

    @app_commands.command(name="timetable", description="查詢時間表")
    @app_commands.describe(
        class_name="班別 (例如: 1A, 2B)",
        day="星期幾 (A/B/C/D/E，留空=今日)",
        style="顯示方式 (留空=你嘅個人預設)",
    )
    @app_commands.choices(style=STYLE_CHOICES)
    async def slash_timetable(self, interaction: discord.Interaction, class_name: str,
                              day: str = None, style: app_commands.Choice[str] = None):
        await interaction.response.defer()

        # ⭐ 揀顯示方式：指令參數 > 個人預設 > text
        chosen = style.value if style else self._get_user_style(interaction.user.id)
        use_image = (chosen == "image")

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

            if use_image:
                try:
                    w = await get_summary()
                    weather_plain = f"{w['plain']} · {w['title']}"
                except Exception:
                    weather_plain = ""
                buf = render_timetable(
                    class_name, lessons,
                    date_str=f"Day {day}",
                    day_label=day,
                    weather_text=weather_plain,
                    user_name=interaction.user.display_name,
                )
                embed = discord.Embed(title=f"📅 Timetable for {class_name}",
                                      color=discord.Color.dark_grey())
                icon_url = interaction.user.display_avatar.url if hasattr(interaction.user, 'display_avatar') else None
                embed.set_author(name="SPYC Siu Ying", icon_url=icon_url)
                embed.set_image(url="attachment://timetable.png")
                embed.set_footer(text=f"Requested by {interaction.user.display_name}",
                                 icon_url=icon_url)
                await interaction.followup.send(
                    embed=embed, file=discord.File(buf, filename="timetable.png"))
            else:
                embed = create_timetable_embed(class_name, lessons, user=interaction.user)
                await interaction.followup.send(embed=embed)
            return

        # 冇指定 Day：顯示今日 + 按鈕
        today = datetime.now()
        date_str = _fmt_date(today)
        events_data = await self.api.get_date_info(date_str)

        if not events_data:
            await interaction.followup.send("❌ 無法獲取今日資訊。")
            return

        cycle_day = events_data.get("cycleDay", "")
        icon_url = interaction.user.display_avatar.url if hasattr(interaction.user, 'display_avatar') else None

        if not cycle_day:
            embed = discord.Embed(
                title=f"📅 Timetable for {class_name}",
                description=f"**{today.strftime('%a, %d %b %Y')}**\n\n🏖️ 今日冇課（假期 / 周末）",
                color=discord.Color.dark_grey()
            )
            embed.set_author(name="SPYC Siu Ying", icon_url=icon_url)
            embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=icon_url)
            maybe_add_dse(embed, class_name)
            view = TimetableView(self.api, class_name, today, interaction.user, image=use_image)
            view._update_buttons()
            await interaction.followup.send(embed=embed, view=view)
            return

        day = cycle_day.replace("Day ", "").strip()
        lessons = await self.api.get_class_timetable(class_name, day)

        # 🌤️ 天氣
        weather_text = None
        weather_plain = ""
        weather_level = None
        try:
            w = await get_summary()
            weather_level = w["level"]
            weather_text = w["line"] if w["level"] == "OK" else f"{w['line']}\n{w['emoji']} **{w['title']}** — {w['detail']}"
            weather_plain = f"{w['plain']} · {w['title']}"
        except Exception:
            pass

        if use_image:
            buf = render_timetable(
                class_name, lessons,
                date_str=today.strftime("%a, %d %b %Y"),
                day_label=day,
                weather_text=weather_plain,
                events_text=_build_events_text(events_data),
                user_name=interaction.user.display_name,
            )
            embed = discord.Embed(color=discord.Color.dark_grey())
            embed.set_author(name="SPYC Siu Ying", icon_url=icon_url)
            embed.description = f"**{today.strftime('%a, %d %b %Y')} (Day {day})**"
            if weather_text:
                embed.description += f"\n\n{weather_text}"
            maybe_add_dse(embed, class_name)
            embed.set_image(url="attachment://timetable.png")
            embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=icon_url)
            view = TimetableView(self.api, class_name, today, interaction.user, image=True)
            view._update_buttons()
            await interaction.followup.send(
                embed=embed, file=discord.File(buf, filename="timetable.png"), view=view)
        else:
            embed = create_timetable_embed(
                class_name, lessons,
                events_data=events_data,
                user=interaction.user,
                date_obj=today,
                weather_text=weather_text,
                weather_level=weather_level,
            )
            view = TimetableView(self.api, class_name, today, interaction.user, image=False)
            view._update_buttons()
            await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name="today", description="查詢今日時間表+活動")
    @app_commands.describe(
        class_name="班別 (例如: 1A, 2B，留空用預設)",
        style="顯示方式 (留空=你嘅個人預設)",
    )
    @app_commands.choices(style=STYLE_CHOICES)
    async def slash_today(self, interaction: discord.Interaction,
                          class_name: str = None, style: app_commands.Choice[str] = None):
        await interaction.response.defer()

        chosen = style.value if style else self._get_user_style(interaction.user.id)
        use_image = (chosen == "image")

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
        icon_url = interaction.user.display_avatar.url if hasattr(interaction.user, 'display_avatar') else None

        if not cycle_day:
            embed = discord.Embed(
                title=f"📅 Timetable for {class_name}",
                description=f"**{today.strftime('%a, %d %b %Y')}**\n\n🏖️ 今日冇課（假期 / 周末）",
                color=discord.Color.dark_grey()
            )
            embed.set_author(name="SPYC Siu Ying", icon_url=icon_url)
            embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=icon_url)
            maybe_add_dse(embed, class_name)
            view = TimetableView(self.api, class_name, today, interaction.user, image=use_image)
            view._update_buttons()
            await interaction.followup.send(embed=embed, view=view)
            return

        day = cycle_day.replace("Day ", "").strip()
        lessons = await self.api.get_class_timetable(class_name, day)

        weather_text = None
        weather_plain = ""
        weather_level = None
        try:
            w = await get_summary()
            weather_level = w["level"]
            weather_text = w["line"] if w["level"] == "OK" else f"{w['line']}\n{w['emoji']} **{w['title']}** — {w['detail']}"
            weather_plain = f"{w['plain']} · {w['title']}"
        except Exception:
            pass

        if use_image:
            buf = render_timetable(
                class_name, lessons,
                date_str=today.strftime("%a, %d %b %Y"),
                day_label=day,
                weather_text=weather_plain,
                events_text=_build_events_text(events_data),
                user_name=interaction.user.display_name,
            )
            embed = discord.Embed(color=discord.Color.dark_grey())
            embed.set_author(name="SPYC Siu Ying", icon_url=icon_url)
            embed.description = f"**{today.strftime('%a, %d %b %Y')} (Day {day})**"
            if weather_text:
                embed.description += f"\n\n{weather_text}"
            maybe_add_dse(embed, class_name)
            embed.set_image(url="attachment://timetable.png")
            embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=icon_url)
            view = TimetableView(self.api, class_name, today, interaction.user, image=True)
            view._update_buttons()
            await interaction.followup.send(
                embed=embed, file=discord.File(buf, filename="timetable.png"), view=view)
        else:
            embed = create_timetable_embed(
                class_name, lessons,
                events_data=events_data,
                user=interaction.user,
                date_obj=today,
                weather_text=weather_text,
                weather_level=weather_level,
            )
            view = TimetableView(self.api, class_name, today, interaction.user, image=False)
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

    @app_commands.command(name="dse", description="DSE 倒數")
    async def slash_dse(self, interaction: discord.Interaction):
        days = dse_days_left()
        date_str = f"{DSE_EXAM_DATE.day}/{DSE_EXAM_DATE.month}/{DSE_EXAM_DATE.year}"

        embed = discord.Embed(color=discord.Color.red())
        icon_url = interaction.user.display_avatar.url if hasattr(interaction.user, 'display_avatar') else None
        embed.set_author(name="SPYC Siu Ying", icon_url=icon_url)
        embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=icon_url)

        if days > 0:
            stage = (
                "😌 仲有排，慢慢嚟" if days > 100 else
                "📚 係時候 plan 溫書時間表喇" if days > 50 else
                "🔥 溫書模式 ON" if days > 20 else
                "⚡ 最後衝刺階段" if days > 7 else
                "💪 好近喇，早啲瞓養好精神"
            )
            embed.title = "🎯 DSE 倒數"
            embed.description = (
                f"**DSE 開考日：{date_str}**（首日筆試：中國語文 📖）\n\n"
                f"仲有 **{days} 日** ⏳\n{stage}"
            )
        elif days == 0:
            embed.title = "🎯 DSE 今日開考！"
            embed.description = "深呼吸，正常發揮就得！加油！🎉"
        else:
            embed.title = "🎯 DSE"
            embed.description = f"DSE 已喺 {date_str} 開考，加油撐住！💪"

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="setclass", description="設定預設班別＋顯示方式")
    @app_commands.describe(
        class_name="班別 (例如: 1A, 2B)",
        style="時間表顯示方式 (預設: 文字)",
    )
    @app_commands.choices(style=STYLE_CHOICES)
    async def slash_setclass(self, interaction: discord.Interaction, class_name: str,
                            style: app_commands.Choice[str] = None):
        class_name = class_name.upper()

        timetable = await self.api.fetch_timetable()
        if timetable and class_name not in timetable:
            classes = ", ".join(sorted(timetable.keys()))
            await interaction.response.send_message(f"❌ 搵唔到 `{class_name}` 班。可用班別: {classes}")
            return

        uid = str(interaction.user.id)
        if uid not in self.user_data:
            self.user_data[uid] = {}
        self.user_data[uid]["class"] = class_name

        if style is not None:
            self.user_data[uid]["style"] = style.value
        else:
            self.user_data[uid].setdefault("style", "text")

        self._save_user_data()

        style_label = "🖼️ 圖片" if self.user_data[uid]["style"] == "image" else "📝 文字"
        await interaction.response.send_message(
            f"✅ 已設定：班別 `{class_name}` · 顯示方式 {style_label}"
        )

    @app_commands.command(name="myclass", description="顯示已設定嘅班別")
    async def slash_myclass(self, interaction: discord.Interaction):
        info = self.user_data.get(str(interaction.user.id), {})
        user_class = info.get("class")
        if user_class:
            style_label = "🖼️ 圖片" if info.get("style", "text") == "image" else "📝 文字"
            await interaction.response.send_message(
                f"📚 你嘅預設班別係 `{user_class}`，顯示方式：{style_label}。\n"
                f"想轉？用 `/setclass <班別> style:` 或者 `/timetable style:`。"
            )
        else:
            await interaction.response.send_message("❌ 你仲未設定班別，用 `/setclass <班別>` 設定。")

    @app_commands.command(name="help", description="顯示幫助")
    async def slash_help(self, interaction: discord.Interaction):
        embed = create_help_embed()
        await interaction.response.send_message(embed=embed)


# ============================================================
# 冇咗佢就會 NoEntryPointError！
# ============================================================
async def setup(bot):
    await bot.add_cog(TimetableCog(bot))