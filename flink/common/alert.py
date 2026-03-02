import os
import json
import urllib.request
import time
from datetime import datetime, timedelta, timezone

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_telegram_alert(message):
    try:
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("[Alert] Telegram credentials missing.")
            return

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.getcode() != 200:
                print(f"[Alert] Failed to send Telegram: {response.read()}")
    except Exception as e:
        print(f"[Alert] Error sending Telegram: {e}")


class AlertManager:
    _instance = None
    _history = {}
    _cooldown = 300  # 5 minutes

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AlertManager, cls).__new__(cls)
        return cls._instance

    def is_dnd_active(self):
        """Check if current time is 01:00 ~ 06:00 KST"""
        kst = timezone(timedelta(hours=9))
        now_kst = datetime.now(kst)
        if 1 <= now_kst.hour < 6:
            return True
        return False

    def should_send(self, symbol, cooldown_override=None):
        if self.is_dnd_active():
            print(f"[AlertManager] DND Active. Skipping {symbol}")
            return False

        now = time.time()
        last = self._history.get(symbol, 0)

        cooldown = cooldown_override if cooldown_override is not None else self._cooldown

        if now - last < cooldown:
            return False
        return True

    def update(self, symbol):
        self._history[symbol] = time.time()
