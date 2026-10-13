#!/usr/bin/env bash
# blue_green/down.sh —— 清理绿环境
#
# 用法: ./scripts/blue_green/down.sh [--keep-blue]
#
# 默认行为: 关绿容器 + 删绿容器 + 删绿网络 + 删镜像
# --keep-blue: 蓝环境不动（PR 合入后保留 7 天 standby）
#
# 触发:
#   - 验证失败后清理（取证已导出）
#   - PR 合入 + 7 天 standby 期到期

set -euo pipefail

KEEP_BLUE=0
for arg in "$@"; do
  case "${arg}" in
    --keep-blue) KEEP_BLUE=1 ;;
    *) echo "unknown arg: ${arg}" >&2; exit 64 ;;
  esac
done

echo "[down] cleaning green environment ..."
echo "[down] TODO: docker compose down + volume prune"

if [[ "${KEEP_BLUE}" -eq 1 ]]; then
  echo "[down] --keep-blue: blue environment untouched, 7d standby"
else
  echo "[down] blue will also be cleaned (manual confirmation recommended)"
fi

# 骨架阶段: 警告 + 退出
echo "[down] NOT YET IMPLEMENTED — manual docker compose down required" >&2
exit 78