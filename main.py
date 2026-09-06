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

        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            intents=intents,
            application_id=APPLICATION_ID
        )

    async def setup_hook(self):
        """Load cogs and sync commands"""
        await self.load_extension("cogs.timetable_cog")
        await self.load_extension("cogs.qr_cog")   # ⬅ 新加呢行

        # Sync slash commands
        try:
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} slash commands")
        except Exception as e:
            print(f"❌ Failed to sync commands: {e}")

    async def on_ready(self):
        """Called when bot is ready"""
        print(f"🤖 Logged in as {self.user} (ID: {self.user.id})")
        print(f"📊 Connected to {len(self.guilds)} servers")
        print("=" * 50)

        # Set activity
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="SPYC 時間表 | /help"
        )
        await self.change_presence(activity=activity)

    async def on_guild_join(self, guild):
        """Called when bot joins a new server"""
        print(f"➕ Joined new server: {guild.name} (ID: {guild.id})")

    async def on_error(self, event, *args, **kwargs):
        """Handle errors"""
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
