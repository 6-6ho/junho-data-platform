# Trade Helper (Binance USDT-M) 🚀

Real-time crypto market monitoring dashboard powered by Spark Streaming.

![License](https://img.shields.io/badge/license-MIT-blue)
![Stack](https://img.shields.io/badge/stack-React_FastAPI_Spark_Kafka-orange)

## 🌟 Key Features

### 1. Real-time Movers Detection 📈
- **Engine**: Apache Spark Structured Streaming processes Binance WebSocket feed.
- **Logic**: Aggregates price changes over sliding windows (5m, 2h).
- **Alerts**:
    - **UI**: Toast notifications for >5% rise in 5 minutes.
    - **Sound**: Audio alert ("Ding!") for high risers.
    - **Display**: "Time Ago" indicator to verify data freshness.

### 2. Favorites Watchlist ⭐
- Custom watchlist for tracking specific symbols.
- Real-time price updates.
- Auto-symbol correction (e.g., input "BTC" -> converts to "BTCUSDT").

### 3. Binance-Style UI 🎨
- Dark theme (`#0b0e11`) with Binance typography and colors.
- Responsive grid layout.
- Custom Favicon.

---

## 🏗️ Architecture

| Component | Technology | Description |
|-----------|------------|-------------|
| **Frontend** | React + Vite + Tailwind | Responsive Dashboard with Toast/Sound Context |
| **Backend** | FastAPI (Python) | REST API for Movers & Favorites |
| **Ingest** | Python | Binance WS -> Kafka Producer |
| **Processing** | Apache Spark | Real-time Window Aggregation (5m/15s trigger) |
| **Message Queue** | Kafka | Decouples ingestion from processing |
| **Database** | PostgreSQL | Persists Movers history & Favorites |
| **Monitoring** | Prometheus + Grafana | System metrics & Historical data analysis |

---

## 🚀 Deployment

### Prerequisites
- Docker & Docker Compose
- 4GB+ RAM recommended (for Spark + Kafka)

### Run
```bash
# 1. Update and Build
git pull
docker compose up -d --build

# 2. Access
# Frontend: http://localhost:3000
# Grafana: http://localhost:3001 (admin/admin)
```

---

## 📂 Project Structure

```
trade-helper/
├── frontend/           # React dashboard
├── backend/            # FastAPI server
├── spark/              # Spark Streaming Jobs
│   ├── jobs/           # movers_job.py, alerts_job.py
│   └── common/         # Shared DB logic
├── ingest/             # Binance WebSocket ingest
├── infra/              # Prometheus/Grafana config
├── docs/               # Documentation & DDL
└── docker-compose.yml  # Orchestration
```

## 📝 Recent Updates
- **v1.2**: Added Sound Effects & Lowered Alert Threshold to 5%.
- **v1.1**: Implemented Favorites Watchlist & Removed Legacy Chart.
- **v1.0**: Initial Release with Spark Movers.
