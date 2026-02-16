# System Architecture

## Overview
The Junho Data Platform is a high-performance, real-time analytics system processing both Crypto Trade data and Shopping Mall events.
It leverages **Spark Structured Streaming** for low-latency processing and **Airflow** for batch orchestration.

```mermaid
graph TD
    subgraph Data Sources
        Binance[Binance WebSocket] --> Ingest[Trade Ingest Service]
        ShopUsers[Shop Users] --> ShopGen[Shop Generator]
    end

    subgraph Messaging
        Ingest --> Kafka{Apache Kafka}
        ShopGen --> Kafka
    end

    subgraph Processing Layer [Spark Cluster]
        Kafka --> SparkDriver[Unified Spark Driver]
        SparkDriver --> Worker1[Spark Worker 1]
        SparkDriver --> Worker2[Spark Worker 2]
        
        SparkDriver --"Trade Stream (Always On)"--> TradeProc[Movers Detection]
        SparkDriver --"Shop Stream (Toggle)"--> ShopProc[Shop ETL]
        
        TradeProc --"Alert (Rise Only)"--> Telegram[Telegram Bot]
    end

    subgraph Storage
        TradeProc --> Postgres[(PostgreSQL)]
        ShopProc --> Postgres
        ShopProc --> Iceberg[(MinIO / Iceberg)]
    end

    subgraph Serving & Monitoring
        Postgres --> Backend[FastAPI Backend]
        
        Airflow --> SparkBatch[Daily Report Generation]
        SparkBatch --"Structured Metrics"--> Postgres[(Report Archive)]
        
        Backend --> TradeUI[Trade Frontend]
        Postgres --> ShopUI[Shop Analytics UI]
        
        Postgres --> Grafana[Grafana Dashboards]
    end

    style Telegram fill:#0088cc,stroke:#fff,stroke-width:2px,color:#fff
    style SparkDriver fill:#E25A1C,stroke:#fff,stroke-width:2px,color:#fff
```

## Deployment & Configuration

### 🔔 Telegram Alerts
Configure credentials in `.env` file at project root:
```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789
```

### 🎛️ Streaming Modes
Control resource allocation via `docker-compose.yml` or `.env`:
- **Trade Only Mode**: Set `ENABLE_SHOP_STREAMING=false` to dedicate resources to Trade latency.
- **Unified Mode**: Set `ENABLE_SHOP_STREAMING=true` (Data Lake ETL enabled).
