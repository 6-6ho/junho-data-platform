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


@router.get("/cross-exchange")
def get_cross_exchange(db: Session = Depends(get_db)):
    """거래소 간 가격 교차검증 — Binance vs Upbit/Bithumb"""
    try:
        rows = db.execute(text("""
            SELECT
                REPLACE(ms.symbol, 'USDT', '') as symbol,
                ms.price as binance_usd,
                up.price_krw as upbit_krw,
                bt.price_krw as bithumb_krw,
                up.updated_at as upbit_updated,
                bt.updated_at as bithumb_updated
            FROM market_snapshot ms
            LEFT JOIN exchange_price_snapshot up
                ON REPLACE(ms.symbol, 'USDT', '') = up.symbol AND up.exchange = 'upbit'
            LEFT JOIN exchange_price_snapshot bt
                ON REPLACE(ms.symbol, 'USDT', '') = bt.symbol AND bt.exchange = 'bithumb'
            WHERE (up.price_krw IS NOT NULL OR bt.price_krw IS NOT NULL)
              AND ms.price > 0
            ORDER BY ms.price * ms.volume_24h DESC
            LIMIT 30
        """)).fetchall()
        return [
            {
                "symbol": r.symbol,
                "binance_usd": float(r.binance_usd) if r.binance_usd else None,
                "upbit_krw": float(r.upbit_krw) if r.upbit_krw else None,
                "bithumb_krw": float(r.bithumb_krw) if r.bithumb_krw else None,
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"dq/cross-exchange failed: {e}")
        return []


@router.get("/drift")
def get_drift(db: Session = Depends(get_db)):
    """최근 7일 드리프트 이벤트 — 심볼별 분포 변화 감지"""
    try:
        rows = db.execute(text("""
            SELECT detected_at AT TIME ZONE 'Asia/Seoul' as detected_at,
                   anomaly_type, dimension as symbol,
                   expected_value, actual_value, severity, notes
            FROM dq_trade_anomaly_log
            WHERE anomaly_type LIKE 'drift_%'
              AND detected_at >= NOW() - INTERVAL '7 days'
            ORDER BY detected_at DESC
            LIMIT 50
        """)).fetchall()
        return [
            {
                "detected_at": str(r.detected_at),
                "type": r.anomaly_type.replace("drift_", ""),
                "symbol": r.symbol,
                "expected": float(r.expected_value) if r.expected_value else None,
                "actual": float(r.actual_value) if r.actual_value else None,
                "severity": r.severity,
                "notes": r.notes,
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"dq/drift failed: {e}")
        return []


@router.get("/onchain")
def get_onchain(db: Session = Depends(get_db)):
    """BTC 온체인 최신 메트릭 + 24h 트렌드"""
    try:
        # 최신 1건
        latest = db.execute(text("""
            SELECT block_height, mempool_tx_count, mempool_vsize, mempool_total_fee,
                   fee_fastest, fee_half_hour, fee_hour, fee_economy,
                   difficulty_progress, difficulty_remaining_blocks, difficulty_estimated_retarget,
                   collected_at AT TIME ZONE 'Asia/Seoul' as collected_at
            FROM onchain_btc_metrics ORDER BY collected_at DESC LIMIT 1
        """)).fetchone()

        # 24h 시간별 트렌드
        hourly = db.execute(text("""
            SELECT hour AT TIME ZONE 'Asia/Seoul' as hour,
                   avg_mempool_tx, avg_fee_fastest, avg_fee_economy, block_count
            FROM onchain_btc_hourly
            WHERE hour >= NOW() - INTERVAL '24 hours'
            ORDER BY hour
        """)).fetchall()

        return {
            "latest": {
                "block_height": latest.block_height,
                "mempool_tx_count": latest.mempool_tx_count,
                "mempool_vsize_mb": round(latest.mempool_vsize / 1e6, 1) if latest.mempool_vsize else 0,
                "mempool_total_fee_btc": float(latest.mempool_total_fee) if latest.mempool_total_fee else 0,
                "fee_fastest": latest.fee_fastest,
                "fee_economy": latest.fee_economy,
                "difficulty_progress": float(latest.difficulty_progress) if latest.difficulty_progress else 0,
                "collected_at": str(latest.collected_at),
            } if latest else None,
            "hourly": [
                {
                    "hour": str(r.hour),
                    "mempool_tx": r.avg_mempool_tx,
                    "fee_fastest": r.avg_fee_fastest,
                    "fee_economy": r.avg_fee_economy,
                    "blocks": r.block_count,
                }
                for r in hourly
            ],
        }
    except Exception as e:
        logger.error(f"dq/onchain failed: {e}")
        return {"latest": None, "hourly": []}
