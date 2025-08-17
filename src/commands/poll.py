# src/commands/poll.py
# 버튼 투표 (/poll)
import discord
from discord import app_commands
from discord.ext import commands
from typing import List

from src.persona import PASTEL_PINK

NUM_EMOJIS = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]

class PollView(discord.ui.View):
    def __init__(self, question: str, options: List[str], *, multi: bool, timeout_sec: int):
        super().__init__(timeout=timeout_sec)
        self.question = question
        self.options = options
        self.multi = multi
        self.votes = {i: set() for i in range(len(options))}
        self.message: discord.Message | None = None

        for idx, label in enumerate(options):
            self.add_item(self._make_button(idx, label))  # <-- 이제 실제 Button 객체를 추가

    def _make_button(self, idx: int, label: str) -> discord.ui.Button:
        # 동적 버튼은 데코레이터가 아니라 Button 인스턴스 + 콜백 할당 방식 사용
        btn = discord.ui.Button(
            label=f"{NUM_EMOJIS[idx]} {label}",
            style=discord.ButtonStyle.secondary,
            custom_id=f"poll_{idx}",
        )

        async def callback(interaction: discord.Interaction):
            uid = interaction.user.id

            # 단일선택이면 다른 선택 해제
            if not self.multi:
                for i in range(len(self.options)):
                    if uid in self.votes[i]:
                        self.votes[i].remove(uid)

            # 토글
            if uid in self.votes[idx]:
                self.votes[idx].remove(uid)
            else:
                self.votes[idx].add(uid)

            await self._refresh(interaction)

        btn.callback = callback  # 콜백 부착
        return btn

    async def _refresh(self, interaction: discord.Interaction):
        embed = self._build_embed(running=True)
        await interaction.response.edit_message(embed=embed, view=self)

    def _build_embed(self, *, running: bool):
        total = sum(len(s) for s in self.votes.values())
        title = "📊 투표 진행 중" if running else "📌 투표 종료"
        desc = f"**{self.question}**\n(참여 {total}명 • {'복수선택' if self.multi else '단일선택'})"
        e = discord.Embed(title=title, description=desc, color=PASTEL_PINK)
        for i, opt in enumerate(self.options):
            e.add_field(name=f"{NUM_EMOJIS[i]} {opt}", value=f"{len(self.votes[i])} 표", inline=False)
        return e

    async def on_timeout(self):
        # 타임아웃 시 버튼 비활성화 + 결과 고정
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        if self.message:
            await self.message.edit(embed=self._build_embed(running=False), view=self)

class PollCog(commands.Cog):
    def __init__(self, bot): 
        self.bot = bot

    @app_commands.command(name="poll", description="버튼 투표를 만들어요")
    @app_commands.describe(
        question="질문",
        options="쉼표로 구분된 선택지 (최대 10개)",
        minutes="마감 시간(분) (기본 5분)",
        multi="복수 선택 허용 (기본: 불가)",
        public="채널에 공개로 보내기 (권장)"
    )
    async def poll(self, interaction: discord.Interaction, question: str, options: str, minutes: int = 5, multi: bool = False, public: bool = True):
        opts = [o.strip() for o in options.split(",") if o.strip()]
        if not (2 <= len(opts) <= 10):
            return await interaction.response.send_message("선택지는 2~10개로 입력해 주세요.", ephemeral=True)

        timeout_sec = max(30, min(60*60, minutes*60))
        view = PollView(question, opts, multi=multi, timeout_sec=timeout_sec)
        embed = view._build_embed(running=True)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=not public)
        msg = await interaction.original_response()
        view.message = msg  # 타임아웃 시 메시지 수정 위해 보관

async def setup(bot):
    await bot.add_cog(PollCog(bot))
