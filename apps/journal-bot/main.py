"""
Journal Bot — 투자/경제 인사이트 메모 수집 텔레그램 봇.
getUpdates 롱폴링으로 메시지 수신 → Voyage 임베딩 → pgvector 저장.
"""
import os
import json
import time
import logging
import urllib.request

import psycopg2
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# === Config ===
BOT_TOKEN = os.getenv("JOURNAL_BOT_TOKEN", "")
CHAT_ID = os.getenv("JOURNAL_CHAT_ID", "")  # 빈 값이면 모든 채팅 허용
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "app")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# 자동 태그 키워드
TAG_KEYWORDS = {
    "금리": "금리", "환율": "환율", "인플레이션": "인플레이션",
    "CPI": "CPI", "PPI": "PPI", "고용": "고용",
    "BTC": "BTC", "ETH": "ETH", "비트코인": "BTC", "이더리움": "ETH",
    "ETF": "ETF", "옵션": "옵션", "선물": "선물",
    "연준": "연준", "Fed": "연준", "FOMC": "FOMC",
    "도미넌스": "도미넌스", "알트": "알트코인",
    "숏스퀴즈": "숏스퀴즈", "청산": "청산",
    "매크로": "매크로", "경기": "경기",
}

_voyage_client = None


# === DB ===

def connect_db():
    """DB 연결 (재시도)."""
    for attempt in range(1, 11):
        try:
            conn = psycopg2.connect(
                host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
                user=DB_USER, password=DB_PASSWORD,
            )
            conn.autocommit = True
            logger.info("DB 연결 성공")
            return conn
        except psycopg2.OperationalError as e:
            logger.warning(f"DB 연결 실패 (시도 {attempt}/10): {e}")
            time.sleep(5)
    raise RuntimeError("DB 연결 10회 실패")


def ensure_conn(conn):
    """연결 확인, 끊겼으면 재연결."""
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        return conn
    except Exception:
        logger.warning("DB 재연결")
        try:
            conn.close()
        except Exception:
            pass
        return connect_db()


# === Telegram ===

def send_message(chat_id, text):
    """텔레그램 메시지 전송."""
    try:
        resp = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.error(f"텔레그램 전송 실패: {resp.text}")
    except Exception as e:
        logger.error(f"텔레그램 오류: {e}")


def get_updates(offset=None, timeout=30):
    """getUpdates 롱폴링."""
    try:
        params = {"timeout": timeout}
        if offset:
            params["offset"] = offset
        resp = requests.get(
            f"{TELEGRAM_API}/getUpdates",
            params=params,
            timeout=timeout + 10,
        )
        if resp.status_code == 200:
            return resp.json().get("result", [])
    except Exception as e:
        logger.error(f"getUpdates 오류: {e}")
    return []


# === Embedding ===

def get_voyage_client():
    """Voyage AI 클라이언트."""
    global _voyage_client
    if _voyage_client is None and VOYAGE_API_KEY:
        import voyageai
        _voyage_client = voyageai.Client(api_key=VOYAGE_API_KEY)
    return _voyage_client


def embed_text(text):
    """텍스트 임베딩."""
    client = get_voyage_client()
    if not client:
        return None
    try:
        result = client.embed([text], model="voyage-3-lite")
        return result.embeddings[0]
    except Exception as e:
        logger.warning(f"임베딩 오류: {e}")
        return None


# === Memo 처리 ===

def auto_tag(content):
    """자동 태그 추출."""
    tags = set()
    for keyword, tag in TAG_KEYWORDS.items():
        if keyword.lower() in content.lower():
            tags.add(tag)
    return sorted(tags)


def save_memo(conn, content, source="telegram"):
    """메모 저장."""
    tags = auto_tag(content)
    embedding = embed_text(content)

    cur = conn.cursor()
    if embedding:
        cur.execute("""
            INSERT INTO investment_memo (content, source, tags, embedding)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (content, source, tags, embedding))
    else:
        cur.execute("""
            INSERT INTO investment_memo (content, source, tags)
            VALUES (%s, %s, %s) RETURNING id
        """, (content, source, tags))

    memo_id = cur.fetchone()[0]
    cur.close()
    return memo_id, tags


def search_memos(conn, query, limit=5):
    """메모 벡터 검색."""
    embedding = embed_text(query)
    cur = conn.cursor()

    if embedding:
        cur.execute("""
            SELECT id, content, tags, created_at,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM investment_memo
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (embedding, embedding, limit))
    else:
        cur.execute("""
            SELECT id, content, tags, created_at, 0.0 AS similarity
            FROM investment_memo
            WHERE content ILIKE %s
            ORDER BY created_at DESC LIMIT %s
        """, (f"%{query}%", limit))

    rows = cur.fetchall()
    cur.close()
    return [
        {"id": r[0], "content": r[1], "tags": r[2], "created_at": r[3], "similarity": float(r[4])}
        for r in rows
    ]


def get_recent_memos(conn, limit=5):
    """최근 메모 조회."""
    cur = conn.cursor()
    cur.execute("""
        SELECT id, content, tags, created_at
        FROM investment_memo ORDER BY created_at DESC LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    return rows


def get_criteria_list(conn):
    """투자 기준 목록."""
    cur = conn.cursor()
    cur.execute("SELECT name, content, category FROM investment_criteria ORDER BY category, name")
    rows = cur.fetchall()
    cur.close()
    return rows


def get_stats(conn):
    """통계."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM investment_memo")
    memo_count = cur.fetchone()[0]
    cur.execute("SELECT MAX(created_at) FROM investment_memo")
    last_memo = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM investment_criteria")
    criteria_count = cur.fetchone()[0]
    cur.close()
    return memo_count, last_memo, criteria_count


# === 메시지 처리 ===

def handle_message(conn, message):
    """수신 메시지 처리."""
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    if not text:
        return

    # 채팅 ID 필터 (설정된 경우)
    if CHAT_ID and str(chat_id) != str(CHAT_ID):
        logger.info(f"허용되지 않은 chat_id: {chat_id}")
        send_message(chat_id, "이 봇은 개인용입니다.")
        return

    # 커맨드 처리
    if text.startswith("/search "):
        query = text[8:].strip()
        if not query:
            send_message(chat_id, "사용법: /search <검색어>")
            return
        results = search_memos(conn, query)
        if not results:
            send_message(chat_id, "관련 메모를 찾지 못했습니다.")
            return
        lines = [f"*검색: {query}* ({len(results)}건)\n"]
        for r in results:
            date = r["created_at"].strftime("%m/%d") if r["created_at"] else "?"
            sim = f" ({r['similarity']:.0%})" if r["similarity"] > 0 else ""
            content = r["content"][:80]
            lines.append(f"[{date}]{sim} {content}")
        send_message(chat_id, "\n".join(lines))

    elif text.startswith("/recent"):
        rows = get_recent_memos(conn)
        if not rows:
            send_message(chat_id, "저장된 메모가 없습니다.")
            return
        lines = ["*최근 메모*\n"]
        for r in rows:
            date = r[3].strftime("%m/%d %H:%M") if r[3] else "?"
            content = r[1][:80]
            lines.append(f"#{r[0]} [{date}] {content}")
        send_message(chat_id, "\n".join(lines))

    elif text.startswith("/criteria"):
        rows = get_criteria_list(conn)
        if not rows:
            send_message(chat_id, "저장된 투자 기준이 없습니다.")
            return
        lines = ["*투자 기준*\n"]
        for name, content, category in rows:
            lines.append(f"[{category}] *{name}*: {content[:60]}")
        send_message(chat_id, "\n".join(lines))

    elif text.startswith("/stats"):
        memo_count, last_memo, criteria_count = get_stats(conn)
        last_str = last_memo.strftime("%m/%d %H:%M") if last_memo else "없음"
        send_message(chat_id, (
            f"*Journal Stats*\n"
            f"• 메모: {memo_count}건\n"
            f"• 투자 기준: {criteria_count}개\n"
            f"• 마지막 메모: {last_str}"
        ))

    elif text.startswith("/start"):
        send_message(chat_id, (
            "*JDP Journal Bot*\n\n"
            "메시지를 보내면 투자 인사이트로 저장됩니다.\n\n"
            "*커맨드:*\n"
            "/search <질의> — 메모 검색\n"
            "/recent — 최근 메모\n"
            "/criteria — 투자 기준 목록\n"
            "/stats — 통계"
        ))

    elif text.startswith("/"):
        send_message(chat_id, "알 수 없는 커맨드. /start로 도움말 확인")

    else:
        # 일반 메시지 → 메모 저장
        memo_id, tags = save_memo(conn, text)
        tag_str = ", ".join(tags) if tags else "없음"
        send_message(chat_id, f"메모 저장 (#{memo_id}) 태그: {tag_str}")
        logger.info(f"메모 #{memo_id} 저장: {text[:50]}...")


# === 메인 루프 ===

def main():
    if not BOT_TOKEN:
        logger.error("JOURNAL_BOT_TOKEN 미설정")
        return

    logger.info("Journal Bot 시작")
    conn = connect_db()

    # chat_id 로깅 (설정용)
    if not CHAT_ID:
        logger.info("JOURNAL_CHAT_ID 미설정 — 모든 채팅 허용, 첫 메시지의 chat_id를 확인하세요")

    offset = None
    while True:
        conn = ensure_conn(conn)
        updates = get_updates(offset)

        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message")
            if message:
                try:
                    handle_message(conn, message)
                except Exception as e:
                    logger.error(f"메시지 처리 오류: {e}")

        time.sleep(1)


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            logger.error(f"치명적 오류: {e}, 10초 후 재시작")
            time.sleep(10)
