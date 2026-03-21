"""인사이트 메모 저장/검색."""
import json
from db import execute_query, execute_command
from embedding import embed_text

# 자동 태그 키워드
TAG_KEYWORDS = {
    "금리": "금리", "환율": "환율", "인플레이션": "인플레이션",
    "CPI": "CPI", "PPI": "PPI", "고용": "고용",
    "BTC": "BTC", "ETH": "ETH", "비트코인": "BTC", "이더리움": "ETH",
    "ETF": "ETF", "옵션": "옵션", "선물": "선물",
    "연준": "연준", "Fed": "연준", "FOMC": "FOMC",
    "도미넌스": "도미넌스", "알트": "알트코인",
    "숏스퀴즈": "숏스퀴즈", "청산": "청산",
    "매크로": "매크로", "경기": "경기",
}


def _auto_tag(content: str) -> list[str]:
    """내용에서 자동 태그 추출."""
    tags = set()
    for keyword, tag in TAG_KEYWORDS.items():
        if keyword.lower() in content.lower():
            tags.add(tag)
    return sorted(tags)


def save_memo(content: str, tags: list[str] | None = None, source: str = "mcp") -> str:
    """메모 저장 (자동 임베딩 + 태그)."""
    auto_tags = _auto_tag(content)
    all_tags = sorted(set((tags or []) + auto_tags))

    # 임베딩
    embedding = embed_text(content)

    if embedding:
        result = execute_command("""
            INSERT INTO investment_memo (content, source, tags, embedding)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (content, source, all_tags, embedding))
    else:
        result = execute_command("""
            INSERT INTO investment_memo (content, source, tags)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (content, source, all_tags))

    return json.dumps({
        "status": "saved",
        "id": result[0],
        "tags": all_tags,
        "has_embedding": embedding is not None,
    }, ensure_ascii=False)


def search_memos(query: str, limit: int = 5) -> str:
    """유사 메모 벡터 검색."""
    embedding = embed_text(query)

    if embedding:
        # 벡터 검색
        rows = execute_query("""
            SELECT id, content, tags, created_at,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM investment_memo
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (embedding, embedding, limit))
    else:
        # 임베딩 불가 시 텍스트 검색 fallback
        rows = execute_query("""
            SELECT id, content, tags, created_at, 0.0 AS similarity
            FROM investment_memo
            WHERE content ILIKE %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (f"%{query}%", limit))

    for r in rows:
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()
        if r.get("similarity") is not None:
            r["similarity"] = round(float(r["similarity"]), 4)

    return json.dumps({
        "query": query,
        "results": rows,
        "count": len(rows),
        "method": "vector" if embedding else "text",
    }, ensure_ascii=False)


def recent_memos(limit: int = 10) -> str:
    """최근 메모 조회."""
    rows = execute_query("""
        SELECT id, content, tags, source, created_at
        FROM investment_memo
        ORDER BY created_at DESC
        LIMIT %s
    """, (limit,))

    for r in rows:
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()

    return json.dumps({"memos": rows, "count": len(rows)}, ensure_ascii=False)
