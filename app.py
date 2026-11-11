"""
QR Dine - Restaurant QR Ordering System (beginner demo)

How pages are chosen (using the URL query parameters):
    /?table=3          -> customer menu for table 3   (this is what the QR code opens)
    /?view=kitchen     -> kitchen dashboard
    /?view=admin       -> admin dashboard (demo PIN)
    /                  -> home page with links

Run locally:   streamlit run app.py
"""

import streamlit as st

# set_page_config must be the first Streamlit command in the script.
st.set_page_config(
    page_title="QR Dine",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

import admin_view  # noqa: E402
import customer_view  # noqa: E402
import database as db  # noqa: E402
import kitchen_view  # noqa: E402
from assets_helper import ensure_sample_images  # noqa: E402
from ui import MAX_TABLES, RESTAURANT_NAME, go_to, inject_css  # noqa: E402


@st.cache_resource
def prepare_images():
    """Create sample images once per server start."""
    ensure_sample_images()
    return True


def parse_table(raw_value):
    """Turn '3' into 3. Return None if it is not a valid table number."""
    try:
        number = int(str(raw_value).strip())
    except (TypeError, ValueError):
        return None
    return number if 1 <= number <= MAX_TABLES else None


def home_page():
    st.title(f"🍽️ {RESTAURANT_NAME}")
    st.caption("QR Dine - a demo restaurant QR ordering system")
    st.write(
        "Customers scan a QR code on their table, order from their phone, and the order appears "
        "on the kitchen dashboard in a few seconds."
    )
    left, middle, right = st.columns(3)
    with left:
        with st.container(border=True):
            st.subheader("📱 Customer menu")
            st.write("Open the menu as if you scanned a table's QR code.")
            for table in (1, 2, 3):
                st.button(f"Open Table {table}", key=f"home_table_{table}", on_click=go_to, kwargs={"table": table})
    with middle:
        with st.container(border=True):
            st.subheader("👨‍🍳 Kitchen")
            st.write("Live board of incoming orders.")
            st.button("Open Kitchen Dashboard", key="home_kitchen", on_click=go_to, kwargs={"view": "kitchen"})
    with right:
        with st.container(border=True):
            st.subheader("🛠️ Admin")
            st.write("Menu, orders, sales and QR codes (demo PIN).")
            st.button("Open Admin Dashboard", key="home_admin", on_click=go_to, kwargs={"view": "admin"})

    st.info(
        "Tip: open the customer menu in one browser tab and the kitchen dashboard in another "
        "(or on another device) to watch orders arrive."
    )


def main():
    # Make sure the database and tables exist (adds demo data on the very first run).
    try:
        db.init_db()
    except db.DatabaseError as exc:
        st.error(f"The database could not be started: {exc}")
        st.stop()
    prepare_images()

    view = str(st.query_params.get("view", "")).strip().lower()
    table_raw = st.query_params.get("table")

    if view == "kitchen":
        inject_css("staff")
        kitchen_view.show()
    elif view == "admin":
        inject_css("staff")
        admin_view.show()
    elif table_raw is not None:
        table_number = parse_table(table_raw)
        if table_number is None:
            inject_css("staff")
            st.error(f"Invalid table number. Please use a number from 1 to {MAX_TABLES}.")
            st.button("🏠 Home", key="bad_table_home", on_click=go_to)
        else:
            inject_css("customer")
            customer_view.show(table_number)
    else:
        inject_css("staff")
        home_page()


main()
