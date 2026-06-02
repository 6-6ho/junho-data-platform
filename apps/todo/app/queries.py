import json

from . import db


async def get_board() -> dict:
    """공유 보드의 카드 배열 + 현재 rev 반환. asyncpg 는 jsonb 를 str 로 줄 수 있어 파싱."""
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT data, rev FROM todo.board WHERE id = 1")
    if not row:
        return {"tasks": [], "rev": 0}
    data = row["data"]
    tasks = data if isinstance(data, list) else json.loads(data or "[]")
    return {"tasks": tasks, "rev": row["rev"]}


async def save_board(tasks: list, base_rev: int, updated_by: str | None = None) -> dict | None:
    """base_rev 가 현재 rev 와 같을 때만 저장 (낙관적 잠금). 성공 시 {'rev': new_rev}.
    충돌(그 사이 다른 사람이 저장해 rev 가 바뀜) 시 None — 호출부가 409 + 최신본을 돌려준다."""
    pool = await db.get_pool()
    payload = json.dumps(tasks, ensure_ascii=False)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE todo.board
            SET data = $1::jsonb, rev = rev + 1, updated_at = NOW(), updated_by = $2
            WHERE id = 1 AND rev = $3
            RETURNING rev
            """,
            payload, updated_by, base_rev,
        )
    return {"rev": row["rev"]} if row else None
