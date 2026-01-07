# Data Schemas

## 1) Kafka: raw.ticker.usdtm
### Key
- symbol (string)

### Value (JSON)
```json
{
  "event_time_ms": 1704550000123,
  "symbol": "BTCUSDT",
  "price": 43123.12,
  "volume_24h": 123456.78,
  "quote_volume_24h": 987654321.12,
  "change_pct_24h": 3.21
}
```

## 2) Kafka: movers.events
### Key
- symbol

### Value (JSON)
```json
{
  "event_time_ms": 1704550000123,
  "symbol": "BTCUSDT",
  "type": "rise",
  "status": "[Mid] 5 min Rise",
  "window": "5m",
  "change_pct_window": 8.12,
  "change_pct_24h": 3.21,
  "vol_15m": 12345.0,
  "avg_vol_15m_24h": 200.0,
  "vol_ratio": 61.7
}
```

## 3) Kafka: alerts.config (upsert/delete)
### Key
- line_id (uuid string)

### Value (JSON)
```json
{
  "op": "upsert",
  "line_id": "8b3c...uuid",
  "symbol": "BTCUSDT",
  "t1_ms": 1704549000000,
  "p1": 42000.5,
  "t2_ms": 1704549600000,
  "p2": 42510.2,
  "basis": "close",
  "mode": "both",
  "buffer_pct": 0.1,
  "cooldown_sec": 600,
  "enabled": true,
  "updated_at_ms": 1704550000000
}
```

## 4) Kafka: alerts.events
### Key
- symbol

### Value (JSON)
```json
{
  "event_time_ms": 1704550100123,
  "symbol": "BTCUSDT",
  "line_id": "8b3c...uuid",
  "direction": "break_up",
  "price": 43123.1,
  "line_price": 43080.0,
  "buffer_pct": 0.1
}
```
