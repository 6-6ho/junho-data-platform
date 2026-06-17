"""통합 브리핑 텔레그램 발송 (HTML). 4096자 초과 시 분할."""
from __future__ import annotations

import logging

import httpx

from . import config

log = logging.getLogger(__name__)
API = "https://api.telegram.org/bot{token}/sendMessage"
LIMIT = 3900


def enabled() -> bool:
    return bool(config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID)


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _arrow(d: dict) -> str:
    return {"up": "▲", "down": "▼"}.get(d.get("dir"), "→")


def build_messages(brief: dict) -> list[str]:
    head = f"🌅 <b>Morning Brief {brief['run_date']}</b>"
    blocks: list[str] = []

    if brief.get("ideas"):
        blocks.append("💡 <b>오늘의 마케팅 인사이트</b>\n" + _esc(brief["ideas"]))

    reads = brief.get("reads") or []
    if reads:
        lines = ["📣 <b>마케팅 읽을거리</b>"]
        for r in reads:
            lines.append(f"• <a href=\"{_esc(r['url'])}\">{_esc(r['title'])}</a> <i>{_esc(r['source'])}</i>")
        blocks.append("\n".join(lines))

    nv = brief.get("naver") or []
    if nv:
        lines = ["📊 <b>세그먼트별 관심사 추이</b>"]
        for seg in nv:
            tops = [x for x in seg.get("items", []) if x["dir"] == "up"][:3] + [x for x in seg.get("items", []) if x["dir"] == "down"][-2:]
            chips = "  ".join(f"{_arrow(x)}{_esc(x['name'])} {'+' if x['pct']>=0 else ''}{x['pct']}%" for x in tops)
            lines.append(f"<b>{_esc(seg['segment'])}</b>\n{chips}")
        blocks.append("\n".join(lines))

    tr = brief.get("trends") or []
    if tr:
        lines = ["🔥 <b>오늘 한국 실시간 검색</b>"]
        for t in tr:
            traf = f" <i>({_esc(t['traffic'])})</i>" if t.get("traffic") else ""
            lines.append(f"• {_esc(t['title'])}{traf}")
        blocks.append("\n".join(lines))

    ph = brief.get("producthunt") or []
    if ph:
        lines = ["🚀 <b>Product Hunt</b>"]
        for p in ph:
            tg = f" — {_esc(p['tagline'])}" if p.get("tagline") else ""
            lines.append(f"<b>{p['rank']}.</b> <a href=\"{_esc(p['url'])}\">{_esc(p['name'])}</a>{tg}")
        blocks.append("\n".join(lines))

    gk = brief.get("geeknews") or []
    if gk:
        lines = [f"📰 <b>GeekNews · 어제</b>"]
        for it in gk:
            lines.append(f"<b>{it['rank']}.</b> <a href=\"{_esc(it['url'])}\">{_esc(it['title'])}</a>  👍{it['points']}")
            if it.get("summary"):
                lines.append(f"<i>{_esc(it['summary'])}</i>")
        blocks.append("\n".join(lines))

    gh = brief.get("github") or []
    if gh:
        lines = ["🐙 <b>GitHub Trending · Python</b>"]
        for it in gh:
            lines.append(f"<b>{it['rank']}.</b> <a href=\"{_esc(it['url'])}\">{_esc(it['repo'])}</a>  ⭐+{it['stars_today']}")
            if it.get("summary"):
                lines.append(f"<i>{_esc(it['summary'])}</i>")
        blocks.append("\n".join(lines))

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
                r = await client.post(url, json={"chat_id": config.TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML", "disable_web_page_preview": True})
                if r.status_code != 200:
                    log.warning("telegram send failed %s: %s", r.status_code, r.text[:200])
                    return False
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("telegram error: %s", e)
        return False
