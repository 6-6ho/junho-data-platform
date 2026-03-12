#!/bin/bash
# K8s 초기 설정 스크립트
# kubeadm 클러스터 구축 후, 서비스 배포 전에 실행
#
# 사용법: bash k8s/setup.sh
# 사전조건: kubectl 접근 가능, .env 파일 존재

set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Phase 0: K8s Initial Setup ==="

# 1. Namespaces
echo "[1/6] Creating namespaces..."
kubectl apply -f k8s/base/namespace.yaml

# 2. Registry
echo "[2/6] Deploying local registry..."
kubectl apply -f k8s/base/registry.yaml
echo "  Waiting for registry pod..."
kubectl wait --for=condition=ready pod -l app=registry -n default --timeout=60s

# 3. Secrets
echo "[3/6] Creating secrets..."
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi
bash k8s/secrets/create-secrets.sh

# 4. Generate Postgres init-scripts ConfigMap
echo "[4/6] Generating postgres-init-scripts ConfigMap..."
kubectl create configmap postgres-init-scripts \
  --from-file=infra/postgres-init/ \
  -n database --dry-run=client -o yaml | kubectl apply -f -

# 5. Generate Grafana dashboards ConfigMap
echo "[5/6] Generating grafana-dashboards ConfigMap..."
kubectl create configmap grafana-dashboards \
  --from-file=infra/grafana/provisioning/dashboards/json/ \
  -n monitoring --dry-run=client -o yaml | kubectl apply -f -

# 6. Apply common ConfigMaps
echo "[6/6] Applying common ConfigMaps..."
kubectl apply -f k8s/configmaps/

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Build and push images:  bash k8s/build-images.sh"
echo "  2. Deploy Phase 1:         kubectl apply -f k8s/trade/ -f k8s/shop/ -f k8s/infra/"
echo "  3. Deploy Phase 2:         kubectl apply -f k8s/database/ -f k8s/data/ -f k8s/monitoring/"
echo "  4. Deploy Phase 3:         (analytics-streaming already in k8s/shop/)"
echo "  5. Deploy Phase 4:         kubectl apply -f k8s/airflow/"
