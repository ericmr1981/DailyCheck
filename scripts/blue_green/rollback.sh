#!/usr/bin/env bash
# blue_green/rollback.sh —— 秒级切回蓝
#
# 用法: ./scripts/blue_green/rollback.sh
#
# 触发: 绿环境出现异常（错误率上升、P95 超阈、健康检查失败）
# 行为: Nginx upstream 切回蓝，绿环境保留为取证状态（待人工调查）
# 设计: docs/agent-framework/v0.1.md §四.2 第 5 项（回滚演练）

set -euo pipefail

echo "[rollback] switching upstream back to blue ..."
echo "[rollback] TODO: implement Nginx upstream switch"
echo "[rollback] TODO: capture green env state for forensics"
echo "[rollback] TODO: alert Eric via notification"

# 骨架阶段: 警告 + 退出
echo "[rollback] NOT YET IMPLEMENTED — manual intervention required" >&2
exit 78