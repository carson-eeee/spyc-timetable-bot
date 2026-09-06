import discord  # type: ignore[reportMissingImports]
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import json
import os
from collections import deque

STATS_FILE = "admin_stats.json"
USER_DATA_FILE = "user_data.json"
BLACKLIST_FILE = "blacklist.json"
FEEDBACK_FILE = "feedback.json"


def _today():
    return datetime.now().strftime("%Y-%m-%d")


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now()
        self.stats = self._load_stats()
        self.recent_logs = deque(maxlen=200)   # 最近 200 條記錄 (in-memory)
        self.blacklist = self._load_json(BLACKLIST_FILE, {})
        self.feedback = self._load_json(
            FEEDBACK_FILE,
            {"next_id": 1, "channel_id": None, "entries": []},
        )

        # ============================================================
        # 🚫 全局封鎖 hook
        # Patch 咗 CommandTree 嘅 interaction_check：
        # 任何人用任何 slash command 之前都會先行呢個 check，
        # 喺黑名單入面嘅人即刻被彈開（連 /help 都用唔到）。
        # ============================================================
        self.bot.tree.interaction_check = self._blacklist_check

        # 吞埋「global interaction check failed」嗰啲 traceback，
        # 唔係嘅話每次封鎖人，console 都會印一大舊紅字
        _orig_tree_on_error = self.bot.tree.on_error

        async def _quiet_tree_on_error(interaction, error):
            if isinstance(error, app_commands.CheckFailure):
                return  # 已經喺 check 度回覆咗 ephemeral 訊息
            await _orig_tree_on_error(interaction, error)

        self.bot.tree.on_error = _quiet_tree_on_error

    # ==================== 通用 JSON 讀寫 ====================

    def _load_json(self, path, default):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return default

    def _save_json(self, path, data):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 儲存 {path} 失敗: {e}")

    def _load_stats(self):
        return self._load_json(STATS_FILE, {"total": 0, "daily": {}, "commands": {}, "users": {}})

    def _save_stats(self):
        self._save_json(STATS_FILE, self.stats)

    def _is_admin(self, interaction: discord.Interaction) -> bool:
        """淨係 server 管理員先用得（私訊入面一律當冇權限）"""
        if isinstance(interaction.user, discord.Member):
            return interaction.user.guild_permissions.administrator
        return False

    # ==================== 🚫 Blacklist 全局 check ====================

    async def _blacklist_check(self, interaction: discord.Interaction) -> bool:
        try:
            uid = str(interaction.user.id)
            if uid in self.blacklist:
                if interaction.type is discord.InteractionType.application_command:
                    entry = self.blacklist[uid]
                    reason = entry.get("reason", "")
                    msg = "❌ 你已被管理員封鎖，暫時唔可以使用呢個 bot 嘅指令。"
                    if reason:
                        msg += f"\n📝 原因：{reason}"
                    try:
                        await interaction.response.send_message(msg, ephemeral=True)
                    except Exception:
                        pass
                return False
        except Exception:
            return True   # check 自己炸咗都照放行，唔好累埋成個 bot
        return True

    # ==================== 自動記錄（核心）====================

    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction, command):
        """每當有人成功用任何 slash command，自動記錄"""
        try:
            now = datetime.now()
            user = interaction.user
            uid = str(user.id)
            uname = str(user)
            gname = interaction.guild.name if interaction.guild else "私訊"

            self.recent_logs.append(
                f"`{now.strftime('%d/%m %H:%M')}` `/{command.name}` — {uname} @ {gname}"
            )

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

    # ==================== 📊 統計指令 ====================

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

        top_cmd, top_count = "—", 0
        if s["commands"]:
            top_cmd, top_count = max(s["commands"].items(), key=lambda x: x[1])
            top_cmd = f"/{top_cmd}"

        week = 0
        for i in range(7):
            k = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            week += s["daily"].get(k, 0)

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

    # ==================== 🚫 Blacklist 指令 ====================

    @app_commands.command(name="blacklist_add", description="🛡️ [管理員] 封鎖用戶")
    @app_commands.describe(user="要封鎖嘅用戶", reason="原因 (可選)")
    async def slash_blacklist_add(self, interaction: discord.Interaction, user: discord.User, reason: str = None):
        if not self._is_admin(interaction):
            await interaction.response.send_message("❌ 呢個係管理員指令。", ephemeral=True)
            return

        if user.id == interaction.user.id:
            await interaction.response.send_message("😂 唔可以封鎖你自己喎。", ephemeral=True)
            return

        uid = str(user.id)
        if uid in self.blacklist:
            await interaction.response.send_message(f"⚠️ {user.mention} 已經喺封鎖名單入面。", ephemeral=True)
            return

        self.blacklist[uid] = {
            "name": str(user),
            "reason": reason or "",
            "by": str(interaction.user),
            "at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
        self._save_json(BLACKLIST_FILE, self.blacklist)

        extra = f"（原因：{reason}）" if reason else ""
        await interaction.response.send_message(
            f"🚫 已封鎖 {user.mention}{extra}。佢而家用唔到呢個 bot 嘅任何指令。",
            ephemeral=True
        )

    @app_commands.command(name="blacklist_remove", description="🛡️ [管理員] 解封用戶")
    @app_commands.describe(user="要解封嘅用戶")
    async def slash_blacklist_remove(self, interaction: discord.Interaction, user: discord.User):
        if not self._is_admin(interaction):
            await interaction.response.send_message("❌ 呢個係管理員指令。", ephemeral=True)
            return

        uid = str(user.id)
        if uid not in self.blacklist:
            await interaction.response.send_message(f"⚠️ {user.mention} 本來就唔喺封鎖名單入面。", ephemeral=True)
            return

        del self.blacklist[uid]
        self._save_json(BLACKLIST_FILE, self.blacklist)
        await interaction.response.send_message(f"✅ 已解封 {user.mention}，佢可以返嚟用指令喇。", ephemeral=True)

    @app_commands.command(name="blacklist_list", description="🛡️ [管理員] 查看封鎖名單")
    async def slash_blacklist_list(self, interaction: discord.Interaction):
        if not self._is_admin(interaction):
            await interaction.response.send_message("❌ 呢個係管理員指令。", ephemeral=True)
            return

        if not self.blacklist:
            await interaction.response.send_message("📭 封鎖名單係空嘅，世界和平 🕊️", ephemeral=True)
            return

        lines = []
        for uid, e in self.blacklist.items():
            reason = e.get("reason") or "無"
            lines.append(f"🚫 **{e['name']}**\n　原因：{reason} · 由 {e['by']} 於 {e['at']} 封鎖")

        embed = discord.Embed(
            title=f"🚫 封鎖名單（{len(self.blacklist)} 人）",
            description="\n".join(lines)[:4000],
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ==================== 📮 意見箱 ====================

    @app_commands.command(name="feedback", description="📮 遞交意見／建議俾管理員")
    @app_commands.describe(message="你嘅意見", anonymous="匿名遞交 (預設: 匿名)")
    async def slash_feedback(self, interaction: discord.Interaction, message: str, anonymous: bool = True):
        fid = self.feedback["next_id"]
        self.feedback["next_id"] += 1

        entry = {
            "id": fid,
            "message": message[:1500],
            "anonymous": anonymous,
            "user": "匿名" if anonymous else str(interaction.user),
            "user_id": None if anonymous else str(interaction.user.id),
            "time": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "resolved": False,
        }
        self.feedback["entries"].append(entry)
        self._save_json(FEEDBACK_FILE, self.feedback)

        # 自動轉發去設定咗嘅 channel（有設定先會轉發）
        cid = self.feedback.get("channel_id")
        if cid:
            channel = self.bot.get_channel(cid)
            if channel:
                try:
                    embed = discord.Embed(
                        title=f"📮 新意見 #{fid}",
                        description=entry["message"][:4000],
                        color=discord.Color.gold(),
                        timestamp=datetime.now(),
                    )
                    embed.add_field(name="來自", value=entry["user"], inline=True)
                    embed.add_field(name="時間", value=entry["time"], inline=True)
                    await channel.send(embed=embed)
                except Exception:
                    pass

        await interaction.response.send_message(
            f"✅ 多謝你嘅意見（編號 #{fid}）！管理員會盡快處理。🙏",
            ephemeral=True,
        )

    @app_commands.command(name="feedback_list", description="🛡️ [管理員] 查看意見箱")
    @app_commands.describe(page="頁數 (預設第 1 頁)")
    async def slash_feedback_list(self, interaction: discord.Interaction, page: app_commands.Range[int, 1, 999] = 1):
        if not self._is_admin(interaction):
            await interaction.response.send_message("❌ 呢個係管理員指令。", ephemeral=True)
            return

        entries = self.feedback["entries"]
        if not entries:
            await interaction.response.send_message("📭 意見箱係空嘅。", ephemeral=True)
            return

        per_page = 10
        newest_first = list(reversed(entries))
        total_pages = (len(newest_first) + per_page - 1) // per_page
        if page > total_pages:
            page = total_pages

        chunk = newest_first[(page - 1) * per_page: page * per_page]

        lines = []
        for e in chunk:
            status = "✅" if e.get("resolved") else "⏳"
            lines.append(f"{status} **#{e['id']}** · {e['time']} · 來自 {e['user']}\n「{e['message'][:180]}」")

        embed = discord.Embed(
            title=f"📮 意見箱（第 {page}/{total_pages} 頁，共 {len(entries)} 條）",
            description="\n".join(lines)[:4000],
            color=discord.Color.gold(),
        )
        embed.set_footer(text="⏳ 未處理 · ✅ 已處理 · 用 /feedback_resolve <編號> 標記")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="feedback_resolve", description="🛡️ [管理員] 標記意見為已處理")
    @app_commands.describe(feedback_id="意見編號 (#)")
    async def slash_feedback_resolve(self, interaction: discord.Interaction, feedback_id: int):
        if not self._is_admin(interaction):
            await interaction.response.send_message("❌ 呢個係管理員指令。", ephemeral=True)
            return

        for e in self.feedback["entries"]:
            if e["id"] == feedback_id:
                e["resolved"] = True
                self._save_json(FEEDBACK_FILE, self.feedback)
                await interaction.response.send_message(f"✅ 意見 #{feedback_id} 已標記為已處理。", ephemeral=True)
                return

        await interaction.response.send_message(f"❌ 搵唔到編號 #{feedback_id} 嘅意見。", ephemeral=True)

    @app_commands.command(name="feedback_setchannel", description="🛡️ [管理員] 設定意見自動轉發 channel")
    @app_commands.describe(channel="新意見會自動轉發去呢度 (留空 = 取消轉發)")
    async def slash_feedback_setchannel(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        if not self._is_admin(interaction):
            await interaction.response.send_message("❌ 呢個係管理員指令。", ephemeral=True)
            return

        if channel is None:
            self.feedback["channel_id"] = None
            self._save_json(FEEDBACK_FILE, self.feedback)
            await interaction.response.send_message("✅ 已取消意見自動轉發。", ephemeral=True)
        else:
            self.feedback["channel_id"] = channel.id
            self._save_json(FEEDBACK_FILE, self.feedback)
            await interaction.response.send_message(f"✅ 之後有新意見會自動轉發去 {channel.mention}。", ephemeral=True)


# ============================================================
# 冇咗佢就會 NoEntryPointError！
# ============================================================
async def setup(bot):
    await bot.add_cog(AdminCog(bot))