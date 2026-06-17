"""마케팅 브리핑 오케스트레이션: 수집(독립 try) → 콘텐츠 아이디어 합성 → 저장 → 텔레그램."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from . import config, fetcher, queries, summarizer, telegram

log = logging.getLogger(__name__)
KST = timezone(timedelta(hours=9))


async def run_brief(notify: bool = True) -> dict:
    run_date = datetime.now(KST).date()
    errors: list[str] = []

    trends: list[dict] = []
    try:
        trends = await fetcher.fetch_trends()
    except Exception as e:  # noqa: BLE001
        log.exception("trends failed")
        errors.append(f"trends: {e}")

    products: list[dict] = []
    try:
        products = await fetcher.fetch_producthunt()
    except Exception as e:  # noqa: BLE001
        log.exception("producthunt failed")
        errors.append(f"producthunt: {e}")

    hn: list[dict] = []
    try:
        hn = await fetcher.fetch_hackernews()
    except Exception as e:  # noqa: BLE001
        log.exception("hackernews failed")
        errors.append(f"hackernews: {e}")

    naver: list[dict] = []
    try:
        naver = await fetcher.fetch_datalab()
    except Exception as e:  # noqa: BLE001
        log.exception("datalab failed")
        errors.append(f"datalab: {e}")

    ideas = ""
    if trends or products or hn or naver:
        try:
            async with fetcher._client() as client:
                ideas = await summarizer.marketing_insights(
                    client, trends, products, hn, naver, config.APPS)
        except Exception as e:  # noqa: BLE001
            log.exception("insights failed")
            errors.append(f"insights: {e}")

    status = "ok" if (trends or products or hn or naver) else "failed"
    error = " | ".join(errors) or None
    await queries.save_brief(run_date, trends, products, hn, naver, ideas, status, error)

    sent = False
    if notify and status == "ok" and telegram.enabled():
        sent = await telegram.send_brief({
            "run_date": run_date.isoformat(),
            "trends": trends, "producthunt": products, "hackernews": hn,
            "naver": naver, "ideas": ideas,
        })

    log.info("marketing brief %s: trends=%d ph=%d hn=%d naver=%d ideas=%s telegram=%s status=%s",
             run_date, len(trends), len(products), len(hn), len(naver), bool(ideas), sent, status)
    return {
        "run_date": run_date.isoformat(),
        "trends": len(trends), "producthunt": len(products), "hackernews": len(hn),
        "naver": len(naver), "ideas": bool(ideas),
        "status": status, "error": error, "telegram": sent,
    }
