"""Gemini — 기술 글/레포 요약 + 마케팅 인사이트 합성.

키는 x-goog-api-key 헤더(로그 노출 방지). 429 1회 백오프. gemini-2.5 는 thinking
모델이라 thinkingBudget=0 (안 끄면 출력이 몇 글자에서 잘림).
"""
from __future__ import annotations

import asyncio
import logging

import httpx

from . import config

log = logging.getLogger(__name__)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _redact(msg: str) -> str:
    return msg.replace(config.GEMINI_API_KEY, "<KEY>") if config.GEMINI_API_KEY else msg


async def _generate(client: httpx.AsyncClient, prompt: str, max_tokens: int, temp: float = 0.3) -> str:
    if not config.GEMINI_API_KEY:
        return ""
    url = GEMINI_URL.format(model=config.GEMINI_MODEL)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temp, "maxOutputTokens": max_tokens, "thinkingConfig": {"thinkingBudget": 0}},
    }
    for attempt in range(2):
        try:
            r = await client.post(url, headers={"x-goog-api-key": config.GEMINI_API_KEY}, json=payload, timeout=60)
            if r.status_code == 429 and attempt == 0:
                await asyncio.sleep(8)
                continue
            r.raise_for_status()
            return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:  # noqa: BLE001
            if attempt == 0:
                await asyncio.sleep(4)
                continue
            log.warning("gemini failed: %s", _redact(str(e)))
            return ""
    return ""


async def summarize_article(client: httpx.AsyncClient, title: str, body: str) -> str:
    prompt = (
        "다음 기술/개발 글을 한국어 2~3줄로 핵심만 요약해줘. 마케팅·홍보 톤은 빼고 기술 디테일 중심으로.\n\n"
        f"제목: {title}\n\n본문:\n{body[:2000]}\n\n요약(2~3줄):"
    )
    return await _generate(client, prompt, 400)


async def summarize_repo(client: httpx.AsyncClient, repo: str, content: str) -> str:
    prompt = (
        "다음 GitHub 저장소가 무엇을 하는 프로젝트인지 한국어 1~2줄로 간결히 설명해줘.\n\n"
        f"저장소: {repo}\n설명/README:\n{content[:1800]}\n\n한국어 설명(1~2줄):"
    )
    return await _generate(client, prompt, 250)


async def marketing_insights(client: httpx.AsyncClient, reads: list, trends: list,
                             products: list, datalab: list, apps: list[str]) -> str:
    read_lines = "\n".join(f"- [{r['source']}] {r['title']}" for r in reads[:8]) or "(없음)"
    trend_lines = "\n".join(f"- {t['title']} ({t.get('traffic','')})" for t in trends[:8])
    dl_lines = ""
    for seg in datalab:
        top = ", ".join(f"{x['name']}{'+' if x['pct'] >= 0 else ''}{x['pct']}%" for x in seg["items"][:5])
        dl_lines += f"- [{seg['segment']}] {top}\n"
    dl_lines = dl_lines or "(없음)"
    ph_lines = "\n".join(f"- {p['name']}: {p.get('tagline','')}" for p in products[:6])
    prompt = (
        "너는 앱·서비스 마케팅 전략가다. 타겟은 '돈 많이 쓰는 세대'(30-50대, 남녀 다양 — 20대 남성 제외). "
        "오늘의 신호로 앱/마케팅 실무자가 바로 써먹을 인사이트를 뽑아라.\n\n"
        f"[오늘 마케팅 매체 헤드라인]\n{read_lines}\n\n"
        f"[실시간 한국 검색 트렌드]\n{trend_lines}\n\n"
        f"[세그먼트별 관심사 검색 추이(데이터랩, 최근 vs 과거 %)]\n{dl_lines}\n"
        f"[오늘 뜨는 글로벌 프로덕트(Product Hunt)]\n{ph_lines}\n\n"
        f"[참고 — 우리 앱]\n{', '.join(apps)}\n\n"
        "인사이트 5개. 세그먼트별 소비 동기가 다르니 어느 세대/성별에게 무엇을 어떤 각도로 밀지 구체적으로. "
        "매체 헤드라인·검색 추이·실시간 트렌드를 엮을 것. 뻔한 말 금지. 각 줄:\n"
        "• [타겟 세그먼트] [포착 신호] → [마케팅 시사점/콘텐츠·채널 각도]\n다른 말 없이 5줄만."
    )
    return await _generate(client, prompt, 1000, temp=0.7)
