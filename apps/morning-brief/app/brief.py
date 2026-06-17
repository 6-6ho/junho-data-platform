"""통합 브리핑 — 기술(GeekNews·GitHub) + 마케팅(읽을거리·트렌드·PH·데이터랩·인사이트).

각 소스 독립 try. 한 곳 실패해도 나머지 진행.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from . import config, fetcher, queries, summarizer, telegram

log = logging.getLogger(__name__)
KST = timezone(timedelta(hours=9))


async def _geeknews(yesterday) -> list[dict]:
    raw = await fetcher.fetch_geeknews_for_date(yesterday)
    items: list[dict] = []
    async with fetcher._client() as client:
        for i, it in enumerate(raw, 1):
            body = await fetcher.fetch_topic_body(client, it["topic_url"], it["desc"])
            summary = await summarizer.summarize_article(client, it["title"], body or it["desc"])
            items.append({"rank": i, "title": it["title"], "url": it["url"], "topic_url": it["topic_url"],
                          "points": it["points"], "comments": it["comments"], "summary": summary or it["desc"]})
    return items


async def _github() -> list[dict]:
    raw = await fetcher.fetch_github()
    items: list[dict] = []
    async with fetcher._client() as client:
        for it in raw:
            content = it["description"]
            if len(content) < 30:
                content = (await fetcher.fetch_readme(client, it["repo"])) or content or it["repo"]
            summary = await summarizer.summarize_repo(client, it["repo"], content)
            items.append({"rank": it["rank"], "repo": it["repo"], "url": it["url"],
                          "language": it["language"], "stars_today": it["stars_today"],
                          "summary": summary or it["description"]})
    return items


async def run_brief(notify: bool = True) -> dict:
    now = datetime.now(KST)
    run_date = now.date()
    yesterday = run_date - timedelta(days=1)
    errors: list[str] = []

    async def _try(coro, name, default):
        try:
            return await coro
        except Exception as e:  # noqa: BLE001
            log.exception("%s failed", name)
            errors.append(f"{name}: {e}")
            return default

    geeknews = await _try(_geeknews(yesterday), "geeknews", [])
    github = await _try(_github(), "github", [])
    reads = await _try(fetcher.fetch_marketing_reads(), "reads", [])
    trends = await _try(fetcher.fetch_trends(), "trends", [])
    producthunt = await _try(fetcher.fetch_producthunt(), "producthunt", [])
    naver = await _try(fetcher.fetch_datalab(), "datalab", [])

    ideas = ""
    if reads or trends or producthunt or naver:
        try:
            async with fetcher._client() as client:
                ideas = await summarizer.marketing_insights(client, reads, trends, producthunt, naver, config.APPS)
        except Exception as e:  # noqa: BLE001
            log.exception("insights failed")
            errors.append(f"insights: {e}")

    got = geeknews or github or reads or trends or producthunt or naver
    status = "ok" if got else "failed"
    error = " | ".join(errors) or None
    await queries.save_brief(run_date, yesterday, geeknews, github, reads, trends,
                             producthunt, naver, ideas, status, error)

    sent = False
    if notify and status == "ok" and telegram.enabled():
        sent = await telegram.send_brief({
            "run_date": run_date.isoformat(), "geeknews_date": yesterday.isoformat(),
            "geeknews": geeknews, "github": github, "reads": reads, "trends": trends,
            "producthunt": producthunt, "naver": naver, "ideas": ideas,
        })

    log.info("brief %s: geek=%d gh=%d reads=%d trends=%d ph=%d naver=%d ideas=%s tg=%s",
             run_date, len(geeknews), len(github), len(reads), len(trends),
             len(producthunt), len(naver), bool(ideas), sent)
    return {"run_date": run_date.isoformat(), "geeknews": len(geeknews), "github": len(github),
            "reads": len(reads), "trends": len(trends), "producthunt": len(producthunt),
            "naver": len(naver), "ideas": bool(ideas), "status": status, "error": error, "telegram": sent}
