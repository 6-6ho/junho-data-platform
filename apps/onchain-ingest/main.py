"""
BTC On-Chain Data Collector

mempool.space API → onchain_btc_metrics 테이블.
5분 간격으로 BTC 네트워크 상태를 수집:
  - 멤풀: 미확인 트랜잭션 수, vsize, 총 수수료
  - 수수료: fastest/halfHour/hour/economy sat/vB
  - 블록: 현재 높이
  - 난이도: 조정 진행률, 잔여 블록, 예상 리타겟

시간 집계(onchain_btc_hourly)로 DQ 드리프트 감지와 연동 가능.
"""
import os
import time
import logging
import requests
import psycopg2

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "app")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")

MEMPOOL_BASE = "https://mempool.space/api"
COLLECT_INTERVAL = 300  # 5분


def get_conn():
    return psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS)


def fetch_json(path):
    resp = requests.get(f"{MEMPOOL_BASE}{path}", timeout=10)
    resp.raise_for_status()
    return resp.json()


def collect_metrics():
    """mempool.space에서 BTC 온체인 메트릭 수집 → DB 적재."""
    try:
        # 멤풀 상태
        mempool = fetch_json("/mempool")
        tx_count = mempool.get("count", 0)
        vsize = mempool.get("vsize", 0)
        total_fee = mempool.get("total_fee", 0) / 1e8  # satoshi → BTC

        # 수수료 추천
        fees = fetch_json("/v1/fees/recommended")
        fee_fastest = fees.get("fastestFee", 0)
        fee_half = fees.get("halfHourFee", 0)
        fee_hour = fees.get("hourFee", 0)
        fee_economy = fees.get("economyFee", 0)

        # 블록 높이
        block_height = fetch_json("/blocks/tip/height")

        # 난이도 조정
        diff = fetch_json("/v1/difficulty-adjustment")
        diff_progress = diff.get("progressPercent", 0)
        diff_remaining = diff.get("remainingBlocks", 0)
        diff_retarget = diff.get("estimatedRetargetPercentage", 0)

        # DB 적재
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO onchain_btc_metrics (
                block_height, mempool_tx_count, mempool_vsize, mempool_total_fee,
                fee_fastest, fee_half_hour, fee_hour, fee_economy,
                difficulty_progress, difficulty_remaining_blocks, difficulty_estimated_retarget
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            block_height, tx_count, vsize, total_fee,
            fee_fastest, fee_half, fee_hour, fee_economy,
            diff_progress, diff_remaining, diff_retarget,
        ))

        # 시간 집계 upsert
        cur.execute("""
            INSERT INTO onchain_btc_hourly (hour, avg_mempool_tx, avg_mempool_vsize, avg_fee_fastest, avg_fee_economy, block_count)
            SELECT
                date_trunc('hour', NOW()),
                AVG(mempool_tx_count)::int,
                AVG(mempool_vsize)::bigint,
                AVG(fee_fastest)::int,
                AVG(fee_economy)::int,
                MAX(block_height) - MIN(block_height)
            FROM onchain_btc_metrics
            WHERE collected_at >= date_trunc('hour', NOW())
            ON CONFLICT (hour) DO UPDATE SET
                avg_mempool_tx = EXCLUDED.avg_mempool_tx,
                avg_mempool_vsize = EXCLUDED.avg_mempool_vsize,
                avg_fee_fastest = EXCLUDED.avg_fee_fastest,
                avg_fee_economy = EXCLUDED.avg_fee_economy,
                block_count = EXCLUDED.block_count,
                created_at = NOW()
        """)

        conn.commit()
        cur.close()
        conn.close()

        logger.info(
            f"BTC: height={block_height}, mempool={tx_count}tx/{vsize/1e6:.1f}MvB, "
            f"fee={fee_fastest}/{fee_economy} sat/vB, diff={diff_progress:.1f}%"
        )

    except Exception as e:
        logger.error(f"Collection failed: {e}")


def main():
    logger.info("On-Chain Ingest starting...")

    # DB 대기
    for attempt in range(10):
        try:
            conn = get_conn()
            conn.close()
            break
        except Exception:
            logger.warning(f"DB not ready ({attempt+1}/10)...")
            time.sleep(5)

    while True:
        collect_metrics()
        time.sleep(COLLECT_INTERVAL)


if __name__ == "__main__":
    main()
