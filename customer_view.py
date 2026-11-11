"""
customer_view.py - the mobile menu customers see after scanning a table QR code.

URL example:  https://your-app.streamlit.app/?table=3
"""

import html

import streamlit as st

import database as db
from ui import RESTAURANT_NAME, category_icon, money, render_image
from assets_helper import ASSETS_DIR

MAX_QTY = db.MAX_QTY_PER_ITEM


# ---------------------------------------------------------------------------
# Cart helpers (the cart lives in st.session_state, one per browser session)
# ---------------------------------------------------------------------------
def init_state():
    st.session_state.setdefault("cart", {})  # {menu_item_id: quantity}
    st.session_state.setdefault("last_order_id", None)


def change_qty(item_id, delta):
    cart = st.session_state.cart
    new_qty = min(max(cart.get(item_id, 0) + delta, 0), MAX_QTY)
    if new_qty == 0:
        cart.pop(item_id, None)
    else:
        cart[item_id] = new_qty


def remove_item(item_id):
    st.session_state.cart.pop(item_id, None)


def start_new_order():
    st.session_state.last_order_id = None


def clean_cart(items_by_id):
    """Drop items that were deleted or became unavailable since they were added."""
    removed = []
    for item_id in list(st.session_state.cart):
        item = items_by_id.get(item_id)
        if item is None or not item["available"]:
            removed.append(item["name"] if item else "An item")
            st.session_state.cart.pop(item_id)
    if removed:
        st.warning("Removed from your cart (no longer available): " + ", ".join(removed))


def cart_totals(items_by_id):
    count = sum(st.session_state.cart.values())
    total = sum(items_by_id[i]["price"] * q for i, q in st.session_state.cart.items())
    return count, total


# ---------------------------------------------------------------------------
# Page pieces
# ---------------------------------------------------------------------------
def render_header(table_number):
    logo_col, text_col = st.columns([1, 5])
    with logo_col:
        st.image(str(ASSETS_DIR / "logo.png"))
    with text_col:
        st.markdown(
            f"<div class='brand'><h2>{html.escape(RESTAURANT_NAME)}</h2>"
            f"<span>🪑 Table {int(table_number)} &nbsp;•&nbsp; Scan, order, enjoy!</span></div>",
            unsafe_allow_html=True,
        )


def qty_controls(item_id, qty, prefix, with_remove=False):
    cols = st.columns(4 if with_remove else 3)
    cols[0].button("−", key=f"{prefix}_dec_{item_id}", on_click=change_qty, args=(item_id, -1))
    cols[1].markdown(f"<div class='qty'>{qty}</div>", unsafe_allow_html=True)
    cols[2].button("＋", key=f"{prefix}_inc_{item_id}", on_click=change_qty, args=(item_id, 1))
    if with_remove:
        cols[3].button("🗑️", key=f"{prefix}_rm_{item_id}", on_click=remove_item, args=(item_id,))


def render_item_card(item):
    qty = st.session_state.cart.get(item["id"], 0)
    with st.container(border=True):
        render_image(item["image"])
        st.markdown(f"<div class='item-name'>{html.escape(item['name'])}</div>", unsafe_allow_html=True)
        if item["description"]:
            st.caption(item["description"])
        price_col, action_col = st.columns([2, 3])
        price_col.markdown(f"<div class='price'>{money(item['price'])}</div>", unsafe_allow_html=True)
        with action_col:
            if not item["available"]:
                st.markdown("⛔ **Sold out**")
            elif qty == 0:
                st.button("➕ Add to Cart", key=f"add_{item['id']}", on_click=change_qty, args=(item["id"], 1))
            else:
                qty_controls(item["id"], qty, "menu")


def render_category(items, category):
    cat_items = [i for i in items if i["category_id"] == category["id"]]
    if not cat_items:
        st.info("Nothing in this category yet.")
        return
    for item in cat_items:
        render_item_card(item)


def render_cart(items_by_id, table_number):
    cart = st.session_state.cart
    if not cart:
        st.info("Your cart is empty. Add something tasty from the menu! 😋")
        return

    for item_id, qty in cart.items():
        item = items_by_id[item_id]
        with st.container(border=True):
            st.markdown(
                f"<div class='item-name'>{html.escape(item['name'])}</div>"
                f"<div class='muted'>{money(item['price'])} each &nbsp;•&nbsp; "
                f"<b>{money(item['price'] * qty)}</b></div>",
                unsafe_allow_html=True,
            )
            qty_controls(item_id, qty, "cart", with_remove=True)

    _count, total = cart_totals(items_by_id)
    st.markdown(f"### Total: {money(total)}")
    st.text_input("Your name (optional)", key="customer_name", max_chars=40, placeholder="e.g. Ayesha")
    st.caption(f"Your order will be sent to the kitchen for **Table {table_number}**.")

    if st.button("✅ Place Order", type="primary", key="place_order"):
        try:
            result = db.create_order(table_number, st.session_state.get("customer_name", ""), dict(cart))
        except db.DatabaseError as exc:
            st.error(f"Could not place your order: {exc}")
        else:
            st.session_state.cart = {}
            st.session_state.last_order_id = result["id"]
            st.rerun()


# ---------------------------------------------------------------------------
# Order confirmation
# ---------------------------------------------------------------------------
STATUS_PROGRESS = {"New": 0.25, "Preparing": 0.6, "Ready": 0.9, "Completed": 1.0}
STATUS_TEXT = {
    "New": "📨 Order received - waiting for the kitchen",
    "Preparing": "👨‍🍳 The kitchen is preparing your food",
    "Ready": "🛎️ Your order is ready!",
    "Completed": "🏁 Completed - enjoy your meal!",
}


@st.fragment(run_every=10)
def order_status_box(order_id):
    """Refreshes itself every 10 seconds so customers see kitchen progress."""
    try:
        order = db.get_order(order_id)
    except db.DatabaseError as exc:
        st.error(str(exc))
        return
    if order is None:
        st.warning("We could not find this order any more.")
        return
    st.markdown(f"**Status:** {STATUS_TEXT.get(order['status'], order['status'])}")
    st.progress(STATUS_PROGRESS.get(order["status"], 0.25))


def show_confirmation(order_id):
    try:
        order = db.get_order(order_id)
    except db.DatabaseError as exc:
        st.error(str(exc))
        return
    if order is None:
        st.session_state.last_order_id = None
        st.rerun()
        return

    st.success("Thank you! Your order has been sent to the kitchen. 🎉")
    with st.container(border=True):
        st.markdown("<div class='muted'>Your order number</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='big-number'>{order['order_number']}</div>", unsafe_allow_html=True)
        st.markdown(f"🪑 Table {order['table_number']}")
        if order["customer_name"]:
            st.markdown(f"👤 {html.escape(order['customer_name'])}")
        st.divider()
        for line in order["items"]:
            st.markdown(f"{line['quantity']} × {line['name']} — {money(line['unit_price'] * line['quantity'])}")
        st.markdown(f"**Total: {money(order['total'])}**")
        st.divider()
        order_status_box(order_id)
    st.button("🍽️ Order something else", key="order_more", on_click=start_new_order)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def show(table_number):
    init_state()
    render_header(table_number)

    if st.session_state.last_order_id:
        show_confirmation(st.session_state.last_order_id)
        return

    try:
        categories = db.get_categories()
        items = db.get_menu_items()
    except db.DatabaseError as exc:
        st.error(f"Sorry, the menu could not be loaded: {exc}")
        return

    items_by_id = {i["id"]: i for i in items}
    clean_cart(items_by_id)
    count, total = cart_totals(items_by_id)
    if count:
        st.markdown(
            f"<div class='cart-banner'>🛒 {count} item(s) • {money(total)} — "
            f"open the <b>Cart</b> tab to place your order</div>",
            unsafe_allow_html=True,
        )

    # NOTE: tab labels stay constant, otherwise Streamlit jumps back to the first tab.
    labels = [f"{category_icon(c['name'])} {c['name']}" for c in categories] + ["🛒 Cart"]
    tabs = st.tabs(labels)
    for tab, category in zip(tabs, categories):
        with tab:
            render_category(items, category)
    with tabs[-1]:
        render_cart(items_by_id, table_number)
