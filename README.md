# 🍽️ QR Dine – Restaurant QR Ordering System

A beginner-friendly demo built with **Python, Streamlit, SQLite, qrcode and Pillow**.

Customers scan a QR code on their table, order from their phone, and the order appears live on a Kitchen Dashboard. The manager has an Admin dashboard for the menu, orders, sales and QR codes.

| Page | Address | Who uses it |
|---|---|---|
| Home | `/` | Links to everything |
| Customer menu | `/?table=3` | Customers (this is what the QR code opens) |
| Kitchen dashboard | `/?view=kitchen` | Kitchen staff |
| Admin dashboard | `/?view=admin` | Manager (demo PIN) |

> ⚠️ **Demo only.** SQLite on Streamlit Community Cloud is *not* permanent storage, and the admin PIN is *not* real security. See [Production warning](#production-warning).

---

## Project structure

```
qr-dine/
├── app.py               # entry point: picks the page from the URL
├── database.py          # ALL SQLite code (tables, orders, menu, sales)
├── customer_view.py     # mobile menu, cart, order confirmation
├── kitchen_view.py      # live kitchen board
├── admin_view.py        # menu / categories / orders / sales / QR / demo data
├── qr_utils.py          # builds table links and QR code images
├── assets_helper.py     # creates sample images, saves uploaded photos
├── ui.py                # shared styling and small helpers
├── requirements.txt
├── .gitignore
├── .streamlit/
│   ├── config.toml              # theme
│   └── secrets.toml.example     # copy to secrets.toml (local use)
└── assets/              # sample images (auto-created on first run)
```

---

## 1. Run locally

You need Python 3.9 or newer.

```bash
cd qr-dine
python -m venv .venv

# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Your browser opens at <http://localhost:8501>. The database file `qr_dine.db` and the sample food images are created automatically on the first run.

**Admin PIN:** the default is `1234`. To change it locally, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and edit `ADMIN_PIN`.

---

## 2. Test ordering and the kitchen in two browser sessions

1. Start the app (step 1).
2. **Session A (customer):** open <http://localhost:8501/?table=3>.
3. **Session B (kitchen):** open <http://localhost:8501/?view=kitchen> in a *different browser* (or a private/incognito window, or your phone on the same Wi-Fi using `http://YOUR-COMPUTER-IP:8501/?view=kitchen`).
4. In Session A: tap **Add to Cart** on a few items, use **− / ＋**, open the **🛒 Cart** tab, type an optional name, press **Place Order**. You get an order number like `QD-0001`.
5. In Session B: within ~5 seconds the order appears with a pulsing red **NEW** highlight, showing table, items, time and total.
6. In Session B: press **Start Preparing → Mark Ready → Complete**.
7. Back in Session A: the status on the confirmation screen updates by itself (every 10 seconds).

Both sessions see the same orders because they are stored in the SQLite database, not in browser memory.

**Test the admin side:** open `/?view=admin`, log in, then:
- *Menu* tab → add an item, edit a price, flip **Available** off. Reload the customer menu: it shows **Sold out** and cannot be ordered.
- *Orders* / *Sales* tabs → see your test orders and today's totals.
- *QR Codes* tab → see the table codes.

---

## 3. Reset demo data

Admin → **⚙️ Demo data** tab:

- **Delete all orders**: keeps the menu, removes every order.
- **Reset demo data**: type `RESET` to delete *everything* and restore the 12 sample menu items.

Or simply delete the file `qr_dine.db` while the app is stopped; it is recreated with sample data on next start.

---

## 4. Upload the project to GitHub

1. Create a free account at <https://github.com> and click **New repository**. Name it `qr-dine`, choose **Public** (Streamlit Community Cloud's free tier works easily with public repos), and do **not** add a README (you already have one).
2. In your project folder:

```bash
git init
git add .
git commit -m "QR Dine demo"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/qr-dine.git
git push -u origin main
```

3. Check on GitHub that `app.py` is at the **top level** of the repository (not inside another folder). The `.gitignore` already keeps your database and `secrets.toml` out of GitHub.

---

## 5. Deploy on Streamlit Community Cloud

1. Go to <https://share.streamlit.io> and sign in with GitHub.
2. Click **Create app** → **Deploy a public app from GitHub**.
3. Choose your repository, branch `main`, and main file path `app.py`.
4. Open **Advanced settings → Secrets** and paste:

```toml
ADMIN_PIN = "choose-your-own-pin"
APP_URL = "https://your-app-name.streamlit.app"
```

   (Use the real URL once you know it; you can edit secrets later in *App settings → Secrets*.)
5. Order times use the time zone set by `TIMEZONE_NAME` in `database.py` (default `Asia/Karachi`). Change it to your own IANA name such as `America/New_York` *before* pushing to GitHub.
6. Click **Deploy**. The first build takes a minute or two.

---

## 6. Generate QR codes after deployment

1. Open `https://your-app-name.streamlit.app/?view=admin` and log in with your PIN.
2. Go to **🔳 QR Codes**.
3. Paste your deployed URL (or set `APP_URL` in Secrets so it is pre-filled).
4. Choose the number of tables.
5. Download **all codes as a ZIP** or each table's PNG, print them and place one on each table.
6. **Test one with your phone camera** before printing the whole batch. Table 3's code opens `https://your-app-name.streamlit.app/?table=3`.

If you change the app URL later, the old QR codes stop working; regenerate and reprint.

---

## Common errors and solutions

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: No module named 'streamlit'` (or `qrcode`, `PIL`) | Activate your virtual environment and run `pip install -r requirements.txt`. |
| `streamlit: command not found` | Use `python -m streamlit run app.py`. |
| Port 8501 already in use | `streamlit run app.py --server.port 8502`. |
| Phone can't open `localhost` QR codes | `localhost` only exists on your own computer. Deploy the app and use the deployed URL in the QR tab. |
| Streamlit Cloud: `ModuleNotFoundError` after deploy | Make sure `requirements.txt` is in the repo root and spelled correctly, then reboot the app. |
| Streamlit Cloud: "file not found: app.py" | `app.py` must be at the repository top level, or set the correct path when deploying. |
| Orders/menu changes vanished | Expected on Streamlit Community Cloud: the app's disk is temporary (restart, sleep or redeploy resets it). Use a persistent database for real use. |
| App is "asleep" when a customer scans | Free apps sleep after inactivity. Open the app before service, or use a paid host. |
| Order times are wrong | Cloud servers use UTC. Change `TIMEZONE_NAME` in `database.py`. |
| Forgot admin PIN | Local: check `.streamlit/secrets.toml` (default `1234`). Cloud: *App settings → Secrets*. |
| `database is locked` | Rare with SQLite under load. Retry; for many simultaneous users move to PostgreSQL. |
| Sold-out/removed item in cart | The menu automatically removes such items from the cart and shows a notice. |
| Kitchen board not updating | Check the "last update" time under the counters; refresh the page. Auto-refresh needs a working connection. |
| Uploaded food photo disappears after restart | Same temporary-disk limitation. Use an image web link or commit photos into `assets/` in GitHub. |

**Using your own food photos:** replace any file in `assets/` (keep the file name), or in Admin → Menu paste an image web link, or upload a photo (demo-only storage).

---

## How it works (for learning)

- **Routing:** `app.py` reads `st.query_params`. `?table=3` → customer view, `?view=kitchen` → kitchen, `?view=admin` → admin.
- **Database:** `database.py` holds every SQL statement, always with `?` placeholders (no SQL injection). Each call opens a short-lived connection, so many browser sessions can share the one file safely.
- **Order totals** are computed on the server from database prices, so a customer can't tamper with prices.
- **Order history** copies the item name and price at order time, so editing or deleting a menu item never changes old orders.
- **Live updates:** the kitchen uses `@st.fragment(run_every=5)` to re-read the database every 5 seconds without reloading the page.
- **Cart:** lives in `st.session_state` (per customer browser) until the order is placed, then it is saved to the database.

---

## Production warning

This is a **learning demo**, not a system to run a real restaurant:

- **Data is not permanent on Streamlit Community Cloud.** SQLite stores data in a file on a temporary disk. Restarts, sleep, redeploys or platform maintenance can erase orders, menu edits and uploads. Do not rely on it for real orders or sales records.
- **The admin PIN is not real security.** It is a single shared PIN with no accounts, no login-attempt limits, and the kitchen page has no protection at all. Anyone who knows the `?view=kitchen` link can change order statuses.
- **A real deployment needs:** a persistent hosted database (for example PostgreSQL), proper staff accounts with hashed passwords and roles, HTTPS everywhere, rate limiting, backups, payment handling by a certified provider if you take payments, and compliance with local food-business and privacy rules.
- Anyone who can open a table link can place an order for that table. A real system would add measures against prank or fake orders.
