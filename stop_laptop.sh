#!/bin/bash

echo "💻 Stopping Laptop Node..."
echo "--------------------------------"

docker compose -f docker-compose.laptop.yml down --remove-orphans

echo "--------------------------------"
echo "✅ Laptop services stopped."
echo "💤 데스크탑은 독립적으로 계속 동작합니다."
