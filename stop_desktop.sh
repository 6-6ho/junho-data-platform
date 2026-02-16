#!/bin/bash

echo "🖥️  Stopping Desktop Node..."
echo "--------------------------------"

docker compose -f docker-compose.desktop.yml down --remove-orphans

echo "--------------------------------"
echo "✅ Desktop services stopped."
echo "💡 노트북 웹 서빙은 독립적으로 계속 동작합니다."
echo "   기존 데이터는 노트북에서 계속 조회 가능합니다."
