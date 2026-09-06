import discord  # type: ignore[reportMissingImports]
from discord import app_commands
from discord.ext import commands
import io
import segno


class QRCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="qr", description="產生 QR code")
    @app_commands.describe(
        text="想轉做 QR code 嘅內容 (網址 / 文字)",
        scale="圖片大小 (3-20，預設 8)"
    )
    async def slash_qr(self, interaction: discord.Interaction, text: str, scale: app_commands.Range[int, 3, 20] = 8):
        await interaction.response.defer()

        try:
            qr = segno.make(text)
        except Exception as e:
            await interaction.followup.send(f"❌ 產生 QR code 失敗：內容太長或者格式有問題。\n`({e})`")
            return

        buffer = io.BytesIO()
        qr.save(buffer, kind="png", scale=scale, border=2)
        buffer.seek(0)

        file = discord.File(buffer, filename="qr.png")

        icon_url = interaction.user.display_avatar.url if hasattr(interaction.user, 'display_avatar') else None
        embed = discord.Embed(
            title="📱 QR Code",
            color=discord.Color.green()
        )
        embed.set_author(name="SPYC Siu Ying", icon_url=icon_url)
        shown = text[:300] + ("..." if len(text) > 300 else "")
        embed.description = f"內容：{shown}"
        embed.set_image(url="attachment://qr.png")
        embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=icon_url)

        await interaction.followup.send(embed=embed, file=file)


# ============================================================
# 冇咗佢就會 NoEntryPointError！
# ============================================================
async def setup(bot):
    await bot.add_cog(QRCog(bot))