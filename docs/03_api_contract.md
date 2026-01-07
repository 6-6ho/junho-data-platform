# API Contract

> 외부 포트는 프론트 1개만 노출. 프론트는 Nginx 프록시로 `/api/*` 를 백엔드로 호출한다.

## 1) Movers
### GET /api/movers/latest
- Query
  - `type`: `rise` | `high_vol_up`
  - `limit`: 기본 20
- Response (JSON)
```json
[
  {
    "symbol": "BTCUSDT",
    "event_time": "2026-01-07T00:12:10Z",
    "status": "[Mid] 5 min Rise",
    "window": "5m",
    "change_pct_window": 8.12,
    "change_pct_24h": 3.21,
    "vol_ratio": null
  }
]
```

## 2) Klines (차트용)
### GET /api/klines
- Query: `symbol`, `interval`, `limit`
- Response: OHLCV 리스트
```json
[
  [1704550000000, "42000.0", "42120.0", "41980.0", "42050.0", "123.45"]
]
```

## 3) Trendlines CRUD
### GET /api/trendlines?symbol=BTCUSDT
### POST /api/trendlines
### PUT /api/trendlines/{line_id}
### DELETE /api/trendlines/{line_id}

Trendline payload (v1: basis=close 고정 가능)
```json
{
  "symbol": "BTCUSDT",
  "t1_ms": 1704549000000,
  "p1": 42000.5,
  "t2_ms": 1704549600000,
  "p2": 42510.2,
  "basis": "close",
  "mode": "both",
  "buffer_pct": 0.1,
  "cooldown_sec": 600,
  "enabled": true
}
```

## 4) Alerts feed
### GET /api/alerts/latest?symbol=BTCUSDT&limit=50
Response
```json
[
  {
    "event_time": "2026-01-07T00:15:00Z",
    "symbol": "BTCUSDT",
    "line_id": "8b3c...uuid",
    "direction": "break_up",
    "price": 43123.1,
    "line_price": 43080.0,
    "buffer_pct": 0.1
  }
]
```
