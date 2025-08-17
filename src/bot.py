import os
import asyncio
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
load_dotenv(override=True)

TOKEN = os.getenv("DISCORD_TOKEN")
TEST_GUILD_ID = os.getenv("TEST_GUILD_ID")  # 있으면 길드 즉시 동기화

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing in .env")

intents = discord.Intents.default()   # 슬래시 커맨드만 사용 → 기본 인텐트 OK
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    try:
        if TEST_GUILD_ID:
            guild = discord.Object(id=int(TEST_GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)   # 즉시 반영
        else:
            synced = await bot.tree.sync()              # 글로벌(전파 지연 있을 수 있음)
        logging.info(f"Synced {len(synced)} app command(s)")
    except Exception:
        logging.exception("Slash command sync failed")
    logging.info(f"Logged in as {bot.user} (ID: {bot.user.id})")

async def load_extensions():
    await bot.load_extension("src.commands.ping")
    await bot.load_extension("src.commands.animepic")
    await bot.load_extension("src.commands.poll")
    await bot.load_extension("src.commands.aoi")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
