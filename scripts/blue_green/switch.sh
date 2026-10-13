#!/usr/bin/env bash
# blue_green/switch.sh —— 切流量
#
# 用法: ./scripts/blue_green/switch.sh <green|blue> [percent]
#
# 状态: v0.1 占位。需补：
#   - VPS 上 Nginx upstream 配置路径
#   - Nginx reload 信号（避免重启）
#   - 灰度 5% → 50% → 100% 的多次切换

set -euo pipefail

TARGET="${1:-}"
PERCENT="${2:-100}"

case "${TARGET}" in
  green|blue) ;;
  *) echo "usage: $0 <green|blue> [percent]" >&2; exit 64 ;;
esac

echo "[switch] target=${TARGET} percent=${PERCENT}"
echo "[switch] TODO: integrate with VPS nginx upstream"
echo "[switch] TODO: graceful reload, no dropped connections"

# 骨架阶段: 警告 + 退出
echo "[switch] NOT YET IMPLEMENTED — refusing to switch traffic" >&2
exit 78