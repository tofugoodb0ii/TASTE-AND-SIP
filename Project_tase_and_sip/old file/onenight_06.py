# -*- coding: utf-8 -*-
"""
TASTE & SIP — Login + Admin + Customer (CustomTkinter, single mainloop)

• Login (Sign in/up/forgot) → route by role
• Admin:
  - Categories (ชนิดหลัก: FOOD/DRINK; FOOD มี country เป็นหมวดย่อย)
  - Products (รูป, ราคา, stock, ptype, category, active)
  - Options (FOOD: Meat/Spice; DRINK: Sweetness/Ice) [dropdown configs]
  - Toppings (CRUD) + map ไปยังสินค้าใดเปิดใช้ท็อปปิงได้
  - Orders (สถานะ, ใบเสร็จ PDF — VAT 7% — TAX ID จาก config)
  - Logout → กลับหน้า Login อัตโนมัติ
• Customer:
  - Header: avatar + username (แก้โปรไฟล์/ตั้งรูปได้)
  - 3 ปุ่มวงกลม: FOOD | DRINK | CART
  - รายการสินค้า → dialog ตัวเลือก (dropdown) + toppings + note + qty + จำกัดไม่เกิน stock
  - Cart: subtotal, VAT(7%), total; เลือกส่ง/รับเอง + วิธีจ่าย (ส่ง=QR เท่านั้น; รับเอง=เงินสด/QR)
  - สั่งซื้อ → ตัด stock ตามจำนวน, บันทึก order, ออกบิลดาวน์โหลด
  - Logout → กลับหน้า Login อัตโนมัติ

DB file: taste_and_sip.db (auto-migrate schema)
"""

import os, re, json, sqlite3, hashlib
from datetime import datetime as dt, timedelta
from typing import Optional, Callable, Dict, Any, List

from PIL import Image, ImageTk, ImageOps

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import customtkinter as ctk

# -------------------- CONFIG --------------------
APP_TITLE = "TASTE AND SIP"
DB_FILE   = "taste_and_sip.db"
ASSETS    = os.path.join("assets")
ASSETS_IMG = os.path.join(ASSETS, "images")
ASSETS_PROD = os.path.join(ASSETS_IMG, "products")
REPORTS   = "reports"
os.makedirs(ASSETS_PROD, exist_ok=True); os.makedirs(REPORTS, exist_ok=True)

# **ปรับพาธให้ตรงเครื่องคุณ**
LEFT_BG_PATH = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\AVIBRA_1.png"
LOGO_PATH    = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\lologogo.png-removebg-preview.png"
QR_PATH      = r"C:\Users\thatt\Downloads\qrcode.jpg"

TAX_ID   = "0998877445566"
VAT_RATE = 0.07

# UI palette
RIGHT_BG   = "#f8eedb"
CARD_BG    = "#edd8b8"
TEXT_DARK  = "#1f2937"
LINK_FG    = "#0057b7"
BORDER     = "#d3c6b4"
RADIUS     = 18
CARD_W     = 660
CARD_H     = 560

# -------------------- HELPERS --------------------
def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def now_ts() -> str:
    return dt.now().strftime("%Y-%m-%d %H:%M:%S")

def safe_float(x, d=0.0):
    try: return float(x)
    except: return d

def try_reportlab():
    try:
        from reportlab.pdfgen import canvas as pdfcanvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        return pdfcanvas, A4, mm
    except Exception:
        return None, None, None

# -------------------- AUTH VALIDATION --------------------
USERNAME_RE = re.compile(r"^[A-Za-z0-9]{6,}$")
PHONE_RE    = re.compile(r"^\d{10}$")
EMAIL_RE    = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PWD_RE      = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,}$")

def validate_username(v): return None if USERNAME_RE.match(v or "") else "USERNAME ≥ 6 (A–Z/0–9)"
def validate_phone(v):    return None if PHONE_RE.match(v or "")    else "PHONE = 10 DIGITS"
def validate_email(v):    return None if EMAIL_RE.match(v or "")    else "INVALID EMAIL"
def validate_password(v): return None if PWD_RE.match(v or "")      else "PASSWORD ≥8 มี A/a/0-9"

# =====================================================================
# DB LAYER (auth + shop)
# =====================================================================
class DB:
    def __init__(self, path=DB_FILE):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._schema()
        self._seed()

    def _schema(self):
        c = self.conn.cursor()
        # users
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT, phone TEXT, email TEXT, birthdate TEXT, gender TEXT,
            avatar TEXT, role TEXT DEFAULT 'customer'
        )""")
        # categories (ptype: FOOD/DRINK, country nullable — ใช้กับ FOOD เท่านั้น)
        c.execute("""CREATE TABLE IF NOT EXISTS categories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ptype TEXT NOT NULL,       -- FOOD | DRINK
            country TEXT               -- เฉพาะ FOOD
        )""")
        # products
        c.execute("""CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER,
            ptype TEXT NOT NULL,       -- FOOD | DRINK
            base_price REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            image TEXT,
            is_active INTEGER DEFAULT 1
        )""")
        # options
        c.execute("""CREATE TABLE IF NOT EXISTS product_options(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            option_name TEXT NOT NULL,
            option_values_json TEXT
        )""")
        # toppings master
        c.execute("""CREATE TABLE IF NOT EXISTS toppings(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL
        )""")
        # map product→toppings allowed
        c.execute("""CREATE TABLE IF NOT EXISTS product_toppings(
            product_id INTEGER NOT NULL,
            topping_id INTEGER NOT NULL,
            UNIQUE(product_id, topping_id)
        )""")
        # orders
        c.execute("""CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            order_datetime TEXT,
            status TEXT,               -- PENDING/CONFIRMED/PAID/CANCELLED
            subtotal REAL, discount REAL, vat REAL, total REAL,
            note TEXT,
            fulfillment TEXT,          -- DELIVERY/PICKUP
            pay_method TEXT,           -- QR/CASH
            address_json TEXT          -- {name,phone,address}
        )""")
        # order items
        c.execute("""CREATE TABLE IF NOT EXISTS order_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            name TEXT,
            qty INTEGER,
            unit_price REAL,
            options_json TEXT,
            toppings_json TEXT,
            toppings_price REAL DEFAULT 0
        )""")
        self.conn.commit()

    def _seed(self):
        c = self.conn.cursor()
        # seed admin
        if not c.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
            c.execute("INSERT INTO users(username,password_hash,name,role) VALUES(?,?,?,?)",
                      ("admin", sha256("admin123"), "Administrator", "admin"))

        # Seed categories (ตามที่ให้)
        if c.execute("SELECT COUNT(*) n FROM categories").fetchone()["n"] == 0:
            cats = [
                ("THAI FOOD", "FOOD", "Thailand"),
                ("ITALIAN FOOD", "FOOD", "Italy"),
                ("KOREAN FOOD", "FOOD", "Korea"),
                ("CHAINESE FOOD", "FOOD", "China"),
                ("JAPANNESE FOOD", "FOOD", "Japan"),
                ("DRINKS", "DRINK", None),
            ]
            c.executemany("INSERT INTO categories(name,ptype,country) VALUES(?,?,?)", cats)

        # Seed products demo
        if c.execute("SELECT COUNT(*) n FROM products").fetchone()["n"] == 0:
            # get some ids
            cat_food = c.execute("SELECT id FROM categories WHERE ptype='FOOD' LIMIT 1").fetchone()["id"]
            cat_drk  = c.execute("SELECT id FROM categories WHERE ptype='DRINK' LIMIT 1").fetchone()["id"]
            demo = [
                ("Pad Krapao Moo Krob", cat_food, "FOOD", 60.0, 20, "", 1),
                ("Spaghetti Carbonara", cat_food, "FOOD", 85.0, 15, "", 1),
                ("Matcha Latte",        cat_drk,  "DRINK",55.0, 30, "", 1),
                ("Thai Milk Tea",       cat_drk,  "DRINK",35.0, 40, "", 1),
            ]
            c.executemany("""INSERT INTO products(name,category_id,ptype,base_price,stock,image,is_active)
                             VALUES(?,?,?,?,?,?,?)""", demo)

        # Default options for demo products
        for p in self.conn.execute("SELECT * FROM products").fetchall():
            pid, ptype = p["id"], p["ptype"]
            if ptype == "FOOD":
                if not self.conn.execute("SELECT 1 FROM product_options WHERE product_id=? AND option_name='Meat'", (pid,)).fetchone():
                    self.conn.execute("INSERT INTO product_options(product_id,option_name,option_values_json) VALUES(?,?,?)",
                                      (pid, "Meat", json.dumps({"values":["หมูสับ","หมูชิ้น","ไก่","หมูกรอบ","ปลาหมึก"]})))
                if not self.conn.execute("SELECT 1 FROM product_options WHERE product_id=? AND option_name='Spice'", (pid,)).fetchone():
                    self.conn.execute("INSERT INTO product_options(product_id,option_name,option_values_json) VALUES(?,?,?)",
                                      (pid, "Spice", json.dumps({"values":["เผ็ดน้อย","กลาง","เผ็ดมาก"]})))
            else:
                if not self.conn.execute("SELECT 1 FROM product_options WHERE product_id=? AND option_name='Sweetness'", (pid,)).fetchone():
                    self.conn.execute("INSERT INTO product_options(product_id,option_name,option_values_json) VALUES(?,?,?)",
                                      (pid, "Sweetness", json.dumps({"values":["0%","50%","100%"]})))
                if not self.conn.execute("SELECT 1 FROM product_options WHERE product_id=? AND option_name='Ice'", (pid,)).fetchone():
                    self.conn.execute("INSERT INTO product_options(product_id,option_name,option_values_json) VALUES(?,?,?)",
                                      (pid, "Ice", json.dumps({"values":["0%","25%","50%","75%","100%"]})))
        # Seed toppings
        if self.conn.execute("SELECT COUNT(*) n FROM toppings").fetchone()["n"] == 0:
            tops = [("ไข่ต้ม",15),("ไข่ดาว",15),("ไข่ออนเซ็น",15),("ไข่ข้น",15),("ไข่ดอง",15),("เบค่อน",25),("ไข่กุ้ง",20)]
            self.conn.executemany("INSERT INTO toppings(name,price) VALUES(?,?)", tops)

        self.conn.commit()

    # ---------------- AUTH ----------------
    def login(self, username, password):
        return self.conn.execute(
            "SELECT * FROM users WHERE username=? AND password_hash=?",
            (username, sha256(password))
        ).fetchone()

    def username_exists(self, u): 
        return self.conn.execute("SELECT 1 FROM users WHERE username=?", (u,)).fetchone() is not None

    def create_user(self, username, phone, email, password):
        self.conn.execute(
            "INSERT INTO users(username,password_hash,phone,email,role) VALUES(?,?,?,?,?)",
            (username, sha256(password), phone, email, "customer")
        ); self.conn.commit()

    def verify_user_contact(self, username, contact):
        return self.conn.execute(
            "SELECT * FROM users WHERE username=? AND (email=? OR phone=?)",
            (username, contact, contact)
        ).fetchone()

    def change_password(self, username, new_password):
        self.conn.execute("UPDATE users SET password_hash=? WHERE username=?",
                          (sha256(new_password), username)); self.conn.commit()

    def update_profile(self, uid, name, phone, email, avatar):
        self.conn.execute("""UPDATE users SET name=?, phone=?, email=?, avatar=? WHERE id=?""",
                          (name, phone, email, avatar, uid)); self.conn.commit()

    # --------------- ADMIN: categories ---------------
    def list_categories(self):
        return self.conn.execute("""SELECT * FROM categories ORDER BY ptype DESC, country, name""").fetchall()
    def upsert_category(self, cid, name, ptype, country):
        if cid:
            self.conn.execute("UPDATE categories SET name=?, ptype=?, country=? WHERE id=?",
                              (name, ptype, country, cid))
        else:
            self.conn.execute("INSERT INTO categories(name,ptype,country) VALUES(?,?,?)",
                              (name, ptype, country))
        self.conn.commit()
    def del_category(self, cid):
        self.conn.execute("DELETE FROM categories WHERE id=?", (cid,)); self.conn.commit()

    # --------------- ADMIN: products -----------------
    def list_products(self):
        return self.conn.execute("""
            SELECT p.*, c.name AS category_name, c.ptype AS cat_ptype, c.country AS country
            FROM products p LEFT JOIN categories c ON c.id=p.category_id
            ORDER BY p.id DESC
        """).fetchall()
    def upsert_product(self, pid, name, cat_id, ptype, price, stock, image, active):
        c = self.conn.cursor()
        if pid:
            c.execute("""UPDATE products SET name=?,category_id=?,ptype=?,base_price=?,stock=?,image=?,is_active=? WHERE id=?""",
                      (name, cat_id, ptype, price, stock, image, active, pid))
        else:
            c.execute("""INSERT INTO products(name,category_id,ptype,base_price,stock,image,is_active)
                         VALUES(?,?,?,?,?,?,?)""", (name, cat_id, ptype, price, stock, image, active))
        self.conn.commit()
    def del_product(self, pid):
        self.conn.execute("DELETE FROM products WHERE id=?", (pid,)); self.conn.commit()

    # options
    def get_options(self, pid)->Dict[str,Any]:
        out = {}
        for r in self.conn.execute("SELECT * FROM product_options WHERE product_id=?", (pid,)).fetchall():
            try: out[r["option_name"]] = json.loads(r["option_values_json"] or "{}")
            except: out[r["option_name"]] = {}
        return out
    def set_option(self, pid, name, obj):
        data = json.dumps(obj, ensure_ascii=False)
        if self.conn.execute("SELECT 1 FROM product_options WHERE product_id=? AND option_name=?", (pid, name)).fetchone():
            self.conn.execute("UPDATE product_options SET option_values_json=? WHERE product_id=? AND option_name=?",
                              (data, pid, name))
        else:
            self.conn.execute("INSERT INTO product_options(product_id,option_name,option_values_json) VALUES(?,?,?)",
                              (pid, name, data))
        self.conn.commit()

    # toppings
    def list_toppings(self):
        return self.conn.execute("SELECT * FROM toppings ORDER BY name").fetchall()
    def upsert_topping(self, tid, name, price):
        if tid:
            self.conn.execute("UPDATE toppings SET name=?, price=? WHERE id=?", (name, price, tid))
        else:
            self.conn.execute("INSERT INTO toppings(name,price) VALUES(?,?)", (name,price))
        self.conn.commit()
    def del_topping(self, tid):
        self.conn.execute("DELETE FROM toppings WHERE id=?", (tid,)); self.conn.commit()
    def product_allowed_toppings(self, pid)->List[int]:
        return [r["topping_id"] for r in self.conn.execute("SELECT topping_id FROM product_toppings WHERE product_id=?", (pid,)).fetchall()]
    def set_product_toppings(self, pid, topping_ids: List[int]):
        self.conn.execute("DELETE FROM product_toppings WHERE product_id=?", (pid,))
        self.conn.executemany("INSERT INTO product_toppings(product_id,topping_id) VALUES(?,?)",
                              [(pid, t) for t in topping_ids])
        self.conn.commit()

    # --------------- ORDERS --------------------------
    def list_orders(self, status=None):
        q="SELECT * FROM orders"; params=[]
        if status and status!="ALL": q+=" WHERE status=?"; params.append(status)
        q+=" ORDER BY id DESC"
        return self.conn.execute(q, params).fetchall()
    def order_items(self, oid):
        return self.conn.execute("SELECT * FROM order_items WHERE order_id=?", (oid,)).fetchall()
    def set_order_status(self, oid, status):
        self.conn.execute("UPDATE orders SET status=? WHERE id=?", (status, oid)); self.conn.commit()

    # --------------- CUSTOMER APIs -------------------
    def categories_by_ptype(self, ptype):
        return self.conn.execute("""SELECT * FROM categories WHERE ptype=? ORDER BY country, name""", (ptype,)).fetchall()
    def products_in_category(self, cid):
        return self.conn.execute("""SELECT * FROM products WHERE category_id=? AND is_active=1 ORDER BY name""", (cid,)).fetchall()
    def product_row(self, pid): return self.conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    def allowed_toppings_rows(self, pid):
        return self.conn.execute("""
            SELECT t.* FROM toppings t
            JOIN product_toppings pt ON pt.topping_id=t.id
            WHERE pt.product_id=?
            ORDER BY t.name
        """, (pid,)).fetchall()

    def create_order(self, user_id, items, fulfillment, pay_method, addr:dict):
        # items: [{pid, name, qty, unit_price, options{}, toppings[{id,name,price}], note}]
        subtotal=0.0
        for it in items:
            tp = sum(t["price"] for t in it.get("toppings",[]))
            subtotal += (it["unit_price"] + tp) * it["qty"]
        discount=0.0
        vat = round((subtotal - discount) * VAT_RATE, 2)
        total = round(subtotal - discount + vat, 2)

        # ตัด stock (validate)
        for it in items:
            p = self.product_row(it["pid"])
            if not p: raise ValueError("Product not found")
            if it["qty"] > int(p["stock"] or 0):
                raise ValueError(f"'{p['name']}' stock not enough")
        # commit
        cur = self.conn.cursor()
        cur.execute("""INSERT INTO orders(user_id,order_datetime,status,subtotal,discount,vat,total,note,fulfillment,pay_method,address_json)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (user_id, now_ts(), "PENDING", round(subtotal,2), round(discount,2), vat, total, None,
                     fulfillment, pay_method, json.dumps(addr, ensure_ascii=False) if addr else None))
        oid = cur.lastrowid
        for it in items:
            tp = sum(t["price"] for t in it.get("toppings",[]))
            cur.execute("""INSERT INTO order_items(order_id,product_id,name,qty,unit_price,options_json,toppings_json,toppings_price)
                           VALUES(?,?,?,?,?,?,?,?)""",
                        (oid, it["pid"], it["name"], it["qty"], it["unit_price"],
                         json.dumps(it.get("options",{}), ensure_ascii=False),
                         json.dumps(it.get("toppings",[]), ensure_ascii=False), tp))
            # deduct stock
            self.conn.execute("UPDATE products SET stock=stock-? WHERE id=?", (it["qty"], it["pid"]))
        self.conn.commit()
        return oid, subtotal, discount, vat, total

# =====================================================================
# RECEIPT
# =====================================================================
def save_receipt(db: DB, order_id: int, path_hint: Optional[str]=None) -> str:
    pdfcanvas, A4, mm = try_reportlab()
    order = db.conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    items = db.order_items(order_id)

    if pdfcanvas:
        path = path_hint or os.path.join(REPORTS, f"receipt_{order_id}.pdf")
        canv = pdfcanvas.Canvas(path, pagesize=A4)
        W,H = A4; x = 18*mm; y = H - 20*mm

        # logo
        try:
            from reportlab.lib.utils import ImageReader
            if os.path.exists(LOGO_PATH):
                canv.drawImage(ImageReader(LOGO_PATH), x, y-18*mm, width=24*mm, height=24*mm, mask='auto')
        except: pass

        canv.setFont("Helvetica-Bold", 16); canv.drawString(x+28*mm, y-4*mm, "TASTE & SIP")
        canv.setFont("Helvetica", 10)
        canv.drawString(x+28*mm, y-10*mm, f"TAX ID: {TAX_ID}")
        canv.drawString(x, y-26*mm, f"DATE: {order['order_datetime']}")
        canv.drawString(x+70*mm, y-26*mm, f"ORDER NO: #{order_id}")

        y = y-34*mm
        canv.line(x, y, W-x, y); y -= 6

        # header
        canv.setFont("Helvetica-Bold", 10)
        canv.drawString(x, y, "No.")
        canv.drawString(x+12*mm, y, "MENU")
        canv.drawString(x+96*mm, y, "QTY")
        canv.drawString(x+110*mm, y, "PRICE")
        canv.drawString(x+134*mm, y, "TOTAL")
        y -= 5
        canv.setFont("Helvetica", 10)

        n=1
        for it in items:
            opts = json.loads(it['options_json'] or "{}")
            tops = json.loads(it['toppings_json'] or "[]")
            line = (it["unit_price"] + float(it["toppings_price"] or 0)) * it["qty"]

            canv.drawString(x, y, f"{n:02d}")
            canv.drawString(x+12*mm, y, f"{it['name']}")
            canv.drawRightString(x+106*mm, y, f"{it['qty']}")
            canv.drawRightString(x+128*mm, y, f"{it['unit_price']:.2f}")
            canv.drawRightString(x+156*mm, y, f"{line:.2f}")
            y -= 5
            if opts:
                canv.setFont("Helvetica-Oblique", 9)
                canv.drawString(x+12*mm, y, "Options: " + ", ".join(f"{k}:{v}" for k,v in opts.items()))
                y -= 4; canv.setFont("Helvetica", 10)
            if tops:
                canv.setFont("Helvetica-Oblique", 9)
                canv.drawString(x+12*mm, y, "Toppings: " + ", ".join(f"{t['name']} (+{t['price']})" for t in tops))
                y -= 4; canv.setFont("Helvetica", 10)
            y -= 2; n+=1

        y -= 6
        canv.line(x, y, W-x, y); y -= 8
        canv.setFont("Helvetica-Bold", 11)
        canv.drawRightString(x+128*mm, y, "Subtotal")
        canv.drawRightString(x+156*mm, y, f"{order['subtotal']:.2f}"); y -= 6
        canv.drawRightString(x+128*mm, y, "Discount")
        canv.drawRightString(x+156*mm, y, f"{order['discount']:.2f}"); y -= 6
        canv.drawRightString(x+128*mm, y, "VAT (7%)")
        canv.drawRightString(x+156*mm, y, f"{order['vat']:.2f}"); y -= 6
        canv.drawRightString(x+128*mm, y, "TOTAL")
        canv.drawRightString(x+156*mm, y, f"{order['total']:.2f}")

        canv.showPage(); canv.save()
        return path
    else:
        path = path_hint or os.path.join(REPORTS, f"receipt_{order_id}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"TASTE & SIP\nTAX ID: {TAX_ID}\n\n")
            f.write(f"DATE: {order['order_datetime']}\nORDER NO: #{order_id}\n")
            f.write("\nItems:\n")
            for i,it in enumerate(items,1):
                opts = json.loads(it['options_json'] or "{}")
                tops = json.loads(it['toppings_json'] or "[]")
                line = (it["unit_price"] + float(it["toppings_price"] or 0)) * it["qty"]
                f.write(f"{i:02d}. {it['name']} x{it['qty']} @ {it['unit_price']:.2f} = {line:.2f}\n")
                if opts: f.write("    Options: " + ", ".join(f"{k}:{v}" for k,v in opts.items()) + "\n")
                if tops: f.write("    Toppings: " + ", ".join(f"{t['name']} (+{t['price']})" for t in tops) + "\n")
            f.write(f"\nSubtotal: {order['subtotal']:.2f}\nDiscount: {order['discount']:.2f}\nVAT(7%): {order['vat']:.2f}\nTOTAL: {order['total']:.2f}\n")
        return path

# =====================================================================
# UI COMMON WIDGETS
# =====================================================================
class Title(ctk.CTkLabel):
    def __init__(self, master, text): super().__init__(master, text=text.upper(),
                        font=ctk.CTkFont(size=20, weight="bold"), text_color=TEXT_DARK, fg_color="transparent")
class ErrorLabel(ctk.CTkLabel):
    def __init__(self, m): super().__init__(m, text="", text_color="#b00020", wraplength=560, justify="left", fg_color="transparent")
    def set(self, t): self.configure(text=(t or "").upper())
class LabeledEntry(ctk.CTkFrame):
    def __init__(self, m, label, show=""):
        super().__init__(m, fg_color="transparent"); self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=label.upper(), text_color="#333", font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="transparent").grid(row=0, column=0, sticky="w", padx=2, pady=(0,2))
        self.entry = ctk.CTkEntry(self, show=show, corner_radius=RADIUS, border_color=BORDER, fg_color="white")
        self.entry.grid(row=1, column=0, sticky="ew")
    def get(self): return self.entry.get()
    def set(self, v): self.entry.delete(0,"end"); self.entry.insert(0, v)
class SubmitBtn(ctk.CTkButton):
    def __init__(self, m, text, command): super().__init__(m, text=text.upper(), command=command,
        height=44, corner_radius=RADIUS, fg_color="#f6e8d3", hover_color="#f6e8d3", text_color=TEXT_DARK,
        border_color=BORDER, border_width=1)
class LinkBtn(ctk.CTkButton):
    def __init__(self, m, text, command): super().__init__(m, text=text.upper(), command=command,
        height=36, corner_radius=RADIUS, fg_color="transparent", hover_color="#e9dcc6", text_color=LINK_FG)

# =====================================================================
# LOGIN APP (root)
# =====================================================================
class LoginApp(ctk.CTk):
    def __init__(self, db: DB):
        super().__init__()
        ctk.set_appearance_mode("light")
        self.title(APP_TITLE)
        try: self.state("zoomed")
        except: self.geometry("1200x720")
        self.configure(fg_color=RIGHT_BG)
        self.db = db

        # left canvas
        self.grid_columnconfigure(0, weight=1); self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)
        self.left = ctk.CTkFrame(self, fg_color=RIGHT_BG, corner_radius=0); self.left.grid(row=0, column=0, sticky="nsew")
        self.cv = tk.Canvas(self.left, highlightthickness=0, bd=0, bg=RIGHT_BG); self.cv.place(x=0,y=0, relwidth=1, relheight=1)
        self._imgtk=None; self.left.bind("<Configure>", lambda e: self._paint_left())

        # right: logo + card
        self.right = ctk.CTkFrame(self, fg_color=RIGHT_BG, corner_radius=0); self.right.grid(row=0, column=1, sticky="nsew")
        self.right.grid_rowconfigure(1, weight=1); self.right.grid_columnconfigure(0, weight=1)
        self.logo_wrap = ctk.CTkFrame(self.right, fg_color=RIGHT_BG, corner_radius=0); self.logo_wrap.grid(row=0, column=0, pady=(30,10))
        self._render_logo()

        self.card = ctk.CTkFrame(self.right, fg_color=CARD_BG, corner_radius=RADIUS, border_color=BORDER, border_width=1, width=CARD_W, height=CARD_H)
        self.card.grid(row=1, column=0, sticky="n", padx=80, pady=(10,40)); self.card.grid_propagate(False); self.card.grid_columnconfigure(0, weight=1)

        self.show_signin()

    def _paint_left(self):
        c = self.cv; c.delete("all")
        w = max(300, int(self.winfo_width()*0.5)); h = max(300, self.winfo_height())
        c.configure(width=w, height=h); c.create_rectangle(0,0,w,h, fill=RIGHT_BG, outline="")
        if os.path.exists(LEFT_BG_PATH):
            try:
                img = Image.open(LEFT_BG_PATH).convert("RGB")
                iw,ih = img.size
                scale = max(w/iw, h/ih); nw,nh = int(iw*scale), int(ih*scale)
                img = img.resize((nw,nh), Image.LANCZOS)
                left=max(0,(nw-w)//2); top=max(0,(nh-h)//2)
                img = img.crop((left,top,left+w,top+h))
                self._imgtk = ImageTk.PhotoImage(img); c.create_image(0,0,anchor="nw", image=self._imgtk)
            except: pass
        t1 = c.create_text(28,28, anchor="nw", fill="white", font=("Segoe UI",36,"bold"),
                           text=f"WELCOME TO\n{APP_TITLE}".upper())
        bbox = c.bbox(t1); y2 = (bbox[3] if bbox else 120)+18
        c.create_text(32,y2, anchor="nw", fill="white", font=("Segoe UI",18,"bold"), text="FOOD AND DRINK!".upper())

    def _render_logo(self):
        for w in self.logo_wrap.winfo_children(): w.destroy()
        if os.path.exists(LOGO_PATH):
            try:
                img = Image.open(LOGO_PATH); self._logo = ctk.CTkImage(light_image=img, dark_image=img, size=(220,220))
                ctk.CTkLabel(self.logo_wrap, image=self._logo, text="", fg_color="transparent").pack(); return
            except: pass
        ctk.CTkLabel(self.logo_wrap, text=APP_TITLE.upper(), font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=TEXT_DARK, fg_color="transparent").pack()

    def _clear_card(self):
        for w in self.card.winfo_children(): w.destroy()
        self.card.grid_columnconfigure(0, weight=1)

    # screens
    def show_signin(self):
        self._clear_card()
        Title(self.card,"SIGN IN").pack(pady=(22,6))
        self.si_err=ErrorLabel(self.card); self.si_err.pack(padx=28, fill="x")
        self.e_user=LabeledEntry(self.card,"USERNAME"); self.e_user.pack(fill="x", padx=28, pady=(6,8))
        self.e_pwd =LabeledEntry(self.card,"PASSWORD", show="•"); self.e_pwd.pack(fill="x", padx=28, pady=(6,12))
        SubmitBtn(self.card,"SIGN IN", self._signin).pack(fill="x", padx=28, pady=(0,12))
        bottom = ctk.CTkFrame(self.card, fg_color="transparent"); bottom.pack(fill="x", pady=(4,18))
        LinkBtn(bottom,"FORGOT PASSWORD?", self.show_forgot).pack(side="left", padx=4)
        LinkBtn(bottom,"CREATE ACCOUNT", self.show_signup).pack(side="right", padx=4)

    def show_signup(self):
        self._clear_card()
        Title(self.card,"CREATE ACCOUNT").pack(pady=(22,6))
        self.su_err=ErrorLabel(self.card); self.su_err.pack(padx=24, fill="x")
        form = ctk.CTkFrame(self.card, fg_color="transparent"); form.pack(fill="x", padx=24, pady=(6,10))
        form.grid_columnconfigure(0, weight=1, uniform="c"); form.grid_columnconfigure(1, weight=1, uniform="c")
        self.su_user=LabeledEntry(form,"USERNAME"); self.su_user.grid(row=0,column=0, padx=8,pady=6,sticky="ew")
        self.su_phone=LabeledEntry(form,"PHONE"); self.su_phone.grid(row=0,column=1, padx=8,pady=6,sticky="ew")
        self.su_email=LabeledEntry(form,"EMAIL"); self.su_email.grid(row=1,column=0, columnspan=2, padx=8,pady=6,sticky="ew")
        self.su_pwd1=LabeledEntry(form,"PASSWORD",show="•"); self.su_pwd1.grid(row=2,column=0, padx=8,pady=6,sticky="ew")
        self.su_pwd2=LabeledEntry(form,"CONFIRM PASSWORD",show="•"); self.su_pwd2.grid(row=2,column=1, padx=8,pady=6,sticky="ew")
        SubmitBtn(self.card,"REGISTER", self._signup).pack(fill="x", padx=24, pady=(8,12))
        LinkBtn(self.card,"BACK TO LOGIN", self.show_signin).pack(pady=(0,18))

    def show_forgot(self):
        self._clear_card()
        Title(self.card,"FORGOT PASSWORD").pack(pady=(22,6))
        self.fp_err=ErrorLabel(self.card); self.fp_err.pack(padx=24, fill="x")
        self.fp_user=LabeledEntry(self.card,"USERNAME"); self.fp_user.pack(fill="x", padx=24, pady=(6,8))
        self.fp_contact=LabeledEntry(self.card,"EMAIL OR PHONE"); self.fp_contact.pack(fill="x", padx=24, pady=(6,10))
        SubmitBtn(self.card,"VERIFY", self._forgot_verify).pack(fill="x", padx=24, pady=(0,12))

        self.fp_step2 = ctk.CTkFrame(self.card, fg_color="transparent"); self.fp_step2.pack(fill="x", padx=16, pady=(6,12))
        self.fp_step2.grid_columnconfigure(0, weight=1); self.fp_step2.pack_forget()
        self.fp_pwd1=LabeledEntry(self.fp_step2,"NEW PASSWORD",show="•"); self.fp_pwd1.pack(fill="x", padx=12,pady=(6,8))
        self.fp_pwd2=LabeledEntry(self.fp_step2,"CONFIRM NEW PASSWORD",show="•"); self.fp_pwd2.pack(fill="x", padx=12,pady=(6,10))
        SubmitBtn(self.fp_step2,"CHANGE PASSWORD", self._forgot_change).pack(fill="x", padx=12, pady=(0,10))
        LinkBtn(self.card,"BACK TO LOGIN", self.show_signin).pack(pady=(0,18))
        self._verified_username=None

    # actions
    def _signin(self):
        self.si_err.set("")
        u=self.e_user.get().strip(); p=self.e_pwd.get().strip()
        if not u or not p: self.si_err.set("PLEASE ENTER USERNAME/PASSWORD"); return
        row = self.db.login(u,p)
        if not row: self.si_err.set("INVALID CREDENTIALS"); return
        # route
        role = (row["role"] or "customer").lower()
        self.withdraw()
        if role=="admin":
            AdminApp(self, self.db, row)
        else:
            CustomerApp(self, self.db, row)

    def _signup(self):
        self.su_err.set("")
        u=self.su_user.get().strip(); ph=self.su_phone.get().strip()
        em=self.su_email.get().strip(); p1=self.su_pwd1.get().strip(); p2=self.su_pwd2.get().strip()
        for fn in (lambda:validate_username(u), lambda:validate_phone(ph), lambda:validate_email(em), lambda:validate_password(p1)):
            msg=fn()
            if msg: self.su_err.set(msg); return
        if p1!=p2: self.su_err.set("PASSWORDS DO NOT MATCH"); return
        if self.db.username_exists(u): self.su_err.set("USERNAME EXISTS"); return
        self.db.create_user(u,ph,em,p1); self.su_err.set("ACCOUNT CREATED. PLEASE SIGN IN.")

    def _forgot_verify(self):
        self.fp_err.set("")
        u=self.fp_user.get().strip(); cp=self.fp_contact.get().strip()
        if not u or not cp: self.fp_err.set("FILL USERNAME + EMAIL/PHONE"); return
        row=self.db.verify_user_contact(u,cp)
        if row:
            self._verified_username=u; self.fp_err.set("VERIFIED. SET NEW PASSWORD BELOW.")
            self.fp_step2.pack(fill="x", padx=16, pady=(6,12))
        else:
            self.fp_err.set("NO MATCHING ACCOUNT")

    def _forgot_change(self):
        if not self._verified_username: self.fp_err.set("VERIFY FIRST"); return
        p1=self.fp_pwd1.get().strip(); p2=self.fp_pwd2.get().strip()
        msg=validate_password(p1); ifmsg=msg or (None if p1==p2 else "PASSWORDS DO NOT MATCH")
        if ifmsg: self.fp_err.set(ifmsg); return
        self.db.change_password(self._verified_username, p1)
        self.fp_err.set("PASSWORD CHANGED. YOU CAN SIGN IN NOW.")

# =====================================================================
# ADMIN APP (Toplevel)
# =====================================================================
class AdminApp(ctk.CTkToplevel):
    def __init__(self, master, db: DB, user_row):
        super().__init__(master); self.db=db; self.user=user_row
        self.title(f"{APP_TITLE} — ADMIN"); 
        try: self.state("zoomed")
        except: self.geometry("1400x820")
        self.configure(fg_color=RIGHT_BG)
        self.protocol("WM_DELETE_WINDOW", self._logout)

        # Topbar
        top = ctk.CTkFrame(self, fg_color="transparent"); top.pack(fill="x", padx=12, pady=12)
        ctk.CTkLabel(top, text=f"ADMIN: {self.user['username']}", font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=TEXT_DARK, fg_color="transparent").pack(side="left")
        ctk.CTkButton(top, text="Logout", command=self._logout, corner_radius=RADIUS).pack(side="right")

        tabs = ctk.CTkTabview(self, fg_color=CARD_BG, segmented_button_fg_color="#e8d4b2",
                              segmented_button_selected_color="#e2cda6",
                              segmented_button_unselected_color="#f1e3ca",
                              text_color=TEXT_DARK, corner_radius=RADIUS)
        tabs.pack(fill="both", expand=True, padx=12, pady=12)

        self.tab_cat = tabs.add("Categories")
        self.tab_prod= tabs.add("Products")
        self.tab_top = tabs.add("Toppings")
        self.tab_ord = tabs.add("Orders")

        self._ui_categories()
        self._ui_products()
        self._ui_toppings()
        self._ui_orders()

        self.grab_set(); self.focus()

    def _logout(self):
        try: self.grab_release()
        except: pass
        self.destroy()
        # back to login
        self.master.deiconify()

    # ---------- Categories ----------
    def _ui_categories(self):
        wrap = ctk.CTkFrame(self.tab_cat, fg_color="transparent"); wrap.pack(fill="both", expand=True, padx=10, pady=10)
        self.tv_cat = ttk.Treeview(wrap, columns=("id","name","ptype","country"), show="headings", height=16)
        for k,w in [("id",60),("name",200),("ptype",100),("country",160)]:
            self.tv_cat.heading(k, text=k.upper()); self.tv_cat.column(k, width=w, anchor="w")
        self.tv_cat.pack(fill="both", expand=True)

        form = ctk.CTkFrame(self.tab_cat, fg_color="transparent"); form.pack(fill="x", padx=10, pady=(0,10))
        self.vc = {k: tk.StringVar() for k in ["id","name","ptype","country"]}
        for (label,key,wid) in [("Name","name",220),("Type (FOOD/DRINK)","ptype",140),("Country (FOOD only)","country",220)]:
            box = ctk.CTkFrame(form, fg_color="transparent"); box.pack(side="left", padx=6)
            ctk.CTkLabel(box, text=label).pack(anchor="w")
            ctk.CTkEntry(box, textvariable=self.vc[key], corner_radius=RADIUS, width=wid).pack()
        ctk.CTkButton(form, text="Add/Update", command=self._cat_save, corner_radius=RADIUS).pack(side="left", padx=6)
        ctk.CTkButton(form, text="Delete", command=self._cat_del, corner_radius=RADIUS).pack(side="left", padx=6)
        self.tv_cat.bind("<<TreeviewSelect>>", lambda e: self._cat_pick())
        self._cat_reload()

    def _cat_reload(self):
        for i in self.tv_cat.get_children(): self.tv_cat.delete(i)
        for r in self.db.list_categories():
            self.tv_cat.insert("", "end", values=(r["id"], r["name"], r["ptype"], r["country"] or ""))

    def _cat_pick(self):
        sel=self.tv_cat.selection()
        if not sel: return
        v=self.tv_cat.item(sel[0],"values")
        self.vc["id"].set(str(v[0])); self.vc["name"].set(v[1]); self.vc["ptype"].set(v[2]); self.vc["country"].set(v[3])

    def _cat_save(self):
        cid = int(self.vc["id"].get() or 0) or None
        name=self.vc["name"].get().strip(); ptype=self.vc["ptype"].get().strip().upper()
        country=self.vc["country"].get().strip() or None
        if not name or ptype not in ("FOOD","DRINK"):
            messagebox.showerror("Category","Invalid input"); return
        if ptype=="DRINK": country=None
        self.db.upsert_category(cid, name, ptype, country)
        self._cat_reload(); self.vc["id"].set("")

    def _cat_del(self):
        sel=self.tv_cat.selection()
        if not sel: return
        cid=int(self.tv_cat.item(sel[0],"values")[0])
        if messagebox.askyesno("Delete","Delete this category?"):
            self.db.del_category(cid); self._cat_reload()

    # ---------- Products ----------
    def _ui_products(self):
        wrap = ctk.CTkFrame(self.tab_prod, fg_color="transparent"); wrap.pack(fill="both", expand=True, padx=10, pady=10)
        self.tv_prod = ttk.Treeview(wrap, columns=("id","name","ptype","category","country","price","stock","active","image"), show="headings", height=16)
        for k,w in [("id",60),("name",160),("ptype",80),("category",160),("country",120),("price",80),("stock",80),("active",60),("image",220)]:
            self.tv_prod.heading(k, text=k.upper()); self.tv_prod.column(k, width=w, anchor="w")
        self.tv_prod.pack(fill="both", expand=True)
        btns = ctk.CTkFrame(self.tab_prod, fg_color="transparent"); btns.pack(fill="x", padx=10, pady=(6,10))
        ctk.CTkButton(btns, text="Add/Edit", command=self._prod_edit, corner_radius=RADIUS).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Delete", command=self._prod_del, corner_radius=RADIUS).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Options", command=self._prod_opts, corner_radius=RADIUS).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Toppings map", command=self._prod_topmap, corner_radius=RADIUS).pack(side="left", padx=4)
        self._prod_reload()

    def _prod_reload(self):
        for i in self.tv_prod.get_children(): self.tv_prod.delete(i)
        for r in self.db.list_products():
            self.tv_prod.insert("", "end", values=(r["id"], r["name"], r["ptype"], r["category_name"] or "-", r["country"] or "-",
                                                   f"{r['base_price']:.2f}", r["stock"], r["is_active"], r["image"] or ""))

    def _prod_edit(self):
        sel=self.tv_prod.selection()
        pid=int(self.tv_prod.item(sel[0],"values")[0]) if sel else None
        ProductEditor(self, self.db, pid, self._prod_reload)

    def _prod_del(self):
        sel=self.tv_prod.selection()
        if not sel: return
        pid=int(self.tv_prod.item(sel[0],"values")[0])
        if messagebox.askyesno("Delete","Delete product?"):
            self.db.del_product(pid); self._prod_reload()

    def _prod_opts(self):
        sel=self.tv_prod.selection()
        if not sel: messagebox.showinfo("Options","Select a product"); return
        pid=int(self.tv_prod.item(sel[0],"values")[0])
        ProductOptionEditor(self, self.db, pid)

    def _prod_topmap(self):
        sel=self.tv_prod.selection()
        if not sel: messagebox.showinfo("Toppings","Select a product"); return
        pid=int(self.tv_prod.item(sel[0],"values")[0])
        ProductToppingMap(self, self.db, pid)

    # ---------- Toppings ----------
    def _ui_toppings(self):
        wrap = ctk.CTkFrame(self.tab_top, fg_color="transparent"); wrap.pack(fill="both", expand=True, padx=10, pady=10)
        self.tv_top = ttk.Treeview(wrap, columns=("id","name","price"), show="headings", height=16)
        for k,w in [("id",60),("name",220),("price",120)]:
            self.tv_top.heading(k, text=k.upper()); self.tv_top.column(k, width=w, anchor="w")
        self.tv_top.pack(fill="both", expand=True)
        form = ctk.CTkFrame(self.tab_top, fg_color="transparent"); form.pack(fill="x", padx=10, pady=(6,10))
        self.vt = {k: tk.StringVar() for k in ["id","name","price"]}
        for (label,key,wid) in [("Name","name",240),("Price","+"),]:
            box = ctk.CTkFrame(form, fg_color="transparent"); box.pack(side="left", padx=6)
            ctk.CTkLabel(box, text=label).pack(anchor="w")
            w = ctk.CTkEntry(box, textvariable=self.vt[key], corner_radius=RADIUS)
            if key=="name": w.configure(width=240)
            w.pack()
        ctk.CTkButton(form, text="Add/Update", command=self._top_save, corner_radius=RADIUS).pack(side="left", padx=6)
        ctk.CTkButton(form, text="Delete", command=self._top_del, corner_radius=RADIUS).pack(side="left", padx=6)
        self.tv_top.bind("<<TreeviewSelect>>", lambda e: self._top_pick())
        self._top_reload()

    def _top_reload(self):
        for i in self.tv_top.get_children(): self.tv_top.delete(i)
        for r in self.db.list_toppings():
            self.tv_top.insert("", "end", values=(r["id"], r["name"], f"{r['price']:.2f}"))

    def _top_pick(self):
        sel=self.tv_top.selection()
        if not sel: return
        v=self.tv_top.item(sel[0],"values")
        self.vt["id"].set(str(v[0])); self.vt["name"].set(v[1]); self.vt["price"].set(str(v[2]))

    def _top_save(self):
        tid=int(self.vt["id"].get() or 0) or None
        name=self.vt["name"].get().strip(); price=safe_float(self.vt["price"].get().strip(),0)
        if not name: messagebox.showerror("Topping","Name required"); return
        self.db.upsert_topping(tid,name,price); self._top_reload(); self.vt["id"].set("")

    def _top_del(self):
        sel=self.tv_top.selection()
        if not sel: return
        tid=int(self.tv_top.item(sel[0],"values")[0])
        if messagebox.askyesno("Delete","Delete topping?"):
            self.db.del_topping(tid); self._top_reload()

    # ---------- Orders ----------
    def _ui_orders(self):
        wrap = ctk.CTkFrame(self.tab_ord, fg_color="transparent"); wrap.pack(fill="both", expand=True, padx=10, pady=10)
        top = ctk.CTkFrame(wrap, fg_color="transparent"); top.pack(fill="x")
        self.var_status = tk.StringVar(value="ALL")
        ctk.CTkLabel(top, text="Status:").pack(side="left"); 
        ttk.Combobox(top, values=["ALL","PENDING","CONFIRMED","PAID","CANCELLED"], textvariable=self.var_status, state="readonly").pack(side="left", padx=6)
        ctk.CTkButton(top, text="Search", command=self._ord_reload).pack(side="left", padx=6)
        ctk.CTkButton(top, text="Confirm", command=lambda:self._ord_set("CONFIRMED")).pack(side="left", padx=6)
        ctk.CTkButton(top, text="Cancel",  command=lambda:self._ord_set("CANCELLED")).pack(side="left", padx=6)
        ctk.CTkButton(top, text="Mark Paid + Receipt", command=self._ord_paid).pack(side="left", padx=6)

        body = ctk.CTkFrame(wrap, fg_color="transparent"); body.pack(fill="both", expand=True, pady=(8,0))
        self.tv_ord = ttk.Treeview(body, columns=("id","dt","status","subtotal","discount","vat","total","fulfillment","pay"), show="headings", height=16)
        for k,w in [("id",60),("dt",160),("status",120),("subtotal",100),("discount",100),("vat",90),("total",100),("fulfillment",120),("pay",90)]:
            self.tv_ord.heading(k, text=k.upper()); self.tv_ord.column(k, width=w, anchor="w")
        self.tv_ord.pack(side="left", fill="both", expand=True, padx=(0,6))
        self.tv_items = ttk.Treeview(body, columns=("name","qty","price","tops","opts"), show="headings", height=16)
        for k,w in [("name",220),("qty",60),("price",90),("tops",220),("opts",260)]:
            self.tv_items.heading(k, text=k.upper()); self.tv_items.column(k, width=w, anchor="w")
        self.tv_items.pack(side="left", fill="both", expand=True)
        self.tv_ord.bind("<<TreeviewSelect>>", self._ord_pick)
        self._ord_reload()

    def _ord_reload(self):
        for i in self.tv_ord.get_children(): self.tv_ord.delete(i)
        for r in self.db.list_orders(self.var_status.get()):
            self.tv_ord.insert("", "end", values=(r["id"], r["order_datetime"], r["status"], f"{r['subtotal']:.2f}",
                                                  f"{r['discount']:.2f}", f"{r['vat']:.2f}", f"{r['total']:.2f}",
                                                  r["fulfillment"] or "-", r["pay_method"] or "-"))
        for i in self.tv_items.get_children(): self.tv_items.delete(i)

    def _ord_pick(self, _e=None):
        for i in self.tv_items.get_children(): self.tv_items.delete(i)
        sel=self.tv_ord.selection()
        if not sel: return
        oid=int(self.tv_ord.item(sel[0],"values")[0])
        for it in self.db.order_items(oid):
            opts=json.loads(it["options_json"] or "{}"); tops=json.loads(it["toppings_json"] or "[]")
            tops_s=", ".join(f"{t['name']}(+{t['price']})" for t in tops)
            self.tv_items.insert("", "end", values=(it["name"], it["qty"], f"{it['unit_price']:.2f}", tops_s,
                                                    ", ".join(f"{k}:{v}" for k,v in opts.items())))

    def _ord_set(self, status):
        sel=self.tv_ord.selection()
        if not sel: return
        oid=int(self.tv_ord.item(sel[0],"values")[0])
        self.db.set_order_status(oid, status); self._ord_reload()

    def _ord_paid(self):
        sel=self.tv_ord.selection()
        if not sel: return
        oid=int(self.tv_ord.item(sel[0],"values")[0])
        self.db.set_order_status(oid, "PAID")
        path=save_receipt(self.db, oid)
        messagebox.showinfo("Receipt", f"Saved:\n{path}")
        self._ord_reload()

# ---------- Product subdialogs ----------
class ProductEditor(ctk.CTkToplevel):
    def __init__(self, master, db: DB, pid, on_done):
        super().__init__(master); self.db=db; self.pid=pid; self.on_done=on_done
        self.title("Product Editor"); self.geometry("760x460"); self.configure(fg_color=RIGHT_BG)
        frm = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=RADIUS); frm.pack(fill="both", expand=True, padx=12, pady=12)

        cats = self.db.list_categories()
        self.cat_map = {f"{r['name']} ({r['ptype']}{' / '+r['country'] if r['country'] else ''})": r["id"] for r in cats}
        self.v = {k: tk.StringVar() for k in ["name","ptype","price","stock","image","active","cat"]}
        if self.cat_map: self.v["cat"].set(list(self.cat_map.keys())[0])

        grid = ctk.CTkFrame(frm, fg_color="transparent"); grid.pack(fill="x", padx=8, pady=8)
        for i in range(4): grid.grid_columnconfigure(i, weight=1, uniform="g")
        def cell(r,c,label,key):
            ctk.CTkLabel(grid, text=label).grid(row=r, column=c, sticky="w", padx=6, pady=2)
            ctk.CTkEntry(grid, textvariable=self.v[key], corner_radius=RADIUS).grid(row=r+1, column=c, sticky="ew", padx=6)
        cell(0,0,"Name","name"); cell(0,1,"Type (FOOD/DRINK)","ptype")
        cell(0,2,"Base Price","price"); cell(0,3,"Stock","stock")

        ctk.CTkLabel(grid, text="Category").grid(row=2, column=0, sticky="w", padx=6, pady=2)
        ttk.Combobox(grid, values=list(self.cat_map.keys()), textvariable=self.v["cat"], state="readonly").grid(row=3, column=0, sticky="ew", padx=6)
        ctk.CTkLabel(grid, text="Active (1/0)").grid(row=2, column=1, sticky="w", padx=6, pady=2)
        ctk.CTkEntry(grid, textvariable=self.v["active"], corner_radius=RADIUS).grid(row=3, column=1, sticky="ew", padx=6)
        ctk.CTkLabel(grid, text="Image path").grid(row=2, column=2, sticky="w", padx=6, pady=2)
        ctk.CTkEntry(grid, textvariable=self.v["image"], corner_radius=RADIUS).grid(row=3, column=2, sticky="ew", padx=6)
        ctk.CTkButton(grid, text="Choose...", command=self._pick_img).grid(row=3, column=3, sticky="w", padx=6)
        ctk.CTkButton(frm, text="Save", command=self._save, corner_radius=RADIUS).pack(pady=10)

        if pid:
            r=self.db.conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
            if r:
                self.v["name"].set(r["name"]); self.v["ptype"].set(r["ptype"])
                self.v["price"].set(str(r["base_price"])); self.v["stock"].set(str(r["stock"]))
                self.v["image"].set(r["image"] or ""); self.v["active"].set(str(r["is_active"]))
                cat = self.db.conn.execute("SELECT name,ptype,country FROM categories WHERE id=?", (r["category_id"],)).fetchone()
                label = f"{cat['name']} ({cat['ptype']}{' / '+cat['country'] if cat['country'] else ''})"
                if label in self.cat_map: self.v["cat"].set(label)

    def _pick_img(self):
        f=filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg")])
        if not f: return
        dst=os.path.join(ASSETS_PROD, os.path.basename(f))
        try:
            import shutil; shutil.copy2(f,dst); self.v["image"].set(dst)
        except Exception as e:
            messagebox.showerror("Image", str(e))

    def _save(self):
        try:
            name=self.v["name"].get().strip(); ptype=self.v["ptype"].get().strip().upper()
            price=safe_float(self.v["price"].get().strip(),0); stock=int(float(self.v["stock"].get().strip() or 0))
            active=0 if (self.v["active"].get().strip()=="0") else 1
            image=self.v["image"].get().strip(); cat_id=self.cat_map.get(self.v["cat"].get().strip())
            if not name or ptype not in ("FOOD","DRINK") or not cat_id:
                messagebox.showerror("Product","Invalid input"); return
            self.db.upsert_product(self.pid, name, cat_id, ptype, price, stock, image, active)
            messagebox.showinfo("Saved","Product saved"); self.on_done(); self.destroy()
        except Exception as e:
            messagebox.showerror("Save", str(e))

class ProductOptionEditor(ctk.CTkToplevel):
    def __init__(self, master, db: DB, pid):
        super().__init__(master); self.db=db; self.pid=pid
        self.title("Product Options"); self.geometry("720x520"); self.configure(fg_color=RIGHT_BG)
        frm = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=RADIUS); frm.pack(fill="both", expand=True, padx=12, pady=12)
        p = self.db.conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
        ctk.CTkLabel(frm, text=f"{p['name']} ({p['ptype']})", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(8,6))

        self.opts = self.db.get_options(pid)
        self.v = {k: tk.StringVar() for k in "meat spice sweet ice".split()}
        self.v["meat"].set(",".join(self.opts.get("Meat",{}).get("values",["หมูสับ","หมูชิ้น","ไก่","หมูกรอบ","ปลาหมึก"])))
        self.v["spice"].set(",".join(self.opts.get("Spice",{}).get("values",["เผ็ดน้อย","กลาง","เผ็ดมาก"])))
        self.v["sweet"].set(",".join(self.opts.get("Sweetness",{}).get("values",["0%","50%","100%"])))
        self.v["ice"].set(",".join(self.opts.get("Ice",{}).get("values",["0%","25%","50%","75%","100%"])))

        grid = ctk.CTkFrame(frm, fg_color="transparent"); grid.pack(fill="x", padx=12, pady=6)
        for i in range(2): grid.grid_columnconfigure(i, weight=1, uniform="g")
        def row(r,c,label,key):
            ctk.CTkLabel(grid, text=label).grid(row=r, column=c, sticky="w", padx=6, pady=4)
            ctk.CTkEntry(grid, textvariable=self.v[key], corner_radius=RADIUS).grid(row=r+1, column=c, sticky="ew", padx=6)

        if p["ptype"]=="FOOD":
            row(0,0,"Meat choices (comma)","meat")
            row(0,1,"Spice levels (comma)","spice")
        else:
            row(0,0,"Sweetness (comma)","sweet")
            row(0,1,"Ice (comma)","ice")

        ctk.CTkButton(frm, text="Save options", command=lambda:self._save(p["ptype"]), corner_radius=RADIUS).pack(pady=10)

    def _save(self, ptype):
        try:
            if ptype=="FOOD":
                self.db.set_option(self.pid, "Meat", {"values":[s.strip() for s in self.v["meat"].get().split(",") if s.strip()]})
                self.db.set_option(self.pid, "Spice",{"values":[s.strip() for s in self.v["spice"].get().split(",") if s.strip()]})
            else:
                self.db.set_option(self.pid, "Sweetness",{"values":[s.strip() for s in self.v["sweet"].get().split(",") if s.strip()]})
                self.db.set_option(self.pid, "Ice",{"values":[s.strip() for s in self.v["ice"].get().split(",") if s.strip()]})
            messagebox.showinfo("Saved","Options updated"); self.destroy()
        except Exception as e:
            messagebox.showerror("Options", str(e))

class ProductToppingMap(ctk.CTkToplevel):
    def __init__(self, master, db: DB, pid):
        super().__init__(master); self.db=db; self.pid=pid
        self.title("Product Toppings Map"); self.geometry("520x520"); self.configure(fg_color=RIGHT_BG)
        frm = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=RADIUS); frm.pack(fill="both", expand=True, padx=12, pady=12)
        self.all = self.db.list_toppings(); allowed = set(self.db.product_allowed_toppings(pid))
        self.vars=[]
        ctk.CTkLabel(frm, text="เลือกท็อปปิงที่อนุญาตให้สินค้าใช้", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10,6))
        box = ctk.CTkFrame(frm, fg_color="transparent"); box.pack(fill="both", expand=True, padx=10, pady=6)
        for t in self.all:
            v=tk.IntVar(value=1 if t["id"] in allowed else 0); self.vars.append((t["id"], v))
            ctk.CTkCheckBox(box, text=f"{t['name']} (+{t['price']:.2f})", variable=v).pack(anchor="w", pady=2)
        ctk.CTkButton(frm, text="Save", command=self._save, corner_radius=RADIUS).pack(pady=10)

    def _save(self):
        ids=[tid for tid,v in self.vars if v.get()==1]
        self.db.set_product_toppings(self.pid, ids)
        messagebox.showinfo("Saved","Toppings mapping updated"); self.destroy()

# =====================================================================
# CUSTOMER APP (Toplevel)
# =====================================================================
class CustomerApp(ctk.CTkToplevel):
    def __init__(self, master, db: DB, user_row):
        super().__init__(master); self.db=db; self.user=user_row
        self.title(f"{APP_TITLE} — STORE"); 
        try: self.state("zoomed")
        except: self.geometry("1200x720")
        self.configure(fg_color=RIGHT_BG)
        self.protocol("WM_DELETE_WINDOW", self._logout)
        self.cart: List[Dict[str,Any]] = []  # {pid,name,qty,unit_price,options,toppings[],note}

        # Header
        top = ctk.CTkFrame(self, fg_color="transparent"); top.pack(fill="x", padx=12, pady=12)
        # avatar
        self._avatar_label = ctk.CTkLabel(top, text="")
        self._avatar_label.pack(side="left", padx=(6,8))
        self._refresh_avatar()
        name = self.user.get("name") or self.user["username"]
        self.lbl_user = ctk.CTkButton(top, text=name, fg_color="transparent", hover_color="#e9dcc6",
                                      command=self._edit_profile)
        self.lbl_user.pack(side="left")

        ctk.CTkButton(top, text="Logout", command=self._logout, corner_radius=RADIUS).pack(side="right")

        # 3 ปุ่มวงกลมกลางหน้า
        mid = ctk.CTkFrame(self, fg_color="transparent"); mid.pack(pady=16)
        def circle(text, cmd):
            b = ctk.CTkButton(mid, text=text, width=140, height=140, corner_radius=140,
                              fg_color="#f1e3ca", hover_color="#e9dcc6", text_color=TEXT_DARK, command=cmd)
            b.pack(side="left", padx=16); return b
        circle("FOOD", self._show_food)
        circle("DRINK", self._show_drink)
        circle("CART", self._show_cart)

        # body placeholder
        self.body = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=RADIUS)
        self.body.pack(fill="both", expand=True, padx=12, pady=12)

        self._show_food()

        self.grab_set(); self.focus()

    def _logout(self):
        try: self.grab_release()
        except: pass
        self.destroy()
        self.master.deiconify()

    def _refresh_avatar(self):
        path = self.user["avatar"] or ""
        if path and os.path.exists(path):
            img = Image.open(path).convert("RGBA")
            img = ImageOps.fit(img, (42,42), Image.LANCZOS)
            mask = Image.new("L", (42,42), 0); mdraw = Image.new("L",(42,42))
            circle = Image.new('L', (42,42), 0); 
            # quick circle mask:
            from PIL import ImageDraw
            d=ImageDraw.Draw(circle); d.ellipse((0,0,42,42), fill=255)
            img.putalpha(circle)
            self._avatar = ctk.CTkImage(light_image=img, dark_image=img, size=(42,42))
            self._avatar_label.configure(image=self._avatar, text="")
        else:
            self._avatar_label.configure(text="🙂", font=ctk.CTkFont(size=28))

    def _clear_body(self):
        for w in self.body.winfo_children(): w.destroy()

    # ---------------- Profile dialog ----------------
    def _edit_profile(self):
        dlg = ctk.CTkToplevel(self); dlg.title("Edit Profile"); dlg.geometry("520x360"); dlg.configure(fg_color=RIGHT_BG)
        frm = ctk.CTkFrame(dlg, fg_color=CARD_BG, corner_radius=RADIUS); frm.pack(fill="both", expand=True, padx=12, pady=12)
        v = {k: tk.StringVar() for k in ["name","phone","email","avatar"]}
        v["name"].set(self.user.get("name") or ""); v["phone"].set(self.user.get("phone") or "")
        v["email"].set(self.user.get("email") or ""); v["avatar"].set(self.user.get("avatar") or "")

        grid = ctk.CTkFrame(frm, fg_color="transparent"); grid.pack(fill="x", padx=12, pady=8)
        for i in range(2): grid.grid_columnconfigure(i, weight=1, uniform="g")
        def row(r,c,label,key):
            ctk.CTkLabel(grid, text=label).grid(row=r, column=c, sticky="w", padx=6, pady=2)
            ctk.CTkEntry(grid, textvariable=v[key], corner_radius=RADIUS).grid(row=r+1, column=c, sticky="ew", padx=6)
        row(0,0,"Name","name"); row(0,1,"Phone","phone"); row(2,0,"Email","email")
        ctk.CTkLabel(grid, text="Avatar path").grid(row=2, column=1, sticky="w", padx=6, pady=2)
        ctk.CTkEntry(grid, textvariable=v["avatar"], corner_radius=RADIUS).grid(row=3, column=1, sticky="ew", padx=6)
        ctk.CTkButton(grid, text="Choose...", command=lambda:self._pick_avatar(v)).grid(row=3, column=0, sticky="w", padx=6)

        ctk.CTkButton(frm, text="Save", command=lambda:self._save_profile(dlg, v)).pack(pady=10)

    def _pick_avatar(self, v):
        f=filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg")])
        if not f: return
        dst=os.path.join(ASSETS_IMG, os.path.basename(f))
        try: import shutil; shutil.copy2(f,dst); v["avatar"].set(dst)
        except Exception as e: messagebox.showerror("Avatar", str(e))

    def _save_profile(self, dlg, v):
        self.db.update_profile(self.user["id"], v["name"].get().strip(), v["phone"].get().strip(),
                               v["email"].get().strip(), v["avatar"].get().strip())
        # refresh current user row
        self.user = self.db.conn.execute("SELECT * FROM users WHERE id=?", (self.user["id"],)).fetchone()
        self._refresh_avatar()
        name = self.user.get("name") or self.user["username"]
        self.lbl_user.configure(text=name)
        dlg.destroy()
        messagebox.showinfo("Profile","Saved")

    # ---------------- FOOD / DRINK / CART views ----------------
    def _show_food(self):
        self._render_menu("FOOD")
    def _show_drink(self):
        self._render_menu("DRINK")

    def _render_menu(self, ptype):
        self._clear_body()
        top = ctk.CTkFrame(self.body, fg_color="transparent"); top.pack(fill="x", padx=12, pady=(12,0))
        ctk.CTkLabel(top, text=ptype, font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        cats = self.db.categories_by_ptype(ptype)
        self.cmb_cat = ttk.Combobox(top, values=[(c["name"] + (f" ({c['country']})" if c["country"] else "")) for c in cats],
                                    state="readonly")
        if cats: self.cmb_cat.current(0)
        self.cmb_cat.pack(side="left", padx=8)
        ctk.CTkButton(top, text="Load", command=lambda:self._load_products(ptype)).pack(side="left")

        self.tv = ttk.Treeview(self.body, columns=("name","price","stock"), show="headings", height=18)
        for k,w in [("name",360),("price",120),("stock",120)]:
            self.tv.heading(k, text=k.upper()); self.tv.column(k, width=w, anchor="w")
        self.tv.pack(fill="both", expand=True, padx=12, pady=12)
        self.tv.bind("<Double-1>", lambda e: self._pick_product(ptype))
        self._menu_ptype = ptype
        self._cats_cache = cats
        self._load_products(ptype)

    def _load_products(self, ptype):
        for i in self.tv.get_children(): self.tv.delete(i)
        sel = self.cmb_cat.current()
        if sel<0: return
        cid = self._cats_cache[sel]["id"]
        self._prod_rows = self.db.products_in_category(cid)
        for p in self._prod_rows:
            self.tv.insert("", "end", values=(p["name"], f"{p['base_price']:.2f}", p["stock"]), iid=str(p["id"]))

    def _pick_product(self, ptype):
        sel=self.tv.selection()
        if not sel: return
        pid=int(sel[0]); pr = self.db.product_row(pid)
        opts=self.db.get_options(pid)
        tops=self.db.allowed_toppings_rows(pid)

        dlg = ctk.CTkToplevel(self); dlg.title(pr["name"]); dlg.geometry("560x520"); dlg.configure(fg_color=RIGHT_BG)
        frm = ctk.CTkFrame(dlg, fg_color=CARD_BG, corner_radius=RADIUS); frm.pack(fill="both", expand=True, padx=12, pady=12)

        lbl = ctk.CTkLabel(frm, text=f"{pr['name']} — {pr['base_price']:.2f}  (stock: {pr['stock']})",
                           font=ctk.CTkFont(size=14, weight="bold")); lbl.pack(anchor="w", padx=12, pady=(10,6))

        grid = ctk.CTkFrame(frm, fg_color="transparent"); grid.pack(fill="x", padx=12, pady=6)
        for i in range(2): grid.grid_columnconfigure(i, weight=1, uniform="g")

        v_qty = tk.IntVar(value=1); v_note=tk.StringVar()
        # Option widgets
        cmb_meat=cmb_spice=cmb_sweet=cmb_ice=None
        if ptype=="FOOD":
            meats=opts.get("Meat",{}).get("values",["หมูสับ","หมูชิ้น","ไก่","หมูกรอบ"])
            spices=opts.get("Spice",{}).get("values",["เผ็ดน้อย","กลาง","เผ็ดมาก"])
            ctk.CTkLabel(grid, text="เนื้อสัตว์").grid(row=0,column=0, sticky="w", padx=6)
            cmb_meat=ttk.Combobox(grid, values=meats, state="readonly"); cmb_meat.current(0); cmb_meat.grid(row=1,column=0, sticky="ew", padx=6)
            ctk.CTkLabel(grid, text="ความเผ็ด").grid(row=0,column=1, sticky="w", padx=6)
            cmb_spice=ttk.Combobox(grid, values=spices, state="readonly"); cmb_spice.current(1 if len(spices)>1 else 0); cmb_spice.grid(row=1,column=1, sticky="ew", padx=6)
        else:
            sweets=opts.get("Sweetness",{}).get("values",["0%","50%","100%"])
            ices=opts.get("Ice",{}).get("values",["0%","25%","50%","75%","100%"])
            ctk.CTkLabel(grid, text="ความหวาน").grid(row=0,column=0, sticky="w", padx=6)
            cmb_sweet=ttk.Combobox(grid, values=sweets, state="readonly"); cmb_sweet.current(1 if "50%" in sweets else 0); cmb_sweet.grid(row=1,column=0, sticky="ew", padx=6)
            ctk.CTkLabel(grid, text="น้ำแข็ง").grid(row=0,column=1, sticky="w", padx=6)
            cmb_ice=ttk.Combobox(grid, values=ices, state="readonly"); cmb_ice.current(2 if "50%" in ices else 0); cmb_ice.grid(row=1,column=1, sticky="ew", padx=6)

        # toppings (checkbox list)
        top_box = ctk.CTkFrame(frm, fg_color="transparent"); top_box.pack(fill="both", expand=True, padx=12, pady=6)
        ctk.CTkLabel(top_box, text="Toppings", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        top_vars=[]
        if tops:
            for t in tops:
                v=tk.IntVar(value=0); top_vars.append((t,v))
                ctk.CTkCheckBox(top_box, text=f"{t['name']} (+{t['price']:.2f})", variable=v).pack(anchor="w")
        else:
            ctk.CTkLabel(top_box, text="— none —", text_color="#6b7280").pack(anchor="w")

        # qty + note
        bottom = ctk.CTkFrame(frm, fg_color="transparent"); bottom.pack(fill="x", padx=12, pady=(4,6))
        ctk.CTkLabel(bottom, text="Qty").pack(side="left"); 
        ent_qty=ctk.CTkEntry(bottom, textvariable=v_qty, width=80, corner_radius=RADIUS); ent_qty.pack(side="left", padx=6)
        ctk.CTkLabel(bottom, text="Note").pack(side="left"); 
        ent_note=ctk.CTkEntry(bottom, textvariable=v_note, width=240, corner_radius=RADIUS); ent_note.pack(side="left", padx=6)
        def add_to_cart():
            qty=max(1, int(safe_float(v_qty.get(),1)))
            if qty > pr["stock"]:
                messagebox.showwarning("Stock","จำนวนเกินสต็อกคงเหลือ"); return
            options={}
            if cmb_meat: options["Meat"]=cmb_meat.get()
            if cmb_spice: options["Spice"]=cmb_spice.get()
            if cmb_sweet: options["Sweetness"]=cmb_sweet.get()
            if cmb_ice: options["Ice"]=cmb_ice.get()
            tops_sel=[{"id":t["id"],"name":t["name"],"price":float(t["price"])} for t,v in top_vars if v.get()==1]
            self.cart.append(dict(pid=pr["id"], name=pr["name"], qty=qty, unit_price=float(pr["base_price"]),
                                  options=options, toppings=tops_sel, note=v_note.get().strip()))
            dlg.destroy(); self._show_cart()
        ctk.CTkButton(frm, text="Add to Basket", command=add_to_cart, corner_radius=RADIUS).pack(pady=(2,10), anchor="e")

    def _show_cart(self):
        self._clear_body()
        ctk.CTkLabel(self.body, text="CART", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=12, pady=(12,0))
        tv = ttk.Treeview(self.body, columns=("name","qty","price","opt"), show="headings", height=16)
        for k,w in [("name",320),("qty",80),("price",120),("opt",320)]:
            tv.heading(k, text=k.upper()); tv.column(k, width=w, anchor="w")
        tv.pack(fill="both", expand=True, padx=12, pady=12)
        subtotal=0.0
        for i,it in enumerate(self.cart,1):
            tops_price = sum(t["price"] for t in it.get("toppings",[]))
            line = (it["unit_price"] + tops_price)*it["qty"]; subtotal += line
            opt_s = ", ".join([*(f"{k}:{v}" for k,v in (it.get("options") or {}).items()),
                               *(f"{t['name']}(+{t['price']})" for t in it.get("toppings",[]))])
            tv.insert("", "end", values=(it["name"], it["qty"], f"{line:.2f}", opt_s))
        vat = round((subtotal)*VAT_RATE, 2); total = round(subtotal + vat, 2)
        summ = ctk.CTkFrame(self.body, fg_color="transparent"); summ.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(summ, text=f"Subtotal: {subtotal:.2f}    VAT(7%): {vat:.2f}    Total: {total:.2f}",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")

        # fulfillment/pay
        box = ctk.CTkFrame(self.body, fg_color="#f1e3ca", corner_radius=RADIUS); box.pack(fill="x", padx=12, pady=(4,12))
        v_ful = tk.StringVar(value="PICKUP"); v_pay=tk.StringVar(value="CASH")
        ttk.Radiobutton(box, text="รับเองที่ร้าน", variable=v_ful, value="PICKUP",
                        command=lambda:v_pay.set("CASH")).pack(side="left", padx=8)
        ttk.Radiobutton(box, text="จัดส่ง", variable=v_ful, value="DELIVERY",
                        command=lambda:v_pay.set("QR")).pack(side="left", padx=8)
        ctk.CTkLabel(box, text="Pay:").pack(side="left", padx=(20,6))
        cmb_pay = ttk.Combobox(box, values=["CASH","QR"], textvariable=v_pay, state="readonly", width=8); cmb_pay.pack(side="left")

        addr_vars = {k: tk.StringVar() for k in ["name","phone","address"]}
        addr_frame = ctk.CTkFrame(self.body, fg_color="transparent"); addr_frame.pack(fill="x", padx=12)
        def _render_addr():
            for w in addr_frame.winfo_children(): w.destroy()
            if v_ful.get()=="DELIVERY":
                for label,key,wid in [("ชื่อผู้รับ","name",200),("โทร","phone",160),("ที่อยู่","address",520)]:
                    row = ctk.CTkFrame(addr_frame, fg_color="transparent"); row.pack(fill="x", pady=4)
                    ctk.CTkLabel(row, text=label).pack(side="left", padx=6)
                    ctk.CTkEntry(row, textvariable=addr_vars[key], corner_radius=RADIUS, width=wid).pack(side="left")
                # show QR
                if os.path.exists(QR_PATH):
                    qr_img = Image.open(QR_PATH)
                    qr_img = ImageOps.contain(qr_img, (180,180))
                    self._qr_ctk = ctk.CTkImage(light_image=qr_img, dark_image=qr_img, size=(180,180))
                    ctk.CTkLabel(addr_frame, image=self._qr_ctk, text="").pack(pady=6)
        _render_addr()
        v_ful.trace_add("write", lambda *a: _render_addr())

        footer = ctk.CTkFrame(self.body, fg_color="transparent"); footer.pack(fill="x", padx=12, pady=8)
        ctk.CTkButton(footer, text="Clear Cart", command=lambda:self._clear_cart(tv), corner_radius=RADIUS).pack(side="left")
        ctk.CTkButton(footer, text="Checkout", command=lambda:self._checkout(v_ful.get(), v_pay.get(), addr_vars), corner_radius=RADIUS).pack(side="right")

    def _clear_cart(self, tv):
        self.cart.clear(); 
        for i in tv.get_children(): tv.delete(i)

    def _checkout(self, fulfillment, pay_method, addr_vars):
        if not self.cart:
            messagebox.showwarning("Checkout","Cart is empty"); return
        addr=None
        if fulfillment=="DELIVERY":
            if not addr_vars["name"].get().strip() or not addr_vars["phone"].get().strip() or not addr_vars["address"].get().strip():
                messagebox.showwarning("Address","กรอกข้อมูลผู้รับให้ครบ"); return
            addr=dict(name=addr_vars["name"].get().strip(), phone=addr_vars["phone"].get().strip(),
                      address=addr_vars["address"].get().strip())
            pay_method="QR"   # บังคับตามสเปก
        try:
            oid, sub, disc, vat, tot = self.db.create_order(self.user["id"], self.cart, fulfillment, pay_method, addr)
            self.cart.clear()
            messagebox.showinfo("Order", f"สร้างคำสั่งซื้อ #{oid}\nSubtotal: {sub:.2f}\nVAT: {vat:.2f}\nTotal: {tot:.2f}\nสถานะ: PENDING")
            # เสนอออกบิลเลยไหม (กรณีจ่ายแล้ว)
            if messagebox.askyesno("Receipt", "ต้องการบันทึกใบเสร็จเลยไหม?"):
                path = save_receipt(self.db, oid)
                messagebox.showinfo("Receipt", f"Saved: {path}")
            self._show_food()
        except Exception as e:
            messagebox.showerror("Checkout", str(e))

# =====================================================================
# MAIN
# =====================================================================
if __name__ == "__main__":
    db = DB(DB_FILE)
    app = LoginApp(db)
    app.mainloop()