import json
from datetime import date

from . import db

_COLS = "id, title, category, status, priority, due_date, memo, sort_order, created_at, updated_at, done_at"


def serialize(r) -> dict:
    d = dict(r)
    for k in ("due_date", "created_at", "updated_at", "done_at"):
        v = d.get(k)
        if v is not None:
            d[k] = v.isoformat()
    return d


def _parse_due(due_date) -> date | None:
    if not due_date:
        return None
    if isinstance(due_date, date):
        return due_date
    return date.fromisoformat(str(due_date))


async def all_tasks() -> list[dict]:
    """Every task (all statuses), ordered for stable rendering."""
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT {_COLS} FROM todo.tasks "
            "ORDER BY sort_order ASC, created_at DESC, id DESC"
        )
    return [serialize(r) for r in rows]


async def list_tasks(status: str | None = None, category: str | None = None) -> list[dict]:
    pool = await db.get_pool()
    clauses, args = [], []
    if status:
        args.append(status)
        clauses.append(f"status = ${len(args)}")
    if category:
        args.append(category)
        clauses.append(f"category = ${len(args)}")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT {_COLS} FROM todo.tasks {where} "
            "ORDER BY status, sort_order ASC, created_at DESC",
            *args,
        )
    return [serialize(r) for r in rows]


async def get_task(task_id: int) -> dict | None:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"SELECT {_COLS} FROM todo.tasks WHERE id = $1", task_id)
    return serialize(row) if row else None


async def add_task(
    title: str,
    category: str | None = None,
    due_date=None,
    priority: str | None = None,
    memo: str | None = None,
    status: str = "todo",
) -> dict:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        # new task goes to the top of its column
        min_order = await conn.fetchval(
            "SELECT COALESCE(MIN(sort_order), 0) - 1 FROM todo.tasks WHERE status = $1",
            status,
        )
        row = await conn.fetchrow(
            f"""
            INSERT INTO todo.tasks (title, category, status, priority, due_date, memo, sort_order, done_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, CASE WHEN $3 = 'done' THEN NOW() END)
            RETURNING {_COLS}
            """,
            title, category or None, status, priority or None,
            _parse_due(due_date), memo or None, min_order,
        )
    return serialize(row)


async def update_task(task_id: int, **fields) -> dict | None:
    allowed = {"title", "category", "priority", "due_date", "memo"}
    sets, args = [], []
    for k, v in fields.items():
        if k not in allowed:
            continue
        if k == "title" and not (v or "").strip():
            continue  # title is NOT NULL — never clear it
        # a present key with empty/None value clears the column (SET NULL)
        args.append(_parse_due(v) if k == "due_date" else (v or None))
        sets.append(f"{k} = ${len(args)}")
    if not sets:
        return await get_task(task_id)
    sets.append("updated_at = NOW()")
    args.append(task_id)
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE todo.tasks SET {', '.join(sets)} WHERE id = ${len(args)} RETURNING {_COLS}",
            *args,
        )
    return serialize(row) if row else None


async def set_status(task_id: int, status: str) -> dict | None:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""
            UPDATE todo.tasks
            SET status = $2,
                done_at = CASE WHEN $2 = 'done' THEN NOW() ELSE NULL END,
                updated_at = NOW()
            WHERE id = $1
            RETURNING {_COLS}
            """,
            task_id, status,
        )
    return serialize(row) if row else None


async def reorder(status: str, ids: list[int]) -> int:
    """Set the given column's membership + order. Cross-column moves land here:
    the moved id is included in `ids` with the target `status`."""
    if not ids:
        return 0
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            for idx, tid in enumerate(ids):
                await conn.execute(
                    """
                    UPDATE todo.tasks
                    SET status = $2, sort_order = $3,
                        done_at = CASE WHEN $2 = 'done' THEN COALESCE(done_at, NOW()) ELSE NULL END,
                        updated_at = NOW()
                    WHERE id = $1
                    """,
                    tid, status, idx,
                )
    return len(ids)


async def delete_task(task_id: int) -> bool:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM todo.tasks WHERE id = $1", task_id)
    return result.endswith("1")


async def clear_done() -> int:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM todo.tasks WHERE status = 'done'")
    return int(result.split()[-1]) if result.startswith("DELETE") else 0


async def categories() -> list[str]:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT DISTINCT category FROM todo.tasks "
            "WHERE category IS NOT NULL AND category <> '' ORDER BY category"
        )
    return [r["category"] for r in rows]


# ===================== 공유 칸반 보드 (JSONB single-row) =====================

async def get_board() -> list[dict]:
    """공유 보드의 카드 배열 전체를 반환. asyncpg 는 jsonb 를 str 로 주므로 파싱."""
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT data FROM todo.board WHERE id = 1")
    if not row or row["data"] is None:
        return []
    data = row["data"]
    return data if isinstance(data, list) else json.loads(data)


async def save_board(tasks: list, updated_by: str | None = None) -> None:
    """카드 배열 전체를 통째로 저장 (last-write-wins)."""
    pool = await db.get_pool()
    payload = json.dumps(tasks, ensure_ascii=False)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO todo.board (id, data, updated_at, updated_by)
            VALUES (1, $1::jsonb, NOW(), $2)
            ON CONFLICT (id) DO UPDATE SET data = $1::jsonb, updated_at = NOW(), updated_by = $2
            """,
            payload, updated_by,
        )
