"""
성북구 투룸/쓰리룸 월세 신규 매물 일일 알림.

docker-compose 에서 상시 가동되는 데몬. 매일 08:00 KST 에 기상 →
어제(00:00~24:00 KST) 등록된 직방·다방 매물을 수집·중복제거 → 텔레그램 발송.

수동 1회 실행이 필요하면 `RUN_ONCE=true` 환경변수로 기동.
"""
import logging
import os
import sys
import time
from datetime import datetime, timedelta

from dedupe import dedupe
from filters import KST, apply_all, yesterday_kst
from notifier import send
from sources import dabang, zigbang

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("realestate")

RUN_HOUR = int(os.getenv("RUN_HOUR_KST", "8"))
RUN_MINUTE = int(os.getenv("RUN_MINUTE_KST", "0"))
RUN_ONCE = os.getenv("RUN_ONCE", "false").lower() == "true"


def _safe_fetch(name: str, fn):
    try:
        return fn()
    except Exception as e:
        log.error("%s 수집 실패: %s", name, e)
        return []


def run_daily() -> None:
    now = datetime.now(KST)
    target = yesterday_kst(now)
    log.info("실행 시각 %s (KST) — 어제(%s) 등록 매물 조회", now.isoformat(), target.isoformat())

    zigbang_items = _safe_fetch("직방", zigbang.fetch_seongbuk)
    dabang_items = _safe_fetch("다방", dabang.fetch_seongbuk)

    stats = {
        "zigbang_raw": len(zigbang_items),
        "dabang_raw": len(dabang_items),
    }
    log.info("원본: 직방 %d / 다방 %d", stats["zigbang_raw"], stats["dabang_raw"])

    merged = zigbang_items + dabang_items
    filtered = apply_all(merged, target_date=target, max_deposit=3000, max_rent=120)
    stats["after_filter"] = len(filtered)

    deduped = dedupe(filtered)
    log.info("최종: %d건", len(deduped))

    send(deduped, target, stats)


def _sleep_until_next_run() -> None:
    now = datetime.now(KST)
    next_run = now.replace(hour=RUN_HOUR, minute=RUN_MINUTE, second=0, microsecond=0)
    if next_run <= now:
        next_run += timedelta(days=1)
    secs = (next_run - now).total_seconds()
    log.info("다음 실행: %s KST (%.1f시간 뒤)", next_run.isoformat(), secs / 3600)
    # 15분씩 쪼개서 대기 — 컨테이너 시계 drift 를 주기적으로 재확인
    while True:
        remaining = (next_run - datetime.now(KST)).total_seconds()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 900))


def main_loop() -> None:
    log.info("realestate-monitor 시작 (매일 %02d:%02d KST 실행)", RUN_HOUR, RUN_MINUTE)
    while True:
        _sleep_until_next_run()
        try:
            run_daily()
        except Exception as e:
            log.exception("run_daily 실패: %s", e)
        # 한 번 실행 후 1분 대기(같은 분에 두 번 실행 방지)
        time.sleep(60)


if __name__ == "__main__":
    if RUN_ONCE:
        log.info("RUN_ONCE 모드 — 1회만 실행")
        run_daily()
        sys.exit(0)
    try:
        main_loop()
    except KeyboardInterrupt:
        log.info("종료 신호 수신")
        sys.exit(0)
