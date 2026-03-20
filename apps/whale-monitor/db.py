"""DB 연결 (listing-monitor 패턴 재사용)."""
import os
import time
import logging

import psycopg2

logger = logging.getLogger(__name__)

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "app")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")


def connect_db():
    """DB 연결 (재시도 로직)."""
    for attempt in range(1, 11):
        try:
            conn = psycopg2.connect(
                host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
                user=DB_USER, password=DB_PASSWORD,
            )
            conn.autocommit = False
            logger.info("DB 연결 성공")
            return conn
        except psycopg2.OperationalError as e:
            logger.warning(f"DB 연결 실패 (시도 {attempt}/10): {e}")
            time.sleep(5)
    raise RuntimeError("DB 연결 10회 실패")


def ensure_conn(conn):
    """연결 상태 확인, 끊겼으면 재연결."""
    try:
        conn.isolation_level
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        return conn
    except Exception:
        logger.warning("DB 연결 끊김, 재연결 시도")
        try:
            conn.close()
        except Exception:
            pass
        return connect_db()
