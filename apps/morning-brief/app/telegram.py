"""브리핑을 텔레그램으로 발송 (Bot API sendMessage, HTML parse_mode).

TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 가 둘 다 있을 때만 동작. 4096자 제한이 있어
필요하면 메시지를 여러 개로 분할.
"""
from __future__ import annotations

import logging

import httpx

from . import config

log = logging.getLogger(__name__)

API = "https://api.telegram.org/bot{token}/sendMessage"
LIMIT = 3900  # 텔레그램 4096 한도 여유


def enabled() -> bool:
    return bool(config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID)


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_messages(brief: dict) -> list[str]:
    head = f"🌅 <b>Morning Brief {brief['run_date']}</b>"

    blocks: list[str] = []

    gk = brief.get("geeknews") or []
    lines = [f"📰 <b>GeekNews</b> · 어제 {brief.get('geeknews_date', '')}"]
    if gk:
        for it in gk:
            lines.append(
                f"\n<b>{it['rank']}.</b> <a href=\"{_esc(it['url'])}\">{_esc(it['title'])}</a>"
                f"  👍{it['points']} 💬{it['comments']}"
            )
            if it.get("summary"):
                lines.append(f"<i>{_esc(it['summary'])}</i>")
    else:
        lines.append("(어제자 글 없음)")
    blocks.append("\n".join(lines))

    gh = brief.get("github") or []
    lines = ["🐙 <b>GitHub Trending · Python</b> · 오늘"]
    if gh:
        for it in gh:
            lang = f" · {_esc(it['language'])}" if it.get("language") else ""
            lines.append(
                f"\n<b>{it['rank']}.</b> <a href=\"{_esc(it['url'])}\">{_esc(it['repo'])}</a>"
                f"  ⭐+{it['stars_today']}{lang}"
            )
            if it.get("summary"):
                lines.append(f"<i>{_esc(it['summary'])}</i>")
    else:
        lines.append("(수집 실패)")
    blocks.append("\n".join(lines))

    # head + 블록을 LIMIT 안에서 메시지로 묶기
    msgs: list[str] = []
    cur = head
    for b in blocks:
        if len(cur) + len(b) + 2 > LIMIT:
            msgs.append(cur)
            cur = b
        else:
            cur = f"{cur}\n\n{b}"
    if cur:
        msgs.append(cur)

    # 한 블록이 그래도 너무 길면 줄 단위로 더 쪼갬
    final: list[str] = []
    for m in msgs:
        while len(m) > LIMIT:
            cut = m.rfind("\n", 0, LIMIT)
            cut = cut if cut > 0 else LIMIT
            final.append(m[:cut])
            m = m[cut:].lstrip("\n")
        if m:
            final.append(m)
    return final


async def send_brief(brief: dict) -> bool:
    if not enabled():
        return False
    url = API.format(token=config.TELEGRAM_BOT_TOKEN)
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            for msg in build_messages(brief):
                r = await client.post(url, json={
                    "chat_id": config.TELEGRAM_CHAT_ID,
                    "text": msg,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                })
                if r.status_code != 200:
                    log.warning("telegram send failed %s: %s", r.status_code, r.text[:200])
                    return False
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("telegram error: %s", e)
        return False
