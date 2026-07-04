"""
db.py — database connection and helper functions for the pharmacy marketplace.
Uses SQLite for simplicity (portable, zero setup). Swap to PostgreSQL later
by changing only this file if the project grows beyond a portfolio demo.
"""

import sqlite3
import hashlib
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "pharmacy_marketplace.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str) -> str:
    """Simple SHA-256 hashing for demo purposes.
    NOTE: for a real production app, use bcrypt/argon2 with per-user salts —
    this is intentionally simple so the logic stays readable for learning."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


# ----------------------------------------------------------------------
# Auth
# ----------------------------------------------------------------------
def get_user_by_username(username: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return row


def create_user(username, password, role, full_name, phone, city):
    conn = get_connection()
    conn.execute(
        "INSERT INTO users (username, password, role, full_name, phone, city) VALUES (?, ?, ?, ?, ?, ?)",
        (username, hash_password(password), role, full_name, phone, city),
    )
    conn.commit()
    user_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    conn.close()
    return user_id


def create_pharmacy(owner_user_id, name, description, license_no, gstin, city):
    conn = get_connection()
    conn.execute(
        """INSERT INTO pharmacies (owner_user_id, name, description, license_no, gstin, city)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (owner_user_id, name, description, license_no, gstin, city),
    )
    conn.commit()
    pharmacy_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    conn.execute("UPDATE users SET pharmacy_id = ? WHERE id = ?", (pharmacy_id, owner_user_id))
    conn.commit()
    conn.close()
    return pharmacy_id


def get_pharmacy(pharmacy_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM pharmacies WHERE id = ?", (pharmacy_id,)).fetchone()
    conn.close()
    return row


def update_pharmacy(pharmacy_id, name, description, logo_url, license_no, gstin, city):
    conn = get_connection()
    conn.execute(
        """UPDATE pharmacies SET name=?, description=?, logo_url=?, license_no=?, gstin=?, city=?
           WHERE id=?""",
        (name, description, logo_url, license_no, gstin, city, pharmacy_id),
    )
    conn.commit()
    conn.close()


# ----------------------------------------------------------------------
# Products
# ----------------------------------------------------------------------
def add_product(pharmacy_id, name, brand, category, image_url, mrp, discount_pct,
                 stock_qty, schedule, gst_rate, batch_no, expiry_date):
    selling_price = round(mrp * (1 - discount_pct / 100), 2)
    conn = get_connection()
    conn.execute(
        """INSERT INTO products
           (pharmacy_id, name, brand, category, image_url, mrp, discount_pct, selling_price,
            stock_qty, schedule, gst_rate, batch_no, expiry_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (pharmacy_id, name, brand, category, image_url, mrp, discount_pct, selling_price,
         stock_qty, schedule, gst_rate, batch_no, expiry_date),
    )
    conn.commit()
    conn.close()


def update_product_discount(product_id, discount_pct):
    conn = get_connection()
    row = conn.execute("SELECT mrp FROM products WHERE id=?", (product_id,)).fetchone()
    selling_price = round(row["mrp"] * (1 - discount_pct / 100), 2)
    conn.execute("UPDATE products SET discount_pct=?, selling_price=? WHERE id=?",
                 (discount_pct, selling_price, product_id))
    conn.commit()
    conn.close()


def get_all_products(search=None, category=None):
    conn = get_connection()
    query = """SELECT p.*, ph.name AS pharmacy_name, ph.city AS pharmacy_city
               FROM products p JOIN pharmacies ph ON p.pharmacy_id = ph.id
               WHERE p.stock_qty > 0"""
    params = []
    if search:
        query += " AND (p.name LIKE ? OR p.brand LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if category and category != "All":
        query += " AND p.category = ?"
        params.append(category)
    query += " ORDER BY p.discount_pct DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_products_by_pharmacy(pharmacy_id):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM products WHERE pharmacy_id = ? ORDER BY id DESC", (pharmacy_id,)).fetchall()
    conn.close()
    return rows


def get_product(product_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    return row


def reduce_stock(product_id, qty):
    conn = get_connection()
    conn.execute("UPDATE products SET stock_qty = stock_qty - ? WHERE id = ?", (qty, product_id))
    conn.commit()
    conn.close()


# ----------------------------------------------------------------------
# Orders
# ----------------------------------------------------------------------
def create_order(customer_id, pharmacy_id, cart_items, payment_mode, delivery_mode):
    """cart_items: list of dicts {product_id, name, qty, unit_price, gst_rate}"""
    subtotal = sum(i["unit_price"] * i["qty"] for i in cart_items)
    gst_amount = sum(i["unit_price"] * i["qty"] * i["gst_rate"] / 100 for i in cart_items)
    total_amount = round(subtotal + gst_amount, 2)
    prescription_required = 1 if any(i.get("schedule") in ("H", "H1", "X") for i in cart_items) else 0

    payment_status = "Pending" if payment_mode == "COD" else "Paid"
    delivery_status = "Placed"

    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO orders
           (customer_id, pharmacy_id, order_date, subtotal, gst_amount, total_amount,
            payment_mode, payment_status, delivery_mode, delivery_status, prescription_required)
           VALUES (?, ?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?)""",
        (customer_id, pharmacy_id, round(subtotal, 2), round(gst_amount, 2), total_amount,
         payment_mode, payment_status, delivery_mode, delivery_status, prescription_required),
    )
    order_id = cur.lastrowid

    for item in cart_items:
        conn.execute(
            """INSERT INTO order_items (order_id, product_id, quantity, unit_price, line_total)
               VALUES (?, ?, ?, ?, ?)""",
            (order_id, item["product_id"], item["qty"], item["unit_price"],
             round(item["unit_price"] * item["qty"], 2)),
        )
        conn.execute("UPDATE products SET stock_qty = stock_qty - ? WHERE id = ?",
                     (item["qty"], item["product_id"]))

    conn.commit()
    conn.close()
    return order_id, total_amount


def get_orders_for_customer(customer_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT o.*, ph.name AS pharmacy_name FROM orders o
           JOIN pharmacies ph ON o.pharmacy_id = ph.id
           WHERE o.customer_id = ? ORDER BY o.order_date DESC""",
        (customer_id,),
    ).fetchall()
    conn.close()
    return rows


def get_orders_for_pharmacy(pharmacy_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT o.*, u.full_name AS customer_name FROM orders o
           JOIN users u ON o.customer_id = u.id
           WHERE o.pharmacy_id = ? ORDER BY o.order_date DESC""",
        (pharmacy_id,),
    ).fetchall()
    conn.close()
    return rows


def get_order_items(order_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT oi.*, p.name AS product_name FROM order_items oi
           JOIN products p ON oi.product_id = p.id WHERE oi.order_id = ?""",
        (order_id,),
    ).fetchall()
    conn.close()
    return rows


def update_delivery_status(order_id, status):
    conn = get_connection()
    conn.execute("UPDATE orders SET delivery_status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()


def update_payment_status(order_id, status):
    conn = get_connection()
    conn.execute("UPDATE orders SET payment_status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()


# ----------------------------------------------------------------------
# Staff & Salary
# ----------------------------------------------------------------------
def get_staff(pharmacy_id):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM staff WHERE pharmacy_id = ?", (pharmacy_id,)).fetchall()
    conn.close()
    return rows


def add_staff(pharmacy_id, name, role, phone, joining_date, monthly_salary):
    conn = get_connection()
    conn.execute(
        """INSERT INTO staff (pharmacy_id, name, role, phone, joining_date, monthly_salary)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (pharmacy_id, name, role, phone, joining_date, monthly_salary),
    )
    conn.commit()
    conn.close()


def get_salary_payments(pharmacy_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT sp.*, s.name AS staff_name FROM salary_payments sp
           JOIN staff s ON sp.staff_id = s.id WHERE s.pharmacy_id = ?
           ORDER BY sp.month DESC""",
        (pharmacy_id,),
    ).fetchall()
    conn.close()
    return rows


def pay_salary(staff_id, month, amount):
    conn = get_connection()
    conn.execute(
        """INSERT INTO salary_payments (staff_id, month, amount, status, payment_date)
           VALUES (?, ?, ?, 'Paid', date('now'))""",
        (staff_id, month, amount),
    )
    conn.commit()
    conn.close()


# ----------------------------------------------------------------------
# Expenses
# ----------------------------------------------------------------------
def add_expense(pharmacy_id, expense_date, category, amount, description):
    conn = get_connection()
    conn.execute(
        """INSERT INTO expenses (pharmacy_id, expense_date, category, amount, description)
           VALUES (?, ?, ?, ?, ?)""",
        (pharmacy_id, expense_date, category, amount, description),
    )
    conn.commit()
    conn.close()


def get_expenses(pharmacy_id):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM expenses WHERE pharmacy_id = ? ORDER BY expense_date DESC",
                         (pharmacy_id,)).fetchall()
    conn.close()
    return rows
