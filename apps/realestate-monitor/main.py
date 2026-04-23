"""
성북구 투룸/쓰리룸 월세 신규 매물 일일 알림.

매일 08:00 KST 기준, 어제(어제 00:00~24:00 KST) 등록된 매물을
직방+다방에서 수집해 중복 제거 후 텔레그램으로 보낸다.

GitHub Actions 크론에서 호출되는 엔트리포인트 (python -m apps.realestate-monitor.main
또는 workflow 가 apps/realestate-monitor 로 cd 한 뒤 python main.py).
"""
import logging
import sys
from datetime import datetime

from dotenv import load_dotenv

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


def _safe_fetch(name: str, fn):
    try:
        return fn()
    except Exception as e:
        log.error("%s 수집 실패: %s", name, e)
        return []


def run_daily() -> int:
    load_dotenv()
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
    return 0


if __name__ == "__main__":
    try:
        sys.exit(run_daily())
    except Exception as e:
        log.exception("치명적 오류: %s", e)
        # 크론 실행 실패도 텔레그램으로 알리고 싶으면 여기서 send([], ...) 호출 가능
        sys.exit(1)
