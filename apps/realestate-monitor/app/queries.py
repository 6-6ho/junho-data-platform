from datetime import date, datetime
from . import db


async def listings_grouped_by_day(days: int = 14) -> list[dict]:
    """Return rows grouped by KST date of first_seen_at, newest day first."""
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                (first_seen_at AT TIME ZONE 'Asia/Seoul')::date AS day,
                id, source, item_id, room_type, service_type, deposit, rent, manage_cost,
                area_m2, floor, all_floors, title, address_local, jibun_address,
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
        grouped.setdefault(d, []).append(dict(r))
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
