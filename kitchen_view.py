"""
kitchen_view.py - live dashboard for the kitchen.

URL:  https://your-app.streamlit.app/?view=kitchen
The board refreshes itself every few seconds (st.fragment with run_every).
"""

import html
from datetime import datetime

import streamlit as st

import database as db
from ui import KITCHEN_REFRESH_SECONDS, home_button, money

# status -> (CSS class prefix, colour, icon)
STATUS_STYLE = {
    "New": ("ordnew", "#ef4444", "🔴"),
    "Preparing": ("ordprep", "#f59e0b", "🟠"),
    "Ready": ("ordready", "#10b981", "🟢"),
    "Completed": ("orddone", "#6b7280", "⚪"),
}
# status -> (next status, button label)
NEXT_STEP = {
    "New": ("Preparing", "👨‍🍳 Start Preparing"),
    "Preparing": ("Ready", "✅ Mark Ready"),
    "Ready": ("Completed", "🏁 Complete"),
}
FILTERS = {
    "Active orders": ["New", "Preparing", "Ready"],
    "Completed": ["Completed"],
    "All orders": None,
}


def change_status(order_id, new_status):
    """Button callback. Errors are stored and shown on the next refresh."""
    try:
        db.update_order_status(order_id, new_status)
        st.session_state.pop("kitchen_error", None)
    except db.DatabaseError as exc:
        st.session_state["kitchen_error"] = str(exc)


def minutes_ago(created_at):
    try:
        created = datetime.strptime(created_at, db.TIME_FORMAT)
    except ValueError:
        return ""
    minutes = int((db.now_dt() - created).total_seconds() // 60)
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes} min ago"
    return f"{minutes // 60} h {minutes % 60} min ago"


def render_order_card(order):
    prefix, colour, icon = STATUS_STYLE.get(order["status"], STATUS_STYLE["New"])
    with st.container(border=True, key=f"{prefix}_{order['id']}"):
        st.markdown(
            f"<div class='order-head'><span class='order-no'>{order['order_number']}</span>"
            f"<span class='status-pill' style='background:{colour}'>{icon} {order['status'].upper()}</span></div>",
            unsafe_allow_html=True,
        )
        who = f" • {html.escape(order['customer_name'])}" if order["customer_name"] else ""
        st.markdown(
            f"<div class='muted'>🪑 <b>Table {order['table_number']}</b>{who}<br>"
            f"🕒 {order['created_at'][11:16]} ({minutes_ago(order['created_at'])})</div>",
            unsafe_allow_html=True,
        )
        items_html = "".join(
            f"<li><b>{line['quantity']} ×</b> {html.escape(line['name'])}</li>" for line in order["items"]
        )
        st.markdown(f"<ul class='order-items'>{items_html}</ul>", unsafe_allow_html=True)
        st.markdown(f"<div class='order-total'>Total: {money(order['total'])}</div>", unsafe_allow_html=True)

        if order["status"] in NEXT_STEP:
            next_status, label = NEXT_STEP[order["status"]]
            st.button(
                label,
                key=f"next_{order['id']}",
                type="primary" if order["status"] == "New" else "secondary",
                on_click=change_status,
                args=(order["id"], next_status),
            )


@st.fragment(run_every=KITCHEN_REFRESH_SECONDS)
def order_board(filter_name):
    """Re-runs by itself every few seconds without reloading the whole page."""
    statuses = FILTERS[filter_name]
    try:
        counts = db.get_status_counts()
        orders = db.get_orders(
            statuses=statuses,
            ascending=(filter_name == "Active orders"),  # oldest first = first come, first served
            limit=60,
        )
    except db.DatabaseError as exc:
        st.error(f"Could not load orders: {exc}")
        return

    if st.session_state.get("kitchen_error"):
        st.error(st.session_state["kitchen_error"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔴 New", counts["New"])
    c2.metric("🟠 Preparing", counts["Preparing"])
    c3.metric("🟢 Ready", counts["Ready"])
    c4.metric("⚪ Completed", counts["Completed"])

    if counts["New"]:
        st.warning(f"🔔 {counts['New']} new order(s) waiting!")
    st.caption(f"Auto-refreshing every {KITCHEN_REFRESH_SECONDS} seconds • last update {db.now_dt():%H:%M:%S}")

    if not orders:
        st.info("No orders here yet. New orders will appear automatically.")
        return

    columns = st.columns(3)
    for index, order in enumerate(orders):
        with columns[index % 3]:
            render_order_card(order)


def show():
    top_left, top_right = st.columns([1, 5])
    with top_left:
        home_button()
    with top_right:
        st.title("👨‍🍳 Kitchen Dashboard")
    filter_name = st.radio("Show", list(FILTERS), horizontal=True, key="kitchen_filter")
    order_board(filter_name)
