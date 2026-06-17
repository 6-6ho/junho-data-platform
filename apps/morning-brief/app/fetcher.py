"""통합 브리핑 수집 — 기술(GeekNews·GitHub) + 마케팅(읽을거리·트렌드·PH·데이터랩).

전부 무료·무인증(네이버 데이터랩만 키). RSS 는 정규식 + html.unescape 로 파싱.
"""
from __future__ import annotations

import html
import logging
import re
from datetime import date, timedelta

import httpx
from bs4 import BeautifulSoup

from . import config

log = logging.getLogger(__name__)

EXCLUDE_KW = ("채용", "구인", "모집", "후원", "광고", "이벤트", "할인", "프로모션", "출시 기념")


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(headers={"User-Agent": config.HTTP_UA}, timeout=30, follow_redirects=True)


def _txt(s: str) -> str:
    s = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", s or "", flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


# ============================ 기술: GeekNews ============================

def parse_geeknews_rows(html_text: str) -> list[dict]:
    soup = BeautifulSoup(html_text, "html.parser")
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


# ============================ 기술: GitHub ============================

def parse_github_rows(html_text: str) -> list[dict]:
    soup = BeautifulSoup(html_text, "html.parser")
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
            "repo": href, "url": "https://github.com/" + href,
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
    for i, row in enumerate(rows[: config.TOP_N], 1):
        row["rank"] = i
    return rows[: config.TOP_N]


async def fetch_readme(client: httpx.AsyncClient, repo: str) -> str:
    for branch in ("main", "master"):
        for name in ("README.md", "readme.md", "README.rst"):
            try:
                r = await client.get(f"https://raw.githubusercontent.com/{repo}/{branch}/{name}")
                if r.status_code == 200 and r.text.strip():
                    return r.text[:2000]
            except Exception:  # noqa: BLE001
                continue
    return ""


# ============================ 마케팅: 읽을거리 ============================

async def fetch_marketing_reads() -> list[dict]:
    """앱/마케팅 실무 매체 최신 기사 (모비인사이드·디지털인사이트)."""
    out: list[dict] = []
    async with _client() as c:
        for feed in config.MARKETING_FEEDS:
            try:
                r = await c.get(feed["url"])
                r.raise_for_status()
                for it in re.findall(r"<item>(.*?)</item>", r.text, re.S)[:4]:
                    title = re.search(r"<title>(.*?)</title>", it, re.S)
                    link = re.search(r"<link>(.*?)</link>", it, re.S)
                    if title and link:
                        out.append({"source": feed["source"], "title": _txt(title.group(1)), "url": _txt(link.group(1))})
            except Exception as e:  # noqa: BLE001
                log.warning("marketing feed %s failed: %s", feed["source"], e)
    return out[: config.TOP_READS]


# ============================ 마케팅: Google Trends KR ============================

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
        out.append({"title": _txt(m.group(1)), "traffic": _txt(traffic.group(1)) if traffic else "", "news": news})
    return out


async def fetch_trends() -> list[dict]:
    async with _client() as c:
        r = await c.get(config.GOOGLE_TRENDS_KR_RSS)
        r.raise_for_status()
        rows = parse_trends(r.text)
    return rows[: config.TOP_TRENDS]


# ============================ 마케팅: Product Hunt ============================

def parse_producthunt(xml: str) -> list[dict]:
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
        out.append({"name": _txt(title.group(1)), "url": link.group(1) if link else "", "tagline": tagline[:200]})
    return out


async def fetch_producthunt() -> list[dict]:
    async with _client() as c:
        r = await c.get(config.PRODUCTHUNT_RSS)
        r.raise_for_status()
        rows = parse_producthunt(r.text)
    for i, row in enumerate(rows[: config.TOP_PH], 1):
        row["rank"] = i
    return rows[: config.TOP_PH]


# ============================ 마케팅: 네이버 데이터랩 ============================

async def _datalab_segment(c: httpx.AsyncClient, headers: dict, seg: dict, start: str, end: str) -> list[dict]:
    groups = config.INTEREST_GROUPS
    items: list[dict] = []
    for i in range(0, len(groups), 5):
        body = {"startDate": start, "endDate": end, "timeUnit": "week", "ages": seg["ages"], "keywordGroups": groups[i:i + 5]}
        if seg.get("gender"):
            body["gender"] = seg["gender"]
        r = await c.post(config.NAVER_DATALAB_URL, headers=headers, json=body)
        r.raise_for_status()
        for res in r.json().get("results", []):
            series = [d["ratio"] for d in res.get("data", [])][:-1]
            if len(series) < 6:
                continue
            recent = sum(series[-3:]) / 3
            earlier = sum(series[:3]) / 3
            pct = round((recent - earlier) / earlier * 100) if earlier else 0
            items.append({"name": res["title"], "pct": pct, "dir": "up" if pct > 12 else ("down" if pct < -12 else "flat")})
    items.sort(key=lambda x: x["pct"], reverse=True)
    return items


async def fetch_datalab() -> list[dict]:
    if not (config.NAVER_CLIENT_ID and config.NAVER_CLIENT_SECRET):
        return []
    end = date.today().isoformat()
    start = (date.today() - timedelta(days=120)).isoformat()
    headers = {"X-Naver-Client-Id": config.NAVER_CLIENT_ID, "X-Naver-Client-Secret": config.NAVER_CLIENT_SECRET, "Content-Type": "application/json"}
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
