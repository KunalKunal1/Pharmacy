"""
init_db.py — creates the SQLite schema and seeds realistic Indian demo data:
multiple pharmacy stores, products with MRP/discount pricing, staff,
customers, and sample orders across all payment/delivery modes.
Run this once before starting the app.
"""

import sqlite3
import random
from pathlib import Path
from datetime import datetime, timedelta

from db import hash_password

DB_PATH = Path(__file__).parent / "data" / "pharmacy_marketplace.db"
DB_PATH.parent.mkdir(exist_ok=True)
DB_PATH.unlink(missing_ok=True)  # fresh start each time this script runs

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON")

# ----------------------------------------------------------------------
# Schema
# ----------------------------------------------------------------------
conn.executescript(
    """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('pharmacy', 'customer')),
    full_name TEXT,
    phone TEXT,
    city TEXT,
    pharmacy_id INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE pharmacies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_user_id INTEGER,
    name TEXT NOT NULL,
    description TEXT,
    logo_url TEXT,
    license_no TEXT,
    gstin TEXT,
    city TEXT,
    FOREIGN KEY(owner_user_id) REFERENCES users(id)
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pharmacy_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    brand TEXT,
    category TEXT,
    image_url TEXT,
    mrp REAL NOT NULL,
    discount_pct REAL DEFAULT 0,
    selling_price REAL NOT NULL,
    stock_qty INTEGER DEFAULT 0,
    schedule TEXT DEFAULT 'OTC',   -- OTC, H, H1, X
    gst_rate REAL DEFAULT 12,
    batch_no TEXT,
    expiry_date TEXT,
    FOREIGN KEY(pharmacy_id) REFERENCES pharmacies(id)
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    pharmacy_id INTEGER NOT NULL,
    order_date TEXT,
    subtotal REAL,
    gst_amount REAL,
    total_amount REAL,
    payment_mode TEXT,      -- Cash, UPI, Card, COD
    payment_status TEXT,    -- Paid, Pending
    delivery_mode TEXT,     -- Store Pickup, Own Rider, Zepto, Blinkit
    delivery_status TEXT,   -- Placed, Packed, Out for Delivery, Delivered, Cancelled
    prescription_required INTEGER DEFAULT 0,
    FOREIGN KEY(customer_id) REFERENCES users(id),
    FOREIGN KEY(pharmacy_id) REFERENCES pharmacies(id)
);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER,
    unit_price REAL,
    line_total REAL,
    FOREIGN KEY(order_id) REFERENCES orders(id),
    FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE staff (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pharmacy_id INTEGER NOT NULL,
    name TEXT,
    role TEXT,              -- Pharmacist, Cashier, Delivery Rider, Manager
    phone TEXT,
    joining_date TEXT,
    monthly_salary REAL,
    FOREIGN KEY(pharmacy_id) REFERENCES pharmacies(id)
);

CREATE TABLE salary_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_id INTEGER NOT NULL,
    month TEXT,
    amount REAL,
    status TEXT,
    payment_date TEXT,
    FOREIGN KEY(staff_id) REFERENCES staff(id)
);

CREATE TABLE expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pharmacy_id INTEGER NOT NULL,
    expense_date TEXT,
    category TEXT,          -- Rent, Electricity, Maintenance, Misc
    amount REAL,
    description TEXT,
    FOREIGN KEY(pharmacy_id) REFERENCES pharmacies(id)
);
"""
)
conn.commit()

# ----------------------------------------------------------------------
# Seed: Pharmacy owners + pharmacies
# ----------------------------------------------------------------------
rng = random.Random(42)

pharmacy_seed = [
    {
        "username": "shreepharmacy", "password": "pharma123",
        "full_name": "Ramesh Deshmukh", "phone": "9876500001", "city": "Shegaon",
        "store_name": "Shree Pharmacy & Medical Store",
        "description": "Trusted neighbourhood pharmacy in Shegaon serving the community for 15+ years. Genuine medicines, licensed pharmacists, and doorstep delivery.",
        "license_no": "MH-BUL-2011-0234", "gstin": "27ABCDE1234F1Z5",
    },
    {
        "username": "wellcarepharmacy", "password": "pharma123",
        "full_name": "Sunita Kulkarni", "phone": "9876500002", "city": "Pune",
        "store_name": "WellCare Pharmacy",
        "description": "Pune-based pharmacy chain offering a wide range of medicines, wellness products, and fast delivery across the city.",
        "license_no": "MH-PUN-2015-0891", "gstin": "27PQRSX5678G1Z2",
    },
    {
        "username": "citymedicos", "password": "pharma123",
        "full_name": "Anil Verma", "phone": "9876500003", "city": "Nagpur",
        "store_name": "City Medicos",
        "description": "Nagpur's reliable medical store for prescription and OTC medicines with the best prices on essentials.",
        "license_no": "MH-NAG-2018-0456", "gstin": "27LMNOP9012H1Z8",
    },
]

pharmacy_ids = {}
for p in pharmacy_seed:
    cur = conn.execute(
        "INSERT INTO users (username, password, role, full_name, phone, city) VALUES (?, ?, 'pharmacy', ?, ?, ?)",
        (p["username"], hash_password(p["password"]), p["full_name"], p["phone"], p["city"]),
    )
    user_id = cur.lastrowid
    cur2 = conn.execute(
        """INSERT INTO pharmacies (owner_user_id, name, description, logo_url, license_no, gstin, city)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, p["store_name"], p["description"],
         f"https://placehold.co/120x120/2E8B57/FFFFFF?text={p['store_name'].split()[0]}",
         p["license_no"], p["gstin"], p["city"]),
    )
    pharmacy_id = cur2.lastrowid
    conn.execute("UPDATE users SET pharmacy_id = ? WHERE id = ?", (pharmacy_id, user_id))
    pharmacy_ids[p["store_name"]] = pharmacy_id

conn.commit()

# ----------------------------------------------------------------------
# Seed: Demo customer
# ----------------------------------------------------------------------
conn.execute(
    "INSERT INTO users (username, password, role, full_name, phone, city) VALUES (?, ?, 'customer', ?, ?, ?)",
    ("customer1", hash_password("customer123"), "Kunal Mhaisane", "9876500099", "Shegaon"),
)
conn.commit()

# ----------------------------------------------------------------------
# Seed: Products (common Indian medicines, distributed across pharmacies)
# ----------------------------------------------------------------------
medicine_catalog = [
    ("Paracetamol 500mg", "Crocin", "Pain Relief", 30, "OTC", 12),
    ("Dolo 650", "Micro Labs", "Pain Relief", 35, "OTC", 12),
    ("Combiflam", "Sanofi", "Pain Relief", 40, "OTC", 12),
    ("Cetirizine 10mg", "Cetrizet", "Allergy", 25, "OTC", 5),
    ("Vicks Vaporub 50ml", "Vicks", "Cold & Cough", 110, "OTC", 18),
    ("ORS Powder", "Electral", "Wellness", 45, "OTC", 5),
    ("Digene Gel 200ml", "Abbott", "Digestive Care", 130, "OTC", 12),
    ("Betadine Ointment", "Win-Medicare", "First Aid", 85, "OTC", 12),
    ("Volini Gel 50g", "Sun Pharma", "Pain Relief", 145, "OTC", 18),
    ("Amoxicillin 500mg", "Novamox", "Antibiotic", 90, "H", 12),
    ("Azithromycin 500mg", "Azithral", "Antibiotic", 120, "H", 12),
    ("Pantoprazole 40mg", "Pantocid", "Digestive Care", 95, "H", 12),
    ("Metformin 500mg", "Glycomet", "Diabetes Care", 60, "H", 5),
    ("Amlodipine 5mg", "Amlopres", "Cardiac Care", 55, "H", 5),
    ("Atorvastatin 10mg", "Atorva", "Cardiac Care", 105, "H", 5),
    ("Losartan 50mg", "Losar", "Cardiac Care", 88, "H", 5),
    ("Insulin Glargine Injection", "Basalog", "Diabetes Care", 650, "H", 5),
    ("Ecosprin 75mg", "USV", "Cardiac Care", 22, "H", 5),
    ("Alprazolam 0.25mg", "Alprax", "Neuro Care", 45, "H1", 12),
    ("Tramadol 50mg", "Tramazac", "Pain Relief", 60, "X", 12),
    ("Multivitamin Tablets", "Revital H", "Wellness", 320, "OTC", 18),
    ("Protein Powder 500g", "Ensure", "Wellness", 780, "OTC", 18),
    ("Hand Sanitizer 200ml", "Dettol", "Hygiene", 95, "OTC", 18),
    ("N95 Face Mask (Pack of 5)", "Venus", "Hygiene", 250, "OTC", 12),
    ("Glucometer Strips (25s)", "Accu-Chek", "Diabetes Care", 480, "OTC", 12),
]

categories = sorted(set(m[2] for m in medicine_catalog))

pharmacy_id_list = list(pharmacy_ids.values())
for pid in pharmacy_id_list:
    # each pharmacy stocks a random subset of the catalog with its own pricing/discounts
    stock_list = rng.sample(medicine_catalog, k=rng.randint(15, len(medicine_catalog)))
    for name, brand, category, mrp, schedule, gst_rate in stock_list:
        discount_pct = rng.choice([0, 5, 10, 12, 15, 20, 25, 30])
        selling_price = round(mrp * (1 - discount_pct / 100), 2)
        stock_qty = rng.randint(5, 200)
        batch_no = f"B{rng.randint(1000,9999)}"
        expiry_date = (datetime.now() + timedelta(days=rng.randint(60, 720))).strftime("%Y-%m-%d")
        conn.execute(
            """INSERT INTO products
               (pharmacy_id, name, brand, category, image_url, mrp, discount_pct, selling_price,
                stock_qty, schedule, gst_rate, batch_no, expiry_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (pid, name, brand, category,
             f"https://placehold.co/300x300/EEEEEE/333333?text={name.split()[0]}",
             mrp, discount_pct, selling_price, stock_qty, schedule, gst_rate, batch_no, expiry_date),
        )

conn.commit()

# ----------------------------------------------------------------------
# Seed: Staff for each pharmacy
# ----------------------------------------------------------------------
staff_names = ["Priya Sharma", "Rahul Deshpande", "Sneha Patil", "Vikram Singh", "Anjali Rao"]
roles = ["Pharmacist", "Cashier", "Delivery Rider", "Manager"]

for pid in pharmacy_id_list:
    for i in range(rng.randint(2, 4)):
        name = rng.choice(staff_names) + f" {rng.randint(1,99)}"
        role = rng.choice(roles)
        salary = {"Pharmacist": 28000, "Cashier": 18000, "Delivery Rider": 15000, "Manager": 35000}[role]
        salary += rng.randint(-2000, 3000)
        joining_date = (datetime.now() - timedelta(days=rng.randint(60, 900))).strftime("%Y-%m-%d")
        conn.execute(
            "INSERT INTO staff (pharmacy_id, name, role, phone, joining_date, monthly_salary) VALUES (?, ?, ?, ?, ?, ?)",
            (pid, name, role, f"98765{rng.randint(10000,99999)}", joining_date, salary),
        )

conn.commit()

# ----------------------------------------------------------------------
# Seed: Sample historical orders (for accounts/balance sheet + reports)
# ----------------------------------------------------------------------
customer_row = conn.execute("SELECT id FROM users WHERE username='customer1'").fetchone()
customer_id = customer_row[0]

payment_modes = ["Cash", "UPI", "Card", "COD"]
delivery_modes = ["Store Pickup", "Own Rider", "Zepto", "Blinkit"]

for pid in pharmacy_id_list:
    products = conn.execute("SELECT id, selling_price, gst_rate, schedule FROM products WHERE pharmacy_id=?", (pid,)).fetchall()
    for _ in range(rng.randint(15, 25)):
        n_items = rng.randint(1, 4)
        chosen = rng.sample(products, k=min(n_items, len(products)))
        subtotal, gst_amount = 0, 0
        order_date = (datetime.now() - timedelta(days=rng.randint(0, 180))).strftime("%Y-%m-%d %H:%M:%S")
        payment_mode = rng.choice(payment_modes)
        payment_status = "Pending" if payment_mode == "COD" and rng.random() < 0.3 else "Paid"
        delivery_mode = rng.choice(delivery_modes)
        delivery_status = rng.choice(["Delivered"] * 6 + ["Out for Delivery", "Placed", "Cancelled"])
        prescription_required = 1 if any(c["schedule"] in ("H", "H1", "X") for c in chosen) else 0

        cur = conn.execute(
            """INSERT INTO orders (customer_id, pharmacy_id, order_date, subtotal, gst_amount, total_amount,
               payment_mode, payment_status, delivery_mode, delivery_status, prescription_required)
               VALUES (?, ?, ?, 0, 0, 0, ?, ?, ?, ?, ?)""",
            (customer_id, pid, order_date, payment_mode, payment_status, delivery_mode, delivery_status, prescription_required),
        )
        order_id = cur.lastrowid

        for c in chosen:
            qty = rng.randint(1, 3)
            line_total = round(c["selling_price"] * qty, 2)
            subtotal += line_total
            gst_amount += line_total * c["gst_rate"] / 100
            conn.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price, line_total) VALUES (?, ?, ?, ?, ?)",
                (order_id, c["id"], qty, c["selling_price"], line_total),
            )

        total_amount = round(subtotal + gst_amount, 2)
        conn.execute(
            "UPDATE orders SET subtotal=?, gst_amount=?, total_amount=? WHERE id=?",
            (round(subtotal, 2), round(gst_amount, 2), total_amount, order_id),
        )

conn.commit()

# ----------------------------------------------------------------------
# Seed: Expenses per pharmacy
# ----------------------------------------------------------------------
expense_categories = ["Rent", "Electricity", "Maintenance", "Marketing", "Misc"]
for pid in pharmacy_id_list:
    for _ in range(rng.randint(4, 8)):
        cat = rng.choice(expense_categories)
        amount = {"Rent": 15000, "Electricity": 3500, "Maintenance": 2000, "Marketing": 4000, "Misc": 1500}[cat]
        amount += rng.randint(-500, 1500)
        exp_date = (datetime.now() - timedelta(days=rng.randint(0, 180))).strftime("%Y-%m-%d")
        conn.execute(
            "INSERT INTO expenses (pharmacy_id, expense_date, category, amount, description) VALUES (?, ?, ?, ?, ?)",
            (pid, exp_date, cat, amount, f"{cat} expense"),
        )

conn.commit()

# ----------------------------------------------------------------------
# Seed: Salary payments (some paid, some pending — for balance sheet)
# ----------------------------------------------------------------------
current_month = datetime.now().strftime("%Y-%m")
prev_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

for pid in pharmacy_id_list:
    staff_rows = conn.execute("SELECT id, monthly_salary FROM staff WHERE pharmacy_id=?", (pid,)).fetchall()
    for s in staff_rows:
        conn.execute(
            "INSERT INTO salary_payments (staff_id, month, amount, status, payment_date) VALUES (?, ?, ?, 'Paid', ?)",
            (s["id"], prev_month, s["monthly_salary"], f"{prev_month}-05"),
        )
        # current month left unpaid intentionally to show as a liability

conn.commit()
conn.close()

print("Database initialized successfully at:", DB_PATH)
print("\nDemo logins:")
print("  Pharmacy owner -> username: shreepharmacy   | password: pharma123")
print("  Pharmacy owner -> username: wellcarepharmacy | password: pharma123")
print("  Pharmacy owner -> username: citymedicos      | password: pharma123")
print("  Customer       -> username: customer1        | password: customer123")
