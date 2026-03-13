import os
import time
import psycopg2
from psycopg2 import pool, extras
from datetime import datetime
import json

class DBConnection:
    _pool = None

    @classmethod
    def initialize(cls):
        if cls._pool is None:
            cls._pool = psycopg2.pool.SimpleConnectionPool(
                1, 10,
                host=os.getenv("DB_HOST", "postgres"),
                port=5432,
                dbname="app",
                user="postgres",
                password=os.getenv("POSTGRES_PASSWORD", "postgres")
            )

    @classmethod
    def _reset_pool(cls):
        if cls._pool:
            try:
                cls._pool.closeall()
            except Exception:
                pass
        cls._pool = None

    @classmethod
    def get_connection(cls, retries=3):
        for attempt in range(retries):
            if cls._pool is None:
                cls.initialize()
            try:
                conn = cls._pool.getconn()
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                conn.rollback()
                return conn
            except (psycopg2.OperationalError, psycopg2.InterfaceError):
                print(f"[DB] Stale connection, resetting pool (attempt {attempt + 1}/{retries})")
                cls._reset_pool()
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
        raise psycopg2.OperationalError("Failed to get DB connection after retries")

    @classmethod
    def return_connection(cls, conn):
        if cls._pool and conn:
            try:
                if conn.closed:
                    cls._pool.putconn(conn, close=True)
                else:
                    cls._pool.putconn(conn)
            except Exception:
                pass

    @classmethod
    def close_all(cls):
        if cls._pool:
            cls._pool.closeall()


def save_movers_batch(movers_data):
    """
    movers_data: list of dicts {type, symbol, status, window, event_time, ...}
    Implements upsert to avoid duplicate alerts for the same event time.
    """
    if not movers_data:
        return

    conn = DBConnection.get_connection()
    try:
        query = """
            INSERT INTO movers_latest (
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
                m['change_pct_window'], m.get('change_pct_24h', 0.0), m.get('vol_ratio'), datetime.now()
            ) for m in movers_data
        ]
        
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, query, data)
        conn.commit()
    except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
        print(f"[DB] Connection error saving movers: {e}, resetting pool")
        DBConnection._reset_pool()
        conn = None
    except Exception as e:
        print(f"[DB] Error saving movers: {e}")
        if not conn.closed:
            conn.rollback()
    finally:
        if conn:
            DBConnection.return_connection(conn)




_watchlist_cache = {"symbols": set(), "ts": 0}
WATCHLIST_CACHE_TTL = 60


def get_watchlist():
    """favorite_items에서 워치리스트 심볼 조회. 60초 TTL 캐시."""
    now = time.time()
    if now - _watchlist_cache["ts"] < WATCHLIST_CACHE_TTL:
        return _watchlist_cache["symbols"]

    conn = DBConnection.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT fi.symbol FROM favorite_items fi JOIN favorite_groups fg ON fi.group_id = fg.group_id WHERE fg.name = 'Watchlist'")
            symbols = {row[0] for row in cur.fetchall()}
        conn.commit()
        _watchlist_cache.update({"symbols": symbols, "ts": now})
        return symbols
    except Exception as e:
        print(f"[DB] Error fetching watchlist: {e}")
        if conn and not conn.closed:
            conn.rollback()
        return _watchlist_cache["symbols"]
    finally:
        if conn:
            DBConnection.return_connection(conn)


def save_market_snapshot(data):
    """
    data: list of dicts {symbol, price, change_pct_24h, volume_24h, change_pct_window, vol_ratio, event_time}
    """
    if not data:
        return

    conn = DBConnection.get_connection()
    try:
        query = """
            INSERT INTO market_snapshot (
                symbol, price, change_pct_24h, volume_24h, change_pct_window, vol_ratio, event_time, updated_at
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
                d['change_pct_window'], d.get('vol_ratio', 0.0), d['event_time'], datetime.now()
            ) for d in data
        ]
        
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, query, rows)
        conn.commit()
    except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
        print(f"[DB] Connection error saving market snapshot: {e}, resetting pool")
        DBConnection._reset_pool()
        conn = None
    except Exception as e:
        print(f"[DB] Error saving market snapshot: {e}")
        if not conn.closed:
            conn.rollback()
    finally:
        if conn:
            DBConnection.return_connection(conn)


# Initialize pool on module load if appropriate, or let explicit call handle it
# DBConnection.initialize()
