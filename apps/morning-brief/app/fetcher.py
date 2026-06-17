"""GeekNews + GitHub Trending 수집·파싱 (httpx + BeautifulSoup).

- GeekNews 리스트(news.hada.io/new)는 최신순. 각 토픽 행에 절대 날짜(data-date)가
  있어 '어제 KST' 필터링이 정확하다. points = <span id='tp{id}'>.
- GitHub Trending 은 article.Box-row, "N stars today" 텍스트로 오늘 증가분 파싱.
"""
from __future__ import annotations

import logging
import re
from datetime import date

import httpx
from bs4 import BeautifulSoup

from . import config

log = logging.getLogger(__name__)

# 단순 홍보/구인/이벤트 제외 (제목 키워드)
EXCLUDE_KW = ("채용", "구인", "모집", "후원", "광고", "이벤트", "할인", "프로모션", "출시 기념")


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": config.HTTP_UA},
        timeout=30,
        follow_redirects=True,
    )


# ---------------------------- GeekNews ----------------------------

def parse_geeknews_rows(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict] = []
    for row in soup.select("div.topic_row"):
        tid = row.get("data-topic-state-id")
        title_a = row.select_one(".topictitle a")
        h2 = row.select_one("h2.topic-title-heading")
        if not (tid and title_a and h2):
            continue
        pts_el = row.select_one(f"#tp{tid}")
        pts_txt = pts_el.get_text(strip=True) if pts_el else ""
        time_el = row.select_one("time")
        desc_el = row.select_one(".topicdesc a")
        cmt_el = row.select_one("a[data-topic-comment-count]")
        rows.append({
            "id": tid,
            "title": h2.get_text(strip=True),
            "url": title_a.get("href", ""),
            "topic_url": f"{config.GEEKNEWS_BASE}/topic?id={tid}",
            "points": int(pts_txt) if pts_txt.isdigit() else 0,
            "comments": int(cmt_el.get("data-topic-comment-count") or 0) if cmt_el else 0,
            "date": time_el.get("data-date") if time_el else None,
            "desc": desc_el.get_text(strip=True) if desc_el else "",
        })
    return rows


async def fetch_geeknews_for_date(target: date) -> list[dict]:
    """target(KST 날짜)에 올라온 글만 모아 추천수 내림차순 Top N. 리스트는 최신순이라
    target 보다 오래된 글이 나오면 페이지네이션 중단."""
    target_s = target.isoformat()
    collected: list[dict] = []
    async with _client() as client:
        for page in range(1, config.GEEKNEWS_MAX_PAGES + 1):
            url = f"{config.GEEKNEWS_BASE}/new" + (f"?page={page}" if page > 1 else "")
            r = await client.get(url)
            r.raise_for_status()
            rows = parse_geeknews_rows(r.text)
            if not rows:
                break
            collected.extend(row for row in rows if row["date"] == target_s)
            dates = [row["date"] for row in rows if row["date"]]
            if dates and min(dates) < target_s:
                break
    items = [r for r in collected if not any(kw in r["title"] for kw in EXCLUDE_KW)]
    items.sort(key=lambda r: r["points"], reverse=True)
    return items[: config.TOP_N]


async def fetch_topic_body(client: httpx.AsyncClient, topic_url: str, fallback: str = "") -> str:
    """토픽 상세(#contents)의 본문 텍스트. 실패 시 fallback(리스트 미리보기)."""
    try:
        r = await client.get(topic_url)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        node = soup.find(id="contents")
        if node:
            txt = re.sub(r"\s+", " ", node.get_text(" ", strip=True))
            if len(txt) > 40:
                return txt[:2400]
    except Exception as e:  # noqa: BLE001
        log.warning("topic body fetch failed %s: %s", topic_url, e)
    return fallback


# ---------------------------- GitHub ----------------------------

def parse_github_rows(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[dict] = []
    for art in soup.select("article.Box-row"):
        h2a = art.select_one("h2 a")
        if not h2a:
            continue
        href = h2a.get("href", "").strip("/")
        desc_el = art.select_one("p")
        lang_el = art.select_one("[itemprop=programmingLanguage]")
        stars_today = 0
        for span in art.select("span"):
            m = re.match(r"([\d,]+)\s+stars today", span.get_text(strip=True))
            if m:
                stars_today = int(m.group(1).replace(",", ""))
                break
        out.append({
            "repo": href,
            "url": "https://github.com/" + href,
            "description": desc_el.get_text(strip=True) if desc_el else "",
            "language": lang_el.get_text(strip=True) if lang_el else "",
            "stars_today": stars_today,
        })
    return out


async def fetch_github() -> list[dict]:
    async with _client() as client:
        r = await client.get(config.GITHUB_TRENDING_URL)
        r.raise_for_status()
        rows = parse_github_rows(r.text)
    rows.sort(key=lambda x: x["stars_today"], reverse=True)
    return rows[: config.TOP_N]


async def fetch_readme(client: httpx.AsyncClient, repo: str) -> str:
    """설명이 부실한 레포의 README 앞부분. 기본 브랜치 추정(main→master)."""
    for branch in ("main", "master"):
        for name in ("README.md", "readme.md", "README.rst"):
            try:
                r = await client.get(f"https://raw.githubusercontent.com/{repo}/{branch}/{name}")
                if r.status_code == 200 and r.text.strip():
                    return r.text[:2000]
            except Exception:  # noqa: BLE001
                continue
    return ""
