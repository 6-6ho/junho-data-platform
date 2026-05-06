from datetime import date, datetime
from . import db


DISTRICT_NAMES = {
    "11290": "성북",
    "11230": "동대문",
    "11140": "중구",
    "11200": "성동",
}


def _district_name(bjd_code: str | None) -> str:
    if not bjd_code:
        return "기타"
    return DISTRICT_NAMES.get(bjd_code[:5], "기타")


async def listings_grouped_by_day(days: int = 14) -> list[dict]:
    """Return rows grouped by KST date of first_seen_at, newest day first."""
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                (first_seen_at AT TIME ZONE 'Asia/Seoul')::date AS day,
                id, source, item_id, room_type, service_type, deposit, rent, manage_cost,
                area_m2, floor, all_floors, title, address_local, jibun_address, bjd_code,
                image_thumbnail, detail_url, first_seen_at, status
            FROM realestate.listings
            WHERE first_seen_at >= NOW() - ($1::int * INTERVAL '1 day')
            ORDER BY first_seen_at DESC, id DESC
            """,
            days,
        )

    grouped: dict[date, list[dict]] = {}
    for r in rows:
        d = r["day"]
        item = dict(r)
        item["district"] = _district_name(item.get("bjd_code"))
        grouped.setdefault(d, []).append(item)
    # Days that ran but had 0 new — show those too (look at scrape_runs)
    async with pool.acquire() as conn:
        run_rows = await conn.fetch(
            """
            SELECT (started_at AT TIME ZONE 'Asia/Seoul')::date AS day,
                   MAX(started_at) AS started_at,
                   SUM(new_count)::int AS new_count
            FROM realestate.scrape_runs
            WHERE started_at >= NOW() - ($1::int * INTERVAL '1 day')
              AND status = 'ok'
            GROUP BY 1
            ORDER BY 1 DESC
            """,
            days,
        )
    for r in run_rows:
        grouped.setdefault(r["day"], [])

    return [
        {"day": d, "listings": grouped[d]}
        for d in sorted(grouped.keys(), reverse=True)
    ]


async def latest_run() -> dict | None:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, started_at, finished_at, status, listed_count, new_count,
                   seen_count, error_message
            FROM realestate.scrape_runs
            ORDER BY started_at DESC
            LIMIT 1
            """
        )
    return dict(row) if row else None


async def total_active() -> int:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT COUNT(*) FROM realestate.listings WHERE status = 'open'"
        )


async def district_counts() -> list[dict]:
    """List of {name, count} for each district present, ordered by count desc."""
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT LEFT(bjd_code, 5) AS prefix, COUNT(*) AS n
            FROM realestate.listings
            WHERE status = 'open'
            GROUP BY 1 ORDER BY 2 DESC
            """
        )
    return [
        {"name": _district_name(r["prefix"]), "prefix": r["prefix"], "count": r["n"]}
        for r in rows
    ]
