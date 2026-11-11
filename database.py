"""
database.py - all SQLite code for QR Dine lives here.

Why a separate file?
    The Streamlit pages (customer, kitchen, admin) never write SQL themselves.
    They just call the small functions below. This keeps the app easy to read.

Safety notes for beginners:
    * Every query uses "?" placeholders, never string formatting with user
      input. This prevents SQL injection.
    * A NEW connection is opened for every operation. Streamlit runs each
      browser session in its own thread, and SQLite connections should not be
      shared between threads.
    * WAL mode lets the kitchen read orders while a customer is writing one.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Where the database file lives. Override with the QR_DINE_DB environment variable.
DB_PATH = os.environ.get("QR_DINE_DB", str(BASE_DIR / "qr_dine.db"))

# Time zone used for order times. Override with RESTAURANT_TIMEZONE.
# (Streamlit Community Cloud servers run in UTC, so we convert explicitly.)
TIMEZONE_NAME = os.environ.get("RESTAURANT_TIMEZONE", "Asia/Karachi")

ORDER_STATUSES = ["New", "Preparing", "Ready", "Completed"]
MAX_QTY_PER_ITEM = 20
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# ---------------------------------------------------------------------------
# Demo menu: (category, name, description, price, image file in assets/)
# ---------------------------------------------------------------------------
DEMO_MENU = [
    ("Burgers", "Classic Beef Burger", "Juicy beef patty, cheddar, lettuce, tomato and house sauce.", 8.50, "classic_burger.png"),
    ("Burgers", "Crispy Chicken Burger", "Crunchy fried chicken fillet with mayo and pickles.", 7.90, "chicken_burger.png"),
    ("Burgers", "Veggie Burger", "Grilled vegetable and chickpea patty with avocado spread.", 7.20, "veggie_burger.png"),
    ("Pizza", "Margherita Pizza", "Tomato sauce, fresh mozzarella and basil.", 9.50, "margherita_pizza.png"),
    ("Pizza", "Pepperoni Pizza", "Mozzarella and plenty of spicy pepperoni.", 11.00, "pepperoni_pizza.png"),
    ("Pizza", "BBQ Chicken Pizza", "Smoky BBQ sauce, grilled chicken and red onion.", 11.50, "bbq_pizza.png"),
    ("Drinks", "Fresh Lemonade", "Cold-pressed lemons with a hint of mint.", 3.00, "lemonade.png"),
    ("Drinks", "Iced Coffee", "Double espresso over ice with milk.", 3.80, "iced_coffee.png"),
    ("Drinks", "Mango Smoothie", "Ripe mango blended with yoghurt.", 4.20, "mango_smoothie.png"),
    ("Desserts", "Chocolate Brownie", "Warm fudge brownie with a scoop of vanilla ice cream.", 5.00, "brownie.png"),
    ("Desserts", "Cheesecake Slice", "Creamy New York style cheesecake with berry sauce.", 5.50, "cheesecake.png"),
    ("Desserts", "Ice Cream Cup", "Three scoops: vanilla, chocolate and strawberry.", 4.00, "ice_cream.png"),
]


class DatabaseError(Exception):
    """Raised for any database problem or invalid data. The message is safe to show to users."""


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------
@contextmanager
def get_connection():
    """Open a connection, commit on success, roll back on error, always close."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        yield conn
        conn.commit()
    except sqlite3.IntegrityError as exc:
        if conn:
            conn.rollback()
        raise DatabaseError(
            "That change conflicts with existing data (for example, a duplicate name)."
        ) from exc
    except sqlite3.Error as exc:
        if conn:
            conn.rollback()
        raise DatabaseError(f"Database problem: {exc}") from exc
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------
def now_dt():
    """Current time in the restaurant's time zone (as a naive datetime)."""
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(TIMEZONE_NAME)).replace(tzinfo=None)
    except Exception:
        return datetime.now()


def now_str():
    return now_dt().strftime(TIME_FORMAT)


def today_str():
    return now_dt().strftime("%Y-%m-%d")


def format_order_number(order_id):
    """Order 7 becomes 'QD-0007'."""
    return f"QD-{int(order_id):04d}"


# ---------------------------------------------------------------------------
# Creating tables and demo data
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS menu_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    price       REAL NOT NULL CHECK (price >= 0),
    image       TEXT NOT NULL DEFAULT '',
    available   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS orders (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    table_number  INTEGER NOT NULL,
    customer_name TEXT NOT NULL DEFAULT '',
    status        TEXT NOT NULL DEFAULT 'New',
    total         REAL NOT NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

-- item_name and unit_price are copied from the menu at order time, so old
-- orders stay correct even if the menu item is edited or deleted later.
CREATE TABLE IF NOT EXISTS order_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id     INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    menu_item_id INTEGER REFERENCES menu_items(id) ON DELETE SET NULL,
    item_name    TEXT NOT NULL,
    unit_price   REAL NOT NULL,
    quantity     INTEGER NOT NULL CHECK (quantity > 0)
);

CREATE TABLE IF NOT EXISTS app_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_status  ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_items_order    ON order_items(order_id);
"""


def _seed_demo_data(conn):
    """Insert the sample categories and menu items using an open connection."""
    category_ids = {}
    for position, (category, *_rest) in enumerate(DEMO_MENU):
        if category not in category_ids:
            cur = conn.execute(
                "INSERT INTO categories (name, sort_order) VALUES (?, ?)",
                (category, len(category_ids) + 1),
            )
            category_ids[category] = cur.lastrowid
    for category, name, description, price, image_file in DEMO_MENU:
        conn.execute(
            "INSERT INTO menu_items (category_id, name, description, price, image, available) "
            "VALUES (?, ?, ?, ?, ?, 1)",
            (category_ids[category], name, description, price, f"assets/{image_file}"),
        )
    conn.execute("INSERT OR REPLACE INTO app_meta (key, value) VALUES ('seeded', '1')")


def init_db():
    """Create tables if needed and add demo data the very first time only."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        seeded = conn.execute("SELECT value FROM app_meta WHERE key = 'seeded'").fetchone()
        if seeded is None:
            _seed_demo_data(conn)


def reset_demo_data():
    """Delete EVERYTHING (menu, categories, orders) and restore the sample menu."""
    with get_connection() as conn:
        conn.executescript(
            """
            DROP TABLE IF EXISTS order_items;
            DROP TABLE IF EXISTS orders;
            DROP TABLE IF EXISTS menu_items;
            DROP TABLE IF EXISTS categories;
            DROP TABLE IF EXISTS app_meta;
            """
        )
    init_db()


def clear_all_orders():
    """Delete all orders but keep the menu."""
    with get_connection() as conn:
        conn.execute("DELETE FROM order_items")
        conn.execute("DELETE FROM orders")


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
def get_categories():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.name, c.sort_order,
                   (SELECT COUNT(*) FROM menu_items m WHERE m.category_id = c.id) AS item_count
            FROM categories c
            ORDER BY c.sort_order, c.id
            """
        ).fetchall()
    return [dict(r) for r in rows]


def add_category(name, sort_order=None):
    name = (name or "").strip()
    if not name:
        raise DatabaseError("Category name cannot be empty.")
    if len(name) > 40:
        raise DatabaseError("Category name is too long (max 40 characters).")
    with get_connection() as conn:
        if sort_order is None:
            row = conn.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 AS n FROM categories").fetchone()
            sort_order = row["n"]
        conn.execute("INSERT INTO categories (name, sort_order) VALUES (?, ?)", (name, int(sort_order)))


def update_category(category_id, name, sort_order):
    name = (name or "").strip()
    if not name:
        raise DatabaseError("Category name cannot be empty.")
    with get_connection() as conn:
        conn.execute(
            "UPDATE categories SET name = ?, sort_order = ? WHERE id = ?",
            (name, int(sort_order), int(category_id)),
        )


def delete_category(category_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM menu_items WHERE category_id = ?", (int(category_id),)
        ).fetchone()
        if row["n"] > 0:
            raise DatabaseError(
                "This category still has food items. Move or delete them first."
            )
        conn.execute("DELETE FROM categories WHERE id = ?", (int(category_id),))


# ---------------------------------------------------------------------------
# Menu items
# ---------------------------------------------------------------------------
def _validate_item(name, price):
    name = (name or "").strip()
    if not name:
        raise DatabaseError("Food name cannot be empty.")
    if len(name) > 60:
        raise DatabaseError("Food name is too long (max 60 characters).")
    try:
        price = round(float(price), 2)
    except (TypeError, ValueError):
        raise DatabaseError("Price must be a number.")
    if price < 0 or price > 100000:
        raise DatabaseError("Price must be between 0 and 100000.")
    return name, price


def get_menu_items(only_available=False):
    sql = """
        SELECT m.id, m.category_id, c.name AS category_name, m.name, m.description,
               m.price, m.image, m.available
        FROM menu_items m
        JOIN categories c ON c.id = m.category_id
    """
    if only_available:
        sql += " WHERE m.available = 1"
    sql += " ORDER BY c.sort_order, c.id, m.name"
    with get_connection() as conn:
        rows = conn.execute(sql).fetchall()
    return [dict(r) for r in rows]


def add_menu_item(name, description, price, category_id, image="", available=True):
    name, price = _validate_item(name, price)
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO menu_items (category_id, name, description, price, image, available) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (int(category_id), name, (description or "").strip(), price, (image or "").strip(), 1 if available else 0),
        )


def update_menu_item(item_id, name, description, price, category_id, image="", available=True):
    name, price = _validate_item(name, price)
    with get_connection() as conn:
        conn.execute(
            "UPDATE menu_items SET category_id = ?, name = ?, description = ?, price = ?, "
            "image = ?, available = ? WHERE id = ?",
            (int(category_id), name, (description or "").strip(), price, (image or "").strip(),
             1 if available else 0, int(item_id)),
        )


def set_availability(item_id, available):
    with get_connection() as conn:
        conn.execute(
            "UPDATE menu_items SET available = ? WHERE id = ?",
            (1 if available else 0, int(item_id)),
        )


def delete_menu_item(item_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM menu_items WHERE id = ?", (int(item_id),))


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
def create_order(table_number, customer_name, cart):
    """
    Save a new order.

    cart is a dict like {menu_item_id: quantity}. Prices are read from the
    database here (never trusted from the browser), and sold-out items are rejected.
    Returns {"id": ..., "order_number": "QD-0001", "total": 12.5}.
    """
    if not cart:
        raise DatabaseError("Your cart is empty.")
    try:
        table_number = int(table_number)
    except (TypeError, ValueError):
        raise DatabaseError("Invalid table number.")
    if table_number < 1:
        raise DatabaseError("Invalid table number.")
    customer_name = (customer_name or "").strip()[:40]

    with get_connection() as conn:
        lines = []
        total = 0.0
        for item_id, qty in cart.items():
            qty = int(qty)
            if qty < 1 or qty > MAX_QTY_PER_ITEM:
                raise DatabaseError(f"Quantity must be between 1 and {MAX_QTY_PER_ITEM}.")
            item = conn.execute(
                "SELECT id, name, price, available FROM menu_items WHERE id = ?", (int(item_id),)
            ).fetchone()
            if item is None:
                raise DatabaseError("One of the items in your cart is no longer on the menu.")
            if not item["available"]:
                raise DatabaseError(f"Sorry, '{item['name']}' is currently unavailable.")
            lines.append((item["id"], item["name"], item["price"], qty))
            total += item["price"] * qty
        total = round(total, 2)

        stamp = now_str()
        cur = conn.execute(
            "INSERT INTO orders (table_number, customer_name, status, total, created_at, updated_at) "
            "VALUES (?, ?, 'New', ?, ?, ?)",
            (table_number, customer_name, total, stamp, stamp),
        )
        order_id = cur.lastrowid
        for menu_item_id, item_name, unit_price, qty in lines:
            conn.execute(
                "INSERT INTO order_items (order_id, menu_item_id, item_name, unit_price, quantity) "
                "VALUES (?, ?, ?, ?, ?)",
                (order_id, menu_item_id, item_name, unit_price, qty),
            )
    return {"id": order_id, "order_number": format_order_number(order_id), "total": total}


def _attach_items(conn, orders):
    """Add an 'items' list to each order dict (uses one extra query)."""
    if not orders:
        return orders
    ids = [o["id"] for o in orders]
    placeholders = ",".join("?" for _ in ids)  # only "?" characters, never user data
    rows = conn.execute(
        f"SELECT order_id, item_name, unit_price, quantity FROM order_items "
        f"WHERE order_id IN ({placeholders}) ORDER BY id",
        ids,
    ).fetchall()
    by_order = {oid: [] for oid in ids}
    for r in rows:
        by_order[r["order_id"]].append(
            {"name": r["item_name"], "unit_price": r["unit_price"], "quantity": r["quantity"]}
        )
    for o in orders:
        o["items"] = by_order[o["id"]]
        o["order_number"] = format_order_number(o["id"])
    return orders


def get_orders(statuses=None, ascending=False, limit=None):
    """Return orders (with their items). statuses=None means all statuses."""
    sql = "SELECT * FROM orders"
    params = []
    if statuses:
        sql += " WHERE status IN ({})".format(",".join("?" for _ in statuses))
        params.extend(statuses)
    sql += " ORDER BY id " + ("ASC" if ascending else "DESC")
    if limit:
        sql += " LIMIT ?"
        params.append(int(limit))
    with get_connection() as conn:
        orders = [dict(r) for r in conn.execute(sql, params).fetchall()]
        return _attach_items(conn, orders)


def get_order(order_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (int(order_id),)).fetchone()
        if row is None:
            return None
        return _attach_items(conn, [dict(row)])[0]


def update_order_status(order_id, new_status):
    if new_status not in ORDER_STATUSES:
        raise DatabaseError("Unknown order status.")
    with get_connection() as conn:
        conn.execute(
            "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
            (new_status, now_str(), int(order_id)),
        )


def get_status_counts():
    counts = {s: 0 for s in ORDER_STATUSES}
    with get_connection() as conn:
        for r in conn.execute("SELECT status, COUNT(*) AS n FROM orders GROUP BY status").fetchall():
            counts[r["status"]] = r["n"]
    return counts


# ---------------------------------------------------------------------------
# Sales summaries
# ---------------------------------------------------------------------------
def get_sales_summary(day):
    """Orders and revenue for one day, given as 'YYYY-MM-DD'."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS orders, COALESCE(SUM(total), 0) AS revenue "
            "FROM orders WHERE substr(created_at, 1, 10) = ?",
            (day,),
        ).fetchone()
    orders = row["orders"]
    revenue = round(row["revenue"], 2)
    return {
        "orders": orders,
        "revenue": revenue,
        "average": round(revenue / orders, 2) if orders else 0.0,
    }


def get_daily_sales(days=14):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS orders, SUM(total) AS revenue "
            "FROM orders GROUP BY day ORDER BY day DESC LIMIT ?",
            (int(days),),
        ).fetchall()
    return [
        {"date": r["day"], "orders": r["orders"], "revenue": round(r["revenue"], 2)}
        for r in reversed(rows)
    ]


def get_top_items(limit=5):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT item_name, SUM(quantity) AS qty, SUM(quantity * unit_price) AS revenue "
            "FROM order_items GROUP BY item_name ORDER BY qty DESC, revenue DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    return [
        {"item": r["item_name"], "quantity": r["qty"], "revenue": round(r["revenue"], 2)}
        for r in rows
    ]
