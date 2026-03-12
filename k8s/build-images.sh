#!/bin/bash
# 커스텀 이미지 빌드 + 레지스트리 push
#
# 사용법: bash k8s/build-images.sh [이미지명]
# 예시:
#   bash k8s/build-images.sh              # 전체 빌드
#   bash k8s/build-images.sh spark        # spark만 빌드
#   bash k8s/build-images.sh trade-frontend shop-backend  # 특정 이미지만

set -euo pipefail
cd "$(dirname "$0")/.."

REGISTRY="registry.local:5000/jdp"

declare -A IMAGES=(
  ["spark"]="spark"
  ["trade-ingest"]="apps/trade-ingest"
  ["trade-backend"]="apps/trade-backend"
  ["trade-frontend"]="apps/trade-frontend"
  ["shop-backend"]="apps/shop-backend"
  ["shop-analytics"]="apps/shop-analytics"
  ["shop-admin"]="apps/shop-admin"
  ["shop-generator"]="apps/shop-generator"
  ["airflow"]="airflow"
  ["infra-monitor"]="apps/infra-monitor"
  ["ttyd"]="infra/ttyd"
)

# 빌드 대상 결정
if [ $# -gt 0 ]; then
  TARGETS=("$@")
else
  TARGETS=("${!IMAGES[@]}")
fi

echo "=== Building Images ==="
for name in "${TARGETS[@]}"; do
  context="${IMAGES[$name]:-}"
  if [ -z "$context" ]; then
    echo "ERROR: Unknown image '${name}'"
    echo "Available: ${!IMAGES[*]}"
    exit 1
  fi

  echo ""
  echo "--- Building ${name} from ./${context} ---"
  docker build -t "${REGISTRY}/${name}:latest" "./${context}"
  docker push "${REGISTRY}/${name}:latest"
  echo "  Pushed ${REGISTRY}/${name}:latest"
done

echo ""
echo "=== All images built and pushed ==="
