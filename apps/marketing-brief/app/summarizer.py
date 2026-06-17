"""Gemini 합성 — 콘텐츠 아이디어 생성 (httpx → Generative Language REST).

- API 키는 x-goog-api-key 헤더로 (에러 로그 노출 방지). 429 1회 백오프 재시도.
- gemini-2.5 thinking 모델이라 thinkingBudget=0 (안 끄면 출력이 몇 글자에서 잘림).
GEMINI_API_KEY 없으면 빈 문자열.
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


async def _generate(client: httpx.AsyncClient, prompt: str, max_tokens: int) -> str:
    if not config.GEMINI_API_KEY:
        return ""
    url = GEMINI_URL.format(model=config.GEMINI_MODEL)
    headers = {"x-goog-api-key": config.GEMINI_API_KEY}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": max_tokens,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    for attempt in range(2):
        try:
            r = await client.post(url, headers=headers, json=payload, timeout=60)
            if r.status_code == 429 and attempt == 0:
                await asyncio.sleep(8)
                continue
            r.raise_for_status()
            data = r.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:  # noqa: BLE001
            if attempt == 0:
                await asyncio.sleep(4)
                continue
            log.warning("gemini failed: %s", _redact(str(e)))
            return ""
    return ""


async def content_ideas(client: httpx.AsyncClient, trends: list, products: list,
                        hn: list, apps: list[str]) -> str:
    trend_lines = "\n".join(f"- {t['title']} ({t.get('traffic','')})" for t in trends[:8])
    ph_lines = "\n".join(f"- {p['name']}: {p.get('tagline','')}" for p in products[:6])
    hn_lines = "\n".join(f"- {h['title']}" for h in hn[:6])
    app_lines = "\n".join(f"- {a}" for a in apps)
    prompt = (
        "너는 한국 소비자 앱의 SNS 마케팅 담당이다. 오늘의 트렌드를 우리 앱과 엮어 "
        "바로 써먹을 콘텐츠 아이디어를 만든다.\n\n"
        f"[오늘 한국 검색 트렌드]\n{trend_lines}\n\n"
        f"[오늘 뜨는 글로벌 프로덕트(Product Hunt)]\n{ph_lines}\n\n"
        f"[글로벌 테크 화제(Hacker News)]\n{hn_lines}\n\n"
        f"[우리 앱]\n{app_lines}\n\n"
        "위 트렌드 중 우리 앱과 자연스럽게 엮을 수 있는 걸 골라, 인스타/숏폼/블로그용 "
        "콘텐츠 아이디어 4개를 제안해줘. 뻔한 건 빼고 후킹되게. 각 아이디어는 정확히 한 줄:\n"
        "• [앱이름] 활용 트렌드 → 콘텐츠 각도(후킹 포인트)\n"
        "다른 말 없이 4줄만 출력."
    )
    return await _generate(client, prompt, 700)
