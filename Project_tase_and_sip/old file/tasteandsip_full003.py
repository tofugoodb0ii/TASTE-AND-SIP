# -*- coding: utf-8 -*-
# TASTE AND SIP (Single file)
# - Fancy Login (left image + logo) -> Full App (Shop, Cart, Options Size/Sweetness/Toppings, Promo, QR Pay, PDF Receipt)
# - Admin: Products (with image upload), Inventory (BOM & low stock), Promotions, Reports
# - DB: SQLite, Images via Pillow, PDF via ReportLab

import os, sys, json, sqlite3, hashlib, shutil
from datetime import datetime as dt, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from PIL import Image, ImageTk
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.units import mm

APP_TITLE = "TASTE AND SIP"
DB_FILE   = "taste_and_sip.db"

# ---------- Login screen images (แก้ path ให้ตรงเครื่องคุณ) ----------
LEFT_BG_PATH = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\AVIBRA_1.png"  # BG ซ้าย
LOGO_PATH    = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\lologogo.png-removebg-preview.png"  # โลโก้

# ---------- Assets & Dirs ----------
ASSETS_DIR          = "assets"
IMG_DIR             = os.path.join(ASSETS_DIR, "images")
IMG_PRODUCTS_DIR    = os.path.join(IMG_DIR, "products")
IMG_QR_PATH         = os.path.join(IMG_DIR, "qr.png")       # <- วางรูปคิวอาร์เอง
IMG_AVATARS_DIR     = os.path.join(ASSETS_DIR, "avatars")
REPORTS_DIR         = "reports"

def ensure_dirs():
    for p in [ASSETS_DIR, IMG_DIR, IMG_PRODUCTS_DIR, IMG_AVATARS_DIR, REPORTS_DIR]:
        os.makedirs(p, exist_ok=True)

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def now_ts():
    return dt.now().strftime("%Y-%m-%d %H:%M:%S")

# ---------- Helpers: load images (Pillow) ----------
def load_photo(path, size):
    if not path or not os.path.exists(path): return None
    try:
        img = Image.open(path).convert("RGBA").resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

# ---------- Helpers: login screen (tk.PhotoImage) ----------
def _tk_load(path):
    try:
        if os.path.exists(path):
            return tk.PhotoImage(file=path)  # PNG/GIF เท่านั้น
    except Exception:
        pass
    return None

def _tk_cover(img, box_w, box_h):
    if not img: return None
    w, h = img.width(), img.height()
    if w == 0 or h == 0: return img
    r = max(box_w / w, box_h / h)
    if r >= 1: return img.zoom(max(1, round(r)))
    return img.subsample(max(1, int(1 / r)))

def _tk_load_and_cover(path, box_w, box_h):
    return _tk_cover(_tk_load(path), box_w, box_h)

def _tk_load_and_fit(path, max_w, max_h):
    img = _tk_load(path)
    if not img: return None
    w, h = img.width(), img.height()
    k = max(1, int(max(w/max_w, h/max_h)))
    return img if k == 1 else img.subsample(k, k)

# ======================= DATABASE =======================
class DB:
    def __init__(self, path=DB_FILE):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._schema()
        self._seed()

    def _schema(self):
        c = self.conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT, phone TEXT, email TEXT, birthdate TEXT, gender TEXT,
            avatar TEXT, role TEXT DEFAULT 'customer'
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
            code TEXT UNIQUE,
            type TEXT,            -- PERCENT_BILL | FLAT_BILL | PERCENT_ITEM | FLAT_ITEM
            value REAL,
            min_spend REAL DEFAULT 0,
            start_at TEXT, end_at TEXT,
            applies_to_product_id INTEGER,
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

    def _seed(self):
        c = self.conn.cursor()
        # admin
        if not c.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
            c.execute("INSERT INTO users(username,password_hash,name,role) VALUES(?,?,?,?)",
                      ("admin", sha256("admin123"), "Administrator", "admin"))
        # categories
        if c.execute("SELECT COUNT(*) n FROM categories").fetchone()['n'] == 0:
            c.executemany("INSERT INTO categories(name) VALUES(?)", [("FOOD",),("DRINK",),("DESSERT",)])
        # toppings
        if c.execute("SELECT COUNT(*) n FROM toppings").fetchone()['n'] == 0:
            c.executemany("INSERT INTO toppings(name,price) VALUES(?,?)",
                          [("Pearl",10),("Pudding",12),("Grass Jelly",8),("Whip Cream",7)])
        # products
        if c.execute("SELECT COUNT(*) n FROM products").fetchone()['n'] == 0:
            cats = {r['name']: r['id'] for r in c.execute("SELECT * FROM categories")}
            sample = [
                ("Pad Thai", cats["FOOD"], 60.0, "", 1),
                ("Thai Milk Tea", cats["DRINK"], 35.0, "", 1),
                ("Mango Sticky Rice", cats["DESSERT"], 50.0, "", 1),
            ]
            c.executemany("INSERT INTO products(name,category_id,base_price,image,is_active) VALUES(?,?,?,?,?)", sample)
        # options (Size, Sweetness) — มีขนาดและระดับความหวาน
        size_json = json.dumps({"values":["S","M","L"],"price_multipliers":{"S":1.0,"M":1.2,"L":1.5}})
        sweet_json = json.dumps({"values":["0%","25%","50%","75%","100%"]})
        for p in c.execute("SELECT id FROM products"):
            if not c.execute("SELECT 1 FROM product_options WHERE product_id=? AND option_name='Size'",(p['id'],)).fetchone():
                c.execute("INSERT INTO product_options(product_id,option_name,option_values_json) VALUES(?,?,?)",(p['id'],"Size",size_json))
            if not c.execute("SELECT 1 FROM product_options WHERE product_id=? AND option_name='Sweetness'",(p['id'],)).fetchone():
                c.execute("INSERT INTO product_options(product_id,option_name,option_values_json) VALUES(?,?,?)",(p['id'],"Sweetness",sweet_json))
        # inventory & BOM (ตัวอย่าง)
        if c.execute("SELECT COUNT(*) n FROM inventory_items").fetchone()['n'] == 0:
            inv = [
                ("Noodles","g",5000,500,0.05),
                ("Tea Leaves","g",3000,300,0.04),
                ("Milk","ml",5000,800,0.02),
                ("Mango","g",2000,300,0.06),
                ("Sticky Rice","g",3000,400,0.03),
            ]
            c.executemany("INSERT INTO inventory_items(name,unit,qty_on_hand,reorder_level,cost_per_unit) VALUES(?,?,?,?,?)", inv)
        pr = {r['name']: r['id'] for r in c.execute("SELECT id,name FROM products")}
        iv = {r['name']: r['id'] for r in c.execute("SELECT id,name FROM inventory_items")}
        for link in [
            (pr.get("Pad Thai"), iv.get("Noodles"), 120),
            (pr.get("Thai Milk Tea"), iv.get("Tea Leaves"), 8),
            (pr.get("Thai Milk Tea"), iv.get("Milk"), 180),
            (pr.get("Mango Sticky Rice"), iv.get("Mango"), 150),
            (pr.get("Mango Sticky Rice"), iv.get("Sticky Rice"), 120),
        ]:
            if all(link):
                c.execute("INSERT OR IGNORE INTO bom_links(product_id,inventory_item_id,qty_per_unit) VALUES(?,?,?)", link)
        # promotions demo
        if c.execute("SELECT COUNT(*) n FROM promotions").fetchone()['n'] == 0:
            today = dt.now()
            st = (today - timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
            ed = (today + timedelta(days=365)).strftime("%Y-%m-%d 23:59:59")
            tea_id = pr.get("Thai Milk Tea")
            promos = [
                ("WELCOME10","PERCENT_BILL",10,0,st,ed,None,1),
                ("TEA5","FLAT_ITEM",5,0,st,ed,tea_id,1),
            ]
            c.executemany("""INSERT INTO promotions(code,type,value,min_spend,start_at,end_at,applies_to_product_id,is_active)
                             VALUES(?,?,?,?,?,?,?,?)""", promos)
        self.conn.commit()

    # --- user/auth/profile ---
    def create_user(self, username, password):
        try:
            self.conn.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                              (username, sha256(password), "customer"))
            self.conn.commit(); return True, "Account created."
        except sqlite3.IntegrityError:
            return False, "Username already exists."

    def auth(self, username, password):
        return self.conn.execute("SELECT * FROM users WHERE username=? AND password_hash=?",
                                 (username, sha256(password))).fetchone()

    def update_profile(self, uid, fields:dict):
        if not fields: return
        cols = ", ".join([f"{k}=?" for k in fields.keys()])
        vals = list(fields.values()) + [uid]
        self.conn.execute(f"UPDATE users SET {cols} WHERE id=?", vals); self.conn.commit()

    def change_password(self, uid, newpass):
        self.conn.execute("UPDATE users SET password_hash=? WHERE id=?", (sha256(newpass), uid))
        self.conn.commit()

    # --- catalog/options/toppings ---
    def categories(self): return self.conn.execute("SELECT * FROM categories").fetchall()
    def products_by_cat(self, cid): 
        return self.conn.execute("SELECT * FROM products WHERE category_id=? AND is_active=1",(cid,)).fetchall()
    def product_options(self, pid):
        out={}
        for r in self.conn.execute("SELECT * FROM product_options WHERE product_id=?", (pid,)).fetchall():
            out[r['option_name']] = json.loads(r['option_values_json'] or "{}")
        return out
    def toppings(self): return self.conn.execute("SELECT * FROM toppings WHERE is_active=1").fetchall()

    # --- promotions ---
    def _within(self, row):
        now = dt.now()
        try:
            st = dt.strptime(row['start_at'],"%Y-%m-%d %H:%M:%S")
            ed = dt.strptime(row['end_at'],"%Y-%m-%d %H:%M:%S")
        except: 
            return True
        return st <= now <= ed

    def find_promo(self, code):
        r = self.conn.execute("SELECT * FROM promotions WHERE code=? AND is_active=1",(code,)).fetchone()
        return r if (r and self._within(r)) else None

    # --- inventory / BOM ---
    def bom(self, pid):
        return self.conn.execute("SELECT * FROM bom_links WHERE product_id=?", (pid,)).fetchall()

    def deduct_for_order(self, order_id):
        rows = self.conn.execute("""
        SELECT oi.qty, bl.inventory_item_id, bl.qty_per_unit
        FROM order_items oi 
        JOIN bom_links bl ON bl.product_id = oi.product_id
        WHERE oi.order_id=?""",(order_id,)).fetchall()
        cur = self.conn.cursor()
        for r in rows:
            dec = float(r['qty']) * float(r['qty_per_unit'])
            cur.execute("UPDATE inventory_items SET qty_on_hand = qty_on_hand - ? WHERE id=?", (dec, r['inventory_item_id']))
            cur.execute("""INSERT INTO stock_movements(inventory_item_id,change_qty,reason,ref_id,created_at)
                           VALUES(?,?,?,?,?)""", (r['inventory_item_id'],-dec,'SALE',order_id, now_ts()))
        self.conn.commit()

    # --- orders / payments ---
    def create_order(self, user_id, channel, pickup_time, cart_items, promo_code, payment_method="QR"):
        subtotal = 0.0
        item_totals = []
        for it in cart_items:
            size_mult = {"S":1.0,"M":1.2,"L":1.5}.get(it.get('size'),1.0)
            base = float(it['base_price']) * size_mult
            tops = sum(t['price']*t.get('qty',1) for t in it.get('toppings',[]))
            line = (base + tops) * it['qty']
            subtotal += line
            item_totals.append((it['product_id'], line, it['qty'], base, tops))

        discount = 0.0
        promo = self.find_promo(promo_code) if promo_code else None
        if promo:
            msp = float(promo['min_spend'] or 0)
            ptype = promo['type']
            val = float(promo['value'] or 0)
            pid = promo['applies_to_product_id']
            if ptype in ("PERCENT_BILL","FLAT_BILL") and subtotal >= msp:
                discount = subtotal*(val/100.0) if ptype=="PERCENT_BILL" else min(val, subtotal)
            elif ptype in ("PERCENT_ITEM","FLAT_ITEM"):
                target = sum(line for (prod,line,qty,b,t) in item_totals if prod==pid)
                if target>0:
                    discount = target*(val/100.0) if ptype=="PERCENT_ITEM" else min(val, target)

        total = max(0.0, subtotal - discount)

        cur = self.conn.cursor()
        cur.execute("""INSERT INTO orders(user_id,order_datetime,channel,pickup_time,subtotal,discount,total,payment_method,status)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (user_id, now_ts(), channel, pickup_time or "", subtotal, discount, total, payment_method, "PAID"))
        order_id = cur.lastrowid
        # items
        for it in cart_items:
            opts = {"Size": it.get("size"), "Sweetness": it.get("sweetness")}
            cur.execute("""INSERT INTO order_items(order_id,product_id,qty,unit_price,options_json,note)
                           VALUES(?,?,?,?,?,?)""",
                        (order_id, it['product_id'], it['qty'], it['base_price'], json.dumps(opts), it.get('note','')))
            oi_id = cur.lastrowid
            for tp in it.get('toppings',[]):
                cur.execute("INSERT INTO order_item_toppings(order_item_id,topping_id,qty,price) VALUES(?,?,?,?)",
                            (oi_id, tp['id'], tp.get('qty',1), tp['price']))
        # payment row
        cur.execute("INSERT INTO payments(order_id,method,amount,paid_at,ref) VALUES(?,?,?,?,?)",
                    (order_id, payment_method, total, now_ts(), ""))
        self.conn.commit()
        # inventory
        self.deduct_for_order(order_id)
        return order_id, subtotal, discount, total

    def orders_of_user(self, uid, limit=200):
        return self.conn.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ?", (uid, limit)).fetchall()

    def order_detail(self, oid):
        o = self.conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        items = self.conn.execute("""SELECT oi.*, p.name AS product_name
                                     FROM order_items oi JOIN products p ON p.id=oi.product_id
                                     WHERE order_id=?""",(oid,)).fetchall()
        tops = self.conn.execute("""SELECT oit.*, t.name AS topping_name
                                    FROM order_item_toppings oit JOIN toppings t ON t.id=oit.topping_id
                                    WHERE oit.order_item_id IN (SELECT id FROM order_items WHERE order_id=?)""",(oid,)).fetchall()
        return o, items, tops

    # --- admin CRUD/promos/reports ---
    def list_products(self):
        return self.conn.execute("""SELECT p.*, c.name AS category_name
                                    FROM products p LEFT JOIN categories c ON c.id=p.category_id
                                    ORDER BY p.id DESC""").fetchall()
    def upsert_product(self, pid, name, cat_id, price, image, active):
        cur = self.conn.cursor()
        if pid:
            cur.execute("""UPDATE products SET name=?,category_id=?,base_price=?,image=?,is_active=? WHERE id=?""",
                        (name,cat_id,price,image,active,pid))
        else:
            cur.execute("""INSERT INTO products(name,category_id,base_price,image,is_active) VALUES(?,?,?,?,?)""",
                        (name,cat_id,price,image,active))
        self.conn.commit()
    def delete_product(self, pid):
        self.conn.execute("DELETE FROM products WHERE id=?", (pid,)); self.conn.commit()

    def list_inventory(self):
        return self.conn.execute("SELECT * FROM inventory_items ORDER BY id DESC").fetchall()
    def adjust_inventory(self, inv_id, delta, reason='ADJUST'):
        cur = self.conn.cursor()
        cur.execute("UPDATE inventory_items SET qty_on_hand = qty_on_hand + ? WHERE id=?", (delta, inv_id))
        cur.execute("""INSERT INTO stock_movements(inventory_item_id,change_qty,reason,ref_id,created_at)
                       VALUES(?,?,?,?,?)""",(inv_id, delta, reason, 0, now_ts()))
        self.conn.commit()

    def list_promotions(self):
        return self.conn.execute("SELECT * FROM promotions ORDER BY id DESC").fetchall()
    def upsert_promotion(self, pid, code, ptype, value, min_spend, start_at, end_at, applies_to_product_id, is_active):
        cur = self.conn.cursor()
        if pid:
            cur.execute("""UPDATE promotions SET code=?,type=?,value=?,min_spend=?,start_at=?,end_at=?,applies_to_product_id=?,is_active=? WHERE id=?""",
                        (code,ptype,value,min_spend,start_at,end_at,applies_to_product_id,is_active,pid))
        else:
            cur.execute("""INSERT INTO promotions(code,type,value,min_spend,start_at,end_at,applies_to_product_id,is_active)
                           VALUES(?,?,?,?,?,?,?,?)""",
                        (code,ptype,value,min_spend,start_at,end_at,applies_to_product_id,is_active))
        self.conn.commit()
    def delete_promotion(self, pid):
        self.conn.execute("DELETE FROM promotions WHERE id=?", (pid,)); self.conn.commit()

    def report_total_by_date(self, start, end):
        return self.conn.execute("""
            SELECT substr(order_datetime,1,10) AS d, SUM(total) total
            FROM orders WHERE order_datetime BETWEEN ? AND ?
            GROUP BY d ORDER BY d
        """,(start+" 00:00:00", end+" 23:59:59")).fetchall()

    def report_by_category(self, start, end):
        return self.conn.execute("""
            SELECT c.name category, SUM(oi.qty*oi.unit_price) AS sales
            FROM order_items oi
            JOIN products p ON p.id=oi.product_id
            JOIN categories c ON c.id=p.category_id
            JOIN orders o ON o.id=oi.order_id
            WHERE o.order_datetime BETWEEN ? AND ?
            GROUP BY c.id ORDER BY sales DESC
        """,(start+" 00:00:00", end+" 23:59:59")).fetchall()

    def report_by_product(self, start, end):
        return self.conn.execute("""
            SELECT p.name product, SUM(oi.qty) qty, SUM(oi.qty*oi.unit_price) sales
            FROM order_items oi
            JOIN products p ON p.id=oi.product_id
            JOIN orders o ON o.id=oi.order_id
            WHERE o.order_datetime BETWEEN ? AND ?
            GROUP BY p.id ORDER BY sales DESC
        """,(start+" 00:00:00", end+" 23:59:59")).fetchall()

    def report_top_customers(self, start, end, limit=10):
        return self.conn.execute("""
            SELECT u.username, u.name, SUM(o.total) total
            FROM orders o JOIN users u ON u.id=o.user_id
            WHERE o.order_datetime BETWEEN ? AND ?
            GROUP BY u.id ORDER BY total DESC LIMIT ?
        """,(start+" 00:00:00", end+" 23:59:59", limit)).fetchall()

    def report_gross_margin(self, start, end):
        return self.conn.execute("""
            WITH sold AS (
                SELECT oi.product_id, SUM(oi.qty) qty
                FROM order_items oi JOIN orders o ON o.id=oi.order_id
                WHERE o.order_datetime BETWEEN ? AND ?
                GROUP BY oi.product_id
            ), cost AS (
                SELECT s.product_id, SUM(s.qty * bl.qty_per_unit * ii.cost_per_unit) cost
                FROM sold s
                JOIN bom_links bl ON bl.product_id=s.product_id
                JOIN inventory_items ii ON ii.id=bl.inventory_item_id
                GROUP BY s.product_id
            )
            SELECT SUM(o.total) revenue, IFNULL(SUM(c.cost),0) cost, SUM(o.total)-IFNULL(SUM(c.cost),0) gross_profit
            FROM orders o LEFT JOIN cost c ON 1=1
            WHERE o.order_datetime BETWEEN ? AND ?
        """,(start+" 00:00:00", end+" 23:59:59", start+" 00:00:00", end+" 23:59:59")).fetchone()

# ======================= RECEIPT (PDF) =======================
def create_receipt_pdf(order_id, db: DB, user_row):
    ensure_dirs()
    path = os.path.join(REPORTS_DIR, f"receipt_{order_id}.pdf")
    canv = pdfcanvas.Canvas(path, pagesize=A4)
    W, H = A4; x = 18*mm; y = H-18*mm

    order, items, tps = db.order_detail(order_id)
    canv.setFont("Helvetica-Bold", 16); canv.drawString(x, y, "TASTE AND SIP - RECEIPT"); y -= 10*mm
    canv.setFont("Helvetica", 10)
    canv.drawString(x, y, f"Order ID: {order_id}"); y -= 5*mm
    canv.drawString(x, y, f"Date/Time: {order['order_datetime']}"); y -= 5*mm
    canv.drawString(x, y, f"Customer: {user_row['name'] or user_row['username']}"); y -= 8*mm

    canv.setFont("Helvetica-Bold", 12); canv.drawString(x, y, "Items"); y -= 6*mm
    canv.setFont("Helvetica", 10)
    for it in items:
        opts = json.loads(it['options_json'] or "{}")
        canv.drawString(x, y, f"- {it['product_name']} x{it['qty']} (Base: {it['unit_price']:.2f})"); y -= 5*mm
        canv.drawString(x+8*mm, y, f"Size: {opts.get('Size','-')}, Sweetness: {opts.get('Sweetness','-')}"); y -= 5*mm
        for tp in tps:
            if tp['order_item_id']==it['id']:
                canv.drawString(x+8*mm, y, f"Topping: {tp['topping_name']} x{tp['qty']} @ {tp['price']:.2f}")
                y -= 5*mm
        if it['note']:
            canv.drawString(x+8*mm, y, f"Note: {it['note']}"); y -= 5*mm
        y -= 2*mm

    canv.setFont("Helvetica-Bold", 11)
    canv.drawString(x, y, f"Subtotal: {order['subtotal']:.2f}    Discount: {order['discount']:.2f}    Total: {order['total']:.2f}"); y -= 8*mm
    canv.setFont("Helvetica", 10)
    canv.drawString(x, y, f"Channel: {order['channel']}  Pickup: {order['pickup_time'] or '-'}  Payment: {order['payment_method']}"); y -= 10*mm

    if os.path.exists(IMG_QR_PATH):
        try:
            canv.drawImage(IMG_QR_PATH, x, y-45*mm, width=40*mm, height=40*mm, preserveAspectRatio=True, mask='auto')
            canv.drawString(x+45*mm, y-5*mm, "Scan to pay (display only)")
        except:
            canv.drawString(x, y, "QR image error.")
    else:
        canv.drawString(x, y, "QR Placeholder: add image at assets/images/qr.png")
    canv.showPage(); canv.save()
    return path

# ======================= UI Components =======================
class ProductCard(ttk.Frame):
    def __init__(self, master, row, on_customize):
        super().__init__(master, padding=6, style="Card.TFrame")
        self.row = row; self.on_customize = on_customize
        img = load_photo(row['image'], (160,120))
        ttk.Label(self, image=img if img else None, text="" if img else "[No Image]",
                  compound="none").pack()
        if img: self._img = img
        ttk.Label(self, text=row['name'], style="Title.TLabel").pack(pady=(6,0))
        ttk.Label(self, text=f"{row['base_price']:.2f} ฿", style="Price.TLabel").pack()
        ttk.Button(self, text="Customize + Add", command=lambda: self.on_customize(row)).pack(pady=4)

class ProductDialog(tk.Toplevel):
    def __init__(self, master, db: DB, prod_row, toppings, on_add):
        super().__init__(master); self.title(f"Customize - {prod_row['name']}")
        self.db=db; self.prod=prod_row; self.toppings=toppings; self.on_add=on_add
        self.geometry("420x560"); self.resizable(False, False)
        opts = db.product_options(prod_row['id'])
        self.size_cfg = opts.get('Size', {"values":["S","M","L"],"price_multipliers":{"S":1.0,"M":1.2,"L":1.5}})
        self.sweet_cfg = opts.get('Sweetness', {"values":["0%","25%","50%","75%","100%"]})

        frm = ttk.Frame(self, padding=10); frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Size").pack(anchor="w")
        self.var_size = tk.StringVar(value=self.size_cfg["values"][0])
        ttk.Combobox(frm, values=self.size_cfg["values"], textvariable=self.var_size, state="readonly").pack(fill="x", pady=4)

        ttk.Label(frm, text="Sweetness").pack(anchor="w")
        self.var_sweet = tk.StringVar(value=self.sweet_cfg["values"][2] if len(self.sweet_cfg["values"])>2 else self.sweet_cfg["values"][0])
        ttk.Combobox(frm, values=self.sweet_cfg["values"], textvariable=self.var_sweet, state="readonly").pack(fill="x", pady=4)

        ttk.Label(frm, text="Toppings").pack(anchor="w", pady=(8,0))
        self.top_vars={}
        frt = ttk.Frame(frm); frt.pack(fill="x")
        for t in toppings:
            v=tk.IntVar(0); ttk.Checkbutton(frt, text=f"{t['name']} (+{t['price']:.2f})", variable=v).pack(anchor="w")
            self.top_vars[t['id']] = (v, t)

        frq = ttk.Frame(frm); frq.pack(fill="x", pady=6)
        ttk.Label(frq, text="Qty").grid(row=0,column=0,sticky="w")
        self.var_qty = tk.IntVar(1); ttk.Spinbox(frq, from_=1, to=99, textvariable=self.var_qty, width=6).grid(row=0,column=1,padx=6)
        ttk.Label(frm, text="Note").pack(anchor="w")
        self.txt_note = tk.Text(frm, height=3); self.txt_note.pack(fill="x")

        ttk.Button(frm, text="Add to Cart", command=self._add).pack(pady=8, fill="x")

    def _add(self):
        tops=[]
        for tid,(v,trow) in self.top_vars.items():
            if v.get()==1:
                tops.append({"id":trow['id'],"name":trow['name'],"price":float(trow['price']),"qty":1})
        item = {
            "product_id": self.prod['id'], "name": self.prod['name'],
            "base_price": float(self.prod['base_price']),
            "size": self.var_size.get(), "sweetness": self.var_sweet.get(),
            "toppings": tops, "qty": int(self.var_qty.get()),
            "note": self.txt_note.get("1.0","end").strip()
        }
        self.on_add(item); self.destroy()

# ======================= MAIN APP =======================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE); self.state("zoomed")
        ensure_dirs()
        self.db = DB()
        self.user = None
        self.cart = []
        self._styles()
        self._layout()

    def _styles(self):
        st = ttk.Style(self)
        st.configure("Card.TFrame", relief="groove", borderwidth=1)
        st.configure("Title.TLabel", font=("Segoe UI", 11, "bold"))
        st.configure("Price.TLabel", foreground="#087", font=("Segoe UI", 10, "bold"))
        st.configure("Warn.TLabel", foreground="#b50", font=("Segoe UI", 10, "bold"))

    def _layout(self):
        top = ttk.Frame(self, padding=6); top.pack(side="top", fill="x")
        self.lbl_user = ttk.Label(top, text="Not signed in"); self.lbl_user.pack(side="left")

        ttk.Button(top, text="Shop", command=lambda:self.show("Shop")).pack(side="left", padx=4)
        ttk.Button(top, text="Orders", command=lambda:self.show("Orders")).pack(side="left", padx=4)
        ttk.Button(top, text="Profile", command=lambda:self.show("Profile")).pack(side="left", padx=4)
        self.btn_admin = ttk.Button(top, text="Admin", command=lambda:self.show("Admin")); self.btn_admin.pack(side="left", padx=4)

        self.btn_logout = ttk.Button(top, text="Logout", command=self.logout, state="disabled")
        self.btn_logout.pack(side="right")

        self.content = ttk.Frame(self); self.content.pack(fill="both", expand=True)
        self.frames={}
        for F in (LoginView, RegisterView, ShopView, OrdersView, ProfileView, AdminView):
            f = F(self.content, self); self.frames[F.__name__]=f; f.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.show("Login")

    def show(self, name):
        target = {
            "Login":"LoginView", "Register":"RegisterView",
            "Shop":"ShopView", "Orders":"OrdersView", "Profile":"ProfileView", "Admin":"AdminView"
        }[name]
        self.frames[target].tkraise()
        if hasattr(self.frames[target], "on_show"): self.frames[target].on_show()

    def login_ok(self, user_row):
        self.user = user_row
        self.lbl_user.config(text=f"{user_row['username']} ({user_row['role']})")
        self.btn_logout['state']="normal"
        self.btn_admin['state']="normal" if user_row['role']=="admin" else "disabled"
        self.show("Shop")

    def logout(self):
        self.user=None; self.cart.clear()
        self.lbl_user.config(text="Not signed in")
        self.btn_logout['state']="disabled"; self.btn_admin['state']="disabled"
        self.show("Login")

# ---------- Views ----------
class LoginView(ttk.Frame):
    """ Login view (แบบเรียบในแอปหลัก สำหรับ fallback/แอดมิน) """
    def __init__(self, master, app: App):
        super().__init__(master, padding=20); self.app=app
        ttk.Label(self, text="Sign In", font=("Segoe UI", 18, "bold")).pack(pady=8)
        frm = ttk.Frame(self); frm.pack()
        ttk.Label(frm,text="Username").grid(row=0,column=0,sticky="e",padx=6,pady=4)
        ttk.Label(frm,text="Password").grid(row=1,column=0,sticky="e",padx=6,pady=4)
        self.euser=ttk.Entry(frm,width=30); self.euser.grid(row=0,column=1,pady=4)
        self.epass=ttk.Entry(frm,width=30,show="•"); self.epass.grid(row=1,column=1,pady=4)
        ttk.Button(self,text="Sign In",command=self.signin).pack(pady=6)
        ttk.Button(self,text="Create Account",command=lambda:self.app.show("Register")).pack()
    def on_show(self): self.euser.focus_set()
    def signin(self):
        u=self.euser.get().strip(); p=self.epass.get().strip()
        if not u or not p: messagebox.showerror("Error","Fill username & password"); return
        row=self.app.db.auth(u,p)
        if row: self.app.login_ok(row)
        else: messagebox.showerror("Error","Invalid credentials")

class RegisterView(ttk.Frame):
    def __init__(self, master, app: App):
        super().__init__(master,padding=20); self.app=app
        ttk.Label(self,text="Create Account",font=("Segoe UI",18,"bold")).pack(pady=8)
        frm=ttk.Frame(self); frm.pack()
        self.euser=self._row(frm,"Username",0)
        self.ep1=self._row(frm,"Password",1,show="•")
        self.ep2=self._row(frm,"Confirm",2,show="•")
        ttk.Button(self,text="Register",command=self.reg).pack(pady=6)
        ttk.Button(self,text="Back to Login",command=lambda:self.app.show("Login")).pack()
    def _row(self, parent, label, r, show=""):
        ttk.Label(parent,text=label).grid(row=r,column=0,sticky="e",padx=6,pady=4)
        e=ttk.Entry(parent,width=30,show=show); e.grid(row=r,column=1,pady=4); return e
    def reg(self):
        u=self.euser.get().strip(); p1=self.ep1.get().strip(); p2=self.ep2.get().strip()
        if not u or not p1 or not p2: messagebox.showerror("Error","Fill all fields"); return
        if p1!=p2: messagebox.showerror("Error","Passwords do not match"); return
        ok,msg=self.app.db.create_user(u,p1)
        if ok: messagebox.showinfo("Success",msg); self.app.show("Login")
        else: messagebox.showerror("Error",msg)

class ShopView(ttk.Frame):
    def __init__(self, master, app: App):
        super().__init__(master,padding=8); self.app=app
        self.nb=ttk.Notebook(self); self.nb.pack(side="left",fill="both",expand=True)
        right=ttk.Frame(self,padding=8); right.pack(side="left",fill="y")

        ttk.Label(right,text="Cart",font=("Segoe UI",14,"bold")).pack(anchor="w")
        self.tv=ttk.Treeview(right,columns=("name","qty","price"),show="headings",height=18)
        for k,w,anc in [("name",180,"w"),("qty",40,"e"),("price",90,"e")]:
            self.tv.heading(k,text=k.upper()); self.tv.column(k,width=w,anchor=anc)
        self.tv.pack(fill="y",pady=4)

        f1=ttk.Frame(right); f1.pack(fill="x",pady=4)
        ttk.Label(f1,text="Promo Code").grid(row=0,column=0,sticky="w"); 
        self.var_code=tk.StringVar(); ttk.Entry(f1,textvariable=self.var_code,width=12).grid(row=0,column=1,padx=4)
        ttk.Button(f1,text="Apply",command=self.refresh).grid(row=0,column=2)

        f2=ttk.Frame(right); f2.pack(fill="x",pady=4)
        ttk.Label(f2,text="Channel").grid(row=0,column=0,sticky="w")
        self.var_channel=tk.StringVar(value="INSTORE")
        ttk.Combobox(f2,values=["INSTORE","PICKUP","DELIVERY"],textvariable=self.var_channel,state="readonly",width=12).grid(row=0,column=1,padx=4)
        ttk.Label(f2,text="Pickup Time").grid(row=1,column=0,sticky="w")
        self.var_pickup=tk.StringVar(value=(dt.now()+timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M"))
        ttk.Entry(f2,textvariable=self.var_pickup,width=18).grid(row=1,column=1,padx=4)

        self.lbl_sub=ttk.Label(right,text="Subtotal: 0.00"); self.lbl_sub.pack(anchor="e")
        self.lbl_dis=ttk.Label(right,text="Discount: 0.00"); self.lbl_dis.pack(anchor="e")
        self.lbl_tot=ttk.Label(right,text="Total: 0.00",font=("Segoe UI",12,"bold")); self.lbl_tot.pack(anchor="e")

        ttk.Separator(right).pack(fill="x",pady=6)
        ttk.Label(right,text="Payment: QR").pack(anchor="w")
        self.qr=tk.Canvas(right,width=180,height=180,bg="#fff",highlightthickness=1,highlightbackground="#ddd")
        self.qr.pack(pady=4); self._draw_qr()
        ttk.Button(right,text="Checkout & Pay",command=self.checkout).pack(fill="x",pady=6)
        ttk.Button(right,text="Clear Cart",command=self.clear).pack(fill="x")

    def on_show(self):
        self._build_tabs(); self.refresh()

    def _draw_qr(self):
        self.qr.delete("all")
        if os.path.exists(IMG_QR_PATH):
            try:
                img=Image.open(IMG_QR_PATH).convert("RGBA").resize((180,180),Image.LANCZOS)
                self._qrimg=ImageTk.PhotoImage(img); self.qr.create_image(90,90,image=self._qrimg); return
            except: pass
        self.qr.create_text(90,90,text="QR Placeholder\nassets/images/qr.png",justify="center")

    def _build_tabs(self):
        for t in self.nb.tabs(): self.nb.forget(t)
        for cat in self.app.db.categories():
            frm=ttk.Frame(self.nb); self.nb.add(frm,text=cat['name'])
            can=tk.Canvas(frm); vs=ttk.Scrollbar(frm,orient="vertical",command=can.yview)
            holder=ttk.Frame(can); holder.bind("<Configure>", lambda e, c=can: c.configure(scrollregion=c.bbox("all")))
            can.create_window((0,0),window=holder,anchor="nw"); can.configure(yscrollcommand=vs.set)
            can.pack(side="left",fill="both",expand=True); vs.pack(side="right",fill="y")
            rowf=None; col=0
            for i,p in enumerate(self.app.db.products_by_cat(cat['id'])):
                if i%3==0: rowf=ttk.Frame(holder); rowf.pack(fill="x",pady=6); col=0
                ProductCard(rowf,p,self.customize).grid(row=0,column=col,padx=6); col+=1

    def customize(self, prod_row):
        ProductDialog(self, self.app.db, prod_row, self.app.db.toppings(), self.add)

    def add(self, item):
        self.app.cart.append(item); self.refresh()

    def _totals(self):
        subtotal=0.0
        for it in self.app.cart:
            size_mult={"S":1.0,"M":1.2,"L":1.5}.get(it.get("size"),1.0)
            base=float(it['base_price'])*size_mult
            tops=sum(t['price']*t.get('qty',1) for t in it.get('toppings',[]))
            subtotal+=(base+tops)*it['qty']
        discount=0.0
        code=self.var_code.get().strip().upper()
        promo=self.app.db.find_promo(code) if code else None
        if promo:
            ptype=promo['type']; val=float(promo['value'] or 0); pid=promo['applies_to_product_id']
            if ptype in ("PERCENT_BILL","FLAT_BILL") and subtotal>=float(promo['min_spend'] or 0):
                discount = subtotal*(val/100.0) if ptype=="PERCENT_BILL" else min(val, subtotal)
            elif ptype in ("PERCENT_ITEM","FLAT_ITEM"):
                target=0.0
                for it in self.app.cart:
                    if it['product_id']==pid:
                        size_mult={"S":1.0,"M":1.2,"L":1.5}.get(it.get("size"),1.0)
                        base=float(it['base_price'])*size_mult
                        tops=sum(t['price']*t.get('qty',1) for t in it.get('toppings',[]))
                        target+=(base+tops)*it['qty']
                discount = target*(val/100.0) if ptype=="PERCENT_ITEM" else min(val, target)
        total=max(0.0, subtotal-discount)
        return subtotal, discount, total, promo

    def refresh(self):
        for i in self.tv.get_children(): self.tv.delete(i)
        for it in self.app.cart:
            size_mult={"S":1.0,"M":1.2,"L":1.5}.get(it.get("size"),1.0)
            base=float(it['base_price'])*size_mult
            tops=sum(t['price']*t.get('qty',1) for t in it.get('toppings',[]))
            line=(base+tops)*it['qty']
            self.tv.insert("", "end", values=(f"{it['name']} [{it.get('size','-')}/{it.get('sweetness','-')}]", it['qty'], f"{line:.2f}"))
        sub,dis,tot,_=self._totals()
        self.lbl_sub.config(text=f"Subtotal: {sub:.2f}")
        self.lbl_dis.config(text=f"Discount: {dis:.2f}")
        self.lbl_tot.config(text=f"Total: {tot:.2f}")

    def checkout(self):
        if not self.app.user: messagebox.showwarning("Login","Please sign in"); return
        if not self.app.cart: messagebox.showwarning("Cart","Cart empty"); return
        code=self.var_code.get().strip().upper()
        oid, sub, dis, tot = self.app.db.create_order(
            user_id=self.app.user['id'],
            channel=self.var_channel.get(), pickup_time=self.var_pickup.get().strip(),
            cart_items=self.app.cart, promo_code=code, payment_method="QR"
        )
        path = create_receipt_pdf(oid, self.app.db, self.app.user)
        messagebox.showinfo("Success", f"Order #{oid} placed.\nReceipt saved:\n{path}")
        self.app.cart.clear(); self.refresh(); self.app.show("Orders")

    def clear(self): self.app.cart.clear(); self.refresh()

class OrdersView(ttk.Frame):
    def __init__(self, master, app: App):
        super().__init__(master,padding=10); self.app=app
        ttk.Label(self,text="Order History",font=("Segoe UI",16,"bold")).pack(anchor="w")
        self.tv=ttk.Treeview(self,columns=("id","date","channel","total"),show="headings")
        for k,w in [("id",80),("date",160),("channel",100),("total",90)]:
            self.tv.heading(k,text=k.upper()); self.tv.column(k,width=w,anchor="w")
        self.tv.pack(fill="both",expand=True,pady=6)
        fr=ttk.Frame(self); fr.pack(anchor="e")
        ttk.Button(fr,text="Open Receipt",command=self.open).pack(side="right",padx=4)
        ttk.Button(fr,text="Refresh",command=self.refresh).pack(side="right",padx=4)
    def on_show(self): self.refresh()
    def refresh(self):
        for i in self.tv.get_children(): self.tv.delete(i)
        if not self.app.user: return
        for r in self.app.db.orders_of_user(self.app.user['id']):
            self.tv.insert("", "end", values=(r['id'], r['order_datetime'], r['channel'], f"{r['total']:.2f}"))
    def open(self):
        sel=self.tv.selection()
        if not sel: messagebox.showinfo("Open","Select an order"); return
        oid=int(self.tv.item(sel[0],"values")[0]); path=os.path.join(REPORTS_DIR,f"receipt_{oid}.pdf")
        if not os.path.exists(path): path=create_receipt_pdf(oid,self.app.db,self.app.user)
        try:
            if sys.platform.startswith("win"): os.startfile(path)
            elif sys.platform=="darwin": os.system(f"open '{path}'")
            else: os.system(f"xdg-open '{path}'")
        except: messagebox.showinfo("Receipt", f"Saved at: {path}")

class ProfileView(ttk.Frame):
    def __init__(self, master, app: App):
        super().__init__(master,padding=12); self.app=app
        ttk.Label(self,text="My Profile",font=("Segoe UI",16,"bold")).pack(anchor="w")
        container=ttk.Frame(self); container.pack(fill="x",pady=6)
        self.avatar_canvas=tk.Canvas(container,width=120,height=120,bg="#eee",highlightthickness=1,highlightbackground="#ddd")
        self.avatar_canvas.grid(row=0,column=0,rowspan=4,padx=8)
        ttk.Button(container,text="Change Avatar",command=self.change_avatar).grid(row=4,column=0,padx=8,pady=4)
        self.vars={}
        fields=[("name","Name"),("phone","Phone"),("email","Email"),("birthdate","Birthdate (YYYY-MM-DD)"),("gender","Gender")]
        for i,(k,label) in enumerate(fields):
            ttk.Label(container,text=label).grid(row=i,column=1,sticky="e",padx=6,pady=4)
            v=tk.StringVar(); ttk.Entry(container,textvariable=v,width=30).grid(row=i,column=2,pady=4)
            self.vars[k]=v
        fr=ttk.Frame(self); fr.pack(anchor="w",pady=6)
        ttk.Button(fr,text="Save Profile",command=self.save).pack(side="left")
        ttk.Button(fr,text="Change Password",command=self.change_pw).pack(side="left",padx=6)

    def on_show(self):
        u=self.app.user
        if not u: return
        for k in self.vars: self.vars[k].set(u[k] or "")
        self._draw_avatar(u['avatar'])

    def _draw_avatar(self, path):
        self.avatar_canvas.delete("all")
        img=load_photo(path,(120,120))
        if img:
            self._av=img; self.avatar_canvas.create_image(60,60,image=self._av)
        else:
            self.avatar_canvas.create_text(60,60,text="No Avatar")

    def change_avatar(self):
        if not self.app.user: return
        f=filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg")])
        if not f: return
        os.makedirs(IMG_AVATARS_DIR, exist_ok=True)
        dest=os.path.join(IMG_AVATARS_DIR, os.path.basename(f))
        try:
            shutil.copy2(f,dest)
            self.app.db.update_profile(self.app.user['id'], {"avatar":dest})
            self.app.user = self.app.db.conn.execute("SELECT * FROM users WHERE id=?", (self.app.user['id'],)).fetchone()
            self._draw_avatar(dest)
        except Exception as e:
            messagebox.showerror("Avatar", f"Copy failed: {e}")

    def save(self):
        if not self.app.user: return
        data={k:self.vars[k].get().strip() for k in self.vars}
        self.app.db.update_profile(self.app.user['id'], data)
        self.app.user = self.app.db.conn.execute("SELECT * FROM users WHERE id=?", (self.app.user['id'],)).fetchone()
        messagebox.showinfo("Saved","Profile updated")

    def change_pw(self):
        if not self.app.user: return
        np = simpledialog.askstring("Change Password","New password:", show="•")
        if not np: return
        self.app.db.change_password(self.app.user['id'], np)
        messagebox.showinfo("Password","Password updated")

class AdminView(ttk.Frame):
    def __init__(self, master, app: App):
        super().__init__(master,padding=8); self.app=app
        ttk.Label(self,text="Admin Panel",font=("Segoe UI",16,"bold")).pack(anchor="w")
        self.nb=ttk.Notebook(self); self.nb.pack(fill="both",expand=True)
        self.tab_products=ttk.Frame(self.nb,padding=8); self.nb.add(self.tab_products,text="Products")
        self.tab_inventory=ttk.Frame(self.nb,padding=8); self.nb.add(self.tab_inventory,text="Inventory")
        self.tab_promos=ttk.Frame(self.nb,padding=8); self.nb.add(self.tab_promos,text="Promotions")
        self.tab_reports=ttk.Frame(self.nb,padding=8); self.nb.add(self.tab_reports,text="Reports")
        self._products(); self._inventory(); self._promos(); self._reports()

    def on_show(self):
        if not self.app.user or self.app.user['role']!="admin":
            messagebox.showwarning("Permission","Admin only"); self.app.show("Login"); return
        self.reload_products(); self.reload_inventory(); self.reload_promos(); self.low_stock_banner()

    # --- Products tab ---
    def _products(self):
        top=ttk.Frame(self.tab_products); top.pack(fill="x")
        ttk.Button(top,text="Add",command=lambda:ProductEditor(self,self.app.db,None,self.reload_products)).pack(side="left")
        ttk.Button(top,text="Edit",command=self._edit).pack(side="left",padx=4)
        ttk.Button(top,text="Delete",command=self._delete).pack(side="left",padx=4)
        ttk.Button(top,text="Refresh",command=self.reload_products).pack(side="left",padx=4)
        self.tvp=ttk.Treeview(self.tab_products,columns=("id","name","category","price","image","active"),show="headings")
        for k,w in [("id",50),("name",160),("category",100),("price",80),("image",240),("active",60)]:
            self.tvp.heading(k,text=k.upper()); self.tvp.column(k,width=w,anchor="w")
        self.tvp.pack(fill="both",expand=True,pady=6)
    def reload_products(self):
        for i in self.tvp.get_children(): self.tvp.delete(i)
        for r in self.app.db.list_products():
            self.tvp.insert("", "end", values=(r['id'], r['name'], r['category_name'], f"{r['base_price']:.2f}", r['image'], r['is_active']))
    def _edit(self):
        sel=self.tvp.selection()
        if not sel: messagebox.showinfo("Edit","Select a product"); return
        pid=int(self.tvp.item(sel[0],"values")[0]); ProductEditor(self,self.app.db,pid,self.reload_products)
    def _delete(self):
        sel=self.tvp.selection()
        if not sel: messagebox.showinfo("Delete","Select a product"); return
        pid=int(self.tvp.item(sel[0],"values")[0])
        if messagebox.askyesno("Confirm","Delete product?"):
            self.app.db.delete_product(pid); self.reload_products()

    # --- Inventory tab ---
    def _inventory(self):
        self.banner=ttk.Label(self.tab_inventory,text="",style="Warn.TLabel"); self.banner.pack(anchor="w")
        top=ttk.Frame(self.tab_inventory); top.pack(fill="x")
        ttk.Button(top,text="Adjust +",command=lambda:self._adjust(1)).pack(side="left")
        ttk.Button(top,text="Adjust -",command=lambda:self._adjust(-1)).pack(side="left",padx=4)
        ttk.Button(top,text="Refresh",command=self.reload_inventory).pack(side="left",padx=4)
        self.tvi=ttk.Treeview(self.tab_inventory,columns=("id","name","qty","unit","reorder","cost"),show="headings")
        for k,w in [("id",50),("name",180),("qty",100),("unit",60),("reorder",80),("cost",80)]:
            self.tvi.heading(k,text=k.upper()); self.tvi.column(k,width=w,anchor="w")
        self.tvi.pack(fill="both",expand=True,pady=6)
    def reload_inventory(self):
        for i in self.tvi.get_children(): self.tvi.delete(i)
        for r in self.app.db.list_inventory():
            tag = "low" if float(r['qty_on_hand'])<=float(r['reorder_level']) and float(r['reorder_level'])>0 else ""
            self.tvi.insert("", "end", values=(r['id'], r['name'], f"{r['qty_on_hand']} {r['unit']}", r['unit'], r['reorder_level'], r['cost_per_unit']), tags=(tag,))
        self.tvi.tag_configure("low", background="#fff2e6")
    def _adjust(self, sign):
        sel=self.tvi.selection()
        if not sel: messagebox.showinfo("Adjust","Select an item"); return
        inv_id=int(self.tvi.item(sel[0],"values")[0])
        val=simpledialog.askfloat("Adjust","Quantity (+/-)")
        if val is None: return
        self.app.db.adjust_inventory(inv_id, sign*abs(val)); self.reload_inventory()
    def low_stock_banner(self):
        low=[]
        for r in self.app.db.list_inventory():
            if float(r['reorder_level'])>0 and float(r['qty_on_hand'])<=float(r['reorder_level']):
                low.append(r['name'])
        self.banner.config(text=("Low stock: "+", ".join(low)) if low else "")

    # --- Promotions tab ---
    def _promos(self):
        top=ttk.Frame(self.tab_promos); top.pack(fill="x")
        ttk.Button(top,text="Add",command=lambda:PromoEditor(self,self.app.db,None,self.reload_promos)).pack(side="left")
        ttk.Button(top,text="Edit",command=self._edit_p).pack(side="left",padx=4)
        ttk.Button(top,text="Delete",command=self._del_p).pack(side="left",padx=4)
        ttk.Button(top,text="Refresh",command=self.reload_promos).pack(side="left",padx=4)
        self.tvpr=ttk.Treeview(self.tab_promos,columns=("id","code","type","value","min","start","end","prod","active"),show="headings")
        heads=[("id",50),("code",120),("type",120),("value",80),("min",80),("start",140),("end",140),("prod",80),("active",60)]
        for k,w in heads: self.tvpr.heading(k,text=k.upper()); self.tvpr.column(k,width=w,anchor="w")
        self.tvpr.pack(fill="both",expand=True,pady=6)
    def reload_promos(self):
        for i in self.tvpr.get_children(): self.tvpr.delete(i)
        for r in self.app.db.list_promotions():
            self.tvpr.insert("", "end", values=(r['id'],r['code'],r['type'],r['value'],r['min_spend'],r['start_at'],r['end_at'],r['applies_to_product_id'] or "-",r['is_active']))
    def _edit_p(self):
        sel=self.tvpr.selection()
        if not sel: messagebox.showinfo("Edit","Select a promotion"); return
        pid=int(self.tvpr.item(sel[0],"values")[0]); PromoEditor(self,self.app.db,pid,self.reload_promos)
    def _del_p(self):
        sel=self.tvpr.selection()
        if not sel: messagebox.showinfo("Delete","Select a promotion"); return
        pid=int(self.tvpr.item(sel[0],"values")[0])
        if messagebox.askyesno("Confirm","Delete promotion?"):
            self.app.db.delete_promotion(pid); self.reload_promos()

    # --- Reports tab ---
    def _reports(self):
        fr=ttk.Frame(self.tab_reports); fr.pack(fill="x")
        self.var_start=tk.StringVar(value=dt.now().strftime("%Y-%m-01"))
        self.var_end=tk.StringVar(value=dt.now().strftime("%Y-%m-%d"))
        ttk.Label(fr,text="Start (YYYY-MM-DD)").grid(row=0,column=0,sticky="w")
        ttk.Entry(fr,textvariable=self.var_start,width=12).grid(row=0,column=1,padx=6)
        ttk.Label(fr,text="End").grid(row=0,column=2,sticky="w")
        ttk.Entry(fr,textvariable=self.var_end,width=12).grid(row=0,column=3,padx=6)
        ttk.Button(fr,text="Daily Total",command=self.run_daily).grid(row=0,column=4,padx=6)
        ttk.Button(fr,text="By Category",command=self.run_cat).grid(row=0,column=5,padx=6)
        ttk.Button(fr,text="By Product",command=self.run_prod).grid(row=0,column=6,padx=6)
        ttk.Button(fr,text="Top Customers",command=self.run_top).grid(row=0,column=7,padx=6)
        ttk.Button(fr,text="Gross Margin",command=self.run_margin).grid(row=0,column=8,padx=6)
        self.tvr=ttk.Treeview(self.tab_reports,columns=("col1","col2","col3"),show="headings")
        self.tvr.pack(fill="both",expand=True,pady=6)

    def _fill(self, headers, rows):
        self.tvr["columns"]=tuple(f"c{i}" for i in range(len(headers)))
        self.tvr["show"]="headings"
        for i in self.tvr.get_children(): self.tvr.delete(i)
        for i,h in enumerate(headers):
            self.tvr.heading(f"c{i}", text=h); self.tvr.column(f"c{i}", width=160, anchor="w")
        for r in rows:
            self.tvr.insert("", "end", values=tuple(r))

    def run_daily(self):
        s=self.var_start.get().strip(); e=self.var_end.get().strip()
        rows=[(r['d'], f"{(r['total'] or 0):.2f}") for r in self.app.db.report_total_by_date(s,e)]
        self._fill(["DATE","TOTAL"], rows)
    def run_cat(self):
        s=self.var_start.get().strip(); e=self.var_end.get().strip()
        rows=[(r['category'], f"{(r['sales'] or 0):.2f}") for r in self.app.db.report_by_category(s,e)]
        self._fill(["CATEGORY","SALES"], rows)
    def run_prod(self):
        s=self.var_start.get().strip(); e=self.var_end.get().strip()
        rows=[(r['product'], r['qty'], f"{(r['sales'] or 0):.2f}") for r in self.app.db.report_by_product(s,e)]
        self._fill(["PRODUCT","QTY","SALES"], rows)
    def run_top(self):
        s=self.var_start.get().strip(); e=self.var_end.get().strip()
        rows=[(r['username'] or "", r['name'] or "", f"{(r['total'] or 0):.2f}") for r in self.app.db.report_top_customers(s,e)]
        self._fill(["USERNAME","NAME","TOTAL"], rows)
    def run_margin(self):
        s=self.var_start.get().strip(); e=self.var_end.get().strip()
        r=self.app.db.report_gross_margin(s,e)
        rows=[("Revenue", f"{(r['revenue'] or 0):.2f}"), ("Cost", f"{(r['cost'] or 0):.2f}"), ("Gross Profit", f"{(r['gross_profit'] or 0):.2f}")]
        self._fill(["METRIC","VALUE"], rows)

# ---------- Editors ----------
class ProductEditor(tk.Toplevel):
    def __init__(self, master, db: DB, pid, on_done):
        super().__init__(master); self.db=db; self.pid=pid; self.on_done=on_done
        self.title("Product Editor"); self.geometry("460x400")
        frm=ttk.Frame(self,padding=10); frm.pack(fill="both",expand=True)
        ttk.Label(frm,text="Name").grid(row=0,column=0,sticky="e"); self.en=ttk.Entry(frm,width=30); self.en.grid(row=0,column=1,pady=4)
        ttk.Label(frm,text="Category").grid(row=1,column=0,sticky="e")
        cats=db.categories(); self.cat_map={c['name']:c['id'] for c in cats}
        self.ec=ttk.Combobox(frm,values=list(self.cat_map.keys()),state="readonly",width=27); self.ec.grid(row=1,column=1,pady=4)
        ttk.Label(frm,text="Base Price").grid(row=2,column=0,sticky="e"); self.ep=ttk.Entry(frm,width=30); self.ep.grid(row=2,column=1,pady=4)
        ttk.Label(frm,text="Image").grid(row=3,column=0,sticky="e"); self.ei=ttk.Entry(frm,width=30); self.ei.grid(row=3,column=1,pady=4)
        ttk.Button(frm,text="Choose Image...",command=self.choose_img).grid(row=3,column=2,padx=4)
        ttk.Label(frm,text="Active (1/0)").grid(row=4,column=0,sticky="e"); self.ea=ttk.Entry(frm,width=30); self.ea.grid(row=4,column=1,pady=4)
        ttk.Button(frm,text="Save",command=self.save).grid(row=5,column=1,pady=8)

        if pid:
            r=db.conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
            if r:
                self.en.insert(0, r['name'])
                cname=db.conn.execute("SELECT name FROM categories WHERE id=?", (r['category_id'],)).fetchone()
                self.ec.set(cname['name'] if cname else "")
                self.ep.insert(0, str(r['base_price'])); self.ei.insert(0, r['image'] or ""); self.ea.insert(0, str(r['is_active']))

    def choose_img(self):
        f=filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg")])
        if not f: return
        dest=os.path.join(IMG_PRODUCTS_DIR, os.path.basename(f))
        try: shutil.copy2(f,dest); self.ei.delete(0,"end"); self.ei.insert(0,dest)
        except Exception as e: messagebox.showerror("Image", f"Copy failed: {e}")

    def save(self):
        name=self.en.get().strip(); cat=self.ec.get().strip()
        price=float(self.ep.get().strip() or 0); img=self.ei.get().strip(); act=int(self.ea.get().strip() or 1)
        if not name or not cat: messagebox.showerror("Error","Name/Category required"); return
        self.db.upsert_product(self.pid, name, self.cat_map[cat], price, img, act)
        messagebox.showinfo("Saved","Product saved"); self.on_done(); self.destroy()

class PromoEditor(tk.Toplevel):
    def __init__(self, master, db: DB, pid, on_done):
        super().__init__(master); self.db=db; self.pid=pid; self.on_done=on_done
        self.title("Promotion Editor"); self.geometry("520x320")
        frm=ttk.Frame(self,padding=10); frm.pack(fill="both",expand=True)
        fields=[
            ("Code","code"),("Type [PERCENT_BILL/FLAT_BILL/PERCENT_ITEM/FLAT_ITEM]","type"),
            ("Value","value"),("Min Spend","min"),
            ("Start (YYYY-MM-DD HH:MM:SS)","start"),("End","end"),
            ("Applies to Product ID (for *_ITEM)","prod"),("Active 1/0","act")
        ]
        self.inp={}
        for i,(label,key) in enumerate(fields):
            ttk.Label(frm,text=label).grid(row=i,column=0,sticky="e"); e=ttk.Entry(frm,width=38); e.grid(row=i,column=1,pady=3); self.inp[key]=e
        ttk.Button(frm,text="Save",command=self.save).grid(row=len(fields),column=1,pady=8,sticky="e")

        if pid:
            r=db.conn.execute("SELECT * FROM promotions WHERE id=?", (pid,)).fetchone()
            if r:
                self.inp["code"].insert(0, r['code'])
                self.inp["type"].insert(0, r['type'])
                self.inp["value"].insert(0, str(r['value']))
                self.inp["min"].insert(0, str(r['min_spend']))
                self.inp["start"].insert(0, r['start_at'])
                self.inp["end"].insert(0, r['end_at'])
                self.inp["prod"].insert(0, "" if r['applies_to_product_id'] is None else str(r['applies_to_product_id']))
                self.inp["act"].insert(0, str(r['is_active']))

    def save(self):
        code=self.inp["code"].get().strip().upper()
        ptype=self.inp["type"].get().strip()
        value=float(self.inp["value"].get().strip() or 0)
        min_spend=float(self.inp["min"].get().strip() or 0)
        start=self.inp["start"].get().strip() or (dt.now().strftime("%Y-%m-%d 00:00:00"))
        end=self.inp["end"].get().strip() or (dt.now()+timedelta(days=365)).strftime("%Y-%m-%d 23:59:59")
        prod=self.inp["prod"].get().strip()
        applies=int(prod) if prod.isdigit() else None
        act=int(self.inp["act"].get().strip() or 1)
        if not code or ptype not in ("PERCENT_BILL","FLAT_BILL","PERCENT_ITEM","FLAT_ITEM"):
            messagebox.showerror("Error","Invalid code/type"); return
        self.db.upsert_promotion(self.pid, code, ptype, value, min_spend, start, end, applies, act)
        messagebox.showinfo("Saved","Promotion saved"); self.on_done(); self.destroy()

# -*- coding: utf-8 -*-
"""
Auth screens using customtkinter (rounded/modern, cream theme, uppercase)
- Left: image cover on Canvas (draw image + white titles with no background).
- Right: rounded cream card; Sign Up uses 2-column compact form (balanced height).
- Validations: username/phone/email/password per spec.
- DB: SQLite users table (compatible). SHA-256 password.

Run: python auth_ctk_round.py
"""

import os, re, sqlite3, hashlib
from typing import Optional, Callable
from PIL import Image, ImageTk
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox

APP_TITLE = "TASTE AND SIP"

# ===== Palette & sizing =====
RIGHT_BG   = "#f8eedb"   # cream tone (page background)
CARD_BG    = "#edd8b8"   # deeper cream for card
TEXT_DARK  = "#1f2937"
LINK_FG    = "#0057b7"
BORDER     = "#d3c6b4"
CARD_W     = 660
CARD_H     = 560
RADIUS     = 18          # ความโค้งมน

# ===== Regex rules =====
USERNAME_RE = re.compile(r"^[A-Za-z0-9]{6,}$")
PHONE_RE    = re.compile(r"^\d{10}$")
EMAIL_RE    = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PWD_RE      = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,}$")

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

# ====== Data Layer ======
class AuthDB:
    def __init__(self, path: str = "taste_and_sip.db"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self):
        c = self.conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT, phone TEXT, email TEXT, birthdate TEXT, gender TEXT,
                avatar TEXT, role TEXT DEFAULT 'customer'
            )
            """
        )
        self.conn.commit()

    def find_user_for_login(self, username: str, password: str) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM users WHERE username=? AND password_hash=?",
            (username, sha256(password)),
        ).fetchone()

    def username_exists(self, username: str) -> bool:
        return self.conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone() is not None

    def create_user(self, username: str, phone: str, email: str, password: str):
        self.conn.execute(
            "INSERT INTO users(username, password_hash, phone, email, role) VALUES(?,?,?,?,?)",
            (username, sha256(password), phone, email, "customer"),
        )
        self.conn.commit()

    def verify_user_contact(self, username: str, email_or_phone: str) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM users WHERE username=? AND (email=? OR phone=?)",
            (username, email_or_phone, email_or_phone),
        ).fetchone()

    def change_password(self, username: str, new_password: str):
        self.conn.execute(
            "UPDATE users SET password_hash=? WHERE username=?",
            (sha256(new_password), username),
        )
        self.conn.commit()

# ====== Validation ======
def validate_username(v: str) -> Optional[str]:
    if not USERNAME_RE.match(v or ""):
        return "USERNAME MUST BE AT LEAST 6 CHARACTERS AND CONTAIN ONLY A–Z AND 0–9."
    return None

def validate_phone(v: str) -> Optional[str]:
    if not PHONE_RE.match(v or ""):
        return "PHONE MUST BE 10 DIGITS."
    return None

def validate_email(v: str) -> Optional[str]:
    if not EMAIL_RE.match(v or ""):
        return "INVALID EMAIL FORMAT."
    return None

def validate_password(v: str) -> Optional[str]:
    if not PWD_RE.match(v or ""):
        return "PASSWORD MUST BE ≥ 8 CHARS, INCLUDE UPPERCASE, LOWERCASE AND A DIGIT (LETTERS/DIGITS ONLY)."
    return None

# ====== UI (customtkinter) ======
class AuthApp(ctk.CTk):
    def __init__(self, db_path: str = "taste_and_sip.db", left_bg_path: Optional[str] = None,
                 logo_path: Optional[str] = None,
                 on_login_success: Optional[Callable[[sqlite3.Row], None]] = None):
        super().__init__()
        ctk.set_appearance_mode("light")
        self.title(APP_TITLE)
        try:
            self.state("zoomed")
        except Exception:
            self.geometry("1200x720")
        self.configure(fg_color=RIGHT_BG)

        self.db = AuthDB(db_path)
        self.on_login_success = on_login_success
        self.left_bg_path = left_bg_path
        self.logo_path = logo_path

        # Grid: 2 columns
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # -------- Left (Canvas draws image + white text, no background boxes) --------
        self.left = ctk.CTkFrame(self, fg_color=RIGHT_BG, corner_radius=0)
        self.left.grid(row=0, column=0, sticky="nsew")

        # canvas วาดรูปและข้อความ (transparent text)
        self.left_canvas = tk.Canvas(self.left, highlightthickness=0, bd=0, bg=RIGHT_BG)
        self.left_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self._left_img_tk = None
        self.left.bind("<Configure>", lambda e: self._draw_left_bg())

        # -------- Right (logo + rounded card) --------
        self.right = ctk.CTkFrame(self, fg_color=RIGHT_BG, corner_radius=0)
        self.right.grid(row=0, column=1, sticky="nsew")
        self.right.grid_rowconfigure(1, weight=1)
        self.right.grid_columnconfigure(0, weight=1)

        self.logo_wrap = ctk.CTkFrame(self.right, fg_color=RIGHT_BG, corner_radius=0)
        self.logo_wrap.grid(row=0, column=0, pady=(30, 10))
        self._render_logo()

        # Card (rounded)
        self.card = ctk.CTkFrame(
            self.right, fg_color=CARD_BG, corner_radius=RADIUS, border_color=BORDER, border_width=1,
            width=CARD_W, height=CARD_H
        )
        self.card.grid(row=1, column=0, sticky="n", padx=80, pady=(10, 40))
        self.card.grid_propagate(False)
        self.card.grid_columnconfigure(0, weight=1)

        self.show_signin()

    # ---- Left image drawing (cover + titles on the same canvas) ----
    def _draw_left_bg(self):
        c = self.left_canvas
        c.delete("all")

        w = max(300, int(self.winfo_width() * 0.5))
        h = max(300, self.winfo_height())
        c.configure(width=w, height=h)
        c.create_rectangle(0, 0, w, h, fill=RIGHT_BG, outline="")

        if self.left_bg_path and os.path.exists(self.left_bg_path):
            try:
                img = Image.open(self.left_bg_path).convert("RGB")
                iw, ih = img.size
                scale = max(w / iw, h / ih)
                nw, nh = int(iw * scale), int(ih * scale)
                img = img.resize((nw, nh), Image.LANCZOS)
                left = max(0, (nw - w) // 2)
                top  = max(0, (nh - h) // 2)
                img  = img.crop((left, top, left + w, top + h))
                self._left_img_tk = ImageTk.PhotoImage(img)
                c.create_image(0, 0, anchor="nw", image=self._left_img_tk)
            except Exception:
                pass

        # ข้อความสีขาว “ลอย” บนภาพ (ไม่มีพื้นหลัง)
        t1 = c.create_text(
            28, 28, anchor="nw", fill="white",
            font=("Segoe UI", 36, "bold"),
            text=f"WELCOME TO\n{APP_TITLE}".upper()
        )
        bbox = c.bbox(t1)
        y2 = (bbox[3] if bbox else 120) + 18
        c.create_text(32, y2, anchor="nw", fill="white",
                      font=("Segoe UI", 18, "bold"),
                      text="FOOD AND DRINK!".upper())

    def _render_logo(self):
        for w in self.logo_wrap.winfo_children():
            w.destroy()
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                img = Image.open(self.logo_path)
                self._logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(220, 220))
                ctk.CTkLabel(self.logo_wrap, image=self._logo_img, text="", fg_color="transparent").pack()
                return
            except Exception:
                pass
        ctk.CTkLabel(self.logo_wrap, text=APP_TITLE.upper(),
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=TEXT_DARK,
                     fg_color="transparent").pack()

    # ---- Card helpers ----
    def _clear_card(self):
        for w in self.card.winfo_children():
            w.destroy()
        self.card.grid_columnconfigure(0, weight=1)

    def show_signin(self):
        self._clear_card()
        Title(self.card, "SIGN IN").pack(pady=(22, 6))
        self.si_err = ErrorLabel(self.card); self.si_err.pack(padx=28, fill="x")
        self.si_user = LabeledEntry(self.card, "USERNAME"); self.si_user.pack(fill="x", padx=28, pady=(6, 8))
        self.si_pwd  = LabeledEntry(self.card, "PASSWORD", show="•"); self.si_pwd.pack(fill="x", padx=28, pady=(6, 12))
        SubmitBtn(self.card, "SIGN IN", command=self._signin).pack(fill="x", padx=28, pady=(0, 12))
        bottom = ctk.CTkFrame(self.card, fg_color="transparent"); bottom.pack(fill="x", pady=(4, 18))
        LinkBtn(bottom, "FORGOT PASSWORD?", command=self.show_forgot).pack(side="left", padx=4)
        LinkBtn(bottom, "CREATE ACCOUNT", command=self.show_signup).pack(side="right", padx=4)

    def show_signup(self):
        self._clear_card()
        Title(self.card, "CREATE ACCOUNT").pack(pady=(22, 6))
        self.su_err = ErrorLabel(self.card); self.su_err.pack(padx=24, fill="x")

        form = ctk.CTkFrame(self.card, fg_color="transparent")
        form.pack(fill="x", padx=24, pady=(6, 10))
        form.grid_columnconfigure(0, weight=1, uniform="c")
        form.grid_columnconfigure(1, weight=1, uniform="c")

        self.su_user  = LabeledEntry(form, "USERNAME");  self.su_user.grid(row=0, column=0, padx=8, pady=6, sticky="ew")
        self.su_phone = LabeledEntry(form, "PHONE");     self.su_phone.grid(row=0, column=1, padx=8, pady=6, sticky="ew")
        self.su_email = LabeledEntry(form, "EMAIL");     self.su_email.grid(row=1, column=0, columnspan=2, padx=8, pady=6, sticky="ew")
        self.su_pwd1  = LabeledEntry(form, "PASSWORD", show="•"); self.su_pwd1.grid(row=2, column=0, padx=8, pady=6, sticky="ew")
        self.su_pwd2  = LabeledEntry(form, "CONFIRM PASSWORD", show="•"); self.su_pwd2.grid(row=2, column=1, padx=8, pady=6, sticky="ew")

        SubmitBtn(self.card, "REGISTER", command=self._signup).pack(fill="x", padx=24, pady=(8, 12))
        LinkBtn(self.card, "BACK TO LOGIN", command=self.show_signin).pack(pady=(0, 18))

    def show_forgot(self):
        self._clear_card()
        Title(self.card, "FORGOT PASSWORD").pack(pady=(22, 6))
        self.fp_err = ErrorLabel(self.card); self.fp_err.pack(padx=24, fill="x")
        self.fp_user = LabeledEntry(self.card, "USERNAME"); self.fp_user.pack(fill="x", padx=24, pady=(6, 8))
        self.fp_contact = LabeledEntry(self.card, "EMAIL OR PHONE"); self.fp_contact.pack(fill="x", padx=24, pady=(6, 10))
        SubmitBtn(self.card, "VERIFY", command=self._forgot_verify).pack(fill="x", padx=24, pady=(0, 12))

        self.fp_step2 = ctk.CTkFrame(self.card, fg_color="transparent"); self.fp_step2.pack(fill="x", padx=16, pady=(6, 12))
        self.fp_step2.grid_columnconfigure(0, weight=1)
        self.fp_step2.pack_forget()

        self.fp_pwd1 = LabeledEntry(self.fp_step2, "NEW PASSWORD", show="•"); self.fp_pwd1.pack(fill="x", padx=12, pady=(6, 8))
        self.fp_pwd2 = LabeledEntry(self.fp_step2, "CONFIRM NEW PASSWORD", show="•"); self.fp_pwd2.pack(fill="x", padx=12, pady=(6, 10))
        SubmitBtn(self.fp_step2, "CHANGE PASSWORD", command=self._forgot_change).pack(fill="x", padx=12, pady=(0, 10))

        LinkBtn(self.card, "BACK TO LOGIN", command=self.show_signin).pack(pady=(0, 18))
        self._verified_username = None

    # --- Actions ---
    def _signin(self):
        self.si_err.set("")
        u = (self.si_user.get() or "").strip(); p = (self.si_pwd.get() or "").strip()
        if not u or not p:
            self.si_err.set("PLEASE ENTER USERNAME AND PASSWORD."); return
        row = self.db.find_user_for_login(u, p)
        if row:
            if self.on_login_success: self.on_login_success(row)
            else: messagebox.showinfo("SUCCESS", f"WELCOME, {u}!")
        else:
            self.si_err.set("INVALID CREDENTIALS.")

    def _signup(self):
        self.su_err.set("")
        u  = (self.su_user.get() or "").strip()
        ph = (self.su_phone.get() or "").strip()
        em = (self.su_email.get() or "").strip()
        p1 = (self.su_pwd1.get() or "").strip()
        p2 = (self.su_pwd2.get() or "").strip()
        for fn in (lambda: validate_username(u), lambda: validate_phone(ph), lambda: validate_email(em), lambda: validate_password(p1)):
            msg = fn()
            if msg: self.su_err.set(msg); return
        if p1 != p2:
            self.su_err.set("PASSWORDS DO NOT MATCH."); return
        if self.db.username_exists(u):
            self.su_err.set("USERNAME ALREADY EXISTS."); return
        try:
            self.db.create_user(u, ph, em, p1)
            self.su_err.set("ACCOUNT CREATED. PLEASE SIGN IN.")
        except sqlite3.IntegrityError:
            self.su_err.set("USERNAME ALREADY EXISTS.")
        except Exception as e:
            self.su_err.set(f"FAILED TO REGISTER: {e}")

    def _forgot_verify(self):
        self.fp_err.set("")
        u = (self.fp_user.get() or "").strip(); cp = (self.fp_contact.get() or "").strip()
        if not u or not cp:
            self.fp_err.set("PLEASE FILL USERNAME AND EMAIL/PHONE."); return
        row = self.db.verify_user_contact(u, cp)
        if row:
            self._verified_username = u
            self.fp_err.set("VERIFIED. PLEASE SET A NEW PASSWORD BELOW.")
            self.fp_step2.pack(fill="x", padx=16, pady=(6, 12))
        else:
            self.fp_err.set("NO MATCHING ACCOUNT FOR THE GIVEN USERNAME AND EMAIL/PHONE.")

    def _forgot_change(self):
        if not self._verified_username:
            self.fp_err.set("PLEASE VERIFY FIRST."); return
        p1 = (self.fp_pwd1.get() or "").strip(); p2 = (self.fp_pwd2.get() or "").strip()
        msg = validate_password(p1)
        if msg: self.fp_err.set(msg); return
        if p1 != p2: self.fp_err.set("PASSWORDS DO NOT MATCH."); return
        try:
            self.db.change_password(self._verified_username, p1)
            self.fp_err.set("PASSWORD CHANGED. YOU CAN SIGN IN NOW.")
        except Exception as e:
            self.fp_err.set(f"FAILED TO CHANGE PASSWORD: {e}")

# ====== Reusable UI pieces (rounded) ======
class Title(ctk.CTkLabel):
    def __init__(self, master, text: str):
        super().__init__(master, text=text.upper(),
                         font=ctk.CTkFont(size=20, weight="bold"),
                         text_color=TEXT_DARK,
                         fg_color="transparent")

class ErrorLabel(ctk.CTkLabel):
    def __init__(self, master):
        super().__init__(master, text="", text_color="#b00020", wraplength=560, justify="left", fg_color="transparent")
    def set(self, text: str):
        self.configure(text=(text or "").upper())

class LabeledEntry(ctk.CTkFrame):
    def __init__(self, master, label: str, show: str = ""):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=label.upper(), text_color="#333333",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     fg_color="transparent").grid(row=0, column=0, sticky="w", padx=2, pady=(0,2))
        self.entry = ctk.CTkEntry(self, show=show, corner_radius=RADIUS,
                                  border_color=BORDER, fg_color="white")
        self.entry.grid(row=1, column=0, sticky="ew")

    def get(self) -> str:
        return self.entry.get()

    def set(self, v: str):
        self.entry.delete(0, "end"); self.entry.insert(0, v)

class SubmitBtn(ctk.CTkButton):
    def __init__(self, master, text: str, command):
        super().__init__(master, text=text.upper(), command=command,
                         height=44, corner_radius=RADIUS,
                         fg_color="#f6e8d3", hover_color="#f6e8d3",
                         text_color=TEXT_DARK, border_color=BORDER, border_width=1)

class LinkBtn(ctk.CTkButton):
    def __init__(self, master, text: str, command):
        super().__init__(master, text=text.upper(), command=command,
                         height=36, corner_radius=RADIUS,
                         fg_color="transparent", hover_color="#e9dcc6",
                         text_color=LINK_FG)

# ====== Standalone run ======
if __name__ == "__main__":
    LEFT_BG_PATH = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\AVIBRA_1.png"
    LOGO_PATH    = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\lologogo.png-removebg-preview.png"

    def _demo_success(user_row):
        messagebox.showinfo("SIGNED IN", f"HELLO, {user_row['username']}!")

    app = AuthApp(db_path="taste_and_sip.db", left_bg_path=LEFT_BG_PATH, logo_path=LOGO_PATH,
                  on_login_success=_demo_success)
    app.mainloop()