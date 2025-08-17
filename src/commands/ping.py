import discord
from discord import app_commands
from discord.ext import commands

class PingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="봇 응답 테스트")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("꒰◍•ᴗ•◍꒱ pong! 봇이 잘 켜졌어요 ✨", ephemeral=True)

async def setup(bot):
    await bot.add_cog(PingCog(bot))
