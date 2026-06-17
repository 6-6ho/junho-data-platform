"""Gemini 요약 (httpx → Generative Language REST API).

- API 키는 URL 파라미터가 아니라 x-goog-api-key 헤더로 전달 (에러 로그에 키 노출 방지).
- 429(레이트/쿼터)는 한 번 백오프 후 재시도. 그래도 실패하면 빈 문자열 →
  호출부가 메타/미리보기로 폴백.
GEMINI_API_KEY 가 없으면 바로 빈 문자열.
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
            "temperature": 0.3,
            "maxOutputTokens": max_tokens,
            # gemini-2.5 는 thinking 모델 — 끄지 않으면 사고 토큰이 출력 예산을 먹어
            # 실제 요약이 몇 글자에서 잘린다. 단순 요약이라 thinking 0.
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    for attempt in range(2):
        try:
            r = await client.post(url, headers=headers, json=payload, timeout=45)
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


async def summarize_article(client: httpx.AsyncClient, title: str, body: str) -> str:
    prompt = (
        "다음 기술/개발 글을 한국어 2~3줄로 핵심만 요약해줘. "
        "마케팅·홍보 톤은 빼고 기술 디테일 중심으로, 군더더기 없이.\n\n"
        f"제목: {title}\n\n본문:\n{body[:2000]}\n\n요약(2~3줄):"
    )
    return await _generate(client, prompt, 400)


async def summarize_repo(client: httpx.AsyncClient, repo: str, content: str) -> str:
    prompt = (
        "다음 GitHub 저장소가 무엇을 하는 프로젝트인지 한국어 1~2줄로 간결히 설명해줘. "
        "과장 없이 무슨 도구/라이브러리인지 위주로.\n\n"
        f"저장소: {repo}\n설명/README:\n{content[:1800]}\n\n한국어 설명(1~2줄):"
    )
    return await _generate(client, prompt, 250)
