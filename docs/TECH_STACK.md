# Technical Stack & Decision Rationale

This document outlines the core technologies used in the **Junho Data Platform** and the reasoning behind each choice.

---

## 🏗️ Core Infrastructure

### **Docker Compose**
> **Why?** Simplified Orchestration for Single-Node Cluster
- **Decision**: Instead of using heavy orchestration tools like Kubernetes (K8s), we chose Docker Compose for a lightweight, single-node deployment suitable for development and small-scale production.
- **Benefit**:
    - **Resource Efficiency**: Minimal overhead compared to K8s.
    - **Environment Consistency**: Identical setup across dev/prod.
    - **Dynamic Toggling**: Easy to enable/disable specific services (e.g., Shop Streaming) via environment variables to manage resource contention.

### **Apache Kafka**
> **Why?** Decoupling & Backpressure Management
- **Decision**: Kafka serves as the central message bus, buffering high-throughput WebSocket data from Binance.
- **Benefit**:
    - **Decoupling**: The Ingest service (Producer) and Spark (Consumer) operate independently. If Spark restarts, data persists in Kafka.
    - **Scalability**: Partitioning allows parallel processing (currently 4 partitions for `ticker.usdtm`).

---

## ⚡ Data Processing

### **Apache Spark Structured Streaming**
> **Why?** High-Throughput Window Aggregation
- **Decision**: We needed to aggregate thousands of price updates per second into 5-minute sliding windows.
- **Benefit**:
    - **State Management**: Built-in watermark handling for late-arriving data.
    - **Micro-batch Processing**: Achieves sub-second latency (0.8s) while maintaining exactly-once semantics.
    - **Rich API**: SQL-like syntax makes complex window aggregations readable and maintainable.

### **Apache Airflow**
> **Why?** Dependency Management for Batch Jobs
- **Decision**: For daily reporting and shop analytics (Affinity, RFM), tasks must run in a specific order (Ingest -> ETL -> Mart).
- **Benefit**:
    - **DAG Visualization**: Easy monitoring of complex workflows.
    - **Retry Logic**: Automatic retries on transient failures (e.g., MinIO momentarily down).
    - **Backfilling**: Ability to re-run historical data analytics.

---

## 🎨 Frontend Application

### **React + Vite**
> **Why?** Modern SPA Performance & Developer Experience
- **Decision**: Migrated from legacy Create-React-App to Vite for lightning-fast HMR (Hot Module Replacement) and build times.
- **Benefit**:
    - **Performance**: Significant reduction in bundle size and load time.
    - **Ecosystem**: Access to vast React libraries (Lucide Icons, Recharts).

### **Recharts**
> **Why?** Composable & Declarative Visualization
- **Decision**: Chosen for the V3 Dashboard over Chart.js or D3.
- **Benefit**:
    - **React-Native Feel**: Chart components are composed as JSX elements (e.g., `<BarChart><XAxis /><YAxis /></BarChart>`), aligning perfectly with React's component model.
    - **Responsiveness**: `ResponsiveContainer` handles window resizing automatically.
    - **Customizability**: Easy to inject custom tooltips and legends.

### **Tailwind CSS**
> **Why?** Rapid UI Development & Design System
- **Decision**: Utility-first CSS framework to build a custom "Dark Mode" design system without fighting global styles.
- **Benefit**:
    - **Consistency**: Centralized color palette (zinc-900, orange-500) ensures visual coherence.
    - **Glassmorphism**: Easy implementation of backdrop-blur effects for premium UI.

---

## 🛡️ Backend & Serving

### **FastAPI (Python)**
> **Why?** Async I/O & Automatic Docs
- **Decision**: High-performance Python web framework to serve metrics from PostgreSQL to the implementation.
- **Benefit**:
    - **Async Support**: Handles multiple concurrent requests efficiently, crucial for real-time dashboards.
    - **Pydantic Validation**: Automatic request/response validation ensures data integrity.
    - **Swagger UI**: Auto-generated API documentation speeds up frontend integration.

### **PostgreSQL**
> **Why?** Relational Reliability for Serving Layer
- **Decision**: While raw data is in Kafka/Iceberg, the "Serving Layer" needs low-latency indexed queries for the dashboard.
- **Benefit**:
    - **Structured Data**: Perfect for storing aggregated metrics (Win Rate, Volume) and user profiles.
    - **JSONB Support**: Flexibility to store semi-structured report data before schema finalization.
