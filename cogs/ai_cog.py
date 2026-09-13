import os
import time
import asyncio
import discord  # type: ignore[reportMissingImports]
from discord import app_commands
from discord.ext import commands

from utils.ai import (
    ask_ai, gemini_available, nim_available, default_provider,
    fetch_nim_models, current_nim_model,
)

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

    # ==================== /ask ====================

    @app_commands.command(name="ask", description="🤖 問 AI 助手 (Gemini / NVIDIA NIM)")
    @app_commands.describe(
        question="你想問嘅問題",
        provider="AI 引擎 (預設: 自動)",
        model="自訂模型名 (NIM 唔啱用會自動轉模型)",
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

        # 🔄 偵測有冇自動轉咗模型
        note = ""
        if model:
            actual = model_label.split(" · ", 1)[-1]
            if actual != model:
                note = (f"\n\nℹ️ 你揀嘅 `{model}` 已唔再提供服務，"
                        f"已自動改用 `{actual}`。用 `/aimodels` 睇晒可用模型。")

        # 起 embed
        embed = discord.Embed(color=discord.Color.green())
        embed.set_author(
            name="🤖 AI 助手",
            icon_url=interaction.user.display_avatar.url if hasattr(interaction.user, "display_avatar") else None
        )
        q = question if len(question) <= 150 else question[:150] + "..."
        embed.description = f"💬 **{q}**{note}\n\n{answer[:3600]}"

        prov_emoji = "✨" if prov == "gemini" else "🟩"
        embed.set_footer(
            text=f"{prov_emoji} {model_label} · {elapsed:.1f}s · 每小時限 {MAX_PER_HOUR} 次"
        )
        await interaction.followup.send(embed=embed)

    # ==================== /aimodels ====================

    @app_commands.command(name="aimodels", description="📋 查看 AI 引擎狀態同 NIM 可用模型")
    @app_commands.describe(refresh="強制重新整理 NIM 模型列表 (預設: 用 cache)")
    async def slash_aimodels(self, interaction: discord.Interaction, refresh: bool = False):
        await interaction.response.defer()

        embed = discord.Embed(title="📋 AI 引擎狀態", color=discord.Color.blurple())

        # 引擎狀態
        gem = "✅ 已設定" if gemini_available() else "❌ 未設定"
        nim = "✅ 已設定" if nim_available() else "❌ 未設定"
        prov = default_provider() or "無"
        embed.add_field(
            name="🔌 引擎",
            value=(
                f"✨ Google Gemini：{gem}\n"
                f"🟩 NVIDIA NIM：{nim}\n"
                f"🎯 目前優先使用：`{prov}`"
            ),
            inline=False
        )

        # NIM 模型列表
        if nim_available():
            models = await asyncio.to_thread(fetch_nim_models, refresh)
            using = current_nim_model() or "（未用過）"

            if models:
                # 標記而家用緊嗰個
                shown = []
                for m in models[:40]:
                    mark = "🟢 " if m == using else "• "
                    shown.append(f"{mark}`{m}`")
                extra = "" if len(models) <= 40 else f"\n…仲有 {len(models) - 40} 個"
                embed.add_field(
                    name=f"🟩 NVIDIA NIM 模型（{len(models)} 個可用）",
                    value="\n".join(shown)[:1020] + extra,
                    inline=False
                )
                embed.add_field(
                    name="🎯 而家用緊",
                    value=f"`{using}`\n"
                          f"模型唔再提供服務嗰陣，bot 會自動轉用其他模型。"
                          f"想指定模型：`/ask model:模型名`",
                    inline=False
                )
            else:
                embed.add_field(
                    name="🟩 NVIDIA NIM 模型",
                    value="⚠️ 暫時攞唔到模型列表，用緊預設模型。\n"
                          "試 `/aimodels refresh: True` 強制重新整理。",
                    inline=False
                )
        else:
            embed.add_field(
                name="🟩 NVIDIA NIM",
                value="未設定 `NIM_API_KEY`，想用 NIM 就叫 bot 擁有者去 `.env` 加 key。\n"
                      "免費 key 申請：build.nvidia.com",
                inline=False
            )

        embed.set_footer(
            text="NIM 模型列表每小時自動更新 · 🟢 = 而家用緊",
            icon_url=interaction.user.display_avatar.url if hasattr(interaction.user, 'display_avatar') else None
        )
        await interaction.followup.send(embed=embed)


# 冇咗佢就會 NoEntryPointError！
async def setup(bot):
    await bot.add_cog(AICog(bot))