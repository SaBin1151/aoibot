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
UA = "AoiDiscordBot/1.4 (+https://discord.com)"

# 표시용 타입 텍스트(없어도 동작에는 문제 없음)
TAG_TYPE_MAP = {0: "일반", 1: "아티스트", 3: "저작권", 4: "캐릭터", 2: "메타"}

# 허용 문자만: 영숫자/공백/_-()[].*~
TAG_SAFE_RE = re.compile(r"[^0-9a-zA-Z _\-\(\)\[\]\.\*\~]+")

# 자동완성 완전 실패 시 보여줄 로컬 기본 후보(일부 예시)
POPULAR_TAGS = [
    "gawr_gura", "yoimiya_(genshin_impact)", "arona_(blue_archive)", "shiroko_(blue_archive)",
    "koharu_(blue_archive)", "nakiri_ayame", "inugami_korone", "amatsukaze_(kancolle)",
    "megumin", "asuka_langley", "kirisame_marisa", "miku_hatsune", "kaguya_shinomiya"
]

def _clean_for_query(s: str) -> str:
    """입력 정리 + 공백→언더바 (Safebooru 태그 관습)"""
    s = TAG_SAFE_RE.sub("", s or "").strip()
    s = re.sub(r"\s+", "_", s)
    return s

def _clean_for_display(s: str) -> str:
    """표시용(그대로 보여주되 위험문자 제거)"""
    return TAG_SAFE_RE.sub("", s or "").strip()

# ----------------- 태그 추천 -----------------
def _normalize_tag_label_to_name(raw: str) -> str:
    """Autocomplete2가 주는 label/value를 보루 태그 표기로 정규화"""
    s = (raw or "").strip().lower()
    s = re.sub(r"\s+", "_", s)
    return s

def _score_tag(name: str, q: str, tag_type: int | None = None, count: int | None = None) -> int:
    """
    간단 점수: 접두어 매치>부분 매치, 캐릭터/저작권 가중, 카운트 약가중.
    type 추정: 1 artist, 3 copyright, 4 character
    """
    name_l = name.lower()
    q_l = q.lower()
    sc = 0
    if name_l.startswith(q_l):
        sc += 120
    if q_l in name_l:
        sc += 60
    if tag_type in (4, 3):
        sc += 15
    if count:
        sc += min(count // 1000, 20)
    if "(" in name or "_" in name:
        sc += 5
    return sc

async def _autocomplete2(term: str, limit: int) -> List[Dict]:
    """Safebooru의 실제 자동완성 API(page=autocomplete2)"""
    params = {"page": "autocomplete2", "type": "tag_query", "term": term, "limit": str(limit)}
    headers = {"User-Agent": UA}
    timeout = aiohttp.ClientTimeout(total=6)
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as s:
        async with s.get(SAFEBOORU_API, params=params) as r:
            if r.status != 200:
                return []
            data = await r.json(content_type=None)
    rows: List[Dict] = []
    if isinstance(data, list):
        for it in data:
            raw = (it.get("value") or it.get("label") or "").strip()
            if not raw:
                continue
            nm = _normalize_tag_label_to_name(raw)
            cnt = int(it.get("post_count", 0) or 0)
            typet = (it.get("type") or "").lower()
            rows.append({"name": nm, "count": cnt, "type_text": typet})
    # 중복 제거 + 정렬
    out, seen = [], set()
    for r in sorted(rows, key=lambda x: (-x["count"], x["name"])):
        k = r["name"].lower()
        if k in seen: 
            continue
        seen.add(k); out.append(r)
    return out[:limit]

async def _dapi_tags(term: str, limit: int) -> List[Dict]:
    """DAPI 태그 엔드포인트로 보강(name_pattern / 접두 매치)"""
    q = _clean_for_query(term)
    if not q:
        return []
    param_sets = [
        {"page":"dapi","s":"tag","q":"index","json":1,"name_pattern":f"*{q}*","orderby":"count","order":"desc","limit":str(limit)},
        {"page":"dapi","s":"tag","q":"index","json":1,"name":f"{q}*","orderby":"count","order":"desc","limit":str(limit)},
    ]
    headers = {"User-Agent": UA}
    timeout = aiohttp.ClientTimeout(total=6)
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as s:
        for params in param_sets:
            try:
                async with s.get(SAFEBOORU_API, params=params) as r:
                    if r.status != 200: 
                        continue
                    data = await r.json(content_type=None)
                    if not isinstance(data, list) or not data:
                        continue
                    rows: List[Dict] = []
                    for t in data:
                        name = (t.get("name") or "").strip()
                        if not name:
                            continue
                        try:
                            cnt = int(t.get("count", 0) or 0)
                        except Exception:
                            cnt = 0
                        try:
                            ttype = int(t.get("type")) if t.get("type") is not None else None
                        except Exception:
                            ttype = None
                        rows.append({"name": name, "count": cnt, "type": ttype})
                    # 중복 제거 + 정렬(카운트/이름)
                    out, seen = [], set()
                    for r_ in sorted(rows, key=lambda x: (-x["count"], x["name"].lower())):
                        k = r_["name"].lower()
                        if k in seen:
                            continue
                        seen.add(k); out.append(r_)
                    return out[:limit]
            except Exception:
                continue
    return []

async def safebooru_tag_suggest(query: str, limit: int = 25) -> List[Dict]:
    """autocomplete2 → DAPI(tags) → 로컬 목록 순으로 폴백해서 병합"""
    if not query or len(query.strip()) < 2:
        return []
    results: Dict[str, Dict] = {}
    # 1) autocomplete2
    try:
        a = await _autocomplete2(query, limit=100)
        for it in a:
            nm = it["name"]
            results[nm] = {
                "name": nm,
                "score": _score_tag(nm, query, None, it.get("count", 0)),
                "count": it.get("count", 0),
                "type_text": it.get("type_text", ""),
            }
    except Exception:
        pass
    # 2) DAPI(tags)
    try:
        b = await _dapi_tags(query, limit=100)
        for it in b:
            nm = it["name"]
            sc = _score_tag(nm, query, it.get("type"), it.get("count"))
            prev = results.get(nm)
            if not prev or sc > prev["score"]:
                results[nm] = {
                    "name": nm, "score": sc,
                    "count": it.get("count", 0),
                    "type_text": TAG_TYPE_MAP.get(it.get("type", 0), ""),
                }
    except Exception:
        pass
    if not results:
        # 3) 로컬 후보
        q = _clean_for_query(query).lower()
        picks = [t for t in POPULAR_TAGS if q in t.lower()]
        return [{"name": t, "count": 0, "type_text": ""} for t in picks[:limit]]

    merged = sorted(results.values(), key=lambda x: x["score"], reverse=True)
    return merged[:limit]

# ----------------- 랜덤 포스트 -----------------
async def safebooru_random_post(tag: Optional[str]) -> Optional[Dict]:
    params = {"page": "dapi", "s": "post", "q": "index", "json": 1, "limit": 100}
    tag_q = _clean_for_query(tag or "")
    if tag_q:
        params["tags"] = tag_q

    headers = {"User-Agent": UA}
    timeout = aiohttp.ClientTimeout(total=12)
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
        # 원본 메시지 편집(버튼 유지)
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

    # 자동완성 핸들러
    @animepic.autocomplete("tag")
    async def animepic_tag_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        cur = current or ""
        if len(cur.strip()) < 2:
            return []
        rows = await safebooru_tag_suggest(cur, limit=25)
        out: List[app_commands.Choice[str]] = []
        for t in rows[:25]:
            dtype = t.get("type_text", "")
            disp = f"{t['name']} ({t.get('count',0):,})" + (f" · {dtype}" if dtype else "")
            out.append(app_commands.Choice(name=disp, value=t["name"]))
        return out

    @app_commands.command(name="tag-suggest", description="Safebooru에서 태그 후보를 찾아줘요 (자동완성 참고용)")
    @app_commands.describe(query="예: gawr, gura, koharu, yoimiya 등", public="채널에 공개로 보내기 (기본 비공개)")
    async def tag_suggest(self, interaction: discord.Interaction, query: str, public: bool = False):
        await interaction.response.defer(ephemeral=not public, thinking=True)
        rows = await safebooru_tag_suggest(query, limit=20)
        if not rows:
            return await interaction.followup.send("해당 검색어로 태그를 찾지 못했어요. 철자를 바꾸거나 더 일반적인 단어로 시도해 볼까요? ꒰◍•ᴗ•◍꒱", ephemeral=not public)

        e = discord.Embed(
            title=f"태그 후보 · '{_clean_for_display(query)}'",
            color=PASTEL_PINK,
            description="`/animepic` 입력 칸에서도 자동완성이 떠요!",
        )
        for t in rows[:10]:
            e.add_field(
                name=t["name"],
                value=f"유형: **{t.get('type_text','?')}** · 사용 수: **{t.get('count',0):,}**\n"
                      f"예: `/animepic tag:{t['name']}`",
                inline=False
            )
        await interaction.followup.send(embed=e, ephemeral=not public)

    async def cog_unload(self):
        self._live_views.clear()

async def setup(bot):
    await bot.add_cog(AnimePicCog(bot))
