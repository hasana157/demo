"""
ui.py - small helpers and the CSS shared by all pages.
"""

import os
from pathlib import Path

import streamlit as st

from assets_helper import ASSETS_DIR

BASE_DIR = Path(__file__).resolve().parent

RESTAURANT_NAME = "QR Dine Demo Restaurant"
CURRENCY = "$"
MAX_TABLES = 50
KITCHEN_REFRESH_SECONDS = 5

CATEGORY_ICONS = {"burgers": "🍔", "pizza": "🍕", "drinks": "🥤", "desserts": "🍰"}


def money(amount):
    return f"{CURRENCY}{float(amount):,.2f}"


def category_icon(name):
    return CATEGORY_ICONS.get(str(name).strip().lower(), "🍽️")


def get_secret(name, default=""):
    """Read a setting from Streamlit secrets, then environment variables."""
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass  # no secrets file - that's fine
    return os.environ.get(name, default)


def go_to(**params):
    """Callback for buttons: switch page by changing the URL query parameters."""
    st.query_params.clear()
    for key, value in params.items():
        st.query_params[key] = str(value)


def home_button():
    st.button("🏠 Home", key="home_button", on_click=go_to)


def render_image(src):
    """Show a food image from a local path (relative to the project) or a web URL."""
    src = (src or "").strip()
    if src.startswith(("http://", "https://")):
        st.image(src)
        return
    if src:
        path = BASE_DIR / src
        if path.is_file():
            st.image(str(path))
            return
    st.image(str(ASSETS_DIR / "placeholder.png"))


BASE_CSS = """
<style>
#MainMenu, footer {visibility: hidden;}
.stButton > button, .stDownloadButton > button {
    width: 100%; border-radius: 10px; font-weight: 600;
}
.status-pill {
    display: inline-block; padding: 2px 12px; border-radius: 999px;
    color: white; font-weight: 700; font-size: 0.8rem; letter-spacing: .04em;
}
.big-number {font-size: 2rem; font-weight: 800; color: #E4572E; line-height: 1.1;}
.muted {color: #6b7280; font-size: 0.9rem;}
</style>
"""

CUSTOMER_CSS = """
<style>
.block-container {max-width: 520px; padding-top: 1rem; padding-bottom: 4rem;}
/* Keep the - qty + buttons on ONE row even on narrow phone screens */
div[data-testid="stHorizontalBlock"] {flex-wrap: nowrap !important; align-items: center;}
div[data-testid="stHorizontalBlock"] > div {min-width: 0 !important;}
div[data-testid="stImage"] img {width: 100%; border-radius: 12px;}
.brand {
    background: linear-gradient(135deg, #E4572E, #F29E4C); color: white;
    padding: 14px 16px; border-radius: 16px; margin-bottom: 10px;
}
.brand h2 {margin: 0; padding: 0; color: white; font-size: 1.25rem;}
.brand span {opacity: .92; font-size: .9rem;}
.item-name {font-weight: 700; font-size: 1.05rem;}
.price {font-weight: 800; color: #E4572E; font-size: 1.1rem;}
.qty {text-align: center; font-weight: 800; font-size: 1.1rem;}
.cart-banner {
    background: #FFF4EC; border: 1px solid #F6C9A8; color: #7a3a12;
    padding: 8px 12px; border-radius: 10px; margin-bottom: 8px; font-weight: 600;
}
</style>
"""

STAFF_CSS = """
<style>
.block-container {padding-top: 1.2rem; max-width: 1200px;}
.order-head {display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;}
.order-no {font-weight: 800; font-size: 1.2rem;}
.order-items {margin: 6px 0 6px 0; padding-left: 1.1rem;}
.order-items li {margin: 2px 0; font-size: 1rem;}
.order-total {font-weight: 800; font-size: 1.05rem;}

/* Keyed containers: each order card gets a colour by status */
div[class*="st-key-ordnew_"]  {border: 2px solid #ef4444 !important; background: rgba(239,68,68,.08);
                               animation: pulse 1.6s infinite;}
div[class*="st-key-ordprep_"] {border: 2px solid #f59e0b !important; background: rgba(245,158,11,.08);}
div[class*="st-key-ordready_"]{border: 2px solid #10b981 !important; background: rgba(16,185,129,.08);}
div[class*="st-key-orddone_"] {border: 1px solid #9ca3af !important; opacity: .75;}
@keyframes pulse {
    0%   {box-shadow: 0 0 0 0 rgba(239,68,68,.45);}
    70%  {box-shadow: 0 0 0 10px rgba(239,68,68,0);}
    100% {box-shadow: 0 0 0 0 rgba(239,68,68,0);}
}
</style>
"""


def inject_css(view):
    st.markdown(BASE_CSS, unsafe_allow_html=True)
    if view == "customer":
        st.markdown(CUSTOMER_CSS, unsafe_allow_html=True)
    else:
        st.markdown(STAFF_CSS, unsafe_allow_html=True)
