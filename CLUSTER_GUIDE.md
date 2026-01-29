# 분산 클러스터 실행 가이드

## 아키텍처 (Trade/Shop 분리)
```
┌─────────────────────────────────────┐      ┌─────────────────────────────────────┐
│  노트북 (192.168.219.101)            │      │  데스크탑 (192.168.219.108)          │
│  항상 켜짐 / Trade 담당               │      │  가끔 끔 / Shop 담당                 │
│  ───────────────────────────────    │      │  ───────────────────────────────    │
│  Frontend + Nginx + Tunnel          │◄────►│  Spark Master + Worker              │
│  Kafka (9092)                       │  LAN │  spark-shop-runner                  │
│  Postgres (5432)                    │      │  MinIO (Iceberg)                    │
│  trade-ingest (Binance)             │      │  shop-generator                     │
│  spark-trade-runner                 │      │                                     │
│  Grafana + Prometheus               │      │                                     │
└─────────────────────────────────────┘      └─────────────────────────────────────┘
```

## IP 정보
| 머신 | IP | Spark Job |
|------|-----|-----------|
| **노트북** | 192.168.219.101 | Trade (Movers, Alerts) |
| **데스크탑** | 192.168.219.108 | Shop (Sales, Brand, Funnel, KPI + Iceberg) |

---

## 사전 준비 (양쪽 모두)

### Windows 방화벽 설정
PowerShell (관리자 권한):
```powershell
netsh advfirewall firewall add rule name="Kafka" dir=in action=allow protocol=TCP localport=9092
netsh advfirewall firewall add rule name="Postgres" dir=in action=allow protocol=TCP localport=5432
netsh advfirewall firewall add rule name="Spark" dir=in action=allow protocol=TCP localport=7077
netsh advfirewall firewall add rule name="MinIO" dir=in action=allow protocol=TCP localport=9000
```

### WSL에서 Windows 포트 접근 허용
```powershell
# WSL에서 외부 접근 허용 (관리자 PowerShell)
netsh interface portproxy add v4tov4 listenport=9092 listenaddress=0.0.0.0 connectport=9092 connectaddress=172.x.x.x
# (172.x.x.x = WSL 내부 IP, `wsl hostname -I`로 확인)
```

---

## 실행 순서

### Step 1: 노트북에서 (Trade + 인프라)
```bash
cd ~/junho-data-platform

# 기존 컨테이너 정리
docker compose down

# 노트북 서비스 시작 (Trade 포함)
docker compose -f docker-compose.laptop.yml up -d
```

### Step 2: 데스크탑에서 (Shop + Iceberg)
```bash
cd ~/junho-data-platform

# 노트북 IP 설정
export LAPTOP_IP=192.168.219.101

# 데스크탑 서비스 시작
docker compose -f docker-compose.desktop.yml up -d
```

---

## 확인 방법

### 노트북에서
```bash
# Trade Spark Job 확인
docker logs spark-trade-runner --tail 20

# Kafka 토픽 확인
docker exec junho-data-platform-kafka-1 kafka-topics.sh --list --bootstrap-server localhost:9092
```

### 데스크탑에서
```bash
# Shop Spark Job 확인
docker logs spark-shop-runner --tail 20

# Iceberg 데이터 확인
docker run --network junho-data-platform_appnet --rm --entrypoint /bin/sh minio/mc -c \
  "mc alias set m http://minio:9000 minio minio123 && mc ls -r m/iceberg-warehouse/"
```

---

## 데스크탑 껐다 켜기

### 끌 때
```bash
docker compose -f docker-compose.desktop.yml down
```
→ 노트북 Trade는 계속 동작, Shop 데이터만 Kafka에 쌓임

### 켤 때
```bash
export LAPTOP_IP=192.168.219.101
docker compose -f docker-compose.desktop.yml up -d
```
→ Shop Spark가 Kafka 오프셋부터 자동 재개

---

## 트러블슈팅

### 데스크탑에서 노트북 연결 안 될 때
```bash
# 노트북 Kafka 연결 테스트
docker run --rm confluentinc/cp-kafka kafka-broker-api-versions --bootstrap-server 192.168.219.101:9092

# 노트북 Postgres 연결 테스트
docker run --rm postgres:16 psql -h 192.168.219.101 -U postgres -d app -c "SELECT 1"
```

### WSL 포트 확인
```powershell
# Windows에서 WSL 포트 열렸는지 확인
netstat -an | findstr 9092
```
