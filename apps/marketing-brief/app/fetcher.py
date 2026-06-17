"""마케팅 소스 수집 — Google Trends KR RSS, Product Hunt RSS, Hacker News(Algolia).

전부 무료·무인증. RSS 는 정규식 + html.unescape 로 파싱 (ht: 네임스페이스 단순 처리).
"""
from __future__ import annotations

import html
import logging
import re
from datetime import date, timedelta

import httpx

from . import config

log = logging.getLogger(__name__)


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": config.HTTP_UA}, timeout=30, follow_redirects=True
    )


def _txt(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


# ---------------------- Google Trends KR ----------------------

def parse_trends(xml: str) -> list[dict]:
    out: list[dict] = []
    for it in re.findall(r"<item>(.*?)</item>", xml, re.S):
        m = re.search(r"<title>(.*?)</title>", it, re.S)
        if not m:
            continue
        traffic = re.search(r"<ht:approx_traffic>(.*?)</ht:approx_traffic>", it)
        n_titles = re.findall(r"<ht:news_item_title>(.*?)</ht:news_item_title>", it, re.S)
        n_urls = re.findall(r"<ht:news_item_url>(.*?)</ht:news_item_url>", it, re.S)
        news = [{"title": _txt(t), "url": _txt(u)} for t, u in zip(n_titles, n_urls)][:2]
        out.append({
            "title": _txt(m.group(1)),
            "traffic": _txt(traffic.group(1)) if traffic else "",
            "news": news,
        })
    return out


async def fetch_trends() -> list[dict]:
    async with _client() as c:
        r = await c.get(config.GOOGLE_TRENDS_KR_RSS)
        r.raise_for_status()
        rows = parse_trends(r.text)
    return rows[: config.TOP_TRENDS]


# ---------------------- Product Hunt ----------------------

def parse_producthunt(xml: str) -> list[dict]:
    # Product Hunt 피드는 Atom (<entry>). link 은 href 속성, tagline 은 <content> 안에 escape.
    out: list[dict] = []
    for it in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
        title = re.search(r"<title>(.*?)</title>", it, re.S)
        link = re.search(r'<link[^>]*rel="alternate"[^>]*href="([^"]+)"', it)
        content = re.search(r"<content[^>]*>(.*?)</content>", it, re.S)
        if not title:
            continue
        tagline = ""
        if content:
            unescaped = html.unescape(content.group(1))
            p = re.search(r"<p>(.*?)</p>", unescaped, re.S)
            tagline = _txt(p.group(1) if p else unescaped)
        out.append({
            "name": _txt(title.group(1)),
            "url": link.group(1) if link else "",
            "tagline": tagline[:200],
        })
    return out


async def fetch_producthunt() -> list[dict]:
    async with _client() as c:
        r = await c.get(config.PRODUCTHUNT_RSS)
        r.raise_for_status()
        rows = parse_producthunt(r.text)
    for i, row in enumerate(rows[: config.TOP_PH], 1):
        row["rank"] = i
    return rows[: config.TOP_PH]


# ---------------------- Hacker News ----------------------

async def _datalab_segment(c: httpx.AsyncClient, headers: dict, seg: dict,
                           start: str, end: str) -> list[dict]:
    groups = config.INTEREST_GROUPS
    items: list[dict] = []
    for i in range(0, len(groups), 5):
        body = {
            "startDate": start, "endDate": end, "timeUnit": "week",
            "ages": seg["ages"], "keywordGroups": groups[i:i + 5],
        }
        if seg.get("gender"):
            body["gender"] = seg["gender"]
        r = await c.post(config.NAVER_DATALAB_URL, headers=headers, json=body)
        r.raise_for_status()
        for res in r.json().get("results", []):
            series = [d["ratio"] for d in res.get("data", [])][:-1]  # 진행중 주 제외
            if len(series) < 6:
                continue
            recent = sum(series[-3:]) / 3
            earlier = sum(series[:3]) / 3
            pct = round((recent - earlier) / earlier * 100) if earlier else 0
            items.append({
                "name": res["title"], "pct": pct,
                "dir": "up" if pct > 12 else ("down" if pct < -12 else "flat"),
            })
    items.sort(key=lambda x: x["pct"], reverse=True)
    return items


async def fetch_datalab() -> list[dict]:
    """네이버 데이터랩 — '돈 쓰는 세대' 여러 세그먼트별 관심사 검색 추이.
    각 키워드 최근(완성 주) vs 과거 비교로 상승/하락 %. 반환: [{segment, items[]}]."""
    if not (config.NAVER_CLIENT_ID and config.NAVER_CLIENT_SECRET):
        return []
    end = date.today().isoformat()
    start = (date.today() - timedelta(days=120)).isoformat()
    headers = {
        "X-Naver-Client-Id": config.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": config.NAVER_CLIENT_SECRET,
        "Content-Type": "application/json",
    }
    out: list[dict] = []
    async with _client() as c:
        for seg in config.SEGMENTS:
            try:
                items = await _datalab_segment(c, headers, seg, start, end)
            except Exception as e:  # noqa: BLE001
                log.warning("datalab segment %s failed: %s", seg["label"], e)
                items = []
            if items:
                out.append({"segment": seg["label"], "items": items})
    return out


async def fetch_hackernews() -> list[dict]:
    async with _client() as c:
        r = await c.get(config.HN_ALGOLIA_URL)
        r.raise_for_status()
        hits = r.json().get("hits", [])
    out: list[dict] = []
    for i, h in enumerate(hits[: config.TOP_HN], 1):
        oid = h.get("objectID", "")
        out.append({
            "rank": i,
            "title": h.get("title") or h.get("story_title") or "",
            "url": h.get("url") or f"https://news.ycombinator.com/item?id={oid}",
            "points": h.get("points", 0),
            "comments": h.get("num_comments", 0),
        })
    return out
