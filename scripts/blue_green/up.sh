#!/usr/bin/env bash
# blue_green/up.sh —— 起绿环境
#
# 用法: ./scripts/blue_green/up.sh <pr-num> <commit-sha>
#
# 状态: v0.1 骨架。需补：
#   - VPS 上的镜像仓库地址（GHCR?）
#   - 写隔离 dry_run 配置注入方式（环境变量? ConfigMap?）
#   - 健康检查端点
#
# 设计: 与 docs/agent-framework/v0.1.md §四 对齐

set -euo pipefail

PR_NUM="${1:-}"
COMMIT_SHA="${2:-}"
if [[ -z "$PR_NUM" || -z "$COMMIT_SHA" ]]; then
  echo "usage: $0 <pr-num> <commit-sha>" >&2
  exit 64
fi

IMAGE_TAG="dailycheck:pr-${PR_NUM}-${COMMIT_SHA:0:7}"
GREEN_PORT=8091
CONTAINER_NAME="dailycheck-green-pr-${PR_NUM}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.preview.yml}"

# TODO: 拉取镜像（GHCR auth 需配）
echo "[up] pulling ${IMAGE_TAG} ..."
# docker pull "${IMAGE_TAG}"

# TODO: 起容器，注入 dry_run=True 环境变量
echo "[up] starting ${CONTAINER_NAME} on :${GREEN_PORT} ..."
# docker compose -f "${COMPOSE_FILE}" up -d \
#   -e DRY_RUN=true \
#   -e DB_WRITE_PREFIX=green_ \
#   --scale app=1

# 健康检查
echo "[up] health check ..."
for i in {1..30}; do
  # if curl -fsS "http://localhost:${GREEN_PORT}/health" >/dev/null; then
  #   echo "[up] green healthy"
  #   exit 0
  # fi
  sleep 2
done

echo "[up] health check timeout" >&2
exit 1