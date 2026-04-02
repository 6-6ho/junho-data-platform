"""
Trade DQ (Data Quality) Router
- GET /api/dq/score-trend   — 14일 DQ 스코어 트렌드
- GET /api/dq/overview      — 통합 요약 (스코어+어제비교+anomaly count+교차검증)
- GET /api/dq/anomalies     — 최근 20건 이상 탐지
- GET /api/dq/reconciliation — 24h 교차검증 결과

Shop DQ와 완전 독립. dq_trade_* 테이블만 사용.
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dq", tags=["dq"])


@router.get("/score-trend")
def get_score_trend(db: Session = Depends(get_db)):
    """14일 DQ 스코어 트렌드"""
    try:
        rows = db.execute(text("""
            SELECT date, completeness_score, validity_score, timeliness_score, total_score
            FROM dq_trade_daily_score
            ORDER BY date DESC LIMIT 14
        """)).fetchall()
        return [
            {"date": str(r.date), "completeness": r.completeness_score,
             "validity": r.validity_score, "timeliness": r.timeliness_score,
             "total": r.total_score}
            for r in reversed(rows)
        ]
    except Exception as e:
        logger.error(f"dq/score-trend failed: {e}")
        return []


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    """DQ 통합 요약"""
    try:
        # 최근 2일 스코어
        scores = db.execute(text("""
            SELECT date, total_score, completeness_score, validity_score, timeliness_score
            FROM dq_trade_daily_score ORDER BY date DESC LIMIT 2
        """)).fetchall()

        score = scores[0].total_score if scores else None
        prev_score = scores[1].total_score if len(scores) >= 2 else None
        detail = {}
        if scores:
            detail = {"completeness": scores[0].completeness_score,
                      "validity": scores[0].validity_score,
                      "timeliness": scores[0].timeliness_score}

        # 24h anomaly severity 카운트
        sev_rows = db.execute(text("""
            SELECT severity, COUNT(*) as cnt
            FROM dq_trade_anomaly_log
            WHERE detected_at >= NOW() - INTERVAL '24 hours'
            GROUP BY severity
        """)).fetchall()
        anomalies_24h = {r.severity: r.cnt for r in sev_rows}

        # 미해결 건수
        unresolved = db.execute(text(
            "SELECT COUNT(*) FROM dq_trade_anomaly_log WHERE resolved = FALSE"
        )).scalar() or 0

        # 최대 교차검증 diff
        max_diff_row = db.execute(text("""
            WITH diffs AS (
                SELECT s.hour,
                    ABS(s.event_count - COALESCE(y.total_ticks, 0))::float
                    / GREATEST(s.event_count, COALESCE(y.total_ticks, 0), 1) * 100 as diff_pct
                FROM dq_trade_source_hourly s
                LEFT JOIN (
                    SELECT hour, SUM(tick_count) as total_ticks
                    FROM dq_trade_symbol_hourly
                    WHERE hour >= NOW() - INTERVAL '24 hours'
                    GROUP BY hour
                ) y ON s.hour = y.hour
                WHERE s.source = 'ticker'
                  AND s.hour >= NOW() - INTERVAL '24 hours'
            )
            SELECT ROUND(MAX(diff_pct)::numeric, 1) FROM diffs
        """)).scalar() or 0

        return {
            "score": score,
            "prev_score": prev_score,
            "score_change": score - prev_score if score is not None and prev_score is not None else None,
            "detail": detail,
            "anomalies_24h": anomalies_24h,
            "unresolved": unresolved,
            "max_diff_pct": float(max_diff_row),
        }
    except Exception as e:
        logger.error(f"dq/overview failed: {e}")
        return {"score": None, "prev_score": None, "score_change": None,
                "detail": {}, "anomalies_24h": {}, "unresolved": 0, "max_diff_pct": 0}


@router.get("/anomalies")
def get_anomalies(db: Session = Depends(get_db)):
    """최근 20건 이상 탐지"""
    try:
        rows = db.execute(text("""
            SELECT detected_at AT TIME ZONE 'Asia/Seoul' as detected_at,
                   anomaly_type, dimension, expected_value, actual_value, severity, notes
            FROM dq_trade_anomaly_log
            ORDER BY detected_at DESC LIMIT 20
        """)).fetchall()
        return [
            {"detected_at": str(r.detected_at), "anomaly_type": r.anomaly_type,
             "dimension": r.dimension,
             "expected_value": float(r.expected_value) if r.expected_value else None,
             "actual_value": float(r.actual_value) if r.actual_value else None,
             "severity": r.severity, "notes": r.notes}
            for r in rows
        ]
    except Exception as e:
        logger.error(f"dq/anomalies failed: {e}")
        return []


@router.get("/reconciliation")
def get_reconciliation(db: Session = Depends(get_db)):
    """24h 교차검증 결과"""
    try:
        rows = db.execute(text("""
            WITH source AS (
                SELECT hour, event_count
                FROM dq_trade_source_hourly
                WHERE source = 'ticker' AND hour >= NOW() - INTERVAL '24 hours'
            ),
            symbol AS (
                SELECT hour, SUM(tick_count) as total_ticks
                FROM dq_trade_symbol_hourly
                WHERE hour >= NOW() - INTERVAL '24 hours'
                GROUP BY hour
            )
            SELECT
                COALESCE(s.hour, y.hour) AT TIME ZONE 'Asia/Seoul' as hour,
                COALESCE(s.event_count, 0) as source_count,
                COALESCE(y.total_ticks, 0) as symbol_count
            FROM source s
            FULL OUTER JOIN symbol y ON s.hour = y.hour
            ORDER BY hour
        """)).fetchall()
        result = []
        for r in rows:
            base = max(r.source_count, r.symbol_count, 1)
            diff_pct = abs(r.source_count - r.symbol_count) / base * 100
            result.append({
                "hour": str(r.hour),
                "source_count": r.source_count,
                "symbol_count": r.symbol_count,
                "diff_pct": round(diff_pct, 1),
            })
        return result
    except Exception as e:
        logger.error(f"dq/reconciliation failed: {e}")
        return []
