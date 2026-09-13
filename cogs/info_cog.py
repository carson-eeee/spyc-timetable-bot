import discord  # type: ignore[reportMissingImports]
from discord import app_commands
from discord.ext import commands


class InfoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="avatar", description="🖼️ 查看用戶頭像 (高清)")
    @app_commands.describe(user="用戶 (留空=自己)")
    async def slash_avatar(self, interaction: discord.Interaction, user: discord.User = None):
        target = user or interaction.user
        avatar = target.display_avatar.with_size(1024)

        embed = discord.Embed(
            title=f"{target.display_name} 嘅頭像",
            color=discord.Color.blurple()
        )
        embed.set_image(url=avatar.url)
        embed.add_field(
            name="🔗 下載原圖",
            value=(
                f"[PNG]({avatar.with_format('png').url}) · "
                f"[JPG]({avatar.with_format('jpg').url}) · "
                f"[WEBP]({avatar.with_format('webp').url})"
            ),
            inline=False
        )
        embed.set_footer(text=f"ID: {target.id}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="👤 查看用戶資料")
    @app_commands.describe(user="用戶 (留空=自己)")
    async def slash_userinfo(self, interaction: discord.Interaction, user: discord.User = None):
        target = user or interaction.user

        member = None
        if interaction.guild:
            member = interaction.guild.get_member(target.id)

        embed = discord.Embed(
            title=f"👤 {target.display_name}",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🏷️ 用戶名", value=str(target), inline=True)
        embed.add_field(name="🆔 用戶 ID", value=str(target.id), inline=True)
        embed.add_field(name="🤖 機器人", value="係" if target.bot else "唔係", inline=True)
        embed.add_field(
            name="📅 帳號建立",
            value=f"{discord.utils.format_dt(target.created_at, 'D')}\n({discord.utils.format_dt(target.created_at, 'R')})",
            inline=True
        )
        if member:
            if member.joined_at:
                embed.add_field(
                    name="➡️ 加入伺服器",
                    value=f"{discord.utils.format_dt(member.joined_at, 'D')}\n({discord.utils.format_dt(member.joined_at, 'R')})",
                    inline=True
                )
            roles = [r.mention for r in reversed(member.roles)
                     if r != interaction.guild.default_role][:15]
            embed.add_field(
                name=f"🎭 身份組 ({len(member.roles) - 1})",
                value=" ".join(roles) or "無",
                inline=False
            )
        embed.set_footer(
            text=f"Requested by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url if hasattr(interaction.user, 'display_avatar') else None
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="🏰 查看伺服器資料")
    async def slash_serverinfo(self, interaction: discord.Interaction):
        g = interaction.guild
        if not g:
            await interaction.response.send_message("❌ 呢個指令要喺伺服器入面用。", ephemeral=True)
            return

        owner = str(g.owner) if g.owner else f"ID: {g.owner_id}"

        embed = discord.Embed(title=f"🏰 {g.name}", color=discord.Color.blurple())
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name="🆔 伺服器 ID", value=str(g.id), inline=True)
        embed.add_field(name="👑 擁有者", value=owner, inline=True)
        embed.add_field(name="👥 成員數", value=str(g.member_count or "?"), inline=True)
        embed.add_field(
            name="📅 伺服器建立",
            value=f"{discord.utils.format_dt(g.created_at, 'D')}\n({discord.utils.format_dt(g.created_at, 'R')})",
            inline=True
        )
        embed.add_field(
            name="📺 頻道",
            value=f"💬 {len(g.text_channels)} 文字 · 🔊 {len(g.voice_channels)} 語音",
            inline=True
        )
        embed.add_field(name="🎭 身份組", value=str(len(g.roles)), inline=True)
        embed.add_field(
            name="🚀 Boost",
            value=f"等級 {g.premium_tier}（{g.premium_subscription_count} 個）",
            inline=True
        )
        embed.set_footer(
            text=f"Requested by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url if hasattr(interaction.user, 'display_avatar') else None
        )
        await interaction.response.send_message(embed=embed)


# 冇咗佢就會 NoEntryPointError！
async def setup(bot):
    await bot.add_cog(InfoCog(bot))