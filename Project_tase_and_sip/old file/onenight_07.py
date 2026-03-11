# -*- coding: utf-8 -*-
"""
TASTE & SIP — Single-file App (Auth + Admin + Customer)
- customtkinter, sqlite3, pillow, reportlab
- TAX ID, VAT 7%, QR path, Logo path per user spec
- Categories: only FOOD and DRINK; FOOD has sub 'country' (THAI/ITALIAN/KOREAN/CHINESE/JAPANESE)
- Admin: manage categories/countries, products (image + stock), toppings, orders, promotions(optional), receipt PDF
- Customer: profile (edit + avatar), 3 big circular buttons FOOD/DRINK/CART, options, toppings, notes, stock check, delivery/pickup, pay (QR / cash for pickup)
- Logout returns to Login

Run: python taste_and_sip.py
"""

import os, re, json, sqlite3, hashlib
from datetime import datetime as dt, timedelta
from typing import Optional, Callable, Dict, Any, List
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import customtkinter as ctk
from PIL import Image, ImageTk

# ------------------ CONSTANTS ------------------
APP_TITLE = "TASTE AND SIP"
DB_FILE   = "taste_and_sip.db"
ASSETS    = "assets"; os.makedirs(ASSETS, exist_ok=True)
IMG_DIR   = os.path.join(ASSETS, "images"); os.makedirs(IMG_DIR, exist_ok=True)
IMG_PROD  = os.path.join(IMG_DIR, "products"); os.makedirs(IMG_PROD, exist_ok=True)
REPORTS   = "receipts"; os.makedirs(REPORTS, exist_ok=True)

RIGHT_BG   = "#f8eedb"
CARD_BG    = "#edd8b8"
TEXT_DARK  = "#1f2937"
LINK_FG    = "#0057b7"
BORDER     = "#d3c6b4"
RADIUS     = 18

# User-provided paths
LOGO_PATH = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\lologogo.png-removebg-preview.png"
QR_PATH   = r"C:\Users\thatt\Downloads\qrcode.jpg"
TAX_ID    = "0998877445566"
TEL       = "0954751704"

# ------------------ HELPERS ------------------
def sha256(s: str) -> str: return hashlib.sha256(s.encode("utf-8")).hexdigest()
def now() -> str: return dt.now().strftime("%Y-%m-%d %H:%M:%S")
def f2(x): 
    try: return f"{float(x):.2f}"
    except: return "0.00"

# ------------------ DB LAYER ------------------
class DB:
    def __init__(self, path=DB_FILE):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.schema(); self.seed()

    def schema(self):
        c = self.conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT, email TEXT, phone TEXT,
            avatar TEXT, role TEXT DEFAULT 'customer',
            address TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS categories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            main TEXT NOT NULL,        -- FOOD or DRINK
            country TEXT               -- only for FOOD; NULL for DRINK
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ptype TEXT NOT NULL,       -- FOOD/DRINK
            category_id INTEGER,
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            image TEXT,
            is_active INTEGER DEFAULT 1
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS product_options(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            option_name TEXT NOT NULL,
            option_json TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS toppings(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            is_active INTEGER DEFAULT 1
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            order_datetime TEXT,
            status TEXT,
            ship_method TEXT, -- DELIVERY/PICKUP
            ship_name TEXT, ship_phone TEXT, ship_address TEXT,
            subtotal REAL, discount REAL, vat REAL, total REAL,
            payment TEXT, note TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS order_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            name TEXT,
            qty INTEGER,
            unit_price REAL,
            options_json TEXT,
            toppings_json TEXT,
            add_price REAL DEFAULT 0
        )""")
        self.conn.commit()

    def seed(self):
        c = self.conn.cursor()
        # admin
        if not c.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
            c.execute("INSERT INTO users(username,password_hash,name,role) VALUES(?,?,?,?)",
                      ("admin", sha256("admin123"), "Administrator", "admin"))
        # categories: only FOOD main with countries + DRINK (country NULL)
        wanted_countries = ["THAI","ITALIAN","KOREAN","CHINESE","JAPANESE"]
        for ct in wanted_countries:
            if not c.execute("SELECT 1 FROM categories WHERE main='FOOD' AND country=?", (ct,)).fetchone() :
                c.execute("INSERT INTO categories(main,country) VALUES('FOOD',?)", (ct,))
        if not c.execute("SELECT 1 FROM categories WHERE main='DRINK'").fetchone():
            c.execute("INSERT INTO categories(main,country) VALUES('DRINK',NULL)")
        # toppings default
        def ensure_top(name, price):
            if not c.execute("SELECT 1 FROM toppings WHERE name=?", (name,)).fetchone():
                c.execute("INSERT INTO toppings(name,price,is_active) VALUES(?,?,1)", (name, price))
        for nm,pr in [("ไข่ต้ม",15),("ไข่ดาว",15),("ไข่ออนเซ็น",15),("ไข่ข้น",15),("ไข่ดอง",15),
                      ("เบค่อน",25),("หมูกรอบ",25),("ไข่กุ้ง",20)]:
            ensure_top(nm, pr)
        # demo products
        if not c.execute("SELECT 1 FROM products").fetchone():
            cat_thai = c.execute("SELECT id FROM categories WHERE main='FOOD' AND country='THAI'").fetchone()["id"]
            cat_drk  = c.execute("SELECT id FROM categories WHERE main='DRINK'").fetchone()["id"]
            demo = [
                ("กะเพราหมูกรอบ", "FOOD", cat_thai, 65, 20, "", 1),
                ("ผัดไทยกุ้งสด", "FOOD", cat_thai, 75, 15, "", 1),
                ("Thai Milk Tea", "DRINK", cat_drk, 35, 40, "", 1),
                ("Matcha Latte", "DRINK", cat_drk, 55, 30, "", 1),
            ]
            c.executemany("""INSERT INTO products(name,ptype,category_id,price,stock,image,is_active)
                             VALUES(?,?,?,?,?,?,?)""", demo)
        # options defaults
        for p in self.conn.execute("SELECT * FROM products").fetchall():
            pid, ptype = p["id"], p["ptype"]
            if ptype=="FOOD":
                if not self.conn.execute("SELECT 1 FROM product_options WHERE product_id=? AND option_name='Meat'",(pid,)).fetchone():
                    self.conn.execute("INSERT INTO product_options(product_id,option_name,option_json) VALUES(?,?,?)",
                                      (pid,"Meat",json.dumps({"values":["Pork","Chicken","Beef","Seafood"]})))
                if not self.conn.execute("SELECT 1 FROM product_options WHERE product_id=? AND option_name='Spice'",(pid,)).fetchone():
                    self.conn.execute("INSERT INTO product_options(product_id,option_name,option_json) VALUES(?,?,?)",
                                      (pid,"Spice",json.dumps({"values":["Mild","Medium","Hot","Extra Hot"]})))
            else:
                if not self.conn.execute("SELECT 1 FROM product_options WHERE product_id=? AND option_name='Size'",(pid,)).fetchone():
                    self.conn.execute("INSERT INTO product_options(product_id,option_name,option_json) VALUES(?,?,?)",
                                      (pid,"Size",json.dumps({"values":["S","M","L"],"mul":{"S":1.0,"M":1.2,"L":1.5}})))
                for nm in ("Ice","Sweetness"):
                    if not self.conn.execute("SELECT 1 FROM product_options WHERE product_id=? AND option_name=?", (pid,nm)).fetchone():
                        self.conn.execute("INSERT INTO product_options(product_id,option_name,option_json) VALUES(?,?,?)",
                                          (pid,nm,json.dumps({"values":["0%","25%","50%","75%","100%"]})))
        self.conn.commit()

db = DB()

# ------------------ RECEIPT ------------------
def try_reportlab():
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.utils import ImageReader
        return canvas, A4, mm, ImageReader
    except Exception:
        return None, None, None, None

def generate_receipt(order_id: int, save_dir=REPORTS) -> str:
    c, A4, mm, IR = try_reportlab()
    if not c: raise RuntimeError("reportlab not installed")

    conn = db.conn
    o = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    its = conn.execute("SELECT * FROM order_items WHERE order_id=?", (order_id,)).fetchall()
    if not o: raise RuntimeError("Order not found")

    os.makedirs(save_dir, exist_ok=True)
    filename = os.path.join(save_dir, f"receipt_{order_id}.pdf")
    canv = c.Canvas(filename, pagesize=A4)
    W,H = A4

    # Header (logo + titles)
    y = H - 30*mm
    if LOGO_PATH and os.path.exists(LOGO_PATH):
        try: canv.drawImage(IR(LOGO_PATH), 15*mm, y-18*mm, 18*mm, 18*mm, mask='auto', preserveAspectRatio=True)
        except: pass
    canv.setFont("Helvetica-Bold", 16); canv.drawString(35*mm, y-4*mm, "TASTE & SIP")
    canv.setFont("Helvetica", 9); canv.drawString(35*mm, y-10*mm, "FOOD AND DRINK")
    canv.setFont("Helvetica", 10)
    canv.drawString(15*mm, y-24*mm, f"TEL. {TEL}")
    canv.drawString(80*mm, y-24*mm, f"TAX ID : {TAX_ID}")
    canv.drawString(15*mm, y-30*mm, "DATE " + dt.strptime(o["order_datetime"], "%Y-%m-%d %H:%M:%S").strftime("%d / %m / %Y"))
    canv.drawString(80*mm, y-30*mm, "TIME " + dt.strptime(o["order_datetime"], "%Y-%m-%d %H:%M:%S").strftime("%H : %M"))

    # Order no.
    canv.setFont("Helvetica-Bold", 13)
    canv.drawString(15*mm, y-45*mm, "ORDER NO.")
    canv.setFont("Helvetica-Bold", 12)
    canv.drawString(15*mm, y-52*mm, f"#{o['id']}")
    canv.line(15*mm, y-56*mm, 120*mm, y-56*mm)

    # Table header
    canv.setFont("Helvetica-Bold", 10)
    yy = y-64*mm
    canv.drawString(15*mm, yy, "No.")
    canv.drawString(25*mm, yy, "MENU")
    canv.drawString(80*mm, yy, "QTY.")
    canv.drawString(95*mm, yy, "PRICE")
    canv.drawString(115*mm, yy, "TOTAL")
    yy -= 6*mm

    # Items
    canv.setFont("Helvetica", 10)
    idx=1; subtotal=0
    for it in its:
        line = (it["unit_price"] + float(it["add_price"] or 0)) * it["qty"]
        subtotal += line
        canv.drawString(15*mm, yy, str(idx))
        canv.drawString(25*mm, yy, it["name"])
        canv.drawRightString(90*mm, yy, str(it["qty"]))
        canv.drawRightString(110*mm, yy, f2(it["unit_price"] + float(it["add_price"] or 0)))
        canv.drawRightString(130*mm, yy, f2(line))
        yy -= 6*mm; idx+=1

    # VAT & total
    canv.drawString(15*mm, yy-2*mm, "VAT (7%)")
    canv.drawRightString(130*mm, yy-2*mm, f2(subtotal*0.07))
    canv.line(15*mm, yy-6*mm, 130*mm, yy-6*mm)
    canv.setFont("Helvetica-Bold", 11)
    canv.drawString(15*mm, yy-12*mm, "TOTAL")
    canv.drawRightString(130*mm, yy-12*mm, f2(subtotal*1.07))
    canv.line(15*mm, yy-16*mm, 130*mm, yy-16*mm)

    # QR
    if QR_PATH and os.path.exists(QR_PATH):
        try: canv.drawImage(IR(QR_PATH), 140*mm, 20*mm, 40*mm, 40*mm, mask='auto', preserveAspectRatio=True)
        except: pass

    canv.showPage(); canv.save()
    return filename

# ------------------ AUTH ------------------
USERNAME_RE = re.compile(r"^[A-Za-z0-9]{6,}$")
PHONE_RE    = re.compile(r"^\d{10}$")
EMAIL_RE    = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PWD_RE      = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,}$")

def validate_username(v): return None if USERNAME_RE.match(v or "") else "USERNAME ≥6, A-Z/0-9"
def validate_phone(v):    return None if PHONE_RE.match(v or "") else "PHONE 10 DIGITS"
def validate_email(v):    return None if EMAIL_RE.match(v or "") else "INVALID EMAIL"
def validate_password(v): return None if PWD_RE.match(v or "") else "PASSWORD ≥8 (Aa1)"

class Title(ctk.CTkLabel):
    def __init__(self, master, text): super().__init__(master, text=text.upper(),
        font=ctk.CTkFont(size=20, weight="bold"), text_color=TEXT_DARK, fg_color="transparent")

class ErrorLabel(ctk.CTkLabel):
    def __init__(self, master): super().__init__(master, text="", text_color="#b00020", wraplength=560, fg_color="transparent")
    def set(self, t): self.configure(text=(t or "").upper())

class LineEntry(ctk.CTkFrame):
    def __init__(self, master, label, show=""):
        super().__init__(master, fg_color="transparent"); self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=label.upper(), text_color="#333", font=ctk.CTkFont(size=11, weight="bold"),
                     fg_color="transparent").grid(row=0, column=0, sticky="w", padx=2, pady=(0,2))
        self.ent = ctk.CTkEntry(self, show=show, corner_radius=RADIUS, border_color=BORDER, fg_color="white")
        self.ent.grid(row=1, column=0, sticky="ew")
    def get(self): return self.ent.get()
    def set(self, v): self.ent.delete(0,"end"); self.ent.insert(0,v)

class AuthApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        self.title(APP_TITLE)
        try: self.state("zoomed")
        except: self.geometry("1200x720")
        self.configure(fg_color=RIGHT_BG)
        self.grid_columnconfigure(0,weight=1); self.grid_columnconfigure(1,weight=1); self.grid_rowconfigure(0,weight=1)

        # left canvas
        self.left = ctk.CTkFrame(self, fg_color=RIGHT_BG); self.left.grid(row=0,column=0,sticky="nsew")
        self.cv = tk.Canvas(self.left, bd=0, highlightthickness=0, bg=RIGHT_BG); self.cv.place(relx=0,rely=0,relwidth=1,relheight=1)
        self.left.bind("<Configure>", lambda e: self._paint_left())

        # right card
        self.right = ctk.CTkFrame(self, fg_color=RIGHT_BG); self.right.grid(row=0,column=1,sticky="nsew")
        self.right.grid_rowconfigure(1, weight=1)
        self.logo = ctk.CTkFrame(self.right, fg_color=RIGHT_BG); self.logo.grid(row=0,column=0,pady=(30,10))
        if LOGO_PATH and os.path.exists(LOGO_PATH):
            try:
                img = Image.open(LOGO_PATH); self._logo = ctk.CTkImage(light_image=img, dark_image=img, size=(200,200))
                ctk.CTkLabel(self.logo, image=self._logo, text="").pack()
            except: ctk.CTkLabel(self.logo, text=APP_TITLE, font=ctk.CTkFont(size=22, weight="bold")).pack()
        else:
            ctk.CTkLabel(self.logo, text=APP_TITLE, font=ctk.CTkFont(size=22, weight="bold")).pack()

        self.card = ctk.CTkFrame(self.right, fg_color=CARD_BG, corner_radius=RADIUS,
                                 border_color=BORDER, border_width=1, width=660, height=560)
        self.card.grid(row=1,column=0, sticky="n", padx=80, pady=(10,40)); self.card.grid_propagate(False)
        self.show_login()

    def _paint_left(self):
        c=self.cv; c.delete("all"); w=max(300,int(self.winfo_width()*0.5)); h=max(300,self.winfo_height())
        c.configure(width=w,height=h); c.create_rectangle(0,0,w,h,fill=RIGHT_BG,outline="")
        t1 = c.create_text(28,28,anchor="nw",fill="white",font=("Segoe UI",36,"bold"),
                           text=f"WELCOME TO\n{APP_TITLE}".upper())
        y2 = (c.bbox(t1)[3] if c.bbox(t1) else 120)+18
        c.create_text(32,y2,anchor="nw",fill="white",font=("Segoe UI",18,"bold"),
                      text="FOOD AND DRINK!".upper())

    def _clear(self): [w.destroy() for w in self.card.winfo_children()]

    def show_login(self):
        self._clear(); Title(self.card, "SIGN IN").pack(pady=(22,6))
        self.err = ErrorLabel(self.card); self.err.pack(padx=28, fill="x")
        self.u = LineEntry(self.card,"USERNAME"); self.u.pack(fill="x", padx=28, pady=(6,8))
        self.p = LineEntry(self.card,"PASSWORD",show="•"); self.p.pack(fill="x", padx=28, pady=(6,12))
        ctk.CTkButton(self.card,text="SIGN IN",corner_radius=RADIUS,command=self._do_login).pack(fill="x",padx=28,pady=(0,12))
        bot = ctk.CTkFrame(self.card, fg_color="transparent"); bot.pack(fill="x", pady=(4,18))
        ctk.CTkButton(bot,text="FORGOT PASSWORD?", command=self.show_forgot, fg_color="transparent",
                      hover_color="#e9dcc6", text_color=LINK_FG).pack(side="left", padx=4)
        ctk.CTkButton(bot,text="CREATE ACCOUNT", command=self.show_signup, fg_color="transparent",
                      hover_color="#e9dcc6", text_color=LINK_FG).pack(side="right", padx=4)

    def show_signup(self):
        self._clear(); Title(self.card,"CREATE ACCOUNT").pack(pady=(22,6))
        self.err = ErrorLabel(self.card); self.err.pack(padx=24, fill="x")
        form = ctk.CTkFrame(self.card, fg_color="transparent"); form.pack(fill="x", padx=24, pady=(6,10))
        form.grid_columnconfigure(0,weight=1,uniform="c"); form.grid_columnconfigure(1,weight=1,uniform="c")
        self.su_user=LineEntry(form,"USERNAME");  self.su_user.grid(row=0,column=0, padx=8,pady=6,sticky="ew")
        self.su_phone=LineEntry(form,"PHONE");    self.su_phone.grid(row=0,column=1, padx=8,pady=6,sticky="ew")
        self.su_email=LineEntry(form,"EMAIL");    self.su_email.grid(row=1,column=0, columnspan=2,padx=8,pady=6,sticky="ew")
        self.su_pwd1=LineEntry(form,"PASSWORD",show="•"); self.su_pwd1.grid(row=2,column=0,padx=8,pady=6,sticky="ew")
        self.su_pwd2=LineEntry(form,"CONFIRM PASSWORD",show="•"); self.su_pwd2.grid(row=2,column=1,padx=8,pady=6,sticky="ew")
        ctk.CTkButton(self.card,text="REGISTER",command=self._do_signup,corner_radius=RADIUS).pack(fill="x",padx=24,pady=(8,12))
        ctk.CTkButton(self.card,text="BACK TO LOGIN",command=self.show_login, fg_color="transparent",
                      hover_color="#e9dcc6", text_color=LINK_FG).pack(pady=(0,18))

    def show_forgot(self):
        self._clear(); Title(self.card,"FORGOT PASSWORD").pack(pady=(22,6))
        self.err = ErrorLabel(self.card); self.err.pack(padx=24, fill="x")
        self.fp_user=LineEntry(self.card,"USERNAME"); self.fp_user.pack(fill="x", padx=24, pady=(6,8))
        self.fp_contact=LineEntry(self.card,"EMAIL OR PHONE"); self.fp_contact.pack(fill="x", padx=24, pady=(6,10))
        ctk.CTkButton(self.card,text="VERIFY",command=self._do_verify).pack(fill="x", padx=24, pady=(0,12))
        self.fp2 = ctk.CTkFrame(self.card, fg_color="transparent"); self.fp2.pack(fill="x", padx=16, pady=(6,12)); self.fp2.pack_forget()
        self.np1=LineEntry(self.fp2,"NEW PASSWORD",show="•"); self.np1.pack(fill="x", padx=12, pady=(6,8))
        self.np2=LineEntry(self.fp2,"CONFIRM NEW PASSWORD",show="•"); self.np2.pack(fill="x", padx=12, pady=(6,10))
        ctk.CTkButton(self.fp2,text="CHANGE PASSWORD",command=self._do_change).pack(fill="x", padx=12, pady=(0,10))
        ctk.CTkButton(self.card,text="BACK TO LOGIN",command=self.show_login, fg_color="transparent",
                      hover_color="#e9dcc6", text_color=LINK_FG).pack(pady=(0,18))
        self._verified = None

    # actions
    def _do_login(self):
        u,p = self.u.get().strip(), self.p.get().strip()
        if not u or not p: self.err.set("PLEASE ENTER USERNAME/PASSWORD"); return
        row = db.conn.execute("SELECT * FROM users WHERE username=? AND password_hash=?", (u,sha256(p))).fetchone()
        if not row: self.err.set("INVALID CREDENTIALS"); return
        # route
        self.withdraw()
        if (row["role"] or "customer").lower()=="admin":
            AdminApp(self, row)
        else:
            CustomerApp(self, row)

    def _do_signup(self):
        u,ph,em,p1,p2 = self.su_user.get().strip(), self.su_phone.get().strip(), self.su_email.get().strip(), self.su_pwd1.get().strip(), self.su_pwd2.get().strip()
        for fn,msg in [(validate_username(u),"USERNAME"),(validate_phone(ph),"PHONE"),(validate_email(em),"EMAIL"),(validate_password(p1),"PASSWORD")]:
            if fn: self.err.set(fn); return
        if p1!=p2: self.err.set("PASSWORDS DO NOT MATCH"); return
        try:
            db.conn.execute("INSERT INTO users(username,password_hash,phone,email,role) VALUES(?,?,?,?,?)",
                            (u,sha256(p1),ph,em,"customer")); db.conn.commit()
            self.err.set("ACCOUNT CREATED. PLEASE SIGN IN.")
        except sqlite3.IntegrityError: self.err.set("USERNAME EXISTS")

    def _do_verify(self):
        u,cp = self.fp_user.get().strip(), self.fp_contact.get().strip()
        if not u or not cp: self.err.set("FILL USERNAME + EMAIL/PHONE"); return
        row = db.conn.execute("SELECT 1 FROM users WHERE username=? AND (email=? OR phone=?)",(u,cp,cp)).fetchone()
        if row:
            self._verified = u; self.err.set("VERIFIED. SET NEW PASSWORD"); self.fp2.pack(fill="x")
        else: self.err.set("NO MATCH")

    def _do_change(self):
        if not self._verified: self.err.set("VERIFY FIRST"); return
        p1,p2 = self.np1.get().strip(), self.np2.get().strip()
        if validate_password(p1): self.err.set(validate_password(p1)); return
        if p1!=p2: self.err.set("PASSWORDS DO NOT MATCH"); return
        db.conn.execute("UPDATE users SET password_hash=? WHERE username=?", (sha256(p1), self._verified)); db.conn.commit()
        self.err.set("PASSWORD CHANGED. SIGN IN NOW")

# ------------------ ADMIN UI ------------------
class AdminApp(ctk.CTkToplevel):
    def __init__(self, root, admin_row):
        super().__init__(root); self.root=root; self.admin=admin_row
        self.title(f"{APP_TITLE} — ADMIN"); 
        try: self.state("zoomed")
        except: self.geometry("1400x820")
        self.configure(fg_color=RIGHT_BG)
        self.protocol("WM_DELETE_WINDOW", self._logout)

        top = ctk.CTkFrame(self, fg_color="transparent"); top.pack(fill="x", padx=12, pady=12)
        ctk.CTkLabel(top, text=f"ADMIN: {admin_row['username']}", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        ctk.CTkButton(top, text="LOGOUT", command=self._logout, corner_radius=RADIUS).pack(side="right")

        tabs = ctk.CTkTabview(self, fg_color=CARD_BG, segmented_button_fg_color="#e8d4b2",
                              segmented_button_selected_color="#e2cda6",
                              segmented_button_unselected_color="#f1e3ca",
                              text_color=TEXT_DARK, corner_radius=RADIUS)
        tabs.pack(fill="both", expand=True, padx=12, pady=12)
        self.t_dash = tabs.add("Dashboard"); self.t_cat = tabs.add("Categories/Products")
        self.t_top  = tabs.add("Toppings"); self.t_order = tabs.add("Orders")

        self._dash_ui(); self._catprod_ui(); self._top_ui(); self._order_ui()

    def _logout(self):
        try: self.destroy()
        finally:
            self.root.deiconify()

    # Dashboard (very simple list totals by day)
    def _dash_ui(self):
        fr = ctk.CTkFrame(self.t_dash, fg_color="transparent"); fr.pack(fill="both", expand=True, padx=10, pady=10)
        self.tv = ttk.Treeview(fr, columns=("d","total"), show="headings"); self.tv.pack(fill="both", expand=True)
        self.tv.heading("d", text="DATE"); self.tv.heading("total", text="TOTAL")
        rows = db.conn.execute("""SELECT substr(order_datetime,1,10) d, SUM(total) total
                                  FROM orders GROUP BY d ORDER BY d DESC""").fetchall()
        for r in rows: self.tv.insert("", "end", values=(r["d"], f2(r["total"] or 0)))

    # Categories & Products management
    def _catprod_ui(self):
        wrap = ctk.CTkFrame(self.t_cat, fg_color="transparent"); wrap.pack(fill="both", expand=True, padx=10, pady=10)

        left = ctk.CTkFrame(wrap, fg_color=CARD_BG, corner_radius=RADIUS); left.pack(side="left", fill="y", padx=8, pady=8)
        right= ctk.CTkFrame(wrap, fg_color=CARD_BG, corner_radius=RADIUS); right.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        ctk.CTkLabel(left, text="FOOD Countries", font=ctk.CTkFont(size=14, weight="bold")).pack(padx=12, pady=(12,4), anchor="w")
        self.lb_c = tk.Listbox(left, height=12); self.lb_c.pack(fill="y", padx=12, pady=(0,8))
        btns = ctk.CTkFrame(left, fg_color="transparent"); btns.pack(padx=12, pady=6)
        ctk.CTkButton(btns, text="Add Country", command=self._add_country).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Delete", command=self._del_country).pack(side="left", padx=4)

        ctk.CTkLabel(right, text="Products", font=ctk.CTkFont(size=14, weight="bold")).pack(padx=12, pady=(12,4), anchor="w")
        self.tv_p = ttk.Treeview(right, columns=("id","name","ptype","country","price","stock","active"), show="headings", height=14)
        for k,w in [("id",60),("name",180),("ptype",70),("country",110),("price",80),("stock",70),("active",60)]:
            self.tv_p.heading(k, text=k.upper()); self.tv_p.column(k, width=w, anchor="w")
        self.tv_p.pack(fill="both", expand=True, padx=12, pady=(0,8))
        cb = ctk.CTkFrame(right, fg_color="transparent"); cb.pack(padx=12, pady=6, fill="x")
        ctk.CTkButton(cb, text="Add / Edit", command=self._edit_product).pack(side="left", padx=4)
        ctk.CTkButton(cb, text="Delete", command=self._del_product).pack(side="left", padx=4)
        ctk.CTkButton(cb, text="Options", command=self._edit_options).pack(side="left", padx=4)

        self._reload_countries(); self._reload_products()

    def _reload_countries(self):
        self.lb_c.delete(0,"end")
        self.c_rows = db.conn.execute("SELECT * FROM categories WHERE main='FOOD' ORDER BY country").fetchall()
        for r in self.c_rows: self.lb_c.insert("end", r["country"])

    def _reload_products(self):
        self.tv_p.delete(*self.tv_p.get_children())
        rows = db.conn.execute("""SELECT p.*, c.country FROM products p
                                  LEFT JOIN categories c ON c.id=p.category_id
                                  ORDER BY p.id DESC""").fetchall()
        for r in rows:
            self.tv_p.insert("", "end", values=(r["id"], r["name"], r["ptype"], r["country"] or "-", f2(r["price"]), r["stock"], r["is_active"]))

    def _add_country(self):
        name = tk.simpledialog.askstring("Add Country", "Country (UPPERCASE):")
        if not name: return
        name = name.strip().upper()
        if not name: return
        db.conn.execute("INSERT INTO categories(main,country) VALUES('FOOD',?)",(name,)); db.conn.commit()
        self._reload_countries()

    def _del_country(self):
        sel = self.lb_c.curselection()
        if not sel: return
        cid = self.c_rows[sel[0]]["id"]
        if messagebox.askyesno("Delete","Remove this country? (Menus remain but no country)"):
            db.conn.execute("DELETE FROM categories WHERE id=?", (cid,)); db.conn.commit()
            self._reload_countries(); self._reload_products()

    def _edit_product(self):
        sel = self.tv_p.selection()
        pid = int(self.tv_p.item(sel[0],"values")[0]) if sel else None
        ProductEditor(self, pid, self._reload_products)

    def _del_product(self):
        sel = self.tv_p.selection()
        if not sel: return
        pid = int(self.tv_p.item(sel[0],"values")[0])
        if messagebox.askyesno("Delete","Delete this product?"):
            db.conn.execute("DELETE FROM products WHERE id=?", (pid,)); db.conn.commit()
            self._reload_products()

    def _edit_options(self):
        sel = self.tv_p.selection()
        if not sel: return
        pid = int(self.tv_p.item(sel[0],"values")[0])
        OptionEditor(self, pid)

    # Toppings tab
    def _top_ui(self):
        fr = ctk.CTkFrame(self.t_top, fg_color="transparent"); fr.pack(fill="both", expand=True, padx=10, pady=10)
        self.tv_top = ttk.Treeview(fr, columns=("id","name","price","active"), show="headings")
        for k,w in [("id",60),("name",200),("price",100),("active",80)]:
            self.tv_top.heading(k, text=k.upper()); self.tv_top.column(k,width=w,anchor="w")
        self.tv_top.pack(fill="both", expand=True, padx=8, pady=8)
        bb = ctk.CTkFrame(fr, fg_color="transparent"); bb.pack(pady=6)
        ctk.CTkButton(bb, text="Add", command=self._top_add).pack(side="left", padx=4)
        ctk.CTkButton(bb, text="Edit", command=self._top_edit).pack(side="left", padx=4)
        ctk.CTkButton(bb, text="Delete", command=self._top_del).pack(side="left", padx=4)
        self._top_reload()

    def _top_reload(self):
        self.tv_top.delete(*self.tv_top.get_children())
        for r in db.conn.execute("SELECT * FROM toppings ORDER BY id DESC").fetchall():
            self.tv_top.insert("", "end", values=(r["id"], r["name"], f2(r["price"]), r["is_active"]))

    def _top_add(self):
        name = tk.simpledialog.askstring("Topping","Name:")
        if not name: return
        price = tk.simpledialog.askfloat("Topping","Price:", minvalue=0.0)
        if price is None: return
        db.conn.execute("INSERT INTO toppings(name,price,is_active) VALUES(?,?,1)", (name.strip(), price)); db.conn.commit()
        self._top_reload()

    def _top_edit(self):
        sel = self.tv_top.selection()
        if not sel: return
        rid = int(self.tv_top.item(sel[0],"values")[0])
        r = db.conn.execute("SELECT * FROM toppings WHERE id=?", (rid,)).fetchone()
        name = tk.simpledialog.askstring("Topping","Name:", initialvalue=r["name"]); 
        if not name: return
        price = tk.simpledialog.askfloat("Topping","Price:", initialvalue=float(r["price"])); 
        if price is None: return
        active = messagebox.askyesno("Active","Enable this topping?")
        db.conn.execute("UPDATE toppings SET name=?, price=?, is_active=? WHERE id=?", (name.strip(), price, 1 if active else 0, rid)); db.conn.commit()
        self._top_reload()

    def _top_del(self):
        sel = self.tv_top.selection()
        if not sel: return
        rid = int(self.tv_top.item(sel[0],"values")[0])
        if messagebox.askyesno("Delete","Remove topping?"):
            db.conn.execute("DELETE FROM toppings WHERE id=?", (rid,)); db.conn.commit()
            self._top_reload()

    # Orders tab
    def _order_ui(self):
        fr = ctk.CTkFrame(self.t_order, fg_color="transparent"); fr.pack(fill="both", expand=True, padx=10, pady=10)
        self.tv_o = ttk.Treeview(fr, columns=("id","dt","status","user","subtotal","vat","total","ship"), show="headings", height=14)
        for k,w in [("id",60),("dt",160),("status",110),("user",120),("subtotal",90),("vat",80),("total",90),("ship",100)]:
            self.tv_o.heading(k, text=k.upper()); self.tv_o.column(k,width=w,anchor="w")
        self.tv_o.pack(fill="both", expand=True, padx=8, pady=(8,4))
        bb = ctk.CTkFrame(fr, fg_color="transparent"); bb.pack()
        ctk.CTkButton(bb, text="Confirm", command=lambda:self._set_status("CONFIRMED")).pack(side="left", padx=4)
        ctk.CTkButton(bb, text="Cancel", command=lambda:self._set_status("CANCELLED")).pack(side="left", padx=4)
        ctk.CTkButton(bb, text="Mark Paid + Receipt", command=self._paid_receipt).pack(side="left", padx=4)
        ctk.CTkButton(bb, text="Refresh", command=self._reload_orders).pack(side="left", padx=4)
        self._reload_orders()

    def _reload_orders(self):
        self.tv_o.delete(*self.tv_o.get_children())
        rows = db.conn.execute("""SELECT o.*, u.username user FROM orders o LEFT JOIN users u ON u.id=o.user_id
                                  ORDER BY o.id DESC""").fetchall()
        for r in rows:
            self.tv_o.insert("", "end", values=(r["id"], r["order_datetime"], r["status"], r["user"] or "-", f2(r["subtotal"]), f2(r["vat"]), f2(r["total"]), r["ship_method"] or "-"))

    def _set_status(self, s):
        sel = self.tv_o.selection()
        if not sel: return
        oid = int(self.tv_o.item(sel[0],"values")[0])
        db.conn.execute("UPDATE orders SET status=? WHERE id=?", (s,oid)); db.conn.commit()
        self._reload_orders()

    def _paid_receipt(self):
        sel = self.tv_o.selection()
        if not sel: return
        oid = int(self.tv_o.item(sel[0],"values")[0])
        db.conn.execute("UPDATE orders SET status=?, payment=? WHERE id=?", ("PAID","QR/CASH",oid)); db.conn.commit()
        try:
            path = generate_receipt(oid)
            messagebox.showinfo("Receipt", f"Saved:\n{path}")
        except Exception as e:
            messagebox.showerror("Receipt", str(e))
        self._reload_orders()

# Sub editors
class ProductEditor(ctk.CTkToplevel):
    def __init__(self, master, pid, on_done):
        super().__init__(master); self.pid=pid; self.on_done=on_done
        self.title("Product Editor"); self.geometry("760x420"); self.configure(fg_color=RIGHT_BG)
        frm = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=RADIUS); frm.pack(fill="both", expand=True, padx=12, pady=12)

        cats = db.conn.execute("SELECT * FROM categories ORDER BY main DESC, country").fetchall()
        self.map = {}
        vals=[]
        for r in cats:
            label = f"{r['main']} - {(r['country'] or '-')}"
            self.map[label]=r["id"]; vals.append(label)
        self.v = {k: tk.StringVar() for k in "name ptype price stock image active cat".split()}
        self.v["ptype"].set("FOOD"); self.v["active"].set("1")
        self.v["cat"].set(vals[0] if vals else "")

        grid = ctk.CTkFrame(frm, fg_color="transparent"); grid.pack(fill="x", padx=10, pady=8)
        for i in range(4): grid.grid_columnconfigure(i, weight=1, uniform="g")

        def cell(r,c,txt,key): 
            ctk.CTkLabel(grid,text=txt).grid(row=r, column=c, sticky="w", padx=6, pady=(0,4))
            ctk.CTkEntry(grid, textvariable=self.v[key], corner_radius=RADIUS).grid(row=r+1, column=c, sticky="ew", padx=6)

        cell(0,0,"Name","name"); cell(0,1,"Type (FOOD/DRINK)","ptype")
        cell(0,2,"Price","price"); cell(0,3,"Stock","stock")
        ctk.CTkLabel(grid,text="Category").grid(row=2, column=0, sticky="w", padx=6)
        self.cb = ttk.Combobox(grid, values=vals, textvariable=self.v["cat"], state="readonly"); self.cb.grid(row=3, column=0, sticky="ew", padx=6)
        ctk.CTkLabel(grid,text="Image").grid(row=2, column=1, sticky="w", padx=6)
        ctk.CTkEntry(grid, textvariable=self.v["image"], corner_radius=RADIUS).grid(row=3, column=1, sticky="ew", padx=6)
        ctk.CTkButton(grid,text="Choose...",command=self._pick).grid(row=3, column=2, sticky="w", padx=6)
        cell(2,3,"Active (1/0)","active")

        ctk.CTkButton(frm,text="Save",command=self._save,corner_radius=RADIUS).pack(pady=12)

        if pid:
            r=db.conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
            self.v["name"].set(r["name"]); self.v["ptype"].set(r["ptype"]); self.v["price"].set(str(r["price"]))
            self.v["stock"].set(str(r["stock"])); self.v["image"].set(r["image"] or ""); self.v["active"].set(str(r["is_active"]))
            rc = db.conn.execute("SELECT main,country FROM categories WHERE id=?", (r["category_id"],)).fetchone()
            label = f"{rc['main']} - {(rc['country'] or '-')}" if rc else vals[0]
            if label in self.map: self.v["cat"].set(label)

    def _pick(self):
        f = filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg")])
        if not f: return
        dest = os.path.join(IMG_PROD, os.path.basename(f))
        try:
            import shutil; shutil.copy2(f, dest)
            self.v["image"].set(dest)
        except Exception as e:
            messagebox.showerror("Image", str(e))

    def _save(self):
        try:
            name = self.v["name"].get().strip(); ptype=self.v["ptype"].get().strip().upper()
            price=float(self.v["price"].get().strip() or 0); stock=int(self.v["stock"].get().strip() or 0)
            image=self.v["image"].get().strip(); active=0 if (self.v["active"].get().strip() or "1")=="0" else 1
            cat_id = self.map.get(self.v["cat"].get().strip())
            if not name or ptype not in ("FOOD","DRINK") or not cat_id:
                messagebox.showerror("Save","Invalid inputs"); return
            cur=db.conn.cursor()
            if self.pid:
                cur.execute("""UPDATE products SET name=?,ptype=?,category_id=?,price=?,stock=?,image=?,is_active=? WHERE id=?""",
                            (name,ptype,cat_id,price,stock,image,active,self.pid))
            else:
                cur.execute("""INSERT INTO products(name,ptype,category_id,price,stock,image,is_active) VALUES(?,?,?,?,?,?,?)""",
                            (name,ptype,cat_id,price,stock,image,active))
            db.conn.commit(); self.on_done(); self.destroy()
        except Exception as e:
            messagebox.showerror("Save", str(e))

class OptionEditor(ctk.CTkToplevel):
    def __init__(self, master, pid):
        super().__init__(master); self.pid=pid; self.title("Options"); self.geometry("640x520"); self.configure(fg_color=RIGHT_BG)
        frm = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=RADIUS); frm.pack(fill="both", expand=True, padx=10, pady=10)
        p=db.conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
        ctk.CTkLabel(frm, text=f"{p['name']} ({p['ptype']})", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=12, pady=(8,6))
        self.ptype=p["ptype"]
        # current
        def get(nm, dflt): 
            r=db.conn.execute("SELECT option_json FROM product_options WHERE product_id=? AND option_name=?", (pid,nm)).fetchone()
            return json.loads(r["option_json"]) if r and r["option_json"] else dflt
        self.meat  = tk.StringVar(value=",".join(get("Meat", {"values":["Pork","Chicken","Beef","Seafood"]})["values"]))
        self.spice = tk.StringVar(value=",".join(get("Spice", {"values":["Mild","Medium","Hot","Extra Hot"]})["values"]))
        size_cfg = get("Size", {"values":["S","M","L"], "mul":{"S":1.0,"M":1.2,"L":1.5}})
        self.sizes = tk.StringVar(value=",".join(size_cfg["values"]))
        self.mults = tk.StringVar(value=json.dumps(size_cfg["mul"]))
        self.ice   = tk.StringVar(value=",".join(get("Ice", {"values":["0%","25%","50%","75%","100%"]})["values"]))
        self.sweet = tk.StringVar(value=",".join(get("Sweetness", {"values":["0%","25%","50%","75%","100%"]})["values"]))

        grid = ctk.CTkFrame(frm, fg_color="transparent"); grid.pack(fill="x", padx=12, pady=8)
        for i in range(2): grid.grid_columnconfigure(i, weight=1, uniform="g")
        def row(r,c,lbl,var,hint=""):
            ctk.CTkLabel(grid,text=lbl).grid(row=r, column=c, sticky="w", padx=6)
            ctk.CTkEntry(grid,textvariable=var,corner_radius=RADIUS).grid(row=r+1,column=c,sticky="ew",padx=6,pady=(0,6))
            if hint: ctk.CTkLabel(grid,text=hint,text_color="#6b7280").grid(row=r+2,column=c,sticky="w",padx=6)
        if self.ptype=="FOOD":
            row(0,0,"Meat (comma)", self.meat)
            row(0,1,"Spice (comma)", self.spice)
        else:
            row(0,0,"Size values (comma)", self.sizes, "e.g. S,M,L")
            row(0,1,"Size multipliers (JSON)", self.mults, 'e.g. {"S":1.0,"M":1.2,"L":1.5}')
            row(3,0,"Ice (comma)", self.ice); row(3,1,"Sweetness (comma)", self.sweet)
        ctk.CTkButton(frm,text="Save Options", command=self._save, corner_radius=RADIUS).pack(pady=10)

    def _save(self):
        if self.ptype=="FOOD":
            meats=[s.strip() for s in self.meat.get().split(",") if s.strip()]
            spices=[s.strip() for s in self.spice.get().split(",") if s.strip()]
            db.conn.execute("REPLACE INTO product_options(product_id,option_name,option_json) VALUES(?,?,?)",(self.pid,"Meat",json.dumps({"values":meats})))
            db.conn.execute("REPLACE INTO product_options(product_id,option_name,option_json) VALUES(?,?,?)",(self.pid,"Spice",json.dumps({"values":spices})))
        else:
            sizes=[s.strip() for s in self.sizes.get().split(",") if s.strip()]
            mul=json.loads(self.mults.get().strip() or "{}")
            ice=[s.strip() for s in self.ice.get().split(",") if s.strip()]
            sweet=[s.strip() for s in self.sweet.get().split(",") if s.strip()]
            db.conn.execute("REPLACE INTO product_options(product_id,option_name,option_json) VALUES(?,?,?)",(self.pid,"Size",json.dumps({"values":sizes,"mul":mul})))
            db.conn.execute("REPLACE INTO product_options(product_id,option_name,option_json) VALUES(?,?,?)",(self.pid,"Ice",json.dumps({"values":ice})))
            db.conn.execute("REPLACE INTO product_options(product_id,option_name,option_json) VALUES(?,?,?)",(self.pid,"Sweetness",json.dumps({"values":sweet})))
        db.conn.commit(); messagebox.showinfo("Options","Saved"); self.destroy()

# ------------------ CUSTOMER UI ------------------
class CustomerApp(ctk.CTkToplevel):
    def __init__(self, root, user_row):
        super().__init__(root); self.root=root; self.user=dict(user_row)
        self.title(f"{APP_TITLE} — STORE")
        try: self.state("zoomed")
        except: self.geometry("1200x720")
        self.configure(fg_color=RIGHT_BG)
        self.protocol("WM_DELETE_WINDOW", self._logout)

        # top bar with profile
        top = ctk.CTkFrame(self, fg_color="transparent"); top.pack(fill="x", padx=12, pady=12)
        self._avatar_label = ctk.CTkLabel(top, text="")
        self._avatar_label.pack(side="left"); self._refresh_avatar()
        ctk.CTkLabel(top, text=self.user.get("username",""), font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=8)
        ctk.CTkButton(top, text="Edit Profile", command=self._edit_profile).pack(side="left", padx=6)
        ctk.CTkButton(top, text="Logout", command=self._logout).pack(side="right")

        # 3 big circular buttons center
        center = ctk.CTkFrame(self, fg_color="transparent"); center.pack(expand=True)
        def bigbtn(text, cmd):
            b = ctk.CTkButton(center, text=text, width=180, height=180, corner_radius=90,
                              font=ctk.CTkFont(size=18, weight="bold"), command=cmd)
            b.pack(side="left", padx=30, pady=20)
        bigbtn("FOOD", self._open_food)
        bigbtn("DRINK", self._open_drink)
        bigbtn("CART", self._open_cart)

    def _logout(self):
        try: self.destroy()
        finally:
            self.root.deiconify()

    def _refresh_avatar(self):
        path = self.user.get("avatar") or ""
        if path and os.path.exists(path):
            img = Image.open(path).resize((40,40))
            self._ava = ctk.CTkImage(light_image=img, dark_image=img, size=(40,40))
            self._avatar_label.configure(image=self._ava)
        else:
            self._avatar_label.configure(text="🙂", image=None)

    def _edit_profile(self):
        EditProfile(self, self.user, self._after_profile)

    def _after_profile(self, new_user):
        self.user.update(new_user)
        self._refresh_avatar()

    def _open_food(self):  MenuBrowser(self, "FOOD", self.user)
    def _open_drink(self): MenuBrowser(self, "DRINK", self.user)
    def _open_cart(self):  CartWindow(self, self.user)

# profile editor
class EditProfile(ctk.CTkToplevel):
    def __init__(self, master, user, on_done):
        super().__init__(master); self.user=user; self.on_done=on_done
        self.title("Edit Profile"); self.geometry("520x420"); self.configure(fg_color=RIGHT_BG)
        frm = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=RADIUS); frm.pack(fill="both", expand=True, padx=12, pady=12)
        self.v = {k: tk.StringVar(value=user.get(k,"") or "") for k in ("name","email","phone","address")}
        self.v["avatar"] = tk.StringVar(value=user.get("avatar","") or "")
        def row(lbl,key):
            ctk.CTkLabel(frm,text=lbl).pack(anchor="w", padx=12)
            ctk.CTkEntry(frm,textvariable=self.v[key],corner_radius=RADIUS).pack(fill="x", padx=12, pady=(0,8))
        row("Name","name"); row("Email","email"); row("Phone","phone")
        ctk.CTkLabel(frm,text="Address").pack(anchor="w", padx=12)
        self.addr = tk.Text(frm, height=4); self.addr.pack(fill="x", padx=12, pady=(0,8)); self.addr.insert("1.0", self.v["address"].get())
        ctk.CTkLabel(frm,text="Avatar").pack(anchor="w", padx=12)
        line = ctk.CTkFrame(frm, fg_color="transparent"); line.pack(fill="x", padx=12)
        ctk.CTkEntry(line,textvariable=self.v["avatar"],corner_radius=RADIUS).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(line,text="Choose...", command=self._pick).pack(side="left", padx=6)
        ctk.CTkButton(frm,text="Save", command=self._save).pack(pady=10)

    def _pick(self):
        f = filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg")])
        if f: self.v["avatar"].set(f)

    def _save(self):
        self.v["address"].set(self.addr.get("1.0","end").strip())
        db.conn.execute("""UPDATE users SET name=?, email=?, phone=?, avatar=?, address=? WHERE username=?""",
                        (self.v["name"].get().strip(), self.v["email"].get().strip(), self.v["phone"].get().strip(),
                         self.v["avatar"].get().strip(), self.v["address"].get().strip(), self.user["username"]))
        db.conn.commit()
        new_user = dict(db.conn.execute("SELECT * FROM users WHERE username=?", (self.user["username"],)).fetchone())
        self.on_done(new_user); self.destroy()

# Menu browser + add-to-cart
class MenuBrowser(ctk.CTkToplevel):
    def __init__(self, master, ptype, user):
        super().__init__(master); self.ptype=ptype; self.user=user
        self.title(f"{ptype} Menu"); self.geometry("1200x720"); self.configure(fg_color=RIGHT_BG)

        body = ctk.CTkFrame(self, fg_color="transparent"); body.pack(fill="both", expand=True, padx=12, pady=12)
        left = ctk.CTkFrame(body, fg_color=CARD_BG, corner_radius=RADIUS); left.pack(side="left", fill="y", padx=6,pady=6)
        mid  = ctk.CTkFrame(body, fg_color=CARD_BG, corner_radius=RADIUS); mid.pack(side="left", fill="both", expand=True, padx=6,pady=6)
        right= ctk.CTkFrame(body, fg_color=CARD_BG, corner_radius=RADIUS); right.pack(side="left", fill="both", padx=6,pady=6)

        # categories
        ctk.CTkLabel(left, text=("COUNTRY" if ptype=="FOOD" else "DRINK"), font=ctk.CTkFont(size=14, weight="bold")).pack(padx=12, pady=(12,4), anchor="w")
        self.lb = tk.Listbox(left, height=18); self.lb.pack(fill="both", expand=True, padx=12, pady=(0,12))
        if ptype=="FOOD":
            self.cats=db.conn.execute("SELECT * FROM categories WHERE main='FOOD' ORDER BY country").fetchall()
            for r in self.cats: self.lb.insert("end", r["country"])
        else:
            self.cats=db.conn.execute("SELECT * FROM categories WHERE main='DRINK'").fetchall()
            self.lb.insert("end","DRINK")
        self.lb.selection_set(0)

        # products
        ctk.CTkLabel(mid, text="PRODUCTS", font=ctk.CTkFont(size=14, weight="bold")).pack(padx=12,pady=(12,4),anchor="w")
        self.tv = ttk.Treeview(mid, columns=("name","price","stock"), show="headings", height=12)
        for k,w in [("name",280),("price",90),("stock",70)]:
            self.tv.heading(k, text=k.upper()); self.tv.column(k,width=w,anchor="w")
        self.tv.pack(fill="both", expand=True, padx=12, pady=(0,8))
        self.tv.bind("<<TreeviewSelect>>", lambda e: self._show_options())

        # options
        opt = ctk.CTkFrame(mid, fg_color="#f1e3ca", corner_radius=RADIUS); opt.pack(fill="x", padx=12, pady=(0,10))
        self.var_qty = tk.IntVar(value=1)
        ctk.CTkLabel(opt, text="QTY").grid(row=0, column=0, sticky="e", padx=8, pady=6)
        ctk.CTkEntry(opt, textvariable=self.var_qty, width=60, corner_radius=RADIUS).grid(row=0, column=1, sticky="w", padx=4)

        self.cmb = {k: ttk.Combobox(opt, state="readonly") for k in ["Meat","Spice","Size","Ice","Sweetness"]}
        self.lbk = {k: ctk.CTkLabel(opt, text=k) for k in self.cmb}
        positions = [("Meat",1,0),("Spice",1,2),("Size",2,0),("Ice",2,2),("Sweetness",3,0)]
        for k,r,c in positions:
            self.lbk[k].grid(row=r, column=c, sticky="e", padx=8, pady=4); self.cmb[k].grid(row=r, column=c+1, sticky="ew", padx=4, pady=4)
        for i in range(4): opt.grid_columnconfigure(i, weight=1)

        # toppings
        self.top_vars=[]
        self.top_box = ctk.CTkFrame(mid, fg_color="transparent"); self.top_box.pack(fill="x", padx=12)
        ctk.CTkLabel(self.top_box,text="TOPPINGS").pack(anchor="w")
        self._render_toppings()

        # note
        ctk.CTkLabel(mid, text="NOTE").pack(anchor="w", padx=12)
        self.note = ctk.CTkEntry(mid, placeholder_text="(optional)", corner_radius=RADIUS); self.note.pack(fill="x", padx=12, pady=(0,8))

        ctk.CTkButton(mid, text="ADD TO CART", command=self._add, corner_radius=RADIUS).pack(padx=12, pady=(0,10), anchor="e")

        # cart preview
        ctk.CTkLabel(right, text="CART", font=ctk.CTkFont(size=14, weight="bold")).pack(padx=12, pady=(12,4), anchor="w")
        self.cart_tv = ttk.Treeview(right, columns=("name","qty","price","opt"), show="headings", height=16)
        for k,w in [("name",240),("qty",60),("price",100),("opt",220)]:
            self.cart_tv.heading(k, text=k.upper()); self.cart_tv.column(k,width=w,anchor="w")
        self.cart_tv.pack(fill="both", expand=True, padx=12, pady=(0,8))
        ctk.CTkButton(right, text="OPEN CART", command=lambda: CartWindow(self, self.user)).pack(padx=12, pady=8)

        self._reload_products()

    def _render_toppings(self):
        for w in self.top_box.winfo_children():
            if isinstance(w, ctk.CTkCheckBox): w.destroy()
        self.top_vars=[]
        for r in db.conn.execute("SELECT * FROM toppings WHERE is_active=1 ORDER BY id").fetchall():
            v = tk.IntVar(value=0)
            ctk.CTkCheckBox(self.top_box, text=f"{r['name']} (+{f2(r['price'])})", variable=v).pack(anchor="w")
            self.top_vars.append((r,v))

    def _current_category_id(self):
        sel = self.lb.curselection()
        if not sel: return None
        return self.cats[sel[0]]["id"]

    def _reload_products(self):
        self.tv.delete(*self.tv.get_children())
        if self.ptype=="FOOD":
            cid = self._current_category_id()
            rows = db.conn.execute("""SELECT * FROM products WHERE ptype='FOOD' AND is_active=1 AND category_id=? ORDER BY name""",(cid,)).fetchall()
        else:
            rows = db.conn.execute("""SELECT * FROM products WHERE ptype='DRINK' AND is_active=1 ORDER BY name""").fetchall()
        self.rows=rows
        for p in rows: self.tv.insert("", "end", values=(p["name"], f2(p["price"]), p["stock"]), iid=str(p["id"]))
        for k in self.cmb: self.cmb[k]["values"]=(); self.cmb[k].set("")

    def _show_options(self):
        sel = self.tv.selection()
        if not sel: return
        pid = int(sel[0])
        p = next((x for x in self.rows if x["id"]==pid), None)
        if not p: return
        # load per product options
        opts={}
        for r in db.conn.execute("SELECT option_name, option_json FROM product_options WHERE product_id=?", (pid,)).fetchall():
            opts[r["option_name"]]=json.loads(r["option_json"] or "{}")
        if p["ptype"]=="FOOD":
            for k in ["Size","Ice","Sweetness"]: self.lbk[k].grid_remove(); self.cmb[k].grid_remove()
            for k in ["Meat","Spice"]: 
                self.lbk[k].grid(); self.cmb[k].grid()
            self.cmb["Meat"]["values"]=opts.get("Meat",{}).get("values",[])
            self.cmb["Spice"]["values"]=opts.get("Spice",{}).get("values",[])
            if self.cmb["Meat"]["values"]: self.cmb["Meat"].current(0)
            if self.cmb["Spice"]["values"]: self.cmb["Spice"].current(0)
        else:
            for k in ["Meat","Spice"]: self.lbk[k].grid_remove(); self.cmb[k].grid_remove()
            for k in ["Size","Ice","Sweetness"]: self.lbk[k].grid(); self.cmb[k].grid()
            self._mul = opts.get("Size",{}).get("mul",{"S":1.0,"M":1.2,"L":1.5})
            self.cmb["Size"]["values"]=opts.get("Size",{}).get("values",[])
            self.cmb["Ice"]["values"]=opts.get("Ice",{}).get("values",[])
            self.cmb["Sweetness"]["values"]=opts.get("Sweetness",{}).get("values",[])
            if self.cmb["Size"]["values"]: self.cmb["Size"].current(0)
            if self.cmb["Ice"]["values"]: self.cmb["Ice"].current(2 if "50%" in self.cmb["Ice"]["values"] else 0)
            if self.cmb["Sweetness"]["values"]: self.cmb["Sweetness"].current(2 if "50%" in self.cmb["Sweetness"]["values"] else 0)

    def _add(self):
        sel = self.tv.selection()
        if not sel: return
        pid = int(sel[0])
        p = next((x for x in self.rows if x["id"]==pid), None)
        if not p: return
        qty = max(1, int(self.var_qty.get() or 1))
        if qty > p["stock"]:
            messagebox.showwarning("Stock", f"Stock not enough (available {p['stock']})"); return
        # compute price with options/toppings
        unit = float(p["price"])
        opts={}
        if p["ptype"]=="FOOD":
            if self.cmb["Meat"].get(): opts["Meat"]=self.cmb["Meat"].get()
            if self.cmb["Spice"].get(): opts["Spice"]=self.cmb["Spice"].get()
        else:
            sz = self.cmb["Size"].get() or "M"; opts["Size"]=sz
            unit *= float(self._mul.get(sz, 1.2))
            if self.cmb["Ice"].get(): opts["Ice"]=self.cmb["Ice"].get()
            if self.cmb["Sweetness"].get(): opts["Sweetness"]=self.cmb["Sweetness"].get()
        tops=[]; add=0.0
        for r,v in self.top_vars:
            if v.get()==1:
                tops.append({"name":r["name"],"price":float(r["price"])})
                add += float(r["price"])
        # add to temp cart table in memory (use orders temp? here: just create immediate row in 'cart' table? Keep in session)
        # Simplify: save to a session list on master
        CART.append({"pid":pid,"name":p["name"],"qty":qty,"unit":round(unit,2),
                     "add":round(add,2), "options":opts, "toppings":tops, "note":self.note.get().strip()})
        self._render_cart_preview()
        messagebox.showinfo("Cart","Added to cart")

    def _render_cart_preview(self):
        self.cart_tv.delete(*self.cart_tv.get_children())
        for i,it in enumerate(CART,1):
            price = (it["unit"] + it["add"]) * it["qty"]
            opt_s = ", ".join(list(it["options"].values()))
            self.cart_tv.insert("", "end", values=(it["name"], it["qty"], f2(price), opt_s))

# cart window and checkout
CART: List[Dict[str,Any]] = []

class CartWindow(ctk.CTkToplevel):
    def __init__(self, master, user):
        super().__init__(master); self.user=user
        self.title("My Cart"); self.geometry("900x640"); self.configure(fg_color=RIGHT_BG)
        self.tv = ttk.Treeview(self, columns=("name","qty","price","opts"), show="headings", height=16)
        for k,w in [("name",260),("qty",60),("price",120),("opts",280)]:
            self.tv.heading(k, text=k.upper()); self.tv.column(k,width=w,anchor="w")
        self.tv.pack(fill="both", expand=True, padx=10, pady=10)
        bb=ctk.CTkFrame(self, fg_color="transparent"); bb.pack(fill="x", padx=10, pady=(0,10))
        ctk.CTkButton(bb,text="Remove Selected", command=self._rm).pack(side="left", padx=4)
        ctk.CTkButton(bb,text="Checkout", command=self._checkout).pack(side="right", padx=4)
        self._render()

    def _render(self):
        self.tv.delete(*self.tv.get_children())
        for i,it in enumerate(CART,1):
            self.tv.insert("", "end", iid=str(i), values=(it["name"], it["qty"], f2((it["unit"]+it["add"])*it["qty"]),
                                                          ", ".join(list(it["options"].values()))))

    def _rm(self):
        sel = self.tv.selection()
        if not sel: return
        idx = int(sel[0])-1
        if 0<=idx<len(CART):
            del CART[idx]; self._render()

    def _checkout(self):
        if not CART: messagebox.showwarning("Cart","Cart empty"); return
        Checkout(self, self.user, self._after_checkout)

    def _after_checkout(self, order_id):
        CART.clear(); self._render()
        messagebox.showinfo("Order", f"Created order #{order_id}\n(Waiting CONFIRM/PAYMENT)")

class Checkout(ctk.CTkToplevel):
    def __init__(self, master, user, on_done):
        super().__init__(master); self.user=user; self.on_done=on_done
        self.title("Checkout"); self.geometry("700x520"); self.configure(fg_color=RIGHT_BG)
        frm = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=RADIUS); frm.pack(fill="both", expand=True, padx=12, pady=12)
        self.ship = tk.StringVar(value="PICKUP")  # DELIVERY or PICKUP
        line = ctk.CTkFrame(frm, fg_color="transparent"); line.pack(fill="x", padx=12, pady=8)
        for k in ("PICKUP","DELIVERY"):
            ctk.CTkRadioButton(line, text=k, variable=self.ship, value=k).pack(side="left", padx=8)

        self.v = {k: tk.StringVar() for k in ("name","phone","address")}
        self.v["name"].set(self.user.get("name") or self.user.get("username"))
        self.v["phone"].set(self.user.get("phone") or "")
        self.v["address"].set(self.user.get("address") or "")

        def row(lbl,key):
            ctk.CTkLabel(frm, text=lbl).pack(anchor="w", padx=12)
            ctk.CTkEntry(frm, textvariable=self.v[key], corner_radius=RADIUS).pack(fill="x", padx=12, pady=(0,8))
        row("Receiver Name","name"); row("Receiver Phone","phone")
        ctk.CTkLabel(frm, text="Address").pack(anchor="w", padx=12)
        self.addr = ctk.CTkEntry(frm, textvariable=self.v["address"], corner_radius=RADIUS)
        self.addr.pack(fill="x", padx=12, pady=(0,8))

        self.pay = tk.StringVar(value="QR")
        line2 = ctk.CTkFrame(frm, fg_color="transparent"); line2.pack(fill="x", padx=12, pady=8)
        ctk.CTkLabel(line2, text="Payment").pack(side="left", padx=(0,8))
        ctk.CTkRadioButton(line2, text="QR", variable=self.pay, value="QR").pack(side="left")
        ctk.CTkRadioButton(line2, text="CASH (Pickup)", variable=self.pay, value="CASH").pack(side="left")

        ctk.CTkButton(frm, text="Place Order", command=self._place).pack(pady=12)

        # QR preview
        if os.path.exists(QR_PATH):
            try:
                img = Image.open(QR_PATH); self._qr=ctk.CTkImage(light_image=img,dark_image=img,size=(160,160))
                ctk.CTkLabel(frm,image=self._qr,text="").pack()
            except: pass

    def _place(self):
        # compute bill
        subtotal = sum((it["unit"]+it["add"]) * it["qty"] for it in CART)
        vat = round(subtotal * 0.07, 2)
        total = round(subtotal + vat, 2)

        # save order & items; also decrease stock
        cur = db.conn.cursor()
        cur.execute("""INSERT INTO orders(user_id, order_datetime, status, ship_method, ship_name, ship_phone, ship_address,
                                          subtotal, discount, vat, total, payment, note)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (self.user["id"], now(), "PENDING", self.ship.get(),
                     self.v["name"].get().strip(), self.v["phone"].get().strip(), self.v["address"].get().strip(),
                     round(subtotal,2), 0.0, vat, total, self.pay.get(), None))
        oid = cur.lastrowid

        for it in CART:
            cur.execute("""INSERT INTO order_items(order_id,product_id,name,qty,unit_price,options_json,toppings_json,add_price)
                           VALUES(?,?,?,?,?,?,?,?)""",
                        (oid, it["pid"], it["name"], it["qty"], it["unit"],
                         json.dumps(it["options"], ensure_ascii=False),
                         json.dumps(it["toppings"], ensure_ascii=False),
                         round(it["add"],2)))
            # stock decrease
            db.conn.execute("UPDATE products SET stock=stock-? WHERE id=?", (it["qty"], it["pid"]))
        db.conn.commit()

        # if pickup & cash paid now → mark paid and output receipt
        if self.ship.get()=="PICKUP" and self.pay.get()=="CASH":
            db.conn.execute("UPDATE orders SET status='PAID' WHERE id=?", (oid,)); db.conn.commit()
            try:
                path = generate_receipt(oid)
                messagebox.showinfo("Receipt", f"Saved:\n{path}")
            except Exception as e:
                messagebox.showerror("Receipt", str(e))

        self.on_done(oid); self.destroy()

# ------------------ BOOT ------------------
if __name__ == "__main__":
    app = AuthApp()
    app.mainloop()
