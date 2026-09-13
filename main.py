import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
APPLICATION_ID = os.getenv("APPLICATION_ID")


class SPYCBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        app_id = None
        if APPLICATION_ID and APPLICATION_ID.strip().isdigit():
            app_id = int(APPLICATION_ID.strip())

        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            intents=intents,
            application_id=app_id,
        )
        self._dedup_done = False

    async def setup_hook(self):
        """Load cogs and sync commands"""
        await self.load_extension("cogs.timetable_cog")
        await self.load_extension("cogs.qr_cog")
        await self.load_extension("cogs.admin_cog")
        await self.load_extension("cogs.weather_cog")
        await self.load_extension("cogs.info_cog")
        await self.load_extension("cogs.ai_cog")   # 🤖 新加

        try:
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} global slash commands")
        except Exception as e:
            print(f"❌ Failed to sync commands: {e}")

    async def on_ready(self):
        # 🧹 一次性清除每個 server 殘留嘅 guild-scoped 指令（防指令 doubled）
        if not self._dedup_done:
            self._dedup_done = True
            for guild in self.guilds:
                try:
                    self.tree.clear_commands(guild=guild)
                    await self.tree.sync(guild=guild)
                    print(f"🧹 Cleared duplicate guild commands in: {guild.name}")
                except Exception as e:
                    print(f"❌ Failed to clear commands in {guild.name}: {e}")

        print(f"🤖 Logged in as {self.user} (ID: {self.user.id})")
        print(f"📊 Connected to {len(self.guilds)} servers")
        print("=" * 50)

        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="SPYC 時間表 | /help"
        )
        await self.change_presence(activity=activity)

    async def on_guild_join(self, guild):
        try:
            self.tree.clear_commands(guild=guild)
            await self.tree.sync(guild=guild)
        except Exception:
            pass
        print(f"➕ Joined new server: {guild.name} (ID: {guild.id})")

    async def on_error(self, event, *args, **kwargs):
        print(f"❌ Error in {event}: {args} {kwargs}")


async def main():
    if not TOKEN:
        print("❌ ERROR: DISCORD_TOKEN not found in .env file!")
        print("Please copy .env.example to .env and fill in your token.")
        return

    bot = SPYCBot()

    try:
        await bot.start(TOKEN)
    except discord.LoginFailure:
        print("❌ ERROR: Invalid Discord token. Please check your .env file.")
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user.")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())