# -*- coding: utf-8 -*-
# TASTE AND SIP - Single file app (Tkinter + SQLite + PIL + ReportLab)
# Features: Auth, Customer Shop (sizes/sweetness/toppings), Cart+Promo, QR pay, Receipt PDF,
# Inventory (BOM) deduction, Order history, Admin (Products with image upload, Inventory, Promotions, Reports)

import os, sys, json, sqlite3, hashlib, shutil, datetime
from datetime import datetime as dt, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.units import mm

APP_TITLE = "TASTE AND SIP"
DB_FILE   = "taste_and_sip.db"

# Assets
ASSETS_DIR          = "assets"
IMG_PRODUCTS_DIR    = os.path.join(ASSETS_DIR, "images", "products")
IMG_QR_PATH         = os.path.join(ASSETS_DIR, "images", "qr.png")
IMG_AVATARS_DIR     = os.path.join(ASSETS_DIR, "avatars")
REPORTS_DIR         = "reports"

# --- Utilities ---
def ensure_dirs():
    for p in [ASSETS_DIR, IMG_PRODUCTS_DIR, IMG_AVATARS_DIR, REPORTS_DIR, os.path.join(ASSETS_DIR, "images")]:
        os.makedirs(p, exist_ok=True)

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def now_ts():
    return dt.now().strftime("%Y-%m-%d %H:%M:%S")

def load_image(path, size=(180, 140)):
    """Load image with PIL; return PhotoImage or None."""
    try:
        if os.path.exists(path):
            img = Image.open(path).convert("RGBA")
            img = img.resize(size, Image.LANCZOS)
            return ImageTk.PhotoImage(img)
    except Exception:
        return None
    return None

# --- Database Layer ---
class AppDB:
    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.init_schema()
        self.seed_minimum()

    def init_schema(self):
        c = self.conn.cursor()
        # Users (add role + profile fields)
        c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT, phone TEXT, email TEXT, birthdate TEXT, gender TEXT, avatar TEXT,
            role TEXT DEFAULT 'customer'
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)""")

        c.execute("""
        CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, category_id INTEGER, base_price REAL,
            image TEXT, is_active INTEGER DEFAULT 1
        )""")

        c.execute("""
        CREATE TABLE IF NOT EXISTS product_options(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            option_name TEXT,
            option_values_json TEXT
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS toppings(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, price REAL, is_active INTEGER DEFAULT 1
        )""")

        c.execute("""
        CREATE TABLE IF NOT EXISTS inventory_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, unit TEXT, qty_on_hand REAL DEFAULT 0,
            reorder_level REAL DEFAULT 0, cost_per_unit REAL DEFAULT 0
        )""")

        c.execute("""
        CREATE TABLE IF NOT EXISTS bom_links(
            product_id INTEGER, inventory_item_id INTEGER, qty_per_unit REAL,
            PRIMARY KEY(product_id, inventory_item_id)
        )""")

        c.execute("""
        CREATE TABLE IF NOT EXISTS promotions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE, type TEXT, value REAL,
            min_spend REAL DEFAULT 0,
            start_at TEXT, end_at TEXT,
            is_active INTEGER DEFAULT 1
        )""")

        c.execute("""
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, order_datetime TEXT,
            channel TEXT, pickup_time TEXT,
            subtotal REAL, discount REAL, total REAL,
            payment_method TEXT, status TEXT
        )""")

        c.execute("""
        CREATE TABLE IF NOT EXISTS order_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER, product_id INTEGER,
            qty INTEGER, unit_price REAL, options_json TEXT, note TEXT
        )""")

        c.execute("""
        CREATE TABLE IF NOT EXISTS order_item_toppings(
            order_item_id INTEGER, topping_id INTEGER, qty INTEGER, price REAL
        )""")

        c.execute("""
        CREATE TABLE IF NOT EXISTS payments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER, method TEXT, amount REAL, paid_at TEXT, ref TEXT
        )""")

        c.execute("""
        CREATE TABLE IF NOT EXISTS stock_movements(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inventory_item_id INTEGER, change_qty REAL, reason TEXT, ref_id INTEGER, created_at TEXT
        )""")

        self.conn.commit()

    def seed_minimum(self):
        c = self.conn.cursor()
        # Admin account
        c.execute("SELECT id FROM users WHERE username='admin'")
        if not c.fetchone():
            c.execute("INSERT INTO users(username, password_hash, name, role) VALUES(?,?,?,?)",
                      ('admin', sha256('admin123'), 'Administrator', 'admin'))

        # Categories
        c.execute("SELECT COUNT(*) AS n FROM categories")
        if c.fetchone()['n'] == 0:
            c.executemany("INSERT INTO categories(name) VALUES(?)",
                          [('FOOD',), ('DRINK',), ('DESSERT',)])

        # Toppings
        c.execute("SELECT COUNT(*) AS n FROM toppings")
        if c.fetchone()['n'] == 0:
            c.executemany("INSERT INTO toppings(name, price) VALUES(?,?)",
                          [('Pearl', 10), ('Pudding', 12), ('Grass Jelly', 8), ('Whip Cream', 7)])

        # Sample products
        c.execute("SELECT COUNT(*) AS n FROM products")
        if c.fetchone()['n'] == 0:
            # Find category ids
            cats = {row['name']: row['id'] for row in c.execute("SELECT * FROM categories")}
            samples = [
                ('Pad Thai', cats.get('FOOD'), 60.0, '', 1),
                ('Thai Milk Tea', cats.get('DRINK'), 35.0, '', 1),
                ('Mango Sticky Rice', cats.get('DESSERT'), 50.0, '', 1),
            ]
            c.executemany("INSERT INTO products(name, category_id, base_price, image, is_active) VALUES(?,?,?,?,?)",
                          samples)

        # Product options: sizes & sweetness presets (only once)
        # sizes with multipliers for price
        size_values = {"values": ["S", "M", "L"], "price_multipliers": {"S": 1.0, "M": 1.2, "L": 1.5}}
        sweet_values = {"values": ["0%", "25%", "50%", "75%", "100%"]}
        for prod in c.execute("SELECT id FROM products").fetchall():
            pid = prod['id']
            # create if not exists
            for name, obj in [('Size', size_values), ('Sweetness', sweet_values)]:
                r = c.execute("SELECT 1 FROM product_options WHERE product_id=? AND option_name=?", (pid, name)).fetchone()
                if not r:
                    c.execute("INSERT INTO product_options(product_id, option_name, option_values_json) VALUES(?,?,?)",
                              (pid, name, json.dumps(obj)))

        # Inventory & BOM (very lightweight)
        c.execute("SELECT COUNT(*) AS n FROM inventory_items")
        if c.fetchone()['n'] == 0:
            inv_examples = [
                ('Noodles', 'g', 5000, 500, 0.05),
                ('Tea Leaves', 'g', 3000, 300, 0.04),
                ('Milk', 'ml', 5000, 800, 0.02),
                ('Mango', 'g', 2000, 300, 0.06),
                ('Sticky Rice', 'g', 3000, 400, 0.03),
            ]
            c.executemany("INSERT INTO inventory_items(name, unit, qty_on_hand, reorder_level, cost_per_unit) VALUES(?,?,?,?,?)",
                          inv_examples)

            # BOM links (approx)
            # Map product name -> required items
            product_ids = {row['name']: row['id'] for row in c.execute("SELECT id,name FROM products")}
            inv_ids = {row['name']: row['id'] for row in c.execute("SELECT id,name FROM inventory_items")}

            bom_seed = [
                (product_ids.get('Pad Thai'), inv_ids.get('Noodles'), 120),
                (product_ids.get('Thai Milk Tea'), inv_ids.get('Tea Leaves'), 8),
                (product_ids.get('Thai Milk Tea'), inv_ids.get('Milk'), 180),
                (product_ids.get('Mango Sticky Rice'), inv_ids.get('Mango'), 150),
                (product_ids.get('Mango Sticky Rice'), inv_ids.get('Sticky Rice'), 120),
            ]
            for x in bom_seed:
                if all(x):
                    c.execute("INSERT OR REPLACE INTO bom_links(product_id, inventory_item_id, qty_per_unit) VALUES(?,?,?)", x)

        # Promotions demo
        c.execute("SELECT COUNT(*) AS n FROM promotions")
        if c.fetchone()['n'] == 0:
            today = dt.now()
            start = (today - timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
            end   = (today + timedelta(days=365)).strftime("%Y-%m-%d 23:59:59")
            promos = [
                ('WELCOME10', 'PERCENT_BILL', 10, 0, start, end, 1),
                ('FLAT20',    'FLAT_BILL',    20, 100, start, end, 1),
            ]
            c.executemany("INSERT INTO promotions(code, type, value, min_spend, start_at, end_at, is_active) VALUES(?,?,?,?,?,?,?)", promos)

        self.conn.commit()

    # --- User/Auth ---
    def create_user(self, username, password, role='customer'):
        try:
            self.conn.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                              (username, sha256(password), role))
            self.conn.commit()
            return True, "Account created."
        except sqlite3.IntegrityError:
            return False, "Username already exists."

    def auth_user(self, username, password):
        row = self.conn.execute("SELECT * FROM users WHERE username=? AND password_hash=?",
                                (username, sha256(password))).fetchone()
        return row

    def set_user_profile(self, uid, **kwargs):
        cols = []
        vals = []
        for k, v in kwargs.items():
            cols.append(f"{k}=?"); vals.append(v)
        if not cols: return
        vals.append(uid)
        self.conn.execute(f"UPDATE users SET {', '.join(cols)} WHERE id=?", vals)
        self.conn.commit()

    # --- Catalog ---
    def get_categories(self):
        return self.conn.execute("SELECT * FROM categories").fetchall()

    def list_products_by_category(self, category_id):
        return self.conn.execute("SELECT * FROM products WHERE category_id=? AND is_active=1", (category_id,)).fetchall()

    def get_product_options(self, product_id):
        rows = self.conn.execute("SELECT * FROM product_options WHERE product_id=?", (product_id,)).fetchall()
        out = {}
        for r in rows:
            out[r['option_name']] = json.loads(r['option_values_json'] or "{}")
        return out

    def list_toppings(self):
        return self.conn.execute("SELECT * FROM toppings WHERE is_active=1").fetchall()

    # --- Promotions ---
    def find_promo(self, code):
        row = self.conn.execute("SELECT * FROM promotions WHERE code=? AND is_active=1", (code,)).fetchone()
        if not row: return None
        now = dt.now()
        try:
            st = dt.strptime(row['start_at'], "%Y-%m-%d %H:%M:%S")
            ed = dt.strptime(row['end_at'], "%Y-%m-%d %H:%M:%S")
        except:
            # accept if parse fails
            st = now - timedelta(days=1); ed = now + timedelta(days=3650)
        if now < st or now > ed:
            return None
        return row

    # --- Inventory/BOM ---
    def bom_for_product(self, product_id):
        return self.conn.execute("SELECT * FROM bom_links WHERE product_id=?", (product_id,)).fetchall()

    def deduct_inventory_for_order(self, order_id):
        # sum per inventory item
        items = self.conn.execute("""
        SELECT oi.product_id, oi.qty, bl.inventory_item_id, bl.qty_per_unit
        FROM order_items oi
        JOIN bom_links bl ON bl.product_id = oi.product_id
        WHERE oi.order_id=?""", (order_id,)).fetchall()

        mv = self.conn.cursor()
        for r in items:
            dec = (r['qty'] * float(r['qty_per_unit']))
            mv.execute("UPDATE inventory_items SET qty_on_hand = qty_on_hand - ? WHERE id=?",
                       (dec, r['inventory_item_id']))
            mv.execute("INSERT INTO stock_movements(inventory_item_id, change_qty, reason, ref_id, created_at) VALUES(?,?,?,?,?)",
                       (r['inventory_item_id'], -dec, 'SALE', order_id, now_ts()))
        self.conn.commit()

    # --- Orders ---
    def create_order(self, user_id, channel, pickup_time, cart_items, promo_row, payment_method, pay_amount):
        """
        cart_items: list of dict{
            product_id, name, base_price, size, sweetness, toppings:[(id,name,price,qty)], qty, note
        }
        promo_row may be None
        """
        subtotal = 0.0
        for it in cart_items:
            # base price * size multiplier + toppings
            size_mult = 1.0
            if it.get('size') and isinstance(it['size'], str):
                # use product_options multipliers, fallback to defaults
                size_mult = {"S":1.0, "M":1.2, "L":1.5}.get(it['size'], 1.0)
            line_base = it['base_price'] * size_mult
            toppings_total = sum(t['price'] * t.get('qty',1) for t in it.get('toppings', []))
            subtotal += (line_base + toppings_total) * it['qty']

        discount = 0.0
        if promo_row:
            if subtotal >= float(promo_row['min_spend']):
                if promo_row['type'] == 'PERCENT_BILL':
                    discount = subtotal * (float(promo_row['value'])/100.0)
                elif promo_row['type'] == 'FLAT_BILL':
                    discount = float(promo_row['value'])
            discount = min(discount, subtotal)

        total = max(0.0, subtotal - discount)

        cur = self.conn.cursor()
        cur.execute("""INSERT INTO orders(user_id, order_datetime, channel, pickup_time, subtotal, discount, total, payment_method, status)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (user_id, now_ts(), channel, pickup_time or "", subtotal, discount, total, payment_method, 'PAID'))
        order_id = cur.lastrowid

        for it in cart_items:
            options = {"Size": it.get('size'), "Sweetness": it.get('sweetness')}
            cur.execute("""INSERT INTO order_items(order_id, product_id, qty, unit_price, options_json, note)
                           VALUES(?,?,?,?,?,?)""",
                        (order_id, it['product_id'], it['qty'], it['base_price'], json.dumps(options), it.get('note','')))
            oi_id = cur.lastrowid
            for tp in it.get('toppings', []):
                cur.execute("INSERT INTO order_item_toppings(order_item_id, topping_id, qty, price) VALUES(?,?,?,?)",
                            (oi_id, tp['id'], tp.get('qty',1), tp['price']))

        # Payment row
        cur.execute("INSERT INTO payments(order_id, method, amount, paid_at, ref) VALUES(?,?,?,?,?)",
                    (order_id, payment_method, total, now_ts(), ""))
        self.conn.commit()

        # Deduct inventory
        self.deduct_inventory_for_order(order_id)
        return order_id, subtotal, discount, total

    def list_orders_of_user(self, uid, limit=50):
        return self.conn.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ?",
                                 (uid, limit)).fetchall()

    def order_detail(self, order_id):
        order = self.conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        items = self.conn.execute("""SELECT oi.*, p.name AS product_name
                                     FROM order_items oi JOIN products p ON p.id=oi.product_id
                                     WHERE order_id=?""", (order_id,)).fetchall()
        tps = self.conn.execute("""SELECT oit.*, t.name AS topping_name
                                   FROM order_item_toppings oit
                                   JOIN toppings t ON t.id=oit.topping_id
                                   WHERE oit.order_item_id IN (SELECT id FROM order_items WHERE order_id=?)""",
                                (order_id,)).fetchall()
        return order, items, tps

    # --- Admin helpers ---
    def list_products(self):
        return self.conn.execute("""SELECT p.*, c.name AS category_name
                                    FROM products p LEFT JOIN categories c ON c.id=p.category_id
                                    ORDER BY p.id DESC""").fetchall()

    def upsert_product(self, pid, name, cat_id, base_price, image, is_active):
        cur = self.conn.cursor()
        if pid:
            cur.execute("""UPDATE products SET name=?, category_id=?, base_price=?, image=?, is_active=? WHERE id=?""",
                        (name, cat_id, base_price, image, is_active, pid))
        else:
            cur.execute("""INSERT INTO products(name, category_id, base_price, image, is_active) VALUES(?,?,?,?,?)""",
                        (name, cat_id, base_price, image, is_active))
        self.conn.commit()

    def delete_product(self, pid):
        self.conn.execute("DELETE FROM products WHERE id=?", (pid,))
        self.conn.commit()

    def list_inventory(self):
        return self.conn.execute("SELECT * FROM inventory_items ORDER BY id DESC").fetchall()

    def adjust_inventory(self, inv_id, delta, reason='ADJUST', ref_id=None):
        cur = self.conn.cursor()
        cur.execute("UPDATE inventory_items SET qty_on_hand = qty_on_hand + ? WHERE id=?", (delta, inv_id))
        cur.execute("""INSERT INTO stock_movements(inventory_item_id, change_qty, reason, ref_id, created_at)
                       VALUES(?,?,?,?,?)""",(inv_id, delta, reason, ref_id or 0, now_ts()))
        self.conn.commit()

    def list_promotions(self):
        return self.conn.execute("SELECT * FROM promotions ORDER BY id DESC").fetchall()

    def upsert_promotion(self, pid, code, ptype, value, min_spend, start_at, end_at, is_active):
        cur = self.conn.cursor()
        if pid:
            cur.execute("""UPDATE promotions SET code=?, type=?, value=?, min_spend=?, start_at=?, end_at=?, is_active=? WHERE id=?""",
                        (code, ptype, value, min_spend, start_at, end_at, is_active, pid))
        else:
            cur.execute("""INSERT INTO promotions(code, type, value, min_spend, start_at, end_at, is_active)
                           VALUES(?,?,?,?,?,?,?)""", (code, ptype, value, min_spend, start_at, end_at, is_active))
        self.conn.commit()

    def delete_promotion(self, pid):
        self.conn.execute("DELETE FROM promotions WHERE id=?", (pid,))
        self.conn.commit()

    def report_total_by_date(self, start_date, end_date):
        return self.conn.execute("""
            SELECT substr(order_datetime,1,10) AS d, SUM(total) AS total
            FROM orders
            WHERE order_datetime BETWEEN ? AND ?
            GROUP BY d ORDER BY d
        """, (start_date+" 00:00:00", end_date+" 23:59:59")).fetchall()

# --- PDF Receipt ---
def create_receipt_pdf(order_id, db: AppDB, user_row):
    ensure_dirs()
    path = os.path.join(REPORTS_DIR, f"receipt_{order_id}.pdf")
    c = pdfcanvas.Canvas(path, pagesize=A4)
    W, H = A4
    left = 18*mm
    top = H - 18*mm
    line = top

    order, items, tps = db.order_detail(order_id)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left, line, "TASTE AND SIP - RECEIPT")
    line -= 10*mm
    c.setFont("Helvetica", 10)
    c.drawString(left, line, f"Order ID: {order_id}")
    line -= 5*mm
    c.drawString(left, line, f"Date/Time: {order['order_datetime']}")
    line -= 5*mm
    c.drawString(left, line, f"Customer: {user_row['name'] or user_row['username']}")
    line -= 8*mm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, line, "Items")
    line -= 6*mm
    c.setFont("Helvetica", 10)

    # items
    cur_y = line
    total_toppings = 0.0
    for it in items:
        opts = json.loads(it['options_json'] or "{}")
        line_text = f"- {it['product_name']} x{it['qty']}  (Base: {it['unit_price']:.2f})"
        c.drawString(left, cur_y, line_text); cur_y -= 5*mm
        size = opts.get('Size'); sweet = opts.get('Sweetness')
        c.drawString(left+8*mm, cur_y, f"Size: {size or '-'}, Sweetness: {sweet or '-'}"); cur_y -= 5*mm
        # toppings for this order_item:
        for tp in tps:
            if tp['order_item_id'] == it['id']:
                c.drawString(left+8*mm, cur_y, f"Topping: {tp['topping_name']} x{tp['qty']} @ {tp['price']:.2f}")
                total_toppings += tp['price'] * tp['qty']; cur_y -= 5*mm
        if it['note']:
            c.drawString(left+8*mm, cur_y, f"Note: {it['note']}"); cur_y -= 5*mm
        cur_y -= 2*mm

    cur_y -= 3*mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left, cur_y, f"Subtotal: {order['subtotal']:.2f}    Discount: {order['discount']:.2f}    Total: {order['total']:.2f}")
    cur_y -= 8*mm
    c.setFont("Helvetica", 10)
    c.drawString(left, cur_y, f"Channel: {order['channel']}  Pickup: {order['pickup_time'] or '-'}  Payment: {order['payment_method']}")
    cur_y -= 10*mm

    # QR image (if exists)
    if os.path.exists(IMG_QR_PATH):
        try:
            c.drawImage(IMG_QR_PATH, left, cur_y-45*mm, width=40*mm, height=40*mm, preserveAspectRatio=True, mask='auto')
            c.drawString(left+45*mm, cur_y-5*mm, "Scan to pay (display only)")
        except:
            c.drawString(left, cur_y, "QR image error.")
    else:
        c.drawString(left, cur_y, "QR Placeholder: put image at assets/images/qr.png")
    c.showPage(); c.save()
    return path

# --- UI Components ---
class ProductCard(ttk.Frame):
    def __init__(self, master, product_row, on_configure):
        super().__init__(master, padding=6)
        self.row = product_row
        self.on_configure = on_configure
        self.configure(style="Card.TFrame")

        img_frame = ttk.Frame(self)
        img_frame.pack()
        img = load_image(self.row['image'] or "", (160, 120))
        if img:
            lbl = ttk.Label(img_frame, image=img)
            lbl.image = img
            lbl.pack()
        else:
            ttk.Label(img_frame, text="[No Image]", width=22, anchor="center").pack()

        ttk.Label(self, text=self.row['name'], style="Title.TLabel").pack(pady=(6,0))
        ttk.Label(self, text=f"{self.row['base_price']:.2f} ฿", style="Price.TLabel").pack()
        ttk.Button(self, text="Customize + Add", command=self.open_config).pack(pady=4)

    def open_config(self):
        self.on_configure(self.row)

class ProductConfigDialog(tk.Toplevel):
    def __init__(self, master, db: AppDB, product_row, toppings, on_add_to_cart):
        super().__init__(master)
        self.title(f"Customize - {product_row['name']}")
        self.db = db
        self.product = product_row
        self.toppings = toppings
        self.on_add = on_add_to_cart
        self.result = None
        self.geometry("420x520")
        self.resizable(False, False)

        opts = db.get_product_options(product_row['id'])
        size_obj = opts.get('Size', {"values": ["S","M","L"], "price_multipliers":{"S":1.0,"M":1.2,"L":1.5}})
        sweet_obj = opts.get('Sweetness', {"values": ["0%","25%","50%","75%","100%"]})

        frm = ttk.Frame(self, padding=10); frm.pack(fill="both", expand=True)

        # Size
        ttk.Label(frm, text="Size").pack(anchor="w")
        self.size_var = tk.StringVar(value=size_obj['values'][0])
        ttk.Combobox(frm, values=size_obj['values'], textvariable=self.size_var, state="readonly").pack(fill="x", pady=4)

        # Sweetness
        ttk.Label(frm, text="Sweetness").pack(anchor="w")
        self.sweet_var = tk.StringVar(value=sweet_obj['values'][2] if len(sweet_obj['values'])>2 else sweet_obj['values'][0])
        ttk.Combobox(frm, values=sweet_obj['values'], textvariable=self.sweet_var, state="readonly").pack(fill="x", pady=4)

        # Toppings list (multi select with qty=1)
        ttk.Label(frm, text="Toppings").pack(anchor="w", pady=(8,0))
        self.top_vars = {}
        tops_frame = ttk.Frame(frm); tops_frame.pack(fill="x")
        for t in self.toppings:
            v = tk.IntVar(value=0)
            cb = ttk.Checkbutton(tops_frame, text=f"{t['name']} (+{t['price']:.2f})", variable=v)
            cb.pack(anchor="w")
            self.top_vars[t['id']] = (v, t)

        # Qty, Note
        qty_note = ttk.Frame(frm); qty_note.pack(fill="x", pady=6)
        ttk.Label(qty_note, text="Qty").grid(row=0, column=0, sticky="w")
        self.qty_var = tk.IntVar(value=1)
        ttk.Spinbox(qty_note, from_=1, to=99, textvariable=self.qty_var, width=6).grid(row=0, column=1, padx=6, sticky="w")

        ttk.Label(frm, text="Note").pack(anchor="w")
        self.note = tk.Text(frm, height=3); self.note.pack(fill="x")

        # Action
        ttk.Button(frm, text="Add to Cart", command=self.add).pack(pady=8, fill="x")

    def add(self):
        tops = []
        for tid, (v, trow) in self.top_vars.items():
            if v.get() == 1:
                tops.append({"id": trow['id'], "name": trow['name'], "price": float(trow['price']), "qty": 1})
        item = {
            "product_id": self.product['id'],
            "name": self.product['name'],
            "base_price": float(self.product['base_price']),
            "size": self.size_var.get(),
            "sweetness": self.sweet_var.get(),
            "toppings": tops,
            "qty": int(self.qty_var.get()),
            "note": self.note.get("1.0", "end").strip()
        }
        self.on_add(item)
        self.destroy()

# --- Main App Window ---
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.state("zoomed")
        self.style = ttk.Style(self)
        self._init_styles()
        ensure_dirs()
        self.db = AppDB()
        self.current_user = None
        self.cart = []  # list of items (dict)
        self._build_layout()

    def _init_styles(self):
        self.style.configure("Card.TFrame", relief="groove", borderwidth=1)
        self.style.configure("Title.TLabel", font=("Segoe UI", 11, "bold"))
        self.style.configure("Price.TLabel", foreground="#0a7", font=("Segoe UI", 10, "bold"))

    def _build_layout(self):
        # Topbar
        top = ttk.Frame(self, padding=6)
        top.pack(side="top", fill="x")
        self.lbl_user = ttk.Label(top, text="Not signed in")
        self.lbl_user.pack(side="left")

        self.btn_shop = ttk.Button(top, text="Shop", command=self.show_shop, state="disabled")
        self.btn_shop.pack(side="left", padx=4)
        self.btn_orders = ttk.Button(top, text="Orders", command=self.show_orders, state="disabled")
        self.btn_orders.pack(side="left", padx=4)
        self.btn_admin = ttk.Button(top, text="Admin", command=self.show_admin, state="disabled")
        self.btn_admin.pack(side="left", padx=4)

        self.btn_logout = ttk.Button(top, text="Logout", command=self.logout, state="disabled")
        self.btn_logout.pack(side="right")

        # Content
        self.content = ttk.Frame(self)
        self.content.pack(fill="both", expand=True)

        self.frames = {}
        for F in (LoginFrame, RegisterFrame, ShopFrame, OrdersFrame, AdminFrame):
            f = F(self.content, self)
            self.frames[F.__name__] = f
            f.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.show_frame("LoginFrame")

    def show_frame(self, name):
        f = self.frames[name]
        f.tkraise()
        if hasattr(f, "on_show"):
            f.on_show()

    def login_ok(self, user_row):
        self.current_user = user_row
        self.lbl_user.config(text=f"Logged in: {user_row['username']} ({user_row['role']})")
        self.btn_shop['state'] = "normal"
        self.btn_orders['state'] = "normal"
        self.btn_logout['state'] = "normal"
        self.btn_admin['state'] = "normal" if user_row['role'] == 'admin' else "disabled"
        self.show_shop()

    def logout(self):
        self.current_user = None
        self.cart.clear()
        self.lbl_user.config(text="Not signed in")
        for b in (self.btn_shop, self.btn_orders, self.btn_admin, self.btn_logout):
            b['state'] = "disabled"
        self.show_frame("LoginFrame")

    def show_shop(self):
        self.show_frame("ShopFrame")

    def show_orders(self):
        self.show_frame("OrdersFrame")

    def show_admin(self):
        if self.current_user and self.current_user['role']=='admin':
            self.show_frame("AdminFrame")
        else:
            messagebox.showwarning("Permission", "Admin only.")

class LoginFrame(ttk.Frame):
    def __init__(self, master, app: App):
        super().__init__(master, padding=20)
        self.app = app
        ttk.Label(self, text="Sign In", font=("Segoe UI", 18, "bold")).pack(pady=8)
        frm = ttk.Frame(self); frm.pack()
        ttk.Label(frm, text="Username").grid(row=0, column=0, sticky="e", padx=6, pady=4)
        ttk.Label(frm, text="Password").grid(row=1, column=0, sticky="e", padx=6, pady=4)
        self.euser = ttk.Entry(frm, width=30); self.euser.grid(row=0, column=1, pady=4)
        self.epass = ttk.Entry(frm, width=30, show="•"); self.epass.grid(row=1, column=1, pady=4)
        ttk.Button(self, text="Sign In", command=self.signin).pack(pady=6)
        ttk.Button(self, text="Create Account", command=lambda: self.app.show_frame("RegisterFrame")).pack()

    def on_show(self):
        self.euser.focus_set()

    def signin(self):
        u = self.euser.get().strip()
        p = self.epass.get().strip()
        if not u or not p:
            messagebox.showerror("Error","Please fill username & password")
            return
        row = self.app.db.auth_user(u, p)
        if row:
            self.app.login_ok(row)
        else:
            messagebox.showerror("Error","Invalid credentials.")

class RegisterFrame(ttk.Frame):
    def __init__(self, master, app: App):
        super().__init__(master, padding=20)
        self.app = app
        ttk.Label(self, text="Create Account", font=("Segoe UI", 18, "bold")).pack(pady=8)
        frm = ttk.Frame(self); frm.pack()
        self.euser = self._row(frm, "Username", 0)
        self.ep1   = self._row(frm, "Password", 1, show="•")
        self.ep2   = self._row(frm, "Confirm", 2, show="•")
        ttk.Button(self, text="Register", command=self.register).pack(pady=6)
        ttk.Button(self, text="Back to Login", command=lambda: self.app.show_frame("LoginFrame")).pack()

    def _row(self, parent, label, r, show=""):
        ttk.Label(parent, text=label).grid(row=r, column=0, sticky="e", padx=6, pady=4)
        e = ttk.Entry(parent, width=30, show=show); e.grid(row=r, column=1, pady=4)
        return e

    def register(self):
        u = self.euser.get().strip()
        p1 = self.ep1.get().strip()
        p2 = self.ep2.get().strip()
        if not u or not p1 or not p2:
            messagebox.showerror("Error","Please fill all fields"); return
        if p1 != p2:
            messagebox.showerror("Error","Passwords do not match"); return
        ok, msg = self.app.db.create_user(u, p1, role='customer')
        if ok:
            messagebox.showinfo("Success", msg)
            self.app.show_frame("LoginFrame")
        else:
            messagebox.showerror("Error", msg)

class ShopFrame(ttk.Frame):
    def __init__(self, master, app: App):
        super().__init__(master, padding=8)
        self.app = app
        self.nb = ttk.Notebook(self)
        self.nb.pack(side="left", fill="both", expand=True)
        self.right = ttk.Frame(self, padding=8)
        self.right.pack(side="left", fill="y")

        # Right panel = cart & checkout
        ttk.Label(self.right, text="Cart", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        self.cart_tv = ttk.Treeview(self.right, columns=("name","qty","price"), show="headings", height=16)
        for i,(t,w) in enumerate([("name",160), ("qty",40), ("price",80)]):
            self.cart_tv.heading(t, text=t.capitalize())
            self.cart_tv.column(t, width=w, anchor="w" if i==0 else "e")
        self.cart_tv.pack(fill="y", pady=4)

        fr_sub = ttk.Frame(self.right); fr_sub.pack(fill="x", pady=4)
        ttk.Label(fr_sub, text="Promo Code").grid(row=0, column=0, sticky="w")
        self.promo_var = tk.StringVar()
        ttk.Entry(fr_sub, textvariable=self.promo_var, width=12).grid(row=0, column=1, padx=4)
        ttk.Button(fr_sub, text="Apply", command=self.recalc_cart).grid(row=0, column=2)

        # channel & pickup time
        fr_ch = ttk.Frame(self.right); fr_ch.pack(fill="x", pady=4)
        ttk.Label(fr_ch, text="Channel").grid(row=0, column=0, sticky="w")
        self.channel_var = tk.StringVar(value="INSTORE")
        ttk.Combobox(fr_ch, values=["INSTORE","PICKUP","DELIVERY"], textvariable=self.channel_var, state="readonly", width=12).grid(row=0, column=1, padx=4)
        ttk.Label(fr_ch, text="Pickup Time").grid(row=1, column=0, sticky="w")
        self.pickup_var = tk.StringVar(value=(dt.now()+timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M"))
        ttk.Entry(fr_ch, textvariable=self.pickup_var, width=18).grid(row=1, column=1, padx=4)

        self.lbl_sub = ttk.Label(self.right, text="Subtotal: 0.00")
        self.lbl_dis = ttk.Label(self.right, text="Discount: 0.00")
        self.lbl_tot = ttk.Label(self.right, text="Total: 0.00", font=("Segoe UI", 12, "bold"))
        for w in (self.lbl_sub, self.lbl_dis, self.lbl_tot):
            w.pack(anchor="e")

        ttk.Separator(self.right).pack(fill="x", pady=6)

        # Payment method (QR only per requirement)
        ttk.Label(self.right, text="Payment: QR").pack(anchor="w")
        self.qr_canvas = tk.Canvas(self.right, width=180, height=180, bg="#fff", highlightthickness=1, highlightbackground="#ddd")
        self.qr_canvas.pack(pady=4)
        self._draw_qr_placeholder()

        ttk.Button(self.right, text="Checkout & Pay", command=self.checkout).pack(fill="x", pady=6)
        ttk.Button(self.right, text="Clear Cart", command=self.clear_cart).pack(fill="x")

        self.populate_tabs()

    def on_show(self):
        self.refresh_cart_view()

    def _draw_qr_placeholder(self):
        self.qr_canvas.delete("all")
        if os.path.exists(IMG_QR_PATH):
            try:
                img = Image.open(IMG_QR_PATH).convert("RGBA")
                img = img.resize((180,180), Image.LANCZOS)
                self.qr_img = ImageTk.PhotoImage(img)
                self.qr_canvas.create_image(90,90, image=self.qr_img)
                return
            except:
                pass
        self.qr_canvas.create_text(90,90, text="QR Placeholder\nPut image at\nassets/images/qr.png", justify="center")

    def populate_tabs(self):
        for t in self.nb.tabs():
            self.nb.forget(t)
        cats = self.app.db.get_categories()
        self.cards_cache = {}
        for cat in cats:
            frame = ttk.Frame(self.nb)
            self.nb.add(frame, text=cat['name'])
            # scroll area
            c = tk.Canvas(frame)
            vs = ttk.Scrollbar(frame, orient="vertical", command=c.yview)
            holder = ttk.Frame(c)
            holder.bind("<Configure>", lambda e, can=c: can.configure(scrollregion=can.bbox("all")))
            c.create_window((0,0), window=holder, anchor="nw")
            c.configure(yscrollcommand=vs.set)
            c.pack(side="left", fill="both", expand=True)
            vs.pack(side="right", fill="y")

            # product cards
            prods = self.app.db.list_products_by_category(cat['id'])
            rowf = None; col=0
            for i, p in enumerate(prods):
                if i%3==0:
                    rowf = ttk.Frame(holder); rowf.pack(fill="x", pady=6)
                    col = 0
                card = ProductCard(rowf, p, on_configure=self.open_config)
                card.grid(row=0, column=col, padx=6)
                col += 1

    def open_config(self, product_row):
        tops = self.app.db.list_toppings()
        ProductConfigDialog(self, self.app.db, product_row, tops, self.add_to_cart)

    def add_to_cart(self, item):
        self.app.cart.append(item)
        self.refresh_cart_view()

    def refresh_cart_view(self):
        for i in self.cart_tv.get_children():
            self.cart_tv.delete(i)
        subtotal, discount, total = self.compute_totals()
        for it in self.app.cart:
            size_mult = {"S":1.0,"M":1.2,"L":1.5}.get(it.get('size'),1.0)
            line_base = it['base_price'] * size_mult
            tops = sum(t['price']*t.get('qty',1) for t in it.get('toppings',[]))
            line_total = (line_base + tops)*it['qty']
            self.cart_tv.insert("", "end", values=(f"{it['name']} [{it.get('size','-')}/{it.get('sweetness','-')}]", it['qty'], f"{line_total:.2f}"))
        self.lbl_sub.config(text=f"Subtotal: {subtotal:.2f}")
        self.lbl_dis.config(text=f"Discount: {discount:.2f}")
        self.lbl_tot.config(text=f"Total: {total:.2f}")

    def compute_totals(self):
        subtotal = 0.0
        for it in self.app.cart:
            size_mult = {"S":1.0,"M":1.2,"L":1.5}.get(it.get('size'),1.0)
            line_base = it['base_price'] * size_mult
            tops = sum(t['price']*t.get('qty',1) for t in it.get('toppings',[]))
            subtotal += (line_base + tops)*it['qty']
        discount = 0.0
        promo = None
        code = self.promo_var.get().strip().upper()
        if code:
            promo = self.app.db.find_promo(code)
            if promo and subtotal >= float(promo['min_spend']):
                if promo['type']=='PERCENT_BILL':
                    discount = subtotal*(float(promo['value'])/100.0)
                elif promo['type']=='FLAT_BILL':
                    discount = float(promo['value'])
        total = max(0.0, subtotal - discount)
        return subtotal, discount, total

    def recalc_cart(self):
        self.refresh_cart_view()

    def checkout(self):
        if not self.app.current_user:
            messagebox.showwarning("Login", "Please sign in first.")
            return
        if not self.app.cart:
            messagebox.showwarning("Cart", "Your cart is empty.")
            return
        code = self.promo_var.get().strip().upper()
        promo = self.app.db.find_promo(code) if code else None
        channel = self.channel_var.get()
        pickup = self.pickup_var.get().strip()
        order_id, subtotal, discount, total = self.app.db.create_order(
            user_id=self.app.current_user['id'],
            channel=channel, pickup_time=pickup,
            cart_items=self.app.cart,
            promo_row=promo, payment_method="QR", pay_amount=0
        )
        # receipt
        path = create_receipt_pdf(order_id, self.app.db, self.app.current_user)
        messagebox.showinfo("Success", f"Order #{order_id} placed.\nReceipt saved:\n{path}")
        self.app.cart.clear()
        self.refresh_cart_view()
        self.app.show_orders()

    def clear_cart(self):
        self.app.cart.clear()
        self.refresh_cart_view()

class OrdersFrame(ttk.Frame):
    def __init__(self, master, app: App):
        super().__init__(master, padding=10)
        self.app = app
        ttk.Label(self, text="Order History", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        self.tv = ttk.Treeview(self, columns=("id","date","total","channel"), show="headings")
        for k,w in [("id",80),("date",160),("channel",100),("total",100)]:
            self.tv.heading(k, text=k.upper())
            self.tv.column(k, width=w, anchor="w")
        self.tv.pack(fill="both", expand=True, pady=6)

        btns = ttk.Frame(self)
        btns.pack(anchor="e")
        ttk.Button(btns, text="Open Receipt", command=self.open_receipt).pack(side="right", padx=4)
        ttk.Button(btns, text="Refresh", command=self.refresh).pack(side="right", padx=4)

    def on_show(self):
        self.refresh()

    def refresh(self):
        for i in self.tv.get_children():
            self.tv.delete(i)
        if not self.app.current_user: return
        rows = self.app.db.list_orders_of_user(self.app.current_user['id'])
        for r in rows:
            self.tv.insert("", "end", values=(r['id'], r['order_datetime'], r['channel'], f"{r['total']:.2f}"))

    def open_receipt(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showinfo("Open", "Select an order first."); return
        oid = self.tv.item(sel[0], "values")[0]
        path = os.path.join(REPORTS_DIR, f"receipt_{oid}.pdf")
        if not os.path.exists(path):
            # regenerate if missing
            path = create_receipt_pdf(int(oid), self.app.db, self.app.current_user)
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform == "darwin":
                os.system(f"open '{path}'")
            else:
                os.system(f"xdg-open '{path}'")
        except Exception as e:
            messagebox.showinfo("Receipt", f"Saved at: {path}")

class AdminFrame(ttk.Frame):
    def __init__(self, master, app: App):
        super().__init__(master, padding=8)
        self.app = app
        ttk.Label(self, text="Admin Panel", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)

        # Tabs
        self.tab_products = ttk.Frame(self.nb, padding=8); self.nb.add(self.tab_products, text="Products")
        self.tab_inventory = ttk.Frame(self.nb, padding=8); self.nb.add(self.tab_inventory, text="Inventory")
        self.tab_promos = ttk.Frame(self.nb, padding=8); self.nb.add(self.tab_promos, text="Promotions")
        self.tab_reports = ttk.Frame(self.nb, padding=8); self.nb.add(self.tab_reports, text="Reports")

        self._build_products()
        self._build_inventory()
        self._build_promos()
        self._build_reports()

    def on_show(self):
        self.refresh_products()
        self.refresh_inventory()
        self.refresh_promos()

    # --- Products ---
    def _build_products(self):
        top = ttk.Frame(self.tab_products); top.pack(fill="x")
        ttk.Button(top, text="Add Product", command=self.add_product).pack(side="left")
        ttk.Button(top, text="Edit", command=self.edit_product).pack(side="left", padx=4)
        ttk.Button(top, text="Delete", command=self.delete_product).pack(side="left", padx=4)
        ttk.Button(top, text="Refresh", command=self.refresh_products).pack(side="left", padx=4)

        self.tv_products = ttk.Treeview(self.tab_products,
            columns=("id","name","category","price","image","active"), show="headings")
        for k,w in [("id",50),("name",160),("category",100),("price",80),("image",220),("active",60)]:
            self.tv_products.heading(k, text=k.upper())
            self.tv_products.column(k, width=w, anchor="w")
        self.tv_products.pack(fill="both", expand=True, pady=6)

    def refresh_products(self):
        for i in self.tv_products.get_children():
            self.tv_products.delete(i)
        rows = self.app.db.list_products()
        for r in rows:
            self.tv_products.insert("", "end", values=(r['id'], r['name'], r['category_name'], f"{r['base_price']:.2f}", r['image'], r['is_active']))

    def add_product(self):
        ProductEditor(self, self.app.db, None, self.refresh_products)

    def edit_product(self):
        sel = self.tv_products.selection()
        if not sel:
            messagebox.showinfo("Edit", "Select a product"); return
        vals = self.tv_products.item(sel[0], "values")
        pid = int(vals[0])
        ProductEditor(self, self.app.db, pid, self.refresh_products)

    def delete_product(self):
        sel = self.tv_products.selection()
        if not sel:
            messagebox.showinfo("Delete", "Select a product"); return
        pid = int(self.tv_products.item(sel[0], "values")[0])
        if messagebox.askyesno("Confirm", "Delete this product?"):
            self.app.db.delete_product(pid)
            self.refresh_products()

    # --- Inventory ---
    def _build_inventory(self):
        top = ttk.Frame(self.tab_inventory); top.pack(fill="x")
        ttk.Button(top, text="Adjust +", command=lambda: self.adjust_inventory(1)).pack(side="left")
        ttk.Button(top, text="Adjust -", command=lambda: self.adjust_inventory(-1)).pack(side="left", padx=4)
        ttk.Button(top, text="Refresh", command=self.refresh_inventory).pack(side="left", padx=4)
        self.tv_inv = ttk.Treeview(self.tab_inventory, columns=("id","name","qty","unit","reorder","cost"),
                                   show="headings")
        for k,w in [("id",50),("name",180),("qty",100),("unit",60),("reorder",80),("cost",80)]:
            self.tv_inv.heading(k, text=k.upper()); self.tv_inv.column(k, width=w, anchor="w")
        self.tv_inv.pack(fill="both", expand=True, pady=6)

    def refresh_inventory(self):
        for i in self.tv_inv.get_children(): self.tv_inv.delete(i)
        for r in self.app.db.list_inventory():
            self.tv_inv.insert("", "end", values=(r['id'], r['name'], f"{r['qty_on_hand']} {r['unit']}", r['unit'], r['reorder_level'], r['cost_per_unit']))

    def adjust_inventory(self, sign):
        sel = self.tv_inv.selection()
        if not sel:
            messagebox.showinfo("Adjust","Select an item"); return
        inv_id = int(self.tv_inv.item(sel[0], "values")[0])
        val = tk.simpledialog.askfloat("Adjust", "Quantity to adjust (+/-)")
        if val is None: return
        self.app.db.adjust_inventory(inv_id, sign*abs(val))
        self.refresh_inventory()

    # --- Promotions ---
    def _build_promos(self):
        top = ttk.Frame(self.tab_promos); top.pack(fill="x")
        ttk.Button(top, text="Add", command=lambda: PromoEditor(self, self.app.db, None, self.refresh_promos)).pack(side="left")
        ttk.Button(top, text="Edit", command=self.edit_promo).pack(side="left", padx=4)
        ttk.Button(top, text="Delete", command=self.delete_promo).pack(side="left", padx=4)
        ttk.Button(top, text="Refresh", command=self.refresh_promos).pack(side="left", padx=4)
        self.tv_promo = ttk.Treeview(self.tab_promos, columns=("id","code","type","value","min","start","end","active"), show="headings")
        for k,w in [("id",50),("code",120),("type",120),("value",80),("min",80),("start",140),("end",140),("active",60)]:
            self.tv_promo.heading(k, text=k.upper()); self.tv_promo.column(k, width=w, anchor="w")
        self.tv_promo.pack(fill="both", expand=True, pady=6)

    def refresh_promos(self):
        for i in self.tv_promo.get_children(): self.tv_promo.delete(i)
        for r in self.app.db.list_promotions():
            self.tv_promo.insert("", "end", values=(r['id'], r['code'], r['type'], r['value'], r['min_spend'], r['start_at'], r['end_at'], r['is_active']))

    def edit_promo(self):
        sel = self.tv_promo.selection()
        if not sel: messagebox.showinfo("Edit","Select a promotion"); return
        pid = int(self.tv_promo.item(sel[0], "values")[0])
        PromoEditor(self, self.app.db, pid, self.refresh_promos)

    def delete_promo(self):
        sel = self.tv_promo.selection()
        if not sel: messagebox.showinfo("Delete","Select a promotion"); return
        pid = int(self.tv_promo.item(sel[0], "values")[0])
        if messagebox.askyesno("Confirm", "Delete this promotion?"):
            self.app.db.delete_promotion(pid)
            self.refresh_promos()

    # --- Reports ---
    def _build_reports(self):
        frm = ttk.Frame(self.tab_reports); frm.pack(fill="x")
        ttk.Label(frm, text="Start (YYYY-MM-DD)").grid(row=0, column=0, sticky="w")
        ttk.Label(frm, text="End").grid(row=0, column=2, sticky="w")
        self.rpt_start = tk.StringVar(value=dt.now().strftime("%Y-%m-01"))
        self.rpt_end   = tk.StringVar(value=dt.now().strftime("%Y-%m-%d"))
        ttk.Entry(frm, textvariable=self.rpt_start, width=12).grid(row=0, column=1, padx=6)
        ttk.Entry(frm, textvariable=self.rpt_end, width=12).grid(row=0, column=3, padx=6)
        ttk.Button(frm, text="Run", command=self.run_report).grid(row=0, column=4, padx=6)

        self.tv_rpt = ttk.Treeview(self.tab_reports, columns=("date","total"), show="headings")
        self.tv_rpt.heading("date", text="DATE")
        self.tv_rpt.heading("total", text="TOTAL")
        self.tv_rpt.column("date", width=140); self.tv_rpt.column("total", width=140)
        self.tv_rpt.pack(fill="both", expand=True, pady=6)

    def run_report(self):
        for i in self.tv_rpt.get_children(): self.tv_rpt.delete(i)
        rows = self.app.db.report_total_by_date(self.rpt_start.get().strip(), self.rpt_end.get().strip())
        for r in rows:
            self.tv_rpt.insert("", "end", values=(r['d'], f"{(r['total'] or 0):.2f}"))

# --- Editors ---
class ProductEditor(tk.Toplevel):
    def __init__(self, master, db: AppDB, product_id, on_done):
        super().__init__(master)
        self.db = db
        self.product_id = product_id
        self.on_done = on_done
        self.title("Product Editor")
        self.geometry("420x380")
        frm = ttk.Frame(self, padding=10); frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Name").grid(row=0, column=0, sticky="e"); self.en = ttk.Entry(frm, width=30); self.en.grid(row=0, column=1, pady=4)
        ttk.Label(frm, text="Category").grid(row=1, column=0, sticky="e")
        cats = db.get_categories(); self.cat_map = {c['name']:c['id'] for c in cats}
        self.ec = ttk.Combobox(frm, values=list(self.cat_map.keys()), state="readonly", width=27); self.ec.grid(row=1, column=1, pady=4)
        ttk.Label(frm, text="Base Price").grid(row=2, column=0, sticky="e"); self.ep = ttk.Entry(frm, width=30); self.ep.grid(row=2, column=1, pady=4)
        ttk.Label(frm, text="Image").grid(row=3, column=0, sticky="e"); self.ei = ttk.Entry(frm, width=30); self.ei.grid(row=3, column=1, pady=4)
        ttk.Button(frm, text="Choose Image...", command=self.choose_img).grid(row=3, column=2, padx=4)
        ttk.Label(frm, text="Active (1/0)").grid(row=4, column=0, sticky="e"); self.ea = ttk.Entry(frm, width=30); self.ea.grid(row=4, column=1, pady=4)
        ttk.Button(frm, text="Save", command=self.save).grid(row=5, column=1, pady=8)

        # load if edit
        if product_id:
            r = db.conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
            if r:
                self.en.insert(0, r['name'])
                # find cat name
                cname = db.conn.execute("SELECT name FROM categories WHERE id=?", (r['category_id'],)).fetchone()
                self.ec.set(cname['name'] if cname else "")
                self.ep.insert(0, str(r['base_price']))
                self.ei.insert(0, r['image'] or "")
                self.ea.insert(0, str(r['is_active']))

    def choose_img(self):
        f = filedialog.askopenfilename(title="Select Image", filetypes=[("Images","*.png;*.jpg;*.jpeg")])
        if not f: return
        # copy to products dir
        fname = os.path.basename(f)
        dest = os.path.join(IMG_PRODUCTS_DIR, fname)
        try:
            shutil.copy2(f, dest)
            self.ei.delete(0, "end")
            self.ei.insert(0, dest)
        except Exception as e:
            messagebox.showerror("Image", f"Copy failed: {e}")

    def save(self):
        name = self.en.get().strip()
        cat  = self.ec.get().strip()
        price = float(self.ep.get().strip() or 0)
        img = self.ei.get().strip()
        act = int(self.ea.get().strip() or 1)
        if not name or not cat:
            messagebox.showerror("Error", "Name/Category required"); return
        cat_id = self.cat_map[cat]
        self.db.upsert_product(self.product_id, name, cat_id, price, img, act)
        messagebox.showinfo("Saved","Product saved")
        self.on_done()
        self.destroy()

class PromoEditor(tk.Toplevel):
    def __init__(self, master, db: AppDB, pid, on_done):
        super().__init__(master)
        self.db = db; self.pid = pid; self.on_done = on_done
        self.title("Promotion Editor"); self.geometry("480x280")
        frm = ttk.Frame(self, padding=10); frm.pack(fill="both", expand=True)
        lb = [("Code","code"),("Type(PERCENT_BILL/FLAT_BILL)","type"),("Value","value"),("Min Spend","min"),
              ("Start (YYYY-MM-DD HH:MM:SS)","start"),("End","end"),("Active 1/0","active")]
        self.inputs={}
        for i,(label, key) in enumerate(lb):
            ttk.Label(frm, text=label).grid(row=i, column=0, sticky="e"); e = ttk.Entry(frm, width=34); e.grid(row=i, column=1, pady=3); self.inputs[key]=e
        ttk.Button(frm, text="Save", command=self.save).grid(row=len(lb), column=1, pady=8, sticky="e")

        if pid:
            r = db.conn.execute("SELECT * FROM promotions WHERE id=?", (pid,)).fetchone()
            if r:
                self.inputs['code'].insert(0, r['code'])
                self.inputs['type'].insert(0, r['type'])
                self.inputs['value'].insert(0, str(r['value']))
                self.inputs['min'].insert(0, str(r['min_spend']))
                self.inputs['start'].insert(0, r['start_at'])
                self.inputs['end'].insert(0, r['end_at'])
                self.inputs['active'].insert(0, str(r['is_active']))

    def save(self):
        code = self.inputs['code'].get().strip().upper()
        ptype = self.inputs['type'].get().strip()
        value = float(self.inputs['value'].get().strip() or 0)
        min_spend = float(self.inputs['min'].get().strip() or 0)
        start = self.inputs['start'].get().strip() or (dt.now().strftime("%Y-%m-%d 00:00:00"))
        end   = self.inputs['end'].get().strip() or (dt.now()+timedelta(days=365))
        if isinstance(end, dt): end = end.strftime("%Y-%m-%d 23:59:59")
        active = int(self.inputs['active'].get().strip() or 1)
        if not code or ptype not in ('PERCENT_BILL','FLAT_BILL'):
            messagebox.showerror("Error", "Invalid code/type"); return
        self.db.upsert_promotion(self.pid, code, ptype, value, min_spend, start, end, active)
        messagebox.showinfo("Saved", "Promotion saved")
        self.on_done(); self.destroy()

# --- run ---
if __name__ == "__main__":
    app = App()
    app.mainloop()

