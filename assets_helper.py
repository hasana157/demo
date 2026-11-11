"""
assets_helper.py - creates sample food images with Pillow so the demo works
without downloading anything, and saves images uploaded by the admin.

You can replace any file in the assets/ folder with a real food photo
(keep the same file name) and the app will use it.
"""

import textwrap
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont

import database as db

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
UPLOADS_DIR = ASSETS_DIR / "uploads"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

CATEGORY_COLORS = {
    "Burgers": (214, 106, 41),
    "Pizza": (200, 60, 50),
    "Drinks": (38, 150, 160),
    "Desserts": (170, 80, 140),
}
DEFAULT_COLOR = (90, 110, 130)


def load_font(size):
    """Try a few common bold fonts, then fall back to Pillow's built-in font."""
    for name in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf", "Helvetica.ttc"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow
        return ImageFont.load_default()


def _make_placeholder(path, label, color, size=(640, 420)):
    width, height = size
    img = Image.new("RGB", size, color)
    draw = ImageDraw.Draw(img)

    # Soft vertical gradient (top light, bottom dark)
    for y in range(height):
        shade = int(70 * y / height)
        draw.line([(0, y), (width, y)], fill=tuple(max(c - shade, 0) for c in color))

    # Decorative circles
    draw.ellipse([width - 220, -80, width + 60, 200], fill=tuple(min(c + 35, 255) for c in color))
    draw.ellipse([-80, height - 160, 160, height + 80], fill=tuple(min(c + 25, 255) for c in color))

    font = load_font(52)
    lines = textwrap.wrap(label, width=15) or [label]
    line_height = 64
    y = (height - line_height * len(lines)) // 2
    for line in lines:
        box = draw.textbbox((0, 0), line, font=font)
        x = (width - (box[2] - box[0])) // 2
        draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0))
        draw.text((x, y), line, font=font, fill=(255, 255, 255))
        y += line_height
    img.save(path)


def _make_logo(path):
    size = 256
    img = Image.new("RGB", (size, size), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse([8, 8, size - 8, size - 8], fill=(228, 87, 46))
    font = load_font(96)
    box = draw.textbbox((0, 0), "QD", font=font)
    draw.text(((size - (box[2] - box[0])) // 2, (size - (box[3] - box[1])) // 2 - 10),
              "QD", font=font, fill=(255, 255, 255))
    img.save(path)


def ensure_sample_images():
    """Create any missing sample images. Safe to call on every start."""
    ASSETS_DIR.mkdir(exist_ok=True)
    UPLOADS_DIR.mkdir(exist_ok=True)
    for category, name, _desc, _price, image_file in db.DEMO_MENU:
        path = ASSETS_DIR / image_file
        if not path.exists():
            _make_placeholder(path, name, CATEGORY_COLORS.get(category, DEFAULT_COLOR))
    if not (ASSETS_DIR / "placeholder.png").exists():
        _make_placeholder(ASSETS_DIR / "placeholder.png", "No image", DEFAULT_COLOR)
    if not (ASSETS_DIR / "logo.png").exists():
        _make_logo(ASSETS_DIR / "logo.png")


def save_uploaded_image(uploaded_file):
    """
    Validate and save an image uploaded in the admin page.
    Returns the relative path to store in the database (e.g. 'assets/uploads/abc.jpg').
    Raises ValueError with a friendly message if the file is not a usable image.
    """
    if uploaded_file.size > MAX_UPLOAD_BYTES:
        raise ValueError("Image is too large (max 5 MB).")
    try:
        img = Image.open(uploaded_file)
        img = img.convert("RGB")
    except Exception as exc:
        raise ValueError("That file is not a valid image.") from exc
    img.thumbnail((900, 900))
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    file_name = f"{uuid4().hex}.jpg"
    img.save(UPLOADS_DIR / file_name, "JPEG", quality=85)
    return f"assets/uploads/{file_name}"
