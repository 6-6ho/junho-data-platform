import os
import time
import psycopg2
from psycopg2 import pool, extras
from datetime import datetime


class DBConnection:
    _pool = None

    @classmethod
    def initialize(cls):
        if cls._pool is None:
            for attempt in range(3):
                try:
                    cls._pool = psycopg2.pool.SimpleConnectionPool(
                        1, 5,
                        host=os.getenv("DB_HOST", "postgres"),
                        port=5432,
                        dbname="app",
                        user="postgres",
                        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
                        connect_timeout=5
                    )
                    return
                except Exception as e:
                    print(f"[DB] Connection attempt {attempt+1}/3 failed: {e}")
                    time.sleep(2)
            raise Exception("[DB] Failed to initialize pool after 3 attempts")

    @classmethod
    def get_connection(cls):
        if cls._pool is None:
            cls.initialize()
        try:
            conn = cls._pool.getconn()
            # Test if connection is alive
            conn.isolation_level
            return conn
        except Exception:
            # Connection is dead, reset pool
            cls.close_all()
            cls._pool = None
            cls.initialize()
            return cls._pool.getconn()

    @classmethod
    def return_connection(cls, conn):
        if cls._pool and conn:
            try:
                cls._pool.putconn(conn)
            except Exception:
                pass

    @classmethod
    def close_all(cls):
        if cls._pool:
            try:
                cls._pool.closeall()
            except Exception:
                pass


def save_movers_batch(movers_data):
    if not movers_data:
        return

    conn = DBConnection.get_connection()
    try:
        query = """
            INSERT INTO movers_latest_flink (
                type, symbol, status, "window", event_time,
                change_pct_window, change_pct_24h, vol_ratio, updated_at
            ) VALUES %s
            ON CONFLICT (type, symbol, status, event_time)
            DO UPDATE SET
                change_pct_window = EXCLUDED.change_pct_window,
                change_pct_24h = EXCLUDED.change_pct_24h,
                vol_ratio = EXCLUDED.vol_ratio,
                updated_at = NOW();
        """
        data = [
            (
                m['type'], m['symbol'], m['status'], m['window'], m['event_time'],
                m['change_pct_window'], m.get('change_pct_24h', 0.0),
                m.get('vol_ratio'), datetime.now()
            ) for m in movers_data
        ]
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, query, data)
        conn.commit()
    except Exception as e:
        print(f"[DB] Error saving movers ({len(movers_data)} rows): {e}")
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        DBConnection.return_connection(conn)


def save_market_snapshot_flink(data):
    if not data:
        return

    # Deduplicate by symbol (keep latest)
    dedup = {}
    for d in data:
        sym = d['symbol']
        if sym not in dedup or d['event_time'] > dedup[sym]['event_time']:
            dedup[sym] = d
    data = list(dedup.values())

    conn = DBConnection.get_connection()
    try:
        query = """
            INSERT INTO market_snapshot_flink (
                symbol, price, change_pct_24h, volume_24h,
                change_pct_window, vol_ratio, event_time, updated_at
            ) VALUES %s
            ON CONFLICT (symbol)
            DO UPDATE SET
                price = EXCLUDED.price,
                change_pct_24h = EXCLUDED.change_pct_24h,
                volume_24h = EXCLUDED.volume_24h,
                change_pct_window = EXCLUDED.change_pct_window,
                vol_ratio = EXCLUDED.vol_ratio,
                event_time = EXCLUDED.event_time,
                updated_at = NOW();
        """
        rows = [
            (
                d['symbol'], d['price'], d['change_pct_24h'], d['volume_24h'],
                d['change_pct_window'], d.get('vol_ratio', 0.0),
                d['event_time'], datetime.now()
            ) for d in data
        ]
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, query, rows)
        conn.commit()
        print(f"[DB] Snapshot: {len(data)} symbols")
    except Exception as e:
        print(f"[DB] Error saving snapshot ({len(data)} rows): {e}")
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        DBConnection.return_connection(conn)
