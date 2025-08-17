# src/commands/help.py
# /help : Aoi(아오이) 봇 사용 안내(공지 요약 포함)
import discord
from discord import app_commands
from discord.ext import commands
from typing import List, Optional
from src.persona import PASTEL_PINK

CHOICES = [
    app_commands.Choice(name="전체", value="all"),
    app_commands.Choice(name="animepic", value="animepic"),
    app_commands.Choice(name="tag-suggest", value="tag-suggest"),
    app_commands.Choice(name="poll", value="poll"),
    app_commands.Choice(name="aoi", value="aoi"),
    app_commands.Choice(name="ping", value="ping"),
]

def _embed_header() -> discord.Embed:
    e = discord.Embed(
        title="Aoi(아오이) 봇 — 사용 안내",
        description="꒰◍•ᴗ•◍꒱ﾉﾞ 안녕하세요! 아오이예요. 서버에서 쓸 수 있는 명령과 팁을 정리했어요.",
        color=PASTEL_PINK,
    )
    e.add_field(
        name="기본 안내",
        value=(
            "• 슬래시 명령은 채팅창에 `/` 입력하면 목록이 떠요.\n"
            "• 대부분의 명령은 **기본 비공개(나만 보기)** 로 응답해요. 공개하려면 `public: true` 옵션을 사용해 주세요.\n"
            "• 과도한 연타는 레이트리밋에 걸릴 수 있어요. 잠시 쉬었다가 다시 시도해 주세요."
        ),
        inline=False,
    )
    return e

def _embed_animepic() -> discord.Embed:
    e = discord.Embed(title="/animepic — 애니/캐릭터 이미지 랜덤 (SFW)", color=PASTEL_PINK)
    e.description = (
        "Safebooru에서 태그 기반으로 **안전한 이미지(SFW)** 를 랜덤으로 가져와요.\n"
        "결과 카드에서 **🔁 다시 뽑기** 버튼으로 같은 태그 재추첨이 가능해요."
    )
    e.add_field(
        name="옵션",
        value=(
            "• `tag` (선택): 태그 자동완성 지원(두 글자 이상 입력)\n"
            "  예) `koharu_(blue_archive)`, `arona_(blue_archive)`, `gawr_gura`\n"
            "• `public` (선택): `true`로 하면 채널에 공개, 기본은 비공개"
        ),
        inline=False,
    )
    e.add_field(name="예시", value="`/animepic` · `/animepic tag:koharu_(blue_archive)`", inline=False)
    return e

def _embed_tag_suggest() -> discord.Embed:
    e = discord.Embed(title="/tag-suggest — Safebooru 태그 후보 찾기", color=PASTEL_PINK)
    e.add_field(
        name="설명",
        value="입력한 키워드로 Safebooru의 **정확한 태그명**(언더바·괄호 포함)을 추천해요.",
        inline=False,
    )
    e.add_field(name="옵션", value="• `query`: 검색어  • `public` (선택)", inline=False)
    e.add_field(name="예시", value="`/tag-suggest query:koharu` · `/tag-suggest query:yoimiya`", inline=False)
    return e

def _embed_poll() -> discord.Embed:
    e = discord.Embed(title="/poll — 버튼 투표 만들기", color=PASTEL_PINK)
    e.add_field(
        name="옵션",
        value=(
            "• `question`: 질문/주제\n"
            "• `options`: 보기 목록 (**`|` 파이프로 구분** 권장, 예: `치킨|피자|햄버거`)\n"
            "• `multi` (선택): 복수선택 허용\n"
            "• `timeout_sec` (선택): 마감 시간(초)"
        ),
        inline=False,
    )
    e.add_field(
        name="예시",
        value=(
            "`/poll question:\"점심 뭐 먹을까요?\" options:\"치킨|피자|햄버거\"`\n"
            "`/poll question:\"모임 요일\" options:\"금|토\" multi:true timeout_sec:3600`"
        ),
        inline=False,
    )
    return e

def _embed_aoi() -> discord.Embed:
    e = discord.Embed(title="/aoi — 아오이랑 짧은 대화", color=PASTEL_PINK)
    e.add_field(name="옵션", value="• `text`: 말 걸기  • `public` (선택)", inline=False)
    e.add_field(name="예시", value="`/aoi text:\"안녕!\"` · `/aoi text:\"수고했어\" public:true`", inline=False)
    return e

def _embed_ping() -> discord.Embed:
    e = discord.Embed(title="/ping — 상태 확인", color=PASTEL_PINK)
    e.add_field(name="예시", value="`/ping`", inline=False)
    return e

def _embed_policy_faq() -> discord.Embed:
    e = discord.Embed(title="정책 & FAQ", color=PASTEL_PINK)
    e.add_field(
        name="정책",
        value="• 본 봇은 **SFW(안전한 이미지)** 만 제공합니다.\n• 저작권/2차 저작물 권리를 존중해 주세요. 원문 링크와 작가 정보를 확인!",
        inline=False,
    )
    e.add_field(
        name="FAQ",
        value=(
            "• **자동완성이 안 떠요** → 두 글자 이상 입력하고 잠시 기다려 주세요.\n"
            "• **이미지가 안 보여요** → 🔁 다시 뽑기 또는 다른 태그로 시도해 보세요.\n"
            "• **왜 나만 보여요?** → 기본은 비공개 응답이에요. `public:true`로 공개 전환!"
        ),
        inline=False,
    )
    return e

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="아오이 봇 사용 방법을 안내해요")
    @app_commands.describe(section="보고 싶은 섹션만 골라볼 수 있어요", public="채널에 공개로 보내기 (기본 비공개)")
    @app_commands.choices(section=CHOICES)
    async def help(
        self,
        interaction: discord.Interaction,
        section: Optional[app_commands.Choice[str]] = None,
        public: bool = False,
    ):
        await interaction.response.defer(ephemeral=not public)

        embeds: List[discord.Embed] = []
        embeds.append(_embed_header())

        key = (section.value if section else "all")
        if key in ("all", "animepic"):
            embeds.append(_embed_animepic())
        if key in ("all", "tag-suggest"):
            embeds.append(_embed_tag_suggest())
        if key in ("all", "poll"):
            embeds.append(_embed_poll())
        if key in ("all", "aoi"):
            embeds.append(_embed_aoi())
        if key in ("all", "ping"):
            embeds.append(_embed_ping())
        if key == "all":
            embeds.append(_embed_policy_faq())

        await interaction.followup.send(embeds=embeds, ephemeral=not public)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
