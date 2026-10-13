#!/usr/bin/env bash
# blue_green/verify.sh —— 跑生产验证
#
# 用法: ./scripts/blue_green/verify.sh <pr-num>
#
# 输出: docs/agent-framework/templates/05-production-verification.md 填好的版本
# 退出码: 0=全绿可切流量；非0=打回 PR

set -euo pipefail

PR_NUM="${1:-}"
if [[ -z "$PR_NUM" ]]; then
  echo "usage: $0 <pr-num>" >&2
  exit 64
fi

REPORT_PATH="backups/prod-verifications/$(date +%Y-%m-%d)-pr-${PR_NUM}.md"

mkdir -p "$(dirname "${REPORT_PATH}")"

echo "[verify] running production verification for PR #${PR_NUM} ..."
echo "[verify] report: ${REPORT_PATH}"

# TODO: 跑五项检查
#   1. 集成测试 (pytest tests/contract tests/integration)
#   2. 模拟用户操作 (Playwright 跑蓝绿双跑)
#   3. 绿 vs 蓝比对 (响应/截图/P95/CPU/内存)
#   4. 回滚演练
#   5. 资源与依赖
#
# 全部绿 → exit 0 + 写出报告 + 标记"通过"
# 任一红 → exit 非0 + 留绿环境取证 + 打回 PR

# 骨架阶段：占位实现
cat > "${REPORT_PATH}" <<EOF
# 生产验证报告 — PR #${PR_NUM}

> ⚠️ **骨架阶段**：v0.1 验证脚本尚未实现，本报告由 verify.sh 占位生成。
> 详见: docs/agent-framework/templates/05-production-verification.md

| 检查项 | 状态 | 备注 |
|--------|------|------|
| 集成测试 | ⚠️ TODO | |
| 模拟用户操作 | ⚠️ TODO | |
| 绿 vs 蓝比对 | ⚠️ TODO | |
| 回滚演练 | ⚠️ TODO | |
| 资源与依赖 | ⚠️ TODO | |

## 决策
- [ ] **占位** — 脚本实现后回填
EOF

echo "[verify] placeholder report written. real checks not yet implemented."
exit 0