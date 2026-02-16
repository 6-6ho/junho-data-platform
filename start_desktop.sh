#!/bin/bash

echo "🖥️  Starting Desktop Node (Data Processing)..."
echo "--------------------------------"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "❌ Docker is not running!"
  exit 1
fi

# Check LAPTOP_IP
if [ -z "$LAPTOP_IP" ]; then
  echo "⚠️  LAPTOP_IP is not set. Using default: 192.168.219.101"
  export LAPTOP_IP=192.168.219.101
fi

echo "📡 Laptop Postgres: ${LAPTOP_IP}:5432"

# Test Postgres connectivity
echo "🔍 Testing Postgres connection..."
if docker run --rm postgres:16 psql -h $LAPTOP_IP -U postgres -d app -c "SELECT 1" > /dev/null 2>&1; then
  echo "✅ Postgres connection OK"
else
  echo "⚠️  Cannot reach Postgres at ${LAPTOP_IP}:5432"
  echo "   Check: 노트북 방화벽, WSL 포트 프록시, Postgres 실행 여부"
  read -p "Continue anyway? [y/N]: " CONTINUE
  if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
    exit 1
  fi
fi

echo ""
echo "Select Mode:"
echo "1) Shop Only (Kafka + Spark + Shop services)"
echo "2) All (Shop + Airflow + Monitoring)"
read -p "Enter choice [1-2]: " CHOICE

case $CHOICE in
    1)
        echo "🛍️  Starting Shop Processing..."
        docker compose -f docker-compose.desktop.yml up -d kafka spark-master spark-worker-1 spark-worker-2 minio minio-init shop-api shop-analytics shop-analytics-job shop-generator
        ;;
    2)
        echo "🔥 Starting ALL Desktop Services..."
        docker compose -f docker-compose.desktop.yml up -d
        ;;
    *)
        echo "❌ Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "⏳ Waiting for services to initialize..."
sleep 5

echo "--------------------------------"
echo "✅ Desktop Node Started!"
echo ""
echo "🔗 Access Points:"
echo "   - ⚡ Spark Master:   http://localhost:8081"
echo "   - 💨 Airflow:        http://localhost:8080 (admin/admin)"
echo "   - 🗄️  MinIO Console:  http://localhost:9001 (minio/minio123)"
echo "   - 🛍️  Shop App:       http://localhost:3001"
echo ""
echo "📡 Connected to Laptop Postgres: ${LAPTOP_IP}:5432"
echo "💡 Stop: ./stop_desktop.sh"
