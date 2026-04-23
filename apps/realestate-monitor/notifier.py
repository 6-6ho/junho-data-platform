"""
텔레그램 전송. 메시지 4096자 제한을 넘으면 자연스러운 경계에서 쪼갠다.
"""
import json
import logging
import os
import urllib.request
from datetime import date

log = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
MAX_LEN = 3800  # 4096 에서 여유 확보


def _send_one(token: str, chat_id: str, text: str) -> bool:
    url = TELEGRAM_API.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.getcode() != 200:
                log.error("텔레그램 전송 실패 status=%s body=%s", resp.getcode(), resp.read())
                return False
    except Exception as e:
        log.error("텔레그램 전송 예외: %s", e)
        return False
    return True


def _chunks(text: str) -> list[str]:
    if len(text) <= MAX_LEN:
        return [text]
    lines = text.split("\n")
    out: list[str] = []
    buf: list[str] = []
    size = 0
    for line in lines:
        ln = len(line) + 1
        if size + ln > MAX_LEN and buf:
            out.append("\n".join(buf))
            buf = [line]
            size = ln
        else:
            buf.append(line)
            size += ln
    if buf:
        out.append("\n".join(buf))
    return out


def _format_item(i: int, item: dict) -> str:
    deposit = item.get("deposit", 0)
    rent = item.get("rent", 0)
    size_m2 = float(item.get("size_m2") or 0)
    pyeong = round(size_m2 / 3.3058, 1) if size_m2 else 0
    addr = item.get("address") or ""
    source = item.get("source", "?")
    floor = item.get("floor") or ""
    floor_part = f" · {floor}층" if floor else ""
    size_part = f"{pyeong}평" if pyeong else f"{size_m2}㎡"
    url = item.get("url") or ""
    tag = "🏠" if source == "zigbang" else "🏡"
    return (
        f"{i}. 보증 {deposit}/월 {rent} · {size_part}{floor_part} · {addr} [{source}]\n"
        f"   {tag} {url}"
    )


def format_message(items: list[dict], target: date, stats: dict) -> str:
    header = (
        f"📅 {target.isoformat()} 성북구 투룸/쓰리룸 월세 신규 매물\n\n"
        f"총 {len(items)}건 "
        f"(직방 {stats.get('zigbang_raw', 0)}, 다방 {stats.get('dabang_raw', 0)}, "
        f"필터 후 {stats.get('after_filter', 0)}, 중복제거 후 {len(items)})"
    )
    if not items:
        return header + "\n\n오늘은 신규 매물이 없습니다."
    body_lines = [_format_item(i + 1, it) for i, it in enumerate(items)]
    return header + "\n\n" + "\n".join(body_lines)


def send(items: list[dict], target: date, stats: dict) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    message = format_message(items, target, stats)

    if not token or not chat_id:
        log.warning("텔레그램 미설정 — 메시지를 stdout 으로 출력합니다.\n%s", message)
        return

    for chunk in _chunks(message):
        ok = _send_one(token, chat_id, chunk)
        if not ok:
            log.error("청크 전송 실패")
