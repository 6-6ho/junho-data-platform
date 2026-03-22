"""
Investment Agent API — 공개 통계 + 인증된 메모/스크리닝
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/api/agent", tags=["agent"])


# === 공개 엔드포인트 ===

@router.get("/stats")
def agent_stats(db: Session = Depends(get_db)):
    """공개 통계."""
    row = db.execute(text("""
        SELECT
            (SELECT COUNT(*) FROM investment_memo) AS memo_count,
            (SELECT COUNT(*) FROM investment_criteria) AS criteria_count,
            (SELECT COUNT(*) FROM agent_query_log
             WHERE created_at > NOW() - INTERVAL '24 hours') AS queries_today,
            (SELECT MAX(created_at) FROM investment_memo) AS last_memo
    """)).fetchone()

    return {
        "memo_count": row[0] if row else 0,
        "criteria_count": row[1] if row else 0,
        "queries_today": row[2] if row else 0,
        "last_memo": row[3].isoformat() if row and row[3] else None,
    }


@router.get("/criteria")
def agent_criteria(
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """투자 기준 목록 (공개)."""
    if category:
        rows = db.execute(text("""
            SELECT id, name, content, category, updated_at
            FROM investment_criteria WHERE category = :cat
            ORDER BY updated_at DESC
        """), {"cat": category}).fetchall()
    else:
        rows = db.execute(text("""
            SELECT id, name, content, category, updated_at
            FROM investment_criteria ORDER BY category, updated_at DESC
        """)).fetchall()

    return {
        "criteria": [
            {
                "id": r[0], "name": r[1], "content": r[2],
                "category": r[3],
                "updated_at": r[4].isoformat() if r[4] else None,
            }
            for r in rows
        ]
    }


@router.get("/memos/recent")
def agent_recent_memos(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """최근 메모 미리보기 (공개, 50자 절삭)."""
    rows = db.execute(text("""
        SELECT id, LEFT(content, 50) AS preview, tags, source, created_at
        FROM investment_memo ORDER BY created_at DESC LIMIT :lim
    """), {"lim": limit}).fetchall()

    return {
        "memos": [
            {
                "id": r[0], "preview": r[1], "tags": r[2],
                "source": r[3],
                "created_at": r[4].isoformat() if r[4] else None,
            }
            for r in rows
        ]
    }


# === 인증 필요 엔드포인트 ===

class MemoRequest(BaseModel):
    content: str
    tags: Optional[List[str]] = None


@router.post("/memo")
def add_memo(
    req: MemoRequest,
    db: Session = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    """웹에서 메모 추가 (인증 필요)."""
    # 자동 태그
    tag_keywords = {
        "금리": "금리", "환율": "환율", "BTC": "BTC", "ETH": "ETH",
        "ETF": "ETF", "연준": "연준", "FOMC": "FOMC", "CPI": "CPI",
        "도미넌스": "도미넌스", "알트": "알트코인", "매크로": "매크로",
    }
    auto_tags = {tag for kw, tag in tag_keywords.items() if kw.lower() in req.content.lower()}
    all_tags = sorted(set((req.tags or []) + list(auto_tags)))

    row = db.execute(text("""
        INSERT INTO investment_memo (content, source, tags)
        VALUES (:content, 'web', :tags) RETURNING id
    """), {"content": req.content, "tags": all_tags}).fetchone()
    db.commit()

    return {"id": row[0], "tags": all_tags}


class SearchRequest(BaseModel):
    query: str
    limit: int = 5


@router.post("/memo/search")
def search_memos(
    req: SearchRequest,
    db: Session = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    """메모 텍스트 검색 (인증 필요)."""
    # 벡터 검색은 Voyage API가 백엔드에 없으므로 ILIKE fallback
    rows = db.execute(text("""
        SELECT id, content, tags, created_at
        FROM investment_memo
        WHERE content ILIKE :q
        ORDER BY created_at DESC
        LIMIT :lim
    """), {"q": f"%{req.query}%", "lim": req.limit}).fetchall()

    # 질의 로그
    db.execute(text("""
        INSERT INTO agent_query_log (query_text, query_type, source)
        VALUES (:q, 'memo_search', 'web')
    """), {"q": req.query})
    db.commit()

    return {
        "results": [
            {
                "id": r[0], "content": r[1], "tags": r[2],
                "created_at": r[3].isoformat() if r[3] else None,
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.post("/screen")
def screen_coins(
    db: Session = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    """종목 스크리닝 (인증 필요)."""
    # 비junk + 거래량 상위
    screener = db.execute(text("""
        SELECT exchange, symbol, price_krw, market_cap_krw, volume_24h_krw,
               junk_score, is_low_cap, is_long_decline
        FROM coin_screener_latest
        WHERE junk_score = 0
        ORDER BY volume_24h_krw DESC NULLS LAST
        LIMIT 20
    """)).fetchall()

    # 최근 movers
    movers = db.execute(text("""
        SELECT DISTINCT ON (symbol)
            symbol, change_pct_window, change_pct_24h, vol_ratio
        FROM movers_latest
        WHERE type = 'rise' AND event_time > NOW() - INTERVAL '1 hour'
        ORDER BY symbol, event_time DESC
    """)).fetchall()

    mover_set = {r[0] for r in movers}
    mover_map = {r[0]: {"change": float(r[1]) if r[1] else None, "change_24h": float(r[2]) if r[2] else None, "vol_ratio": float(r[3]) if r[3] else None} for r in movers}

    coins = []
    for r in screener:
        sym = r[1]
        coins.append({
            "exchange": r[0], "symbol": sym,
            "price_krw": r[2], "market_cap_krw": r[3], "volume_24h_krw": r[4],
            "junk_score": r[5],
            "is_moving": sym in mover_set,
            "move": mover_map.get(sym),
        })

    coins.sort(key=lambda x: (not x["is_moving"], -(x.get("volume_24h_krw") or 0)))

    db.execute(text("""
        INSERT INTO agent_query_log (query_text, query_type, source)
        VALUES ('screen', 'screening', 'web')
    """))
    db.commit()

    return {"coins": coins, "total": len(coins), "moving": sum(1 for c in coins if c["is_moving"])}
