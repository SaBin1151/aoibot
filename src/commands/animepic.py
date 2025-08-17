# src/commands/animepic.py
# Safebooru SFW 랜덤 + 태그 자동완성(/animepic tag:)
import aiohttp
import random
import re
from typing import Optional, List, Dict

import discord
from discord import app_commands
from discord.ext import commands

from src.persona import PASTEL_PINK

SAFEBOORU_API = "https://safebooru.org/index.php"
UA = "AoiDiscordBot/1.3 (+https://discord.com)"

TAG_TYPE_MAP = {0: "일반", 1: "아티스트", 3: "저작권", 4: "캐릭터", 2: "메타"}
TAG_SAFE_RE = re.compile(r"[^0-9a-zA-Z _\-\(\)\[\]\.\*\~]+")

# 자동완성 완전 실패 시 보여줄 로컬 기본 후보(일부 예시)
POPULAR_TAGS = [
    "gawr_gura", "yoimiya_(genshin_impact)", "arona_(blue_archive)", "shiroko_(blue_archive)",
    "nakiri_ayame", "inugami_korone", "amatsukaze_(kancolle)", "megumin", "asuka_langley",
    "kirisame_marisa", "miku_hatsune", "yukinoshita_yukino", "kaguya_shinomiya"
]

def _clean_for_query(s: str) -> str:
    s = TAG_SAFE_RE.sub("", s or "").strip()
    s = re.sub(r"\s+", "_", s)  # 공백 → 언더바 (Safebooru 관습)
    return s

def _clean_for_display(s: str) -> str:
    return TAG_SAFE_RE.sub("", s or "").strip()

# ----------------- 태그 추천 -----------------
async def _autocomplete2(query: str, limit: int) -> List[Dict]:
    term = _clean_for_display(query)
    params = {"page": "autocomplete2", "term": term.replace("_", " "), "type": "tag_query", "limit": str(limit)}
    timeout = aiohttp.ClientTimeout(total=6)
    headers = {"User-Agent": UA}
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as s:
        async with s.get(SAFEBOORU_API, params=params) as r:
            if r.status != 200:
                return []
            data = await r.json(content_type=None)
    rows = []
    if isinstance(data, list):
        for t in data:
            name = (t.get("value") or "").strip()
            if not name:
                continue
            rows.append({
                "name": name,
                "count": int(t.get("post_count", 0) or 0),
                "type_text": (t.get("type") or "").lower(),
            })
    rows.sort(key=lambda x: (-x["count"], x["name"].lower()))
    # 중복 제거
    out, seen = [], set()
    for r in rows:
        k = r["name"].lower()
        if k in seen: continue
        seen.add(k); out.append(r)
    return out[:limit]

async def _dapi_fallback(query: str, limit: int) -> List[Dict]:
    """DAPI로 후보 시도(name_pattern, name 접두 등)"""
    q = _clean_for_query(query)
    if not q:
        return []
    param_sets = [
        {"page":"dapi","s":"tag","q":"index","json":1,"name_pattern":f"*{q}*","orderby":"count","order":"desc","limit":str(limit)},
        {"page":"dapi","s":"tag","q":"index","json":1,"name":f"{q}*","orderby":"count","order":"desc","limit":str(limit)},
    ]
    timeout = aiohttp.ClientTimeout(total=6)
    headers = {"User-Agent": UA}
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as s:
        for params in param_sets:
            try:
                async with s.get(SAFEBOORU_API, params=params) as r:
                    if r.status != 200: continue
                    data = await r.json(content_type=None)
                    if not isinstance(data, list) or not data: continue
                    rows = []
                    for t in data:
                        name = (t.get("name") or "").strip()
                        if not name: continue
                        rows.append({
                            "name": name,
                            "count": int(t.get("count", 0) or 0),
                            "type_text": "",  # DAPI는 type 텍스트가 다를 수 있음
                        })
                    rows.sort(key=lambda x: (-x["count"], x["name"].lower()))
                    out, seen = [], set()
                    for r_ in rows:
                        k = r_["name"].lower()
                        if k in seen: continue
                        seen.add(k); out.append(r_)
                    return out[:limit]
            except Exception:
                continue
    return []

async def safebooru_tag_suggest(query: str, limit: int = 15) -> List[Dict]:
    """자동완성2 → DAPI → 로컬 후보 순서로 폴백"""
    if not query or len(query.strip()) < 2:
        return []
    try:
        rows = await _autocomplete2(query, limit)
        if rows:
            return rows
    except Exception:
        pass
    try:
        rows = await _dapi_fallback(query, limit)
        if rows:
            return rows
    except Exception:
        pass
    # 마지막 폴백: 로컬 후보에서 부분일치
    q = _clean_for_query(query).lower()
    picks = [t for t in POPULAR_TAGS if q in t.lower()]
    return [{"name": t, "count": 0, "type_text": ""} for t in picks[:limit]]

# ----------------- 랜덤 포스트 -----------------
async def safebooru_random_post(tag: Optional[str]) -> Optional[Dict]:
    params = {"page": "dapi", "s": "post", "q": "index", "json": 1, "limit": 100}
    tag_q = _clean_for_query(tag or "")
    if tag_q:
        params["tags"] = tag_q

    timeout = aiohttp.ClientTimeout(total=12)
    headers = {"User-Agent": UA}
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as s:
        async with s.get(SAFEBOORU_API, params=params) as r:
            if r.status != 200:
                return None
            posts = await r.json(content_type=None)
            if not isinstance(posts, list) or not posts:
                return None
            post = random.choice(posts)

    file_url = post.get("file_url") or post.get("sample_url") or post.get("preview_url")
    if not file_url:
        return None
    view_url = f"https://safebooru.org/index.php?page=post&s=view&id={post.get('id')}"
    return {"id": post.get("id"), "file_url": file_url, "tags": post.get("tags",""),
            "score": post.get("score",0), "view_url": view_url}

# ----------------- UI -----------------
class SearchView(discord.ui.View):
    def __init__(self, tag: Optional[str], *, timeout: int = 120):
        super().__init__(timeout=timeout)
        self.tag = tag

    @discord.ui.button(label="다시 뽑기", style=discord.ButtonStyle.secondary, emoji="🔁")
    async def again(self, interaction: discord.Interaction, button: discord.ui.Button):
        post = await safebooru_random_post(self.tag or "")
        if not post:
            return await interaction.response.send_message("앗, 이미지를 가져오지 못했어요. 잠시 후 다시 시도해 주세요 (๑•́ㅁ•̀๑)💦", ephemeral=True)
        e = discord.Embed(title="랜덤 픽!", color=PASTEL_PINK, description=f"태그: `{_clean_for_display(self.tag) or '랜덤'}`")
        e.set_image(url=post["file_url"])
        e.add_field(name="원문", value=f"[Safebooru 열기]({post['view_url']})")
        # 🔧 원본 메시지를 '편집'해서 버튼이 유지되도록
        await interaction.response.edit_message(embed=e, view=self)

class AnimePicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._live_views: set[SearchView] = set()  # 뷰 강한 참조(가비지 컬렉션 방지)

    @app_commands.command(name="animepic", description="애니/캐릭터 이미지를 랜덤으로 보여줘요 (Safebooru, SFW)")
    @app_commands.describe(tag="태그(모르면 비워두세요, 입력 중 자동완성 지원)", public="채널에 공개로 보내기 (기본 비공개)")
    async def animepic(self, interaction: discord.Interaction, tag: Optional[str] = None, public: bool = False):
        await interaction.response.defer(ephemeral=not public, thinking=True)
        post = await safebooru_random_post(tag)
        if not post:
            return await interaction.followup.send("조건에 맞는 이미지를 못 찾았어요… 태그를 바꾸거나 비워보실래요? ꒰◍•ᴗ•◍꒱", ephemeral=not public)

        view = SearchView(tag)
        self._live_views.add(view)  # 참조 보관

        e = discord.Embed(
            title="랜덤 픽!", color=PASTEL_PINK,
            description=f"태그: `{_clean_for_display(tag) or '랜덤'}`",
        )
        e.set_image(url=post["file_url"])
        e.add_field(name="원문", value=f"[Safebooru 열기]({post['view_url']})")
        await interaction.followup.send(embed=e, view=view, ephemeral=not public)

    # 🔽 자동완성 핸들러
    @animepic.autocomplete("tag")
    async def animepic_tag_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        cur = current or ""
        if len(cur.strip()) < 2:
            return []
        rows = await safebooru_tag_suggest(cur, limit=15)
        out: List[app_commands.Choice[str]] = []
        for t in rows[:25]:
            dtype = t.get("type_text", "")
            disp = f"{t['name']} ({t.get('count',0):,})" + (f" · {dtype}" if dtype else "")
            out.append(app_commands.Choice(name=disp, value=t["name"]))
        return out

    # 뷰 타임아웃 뒤 참조 정리(메모리 관리, 선택사항)
    async def cog_unload(self):
        self._live_views.clear()

async def setup(bot):
    await bot.add_cog(AnimePicCog(bot))
