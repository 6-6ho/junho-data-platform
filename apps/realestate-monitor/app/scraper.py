"""직방 스크래퍼.

전략: seed-then-delta.
1. List endpoint로 성북구 6개 geohash 의 itemId 모두 받음
2. DB에 없는 itemId 만 detail endpoint 호출 → first_seen_at = NOW()
3. 이미 본 itemId 는 last_seen_at 만 업데이트
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

import asyncpg
import httpx

from . import config
from .db import get_pool

log = logging.getLogger(__name__)


async def fetch_list_for_geohash(client: httpx.AsyncClient, geohash: str) -> list[int]:
    params = {
        "domain": "zigbang",
        "geohash": geohash,
        "sales_type_in": config.SALES_TYPE,
        "deposit_gteq": 0,
        "deposit_lteq": config.DEPOSIT_MAX,
        "rent_gteq": 0,
        "rent_lteq": config.RENT_MAX,
    }
    r = await client.get(config.ZIGBANG_LIST_URL, params=params, timeout=15)
    r.raise_for_status()
    items = r.json().get("items", [])
    return [int(it["itemId"]) for it in items if "itemId" in it]


async def fetch_all_item_ids(client: httpx.AsyncClient) -> set[int]:
    ids: set[int] = set()
    for h in config.SEONGBUK_GEOHASHES:
        try:
            geo_ids = await fetch_list_for_geohash(client, h)
            ids.update(geo_ids)
            log.info("list geohash=%s items=%d", h, len(geo_ids))
        except Exception as e:
            log.warning("list geohash=%s failed: %s", h, e)
    return ids


async def fetch_detail(client: httpx.AsyncClient, item_id: int) -> dict | None:
    url = config.ZIGBANG_DETAIL_URL.format(item_id=item_id)
    try:
        r = await client.get(url, timeout=15)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("detail %s failed: %s", item_id, e)
        return None


def _matches_filter(item: dict) -> bool:
    if item.get("salesType") != config.SALES_TYPE:
        return False
    if item.get("roomType") not in config.ROOM_TYPES:
        return False
    bjd = (item.get("bjdCode") or "")
    if not bjd.startswith(config.SEONGBUK_BJD_PREFIX):
        return False
    if item.get("status") != "open":
        return False
    price = item.get("price") or {}
    deposit = price.get("deposit", 0) or 0
    rent = price.get("rent", 0) or 0
    if deposit > config.DEPOSIT_MAX or rent > config.RENT_MAX:
        return False
    return True


def _flatten(detail: dict) -> dict:
    item = detail["item"]
    price = item.get("price") or {}
    area = item.get("area") or {}
    floor = item.get("floor") or {}
    location = item.get("location") or {}
    address = item.get("addressOrigin") or {}
    manage = item.get("manageCost") or {}
    updated_at = item.get("updatedAt")
    src_updated = None
    if updated_at:
        try:
            src_updated = datetime.fromisoformat(updated_at.replace(" ", "T")).replace(tzinfo=timezone.utc)
        except Exception:
            src_updated = None
    return {
        "source": "zigbang",
        "item_id": str(item["itemId"]),
        "sales_type": item.get("salesType"),
        "service_type": item.get("serviceType"),
        "room_type": item.get("roomType"),
        "deposit": price.get("deposit"),
        "rent": price.get("rent"),
        "manage_cost": manage.get("amount"),
        "area_m2": area.get("전용면적M2"),
        "floor": floor.get("floor"),
        "all_floors": floor.get("allFloors"),
        "title": item.get("title"),
        "description": item.get("description"),
        "address_local": address.get("localText"),
        "jibun_address": item.get("jibunAddress"),
        "bjd_code": item.get("bjdCode"),
        "lat": location.get("lat"),
        "lng": location.get("lng"),
        "image_thumbnail": item.get("imageThumbnail"),
        "options": json.dumps(item.get("options") or [], ensure_ascii=False),
        "movein_date": item.get("moveinDate"),
        "status": item.get("status"),
        "detail_url": config.ZIGBANG_WEB_URL.format(item_id=item["itemId"]),
        "raw": json.dumps(detail, ensure_ascii=False),
        "source_updated_at": src_updated,
    }


async def _existing_ids(conn: asyncpg.Connection) -> set[str]:
    rows = await conn.fetch(
        "SELECT item_id FROM realestate.listings WHERE source = 'zigbang'"
    )
    return {r["item_id"] for r in rows}


async def _insert_listing(conn: asyncpg.Connection, row: dict) -> bool:
    """Returns True if a new row was inserted."""
    result = await conn.execute(
        """
        INSERT INTO realestate.listings (
            source, item_id, sales_type, service_type, room_type,
            deposit, rent, manage_cost, area_m2, floor, all_floors,
            title, description, address_local, jibun_address, bjd_code,
            lat, lng, image_thumbnail, options, movein_date, status,
            detail_url, raw, source_updated_at
        ) VALUES (
            $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,
            $17,$18,$19,$20::jsonb,$21,$22,$23,$24::jsonb,$25
        )
        ON CONFLICT (source, item_id) DO UPDATE
            SET last_seen_at = NOW(),
                status = EXCLUDED.status,
                source_updated_at = EXCLUDED.source_updated_at
        """,
        row["source"], row["item_id"], row["sales_type"], row["service_type"],
        row["room_type"], row["deposit"], row["rent"], row["manage_cost"],
        row["area_m2"], row["floor"], row["all_floors"], row["title"],
        row["description"], row["address_local"], row["jibun_address"],
        row["bjd_code"], row["lat"], row["lng"], row["image_thumbnail"],
        row["options"], row["movein_date"], row["status"], row["detail_url"],
        row["raw"], row["source_updated_at"],
    )
    return result.startswith("INSERT") and "0 1" in result


async def run_scrape() -> dict:
    """Main entry: list → diff → fetch details for new ids → insert."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        run_id = await conn.fetchval(
            "INSERT INTO realestate.scrape_runs (source, status) VALUES ('zigbang', 'running') RETURNING id"
        )

    listed = 0
    new_count = 0
    seen_count = 0
    err_msg = None

    try:
        async with httpx.AsyncClient(headers={"User-Agent": "realestate-monitor/1.0"}) as client:
            all_ids = await fetch_all_item_ids(client)
            listed = len(all_ids)

            async with pool.acquire() as conn:
                already = await _existing_ids(conn)

            new_ids = all_ids - {int(x) for x in already}
            seen_ids = all_ids & {int(x) for x in already}
            seen_count = len(seen_ids)
            log.info("listed=%d already=%d new_candidates=%d", listed, len(already), len(new_ids))

            # Update last_seen for already-known ids in bulk
            if seen_ids:
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE realestate.listings SET last_seen_at = NOW() "
                        "WHERE source = 'zigbang' AND item_id = ANY($1::text[])",
                        [str(x) for x in seen_ids],
                    )

            # Fetch details for new ids only, with concurrency limit
            sem = asyncio.Semaphore(config.DETAIL_CONCURRENCY)

            async def process(iid: int):
                nonlocal new_count
                async with sem:
                    detail = await fetch_detail(client, iid)
                    if config.DETAIL_DELAY_MS:
                        await asyncio.sleep(config.DETAIL_DELAY_MS / 1000)
                if not detail or "item" not in detail:
                    return
                if not _matches_filter(detail["item"]):
                    return
                row = _flatten(detail)
                async with pool.acquire() as conn:
                    inserted = await _insert_listing(conn, row)
                if inserted:
                    new_count += 1

            await asyncio.gather(*(process(i) for i in new_ids))

    except Exception as e:
        log.exception("scrape failed")
        err_msg = str(e)

    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE realestate.scrape_runs SET finished_at = NOW(), "
            "status = $1, listed_count = $2, new_count = $3, seen_count = $4, error_message = $5 "
            "WHERE id = $6",
            "error" if err_msg else "ok",
            listed, new_count, seen_count, err_msg, run_id,
        )

    return {"listed": listed, "new": new_count, "seen": seen_count, "error": err_msg}
