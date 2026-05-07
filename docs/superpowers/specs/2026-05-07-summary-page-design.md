# 汇总页面设计文档

## 概述
在 DailyCheck 库存管理系统中新增汇总页面 `/summary`，从整体维度展示项目的进货总量、剩余库存、消耗状态和价值。

## 数据模型变更

### items 表新增字段
| 列名 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `unit_cost` | REAL | 0 | 进货单价（成本价），单位 ¥ |

### 已有品项处理
- 已有品项 `unit_cost` 默认为 0
- 品项编辑页面支持随时修改单价
- 价值均按**当前单价**计算（暂不追踪历史变价）

## 新增/修改页面

### 品项创建页（items.html）— 新增单价输入
- 表单新增 "进货单价（¥）" 输入框，类型 number，步长 0.01
- 选填字段，默认为 0

### 品项编辑页（edit_item.html）— 新增单价输入
- 表单新增 "进货单价（¥）" 输入框，预填当前值
- 修改后提交更新数据库

### 新页面：汇总页（summary.html）

**顶部：5 大核心指标卡片**

| 指标 | 计算方式 | 示例 |
|------|---------|------|
| 总进货量 | `SUM(items.quantity - 初始值 + 出库)` 或 `SUM(stock_movements.delta WHERE action='补货入库')` | 1,280 件 |
| 当前库存 | `SUM(items.quantity)` | 520 件 |
| 消耗率 | (总进货量 - 当前库存) ÷ 总进货量 × 100% | 59.4% |
| 进货总金额 | `∑(items.unit_cost × 该品项总入库量)` | ¥18,200 |
| 库存总价值 | `∑(items.unit_cost × items.quantity)` | ¥15,600 |

- 桌面端：一行 5 列
- 移动端：2+2+1 布局（前 2 行各 2 个，最后 1 个通栏宽）

**中部：按品类统计表**

| 品类 | 总进货 | 当前库存 | 已消耗 | 消耗率 | 品类总价值 |
|------|--------|---------|--------|--------|-----------|
| 包材 | 500 件 | 200 件 | 300 件 | 60% | ¥3,000 |
| 原料 | 600 件 | 250 件 | 350 件 | 58% | ¥8,000 |
| 工具 | 80 件 | 30 件 | 50 件 | 62% | ¥2,400 |
| 成品 | 100 件 | 40 件 | 60 件 | 60% | ¥2,200 |

- 移动端支持横向滑动

**底部：消耗排行 Top 10**

| 排名 | 品项 | 品类 | 消耗量 | 消耗金额 |
|------|------|------|--------|---------|
| 1 | 纸箱 | 包材 | 200 件 | ¥1,000 |
| 2 | 面粉 | 原料 | 150 kg | ¥2,400 |
| ... | ... | ... | ... | ... |

- 按 `stock_movements WHERE action='出库' GROUP BY item_id ORDER BY SUM(delta) DESC` 取 Top 10
- 移动端支持横向滑动

### 导航栏更新

| 位置 | 修改 |
|------|------|
| 侧栏（base.html 桌面端） | 新增 `<a href="{{ url_for('summary') }}">汇总</a>` |
| 底部导航（base.html 移动端） | 新增 `<a href="{{ url_for('summary') }}">汇总</a>` |

## 后端路由

### `GET /summary`
执行聚合查询，返回上下文：
- `total_inbound` — 总入库数量
- `total_stock` — 当前总库存
- `consumption_rate` — 消耗率
- `total_inbound_value` — 进货总金额
- `total_stock_value` — 库存总价值
- `category_stats` — 按品类统计列表
- `top_consumed` — 消耗排行 Top 10

### 数据库查询

**总入库量 & 总进货金额：**
```sql
SELECT SUM(m.delta) AS total_qty
FROM stock_movements m
WHERE m.action = '补货入库'
```

**进货总金额（逐品项统计入库量 × 当前单价）：**
```sql
SELECT SUM(i.unit_cost * sub.inbound_qty) AS total_inbound_value
FROM (
    SELECT m.item_id, SUM(m.delta) AS inbound_qty
    FROM stock_movements m
    WHERE m.action = '补货入库'
    GROUP BY m.item_id
) sub
JOIN items i ON i.id = sub.item_id
```

**库存总价值：**
```sql
SELECT SUM(i.quantity * i.unit_cost) FROM items i
```

**按品类统计：**
```sql
SELECT c.name AS category_name,
       SUM(i.quantity) AS stock_qty,
       SUM(i.unit_cost * i.quantity) AS stock_value
FROM items i
JOIN categories c ON c.id = i.category_id
GROUP BY c.id
```

**消耗排行 Top 10：**
```sql
SELECT i.name AS item_name, c.name AS category_name,
       ABS(SUM(m.delta)) AS consumed_qty,
       ABS(SUM(m.delta)) * i.unit_cost AS consumed_value
FROM stock_movements m
JOIN items i ON i.id = m.item_id
JOIN categories c ON c.id = i.category_id
WHERE m.action = '出库'
GROUP BY m.item_id
ORDER BY consumed_qty DESC
LIMIT 10
```

## 路由注册

```python
@app.route("/summary")
def summary():
    ...
    return render_template("summary.html", ...)
```

## 样式
- 在 `static/style.css` 中添加汇总页专属样式
- 卡片复用现有 `.card` 样式，5 卡片使用 `.grid.cols-5` 配合媒体查询处理移动端 2-2-1 适配
- 表格复用现有 `<table>` 样式，外层加 `.table-wrapper` 实现横滑
