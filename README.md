# 轻量库存管理软件

功能：
- 后台品类管理
- 库存品管理
- 入库
- 库存盘点（自动记录差异）
- 库存查阅（支持搜索 + 低库存提示）
- 补货申请（含状态流转）

## 启动

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

访问：`http://127.0.0.1:5001`

数据库：`inventory.db`（首次启动自动创建）
