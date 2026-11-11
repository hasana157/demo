"""
admin_view.py - restaurant manager dashboard.

URL:  https://your-app.streamlit.app/?view=admin

SECURITY WARNING: the PIN below is a DEMO feature only. It is not real
authentication (no user accounts, no lockout, no encryption of the connection
beyond what the host provides). Do not use it to protect real business data.
"""

import hmac

import pandas as pd
import streamlit as st

import database as db
import qr_utils
from assets_helper import save_uploaded_image
from ui import MAX_TABLES, get_secret, home_button, money, render_image

DEFAULT_PIN = "1234"


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def flash(kind, message):
    """Remember a message so it can be shown after st.rerun()."""
    st.session_state.setdefault("flash", []).append((kind, message))


def show_flash():
    for kind, message in st.session_state.pop("flash", []):
        (st.success if kind == "success" else st.error)(message)


def toggle_availability(item_id):
    """Callback for the 'Available' switch. Saves instantly."""
    try:
        db.set_availability(item_id, st.session_state[f"avail_{item_id}"])
    except db.DatabaseError as exc:
        flash("error", str(exc))


# ---------------------------------------------------------------------------
# Login (demo PIN)
# ---------------------------------------------------------------------------
def login_screen():
    home_button()
    st.title("🔐 Admin login")
    st.warning(
        "**Demo PIN only.** This simple PIN is NOT production-grade security. "
        "A real restaurant app needs proper user accounts, hashed passwords, HTTPS-only access "
        "and login attempt limits."
    )
    expected = get_secret("ADMIN_PIN", DEFAULT_PIN)
    if expected == DEFAULT_PIN:
        st.info("The default demo PIN is **1234**. Change it with the `ADMIN_PIN` secret (see README).")

    with st.form("admin_login"):
        pin = st.text_input("Admin PIN", type="password", max_chars=20)
        submitted = st.form_submit_button("Log in")
    if submitted:
        if hmac.compare_digest(pin.encode(), expected.encode()):
            st.session_state.admin_ok = True
            st.rerun()
        else:
            st.error("Wrong PIN.")


def logout():
    st.session_state.admin_ok = False


# ---------------------------------------------------------------------------
# Tab 1: Menu items
# ---------------------------------------------------------------------------
def tab_menu():
    categories = db.get_categories()
    if not categories:
        st.warning("Please create at least one category in the Categories tab first.")
        return
    cat_names = {c["id"]: c["name"] for c in categories}
    cat_ids = list(cat_names)

    with st.expander("➕ Add a new food item"):
        with st.form("add_item_form", clear_on_submit=True):
            name = st.text_input("Food name", max_chars=60)
            c1, c2 = st.columns(2)
            category_id = c1.selectbox("Category", cat_ids, format_func=cat_names.get)
            price = c2.number_input("Price", min_value=0.0, value=5.0, step=0.5, format="%.2f")
            description = st.text_area("Description", max_chars=200)
            image_text = st.text_input("Image: file path (e.g. assets/pizza.png) or web link (optional)")
            upload = st.file_uploader("...or upload a photo", type=["png", "jpg", "jpeg"])
            available = st.checkbox("Available for customers", value=True)
            submitted = st.form_submit_button("Add item")
        if submitted:
            try:
                image = image_text.strip()
                if upload is not None:
                    image = save_uploaded_image(upload)
                db.add_menu_item(name, description, price, category_id, image, available)
                st.success(f"Added '{name.strip()}'.")
            except (db.DatabaseError, ValueError) as exc:
                st.error(str(exc))

    st.subheader("Current menu")
    show_flash()
    try:
        items = db.get_menu_items()
    except db.DatabaseError as exc:
        st.error(str(exc))
        return
    if not items:
        st.info("No food items yet.")
        return

    for item in items:
        item_id = item["id"]
        icon = "✅" if item["available"] else "⛔"
        with st.expander(f"{icon} {item['name']} · {money(item['price'])} · {item['category_name']}"):
            st.toggle(
                "Available for customers",
                value=bool(item["available"]),
                key=f"avail_{item_id}",
                on_change=toggle_availability,
                args=(item_id,),
            )
            preview_col, form_col = st.columns([1, 2])
            with preview_col:
                render_image(item["image"])
            with form_col:
                with st.form(f"edit_form_{item_id}"):
                    new_name = st.text_input("Name", value=item["name"], max_chars=60)
                    e1, e2 = st.columns(2)
                    new_cat = e1.selectbox(
                        "Category",
                        cat_ids,
                        index=cat_ids.index(item["category_id"]) if item["category_id"] in cat_ids else 0,
                        format_func=cat_names.get,
                    )
                    new_price = e2.number_input("Price", min_value=0.0, value=float(item["price"]), step=0.5, format="%.2f")
                    new_desc = st.text_area("Description", value=item["description"], max_chars=200)
                    new_image = st.text_input("Image path or link", value=item["image"])
                    confirm = st.checkbox("Yes, I want to delete this item")
                    b1, b2 = st.columns(2)
                    save = b1.form_submit_button("💾 Save changes")
                    delete = b2.form_submit_button("🗑️ Delete item")
            if save:
                try:
                    db.update_menu_item(item_id, new_name, new_desc, new_price, new_cat, new_image, item["available"])
                    flash("success", f"Saved '{new_name.strip()}'.")
                    st.rerun()
                except db.DatabaseError as exc:
                    st.error(str(exc))
            if delete:
                if not confirm:
                    st.warning("Tick the confirmation box first, then press Delete.")
                else:
                    try:
                        db.delete_menu_item(item_id)
                        flash("success", f"Deleted '{item['name']}'.")
                        st.rerun()
                    except db.DatabaseError as exc:
                        st.error(str(exc))


# ---------------------------------------------------------------------------
# Tab 2: Categories
# ---------------------------------------------------------------------------
def tab_categories():
    with st.form("add_category_form", clear_on_submit=True):
        new_name = st.text_input("New category name", max_chars=40)
        add = st.form_submit_button("➕ Add category")
    if add:
        try:
            db.add_category(new_name)
            st.success(f"Added category '{new_name.strip()}'.")
        except db.DatabaseError as exc:
            st.error(str(exc))

    show_flash()
    st.subheader("Existing categories")
    for cat in db.get_categories():
        with st.form(f"cat_form_{cat['id']}"):
            c1, c2, c3, c4 = st.columns([3, 1.2, 1.2, 1.2])
            name = c1.text_input("Name", value=cat["name"], max_chars=40, key=f"cat_name_{cat['id']}")
            order = c2.number_input("Order", value=int(cat["sort_order"]), step=1, key=f"cat_order_{cat['id']}")
            c3.markdown(f"<br>{cat['item_count']} item(s)", unsafe_allow_html=True)
            c4.markdown("<br>", unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            save = b1.form_submit_button("💾 Save")
            delete = b2.form_submit_button("🗑️ Delete")
        if save:
            try:
                db.update_category(cat["id"], name, order)
                flash("success", "Category saved.")
                st.rerun()
            except db.DatabaseError as exc:
                st.error(str(exc))
        if delete:
            try:
                db.delete_category(cat["id"])
                flash("success", f"Deleted category '{cat['name']}'.")
                st.rerun()
            except db.DatabaseError as exc:
                st.error(str(exc))


# ---------------------------------------------------------------------------
# Tab 3: Orders
# ---------------------------------------------------------------------------
def tab_orders():
    chosen = st.multiselect("Filter by status", db.ORDER_STATUSES, default=db.ORDER_STATUSES)
    try:
        orders = db.get_orders(statuses=chosen or None, ascending=False)
    except db.DatabaseError as exc:
        st.error(str(exc))
        return
    if not orders:
        st.info("No orders found.")
        return
    rows = [
        {
            "Order": o["order_number"],
            "Table": o["table_number"],
            "Customer": o["customer_name"] or "-",
            "Status": o["status"],
            "Items": ", ".join(f"{l['quantity']}× {l['name']}" for l in o["items"]),
            "Total": money(o["total"]),
            "Placed at": o["created_at"],
        }
        for o in orders
    ]
    st.dataframe(pd.DataFrame(rows), hide_index=True)


# ---------------------------------------------------------------------------
# Tab 4: Sales
# ---------------------------------------------------------------------------
def tab_sales():
    try:
        today = db.get_sales_summary(db.today_str())
        daily = db.get_daily_sales(14)
        top = db.get_top_items(5)
        counts = db.get_status_counts()
    except db.DatabaseError as exc:
        st.error(str(exc))
        return

    st.subheader(f"Today ({db.today_str()})")
    c1, c2, c3 = st.columns(3)
    c1.metric("Orders today", today["orders"])
    c2.metric("Sales today", money(today["revenue"]))
    c3.metric("Average order", money(today["average"]))

    st.subheader("Orders by status (all time)")
    st.dataframe(
        pd.DataFrame({"Status": list(counts), "Orders": list(counts.values())}),
        hide_index=True,
    )

    st.subheader("Daily sales (last 14 days with orders)")
    if daily:
        df = pd.DataFrame(daily).set_index("date")
        st.bar_chart(df["revenue"])
        st.dataframe(
            pd.DataFrame(
                {
                    "Date": df.index,
                    "Orders": df["orders"].values,
                    "Sales": [money(v) for v in df["revenue"]],
                }
            ),
            hide_index=True,
        )
    else:
        st.info("No sales yet. Place a test order from a customer menu.")

    st.subheader("Best sellers")
    if top:
        st.dataframe(
            pd.DataFrame(
                {
                    "Item": [t["item"] for t in top],
                    "Quantity sold": [t["quantity"] for t in top],
                    "Sales": [money(t["revenue"]) for t in top],
                }
            ),
            hide_index=True,
        )
    else:
        st.info("Nothing sold yet.")


# ---------------------------------------------------------------------------
# Tab 5: QR codes
# ---------------------------------------------------------------------------
def tab_qr():
    st.write(
        "Each table gets its own QR code. It opens the customer menu with the table number "
        "already filled in (for example `https://your-app.streamlit.app/?table=3`)."
    )
    default_url = get_secret("APP_URL", "http://localhost:8501")
    raw_url = st.text_input(
        "Your deployed app URL",
        value=default_url,
        help="Paste the address of your deployed app, e.g. https://qr-dine-demo.streamlit.app",
    )
    table_count = st.number_input("Number of tables", min_value=1, max_value=MAX_TABLES, value=6, step=1)

    try:
        base_url = qr_utils.normalize_base_url(raw_url)
    except ValueError as exc:
        st.error(str(exc))
        return

    if any(h in base_url for h in ("localhost", "127.0.0.1")):
        st.warning(
            "This is a local address. It works on your own computer only. "
            "Customers' phones cannot open it. Paste your deployed Streamlit Cloud URL "
            "before printing real QR codes."
        )

    try:
        zip_bytes = qr_utils.make_all_qr_zip(base_url, int(table_count))
    except Exception as exc:  # image/QR problems should never crash the page
        st.error(f"Could not create QR codes: {exc}")
        return
    st.download_button(
        "⬇️ Download all QR codes (ZIP)",
        data=zip_bytes,
        file_name="qr-dine-table-qr-codes.zip",
        mime="application/zip",
        key="qr_zip",
    )

    columns = st.columns(3)
    for number in range(1, int(table_count) + 1):
        url = qr_utils.table_url(base_url, number)
        png = qr_utils.make_table_qr_png(base_url, number)
        with columns[(number - 1) % 3]:
            with st.container(border=True):
                st.image(png)
                st.caption(url)
                st.download_button(
                    f"⬇️ Table {number} PNG",
                    data=png,
                    file_name=f"table_{number}_qr.png",
                    mime="image/png",
                    key=f"qr_dl_{number}",
                )


# ---------------------------------------------------------------------------
# Tab 6: Demo data
# ---------------------------------------------------------------------------
def tab_demo_data():
    st.warning(
        "SQLite on Streamlit Community Cloud is for **demos only**. The app's files can be reset "
        "whenever the app restarts, sleeps, or is redeployed, so orders and menu changes may disappear. "
        "A real restaurant needs a persistent hosted database (for example PostgreSQL) and proper security."
    )
    st.caption(f"Database file: `{db.DB_PATH}`")

    st.subheader("Delete all orders")
    st.write("Keeps your menu, removes every order (useful before a live demo).")
    if st.button("🧹 Delete all orders", key="clear_orders"):
        try:
            db.clear_all_orders()
            st.success("All orders deleted.")
        except db.DatabaseError as exc:
            st.error(str(exc))

    st.subheader("Reset everything to the sample data")
    st.write("Removes ALL orders, categories and food items, then restores the sample menu.")
    with st.form("reset_form"):
        text = st.text_input("Type RESET to confirm")
        go = st.form_submit_button("⚠️ Reset demo data")
    if go:
        if text.strip() == "RESET":
            try:
                db.reset_demo_data()
                st.success("Demo data restored.")
            except db.DatabaseError as exc:
                st.error(str(exc))
        else:
            st.error("Please type RESET exactly to confirm.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def show():
    if not st.session_state.get("admin_ok"):
        login_screen()
        return

    top_left, top_mid, top_right = st.columns([1, 4, 1])
    with top_left:
        home_button()
    with top_mid:
        st.title("🛠️ Admin Dashboard")
    with top_right:
        st.button("Log out", key="logout", on_click=logout)

    tabs = st.tabs(["🍽️ Menu", "🗂️ Categories", "📋 Orders", "📊 Sales", "🔳 QR Codes", "⚙️ Demo data"])
    with tabs[0]:
        tab_menu()
    with tabs[1]:
        tab_categories()
    with tabs[2]:
        tab_orders()
    with tabs[3]:
        tab_sales()
    with tabs[4]:
        tab_qr()
    with tabs[5]:
        tab_demo_data()
