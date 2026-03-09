# Service & Port Map

Junho Data Platform의 서비스 구성과 접속 정보를 정리한 문서입니다.

## 🌐 Public/Local Endpoints

| Service | Hostname (Dev) | URL (Localhost) | Port | Description |
|---------|----------------|-----------------|------|-------------|
| **Landing Page** | `6-6ho.com` | `http://localhost:3000` | `3000` | 메인 포트폴리오 랜딩 페이지 |
| **Trade App** | `trade.6-6ho.com` | `http://localhost:3000` | `3000` | 코인 트레이딩 대시보드 (Virtual Host) |
| **Shop App** | `shop.6-6ho.com` | `http://localhost:3000` | `3000` | 쇼핑몰 분석 대시보드 (Virtual Host) |
| **Shop App (Direct)** | - | `http://localhost:3001` | `3001` | 쇼핑몰 분석 대시보드 (Direct Access) |
| **Grafana** | `monitor.6-6ho.com`| `http://localhost:3002` | `3002` | 시스템 모니터링 및 시각화 |
| **Airflow** | - | `http://localhost:8080` | `8080` | 배치 워크플로우 관리 |
| **Spark Master** | - | `http://localhost:8081` | `8081` | Spark 클러스터 상태 확인 |

> **Note**: `3000`번 포트는 Nginx(Frontend)가 점유하며, `Hosl` 헤더에 따라 내부 라우팅을 수행합니다.

## 📦 Container Internal Ports

| Container Metric | Internal Port | Service Name | Volumn Mount |
|------------------|---------------|--------------|--------------|
| **Backend API** | `8000` | `api` | - |
| **Shop Frontend**| `80` | `shop-analytics` | - |
| **Kafka** | `9092` | `kafka` | - |
| **MinIO Console**| `9001` | `minio` | `miniodata` |
| **MinIO API** | `9000` | `minio` | `miniodata` |
| **Postgres** | `5432` | `postgres` | `pgdata` |

## 🔑 Credentials

기본 크레덴셜은 `.env.example` 파일을 참조하세요. `.env`에 실제 값을 설정합니다.

## 🛠️ Typical Troubleshooting

### 1. Connection Refused (Shop API)
- **증상**: Shop Web App에서 차트 데이터가 로딩되지 않음 (502/404).
- **원인**: Nginx 프록시 설정이 `api` 컨테이너를 찾지 못함.
- **해결**: `shop-analytics` 컨테이너의 `nginx.conf` 확인 및 Rebuild.

### 2. Spark Job Fail (OOM)
- **증상**: 스트리밍 잡이 `137` 코드로 종료됨.
- **해결**: `docker-compose.desktop.yml`에서 Spark 워커 메모리 제한 상향.

### 3. Grafana No Data
- **증상**: 대시보드 패널에 데이터가 없음.
- **해결**: Datasource 설정(`datasource.yml`)에서 `database: app` 필드 누락 여부 확인 또는 Timezone 설정 확인.
