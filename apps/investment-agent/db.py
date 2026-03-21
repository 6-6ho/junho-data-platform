"""DB 연결 — MCP 서버는 로컬 프로세스로 실행, localhost:5432 접속."""
import os
import psycopg2

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "app")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

_conn = None


def get_conn():
    """싱글톤 DB 연결."""
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASSWORD,
        )
        _conn.autocommit = True
    return _conn


def execute_query(sql, params=None, fetchall=True):
    """쿼리 실행 후 결과 반환."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        if cur.description:
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall() if fetchall else [cur.fetchone()]
            cur.close()
            return [dict(zip(cols, row)) for row in rows if row]
        cur.close()
        return []
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        raise e


def execute_command(sql, params=None):
    """INSERT/UPDATE/DELETE 실행."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    # RETURNING 절이 있으면 결과 반환
    if cur.description:
        result = cur.fetchone()
        cur.close()
        return result
    cur.close()
    return None
