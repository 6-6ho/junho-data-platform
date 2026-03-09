"""
Infrastructure Monitor — Docker events → Telegram alerts.
Watches container die/start events and sends notifications.
No DND (24/7 infrastructure monitoring).
"""
import os
import json
import time
import urllib.request
from datetime import datetime, timezone, timedelta

import docker

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Track recent deaths for recovery detection
recent_deaths: dict[str, float] = {}  # container_name -> die timestamp


def send_telegram(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[Monitor] Telegram credentials missing. Message: {message}")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.getcode() != 200:
                print(f"[Monitor] Telegram send failed: {resp.read()}")
    except Exception as e:
        print(f"[Monitor] Telegram error: {e}")


def format_kst(ts: float) -> str:
    kst = timezone(timedelta(hours=9))
    return datetime.fromtimestamp(ts, tz=kst).strftime("%H:%M:%S KST")


def main():
    print("[Monitor] Starting infrastructure monitor...")
    client = docker.from_env()

    # Verify connection
    info = client.info()
    print(f"[Monitor] Connected to Docker: {info.get('Name', 'unknown')}")
    print(f"[Monitor] Containers: {info.get('ContainersRunning', '?')} running")

    send_telegram("🟢 *인프라 모니터 시작*\n랩탑 Docker 이벤트 감시 중")

    for event in client.events(decode=True):
        status = event.get("status")
        if status not in ("die", "start"):
            continue

        actor = event.get("Actor", {})
        attrs = actor.get("Attributes", {})
        container_name = attrs.get("name", "unknown")
        now = time.time()

        # Skip self
        if "infra-monitor" in container_name:
            continue

        if status == "die":
            exit_code = attrs.get("exitCode", "?")
            recent_deaths[container_name] = now
            msg = (
                f"🔴 *컨테이너 다운*\n"
                f"• 이름: `{container_name}`\n"
                f"• Exit Code: `{exit_code}`\n"
                f"• 시간: {format_kst(now)}"
            )
            print(f"[Monitor] DIE: {container_name} (exit={exit_code})")
            send_telegram(msg)

        elif status == "start":
            if container_name in recent_deaths:
                die_time = recent_deaths.pop(container_name)
                downtime_sec = now - die_time
                if downtime_sec < 60:
                    downtime_str = f"{downtime_sec:.0f}초"
                else:
                    downtime_str = f"{downtime_sec / 60:.1f}분"
                msg = (
                    f"🟢 *컨테이너 복구*\n"
                    f"• 이름: `{container_name}`\n"
                    f"• 다운타임: {downtime_str}\n"
                    f"• 시간: {format_kst(now)}"
                )
                print(f"[Monitor] RECOVERED: {container_name} (downtime={downtime_str})")
                send_telegram(msg)


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"[Monitor] Fatal error: {e}, restarting in 10s...")
            time.sleep(10)
