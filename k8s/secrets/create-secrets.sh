#!/bin/bash
# K8s Secrets 생성 스크립트
# 사용법: bash k8s/secrets/create-secrets.sh
#
# 실행 전 환경변수 설정 필요:
#   export POSTGRES_PASSWORD=<password>
#   export TELEGRAM_BOT_TOKEN=<token>
#   export TELEGRAM_CHAT_ID=<chat_id>
#   export AIRFLOW_FERNET_KEY=<fernet_key>
#   export AIRFLOW_SECRET_KEY=<secret_key>
#   export AIRFLOW_PASSWORD=<password>
#   export MINIO_ROOT_USER=<user>
#   export MINIO_ROOT_PASSWORD=<password>
#   export OPENAI_API_KEY=<key>
#   export CODE_SERVER_PASSWORD=<password>
#   export CLOUDFLARE_TUNNEL_TOKEN=<token>
#
# 또는: source .env && bash k8s/secrets/create-secrets.sh

set -euo pipefail

: "${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD}"
: "${TELEGRAM_BOT_TOKEN:?Set TELEGRAM_BOT_TOKEN}"
: "${TELEGRAM_CHAT_ID:?Set TELEGRAM_CHAT_ID}"
: "${AIRFLOW_FERNET_KEY:?Set AIRFLOW_FERNET_KEY}"
: "${MINIO_ROOT_USER:=minio}"
: "${MINIO_ROOT_PASSWORD:=minio123}"

echo "=== Creating K8s Secrets ==="

# DB Secret — trade, shop, data, database, airflow, monitoring 에 모두 필요
for NS in trade shop data database airflow monitoring infra; do
  kubectl create secret generic db-secret \
    --from-literal=POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
    -n "$NS" --dry-run=client -o yaml | kubectl apply -f -
done

# Telegram Secret — trade, airflow
for NS in trade airflow default; do
  kubectl create secret generic telegram-secret \
    --from-literal=TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN}" \
    --from-literal=TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID}" \
    -n "$NS" --dry-run=client -o yaml | kubectl apply -f -
done

# MinIO Secret — data, shop, airflow
for NS in data shop airflow; do
  kubectl create secret generic minio-secret \
    --from-literal=MINIO_ROOT_USER="${MINIO_ROOT_USER}" \
    --from-literal=MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD}" \
    --from-literal=MINIO_ACCESS_KEY="${MINIO_ROOT_USER}" \
    --from-literal=MINIO_SECRET_KEY="${MINIO_ROOT_PASSWORD}" \
    -n "$NS" --dry-run=client -o yaml | kubectl apply -f -
done

# Airflow Secret
kubectl create secret generic airflow-secret \
  --from-literal=AIRFLOW_FERNET_KEY="${AIRFLOW_FERNET_KEY}" \
  --from-literal=AIRFLOW_SECRET_KEY="${AIRFLOW_SECRET_KEY:-jdp-secret}" \
  --from-literal=AIRFLOW_PASSWORD="${AIRFLOW_PASSWORD:-admin}" \
  -n airflow --dry-run=client -o yaml | kubectl apply -f -

# OpenAI Secret — shop
kubectl create secret generic openai-secret \
  --from-literal=OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
  -n shop --dry-run=client -o yaml | kubectl apply -f -

# ttyd Secret — infra
kubectl create secret generic ttyd-secret \
  --from-literal=CODE_SERVER_PASSWORD="${CODE_SERVER_PASSWORD:-changeme}" \
  -n infra --dry-run=client -o yaml | kubectl apply -f -

# Cloudflare Tunnel credentials
if [ -f "infra/tunnel/credentials.json" ]; then
  kubectl create secret generic cloudflared-creds \
    --from-file=credentials.json=infra/tunnel/credentials.json \
    -n default --dry-run=client -o yaml | kubectl apply -f -
  echo "  cloudflared-creds created from infra/tunnel/credentials.json"
else
  echo "  WARN: infra/tunnel/credentials.json not found — create cloudflared-creds manually"
fi

echo "=== All Secrets Created ==="
