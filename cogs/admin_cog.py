import discord  # type: ignore[reportMissingImports]
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import json
import os
from collections import deque

STATS_FILE = "admin_stats.json"
USER_DATA_FILE = "user_data.json"


def _today():
    return datetime.now().strftime("%Y-%m-%d")


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now()
        self.stats = self._load_stats()
        self.recent_logs = deque(maxlen=200)   # 最近 200 條記錄 (in-memory)

    # ==================== 載入 / 儲存 ====================

    def _load_stats(self):
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"total": 0, "daily": {}, "commands": {}, "users": {}}

    def _save_stats(self):
        try:
            with open(STATS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 儲存統計失敗: {e}")

    def _is_admin(self, interaction: discord.Interaction) -> bool:
        """淨係 server 管理員先用得（私訊入面一律當冇權限）"""
        if isinstance(interaction.user, discord.Member):
            return interaction.user.guild_permissions.administrator
        return False

    # ==================== 自動記錄（核心）====================
    # 呢個 listener 會自動捕捉【所有】slash command，
    # 包括 timetable_cog / qr_cog 入面嘅，唔使逐個改。

    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction, command):
        """每當有人成功用任何 slash command，自動記錄"""
        try:
            now = datetime.now()
            user = interaction.user
            uid = str(user.id)
            uname = str(user)
            gname = interaction.guild.name if interaction.guild else "私訊"

            # 最近記錄 (in-memory)
            self.recent_logs.append(
                f"`{now.strftime('%d/%m %H:%M')}` `/{command.name}` — {uname} @ {gname}"
            )

            # 統計 (存 JSON)
            self.stats["total"] += 1
            key = now.strftime("%Y-%m-%d")
            self.stats["daily"][key] = self.stats["daily"].get(key, 0) + 1
            self.stats["commands"][command.name] = self.stats["commands"].get(command.name, 0) + 1

            u = self.stats["users"].get(uid) or {"name": uname, "uses": 0}
            u["name"] = uname
            u["uses"] += 1
            u["last"] = now.strftime("%d/%m/%Y %H:%M")
            self.stats["users"][uid] = u

            self._save_stats()
        except Exception as e:
            print(f"❌ 記錄指令時出錯: {e}")

    # ==================== 管理員指令 ====================

    @app_commands.command(name="stats", description="🛡️ [管理員] Bot 使用統計總覽")
    async def slash_stats(self, interaction: discord.Interaction):
        if not self._is_admin(interaction):
            await interaction.response.send_message("❌ 呢個係管理員指令，你冇權限用。", ephemeral=True)
            return

        s = self.stats

        # 設定咗班別嘅人數
        setclass_count = 0
        try:
            with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
                setclass_count = len(json.load(f))
        except Exception:
            pass

        total_members = sum(g.member_count or 0 for g in self.bot.guilds)

        # 最多人用嘅指令
        top_cmd, top_count = "—", 0
        if s["commands"]:
            top_cmd, top_count = max(s["commands"].items(), key=lambda x: x[1])
            top_cmd = f"/{top_cmd}"

        # 近 7 日合計
        week = 0
        for i in range(7):
            k = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            week += s["daily"].get(k, 0)

        # 上線時間
        up = datetime.now() - self.start_time
        uptime = f"{up.days}日 {up.seconds // 3600}小時 {(up.seconds % 3600) // 60}分"

        embed = discord.Embed(title="📊 Bot 使用統計", color=discord.Color.blue())
        embed.add_field(name="📈 總指令次數", value=str(s["total"]), inline=True)
        embed.add_field(name="🔥 今日用量", value=str(s["daily"].get(_today(), 0)), inline=True)
        embed.add_field(name="📅 近7日合計", value=str(week), inline=True)
        embed.add_field(name="🆔 用過 bot 嘅人", value=str(len(s["users"])), inline=True)
        embed.add_field(name="📚 設定咗班別", value=str(setclass_count), inline=True)
        embed.add_field(name="🖥️ 伺服器", value=f"{len(self.bot.guilds)} 個", inline=True)
        embed.add_field(name="👥 伺服器總人數", value=str(total_members), inline=True)
        embed.add_field(name="🏆 最多人用", value=f"{top_cmd}（{top_count} 次）", inline=True)
        embed.set_footer(text=f"⏱️ 上線 {uptime} | 🏓 Ping {round(self.bot.latency * 1000)}ms")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="stats_daily", description="🛡️ [管理員] 每日用量走勢")
    @app_commands.describe(days="顯示幾多日 (3-30，預設 14)")
    async def slash_stats_daily(self, interaction: discord.Interaction, days: app_commands.Range[int, 3, 30] = 14):
        if not self._is_admin(interaction):
            await interaction.response.send_message("❌ 呢個係管理員指令。", ephemeral=True)
            return

        counts = []
        for i in range(days - 1, -1, -1):
            d = datetime.now() - timedelta(days=i)
            counts.append((d, self.stats["daily"].get(d.strftime("%Y-%m-%d"), 0)))

        max_n = max((n for _, n in counts), default=0) or 1
        lines = []
        for d, n in counts:
            bar = "█" * max(1, round(n / max_n * 15)) if n > 0 else "·"
            lines.append(f"`{d.strftime('%d/%m')}` {bar} **{n}**")

        embed = discord.Embed(
            title=f"📈 每日指令用量（近 {days} 日）",
            description="\n".join(lines),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="stats_commands", description="🛡️ [管理員] 指令用量排行")
    async def slash_stats_commands(self, interaction: discord.Interaction):
        if not self._is_admin(interaction):
            await interaction.response.send_message("❌ 呢個係管理員指令。", ephemeral=True)
            return

        cmds = sorted(self.stats["commands"].items(), key=lambda x: x[1], reverse=True)
        if not cmds:
            await interaction.response.send_message("仲冇任何使用記錄。", ephemeral=True)
            return

        max_n = cmds[0][1] or 1
        lines = []
        for i, (name, n) in enumerate(cmds[:15], 1):
            bar = "█" * max(1, round(n / max_n * 12))
            lines.append(f"`#{i:<2}` `/{name}` {bar} **{n}**")

        embed = discord.Embed(
            title="🏆 指令用量排行",
            description="\n".join(lines),
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="stats_users", description="🛡️ [管理員] 最活躍用戶排行")
    async def slash_stats_users(self, interaction: discord.Interaction):
        if not self._is_admin(interaction):
            await interaction.response.send_message("❌ 呢個係管理員指令。", ephemeral=True)
            return

        users = sorted(self.stats["users"].items(), key=lambda kv: kv[1]["uses"], reverse=True)[:10]
        if not users:
            await interaction.response.send_message("仲冇任何使用記錄。", ephemeral=True)
            return

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, (uid, u) in enumerate(users, 1):
            rank = medals[i - 1] if i <= 3 else f"`#{i}`"
            lines.append(f"{rank} **{u['name']}** — {u['uses']} 次（最後：{u.get('last', '?')}）")

        embed = discord.Embed(
            title="👤 最活躍用戶 Top 10",
            description="\n".join(lines),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="logs", description="🛡️ [管理員] 最近指令記錄")
    @app_commands.describe(count="顯示幾多條 (5-20，預設 10)")
    async def slash_logs(self, interaction: discord.Interaction, count: app_commands.Range[int, 5, 20] = 10):
        if not self._is_admin(interaction):
            await interaction.response.send_message("❌ 呢個係管理員指令。", ephemeral=True)
            return

        if not self.recent_logs:
            await interaction.response.send_message("仲冇任何記錄（bot 啱啱重啟？）。", ephemeral=True)
            return

        logs = list(self.recent_logs)[-count:][::-1]  # 最新排最上

        embed = discord.Embed(
            title=f"📜 最近 {len(logs)} 條指令記錄（新→舊）",
            description="\n".join(logs)[:4000],
            color=discord.Color.dark_grey()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="stats_export", description="🛡️ [管理員] 匯出統計數據 (JSON)")
    async def slash_stats_export(self, interaction: discord.Interaction):
        if not self._is_admin(interaction):
            await interaction.response.send_message("❌ 呢個係管理員指令。", ephemeral=True)
            return

        if not os.path.exists(STATS_FILE):
            self._save_stats()
        await interaction.response.send_message(
            "📦 完整統計數據：",
            file=discord.File(STATS_FILE),
            ephemeral=True
        )


# ============================================================
# 冇咗佢就會 NoEntryPointError！
# ============================================================
async def setup(bot):
    await bot.add_cog(AdminCog(bot))