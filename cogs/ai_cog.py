import os
import time
import asyncio
import discord  # type: ignore[reportMissingImports]
from discord import app_commands
from discord.ext import commands

from utils.ai import ask_ai, gemini_available, nim_available, default_provider

MAX_PER_HOUR = 10   # 每人每鐘頭問幾多次


class AICog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.asks = {}   # uid -> [timestamps]

        # 🛡️ .env 超級管理員 bypass rate limit
        self.admin_ids = set()
        for part in (os.getenv("ADMIN_IDS") or "").split(","):
            part = part.strip()
            if part.isdigit():
                self.admin_ids.add(int(part))

    def _rate_check(self, uid, is_admin):
        """限流：超額 return 要等幾多秒，否則記錄並 return 0"""
        if is_admin:
            return 0
        now = time.time()
        lst = [t for t in self.asks.get(uid, []) if now - t < 3600]
        if len(lst) >= MAX_PER_HOUR:
            return max(0.0, 3600 - (now - lst[0]))
        lst.append(now)
        self.asks[uid] = lst
        return 0

    @app_commands.command(name="ask", description="🤖 問 AI 助手 (Gemini / NVIDIA NIM)")
    @app_commands.describe(
        question="你想問嘅問題",
        provider="AI 引擎 (預設: 自動)",
        model="自訂模型名 (進階，留空=預設)",
    )
    @app_commands.choices(provider=[
        app_commands.Choice(name="自動 (有咩用咩)", value="auto"),
        app_commands.Choice(name="Google Gemini", value="gemini"),
        app_commands.Choice(name="NVIDIA NIM", value="nim"),
    ])
    async def slash_ask(
        self,
        interaction: discord.Interaction,
        question: str,
        provider: app_commands.Choice[str] = None,
        model: str = None,
    ):
        await interaction.response.defer()

        # 揀引擎
        prov = provider.value if provider else "auto"
        if prov == "auto":
            prov = default_provider()

        # 限流
        wait = self._rate_check(str(interaction.user.id), interaction.user.id in self.admin_ids)
        if wait > 0:
            await interaction.followup.send(
                f"⏳ 慢住！你今個鐘已經問咗 {MAX_PER_HOUR} 次，"
                f"等大約 {int(wait // 60) + 1} 分鐘再嚟啦。"
            )
            return

        if prov is None:
            gem = "✅" if gemini_available() else "❌"
            nim = "✅" if nim_available() else "❌"
            await interaction.followup.send(
                "❌ 個 bot 未設定任何 AI API key！\n"
                f"Google Gemini {gem} · NVIDIA NIM {nim}\n"
                "叫 bot 擁有者喺 `.env` 加 `GEMINI_API_KEY` 或 `NIM_API_KEY`。"
            )
            return

        if prov == "gemini" and not gemini_available():
            await interaction.followup.send("❌ 冇 Gemini API key，用 `/ask` 揀 NIM，或者叫 admin 設定 `.env`。")
            return
        if prov == "nim" and not nim_available():
            await interaction.followup.send("❌ 冇 NVIDIA NIM API key，用 `/ask` 揀 Gemini，或者叫 admin 設定 `.env`。")
            return

        start = time.time()
        try:
            answer, model_label = await asyncio.to_thread(ask_ai, question, prov, model)
        except RuntimeError as e:
            msg = str(e)
            if msg == "NO_PROVIDER":
                await interaction.followup.send("❌ 冇可用嘅 AI 引擎。")
            else:
                await interaction.followup.send(f"❌ AI 出錯：`{msg[:500]}`")
            return
        except Exception as e:
            await interaction.followup.send(f"❌ AI 出錯：`{str(e)[:500]}`")
            return
        elapsed = time.time() - start

        # 起 embed
        embed = discord.Embed(color=discord.Color.green())
        embed.set_author(
            name="🤖 AI 助手",
            icon_url=interaction.user.display_avatar.url if hasattr(interaction.user, "display_avatar") else None
        )
        q = question if len(question) <= 150 else question[:150] + "..."
        embed.description = f"💬 **{q}**\n\n{answer[:3800]}"

        prov_emoji = "✨" if prov == "gemini" else "🟩"
        embed.set_footer(
            text=f"{prov_emoji} {model_label} · {elapsed:.1f}s · 每小時限 {MAX_PER_HOUR} 次"
        )
        await interaction.followup.send(embed=embed)


# 冇咗佢就會 NoEntryPointError！
async def setup(bot):
    await bot.add_cog(AICog(bot))