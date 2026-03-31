#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}=== Laptop Node ===${NC}"
echo ""

# Docker check
if ! docker info > /dev/null 2>&1; then
  echo -e "${RED}Docker is not running!${NC}"
  exit 1
fi

export COMPOSE_PROJECT_NAME=jdp
COMPOSE_FILE="docker-compose.laptop.yml"

# Trade services
TRADE_SERVICES="kafka postgres ingest trade-movers trade-spark whale-monitor listing-monitor journal-bot api frontend cloudflared grafana"

# Mode selection
echo "Select mode:"
echo -e "  ${GREEN}1)${NC} Trade     — Trade 파이프라인 + 웹 서빙"
echo -e "  ${GREEN}2)${NC} Full      — Trade + Shop + Monitoring 전체"
echo -e "  ${GREEN}3)${NC} Dev       — Full + 실시간 로그"
echo ""
read -p "Enter [1-3, default=1]: " MODE
MODE=${MODE:-1}

case $MODE in
  1)
    echo ""
    echo -e "${CYAN}Starting Trade services...${NC}"
    docker compose -f $COMPOSE_FILE up -d --remove-orphans $TRADE_SERVICES
    ;;
  2)
    echo ""
    echo -e "${CYAN}Starting ALL services...${NC}"
    docker compose -f $COMPOSE_FILE up -d --remove-orphans
    ;;
  3)
    echo ""
    echo -e "${CYAN}Starting ALL services (dev mode)...${NC}"
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

# Postgres health
for i in $(seq 1 30); do
  STATUS=$(docker inspect --format='{{.State.Health.Status}}' jdp-postgres-1 2>/dev/null || echo "missing")
  if [ "$STATUS" = "healthy" ]; then
    echo -e "  Postgres: ${GREEN}OK${NC}"
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo -e "  Postgres: ${YELLOW}not ready (timeout)${NC}"
  fi
  sleep 1
done

# Kafka check
KAFKA_OK=false
for i in $(seq 1 20); do
  if docker exec jdp-kafka-1 kafka-broker-api-versions --bootstrap-server localhost:9092 > /dev/null 2>&1; then
    echo -e "  Kafka:    ${GREEN}OK${NC}"
    KAFKA_OK=true
    break
  fi
  sleep 1
done
if [ "$KAFKA_OK" = false ]; then
  echo -e "  Kafka:    ${YELLOW}not ready (timeout)${NC}"
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
echo -e "  ${BOLD}Trade${NC}"
echo "    Landing:      https://6-6ho.com (localhost:3000)"
echo "    Trade App:    https://trade.6-6ho.com"
echo "    Grafana:      http://localhost:3002"

if [ "$MODE" != "1" ]; then
  echo ""
  echo -e "  ${BOLD}Shop${NC}"
  echo "    Shop App:     https://shop.6-6ho.com (localhost:3001)"
  echo "    Shop Admin:   http://localhost:3003"
  echo "    Airflow:      https://airflow.6-6ho.com (localhost:8080)"
  echo "    MinIO:        http://localhost:9001"
  echo ""
  echo -e "  ${BOLD}Monitoring${NC}"
  echo "    Prometheus:   http://localhost:9090"
  echo "    cAdvisor:     http://localhost:8086"
fi

echo ""
echo -e "Stop: ${CYAN}./stop_laptop.sh${NC}"

# Dev mode: attach logs
if [ "$MODE" = "3" ]; then
  echo ""
  echo -e "${YELLOW}Attaching logs (Ctrl+C to detach)...${NC}"
  docker compose -f $COMPOSE_FILE logs -f
fi
