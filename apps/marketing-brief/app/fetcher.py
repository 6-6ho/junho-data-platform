"""마케팅 소스 수집 — Google Trends KR RSS, Product Hunt RSS, Hacker News(Algolia).

전부 무료·무인증. RSS 는 정규식 + html.unescape 로 파싱 (ht: 네임스페이스 단순 처리).
"""
from __future__ import annotations

import html
import logging
import re

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
