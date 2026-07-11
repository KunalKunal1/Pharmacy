# MedMarket India — Pharmacy Marketplace Platform
https://mpharmacy.streamlit.app/

An Amazon-style two-sided marketplace for pharmacies in India: pharmacies
register, list products with MRP/discount pricing, and manage their store
(inventory, staff, salary, accounts); customers browse across all pharmacies,
add to cart, and check out with multiple payment and delivery options.

## What's included
- **Landing page** — marketing hero + "why choose us" + Login / Customer
  Register / Pharmacy Register tabs (all before login, like Amazon's homepage)
- **Dual accounts** — separate Pharmacy and Customer roles with different
  dashboards after login
- **Pharmacy dashboard**: My Store (description/logo), Products (add with
  image, brand, MRP, discount % → auto-computed selling price shown with
  strikethrough MRP, exactly like Amazon), Orders, Staff & Salary,
  Accounts & Balance Sheet, Delivery Partner settings
- **Customer dashboard**: Shop (search/filter/browse all pharmacies' products),
  Cart, Checkout (COD/UPI/Card + Store Pickup/Own Rider/Zepto/Blinkit), My Orders
- **India-specific**: GST rates (5/12/18%), Drug Schedule flags (OTC/H/H1/X)
  with a "Prescription required" warning, INR pricing, Indian cities/names

## Important note on Zepto/Blinkit
Zepto and Blinkit **do not offer public developer APIs** for individual
pharmacy integration — those are closed B2B partnerships. The "Delivery
Partners" section **simulates** this integration (order handoff, commission %,
10-20 min SLA) so it demonstrates the correct business logic. Describe this
honestly on your resume as "designed a quick-commerce delivery integration
model" rather than claiming a live API connection.

## Demo logins
```
Pharmacy owner : shreepharmacy    / pharma123
Pharmacy owner : wellcarepharmacy / pharma123
Pharmacy owner : citymedicos      / pharma123
Customer       : customer1        / customer123
```
Note: this uses simple SHA-256 password hashing for demo/learning purposes —
not production-grade security. A real app would use bcrypt/argon2 + salting.

## Tech stack
Python · Streamlit · SQLite · SQL · Pandas

## Project structure
```
pharmacy-marketplace/
├── init_db.py     # creates schema + seeds Indian demo data (run once)
├── db.py          # all database queries (this is where you'll learn SQL)
├── app.py         # Streamlit app: landing page, login, both dashboards
├── requirements.txt
└── data/
    └── pharmacy_marketplace.db   # created by init_db.py
```

## 1. Run locally
```bash
pip install -r requirements.txt
python init_db.py        # creates the database with demo data (run once)
streamlit run app.py     # launches the marketplace
```

## 2. Push to GitHub
```bash
git init
git add .
git commit -m "Pharmacy marketplace platform"
git branch -M main
git remote add origin https://github.com/<your-username>/pharmacy-marketplace.git
git push -u origin main
```
**Important:** the `data/pharmacy_marketplace.db` file will be committed too
— that's fine for a demo since it's small and self-contained. For a real
production app you'd add it to `.gitignore` and use a hosted database instead.

## 3. Get a live, clickable link (Streamlit Community Cloud — free)
1. Go to https://share.streamlit.io and sign in with GitHub.
2. Click **"Create app"** → select this repo → main file `app.py`.
3. Click **Deploy**.

You'll get a public URL like:
```
[https://<your-username>-pharmacy-marketplace.streamlit.app](https://pharmacy-fwhxdvbujhrhremj5sfvv4.streamlit.app/)
```
**Note:** on Streamlit Cloud, the database resets on redeploys/restarts since
it's a local SQLite file, not a persistent hosted database — fine for a demo,
but mention this limitation if asked in an interview.

## 4. Power BI reporting layer (for your resume's Power BI skill)
This app is the *operational* system (day-to-day use). Power BI is for
*analytical* reporting on top of it — export the data and build an exec
dashboard:
1. Run this in Python to export tables for Power BI:
   ```python
   import sqlite3, pandas as pd
   conn = sqlite3.connect("data/pharmacy_marketplace.db")
   pd.read_sql("SELECT * FROM orders", conn).to_csv("export_orders.csv", index=False)
   pd.read_sql("SELECT * FROM products", conn).to_csv("export_products.csv", index=False)
   pd.read_sql("SELECT * FROM expenses", conn).to_csv("export_expenses.csv", index=False)
   ```
2. In Power BI Desktop: **Get Data → Text/CSV** → load each export.
3. Build visuals: Revenue by pharmacy, Discount % vs sales volume, Payment
   mode split (Cash/UPI/Card/COD), Delivery mode split (including
   Zepto/Blinkit share), Attrition-style low-stock/expiry alerts.
4. Add DAX measures like:
   ```dax
   Total Revenue = SUM(orders[total_amount])
   COD Pending = CALCULATE(SUM(orders[total_amount]), orders[payment_status]="Pending")
   ```

## What to learn, in order (matched to what you already know)
You know Python and Java basics. Here's the order that will make the most
sense of this specific project:

1. **SQL** (start here) — open `db.py` and read every query. Learn `SELECT`,
   `WHERE`, `JOIN`, `GROUP BY` by matching each query to what it does in the
   app. This is the fastest way to actually learn SQL — you already have
   working, real-world examples.
2. **Git** — you've already done init/add/commit/push in earlier projects;
   next learn `git branch` and `git merge` so you can build new features
   (e.g. a ratings/reviews system) without breaking the working app.
3. **Power BI** — once the SQL clicks, Power BI's DAX will feel familiar
   since it's basically SQL aggregation with different syntax.
4. **Skip Java for this project** — it would only add complexity here.
   Keep it for DSA/interview prep instead; this app is intentionally
   Python-only so you can move fast.

## Resume bullet
"Built a two-sided pharmacy marketplace platform (Python, Streamlit, SQL)
with separate pharmacy and customer portals — including inventory, staff
payroll, and auto-generated balance sheets for sellers, plus a full
shopping/checkout flow with COD/UPI/Card payments and a simulated
quick-commerce (Zepto/Blinkit) delivery integration for buyers."
