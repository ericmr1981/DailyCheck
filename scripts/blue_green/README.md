# Blue-Green Deployment Scripts

> **状态**：v0.2 骨架（2026-10-13 修订）。脚本基于 VPS 真实架构重写——systemd 复用 + DRY_RUN 中间件（决策 1+3），删除 Mac mini Docker 假设（决策 2）。
>
> **v0.1 → v0.2 修订依据**：[Prod Agent 反馈](https://scnzlitcwg39.feishu.cn/drive/folder/SnItfxKQcl8h2cdQtllcVmRynsd)（wdg_vps 实测）。

## 设计目标

按 [`docs/agent-framework/v0.1.md`](../../docs/agent-framework/v0.1.md) §四，Prod Agent 拉 PR 后起绿环境跑验证，通过后切流量。蓝环境保留为 7 天 standby。

## VPS 真实架构（2026-10-13 实测）

| 项 | 蓝（生产） | 绿（候选） |
|----|----------|----------|
| 服务 | `dailycheck.service`（gunicorn :8090, 3 workers） | `dailycheck-green.service`（待建） |
| MCP | `dailycheck-mcp.service` | `dailycheck-green-mcp.service`（待建） |
| DB | `/var/lib/dailycheck/`（master.db + warehouses/*.db） | `/var/lib/dailycheck-green/`（待建） |
| 端口 | gunicorn 127.0.0.1:8090 + nginx :8080 反代 | gunicorn 127.0.0.1:8091 + nginx upstream weight |
| 写隔离 | 正常写 | DRY_RUN=true（中间件 log-only） |
| 工作目录 | `/opt/dailycheck`（待 Eric 确认） | 同 |
| 进程管理 | systemd | systemd |

## 当前文件

| 文件 | 用途 | 状态 |
|------|------|------|
| `up.sh` | 起绿环境（cp DB + systemctl start dailycheck-green.service + 健康检查） | 骨架 + systemd TODO |
| `verify.sh` | 跑五项生产验证 | 骨架（占位报告，exit 0 警告） |
| `switch.sh` | 切流量（nginx upstream weight + reload） | 骨架 + systemd TODO |
| `rollback.sh` | 秒级切回蓝（weight=0 + 不停绿进程） | 骨架 + systemd TODO |
| `down.sh` | 清理绿（systemctl stop + 可选 rm DB） | 骨架 + systemd TODO |

## 端口/路由约定

| 路径 | 端口 | 角色 |
|------|------|------|
| 蓝（线上） | 127.0.0.1:8090 | 当前生产（gunicorn 3 workers） |
| 绿（候选） | 127.0.0.1:8091 | 待验证（gunicorn 2 workers） |
| Nginx | 0.0.0.0:8080 | 反代入口，`/etc/nginx/sites-enabled/dailycheck` |
| Nginx upstream | :8090 + :8091 | 灰度切换点（weight 调整） |

## 写隔离（决策 1：方案 B）

绿环境通过 `DRY_RUN=true` 环境变量启动。`app.py` + `blueprints/*` 写路径走中间件：

```python
if current_app.config.get("DRY_RUN"):
    log.info(f"[dry_run] skip write: {sql}")
    return []  # 或 raise DryRunError
```

中间件需要：
1. `DRY_RUN` 配置读取（`config.py` + 环境变量）
2. blueprints（items / inventory / outbound / production / restock / stocktake）所有 ORM 写路径接入
3. PoC：加 1 个 blueprint 验证后跑全量 pytest（必须仍 16 failed / 718+ passed，零新增）

中间件完成后用 [`prod_dryrun_evidence.sh`](../agent_framework/prod_dryrun_evidence.sh) 验证端到端隔离。

## 待补（v0.2 阶段）

- [ ] `dailycheck-green.service` systemd unit（模板见 up.sh TODO）
- [ ] `dailycheck-green-mcp.service` systemd unit
- [ ] `/var/lib/dailycheck-green/` 目录（cp 自蓝）
- [ ] `app.py` DRY_RUN 中间件 + blueprints 接入（方案 B PoC，1-2d）
- [ ] Nginx `/etc/nginx/sites-enabled/dailycheck` 加 :8091 upstream block
- [ ] `verify.sh` 五项实装（集成 + 模拟用户 + 绿蓝比对 + 回滚演练 + 资源基线）
- [ ] `scripts/agent_framework/prod_dryrun_evidence.sh` 实装（取消 exit 78）
- [ ] 蓝环境 standby 7 天自动清理 cron
- [ ] `vps_self_heal.py` 监控清单补 `dailycheck-green.service`（Phase 2）

## 使用流程

```bash
# 1. 起绿环境
./scripts/blue_green/up.sh pr-123 abc1234

# 2. 跑五项生产验证（出 templates/05 报告）
./scripts/blue_green/verify.sh pr-123

# 3. dry_run 隔离证据采集
./scripts/agent_framework/prod_dryrun_evidence.sh

# 4. 通过后切流量（5% → 50% → 100%）
./scripts/blue_green/switch.sh green 5
./scripts/blue_green/switch.sh green 50
./scripts/blue_green/switch.sh green 100

# 5. 观察窗 30 分钟无异常 → 合 PR
# 6. 蓝环境 standby 7 天后清理
./scripts/blue_green/down.sh --keep-blue
```

## 与现有 deploy_vps.sh 的关系

- `deploy_vps.sh`：手工部署 + 回滚（kill 蓝 gunicorn → 重启），**不是蓝绿**。保留作为应急 / 旧路径。
- `blue_green/*`：自治路径，Prod Agent 主用。**保留蓝 gunicorn 不 kill**（0 中断），起绿 on :8091 → 验证 → 切流量 100% → 蓝降 standby → 绿升为新蓝。
- **过渡期两条路并存**：日常 prod 仍走 deploy 流程；引入新代码（蓝绿目标场景）走 blue_green。
- 后续 v0.3 目标：`deploy_vps.sh` 改造成"起绿"语义（与 `up.sh` 复用同一份 systemd 启动逻辑），不再 kill 蓝。

## 与 vps_self_heal 的关系

- `vps_self_heal.py` 监控蓝 `:8090` 的 dailycheck.service，**不监控绿 `:8091`**。
- Phase 2 加 `dailycheck-green.service` 时要确认是否补进 vps_self_heal 检查清单——避免绿挂了没人发现但生产还在走蓝。
- v0.2 阶段无需改 vps_self_heal（绿还没起），但 up.sh 起来后应当给 Eric 发通知（待接入）。