"""
qr_utils.py - builds the table links and QR code images.

A table QR code simply contains a web address such as:
    https://your-app.streamlit.app/?table=3
"""

import io
import zipfile
from urllib.parse import urlencode, urlsplit

import qrcode
from PIL import Image, ImageDraw
from qrcode.constants import ERROR_CORRECT_M

from assets_helper import load_font


def normalize_base_url(raw_url):
    """
    Clean up the app address typed by the admin.
    'my-app.streamlit.app/'  ->  'https://my-app.streamlit.app'
    'localhost:8501'         ->  'http://localhost:8501'
    Raises ValueError if it cannot be understood.
    """
    raw_url = (raw_url or "").strip()
    if not raw_url:
        raise ValueError("Please enter your app URL.")
    if "://" not in raw_url:
        is_local = raw_url.startswith(("localhost", "127.0.0.1", "192.168.", "10."))
        raw_url = ("http://" if is_local else "https://") + raw_url
    parts = urlsplit(raw_url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ValueError("That does not look like a valid web address.")
    return f"{parts.scheme}://{parts.netloc}{parts.path}".rstrip("/")


def table_url(base_url, table_number):
    """Full customer link for one table, e.g. https://app.example.com/?table=3"""
    return f"{normalize_base_url(base_url)}/?{urlencode({'table': int(table_number)})}"


def make_qr_image(url, label=None):
    """Return a PIL image of the QR code, with an optional caption underneath."""
    qr = qrcode.QRCode(
        version=None,  # pick the smallest size that fits
        error_correction=ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").get_image().convert("RGB")

    if not label:
        return img

    caption_height = 80
    canvas = Image.new("RGB", (img.width, img.height + caption_height), "white")
    canvas.paste(img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font = load_font(44)
    box = draw.textbbox((0, 0), label, font=font)
    draw.text(
        ((canvas.width - (box[2] - box[0])) // 2, img.height + 8),
        label,
        font=font,
        fill="black",
    )
    return canvas


def image_to_png_bytes(img):
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def make_table_qr_png(base_url, table_number):
    """PNG bytes of the QR code for one table (with a 'Table N' caption)."""
    img = make_qr_image(table_url(base_url, table_number), label=f"Table {table_number}")
    return image_to_png_bytes(img)


def make_all_qr_zip(base_url, table_count):
    """ZIP file (bytes) containing one PNG per table."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for number in range(1, int(table_count) + 1):
            zf.writestr(f"table_{number}.png", make_table_qr_png(base_url, number))
    return buffer.getvalue()
