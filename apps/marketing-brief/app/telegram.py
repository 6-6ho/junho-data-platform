"""마케팅 브리핑을 텔레그램으로 발송 (Bot API sendMessage, HTML)."""
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


def _dl_arrow(d: dict) -> str:
    return {"up": "▲", "down": "▼"}.get(d.get("dir"), "→")


def build_messages(brief: dict) -> list[str]:
    head = f"📈 <b>Marketing Brief {brief['run_date']}</b>  <i>돈 쓰는 세대 타겟</i>"
    blocks: list[str] = []

    if brief.get("ideas"):
        blocks.append("💡 <b>오늘의 마케팅 인사이트</b>\n" + _esc(brief["ideas"]))

    nv = brief.get("naver") or []
    if nv:
        lines = ["📊 <b>세그먼트별 관심사 추이</b> <i>(최근 vs 과거)</i>"]
        for seg in nv:
            ups = [x for x in seg.get("items", []) if x["dir"] == "up"][:3]
            downs = [x for x in seg.get("items", []) if x["dir"] == "down"][-2:]
            tops = ups + downs
            chips = "  ".join(f"{_dl_arrow(x)}{_esc(x['name'])} {'+' if x['pct']>=0 else ''}{x['pct']}%" for x in tops)
            lines.append(f"<b>{_esc(seg['segment'])}</b>\n{chips}")
        blocks.append("\n".join(lines))

    tr = brief.get("trends") or []
    lines = ["🔥 <b>오늘 한국 실시간 검색</b>"]
    for t in tr:
        traf = f" <i>({_esc(t['traffic'])})</i>" if t.get("traffic") else ""
        lines.append(f"• {_esc(t['title'])}{traf}")
    blocks.append("\n".join(lines) if tr else "")

    ph = brief.get("producthunt") or []
    lines = ["🚀 <b>오늘 뜨는 프로덕트 (Product Hunt)</b>"]
    for p in ph:
        tg = f" — {_esc(p['tagline'])}" if p.get("tagline") else ""
        lines.append(f"<b>{p['rank']}.</b> <a href=\"{_esc(p['url'])}\">{_esc(p['name'])}</a>{tg}")
    blocks.append("\n".join(lines) if ph else "")

    hn = brief.get("hackernews") or []
    lines = ["💻 <b>글로벌 화제 (Hacker News)</b>"]
    for h in hn:
        lines.append(f"<b>{h['rank']}.</b> <a href=\"{_esc(h['url'])}\">{_esc(h['title'])}</a>  ▲{h['points']}")
    blocks.append("\n".join(lines) if hn else "")

    if brief.get("ideas"):
        blocks.append("💡 <b>오늘의 콘텐츠 아이디어</b>\n" + _esc(brief["ideas"]))

    blocks = [b for b in blocks if b]

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
                r = await client.post(url, json={
                    "chat_id": config.TELEGRAM_CHAT_ID, "text": msg,
                    "parse_mode": "HTML", "disable_web_page_preview": True,
                })
                if r.status_code != 200:
                    log.warning("telegram send failed %s: %s", r.status_code, r.text[:200])
                    return False
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("telegram error: %s", e)
        return False
