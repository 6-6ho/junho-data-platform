#!/bin/bash
set -e

# Load environment variables
source .env

# Configuration
DESKTOP_HOST=${DESKTOP_HOST:?Set DESKTOP_HOST in .env or export it}
DESKTOP_USER=${DESKTOP_USER:-junhod}           # Default or from env
PROJECT_DIR=${PROJECT_DIR:-~/junho-data-platform}

echo "🚀 Starting Deployment to Desktop ($DESKTOP_HOST)..."

# 1. Deploy to Desktop via SSH
ssh -o StrictHostKeyChecking=no ${DESKTOP_USER}@${DESKTOP_HOST} << EOF
    cd ${PROJECT_DIR}
    echo "⬇️ Pulling latest code..."
    git pull origin main
    
    echo "🔄 Restarting Desktop Services..."
    export LAPTOP_IP=${LAPTOP_IP}
    docker compose -f docker-compose.desktop.yml up -d --remove-orphans
EOF

# 2. Healthcheck (Shop API & Airflow)
echo "🏥 Checking Service Health..."
MAX_RETRIES=30
check_service() {
    local url=$1
    local name=$2
    for i in $(seq 1 $MAX_RETRIES); do
        if curl -s -f "$url" > /dev/null; then
            echo "✅ $name is UP!"
            return 0
        fi
        echo "⏳ Waiting for $name... ($i/$MAX_RETRIES)"
        sleep 2
    done
    echo "❌ $name failed to start."
    return 1
}

# Check remote health via curl from Laptop (assuming mapped ports are accessible)
# Note: Use DESKTOP_HOST IP
if check_service "http://${DESKTOP_HOST}:3001" "Shop Analytics" && \
   check_service "http://${DESKTOP_HOST}:8080/health" "Airflow"; then
    STATUS="✅ Deployment Success!"
else
    STATUS="❌ Deployment Failed!"
fi

# 3. Notify via Telegram
if [ ! -z "$TELEGRAM_BOT_TOKEN" ] && [ ! -z "$TELEGRAM_CHAT_ID" ]; then
    echo "📩 Sending Notification..."
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d chat_id="${TELEGRAM_CHAT_ID}" \
        -d text="[Desktop Deploy] ${STATUS}
        Target: ${DESKTOP_HOST}
        Time: $(date)" > /dev/null
fi

echo "$STATUS"
