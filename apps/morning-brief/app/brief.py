"""브리핑 오케스트레이션: 수집 → 필터/정렬 → 요약 → DB 저장.

각 트랙(GeekNews / GitHub)은 독립적으로 try — 한 쪽이 실패해도 다른 쪽은 진행.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from . import config, fetcher, queries, summarizer, telegram

log = logging.getLogger(__name__)
KST = timezone(timedelta(hours=9))


async def _track_geeknews(yesterday) -> list[dict]:
    raw = await fetcher.fetch_geeknews_for_date(yesterday)
    items: list[dict] = []
    async with fetcher._client() as client:
        for i, it in enumerate(raw, 1):
            body = await fetcher.fetch_topic_body(client, it["topic_url"], it["desc"])
            summary = await summarizer.summarize_article(client, it["title"], body or it["desc"])
            items.append({
                "rank": i,
                "title": it["title"],
                "url": it["url"],
                "topic_url": it["topic_url"],
                "points": it["points"],
                "comments": it["comments"],
                "summary": summary or it["desc"],
            })
    return items


async def _track_github() -> list[dict]:
    raw = await fetcher.fetch_github()
    items: list[dict] = []
    async with fetcher._client() as client:
        for i, it in enumerate(raw, 1):
            content = it["description"]
            if len(content) < 30:
                content = (await fetcher.fetch_readme(client, it["repo"])) or content or it["repo"]
            summary = await summarizer.summarize_repo(client, it["repo"], content)
            items.append({
                "rank": i,
                "repo": it["repo"],
                "url": it["url"],
                "language": it["language"],
                "stars_today": it["stars_today"],
                "summary": summary or it["description"],
            })
    return items


async def run_brief(notify: bool = True) -> dict:
    now = datetime.now(KST)
    run_date = now.date()
    yesterday = run_date - timedelta(days=1)
    errors: list[str] = []

    geeknews_items: list[dict] = []
    try:
        geeknews_items = await _track_geeknews(yesterday)
    except Exception as e:  # noqa: BLE001
        log.exception("geeknews track failed")
        errors.append(f"geeknews: {e}")

    github_items: list[dict] = []
    try:
        github_items = await _track_github()
    except Exception as e:  # noqa: BLE001
        log.exception("github track failed")
        errors.append(f"github: {e}")

    status = "ok" if (geeknews_items or github_items) else "failed"
    error = " | ".join(errors) or None
    await queries.save_brief(run_date, yesterday, geeknews_items, github_items, status, error)

    sent = False
    if notify and status == "ok" and telegram.enabled():
        sent = await telegram.send_brief({
            "run_date": run_date.isoformat(),
            "geeknews_date": yesterday.isoformat(),
            "geeknews": geeknews_items,
            "github": github_items,
        })

    log.info("brief %s: geeknews=%d github=%d status=%s telegram=%s",
             run_date, len(geeknews_items), len(github_items), status, sent)
    return {
        "run_date": run_date.isoformat(),
        "geeknews_date": yesterday.isoformat(),
        "geeknews": len(geeknews_items),
        "github": len(github_items),
        "status": status,
        "error": error,
        "telegram": sent,
    }
