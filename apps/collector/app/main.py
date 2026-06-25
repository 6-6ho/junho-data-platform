# 분석 이벤트 콜렉터 — 전 앱 공용 SSOT. 얇은 beacon(sendBeacon, text/plain)을 받아
# analytics.events(Postgres)에 적재. purchase 이벤트는 Discord로 알림.
#
# 설계: 앱은 /e 하나만 호출하고 204를 즉시 받음(대기 0). 적재·디코는 서버 책임.
# 동심원 이벤트: Core(signup·activate·app_open·purchase) + Extended(앱별 추가). 스키마-on-read.
# identity: 이벤트에 user_id 있으면 같이 저장 + $identify 로 distinct_id→user_id 매핑(조회 시점 해소).

import asyncio
import json
import os
import re
from datetime import datetime, timezone

import asyncpg
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

DB = dict(
    host=os.getenv("DB_HOST", "postgres"),
    port=int(os.getenv("DB_PORT", "5432")),
    database=os.getenv("DB_NAME", "app"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", "postgres"),
)
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# 봇/프리페치/모니터 드랍 — 안 거르면 funnel 이 거짓말함.
BOT = re.compile(
    r"bot|crawl|spider|slurp|preview|monitor|curl|wget|python-|httpx|headless|"
    r"facebookexternal|whatsapp|telegram|lighthouse|pingdom|uptime|google-",
    re.I,
)

DDL = """
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE TABLE IF NOT EXISTS analytics.events (
  id          bigserial PRIMARY KEY,
  app         text NOT NULL,
  event       text NOT NULL,
  distinct_id text NOT NULL,
  user_id     text,
  session_id  text,
  ts          timestamptz NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now(),
  props       jsonb NOT NULL DEFAULT '{}',
  ctx         jsonb NOT NULL DEFAULT '{}',
  country     text,
  ua          text
);
CREATE INDEX IF NOT EXISTS events_app_event_ts ON analytics.events(app, event, ts);
CREATE INDEX IF NOT EXISTS events_app_distinct ON analytics.events(app, distinct_id);
CREATE INDEX IF NOT EXISTS events_user ON analytics.events(app, user_id) WHERE user_id IS NOT NULL;
CREATE TABLE IF NOT EXISTS analytics.identities (
  app         text NOT NULL,
  distinct_id text NOT NULL,
  user_id     text NOT NULL,
  first_seen  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (app, distinct_id)
);
"""

app = FastAPI(title="analytics-collector")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # beacon 은 응답을 안 읽지만 fetch fallback 대비 허용
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)
pool: asyncpg.Pool | None = None


@app.on_event("startup")
async def startup() -> None:
    global pool
    pool = await asyncpg.create_pool(**DB, min_size=1, max_size=5)
    async with pool.acquire() as c:
        await c.execute(DDL)


@app.get("/health")
async def health():
    async with pool.acquire() as c:
        await c.fetchval("SELECT 1")
    return {"ok": True}


def _dt(ms) -> datetime:
    try:
        return datetime.fromtimestamp(float(ms) / 1000, tz=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _jsonb(v) -> str:
    # props/ctx 를 jsonb 텍스트로. 과도하면 통째로 비움(잘린 JSON 방지).
    try:
        s = json.dumps(v if isinstance(v, dict) else {})
    except Exception:
        return "{}"
    return s if len(s) <= 8000 else "{}"


@app.post("/e")
async def ingest(request: Request):
    ua = request.headers.get("user-agent", "")
    if BOT.search(ua):
        return Response(status_code=204)  # 봇 드랍 (조용히)
    country = request.headers.get("cf-ipcountry")

    try:
        data = json.loads(await request.body() or b"{}")
    except Exception:
        return Response(status_code=204)
    batch = data if isinstance(data, list) else [data]

    rows = []
    identifies = []
    purchases = []
    for e in batch[:50]:  # 한 요청당 최대 50 이벤트
        if not isinstance(e, dict):
            continue
        app_ = str(e.get("app", ""))[:64]
        ev = str(e.get("event", ""))[:128]
        did = str(e.get("distinct_id", ""))[:128]
        if not app_ or not ev or not did:
            continue
        props = e.get("props") if isinstance(e.get("props"), dict) else {}
        uid = props.get("userId") or e.get("user_id")
        uid = str(uid)[:128] if uid else None
        sid = str(e.get("session_id"))[:128] if e.get("session_id") else None
        rows.append(
            (app_, ev, did, uid, sid, _dt(e.get("ts", 0)),
             _jsonb(props), _jsonb(e.get("ctx")), country, ua[:256])
        )
        if ev == "$identify" and uid:
            identifies.append((app_, did, uid))
        if ev == "purchase":
            purchases.append(e)

    if rows:
        async with pool.acquire() as c:
            await c.executemany(
                "INSERT INTO analytics.events"
                "(app,event,distinct_id,user_id,session_id,ts,props,ctx,country,ua) "
                "VALUES($1,$2,$3,$4,$5,$6,$7::jsonb,$8::jsonb,$9,$10)",
                rows,
            )
            for a, d, u in identifies:
                await c.execute(
                    "INSERT INTO analytics.identities(app,distinct_id,user_id) "
                    "VALUES($1,$2,$3) ON CONFLICT(app,distinct_id) "
                    "DO UPDATE SET user_id=EXCLUDED.user_id",
                    a, d, u,
                )

    for p in purchases:
        asyncio.create_task(_notify_discord(p))

    return Response(status_code=204)


async def _notify_discord(e: dict) -> None:
    if not DISCORD_WEBHOOK_URL:
        return
    pr = e.get("props", {}) if isinstance(e.get("props"), dict) else {}
    msg = (
        f"\U0001F4B0 **결제** `{e.get('app','?')}` — "
        f"{pr.get('pkg','?')} / {pr.get('amount','?')}원 "
        f"(user {pr.get('userId','anon')})"
    )
    try:
        async with httpx.AsyncClient(timeout=5) as cl:
            await cl.post(DISCORD_WEBHOOK_URL, json={"content": msg})
    except Exception:
        pass  # 알림 실패는 적재에 영향 0
