import json
from datetime import date

from . import db


def _ser(row) -> dict | None:
    if not row:
        return None
    d = dict(row)
    for k in ("geeknews", "github"):
        v = d.get(k)
        if isinstance(v, str):
            d[k] = json.loads(v or "[]")
    for k in ("run_date", "geeknews_date", "generated_at"):
        if d.get(k) is not None:
            d[k] = d[k].isoformat()
    return d


async def save_brief(run_date: date, geeknews_date: date, geeknews: list,
                     github: list, status: str, error: str | None) -> None:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO brief.daily (run_date, geeknews_date, geeknews, github, status, error, generated_at)
            VALUES ($1, $2, $3::jsonb, $4::jsonb, $5, $6, NOW())
            ON CONFLICT (run_date) DO UPDATE SET
                geeknews_date = $2, geeknews = $3::jsonb, github = $4::jsonb,
                status = $5, error = $6, generated_at = NOW()
            """,
            run_date, geeknews_date,
            json.dumps(geeknews, ensure_ascii=False),
            json.dumps(github, ensure_ascii=False),
            status, error,
        )


async def latest_brief() -> dict | None:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM brief.daily ORDER BY run_date DESC LIMIT 1")
    return _ser(row)


async def brief_by_date(d: date) -> dict | None:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM brief.daily WHERE run_date = $1", d)
    return _ser(row)


async def recent_dates(limit: int = 30) -> list[str]:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT run_date FROM brief.daily ORDER BY run_date DESC LIMIT $1", limit
        )
    return [r["run_date"].isoformat() for r in rows]
