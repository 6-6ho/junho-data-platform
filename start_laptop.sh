#!/bin/bash

echo "💻 Starting Laptop Node (Trade Pipeline + Web)..."
echo "--------------------------------"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "❌ Docker is not running!"
  exit 1
fi

docker compose -f docker-compose.laptop.yml up -d

echo ""
echo "⏳ Waiting for services to initialize..."
sleep 5

echo "--------------------------------"
echo "✅ Laptop Node Started!"
echo ""
echo "🔗 Access Points:"
echo "   - 🏠 Landing Page:   https://6-6ho.com (or http://localhost:3000)"
echo "   - 📈 Trade App:      https://trade.6-6ho.com"
echo "   - 📊 Grafana:        http://localhost:3002 (admin/admin)"
echo ""
echo "📌 Running: kafka → ingest → trade-movers → postgres → api → frontend"
echo "   ↳ Trade 파이프라인이 독립적으로 동작합니다 (데스크탑 불필요)"
echo ""
echo "💡 Stop: ./stop_laptop.sh"
