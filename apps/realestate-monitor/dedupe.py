"""
직방·다방 중복 제거.

키: (주소 정규화, 면적 반올림, 보증금, 월세) 튜플.
같은 집이면 직방이 상세정보가 더 많은 편이라 충돌 시 직방 우선.
"""
import logging
import re

log = logging.getLogger(__name__)

_WS = re.compile(r"\s+")
_NON_WORD = re.compile(r"[^0-9a-z가-힣\-]")

SOURCE_PRIORITY = {"zigbang": 0, "dabang": 1}


def normalize_address(addr: str) -> str:
    if not addr:
        return ""
    s = addr.strip().lower()
    s = _WS.sub("", s)
    s = _NON_WORD.sub("", s)
    return s


def make_key(item: dict) -> str:
    addr = normalize_address(item.get("address_road") or item.get("address") or "")
    try:
        size = round(float(item.get("size_m2") or 0))
    except (TypeError, ValueError):
        size = 0
    deposit = int(item.get("deposit") or 0)
    rent = int(item.get("rent") or 0)
    return f"{addr}|{size}|{deposit}|{rent}"


def dedupe(items: list[dict]) -> list[dict]:
    """같은 키면 source priority 가 낮은(=선호) 쪽을 남긴다."""
    bucket: dict[str, dict] = {}
    for it in items:
        key = make_key(it)
        if not key or key == "|0|0|0":
            # 키가 빈약하면 dedupe 대상에서 제외하고 무조건 유지
            bucket[f"__keep__{id(it)}"] = it
            continue
        existing = bucket.get(key)
        if existing is None:
            bucket[key] = it
            continue
        if SOURCE_PRIORITY.get(it.get("source"), 99) < SOURCE_PRIORITY.get(
            existing.get("source"), 99
        ):
            bucket[key] = it
    result = list(bucket.values())
    log.info("중복제거: %d → %d건", len(items), len(result))
    return result
