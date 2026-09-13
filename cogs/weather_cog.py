import discord  # type: ignore[reportMissingImports]
from discord import app_commands
from discord.ext import commands
from datetime import datetime

from utils.weather import (
    get_summary, fetch_forecast, fetch_9day, fetch_hourly_shatin,
    fetch_tips, extract_tips, parse_hourly, OM_CODE_EMOJI,
)


class WeatherCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== 🌤️ 現時天氣 ====================

    @app_commands.command(name="weather", description="🌤️ 香港現時天氣＋返學狀態")
    async def slash_weather(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            s = await get_summary()
            tips = extract_tips(await fetch_tips())
        except Exception:
            await interaction.followup.send("❌ 攞唔到天氣資料，請稍後再試。")
            return

        if s["level"] == "STOP":
            color = discord.Color.red()
        elif s["level"] == "CAUTION":
            color = discord.Color.gold()
        else:
            color = discord.Color.blue()

        embed = discord.Embed(title="🌤️ 香港現時天氣", color=color)
        embed.description = f"{s['line']}\n\n{s['emoji']} **{s['title']}**\n{s['detail']}"

        # 詳細資料（有先顯示）
        details = []
        if s["uv"] is not None:
            uv_line = f"UV {s['uv']}"
            if s["uv_desc"]:
                uv_line += f"（{s['uv_desc']}）"
            details.append(f"🕶️ 紫外線：{uv_line}")
        if s["wind"]:
            details.append(f"💨 風：{s['wind']}")
        if s["rain_max"] is not None:
            details.append(f"🌧️ 過去一小時最高雨量：{s['rain_max']} mm")
        if details:
            embed.add_field(name="📊 詳細", value="\n".join(details), inline=False)

        if s["warnings"]:
            embed.add_field(
                name="⚠️ 生效中警告",
                value="\n".join(f"• {w}" for w in s["warnings"])[:1024],
                inline=False
            )
        if tips:
            embed.add_field(
                name="📢 特別天氣提示",
                value="\n".join(f"• {t}" for t in tips)[:1024],
                inline=False
            )

        footer = f"資料來源：{s['source'] or '香港天文台'}"
        if s["updated"]:
            footer += f" · 更新於 {s['updated']}"
        embed.set_footer(text=footer)
        await interaction.followup.send(embed=embed)

    # ==================== ⏰ 逐小時預報（沙田）====================

    @app_commands.command(name="hourly", description="⏰ 沙田未來12小時逐小時預報")
    @app_commands.describe(hours="顯示幾多個鐘 (4-24，預設 12)")
    async def slash_hourly(self, interaction: discord.Interaction,
                           hours: app_commands.Range[int, 4, 24] = 12):
        await interaction.response.defer()

        data = await fetch_hourly_shatin()
        rows = parse_hourly(data, hours)

        if not rows:
            await interaction.followup.send("❌ 攞唔到逐小時預報，請稍後再試。")
            return

        lines = []
        for r in rows:
            emoji = OM_CODE_EMOJI.get(r["code"], "🌡️")
            temp = f"{r['temp']:.0f}°C" if r["temp"] is not None else "—"
            rain = f"{r['rain']}%" if r["rain"] is not None else "—"
            lines.append(f"`{r['time'].strftime('%H:%M')}` {emoji} **{temp}** · ☔ {rain}")

        embed = discord.Embed(
            title=f"⏰ 沙田未來 {len(rows)} 小時",
            description="\n".join(lines),
            color=discord.Color.blue()
        )
        embed.set_footer(text="📍 沙田 · 資料來源：Open-Meteo · ☔ = 降雨機率")
        await interaction.followup.send(embed=embed)

    # ==================== 📆 9日預報 ====================

    @app_commands.command(name="forecast", description="📆 九日天氣預報")
    async def slash_forecast(self, interaction: discord.Interaction):
        await interaction.response.defer()

        flw = await fetch_forecast()
        fnd = await fetch_9day()

        if not fnd or not fnd.get("weatherForecast"):
            await interaction.followup.send("❌ 攞唔到預報資料，請稍後再試。")
            return

        embed = discord.Embed(title="📆 九日天氣預報", color=discord.Color.blue())

        # 天氣概況
        gs = (flw or {}).get("generalSituation", "")
        if gs:
            embed.description = f"📖 **天氣概況**\n{gs[:400]}"

        for fc in fnd.get("weatherForecast", [])[:9]:
            # 日期
            try:
                dt = datetime.strptime(fc.get("forecastDate", ""), "%Y%m%d")
                date_label = f"{dt.day}/{dt.month}"
            except ValueError:
                date_label = fc.get("forecastDate", "?")
            week = (fc.get("week") or "").replace("星期", "")
            name = f"📅 {date_label}" + (f" ({week})" if week else "")

            weather = fc.get("forecastWeather", "")
            try:
                mx = fc["forecastMaxtemp"]["value"]
                mn = fc["forecastMintemp"]["value"]
                temp_str = f"🌡️ {mn}–{mx}°C"
            except (KeyError, TypeError):
                temp_str = "🌡️ —"
            psr = fc.get("PSR", "")

            embed.add_field(
                name=name,
                value=f"{weather}\n{temp_str}\n☔ 雨率：{psr or '—'}",
                inline=True
            )

        embed.set_footer(text="資料來源：香港天文台 · ☔ 雨率 = 顯著降雨機會（低/中/高）")
        await interaction.followup.send(embed=embed)

    # ==================== 🏫 返學判斷 ====================

    @app_commands.command(name="school", description="🏫 而家使唔使返學？（根據天氣警告判斷）")
    async def slash_school(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            s = await get_summary()
        except Exception:
            await interaction.followup.send("❌ 攞唔到天氣資料，請稍後再試。")
            return

        if s["level"] == "STOP":
            color = discord.Color.red()
        elif s["level"] == "CAUTION":
            color = discord.Color.gold()
        else:
            color = discord.Color.green()

        embed = discord.Embed(
            title=f"{s['emoji']} {s['title']}",
            description=s["detail"],
            color=color
        )
        if s["warnings"]:
            embed.add_field(
                name="⚠️ 生效中警告",
                value="\n".join(f"• {w}" for w in s["warnings"])[:1024],
                inline=False
            )
        embed.set_footer(text="🔔 僅供參考，最終請以教育局／學校公佈為準")
        await interaction.followup.send(embed=embed)


# 冇咗佢就會 NoEntryPointError！
async def setup(bot):
    await bot.add_cog(WeatherCog(bot))