# src/commands/aoi.py
# 귀여운 말투 짧은 대화 (/aoi)
import random
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from src.persona import PASTEL_PINK

KAEOMO = ["꒰◍•ᴗ•◍꒱", "( ˶˙ᵕ˙˶ )", "(๑˃̵ᴗ˂̵)و", "( •̀ω•́ )✧", "(ง•̀_•́)ง", "(๑•̀ㅂ•́)و✧"]

def cute_reply(prompt: str) -> str:
    p = prompt.lower()
    heart = "💗"
    face = random.choice(KAEOMO)

    if "안녕" in prompt or "헬로" in p or "hello" in p:
        return f"{face} 안녕하세요! 아오이 비서예요. 무엇을 도와드릴까요? {heart}"
    if "고마워" in prompt or "감사" in prompt:
        return f"{face} 도움이 되어서 기뻐요! 언제든 불러 주세요 ✨"
    if "사랑" in prompt or "최고" in prompt:
        return f"{face} 에헤헷… 과분한 칭찬이에요! 더 열심히 할게요 💖"
    if "힘들" in prompt or "피곤" in prompt:
        return f"{face} 수고 많으셨어요… 따뜻한 물 한 잔과 가벼운 스트레칭 추천드려요 (ง •̀_•́)ง"
    if "애미" in prompt:
        return f"{face} 니애미~"
    # 기본
    return f"{face} 네! '{prompt}'(이)라고요. 메모해 뒀어요. 또 필요하신 건 없으신가요? ✨"

class AronaCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="aoi", description="아오이와 짧게 대화해요")
    @app_commands.describe(text="하고 싶은 말", public="채널에 공개로 보내기 (기본 비공개)")
    async def arona(self, interaction: discord.Interaction, text: str, public: bool = False):
        msg = cute_reply(text)
        e = discord.Embed(description=msg, color=PASTEL_PINK)
        await interaction.response.send_message(embed=e, ephemeral=not public)

async def setup(bot):
    await bot.add_cog(AronaCog(bot))
