"""
직방 API 수집기.

공식 문서 없음 — DevTools에서 확인한 내부 API 기반. 응답 스키마/엔드포인트는
예고 없이 바뀔 수 있으므로 실행 전 검증 필요.

성북구(bbox 37.575~37.635 / 126.995~127.060)를 덮는 precision=5 geohash들을
런타임에 계산해 각각 조회한 뒤, 응답을 공통 스키마로 정규화한다.
"""
import logging

import requests

# geohash base32 알파벳
_B32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def _encode_geohash(lat: float, lon: float, precision: int = 5) -> str:
    """표준 geohash 인코더 (pure Python, deps 없음)."""
    lat_lo, lat_hi = -90.0, 90.0
    lon_lo, lon_hi = -180.0, 180.0
    bits = 0
    bit_count = 0
    even = True  # True 이면 경도 비트 차례
    out = []
    while len(out) < precision:
        if even:
            mid = (lon_lo + lon_hi) / 2
            if lon >= mid:
                bits = (bits << 1) | 1
                lon_lo = mid
            else:
                bits = bits << 1
                lon_hi = mid
        else:
            mid = (lat_lo + lat_hi) / 2
            if lat >= mid:
                bits = (bits << 1) | 1
                lat_lo = mid
            else:
                bits = bits << 1
                lat_hi = mid
        even = not even
        bit_count += 1
        if bit_count == 5:
            out.append(_B32[bits])
            bits = 0
            bit_count = 0
    return "".join(out)

log = logging.getLogger(__name__)

LIST_URL = "https://apis.zigbang.com/v2/items/villa"
DETAIL_URL = "https://apis.zigbang.com/v2/items/list"

# 성북구 대략적 bbox (s, w, n, e)
SEONGBUK_BBOX = (37.575, 126.995, 37.635, 127.060)

# 세부 조회 1회 요청당 넣을 최대 item_id 수
DETAIL_CHUNK = 900

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; realestate-monitor/1.0)",
    "Accept": "application/json",
}


def _geohashes_for_bbox(bbox: tuple, precision: int = 5) -> list[str]:
    """bbox 내부를 덮는 geohash 집합. precision=5면 한 셀이 약 4.9×4.9km."""
    south, west, north, east = bbox
    hashes: set[str] = set()
    lat = south
    # 5자리 geohash가 위도 0.043°, 경도 0.087° 정도이므로 0.01° 스텝이면 충분.
    while lat <= north:
        lon = west
        while lon <= east:
            hashes.add(_encode_geohash(lat, lon, precision))
            lon += 0.01
        lat += 0.01
    return sorted(hashes)


def _list_item_ids(geohash: str) -> list[int]:
    """geohash 하나에 해당하는 매물 ID 목록."""
    params = {
        "domain": "zigbang",
        "geohash": geohash,
        "sales_type_in": "월세",
        "service_type_eq": "빌라",
        "deposit_gteq": 0,
        "deposit_lteq": 3000,
        "rent_gteq": 0,
        "rent_lteq": 120,
    }
    resp = requests.get(LIST_URL, params=params, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("items") or []
    ids = [it.get("item_id") or it.get("itemId") for it in items]
    return [i for i in ids if i]


def _fetch_details(item_ids: list[int]) -> list[dict]:
    """item_id 목록을 상세 스키마로 펼침. 900개씩 청크."""
    out: list[dict] = []
    for i in range(0, len(item_ids), DETAIL_CHUNK):
        chunk = item_ids[i : i + DETAIL_CHUNK]
        body = {"domain": "zigbang", "withCoalition": True, "item_ids": chunk}
        resp = requests.post(DETAIL_URL, json=body, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        out.extend(data.get("items") or [])
    return out


def _normalize(raw: dict) -> dict:
    """직방 응답을 공통 스키마로 변환."""
    item_id = raw.get("item_id") or raw.get("itemId")
    addr_parts = [
        raw.get("address1") or "",
        raw.get("address2") or "",
        raw.get("address3") or "",
    ]
    address = " ".join(p for p in addr_parts if p).strip()

    return {
        "source": "zigbang",
        "id": str(item_id) if item_id is not None else "",
        "url": f"https://www.zigbang.com/home/villa/items/{item_id}" if item_id else "",
        "title": raw.get("title") or raw.get("description") or "",
        "address": address,
        "address_road": raw.get("address1") or "",
        "deposit": int(raw.get("deposit") or 0),
        "rent": int(raw.get("rent") or 0),
        "size_m2": float(raw.get("size_m2") or raw.get("전용면적_m2") or 0),
        "floor": str(raw.get("floor") or ""),
        "building_floor": str(raw.get("building_floor") or ""),
        "sales_type": raw.get("sales_type") or "",
        "service_type": raw.get("service_type") or "",
        "room_type": raw.get("room_type") or "",
        "reg_date": raw.get("reg_date") or raw.get("registDate") or "",
        "thumbnail": raw.get("images_thumbnail") or "",
    }


def fetch_seongbuk() -> list[dict]:
    """성북구 빌라 월세 매물을 공통 스키마 리스트로 반환."""
    hashes = _geohashes_for_bbox(SEONGBUK_BBOX, precision=5)
    log.info("직방: geohash %d개 조회 — %s", len(hashes), hashes)

    all_ids: set[int] = set()
    for gh in hashes:
        try:
            ids = _list_item_ids(gh)
        except Exception as e:
            log.warning("직방 list 실패 geohash=%s: %s", gh, e)
            continue
        all_ids.update(ids)

    log.info("직방: 수집 후보 %d건", len(all_ids))
    if not all_ids:
        return []

    try:
        details = _fetch_details(sorted(all_ids))
    except Exception as e:
        log.error("직방 detail 실패: %s", e)
        return []

    items = [_normalize(d) for d in details]
    log.info("직방: 정규화 결과 %d건", len(items))
    return items
