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


async def marketing_insights(client: httpx.AsyncClient, trends: list, products: list,
                             hn: list, datalab: list, apps: list[str]) -> str:
    trend_lines = "\n".join(f"- {t['title']} ({t.get('traffic','')})" for t in trends[:8])
    dl_lines = "\n".join(
        f"- {d['name']}: {'+' if d['pct'] >= 0 else ''}{d['pct']}% ({d['dir']})" for d in datalab
    ) or "(데이터 없음)"
    ph_lines = "\n".join(f"- {p['name']}: {p.get('tagline','')}" for p in products[:6])
    hn_lines = "\n".join(f"- {h['title']}" for h in hn[:6])
    app_lines = ", ".join(apps)
    prompt = (
        "너는 20-30대 여성을 주 타겟으로 하는 한국 앱들의 마케팅 전략가다. "
        "오늘의 신호들을 보고 '지금 바로 써먹을 마케팅 인사이트'를 뽑아라.\n\n"
        f"[실시간 한국 검색 트렌드]\n{trend_lines}\n\n"
        f"[20-30대 여성 관심사 검색 추이(네이버 데이터랩, 최근 vs 과거)]\n{dl_lines}\n\n"
        f"[오늘 뜨는 글로벌 프로덕트(Product Hunt)]\n{ph_lines}\n\n"
        f"[글로벌 테크 화제(Hacker News)]\n{hn_lines}\n\n"
        f"[참고 — 우리 앱]\n{app_lines}\n\n"
        "20-30대 여성 마케팅 관점에서 인사이트 5개를 뽑아줘. 검색 추이가 오르는/내리는 신호와 "
        "실시간 트렌드를 엮어, 무엇을 언제 어떤 각도로 밀면 좋을지 구체적으로. 우리 앱과 엮이면 "
        "엮되 거기 갇히지 말 것. 뻔한 말·일반론 금지. 각 인사이트는 한 줄:\n"
        "• [포착한 신호] → [마케팅 시사점 / 콘텐츠·채널 각도]\n"
        "다른 말 없이 5줄만 출력."
    )
    return await _generate(client, prompt, 900)
