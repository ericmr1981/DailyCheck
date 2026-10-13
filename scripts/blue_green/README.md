# Blue-Green Deployment Scripts

> **状态**：v0.1 骨架（2026-10-13）。脚本框架就位但具体实现需根据 wdg_vps 实际情况补完。

## 设计目标

按 [`docs/agent-framework/v0.1.md`](../../docs/agent-framework/v0.1.md) §四，Prod Agent 拉 PR 后起绿环境跑验证，通过后切流量。蓝环境保留为 7 天 standby。

## 当前文件

| 文件 | 用途 | 状态 |
|------|------|------|
| `up.sh` | 起绿环境（拉镜像 + 起容器 + 写隔离配置 + 健康检查） | 骨架 |
| `verify.sh` | 跑生产验证（套用 templates/05） | 骨架 |
| `switch.sh` | 切流量（Nginx upstream 切换） | 骨架（占位） |
| `rollback.sh` | 秒级切回蓝 | 骨架（占位） |
| `down.sh` | 清理绿环境（验证失败或 PR 合入后） | 骨架 |

## 端口/路由约定

| 环境 | 端口 | 角色 |
|------|------|------|
| 蓝（线上） | :8090 | 当前生产 |
| 绿（候选） | :8091 | 待验证 |
| Nginx upstream | :80 | 灰度切换点 |

## 写隔离

绿环境所有写操作走 `dry_run=True`（详见 `app.py` 配置或 `mcp_server/main.py`）。
SQLite 通过 schema 前缀 `green_` 或 sqlite-mode transaction-rollback 实现（待选）。

## 待补

- [ ] VPS 上 Nginx upstream 配置模板
- [ ] docker-compose.preview.yml（与 prod 同构）
- [ ] 写隔离的具体实现（dry_run / schema 前缀）
- [ ] 健康检查端点（`/health` 是否已存在？）
- [ ] 蓝环境 standby 7 天自动清理

## 使用流程

```bash
# 1. 起绿环境
./scripts/blue_green/up.sh pr-123 abc1234

# 2. 跑验证（Prod Agent 出 templates/05 报告）
./scripts/blue_green/verify.sh pr-123

# 3. 通过后切流量
./scripts/blue_green/switch.sh green

# 4. 观察窗（30 分钟）后合 PR，蓝环境 standby
# 7 天后清理
./scripts/blue_green/down.sh --keep-blue
```

## 与现有 deploy_vps.sh 的关系

- `deploy_vps.sh`：手工部署 + 回滚（**不是蓝绿**），保留作为应急
- `blue_green/*`：自治路径，Prod Agent 主用
- 两者并存，紧急时 `deploy_vps.sh --rollback` 仍可用