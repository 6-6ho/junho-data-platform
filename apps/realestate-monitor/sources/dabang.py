"""
다방 API 수집기.

공식 문서 없음 — DevTools 캡처 기반. 페이로드 스키마가 바뀌기 쉬우니 실행 전 검증 필요.
bbox(성북구 대략 좌표)를 한 번에 보내서 투룸·쓰리룸 월세만 받는다.
"""
import logging

import requests

log = logging.getLogger(__name__)

ENDPOINT = "https://www.dabangapp.com/api/3/room/list/multi-room/bbox"

# 성북구 bbox
SOUTH, WEST = 37.575, 126.995
NORTH, EAST = 37.635, 127.060

# 한 번에 받을 최대 개수 (기본 200, API 상한 불명이라 넉넉히 500)
TAKE = 500

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; realestate-monitor/1.0)",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Csrf-Token": "nocheck",
}


def _build_filters() -> dict:
    """다방 매물 리스트 요청 바디."""
    return {
        "api_version": "3.0.1",
        "filters": {
            "multi_room_type": [1, 2],   # 1=투룸, 2=쓰리룸
            "selling_type": [1, 2],       # 월세 계열
            "deposit_range": [0, 3000],
            "price_range": [0, 120],
            "deal_type": [0, 1],
        },
        "location": {
            "sw_lng": WEST,
            "sw_lat": SOUTH,
            "ne_lng": EAST,
            "ne_lat": NORTH,
        },
        "use_map": "naver",
        "zoom": 14,
        "take": TAKE,
        "skip": 0,
    }


def _normalize(raw: dict) -> dict:
    """다방 응답을 공통 스키마로 변환."""
    room_id = raw.get("id") or raw.get("room_id") or raw.get("_id") or ""
    address = raw.get("address") or raw.get("jibun_address") or raw.get("road_address") or ""
    size = raw.get("room_size") or raw.get("size_m2") or raw.get("전용면적_m2") or 0

    return {
        "source": "dabang",
        "id": str(room_id),
        "url": f"https://www.dabangapp.com/room/{room_id}" if room_id else "",
        "title": raw.get("title") or raw.get("name") or "",
        "address": address,
        "address_road": raw.get("road_address") or address,
        "deposit": int(raw.get("deposit") or 0),
        "rent": int(raw.get("price") or raw.get("rent") or 0),
        "size_m2": float(size or 0),
        "floor": str(raw.get("floor_string") or raw.get("floor") or ""),
        "building_floor": str(raw.get("building_floor") or ""),
        "sales_type": "월세",
        "service_type": "빌라/다세대",
        "room_type": str(raw.get("room_type_str") or raw.get("room_type") or ""),
        "reg_date": raw.get("reg_date") or raw.get("regist_date") or raw.get("saved_time") or "",
        "thumbnail": raw.get("img_url") or raw.get("photo_thumbnail") or "",
    }


def fetch_seongbuk() -> list[dict]:
    """성북구 bbox 내 투룸·쓰리룸 월세 매물."""
    body = _build_filters()
    try:
        resp = requests.post(ENDPOINT, json=body, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        log.error("다방 요청 실패: %s", e)
        return []

    data = resp.json()
    # 응답 구조 후보: {"rooms": [...]} 또는 {"result": {"rooms": [...]}} 등
    rooms = data.get("rooms") or data.get("result", {}).get("rooms") or data.get("items") or []
    if not isinstance(rooms, list):
        log.warning("다방 응답 스키마 예상 밖: keys=%s", list(data.keys()))
        return []

    items = [_normalize(r) for r in rooms if isinstance(r, dict)]
    log.info("다방: 수집 %d건", len(items))
    return items
