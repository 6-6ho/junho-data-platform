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
    def get_connection(cls):
        if cls._pool is None:
            cls.initialize()
        return cls._pool.getconn()

    @classmethod
    def return_connection(cls, conn):
        if cls._pool and conn:
            cls._pool.putconn(conn)

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
    except Exception as e:
        print(f"[DB] Error saving movers: {e}")
        conn.rollback()
    finally:
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
    except Exception as e:
        print(f"[DB] Error saving market snapshot: {e}")
        conn.rollback()
    finally:
        DBConnection.return_connection(conn)


# Initialize pool on module load if appropriate, or let explicit call handle it
# DBConnection.initialize()
