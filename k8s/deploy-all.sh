#!/bin/bash
# 전체 K8s 매니페스트 적용 (Phase 0 setup 완료 후)
#
# 사용법: bash k8s/deploy-all.sh

set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Deploying All K8s Resources ==="

# Dynamic ConfigMaps (from file)
echo "[1/8] Generating dynamic ConfigMaps..."
kubectl create configmap postgres-init-scripts \
  --from-file=infra/postgres-init/ \
  -n database --dry-run=client -o yaml | kubectl apply -f -
kubectl create configmap grafana-dashboards \
  --from-file=infra/grafana/provisioning/dashboards/json/ \
  -n monitoring --dry-run=client -o yaml | kubectl apply -f -

echo "[2/8] Applying ConfigMaps..."
kubectl apply -f k8s/configmaps/

echo "[3/8] Deploying database..."
kubectl apply -f k8s/database/

echo "[4/8] Deploying data layer (Kafka, MinIO, Spark RBAC)..."
kubectl apply -f k8s/data/

echo "[5/8] Deploying trade services..."
kubectl apply -f k8s/trade/

echo "[6/8] Deploying shop services..."
kubectl apply -f k8s/shop/

echo "[7/8] Deploying monitoring..."
kubectl apply -f k8s/monitoring/

echo "[8/8] Deploying infra + airflow..."
kubectl apply -f k8s/infra/
kubectl apply -f k8s/airflow/

echo ""
echo "=== Waiting for key rollouts ==="
kubectl rollout status statefulset/postgres -n database --timeout=120s 2>/dev/null || echo "  postgres: pending"
kubectl rollout status statefulset/kafka -n data --timeout=120s 2>/dev/null || echo "  kafka: pending"
kubectl rollout status deployment/trade-frontend -n trade --timeout=60s 2>/dev/null || echo "  trade-frontend: pending"
kubectl rollout status deployment/trade-backend -n trade --timeout=60s 2>/dev/null || echo "  trade-backend: pending"

echo ""
echo "=== Deployment Complete ==="
echo "Run 'kubectl get pods -A' to check status"
