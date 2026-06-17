import json
from datetime import date

from . import db


def _ser(row) -> dict | None:
    if not row:
        return None
    d = dict(row)
    for k in ("trends", "producthunt", "hackernews"):
        v = d.get(k)
        if isinstance(v, str):
            d[k] = json.loads(v or "[]")
    for k in ("run_date", "generated_at"):
        if d.get(k) is not None:
            d[k] = d[k].isoformat()
    return d


async def save_brief(run_date: date, trends: list, producthunt: list, hackernews: list,
                     ideas: str, status: str, error: str | None) -> None:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO marketing.daily
                (run_date, trends, producthunt, hackernews, ideas, status, error, generated_at)
            VALUES ($1, $2::jsonb, $3::jsonb, $4::jsonb, $5, $6, $7, NOW())
            ON CONFLICT (run_date) DO UPDATE SET
                trends=$2::jsonb, producthunt=$3::jsonb, hackernews=$4::jsonb,
                ideas=$5, status=$6, error=$7, generated_at=NOW()
            """,
            run_date,
            json.dumps(trends, ensure_ascii=False),
            json.dumps(producthunt, ensure_ascii=False),
            json.dumps(hackernews, ensure_ascii=False),
            ideas, status, error,
        )


async def latest_brief() -> dict | None:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM marketing.daily ORDER BY run_date DESC LIMIT 1")
    return _ser(row)


async def brief_by_date(d: date) -> dict | None:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM marketing.daily WHERE run_date = $1", d)
    return _ser(row)


async def recent_dates(limit: int = 30) -> list[str]:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT run_date FROM marketing.daily ORDER BY run_date DESC LIMIT $1", limit
        )
    return [r["run_date"].isoformat() for r in rows]
