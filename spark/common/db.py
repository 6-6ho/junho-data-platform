import psycopg2
import os

class DBConnection:
    def __init__(self):
        self.host = "postgres"
        self.port = 5432
        self.dbname = os.getenv("POSTGRES_DB", "app")
        self.user = os.getenv("POSTGRES_USER", "postgres")
        self.password = os.getenv("POSTGRES_PASSWORD", "postgres")
    
    def get_connection(self):
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.user,
            password=self.password
        )

def save_movers_batch(movers_data):
    """
    movers_data: list of dicts {type, symbol, status, window, event_time, ...}
    """
    if not movers_data:
        return

    conn = DBConnection().get_connection()
    try:
        cur = conn.cursor()
        query = """
            INSERT INTO movers_latest (
                type, symbol, status, "window", event_time, 
                change_pct_window, change_pct_24h, vol_ratio
            ) VALUES (
                %(type)s, %(symbol)s, %(status)s, %(window)s, %(event_time)s,
                %(change_pct_window)s, %(change_pct_24h)s, %(vol_ratio)s
            )
            ON CONFLICT (type, symbol, status, event_time) 
            DO UPDATE SET
                change_pct_window = EXCLUDED.change_pct_window,
                change_pct_24h = EXCLUDED.change_pct_24h,
                vol_ratio = EXCLUDED.vol_ratio,
                updated_at = NOW();
        """
        cur.executemany(query, movers_data)
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"DB Error: {e}")
        conn.rollback()
    finally:
        conn.close()

def save_alerts_batch(alerts_data):
    if not alerts_data:
        return

    conn = DBConnection().get_connection()
    try:
        cur = conn.cursor()
        query = """
            INSERT INTO alerts_events (
                event_time, symbol, line_id, direction, 
                price, line_price, buffer_pct
            ) VALUES (
                %(event_time)s, %(symbol)s, %(line_id)s, %(direction)s, 
                %(price)s, %(line_price)s, %(buffer_pct)s
            )
        """
        cur.executemany(query, alerts_data)
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"DB Error: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_active_trendlines():
    conn = DBConnection().get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT line_id, symbol, p1, t1_ms, p2, t2_ms, buffer_pct, cooldown_sec FROM trendlines WHERE enabled = true")
        rows = cur.fetchall()
        # Convert to list of dicts
        result = []
        for r in rows:
            result.append({
                "line_id": str(r[0]),
                "symbol": r[1],
                "p1": r[2], "t1_ms": r[3],
                "p2": r[4], "t2_ms": r[5],
                "buffer_pct": r[6],
                "cooldown_sec": r[7]
            })
        cur.close()
        return result
    except Exception as e:
        print(f"DB Read Error: {e}")
        return []
    finally:
        conn.close()
