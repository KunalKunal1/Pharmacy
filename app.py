

import streamlit as st
import pandas as pd
import runpy
from pathlib import Path
from datetime import datetime

import db

st.set_page_config(page_title="MedMarket India", layout="wide", page_icon="§")

# ----------------------------------------------------------------------
# Auto-initialize the database on first run (e.g. fresh Streamlit Cloud
# deploy where init_db.py was never run manually on the server).
# ----------------------------------------------------------------------
if not db.database_is_initialized():
    with st.spinner("Setting up the database for the first time..."):
        runpy.run_path(str(Path(__file__).parent / "init_db.py"), run_name="__main__")
    st.rerun()

# ----------------------------------------------------------------------
# Session state defaults
# ----------------------------------------------------------------------
for key, default in [("user", None), ("cart", [])]:
    if key not in st.session_state:
        st.session_state[key] = default


def logout():
    st.session_state.user = None
    st.session_state.cart = []
    st.rerun()


# ========================================================================
# LANDING PAGE (not logged in)
# ========================================================================
def landing_page():
    st.markdown(
        """
        <div style="background: linear-gradient(90deg,#0f766e,#0d9488); padding: 40px 30px; border-radius: 10px; color: white;">
            <h1 style="margin:0;"> MedMarket India</h1>
            <h3 style="font-weight:400; margin-top:5px;">Genuine medicines. Real discounts. Delivered fast — from your neighbourhood pharmacy.</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("#### ✅ Licensed Pharmacies")
        st.write("Every store is verified with a valid Drug License & GSTIN before listing.")
    with c2:
        st.markdown("#### 💰 Real MRP Discounts")
        st.write("See the MRP struck through and the actual price you pay — no hidden markup.")
    with c3:
        st.markdown("#### ⚡ Quick Commerce Delivery")
        st.write("Choose 10-30 min delivery via Zepto/Blinkit partners, or your local pharmacy's own rider.")
    with c4:
        st.markdown("#### 📋 Prescription Safety")
        st.write("Schedule H/H1/X medicines are flagged automatically for prescription compliance.")

    st.divider()

    tab_login, tab_customer_reg, tab_pharmacy_reg = st.tabs(
        ["🔐 Login", "🧑 Register as Customer", "🏥 Register your Pharmacy"]
    )

    # ---- Login ----
    with tab_login:
        st.subheader("Log in to your account")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in")
        if submitted:
            user = db.get_user_by_username(username)
            if user and db.verify_password(password, user["password"]):
                st.session_state.user = dict(user)
                st.rerun()
            else:
                st.error("Invalid username or password.")

        st.info(
            "**Demo logins:**\n\n"
          #--- "- Pharmacy: `shreepharmacy` / `pharma123`\n"
           #--- "- Customer: `customer1` / `customer123`" 
        )

    # ---- Customer registration ----
    with tab_customer_reg:
        st.subheader("Create a customer account")
        with st.form("customer_reg_form"):
            full_name = st.text_input("Full name")
            phone = st.text_input("Phone number")
            city = st.text_input("City")
            username = st.text_input("Choose a username")
            password = st.text_input("Choose a password", type="password")
            submitted = st.form_submit_button("Register")
        if submitted:
            if not username or not password:
                st.error("Username and password are required.")
            elif db.get_user_by_username(username):
                st.error("Username already taken.")
            else:
                db.create_user(username, password, "customer", full_name, phone, city)
                st.success("Account created! Please log in from the Login tab.")

    # ---- Pharmacy registration ----
    with tab_pharmacy_reg:
        st.subheader("List your pharmacy on MedMarket")
        with st.form("pharmacy_reg_form"):
            owner_name = st.text_input("Owner full name")
            phone = st.text_input("Phone number")
            city = st.text_input("City")
            store_name = st.text_input("Pharmacy / store name")
            description = st.text_area("Short description of your pharmacy")
            license_no = st.text_input("Drug License number")
            gstin = st.text_input("GSTIN")
            username = st.text_input("Choose a username")
            password = st.text_input("Choose a password", type="password")
            submitted = st.form_submit_button("Register Pharmacy")
        if submitted:
            if not username or not password or not store_name:
                st.error("Username, password, and store name are required.")
            elif db.get_user_by_username(username):
                st.error("Username already taken.")
            else:
                user_id = db.create_user(username, password, "pharmacy", owner_name, phone, city)
                db.create_pharmacy(user_id, store_name, description, license_no, gstin, city)
                st.success("Pharmacy registered! Please log in from the Login tab to add products.")


# ========================================================================
# CUSTOMER SIDE
# ========================================================================
def render_product_card(product, col):
    with col:
        with st.container(border=True):
            st.image(product["image_url"], use_container_width=True)
            st.caption(f"{product['pharmacy_name']} · {product['pharmacy_city']}")
            st.markdown(f"**{product['name']}**")
            st.caption(f"{product['brand']} · {product['category']}")

            if product["discount_pct"] > 0:
                st.markdown(
                    f"~~₹{product['mrp']:.0f}~~ &nbsp; **₹{product['selling_price']:.0f}** "
                    f"&nbsp; <span style='color:#16a34a;font-weight:600;'>{product['discount_pct']:.0f}% OFF</span>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"**₹{product['selling_price']:.0f}**")

            if product["schedule"] in ("H", "H1", "X"):
                st.warning("Prescription required", icon="📋")

            qty = st.number_input("Qty", min_value=1, max_value=int(product["stock_qty"]), value=1, key=f"qty_{product['id']}")
            if st.button("🛒 Add to cart", key=f"add_{product['id']}", use_container_width=True):
                st.session_state.cart.append({
                    "product_id": product["id"], "name": product["name"],
                    "pharmacy_id": product["pharmacy_id"], "pharmacy_name": product["pharmacy_name"],
                    "unit_price": product["selling_price"], "gst_rate": product["gst_rate"],
                    "schedule": product["schedule"], "qty": qty,
                })
                st.success(f"Added {qty} x {product['name']} to cart")


def customer_dashboard(user):
    st.sidebar.success(f"Hi, {user['full_name'] or user['username']} 👋")
    if st.sidebar.button("Log out"):
        logout()

    page = st.sidebar.radio("Menu", ["🛍️ Shop", f"🛒 Cart ({len(st.session_state.cart)})", "📦 My Orders"])

    if page == "🛍️ Shop":
        st.title("🛍️ Shop Medicines")
        c1, c2 = st.columns([3, 1])
        search = c1.text_input("Search medicines or brands", "")
        products = db.get_all_products(search=search or None)
        categories = ["All"] + sorted(set(p["category"] for p in products)) if products else ["All"]
        category = c2.selectbox("Category", categories)
        products = db.get_all_products(search=search or None, category=category)

        if not products:
            st.info("No products found.")
        else:
            cols = st.columns(4)
            for i, product in enumerate(products):
                render_product_card(product, cols[i % 4])

    elif page.startswith("🛒"):
        st.title("🛒 Your Cart")
        if not st.session_state.cart:
            st.info("Your cart is empty. Go to Shop to add medicines.")
        else:
            cart_df = pd.DataFrame(st.session_state.cart)
            cart_df["line_total"] = cart_df["unit_price"] * cart_df["qty"]
            st.dataframe(cart_df[["name", "pharmacy_name", "qty", "unit_price", "line_total"]],
                         use_container_width=True, hide_index=True)

            pharmacies_in_cart = cart_df["pharmacy_id"].nunique()
            if pharmacies_in_cart > 1:
                st.warning("Your cart has items from multiple pharmacies. Checkout will create a separate order per pharmacy.")

            subtotal = cart_df["line_total"].sum()
            st.metric("Subtotal", f"₹{subtotal:,.0f}")

            st.subheader("Checkout")
            payment_mode = st.radio("Payment mode", ["COD", "UPI", "Card"], horizontal=True)
            delivery_mode = st.radio("Delivery mode", ["Store Pickup", "Own Rider", "Zepto", "Blinkit"], horizontal=True)

            eta = {"Store Pickup": "Ready in 15 min", "Own Rider": "Same day",
                   "Zepto": "10-20 min ⚡", "Blinkit": "10-20 min ⚡"}[delivery_mode]
            st.caption(f"Estimated delivery: **{eta}**")

            if st.button("✅ Place Order", type="primary"):
                orders_placed = []
                for pharmacy_id, group in cart_df.groupby("pharmacy_id"):
                    items = group.to_dict("records")
                    order_id, total = db.create_order(user["id"], pharmacy_id, items, payment_mode, delivery_mode)
                    orders_placed.append((order_id, total))
                st.session_state.cart = []
                for oid, total in orders_placed:
                    st.success(f"Order #{oid} placed successfully — ₹{total:,.0f} ({payment_mode})")
                st.balloons()

            if st.button("Clear cart"):
                st.session_state.cart = []
                st.rerun()

    else:  # My Orders
        st.title("📦 My Orders")
        orders = db.get_orders_for_customer(user["id"])
        if not orders:
            st.info("You haven't placed any orders yet.")
        for o in orders:
            with st.expander(f"Order #{o['id']} — {o['pharmacy_name']} — ₹{o['total_amount']:.0f} — {o['delivery_status']}"):
                items = db.get_order_items(o["id"])
                items_df = pd.DataFrame([dict(i) for i in items])
                st.dataframe(items_df[["product_name", "quantity", "unit_price", "line_total"]], hide_index=True)
                c1, c2, c3 = st.columns(3)
                c1.write(f"**Payment:** {o['payment_mode']} ({o['payment_status']})")
                c2.write(f"**Delivery:** {o['delivery_mode']}")
                c3.write(f"**Status:** {o['delivery_status']}")
                if o["prescription_required"]:
                    st.warning("This order contains prescription medicines.")


# ========================================================================
# PHARMACY SIDE
# ========================================================================
def pharmacy_dashboard(user):
    pharmacy = db.get_pharmacy(user["pharmacy_id"])
    st.sidebar.success(f"🏥 {pharmacy['name']}")
    if st.sidebar.button("Log out"):
        logout()

    page = st.sidebar.radio(
        "Menu",
        ["🏠 My Store", "📦 Products", "🧾 Orders", "👥 Staff & Salary",
         "💰 Accounts & Balance Sheet", "🚴 Delivery Partners"],
    )

    if page == "🏠 My Store":
        st.title("🏠 My Store")
        with st.form("store_form"):
            name = st.text_input("Store name", pharmacy["name"])
            description = st.text_area("Description", pharmacy["description"] or "")
            logo_url = st.text_input("Logo URL", pharmacy["logo_url"] or "")
            license_no = st.text_input("Drug License number", pharmacy["license_no"] or "")
            gstin = st.text_input("GSTIN", pharmacy["gstin"] or "")
            city = st.text_input("City", pharmacy["city"] or "")
            if st.form_submit_button("Save changes"):
                db.update_pharmacy(pharmacy["id"], name, description, logo_url, license_no, gstin, city)
                st.success("Store details updated.")
                st.rerun()

    elif page == "📦 Products":
        st.title("📦 Products")
        with st.expander("➕ Add new product"):
            with st.form("add_product_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                name = c1.text_input("Medicine name")
                brand = c2.text_input("Brand")
                category = c1.text_input("Category", "General")
                image_url = c2.text_input("Image URL (optional)", f"https://placehold.co/300x300?text=Medicine")
                mrp = c1.number_input("MRP (₹)", min_value=1.0, value=100.0)
                discount_pct = c2.slider("Discount on MRP (%)", 0, 60, 10)
                stock_qty = c1.number_input("Stock quantity", min_value=0, value=50)
                schedule = c2.selectbox("Drug schedule", ["OTC", "H", "H1", "X"])
                gst_rate = c1.selectbox("GST rate (%)", [5, 12, 18])
                batch_no = c2.text_input("Batch number", "B0001")
                expiry_date = st.date_input("Expiry date")
                if st.form_submit_button("Add product"):
                    db.add_product(pharmacy["id"], name, brand, category, image_url, mrp,
                                    discount_pct, stock_qty, schedule, gst_rate, batch_no, str(expiry_date))
                    st.success(f"Added {name} — selling price ₹{mrp*(1-discount_pct/100):.0f}")
                    st.rerun()

        st.subheader("Your products")
        products = db.get_products_by_pharmacy(pharmacy["id"])
        if not products:
            st.info("No products yet — add your first one above.")
        else:
            for p in products:
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([1, 3, 2, 2])
                    c1.image(p["image_url"], width=70)
                    c2.markdown(f"**{p['name']}** ({p['brand']})")
                    c2.caption(f"Stock: {p['stock_qty']} · Schedule: {p['schedule']} · GST: {p['gst_rate']}%")
                    c3.markdown(f"~~₹{p['mrp']:.0f}~~ → **₹{p['selling_price']:.0f}**")
                    new_discount = c4.slider("Discount %", 0, 60, int(p["discount_pct"]), key=f"disc_{p['id']}")
                    if new_discount != p["discount_pct"]:
                        db.update_product_discount(p["id"], new_discount)
                        st.rerun()

    elif page == "🧾 Orders":
        st.title("🧾 Incoming Orders")
        orders = db.get_orders_for_pharmacy(pharmacy["id"])
        if not orders:
            st.info("No orders yet.")
        for o in orders:
            with st.expander(f"Order #{o['id']} — {o['customer_name']} — ₹{o['total_amount']:.0f} — {o['delivery_status']}"):
                items = db.get_order_items(o["id"])
                items_df = pd.DataFrame([dict(i) for i in items])
                st.dataframe(items_df[["product_name", "quantity", "unit_price", "line_total"]], hide_index=True)
                c1, c2 = st.columns(2)
                with c1:
                    new_status = st.selectbox("Update delivery status", ["Placed", "Packed", "Out for Delivery", "Delivered", "Cancelled"],
                                               index=["Placed", "Packed", "Out for Delivery", "Delivered", "Cancelled"].index(o["delivery_status"]),
                                               key=f"status_{o['id']}")
                    if st.button("Update", key=f"upd_{o['id']}"):
                        db.update_delivery_status(o["id"], new_status)
                        st.rerun()
                with c2:
                    if o["payment_status"] == "Pending":
                        if st.button("Mark COD as Collected", key=f"pay_{o['id']}"):
                            db.update_payment_status(o["id"], "Paid")
                            st.rerun()
                    else:
                        st.write("✅ Payment collected")

    elif page == "👥 Staff & Salary":
        st.title("👥 Staff & Salary")
        with st.expander("➕ Add staff member"):
            with st.form("add_staff_form", clear_on_submit=True):
                name = st.text_input("Name")
                role = st.selectbox("Role", ["Pharmacist", "Cashier", "Delivery Rider", "Manager"])
                phone = st.text_input("Phone")
                joining_date = st.date_input("Joining date")
                salary = st.number_input("Monthly salary (₹)", min_value=0, value=20000)
                if st.form_submit_button("Add staff"):
                    db.add_staff(pharmacy["id"], name, role, phone, str(joining_date), salary)
                    st.success(f"Added {name}")
                    st.rerun()

        staff = db.get_staff(pharmacy["id"])
        if staff:
            staff_df = pd.DataFrame([dict(s) for s in staff])
            st.dataframe(staff_df[["name", "role", "phone", "joining_date", "monthly_salary"]], use_container_width=True, hide_index=True)

            st.subheader("Pay salary")
            staff_names = {s["id"]: s["name"] for s in staff}
            staff_id = st.selectbox("Select staff", list(staff_names.keys()), format_func=lambda x: staff_names[x])
            month = st.text_input("Month (YYYY-MM)", datetime.now().strftime("%Y-%m"))
            selected = next(s for s in staff if s["id"] == staff_id)
            if st.button(f"Pay ₹{selected['monthly_salary']:.0f} to {selected['name']}"):
                db.pay_salary(staff_id, month, selected["monthly_salary"])
                st.success("Salary paid.")
                st.rerun()

        st.subheader("Salary payment history")
        payments = db.get_salary_payments(pharmacy["id"])
        if payments:
            pay_df = pd.DataFrame([dict(p) for p in payments])
            st.dataframe(pay_df[["staff_name", "month", "amount", "status", "payment_date"]], use_container_width=True, hide_index=True)

    elif page == "💰 Accounts & Balance Sheet":
        st.title("💰 Accounts & Balance Sheet")

        orders = db.get_orders_for_pharmacy(pharmacy["id"])
        products = db.get_products_by_pharmacy(pharmacy["id"])
        staff = db.get_staff(pharmacy["id"])
        expenses = db.get_expenses(pharmacy["id"])
        payments = db.get_salary_payments(pharmacy["id"])

        cash_collected = sum(o["total_amount"] for o in orders if o["payment_status"] == "Paid")
        receivables = sum(o["total_amount"] for o in orders if o["payment_status"] == "Pending")
        inventory_value = sum(p["mrp"] * p["stock_qty"] * 0.7 for p in products)  # approx cost basis
        total_expenses = sum(e["amount"] for e in expenses)
        salary_paid = sum(p["amount"] for p in payments if p["status"] == "Paid")
        salary_due = sum(s["monthly_salary"] for s in staff)  # current month owed

        cash = cash_collected - total_expenses - salary_paid
        assets = cash + inventory_value + receivables
        liabilities = salary_due
        equity = assets - liabilities

        c1, c2, c3 = st.columns(3)
        c1.metric("Cash Position", f"₹{cash:,.0f}")
        c2.metric("Inventory Value", f"₹{inventory_value:,.0f}")
        c3.metric("Receivables (COD Pending)", f"₹{receivables:,.0f}")

        st.divider()
        st.subheader("Balance Sheet Summary")
        bs = pd.DataFrame({
            "Item": ["Cash", "Inventory Value", "Receivables (Assets)", "Total Assets",
                     "Salary Due (Liabilities)", "Total Liabilities", "Net Equity"],
            "Amount (₹)": [cash, inventory_value, receivables, assets, liabilities, liabilities, equity],
        })
        st.dataframe(bs, use_container_width=True, hide_index=True)

        st.divider()
        with st.expander("➕ Add expense"):
            with st.form("add_expense_form", clear_on_submit=True):
                exp_date = st.date_input("Date")
                category = st.selectbox("Category", ["Rent", "Electricity", "Maintenance", "Marketing", "Misc"])
                amount = st.number_input("Amount (₹)", min_value=0, value=1000)
                description = st.text_input("Description")
                if st.form_submit_button("Add expense"):
                    db.add_expense(pharmacy["id"], str(exp_date), category, amount, description)
                    st.success("Expense recorded.")
                    st.rerun()

        if expenses:
            st.subheader("Expense history")
            exp_df = pd.DataFrame([dict(e) for e in expenses])
            st.dataframe(exp_df[["expense_date", "category", "amount", "description"]], use_container_width=True, hide_index=True)

    elif page == "🚴 Delivery Partners":
        st.title("🚴 Delivery Partner Settings")
        st.info(
            "⚠️ **Note:** Zepto and Blinkit don't offer public developer APIs for "
            "individual pharmacy integration — this section **simulates** how such "
            "an integration would work operationally (handoff, commission, SLA)."
        )

        st.subheader("Available delivery modes")
        modes = pd.DataFrame([
            {"Partner": "Store Pickup", "SLA": "Ready in 15 min", "Commission": "0%", "Status": "Active"},
            {"Partner": "Own Rider", "SLA": "Same day", "Commission": "0% (staff cost)", "Status": "Active"},
            {"Partner": "Zepto", "SLA": "10-20 min", "Commission": "18-22% per order", "Status": "Simulated"},
            {"Partner": "Blinkit", "SLA": "10-20 min", "Commission": "18-22% per order", "Status": "Simulated"},
        ])
        st.dataframe(modes, use_container_width=True, hide_index=True)

        orders = db.get_orders_for_pharmacy(pharmacy["id"])
        quick_commerce_orders = [o for o in orders if o["delivery_mode"] in ("Zepto", "Blinkit")]
        if quick_commerce_orders:
            total_qc_sales = sum(o["total_amount"] for o in quick_commerce_orders)
            est_commission = total_qc_sales * 0.20
            c1, c2 = st.columns(2)
            c1.metric("Orders via Zepto/Blinkit", len(quick_commerce_orders))
            c2.metric("Estimated commission paid (20%)", f"₹{est_commission:,.0f}")


# ========================================================================
# MAIN ROUTER
# ========================================================================
if st.session_state.user is None:
    landing_page()
elif st.session_state.user["role"] == "customer":
    customer_dashboard(st.session_state.user)
else:
    pharmacy_dashboard(st.session_state.user)
