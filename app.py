from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, flash, g, redirect, render_template, request, send_from_directory, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "inventory.db"
FIXED_CATEGORIES = ("包材", "原料", "工具")

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-key-change-me"


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(_: Any) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db() -> None:
    schema = """
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        category_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 0,
        safety_stock INTEGER NOT NULL DEFAULT 0,
        unit TEXT NOT NULL DEFAULT '件',
        updated_at TEXT NOT NULL,
        FOREIGN KEY (category_id) REFERENCES categories(id)
    );

    CREATE TABLE IF NOT EXISTS stock_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        delta INTEGER NOT NULL,
        note TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (item_id) REFERENCES items(id)
    );

    CREATE TABLE IF NOT EXISTS stocktakes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        previous_quantity INTEGER NOT NULL,
        actual_quantity INTEGER NOT NULL,
        diff INTEGER NOT NULL,
        batch_id INTEGER,
        created_at TEXT NOT NULL,
        note TEXT,
        FOREIGN KEY (item_id) REFERENCES items(id)
    );

    CREATE TABLE IF NOT EXISTS stocktake_batches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        note TEXT,
        rolled_back INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS restock_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        requested_quantity INTEGER NOT NULL,
        reason TEXT,
        status TEXT NOT NULL DEFAULT '待审批',
        created_at TEXT NOT NULL,
        FOREIGN KEY (item_id) REFERENCES items(id)
    );
    """
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.executescript(schema)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(stocktakes)").fetchall()]
        if "batch_id" not in cols:
            conn.execute("ALTER TABLE stocktakes ADD COLUMN batch_id INTEGER")

        existing = {r[0] for r in conn.execute("SELECT name FROM categories").fetchall()}
        for name in FIXED_CATEGORIES:
            if name not in existing:
                conn.execute(
                    "INSERT INTO categories (name, description, created_at) VALUES (?, ?, ?)",
                    (name, "系统固定品类", now()),
                )
        conn.commit()


@app.route("/")
def dashboard():
    db = get_db()
    total_items = db.execute("SELECT COUNT(*) AS c FROM items").fetchone()["c"]
    total_categories = db.execute("SELECT COUNT(*) AS c FROM categories").fetchone()["c"]
    low_stock = db.execute(
        "SELECT COUNT(*) AS c FROM items WHERE quantity <= safety_stock"
    ).fetchone()["c"]
    pending_requests = db.execute(
        "SELECT COUNT(*) AS c FROM restock_requests WHERE status = '待审批'"
    ).fetchone()["c"]

    latest_movements = db.execute(
        """
        SELECT m.created_at, m.action, m.delta, i.name AS item_name, i.sku
        FROM stock_movements m
        JOIN items i ON i.id = m.item_id
        ORDER BY m.id DESC
        LIMIT 8
        """
    ).fetchall()

    return render_template(
        "dashboard.html",
        total_items=total_items,
        total_categories=total_categories,
        low_stock=low_stock,
        pending_requests=pending_requests,
        latest_movements=latest_movements,
    )


@app.route("/categories", methods=["GET"])
def categories():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM categories WHERE name IN (?, ?, ?) ORDER BY id ASC",
        FIXED_CATEGORIES,
    ).fetchall()
    return render_template("categories.html", categories=rows)


@app.route("/categories/<int:category_id>/delete", methods=["POST"])
def delete_category(category_id: int):
    flash("品类为系统固定项，不支持删除")
    return redirect(url_for("categories"))


@app.route("/items", methods=["GET", "POST"])
def items():
    db = get_db()
    if request.method == "POST":
        sku = request.form.get("sku", "").strip()
        name = request.form.get("name", "").strip()
        category_id = request.form.get("category_id", "").strip()
        quantity = int(request.form.get("quantity", "0") or 0)
        safety_stock = int(request.form.get("safety_stock", "0") or 0)
        unit = request.form.get("unit", "件").strip() or "件"

        if not sku or not name or not category_id:
            flash("SKU、名称、品类为必填")
            return redirect(url_for("items"))
        try:
            db.execute(
                """
                INSERT INTO items (sku, name, category_id, quantity, safety_stock, unit, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (sku, name, int(category_id), quantity, safety_stock, unit, now()),
            )
            db.commit()
            flash("库存品创建成功")
        except sqlite3.IntegrityError:
            flash("SKU 已存在")
        return redirect(url_for("items"))

    categories_data = db.execute(
        "SELECT id, name FROM categories WHERE name IN (?, ?, ?) ORDER BY name",
        FIXED_CATEGORIES,
    ).fetchall()
    rows = db.execute(
        """
        SELECT i.*, c.name AS category_name
        FROM items i
        JOIN categories c ON c.id = i.category_id
        ORDER BY i.id DESC
        """
    ).fetchall()
    return render_template("items.html", items=rows, categories=categories_data)


@app.route("/items/<int:item_id>/delete", methods=["POST"])
def delete_item(item_id: int):
    db = get_db()
    movement_count = db.execute(
        "SELECT COUNT(*) AS c FROM stock_movements WHERE item_id = ?", (item_id,)
    ).fetchone()["c"]
    stocktake_count = db.execute(
        "SELECT COUNT(*) AS c FROM stocktakes WHERE item_id = ?", (item_id,)
    ).fetchone()["c"]
    restock_count = db.execute(
        "SELECT COUNT(*) AS c FROM restock_requests WHERE item_id = ?", (item_id,)
    ).fetchone()["c"]

    if movement_count + stocktake_count + restock_count > 0:
        flash("该库存品已有业务记录，暂不允许删除")
        return redirect(url_for("items"))

    db.execute("DELETE FROM items WHERE id = ?", (item_id,))
    db.commit()
    flash("库存品已删除")
    return redirect(url_for("items"))


@app.route("/stock-in", methods=["GET", "POST"])
def stock_in():
    db = get_db()
    if request.method == "POST":
        item_id = int(request.form.get("item_id", "0") or 0)
        quantity = int(request.form.get("quantity", "0") or 0)
        note = request.form.get("note", "").strip()
        if item_id <= 0 or quantity <= 0:
            flash("请选择品项并填写正确入库数量")
            return redirect(url_for("stock_in"))

        db.execute(
            "UPDATE items SET quantity = quantity + ?, updated_at = ? WHERE id = ?",
            (quantity, now(), item_id),
        )
        db.execute(
            """
            INSERT INTO stock_movements (item_id, action, delta, note, created_at)
            VALUES (?, '入库', ?, ?, ?)
            """,
            (item_id, quantity, note, now()),
        )
        db.commit()
        flash("入库成功")
        return redirect(url_for("stock_in"))

    items_data = db.execute(
        "SELECT id, sku, name, quantity, unit FROM items ORDER BY name"
    ).fetchall()
    records = db.execute(
        """
        SELECT m.*, i.sku, i.name AS item_name
        FROM stock_movements m
        JOIN items i ON i.id = m.item_id
        WHERE m.action = '入库'
        ORDER BY m.id DESC
        LIMIT 30
        """
    ).fetchall()
    return render_template("stock_in.html", items=items_data, records=records)


@app.route("/stock-in/<int:movement_id>/delete", methods=["POST"])
def delete_stock_in(movement_id: int):
    db = get_db()
    record = db.execute(
        "SELECT * FROM stock_movements WHERE id = ? AND action = '入库'", (movement_id,)
    ).fetchone()
    if record is None:
        flash("未找到入库记录")
        return redirect(url_for("stock_in"))

    item = db.execute(
        "SELECT quantity FROM items WHERE id = ?", (record["item_id"],)
    ).fetchone()
    if item is None:
        flash("入库对应库存品不存在")
        return redirect(url_for("stock_in"))
    if int(item["quantity"]) < int(record["delta"]):
        flash("当前库存不足以回滚该入库记录，删除失败")
        return redirect(url_for("stock_in"))

    db.execute(
        "UPDATE items SET quantity = quantity - ?, updated_at = ? WHERE id = ?",
        (record["delta"], now(), record["item_id"]),
    )
    db.execute("DELETE FROM stock_movements WHERE id = ?", (movement_id,))
    db.commit()
    flash("入库记录已删除并回滚库存")
    return redirect(url_for("stock_in"))


@app.route("/stocktake", methods=["GET"])
def stocktake():
    db = get_db()
    batches = db.execute(
        """
        SELECT b.id, b.created_at, b.note, b.rolled_back, COUNT(s.id) AS item_count
        FROM stocktake_batches b
        LEFT JOIN stocktakes s ON s.batch_id = b.id
        GROUP BY b.id
        ORDER BY b.id DESC
        LIMIT 20
        """
    ).fetchall()
    return render_template("stocktake.html", batches=batches)


@app.route("/stocktake/start", methods=["POST"])
def stocktake_start():
    return redirect(url_for("stocktake_session"))


@app.route("/stocktake/session", methods=["GET"])
def stocktake_session():
    db = get_db()
    items_data = db.execute(
        """
        SELECT i.id, i.sku, i.name, i.quantity, i.unit, i.safety_stock, c.name AS category_name
        FROM items i
        JOIN categories c ON c.id = i.category_id
        ORDER BY c.name, i.name
        """
    ).fetchall()
    return render_template("stocktake_session.html", items=items_data)


@app.route("/stocktake/submit", methods=["POST"])
def stocktake_submit():
    db = get_db()
    note = request.form.get("note", "").strip()
    items_data = db.execute("SELECT id, quantity FROM items").fetchall()

    changed_rows: list[tuple[int, int, int, int]] = []
    for item in items_data:
        field = f"actual_{item['id']}"
        raw = request.form.get(field, "").strip()
        if raw == "":
            continue
        actual_quantity = int(raw)
        previous_quantity = int(item["quantity"])
        diff = actual_quantity - previous_quantity
        changed_rows.append((int(item["id"]), previous_quantity, actual_quantity, diff))

    if not changed_rows:
        flash("请至少填写一个盘点数量")
        return redirect(url_for("stocktake_session"))

    cur = db.execute(
        "INSERT INTO stocktake_batches (created_at, note, rolled_back) VALUES (?, ?, 0)",
        (now(), note),
    )
    batch_id = cur.lastrowid

    for item_id, previous_quantity, actual_quantity, diff in changed_rows:
        db.execute(
            "UPDATE items SET quantity = ?, updated_at = ? WHERE id = ?",
            (actual_quantity, now(), item_id),
        )
        db.execute(
            """
            INSERT INTO stocktakes (item_id, previous_quantity, actual_quantity, diff, batch_id, created_at, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (item_id, previous_quantity, actual_quantity, diff, batch_id, now(), note),
        )
        if diff != 0:
            db.execute(
                """
                INSERT INTO stock_movements (item_id, action, delta, note, created_at)
                VALUES (?, '盘点调整', ?, ?, ?)
                """,
                (item_id, diff, note or f"批次盘点#{batch_id}", now()),
            )
    db.commit()
    flash(f"盘点批次 #{batch_id} 已生成，可在列表中回滚")
    return redirect(url_for("stocktake"))


@app.route("/stocktake/batch/<int:batch_id>/rollback", methods=["POST"])
def rollback_stocktake_batch(batch_id: int):
    db = get_db()
    batch = db.execute(
        "SELECT id, rolled_back FROM stocktake_batches WHERE id = ?", (batch_id,)
    ).fetchone()
    if batch is None:
        flash("盘点批次不存在")
        return redirect(url_for("stocktake"))
    if int(batch["rolled_back"]) == 1:
        flash("该批次已回滚，无需重复操作")
        return redirect(url_for("stocktake"))

    records = db.execute(
        "SELECT item_id, diff FROM stocktakes WHERE batch_id = ?", (batch_id,)
    ).fetchall()
    for record in records:
        diff = int(record["diff"])
        if diff == 0:
            continue
        item_id = int(record["item_id"])
        db.execute(
            "UPDATE items SET quantity = quantity - ?, updated_at = ? WHERE id = ?",
            (diff, now(), item_id),
        )
        db.execute(
            """
            INSERT INTO stock_movements (item_id, action, delta, note, created_at)
            VALUES (?, '盘点回滚', ?, ?, ?)
            """,
            (item_id, -diff, f"回滚盘点批次#{batch_id}", now()),
        )

    db.execute("UPDATE stocktake_batches SET rolled_back = 1 WHERE id = ?", (batch_id,))
    db.commit()
    flash(f"盘点批次 #{batch_id} 已回滚")
    return redirect(url_for("stocktake"))


@app.route("/inventory")
def inventory():
    db = get_db()
    q = request.args.get("q", "").strip()
    if q:
        rows = db.execute(
            """
            SELECT i.*, c.name AS category_name
            FROM items i
            JOIN categories c ON c.id = i.category_id
            WHERE i.sku LIKE ? OR i.name LIKE ? OR c.name LIKE ?
            ORDER BY i.updated_at DESC
            """,
            (f"%{q}%", f"%{q}%", f"%{q}%"),
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT i.*, c.name AS category_name
            FROM items i
            JOIN categories c ON c.id = i.category_id
            ORDER BY i.updated_at DESC
            """
        ).fetchall()
    return render_template("inventory.html", items=rows, q=q)


@app.route("/restock", methods=["GET", "POST"])
def restock():
    db = get_db()
    if request.method == "POST":
        item_id = int(request.form.get("item_id", "0") or 0)
        requested_quantity = int(request.form.get("requested_quantity", "0") or 0)
        reason = request.form.get("reason", "").strip()
        if item_id <= 0 or requested_quantity <= 0:
            flash("请选择品项并填写正确补货数量")
            return redirect(url_for("restock"))

        db.execute(
            """
            INSERT INTO restock_requests (item_id, requested_quantity, reason, status, created_at)
            VALUES (?, ?, ?, '待审批', ?)
            """,
            (item_id, requested_quantity, reason, now()),
        )
        db.commit()
        flash("补货申请已提交")
        return redirect(url_for("restock"))

    status = request.args.get("status", "")
    items_data = db.execute(
        "SELECT id, sku, name, quantity, safety_stock, unit FROM items ORDER BY name"
    ).fetchall()

    if status:
        requests_data = db.execute(
            """
            SELECT r.*, i.name AS item_name, i.sku
            FROM restock_requests r
            JOIN items i ON i.id = r.item_id
            WHERE r.status = ?
            ORDER BY r.id DESC
            """,
            (status,),
        ).fetchall()
    else:
        requests_data = db.execute(
            """
            SELECT r.*, i.name AS item_name, i.sku
            FROM restock_requests r
            JOIN items i ON i.id = r.item_id
            ORDER BY r.id DESC
            """
        ).fetchall()

    return render_template(
        "restock.html", items=items_data, requests=requests_data, status=status
    )


@app.route("/restock/<int:req_id>/status", methods=["POST"])
def update_restock_status(req_id: int):
    status = request.form.get("status", "").strip()
    if status not in {"待审批", "已批准", "已拒绝", "已完成"}:
        flash("状态非法")
        return redirect(url_for("restock"))

    db = get_db()
    db.execute("UPDATE restock_requests SET status = ? WHERE id = ?", (status, req_id))
    db.commit()
    flash("补货申请状态已更新")
    return redirect(url_for("restock"))


@app.route("/restock/<int:req_id>/delete", methods=["POST"])
def delete_restock(req_id: int):
    db = get_db()
    db.execute("DELETE FROM restock_requests WHERE id = ?", (req_id,))
    db.commit()
    flash("补货申请已删除")
    return redirect(url_for("restock"))


@app.route("/sw.js")
def service_worker():
    return send_from_directory(BASE_DIR / "static", "sw.js")


@app.route("/manifest.webmanifest")
def webmanifest():
    return send_from_directory(BASE_DIR / "static", "manifest.webmanifest")


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5001, debug=True)
