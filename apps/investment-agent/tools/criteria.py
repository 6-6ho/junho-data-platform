"""투자 기준 CRUD."""
import json
from db import execute_query, execute_command


def save_criteria(name: str, content: str, category: str = "general") -> str:
    """투자 기준 저장 (이름 중복 시 업데이트)."""
    result = execute_command("""
        INSERT INTO investment_criteria (name, content, category, updated_at)
        VALUES (%s, %s, %s, NOW())
        ON CONFLICT (name) DO UPDATE SET
            content = EXCLUDED.content,
            category = EXCLUDED.category,
            updated_at = NOW()
        RETURNING id, name
    """, (name, content, category))
    return json.dumps({
        "status": "saved",
        "id": result[0],
        "name": result[1],
        "category": category,
    }, ensure_ascii=False)


def list_criteria(category: str | None = None) -> str:
    """투자 기준 목록."""
    if category:
        rows = execute_query("""
            SELECT id, name, content, category, updated_at
            FROM investment_criteria
            WHERE category = %s
            ORDER BY updated_at DESC
        """, (category,))
    else:
        rows = execute_query("""
            SELECT id, name, content, category, updated_at
            FROM investment_criteria
            ORDER BY category, updated_at DESC
        """)

    for r in rows:
        if r.get("updated_at"):
            r["updated_at"] = r["updated_at"].isoformat()

    return json.dumps({"criteria": rows, "count": len(rows)}, ensure_ascii=False)


def get_criteria(name: str) -> str:
    """특정 기준 상세."""
    rows = execute_query("""
        SELECT id, name, content, category, created_at, updated_at
        FROM investment_criteria WHERE name = %s
    """, (name,))

    if not rows:
        return json.dumps({"error": f"'{name}' 기준을 찾을 수 없습니다"}, ensure_ascii=False)

    r = rows[0]
    for k in ("created_at", "updated_at"):
        if r.get(k):
            r[k] = r[k].isoformat()
    return json.dumps(r, ensure_ascii=False)


def delete_criteria(name: str) -> str:
    """기준 삭제."""
    execute_command("DELETE FROM investment_criteria WHERE name = %s", (name,))
    return json.dumps({"status": "deleted", "name": name}, ensure_ascii=False)
