#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}=== Desktop Node ===${NC}"
echo ""

# Docker check
if ! docker info > /dev/null 2>&1; then
  echo -e "${RED}Docker is not running!${NC}"
  exit 1
fi

# LAPTOP_IP check
if [ -z "$LAPTOP_IP" ]; then
  echo -e "${YELLOW}LAPTOP_IP is not set.${NC}"
  read -p "Enter Laptop IP: " INPUT_IP
  if [ -z "$INPUT_IP" ]; then
    echo -e "${RED}LAPTOP_IP is required.${NC}"
    exit 1
  fi
  export LAPTOP_IP=$INPUT_IP
fi

echo -e "  Laptop Postgres: ${CYAN}${LAPTOP_IP}:5432${NC}"

# Load .env
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

export COMPOSE_PROJECT_NAME=jdp
export PGPASSWORD=${POSTGRES_PASSWORD:-postgres}
COMPOSE_FILE="docker-compose.desktop.yml"

# Postgres connectivity
echo ""
echo -e "${YELLOW}Testing Postgres connection...${NC}"
if docker run --rm -e PGPASSWORD=$PGPASSWORD postgres:16 psql -h $LAPTOP_IP -U postgres -d app -c "SELECT 1" > /dev/null 2>&1; then
  echo -e "  Postgres: ${GREEN}OK${NC}"
else
  echo -e "  Postgres: ${RED}FAIL${NC} (${LAPTOP_IP}:5432)"
  echo "  Check: 노트북 방화벽, WSL 포트 프록시, Postgres 실행 여부"
  read -p "  Continue anyway? [y/N]: " CONTINUE
  if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
    exit 1
  fi
fi

# Shop services
SHOP_SERVICES="kafka spark-master spark-worker-1 spark-worker-2 minio minio-init shop-api shop-analytics shop-analytics-job shop-generator shop-admin"

# Mode selection
echo ""
echo "Select mode:"
echo -e "  ${GREEN}1)${NC} Shop     — Spark 클러스터 + Shop 서비스"
echo -e "  ${GREEN}2)${NC} Full     — Shop + Airflow + Monitoring + ttyd"
echo ""
read -p "Enter [1-2, default=1]: " MODE
MODE=${MODE:-1}

case $MODE in
  1)
    echo ""
    echo -e "${CYAN}Starting Shop services...${NC}"
    docker compose -f $COMPOSE_FILE up -d --remove-orphans $SHOP_SERVICES
    ;;
  2)
    echo ""
    echo -e "${CYAN}Starting ALL services...${NC}"
    docker compose -f $COMPOSE_FILE up -d --remove-orphans
    ;;
  *)
    echo -e "${RED}Invalid choice.${NC}"
    exit 1
    ;;
esac

# Health checks
echo ""
echo -e "${YELLOW}Waiting for services...${NC}"

# Kafka check
KAFKA_OK=false
for i in $(seq 1 20); do
  if docker exec jdp-kafka kafka-broker-api-versions --bootstrap-server localhost:9092 > /dev/null 2>&1; then
    echo -e "  Kafka:        ${GREEN}OK${NC}"
    KAFKA_OK=true
    break
  fi
  sleep 1
done
if [ "$KAFKA_OK" = false ]; then
  echo -e "  Kafka:        ${YELLOW}not ready (timeout)${NC}"
fi

# Spark Master check
SPARK_OK=false
for i in $(seq 1 20); do
  if curl -s http://localhost:8081 > /dev/null 2>&1; then
    echo -e "  Spark Master: ${GREEN}OK${NC}"
    SPARK_OK=true
    break
  fi
  sleep 1
done
if [ "$SPARK_OK" = false ]; then
  echo -e "  Spark Master: ${YELLOW}not ready (timeout)${NC}"
fi

# Running services count
echo ""
RUNNING=$(docker compose -f $COMPOSE_FILE ps --format '{{.Name}}' --status running 2>/dev/null | wc -l)
TOTAL=$(docker compose -f $COMPOSE_FILE ps --format '{{.Name}}' 2>/dev/null | wc -l)
echo -e "${GREEN}${RUNNING}/${TOTAL} services running${NC}"

# Access points
echo ""
echo -e "${BOLD}=== Access Points ===${NC}"
echo ""
echo -e "  ${BOLD}Shop${NC}"
echo "    Shop App:     http://localhost:3001"
echo "    Shop Admin:   http://localhost:3003"
echo "    Spark Master: http://localhost:8081"

if [ "$MODE" = "2" ]; then
  echo ""
  echo -e "  ${BOLD}Infra${NC}"
  echo "    Airflow:      http://localhost:8080"
  echo "    MinIO:        http://localhost:9001"
  echo "    cAdvisor:     http://localhost:8086"
  echo "    Web Terminal: https://localhost:8443"
fi

echo ""
echo -e "  Postgres: ${CYAN}${LAPTOP_IP}:5432${NC}"
echo -e "  Stop: ${CYAN}./stop_desktop.sh${NC}"
