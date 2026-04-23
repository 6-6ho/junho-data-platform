"""
공통 필터: 등록일(어제 KST) / 가격 / 지역('성북구' 포함).
reg_date 포맷은 소스마다 다르므로 여러 케이스를 받아낸다.
"""
import logging
from datetime import date, datetime, timedelta, timezone

log = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))


def yesterday_kst(now: datetime | None = None) -> date:
    now = now or datetime.now(KST)
    return (now.astimezone(KST) - timedelta(days=1)).date()


def _to_kst_date(value) -> date | None:
    """reg_date 후보값을 KST 기준 date 로 변환. 알 수 없는 포맷이면 None."""
    if value in (None, "", 0):
        return None

    # epoch 초/밀리초
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:  # ms
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(KST).date()
        except (OverflowError, OSError, ValueError):
            return None

    s = str(value).strip()
    if not s:
        return None

    # ISO 8601 계열 (e.g. "2026-04-22T10:15:00+09:00", "2026-04-22 10:15:00")
    iso_candidates = [s]
    if " " in s and "T" not in s:
        iso_candidates.append(s.replace(" ", "T"))
    for cand in iso_candidates:
        try:
            dt = datetime.fromisoformat(cand.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=KST)
            return dt.astimezone(KST).date()
        except ValueError:
            pass

    # 순수 날짜 포맷
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue

    log.debug("reg_date 파싱 실패: %r", value)
    return None


def is_on_date(reg_date_value, target: date, slack_days: int = 1) -> bool:
    """reg_date가 target ± slack_days 에 들어오는지.

    타임존 표기가 없거나 KST/UTC 혼용 케이스가 있어 기본 ±1일 여유를 둔다.
    """
    d = _to_kst_date(reg_date_value)
    if d is None:
        # 포맷을 모를 땐 보수적으로 통과시킨다 (후속 단계에서 걸러짐)
        return True
    delta = abs((d - target).days)
    return delta <= slack_days


def matches_price(item: dict, max_deposit: int = 3000, max_rent: int = 120) -> bool:
    try:
        return int(item.get("deposit", 0)) <= max_deposit and int(item.get("rent", 0)) <= max_rent
    except (TypeError, ValueError):
        return False


def matches_region(item: dict, keyword: str = "성북구") -> bool:
    """주소에 '성북구' 포함 여부. geohash/bbox 오버슬랩 보정용."""
    addr = (item.get("address") or "") + " " + (item.get("address_road") or "")
    return keyword in addr


def apply_all(
    items: list[dict],
    target_date: date,
    max_deposit: int = 3000,
    max_rent: int = 120,
) -> list[dict]:
    kept = []
    dropped_region = dropped_price = dropped_date = 0
    for it in items:
        if not matches_region(it):
            dropped_region += 1
            continue
        if not matches_price(it, max_deposit, max_rent):
            dropped_price += 1
            continue
        if not is_on_date(it.get("reg_date"), target_date):
            dropped_date += 1
            continue
        kept.append(it)
    log.info(
        "필터 결과: 유지 %d / 지역제외 %d / 가격제외 %d / 날짜제외 %d",
        len(kept), dropped_region, dropped_price, dropped_date,
    )
    return kept
