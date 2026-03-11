# -*- coding: utf-8 -*-
"""
TASTE & SIP — CustomTkinter (Cream/Minimal, Rounded)
- เพิ่ม "ค้นหาเมนู" ในหน้า Shop (Search + Enter + Clear)
- ลูกค้า: Add to Cart ทันที (ไม่มีตัวเลือกความหวาน/ท็อปปิ้ง)
- แอดมิน: Products / Inventory / Promotions / Reports / Orders
"""

import os, sys, json, sqlite3, hashlib, shutil
from datetime import datetime as dt, timedelta

from PIL import Image
import customtkinter as ctk

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
    import hashlib as _h
    return _h.sha256(s.encode("utf-8")).hexdigest()

def now_ts():
    return dt.now().strftime("%Y-%m-%d %H:%M:%S")

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

        c.execute("""CREATE TABLE IF NOT EXISTS product_options(
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
        # toppings (schema ยังอยู่ แต่ UI ไม่ใช้)
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

        # options เดิมยัง seed ไว้แต่หน้า Shop ไม่ใช้
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

    # --- catalog ---
    def categories(self): return self.conn.execute("SELECT * FROM categories").fetchall()
    def products_by_cat(self, cid):
        return self.conn.execute("SELECT * FROM products WHERE category_id=? AND is_active=1",(cid,)).fetchall()

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
        for it in cart_items:
            base = float(it['base_price'])
            subtotal += base * it['qty']

        discount = 0.0
        promo = self.find_promo(promo_code) if promo_code else None
        if promo:
            msp = float(promo['min_spend'] or 0)
            ptype = promo['type']
            val = float(promo['value'] or 0)
            if ptype in ("PERCENT_BILL","FLAT_BILL") and subtotal >= msp:
                discount = subtotal*(val/100.0) if ptype=="PERCENT_BILL" else min(val, subtotal)
            elif ptype in ("PERCENT_ITEM","FLAT_ITEM"):
                pid = promo['applies_to_product_id']
                target = sum(it['base_price'] * it['qty'] for it in cart_items if it['product_id']==pid)
                if target>0:
                    discount = target*(val/100.0) if ptype=="PERCENT_ITEM" else min(val, target)

        total = max(0.0, subtotal - discount)

        cur = self.conn.cursor()
        cur.execute("""INSERT INTO orders(user_id,order_datetime,channel,pickup_time,subtotal,discount,total,payment_method,status)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (user_id, now_ts(), channel, pickup_time or "", subtotal, discount, total, payment_method, "PAID"))
        order_id = cur.lastrowid
        for it in cart_items:
            cur.execute("""INSERT INTO order_items(order_id,product_id,qty,unit_price,options_json,note)
                           VALUES(?,?,?,?,?,?)""",
                        (order_id, it['product_id'], it['qty'], it['base_price'], json.dumps({}), it.get('note','')))
        cur.execute("INSERT INTO payments(order_id,method,amount,paid_at,ref) VALUES(?,?,?,?,?)",
                    (order_id, payment_method, total, now_ts(), ""))
        self.conn.commit()
        self.deduct_for_order(order_id)
        return order_id, subtotal, discount, total

    def orders_of_user(self, uid, limit=200):
        return self.conn.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ?", (uid, limit)).fetchall()

    def order_detail(self, oid):
        o = self.conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        items = self.conn.execute("""SELECT oi.*, p.name AS product_name
                                     FROM order_items oi JOIN products p ON p.id=oi.product_id
                                     WHERE order_id=?""",(oid,)).fetchall()
        tops = []  # not used
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

    def all_orders(self, start=None, end=None):
        if start and end:
            return self.conn.execute("""
               SELECT o.*, u.username
               FROM orders o JOIN users u ON u.id=o.user_id
               WHERE o.order_datetime BETWEEN ? AND ?
               ORDER BY o.id DESC
            """,(start+" 00:00:00", end+" 23:59:59")).fetchall()
        return self.conn.execute("""
            SELECT o.*, u.username
            FROM orders o JOIN users u ON u.id=o.user_id
            ORDER BY o.id DESC LIMIT 200
        """).fetchall()

# ======================= RECEIPT (PDF) =======================
def create_receipt_pdf(order_id, db: DB, user_row):
    ensure_dirs()
    path = os.path.join(REPORTS_DIR, f"receipt_{order_id}.pdf")
    canv = pdfcanvas.Canvas(path, pagesize=A4)
    W, H = A4; x = 18*mm; y = H-18*mm

    order, items, _ = db.order_detail(order_id)
    canv.setFont("Helvetica-Bold", 16); canv.drawString(x, y, "TASTE AND SIP - RECEIPT"); y -= 10*mm
    canv.setFont("Helvetica", 10)
    canv.drawString(x, y, f"Order ID: {order_id}"); y -= 5*mm
    canv.drawString(x, y, f"Date/Time: {order['order_datetime']}"); y -= 5*mm
    canv.drawString(x, y, f"Customer: {user_row['name'] or user_row['username']}"); y -= 8*mm

    canv.setFont("Helvetica-Bold", 12); canv.drawString(x, y, "Items"); y -= 6*mm
    canv.setFont("Helvetica", 10)
    for it in items:
        canv.drawString(x, y, f"- {it['product_name']} x{it['qty']} (Unit: {it['unit_price']:.2f})"); y -= 6*mm

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

# ======================= UI helpers =======================
RIGHT_BG   = "#f8eedb"
CARD_BG    = "#edd8b8"
BORDER     = "#d3c6b4"
TEXT_DARK  = "#1f2937"
RADIUS     = 18

def ctk_image_or_none(path, size):
    if not path or not os.path.exists(path): return None
    try:
        img = Image.open(path)
        return ctk.CTkImage(light_image=img, size=size)
    except Exception:
        return None

class InfoBar(ctk.CTkLabel):
    def __init__(self, master):
        super().__init__(master, text="", corner_radius=RADIUS, padx=10, pady=8,
                         fg_color="#fde2e2", text_color="#b00020",
                         font=ctk.CTkFont(size=12, weight="bold"))
    def set(self, text: str, ok: bool=False):
        self.configure(text=(text or "").upper(),
                       fg_color=("#d9f99d" if ok else "#fde2e2"),
                       text_color=("#166534" if ok else "#b00020"))

class Line(ctk.CTkFrame):
    def __init__(self, master, pad=6):
        super().__init__(master, fg_color=BORDER, height=1)
        self.pack(fill="x", padx=pad, pady=8)

# ======================= Product Card (CTk) =======================
class ProductCard(ctk.CTkFrame):
    def __init__(self, master, row, on_add):
        super().__init__(master, corner_radius=RADIUS, fg_color="#fff", border_width=1, border_color=BORDER)
        self.row=row; self.on_add=on_add
        self.grid_columnconfigure(0, weight=1)
        img = ctk_image_or_none(row['image'], (160,120))
        if img:
            ctk.CTkLabel(self, image=img, text="").grid(row=0, column=0, padx=10, pady=(10,4))
            self._img=img
        else:
            ctk.CTkLabel(self, text="[NO IMAGE]", text_color="#6b7280").grid(row=0, column=0, padx=10, pady=(28,8))
        ctk.CTkLabel(self, text=row['name'], text_color=TEXT_DARK,
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=1, column=0, pady=(0,2))
        ctk.CTkLabel(self, text=f"{row['base_price']:.2f} ฿",
                     text_color="#0a7", font=ctk.CTkFont(size=13, weight="bold")).grid(row=2, column=0)
        addrow = ctk.CTkFrame(self, fg_color="transparent"); addrow.grid(row=3, column=0, pady=8)
        ctk.CTkLabel(addrow, text="Qty").pack(side="left", padx=(0,6))
        self.qty = ctk.IntVar(value=1)
        qty_ent = ctk.CTkEntry(addrow, width=60, textvariable=self.qty, corner_radius=RADIUS, border_color=BORDER)
        qty_ent.pack(side="left")
        ctk.CTkButton(self, text="ADD TO CART", corner_radius=RADIUS,
                      command=self._add, fg_color=CARD_BG, text_color=TEXT_DARK, border_color=BORDER, border_width=1)\
            .grid(row=4, column=0, padx=12, pady=(2,12), sticky="ew")
    def _add(self):
        q=max(1,int(self.qty.get() or 1))
        self.on_add({
            "product_id": self.row['id'],
            "name": self.row['name'],
            "base_price": float(self.row['base_price']),
            "qty": q,
            "note": ""
        })

# ======================= Auth (CTk) =======================
class AuthWindow(ctk.CTk):
    def __init__(self, on_success):
        super().__init__()
        ctk.set_appearance_mode("light")
        self.title(APP_TITLE)
        try: self.state("zoomed")
        except: self.geometry("1200x720")
        self.configure(fg_color=RIGHT_BG)
        ensure_dirs()
        self.db=DB()
        self.on_success = on_success

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # left image
        self.left = ctk.CTkFrame(self, fg_color="#000")
        self.left.grid(row=0, column=0, sticky="nsew")
        self.left.bind("<Configure>", lambda e: self._paint_left())

        # right card
        self.right = ctk.CTkFrame(self, fg_color=RIGHT_BG)
        self.right.grid(row=0, column=1, sticky="nsew")
        self.right.grid_rowconfigure(2, weight=1)
        self.logo_wrap = ctk.CTkFrame(self.right, fg_color=RIGHT_BG); self.logo_wrap.grid(row=0, column=0, pady=(28,8))
        self._render_logo()

        self.card = ctk.CTkFrame(self.right, fg_color="#fff", corner_radius=RADIUS, border_width=1, border_color=BORDER, width=640, height=480)
        self.card.grid(row=1, column=0, sticky="n", padx=60, pady=10); self.card.grid_propagate(False)
        self._make_login()

    def _render_logo(self):
        for w in self.logo_wrap.winfo_children(): w.destroy()
        img = ctk_image_or_none(LOGO_PATH, (220,220))
        if img: ctk.CTkLabel(self.logo_wrap, image=img, text="", fg_color="transparent").pack(); self._logo = img
        else:   ctk.CTkLabel(self.logo_wrap, text=APP_TITLE, font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT_DARK).pack()

    def _paint_left(self):
        for w in self.left.winfo_children(): w.destroy()
        w, h = self.left.winfo_width(), self.left.winfo_height()
        holder = ctk.CTkFrame(self.left, fg_color="#000"); holder.place(relx=0, rely=0, relwidth=1, relheight=1)
        img = ctk_image_or_none(LEFT_BG_PATH, (max(1,w), max(1,h)))
        if img: ctk.CTkLabel(holder, image=img, text="").place(relx=0, rely=0, relwidth=1, relheight=1); self._bg = img
        overlay = ctk.CTkFrame(holder, fg_color="#00000088"); overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        ctk.CTkLabel(overlay, text=f"WELCOME TO\n{APP_TITLE}".upper(), text_color="white",
                     font=ctk.CTkFont(size=36, weight="bold")).place(x=28, y=28)
        ctk.CTkLabel(overlay, text="FOOD AND DRINK!", text_color="white", font=ctk.CTkFont(size=18, weight="bold")).place(x=32, y=110)

    def _make_login(self):
        for w in self.card.winfo_children(): w.destroy()
        ctk.CTkLabel(self.card, text="SIGN IN", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(22,6))
        self.info = InfoBar(self.card); self.info.pack(fill="x", padx=24, pady=(0,8)); self.info.set("")
        self.euser = ctk.CTkEntry(self.card, placeholder_text="USERNAME", height=44, width=420,
                                  border_color=BORDER, corner_radius=RADIUS); self.euser.pack(pady=8)
        self.epass = ctk.CTkEntry(self.card, placeholder_text="PASSWORD", show="•", height=44, width=420,
                                  border_color=BORDER, corner_radius=RADIUS); self.epass.pack(pady=(0,12))
        ctk.CTkButton(self.card, text="SIGN IN", corner_radius=RADIUS, fg_color=CARD_BG, text_color=TEXT_DARK,
                      border_color=BORDER, border_width=1, command=self._signin).pack(pady=(0,8))
        ctk.CTkButton(self.card, text="CREATE ACCOUNT", corner_radius=RADIUS, fg_color="transparent",
                      text_color="#0057b7", command=self._make_register).pack()

    def _make_register(self):
        for w in self.card.winfo_children(): w.destroy()
        ctk.CTkLabel(self.card, text="CREATE ACCOUNT", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(22,6))
        self.info = InfoBar(self.card); self.info.pack(fill="x", padx=24, pady=(0,8)); self.info.set("")
        self.ru = ctk.CTkEntry(self.card, placeholder_text="USERNAME", height=44, width=420,
                               border_color=BORDER, corner_radius=RADIUS); self.ru.pack(pady=8)
        self.rp1= ctk.CTkEntry(self.card, placeholder_text="PASSWORD", show="•", height=44, width=420,
                               border_color=BORDER, corner_radius=RADIUS); self.rp1.pack(pady=8)
        self.rp2= ctk.CTkEntry(self.card, placeholder_text="CONFIRM PASSWORD", show="•", height=44, width=420,
                               border_color=BORDER, corner_radius=RADIUS); self.rp2.pack(pady=(0,12))
        ctk.CTkButton(self.card, text="REGISTER", corner_radius=RADIUS, fg_color=CARD_BG, text_color=TEXT_DARK,
                      border_color=BORDER, border_width=1, command=self._register).pack(pady=(0,8))
        ctk.CTkButton(self.card, text="BACK TO LOGIN", corner_radius=RADIUS, fg_color="transparent",
                      text_color="#0057b7", command=self._make_login).pack()

    def _signin(self):
        u = (self.euser.get() or "").strip(); p = (self.epass.get() or "").strip()
        if not u or not p: self.info.set("PLEASE ENTER USERNAME AND PASSWORD."); return
        row = self.db.auth(u, p)
        if row:
            self.info.set("WELCOME!", ok=True)
            self.destroy()
            MainApp(self.db, row).mainloop()
        else:
            self.info.set("INVALID CREDENTIALS.")

    def _register(self):
        u = (self.ru.get() or "").strip(); p1 = (self.rp1.get() or "").strip(); p2 = (self.rp2.get() or "").strip()
        if not u or not p1 or not p2: self.info.set("FILL ALL FIELDS."); return
        if p1 != p2: self.info.set("PASSWORDS DO NOT MATCH."); return
        ok, msg = self.db.create_user(u, p1)
        if ok:
            self.info.set("ACCOUNT CREATED. PLEASE SIGN IN.", ok=True)
            self._make_login()
        else:
            self.info.set(msg)

# ======================= Main App (CTk) =======================
class MainApp(ctk.CTk):
    def __init__(self, db: DB, user_row):
        super().__init__()
        ctk.set_appearance_mode("light")
        self.title(APP_TITLE)
        try: self.state("zoomed")
        except: self.geometry("1280x800")
        self.configure(fg_color=RIGHT_BG)

        self.db = db
        self.user = user_row
        self.cart = []

        # top bar
        top = ctk.CTkFrame(self, fg_color=RIGHT_BG)
        top.pack(side="top", fill="x", padx=10, pady=10)
        self.lbl_user = ctk.CTkLabel(top, text=f"{self.user['username']} ({self.user['role']})",
                                     text_color=TEXT_DARK, font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_user.pack(side="left")
        ctk.CTkButton(top, text="Shop", command=lambda:self.show("shop"),
                      fg_color=CARD_BG, text_color=TEXT_DARK, corner_radius=RADIUS).pack(side="left", padx=6)
        ctk.CTkButton(top, text="Orders", command=lambda:self.show("orders"),
                      fg_color=CARD_BG, text_color=TEXT_DARK, corner_radius=RADIUS).pack(side="left", padx=6)
        ctk.CTkButton(top, text="Profile", command=lambda:self.show("profile"),
                      fg_color=CARD_BG, text_color=TEXT_DARK, corner_radius=RADIUS).pack(side="left", padx=6)
        self.btn_admin = ctk.CTkButton(top, text="Admin", command=lambda:self.show("admin"),
                                       fg_color=CARD_BG, text_color=TEXT_DARK, corner_radius=RADIUS,
                                       state=("normal" if self.user['role']=="admin" else "disabled"))
        self.btn_admin.pack(side="left", padx=6)
        ctk.CTkButton(top, text="Logout", command=self.logout, fg_color="#fef3c7",
                      text_color="#b91c1c", corner_radius=RADIUS).pack(side="right")

        # content
        self.content = ctk.CTkFrame(self, fg_color=RIGHT_BG)
        self.content.pack(fill="both", expand=True)
        self.frames={}
        self.frames["shop"]    = ShopView(self.content, self)
        self.frames["orders"]  = OrdersView(self.content, self)
        self.frames["profile"] = ProfileView(self.content, self)
        self.frames["admin"]   = AdminView(self.content, self)
        for name, f in self.frames.items():
            f.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.show("shop")

    def show(self, name):
        self.frames[name].tkraise()
        if hasattr(self.frames[name], "on_show"): self.frames[name].on_show()

    def logout(self):
        self.destroy()
        AuthWindow(on_success=None).mainloop()

# ======================= Views =======================
class ShopView(ctk.CTkFrame):
    def __init__(self, master, app: MainApp):
        super().__init__(master, fg_color=RIGHT_BG)
        self.app=app

        # Left column
        left_col = ctk.CTkFrame(self, fg_color=RIGHT_BG)
        left_col.pack(side="left", fill="both", expand=True, padx=(10,6), pady=(0,10))

        # ---- Search bar (NEW) ----
        search_bar = ctk.CTkFrame(left_col, fg_color="#fff", corner_radius=RADIUS, border_width=1, border_color=BORDER)
        search_bar.pack(fill="x", padx=4, pady=(6,2))
        search_bar.grid_columnconfigure(0, weight=1)
        self.search_var = ctk.StringVar()
        ent = ctk.CTkEntry(search_bar, textvariable=self.search_var, placeholder_text="ค้นหาเมนู (เช่น pad, tea, mango ...)",
                           height=40, corner_radius=RADIUS, border_color=BORDER)
        ent.grid(row=0, column=0, padx=8, pady=8, sticky="ew")
        ent.bind("<Return>", lambda e: self._build_tabs())  # กด Enter เพื่อค้นหา
        ctk.CTkButton(search_bar, text="Search", width=100, corner_radius=RADIUS,
                      fg_color=CARD_BG, text_color=TEXT_DARK, command=self._build_tabs).grid(row=0, column=1, padx=(0,8), pady=8)
        ctk.CTkButton(search_bar, text="Clear", width=80, corner_radius=RADIUS,
                      fg_color="#f1e5cf", text_color=TEXT_DARK, command=self._clear_search).grid(row=0, column=2, padx=(0,8), pady=8)

        # Tabs
        self.tabs = ctk.CTkTabview(left_col, fg_color=RIGHT_BG, segmented_button_selected_color=CARD_BG,
                                   segmented_button_unselected_color="#f1e5cf", segmented_button_unselected_hover_color="#e9dcc6",
                                   corner_radius=RADIUS)
        self.tabs.pack(fill="both", expand=True, padx=4, pady=4)

        # Right: cart
        right = ctk.CTkFrame(self, fg_color=RIGHT_BG)
        right.pack(side="left", fill="y", padx=(6,10), pady=(0,10))

        ctk.CTkLabel(right, text="Cart", font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=TEXT_DARK).pack(anchor="w", padx=6, pady=(6,0))
        self.cart_list = ctk.CTkScrollableFrame(right, fg_color="#fff", corner_radius=RADIUS,
                                                border_width=1, border_color=BORDER, width=360, height=420)
        self.cart_list.pack(pady=8, padx=6)

        # promo + channel
        form = ctk.CTkFrame(right, fg_color="#fff", corner_radius=RADIUS, border_width=1, border_color=BORDER)
        form.pack(fill="x", padx=6, pady=6)
        form.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(form, text="Promo Code").grid(row=0, column=0, sticky="w", padx=10, pady=(10,2))
        self.var_code = ctk.StringVar()
        ctk.CTkEntry(form, textvariable=self.var_code, corner_radius=RADIUS, border_color=BORDER, height=36).grid(row=0, column=1, padx=10, pady=(10,2), sticky="ew")
        ctk.CTkButton(form, text="Apply", command=self.refresh, corner_radius=RADIUS, fg_color=CARD_BG, text_color=TEXT_DARK,
                      border_color=BORDER, border_width=1).grid(row=0, column=2, padx=10, pady=(10,2))

        ctk.CTkLabel(form, text="Channel").grid(row=1, column=0, sticky="w", padx=10, pady=4)
        self.var_channel = ctk.StringVar(value="INSTORE")
        ctk.CTkOptionMenu(form, variable=self.var_channel, values=["INSTORE","PICKUP","DELIVERY"],
                          corner_radius=RADIUS, fg_color=CARD_BG, text_color=TEXT_DARK).grid(row=1, column=1, padx=10, pady=4, sticky="w")
        ctk.CTkLabel(form, text="Pickup Time").grid(row=2, column=0, sticky="w", padx=10, pady=(4,10))
        self.var_pickup = ctk.StringVar(value=(dt.now()+timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M"))
        ctk.CTkEntry(form, textvariable=self.var_pickup, corner_radius=RADIUS, border_color=BORDER, height=36).grid(row=2, column=1, padx=10, pady=(4,10), sticky="w")

        # totals
        self.lbl_sub = ctk.CTkLabel(right, text="Subtotal: 0.00", text_color=TEXT_DARK)
        self.lbl_dis = ctk.CTkLabel(right, text="Discount: 0.00", text_color=TEXT_DARK)
        self.lbl_tot = ctk.CTkLabel(right, text="Total: 0.00", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_DARK)
        self.lbl_sub.pack(anchor="e", padx=12); self.lbl_dis.pack(anchor="e", padx=12); self.lbl_tot.pack(anchor="e", padx=12)

        Line(right, pad=6)

        # QR
        ctk.CTkLabel(right, text="Payment: QR", text_color=TEXT_DARK).pack(anchor="w", padx=6)
        self.qr_holder = ctk.CTkFrame(right, fg_color="#fff", corner_radius=RADIUS, border_width=1, border_color=BORDER)
        self.qr_holder.pack(padx=6, pady=6)
        self._draw_qr()

        ctk.CTkButton(right, text="Checkout & Pay", command=self.checkout,
                      corner_radius=RADIUS, fg_color="#fde68a", text_color=TEXT_DARK)\
            .pack(fill="x", padx=6, pady=(6,4))
        ctk.CTkButton(right, text="Clear Cart", command=self.clear,
                      corner_radius=RADIUS, fg_color="#fee2e2", text_color="#991b1b")\
            .pack(fill="x", padx=6)

    def on_show(self):
        self._build_tabs()
        self.refresh()

    def _clear_search(self):
        self.search_var.set("")
        self._build_tabs()

    def _draw_qr(self):
        for w in self.qr_holder.winfo_children(): w.destroy()
        img = ctk_image_or_none(IMG_QR_PATH, (180,180))
        if img:
            ctk.CTkLabel(self.qr_holder, image=img, text="").pack(padx=8, pady=8); self._qr = img
        else:
            ctk.CTkLabel(self.qr_holder, text="QR Placeholder\nassets/images/qr.png", text_color="#6b7280").pack(padx=24, pady=24)

    def _build_tabs(self):
        # clear tabs
        for t in list(self.tabs._tab_dict.keys()):
            self.tabs.delete(t)

        query = (self.search_var.get() or "").strip().lower()

        for cat in self.app.db.categories():
            tab = self.tabs.add(cat['name'])
            wrap = ctk.CTkScrollableFrame(tab, fg_color="transparent")
            wrap.pack(fill="both", expand=True, padx=6, pady=6)
            col=0; row_frame=None; shown=0

            for i, p in enumerate(self.app.db.products_by_cat(cat['id'])):
                # filter by search text
                if query and query not in (p['name'] or "").lower():
                    continue
                if shown % 3 == 0:
                    row_frame = ctk.CTkFrame(wrap, fg_color="transparent")
                    row_frame.pack(fill="x")
                    col=0
                card = ProductCard(row_frame, p, self.add)
                card.grid(row=0, column=col, padx=6, pady=6, sticky="n")
                col+=1; shown+=1

            if shown == 0:
                ctk.CTkLabel(wrap, text="ไม่พบสินค้าในหมวดนี้ตามคำค้น", text_color="#6b7280").pack(pady=12)

    def add(self, item):
        for it in self.app.cart:
            if it['product_id']==item['product_id'] and it.get('note','')==item.get('note',''):
                it['qty'] += item['qty']
                break
        else:
            self.app.cart.append(item)
        self.refresh()

    def _totals(self):
        subtotal = sum(it['base_price']*it['qty'] for it in self.app.cart)
        code = (self.var_code.get() or "").strip().upper()
        discount = 0.0
        promo = self.app.db.find_promo(code) if code else None
        if promo:
            ptype=promo['type']; val=float(promo['value'] or 0)
            if ptype in ("PERCENT_BILL","FLAT_BILL") and subtotal>=float(promo['min_spend'] or 0):
                discount = subtotal*(val/100.0) if ptype=="PERCENT_BILL" else min(val, subtotal)
            elif ptype in ("PERCENT_ITEM","FLAT_ITEM"):
                pid = promo['applies_to_product_id']
                target = sum(it['base_price']*it['qty'] for it in self.app.cart if it['product_id']==pid)
                discount = target*(val/100.0) if ptype=="PERCENT_ITEM" else min(val, target)
        total = max(0.0, subtotal-discount)
        return subtotal, discount, total

    def _render_cart(self):
        for w in self.cart_list.winfo_children(): w.destroy()
        if not self.app.cart:
            ctk.CTkLabel(self.cart_list, text="No items in cart.", text_color="#6b7280").pack(pady=12)
            return
        for idx, it in enumerate(self.app.cart):
            row = ctk.CTkFrame(self.cart_list, fg_color="#fff")
            row.pack(fill="x", padx=6, pady=4)
            ctk.CTkLabel(row, text=f"{it['name']}", text_color=TEXT_DARK).pack(side="left", padx=6)
            ctk.CTkLabel(row, text=f"x{it['qty']}", width=40, anchor="e").pack(side="left")
            line = it['base_price']*it['qty']
            ctk.CTkLabel(row, text=f"{line:.2f}", width=80, anchor="e").pack(side="right", padx=(0,6))
            def _mk_dec(i=idx):
                return lambda: self._dec(i)
            def _mk_inc(i=idx):
                return lambda: self._inc(i)
            def _mk_del(i=idx):
                return lambda: self._del(i)
            ctk.CTkButton(row, text="-", width=28, command=_mk_dec(), corner_radius=RADIUS,
                          fg_color="#f1e5cf", text_color=TEXT_DARK).pack(side="right", padx=2)
            ctk.CTkButton(row, text="+", width=28, command=_mk_inc(), corner_radius=RADIUS,
                          fg_color="#f1e5cf", text_color=TEXT_DARK).pack(side="right", padx=2)
            ctk.CTkButton(row, text="✕", width=28, command=_mk_del(), corner_radius=RADIUS,
                          fg_color="#fee2e2", text_color="#991b1b").pack(side="right", padx=2)

    def _inc(self, i):
        self.app.cart[i]['qty'] += 1; self.refresh()
    def _dec(self, i):
        self.app.cart[i]['qty'] = max(1, self.app.cart[i]['qty']-1); self.refresh()
    def _del(self, i):
        del self.app.cart[i]; self.refresh()

    def refresh(self):
        self._render_cart()
        sub, dis, tot = self._totals()
        self.lbl_sub.configure(text=f"Subtotal: {sub:.2f}")
        self.lbl_dis.configure(text=f"Discount: {dis:.2f}")
        self.lbl_tot.configure(text=f"Total: {tot:.2f}")

    def checkout(self):
        if not self.app.user or not self.app.cart:
            return
        code = (self.var_code.get() or "").strip().upper()
        oid, sub, dis, tot = self.app.db.create_order(
            user_id=self.app.user['id'],
            channel=self.var_channel.get(), pickup_time=(self.var_pickup.get() or "").strip(),
            cart_items=self.app.cart, promo_code=code, payment_method="QR"
        )
        create_receipt_pdf(oid, self.app.db, self.app.user)
        self.app.cart.clear(); self.refresh(); self.app.frames["orders"].on_show()

    def clear(self):
        self.app.cart.clear(); self.refresh()

class OrdersView(ctk.CTkFrame):
    def __init__(self, master, app: MainApp):
        super().__init__(master, fg_color=RIGHT_BG); self.app=app
        ctk.CTkLabel(self, text="Order History", font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=TEXT_DARK).pack(anchor="w", padx=12, pady=(6,0))
        self.list = ctk.CTkScrollableFrame(self, fg_color="#fff", corner_radius=RADIUS,
                                           border_width=1, border_color=BORDER)
        self.list.pack(fill="both", expand=True, padx=12, pady=8)
        self.info = InfoBar(self); self.info.pack(fill="x", padx=12, pady=(0,8)); self.info.set("")

    def on_show(self):
        for w in self.list.winfo_children(): w.destroy()
        if not self.app.user: return
        rows = self.app.db.orders_of_user(self.app.user['id'])
        if not rows:
            ctk.CTkLabel(self.list, text="No orders.", text_color="#6b7280").pack(pady=12)
            return
        for r in rows:
            row = ctk.CTkFrame(self.list, fg_color="#fff"); row.pack(fill="x", padx=6, pady=4)
            ctk.CTkLabel(row, text=f"#{r['id']}  {r['order_datetime']}  [{r['channel']}]", text_color=TEXT_DARK)\
                .pack(side="left", padx=6)
            ctk.CTkLabel(row, text=f"{r['total']:.2f}", width=100, anchor="e").pack(side="right", padx=6)
            def _open(o=r['id']):
                return lambda: self._open_receipt(o)
            ctk.CTkButton(row, text="Open Receipt", corner_radius=RADIUS,
                          fg_color=CARD_BG, text_color=TEXT_DARK, command=_open()).pack(side="right", padx=6)

    def _open_receipt(self, oid):
        path=os.path.join(REPORTS_DIR,f"receipt_{oid}.pdf")
        if not os.path.exists(path): create_receipt_pdf(oid,self.app.db,self.app.user)
        try:
            if sys.platform.startswith("win"): os.startfile(path)
            elif sys.platform=="darwin": os.system(f"open '{path}'")
            else: os.system(f"xdg-open '{path}'")
        except:
            self.info.set(f"RECEIPT SAVED AT: {path}", ok=True)

class ProfileView(ctk.CTkFrame):
    def __init__(self, master, app: MainApp):
        super().__init__(master, fg_color=RIGHT_BG); self.app=app
        ctk.CTkLabel(self, text="My Profile", font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=TEXT_DARK).pack(anchor="w", padx=12, pady=(6,0))
        body = ctk.CTkFrame(self, fg_color="#fff", corner_radius=RADIUS, border_width=1, border_color=BORDER)
        body.pack(fill="x", padx=12, pady=8)
        body.grid_columnconfigure(1, weight=1)

        self.avatar_box = ctk.CTkLabel(body, text="No Avatar", width=120, height=120, corner_radius=RADIUS,
                                       fg_color="#eee", text_color="#6b7280")
        self.avatar_box.grid(row=0, column=0, rowspan=4, padx=12, pady=12, sticky="n")
        ctk.CTkButton(body, text="Change Avatar", command=self.change_avatar, corner_radius=RADIUS,
                      fg_color=CARD_BG, text_color=TEXT_DARK).grid(row=4, column=0, padx=12, pady=6)

        self.vars={}
        fields=[("name","Name"),("phone","Phone"),("email","Email"),("birthdate","Birthdate (YYYY-MM-DD)"),("gender","Gender")]
        for i,(k,label) in enumerate(fields):
            ctk.CTkLabel(body, text=label, text_color=TEXT_DARK).grid(row=i, column=1, sticky="w", padx=8, pady=6)
            v=ctk.StringVar(); ctk.CTkEntry(body, textvariable=v, height=36, corner_radius=RADIUS, border_color=BORDER)\
                .grid(row=i, column=2, sticky="w", padx=8, pady=6)
            self.vars[k]=v

        actions = ctk.CTkFrame(self, fg_color="transparent"); actions.pack(anchor="w", padx=12, pady=6)
        ctk.CTkButton(actions, text="Save Profile", command=self.save, corner_radius=RADIUS,
                      fg_color=CARD_BG, text_color=TEXT_DARK).pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Change Password", command=self.change_pw, corner_radius=RADIUS,
                      fg_color="#fde68a", text_color=TEXT_DARK).pack(side="left", padx=4)

        self.info = InfoBar(self); self.info.pack(fill="x", padx=12, pady=(0,8)); self.info.set("")

    def on_show(self):
        u=self.app.user
        if not u: return
        for k in self.vars: self.vars[k].set(u[k] or "")
        self._draw_avatar(u['avatar'])

    def _draw_avatar(self, path):
        img = ctk_image_or_none(path,(120,120))
        if img:
            self.avatar_box.configure(image=img, text=""); self._av = img
        else:
            self.avatar_box.configure(image=None, text="No Avatar")

    def change_avatar(self):
        import tkinter.filedialog as fd
        f = fd.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg")])
        if not f: return
        os.makedirs(IMG_AVATARS_DIR, exist_ok=True)
        dest=os.path.join(IMG_AVATARS_DIR, os.path.basename(f))
        try:
            shutil.copy2(f,dest)
            self.app.db.update_profile(self.app.user['id'], {"avatar":dest})
            self.app.user = self.app.db.conn.execute("SELECT * FROM users WHERE id=?", (self.app.user['id'],)).fetchone()
            self._draw_avatar(dest)
            self.info.set("AVATAR UPDATED.", ok=True)
        except Exception as e:
            self.info.set(f"AVATAR COPY FAILED: {e}")

    def save(self):
        data={k:self.vars[k].get().strip() for k in self.vars}
        self.app.db.update_profile(self.app.user['id'], data)
        self.app.user = self.app.db.conn.execute("SELECT * FROM users WHERE id=?", (self.app.user['id'],)).fetchone()
        self.info.set("PROFILE UPDATED.", ok=True)

    def change_pw(self):
        d = ctk.CTkInputDialog(text="New password:", title="Change Password")
        np = d.get_input()
        if not np: return
        self.app.db.change_password(self.app.user['id'], np)
        self.info.set("PASSWORD UPDATED.", ok=True)

class AdminView(ctk.CTkFrame):
    def __init__(self, master, app: MainApp):
        super().__init__(master, fg_color=RIGHT_BG); self.app=app
        ctk.CTkLabel(self, text="Admin Panel", font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=TEXT_DARK).pack(anchor="w", padx=12, pady=(6,0))
        self.tabs = ctk.CTkTabview(self, fg_color=RIGHT_BG, segmented_button_selected_color=CARD_BG,
                                   segmented_button_unselected_color="#f1e5cf",
                                   segmented_button_unselected_hover_color="#e9dcc6",
                                   corner_radius=RADIUS)
        self.tabs.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_products = self.tabs.add("Products")
        self.tab_inventory= self.tabs.add("Inventory")
        self.tab_promos   = self.tabs.add("Promotions")
        self.tab_reports  = self.tabs.add("Reports")
        self.tab_orders   = self.tabs.add("Orders")

        self._products()
        self._inventory()
        self._promos()
        self._reports()
        self._orders()

    def on_show(self):
        if not self.app.user or self.app.user['role']!="admin":
            return
        self.reload_products(); self.reload_inventory(); self.reload_promos(); self.load_orders()

    # -------- Products --------
    def _products(self):
        bar = ctk.CTkFrame(self.tab_products, fg_color="transparent"); bar.pack(fill="x", padx=6, pady=6)
        ctk.CTkButton(bar, text="Add", command=lambda:self._open_product_editor(None),
                      corner_radius=RADIUS, fg_color=CARD_BG, text_color=TEXT_DARK).pack(side="left")
        ctk.CTkButton(bar, text="Refresh", command=self.reload_products,
                      corner_radius=RADIUS, fg_color="#f1e5cf", text_color=TEXT_DARK).pack(side="left", padx=6)

        self.prod_list = ctk.CTkScrollableFrame(self.tab_products, fg_color="#fff", corner_radius=RADIUS,
                                                border_width=1, border_color=BORDER)
        self.prod_list.pack(fill="both", expand=True, padx=8, pady=6)

    def reload_products(self):
        for w in self.prod_list.winfo_children(): w.destroy()
        rows = self.app.db.list_products()
        if not rows:
            ctk.CTkLabel(self.prod_list, text="No products.", text_color="#6b7280").pack(pady=12); return
        for r in rows:
            row = ctk.CTkFrame(self.prod_list, fg_color="#fff"); row.pack(fill="x", padx=6, pady=4)
            ctk.CTkLabel(row, text=f"[{r['id']}] {r['name']}  ({r['category_name']})  {r['base_price']:.2f} ฿  {'ACTIVE' if r['is_active'] else 'OFF'}",
                         text_color=TEXT_DARK).pack(side="left", padx=6)
            def _edit(pid=r['id']):
                return lambda: self._open_product_editor(pid)
            def _del(pid=r['id']):
                return lambda: self._delete_product(pid)
            ctk.CTkButton(row, text="Edit", command=_edit(), corner_radius=RADIUS,
                          fg_color=CARD_BG, text_color=TEXT_DARK, width=64).pack(side="right", padx=4)
            ctk.CTkButton(row, text="Delete", command=_del(), corner_radius=RADIUS,
                          fg_color="#fee2e2", text_color="#991b1b", width=64).pack(side="right", padx=4)

    def _open_product_editor(self, pid):
        ProductEditor(self, self.app.db, pid, self.reload_products)

    def _delete_product(self, pid):
        self.app.db.delete_product(pid); self.reload_products()

    # -------- Inventory --------
    def _inventory(self):
        bar = ctk.CTkFrame(self.tab_inventory, fg_color="transparent"); bar.pack(fill="x", padx=6, pady=6)
        ctk.CTkButton(bar, text="Adjust +", command=lambda:self._adjust(+1),
                      corner_radius=RADIUS, fg_color=CARD_BG, text_color=TEXT_DARK).pack(side="left")
        ctk.CTkButton(bar, text="Adjust -", command=lambda:self._adjust(-1),
                      corner_radius=RADIUS, fg_color=CARD_BG, text_color=TEXT_DARK).pack(side="left", padx=6)
        ctk.CTkButton(bar, text="Refresh", command=self.reload_inventory,
                      corner_radius=RADIUS, fg_color="#f1e5cf", text_color=TEXT_DARK).pack(side="left", padx=6)

        self.inv_list = ctk.CTkScrollableFrame(self.tab_inventory, fg_color="#fff", corner_radius=RADIUS,
                                               border_width=1, border_color=BORDER)
        self.inv_list.pack(fill="both", expand=True, padx=8, pady=6)
        self.low_banner = ctk.CTkLabel(self.tab_inventory, text="", text_color="#b45309")
        self.low_banner.pack(anchor="w", padx=8)

    def reload_inventory(self):
        for w in self.inv_list.winfo_children(): w.destroy()
        low=[]
        for r in self.app.db.list_inventory():
            tag_low = (float(r['reorder_level'])>0 and float(r['qty_on_hand'])<=float(r['reorder_level']))
            if tag_low: low.append(r['name'])
            row = ctk.CTkFrame(self.inv_list, fg_color="#fff"); row.pack(fill="x", padx=6, pady=4)
            ctk.CTkLabel(row, text=f"[{r['id']}] {r['name']}  {r['qty_on_hand']} {r['unit']}  (reorder {r['reorder_level']})  cost {r['cost_per_unit']}",
                         text_color=(("#b45309") if tag_low else TEXT_DARK)).pack(side="left", padx=6)
            def _adj(i=r['id'], sign=+1):
                return lambda: self._adjust_input(i, sign)
            ctk.CTkButton(row, text="+", width=28, command=_adj(r['id'],+1), corner_radius=RADIUS,
                          fg_color="#f1e5cf", text_color=TEXT_DARK).pack(side="right", padx=2)
            ctk.CTkButton(row, text="-", width=28, command=_adj(r['id'],-1), corner_radius=RADIUS,
                          fg_color="#f1e5cf", text_color=TEXT_DARK).pack(side="right", padx=2)
        self.low_banner.configure(text=("Low stock: "+", ".join(low)) if low else "")

    def _adjust(self, sign):
        AdjustDialog(self, sign, on_ok=self._adjust_apply)

    def _adjust_input(self, inv_id, sign):
        AdjustDialog(self, sign, on_ok=lambda amount: self._adjust_apply(amount, inv_id))

    def _adjust_apply(self, amount, inv_id=None):
        try:
            amount = float(amount)
        except:
            return
        if inv_id is None:
            return
        self.app.db.adjust_inventory(inv_id, amount)
        self.reload_inventory()

    # -------- Promotions --------
    def _promos(self):
        bar = ctk.CTkFrame(self.tab_promos, fg_color="transparent"); bar.pack(fill="x", padx=6, pady=6)
        ctk.CTkButton(bar, text="Add", command=lambda:self._open_promo_editor(None),
                      corner_radius=RADIUS, fg_color=CARD_BG, text_color=TEXT_DARK).pack(side="left")
        ctk.CTkButton(bar, text="Refresh", command=self.reload_promos,
                      corner_radius=RADIUS, fg_color="#f1e5cf", text_color=TEXT_DARK).pack(side="left", padx=6)

        self.pro_list = ctk.CTkScrollableFrame(self.tab_promos, fg_color="#fff", corner_radius=RADIUS,
                                               border_width=1, border_color=BORDER)
        self.pro_list.pack(fill="both", expand=True, padx=8, pady=6)

    def reload_promos(self):
        for w in self.pro_list.winfo_children(): w.destroy()
        rows = self.app.db.list_promotions()
        if not rows: ctk.CTkLabel(self.pro_list, text="No promotions.", text_color="#6b7280").pack(pady=12); return
        for r in rows:
            row = ctk.CTkFrame(self.pro_list, fg_color="#fff"); row.pack(fill="x", padx=6, pady=4)
            ctk.CTkLabel(row, text=f"[{r['id']}] {r['code']}  {r['type']}  value={r['value']}  min={r['min_spend']}  active={r['is_active']}",
                         text_color=TEXT_DARK).pack(side="left", padx=6)
            def _edit(pid=r['id']):
                return lambda: self._open_promo_editor(pid)
            def _del(pid=r['id']):
                return lambda: self._delete_promo(pid)
            ctk.CTkButton(row, text="Edit", command=_edit(), corner_radius=RADIUS,
                          fg_color=CARD_BG, text_color=TEXT_DARK, width=64).pack(side="right", padx=4)
            ctk.CTkButton(row, text="Delete", command=_del(), corner_radius=RADIUS,
                          fg_color="#fee2e2", text_color="#991b1b", width=64).pack(side="right", padx=4)

    def _open_promo_editor(self, pid):
        PromoEditor(self, self.app.db, pid, self.reload_promos)

    def _delete_promo(self, pid):
        self.app.db.delete_promotion(pid); self.reload_promos()

    # -------- Reports --------
    def _reports(self):
        frm = ctk.CTkFrame(self.tab_reports, fg_color="#fff", corner_radius=RADIUS, border_width=1, border_color=BORDER)
        frm.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(frm, text="Start (YYYY-MM-DD)").grid(row=0, column=0, padx=10, pady=8, sticky="w")
        ctk.CTkLabel(frm, text="End").grid(row=0, column=2, padx=10, pady=8, sticky="w")
        self.var_start = ctk.StringVar(value=dt.now().strftime("%Y-%m-01"))
        self.var_end   = ctk.StringVar(value=dt.now().strftime("%Y-%m-%d"))
        ctk.CTkEntry(frm, textvariable=self.var_start, corner_radius=RADIUS, border_color=BORDER, width=140).grid(row=0, column=1, pady=8, sticky="w")
        ctk.CTkEntry(frm, textvariable=self.var_end, corner_radius=RADIUS, border_color=BORDER, width=140).grid(row=0, column=3, pady=8, sticky="w")

        btns = ctk.CTkFrame(frm, fg_color="transparent"); btns.grid(row=0, column=4, padx=10)
        for label, fn in [("Daily Total", self.run_daily), ("By Category", self.run_cat),
                          ("By Product", self.run_prod), ("Top Customers", self.run_top)]:
            ctk.CTkButton(btns, text=label, command=fn, corner_radius=RADIUS, fg_color=CARD_BG, text_color=TEXT_DARK).pack(side="left", padx=4)

        self.rep_list = ctk.CTkScrollableFrame(self.tab_reports, fg_color="#fff", corner_radius=RADIUS,
                                               border_width=1, border_color=BORDER)
        self.rep_list.pack(fill="both", expand=True, padx=8, pady=8)

    def _fill(self, headers, rows):
        for w in self.rep_list.winfo_children(): w.destroy()
        head = ctk.CTkFrame(self.rep_list, fg_color="#faf5e6"); head.pack(fill="x", padx=6, pady=6)
        for h in headers:
            ctk.CTkLabel(head, text=h, width=200, anchor="w", text_color=TEXT_DARK, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=8)
        for r in rows:
            row = ctk.CTkFrame(self.rep_list, fg_color="#fff"); row.pack(fill="x", padx=6, pady=2)
            for val in r:
                ctk.CTkLabel(row, text=str(val), width=200, anchor="w").pack(side="left", padx=8)

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

    # -------- Orders (Admin) --------
    def _orders(self):
        frm = ctk.CTkFrame(self.tab_orders, fg_color="#fff", corner_radius=RADIUS, border_width=1, border_color=BORDER)
        frm.pack(fill="x", padx=8, pady=8)
        self.var_start_o = ctk.StringVar(value=dt.now().strftime("%Y-%m-01"))
        self.var_end_o   = ctk.StringVar(value=dt.now().strftime("%Y-%m-%d"))
        ctk.CTkLabel(frm, text="Start").grid(row=0, column=0, padx=10, pady=8, sticky="w")
        ctk.CTkEntry(frm, textvariable=self.var_start_o, corner_radius=RADIUS, border_color=BORDER, width=140).grid(row=0, column=1, pady=8, sticky="w")
        ctk.CTkLabel(frm, text="End").grid(row=0, column=2, padx=10, pady=8, sticky="w")
        ctk.CTkEntry(frm, textvariable=self.var_end_o, corner_radius=RADIUS, border_color=BORDER, width=140).grid(row=0, column=3, pady=8, sticky="w")
        ctk.CTkButton(frm, text="Load", command=self.load_orders, corner_radius=RADIUS,
                      fg_color=CARD_BG, text_color=TEXT_DARK).grid(row=0, column=4, padx=10)

        self.order_list = ctk.CTkScrollableFrame(self.tab_orders, fg_color="#fff", corner_radius=RADIUS,
                                                 border_width=1, border_color=BORDER)
        self.order_list.pack(fill="both", expand=True, padx=8, pady=8)

    def load_orders(self):
        for w in self.order_list.winfo_children(): w.destroy()
        s = (self.var_start_o.get() or "").strip()
        e = (self.var_end_o.get() or "").strip()
        rows = self.app.db.all_orders(s if s else None, e if e else None)
        if not rows:
            ctk.CTkLabel(self.order_list, text="No orders.", text_color="#6b7280").pack(pady=12); return
        for r in rows:
            row = ctk.CTkFrame(self.order_list, fg_color="#fff"); row.pack(fill="x", padx=6, pady=4)
            ctk.CTkLabel(row, text=f"#{r['id']}  {r['order_datetime']}  [{r['channel']}] by {r['username']}", text_color=TEXT_DARK)\
                .pack(side="left", padx=6)
            ctk.CTkLabel(row, text=f"{r['total']:.2f}", width=100, anchor="e").pack(side="right", padx=6)

# ------------------- Dialogs -------------------
class AdjustDialog(ctk.CTkToplevel):
    def __init__(self, master, sign, on_ok):
        super().__init__(master)
        self.title("Adjust Inventory"); self.geometry("320x160")
        self.resizable(False, False)
        self.on_ok = on_ok; self.sign = sign
        wrap = ctk.CTkFrame(self, fg_color="#fff", corner_radius=RADIUS, border_width=1, border_color=BORDER)
        wrap.pack(fill="both", expand=True, padx=12, pady=12)
        ctk.CTkLabel(wrap, text=f"Quantity ({'+' if sign>0 else '-'})").pack(pady=(12,4))
        self.var = ctk.StringVar(value="1")
        ctk.CTkEntry(wrap, textvariable=self.var, corner_radius=RADIUS, border_color=BORDER).pack(pady=6)
        ctk.CTkButton(wrap, text="Apply", command=self._apply, corner_radius=RADIUS,
                      fg_color=CARD_BG, text_color=TEXT_DARK).pack(pady=8)
    def _apply(self):
        try:
            amt = float(self.var.get())
        except:
            self.destroy(); return
        self.on_ok(self.sign*abs(amt))
        self.destroy()

class ProductEditor(ctk.CTkToplevel):
    def __init__(self, master, db: DB, pid, on_done):
        super().__init__(master); self.db=db; self.pid=pid; self.on_done=on_done
        self.title("Product Editor"); self.geometry("520x360"); self.resizable(False, False)
        frm=ctk.CTkFrame(self, fg_color="#fff", corner_radius=RADIUS, border_color=BORDER, border_width=1)
        frm.pack(fill="both", expand=True, padx=12, pady=12)
        frm.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frm, text="Name").grid(row=0,column=0,sticky="e",padx=8,pady=6)
        self.en=ctk.CTkEntry(frm); self.en.grid(row=0,column=1,pady=6,sticky="ew")
        ctk.CTkLabel(frm, text="Category").grid(row=1,column=0,sticky="e",padx=8,pady=6)
        cats=db.categories(); self.cat_map={c['name']:c['id'] for c in cats}
        self.ec=ctk.CTkOptionMenu(frm, values=list(self.cat_map.keys()))
        self.ec.grid(row=1,column=1,pady=6,sticky="w")
        ctk.CTkLabel(frm, text="Base Price").grid(row=2,column=0,sticky="e",padx=8,pady=6)
        self.ep=ctk.CTkEntry(frm); self.ep.grid(row=2,column=1,pady=6,sticky="ew")
        ctk.CTkLabel(frm, text="Image").grid(row=3,column=0,sticky="e",padx=8,pady=6)
        self.ei=ctk.CTkEntry(frm); self.ei.grid(row=3,column=1,pady=6,sticky="ew")
        ctk.CTkButton(frm, text="Choose...", command=self.choose_img, corner_radius=RADIUS,
                      fg_color=CARD_BG, text_color=TEXT_DARK).grid(row=3,column=2,padx=6)
        ctk.CTkLabel(frm, text="Active (1/0)").grid(row=4,column=0,sticky="e",padx=8,pady=6)
        self.ea=ctk.CTkEntry(frm); self.ea.grid(row=4,column=1,pady=6,sticky="ew")
        ctk.CTkButton(frm, text="Save", command=self.save, corner_radius=RADIUS,
                      fg_color="#fde68a", text_color=TEXT_DARK).grid(row=5,column=1,pady=12,sticky="e")

        if pid:
            r=db.conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
            if r:
                self.en.insert(0, r['name'])
                cname=db.conn.execute("SELECT name FROM categories WHERE id=?", (r['category_id'],)).fetchone()
                self.ec.set(cname['name'] if cname else list(self.cat_map.keys())[0])
                self.ep.insert(0, str(r['base_price'])); self.ei.insert(0, r['image'] or ""); self.ea.insert(0, str(r['is_active']))
        else:
            self.ec.set(list(self.cat_map.keys())[0]); self.ea.insert(0,"1")

    def choose_img(self):
        import tkinter.filedialog as fd
        f=fd.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg")])
        if not f: return
        dest=os.path.join(IMG_PRODUCTS_DIR, os.path.basename(f))
        try: shutil.copy2(f,dest); self.ei.delete(0,"end"); self.ei.insert(0,dest)
        except Exception as e: pass

    def save(self):
        name=self.en.get().strip(); cat=self.ec.get().strip()
        try:
            price=float(self.ep.get().strip() or 0)
            act=int(self.ea.get().strip() or 1)
        except:
            return
        img=self.ei.get().strip()
        if not name or not cat: return
        self.db.upsert_product(self.pid, name, self.cat_map[cat], price, img, act)
        self.on_done(); self.destroy()

class PromoEditor(ctk.CTkToplevel):
    def __init__(self, master, db: DB, pid, on_done):
        super().__init__(master); self.db=db; self.pid=pid; self.on_done=on_done
        self.title("Promotion Editor"); self.geometry("560x360"); self.resizable(False, False)
        frm=ctk.CTkFrame(self, fg_color="#fff", corner_radius=RADIUS, border_color=BORDER, border_width=1)
        frm.pack(fill="both",expand=True,padx=12,pady=12)
        labels=[
            ("Code","code"),("Type [PERCENT_BILL/FLAT_BILL/PERCENT_ITEM/FLAT_ITEM]","type"),
            ("Value","value"),("Min Spend","min"),
            ("Start (YYYY-MM-DD HH:MM:SS)","start"),("End","end"),
            ("Applies to Product ID (for *_ITEM)","prod"),("Active 1/0","act")
        ]
        self.inp={}
        for i,(lab,key) in enumerate(labels):
            ctk.CTkLabel(frm,text=lab).grid(row=i,column=0,sticky="e",padx=8,pady=6)
            e=ctk.CTkEntry(frm); e.grid(row=i,column=1,sticky="ew",pady=6); self.inp[key]=e
        frm.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(frm,text="Save",command=self.save, corner_radius=RADIUS,
                      fg_color="#fde68a", text_color=TEXT_DARK).grid(row=len(labels),column=1,pady=10,sticky="e")

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
        else:
            now = dt.now()
            self.inp["start"].insert(0, now.strftime("%Y-%m-%d 00:00:00"))
            self.inp["end"].insert(0, (now+timedelta(days=365)).strftime("%Y-%m-%d 23:59:59"))
            self.inp["act"].insert(0, "1")

    def save(self):
        code=self.inp["code"].get().strip().upper()
        ptype=self.inp["type"].get().strip()
        try:
            value=float(self.inp["value"].get().strip() or 0)
            min_spend=float(self.inp["min"].get().strip() or 0)
            start=self.inp["start"].get().strip() or (dt.now().strftime("%Y-%m-%d 00:00:00"))
            end=self.inp["end"].get().strip() or (dt.now()+timedelta(days=365)).strftime("%Y-%m-%d 23:59:59")
            prod=self.inp["prod"].get().strip()
            applies=int(prod) if prod.isdigit() else None
            act=int(self.inp["act"].get().strip() or 1)
        except:
            return
        if not code or ptype not in ("PERCENT_BILL","FLAT_BILL","PERCENT_ITEM","FLAT_ITEM"):
            return
        self.db.upsert_promotion(self.pid, code, ptype, value, min_spend, start, end, applies, act)
        self.on_done(); self.destroy()

# ======================= RUN =======================
if __name__ == "__main__":
    ensure_dirs()
    AuthWindow(on_success=None).mainloop()
