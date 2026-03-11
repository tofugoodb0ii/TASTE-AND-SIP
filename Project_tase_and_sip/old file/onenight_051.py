# -*- coding: utf-8 -*-
"""
Combined Auth (customtkinter) + Admin System (customtkinter)
- Single file: Login -> if role=='admin' => open AdminApp, else (TODO) open POS/front
- Left login side: Canvas draws full-bleed image + pure white text (no background)
- DB: one sqlite file "taste_and_sip.db"
- Seeds: admin/admin123 (role='admin') if not exists

Run: python taste_and_sip_app.py
"""

# ========= COMMON IMPORTS =========
import os, re, sqlite3, hashlib, json
from datetime import datetime as dt, timedelta
from typing import Optional, Callable, Dict, Any, List

from PIL import Image, ImageTk
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk

import customtkinter as ctk

APP_TITLE = "TASTE AND SIP"

# ===== Theme / Palette =====
RIGHT_BG   = "#f8eedb"   # page background
CARD_BG    = "#edd8b8"   # deeper cream for card
TEXT_DARK  = "#1f2937"
LINK_FG    = "#0057b7"
BORDER     = "#d3c6b4"
CARD_W     = 660
CARD_H     = 560
RADIUS     = 18

DB_FILE = "taste_and_sip.db"
ASSETS_DIR = "assets"
IMG_DIR    = os.path.join(ASSETS_DIR, "images")
IMG_PRODUCTS_DIR = os.path.join(IMG_DIR, "products")
REPORTS_DIR = "reports"
os.makedirs(IMG_PRODUCTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# ===== Helpers =====
def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def now_ts() -> str:
    return dt.now().strftime("%Y-%m-%d %H:%M:%S")

def safe_float(x, d=0.0):
    try:
        return float(x)
    except:
        return d

def try_import_reportlab():
    try:
        from reportlab.pdfgen import canvas as pdfcanvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        return pdfcanvas, A4, mm
    except Exception:
        return None, None, None


# ======================================================================
# ============================  AUTH LAYER  =============================
# ======================================================================

# Regex rules
USERNAME_RE = re.compile(r"^[A-Za-z0-9]{6,}$")
PHONE_RE    = re.compile(r"^\d{10}$")
EMAIL_RE    = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PWD_RE      = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,}$")

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


class AuthDB:
    """Auth DB: focuses on users table (shared with admin DB). Seeds admin if missing."""
    def __init__(self, path: str = DB_FILE):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._ensure_schema()
        self._seed_admin()

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

    def _seed_admin(self):
        if not self.conn.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
            self.conn.execute(
                "INSERT INTO users(username,password_hash,name,role) VALUES(?,?,?,?)",
                ("admin", sha256("admin123"), "Administrator", "admin")
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


# ---------- UI widgets (Auth) ----------
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


# ---------- AuthApp ----------
class AuthApp(ctk.CTk):
    def __init__(self, db_path: str = DB_FILE, left_bg_path: Optional[str] = None,
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

        # Left: Canvas draws full image + white texts (no background)
        self.left = ctk.CTkFrame(self, fg_color=RIGHT_BG, corner_radius=0)
        self.left.grid(row=0, column=0, sticky="nsew")
        self.left_canvas = tk.Canvas(self.left, highlightthickness=0, bd=0, bg=RIGHT_BG)
        self.left_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self._left_img_tk = None
        self.left.bind("<Configure>", lambda e: self._draw_left_bg())

        # Right: logo + rounded card
        self.right = ctk.CTkFrame(self, fg_color=RIGHT_BG, corner_radius=0)
        self.right.grid(row=0, column=1, sticky="nsew")
        self.right.grid_rowconfigure(1, weight=1)
        self.right.grid_columnconfigure(0, weight=1)

        self.logo_wrap = ctk.CTkFrame(self.right, fg_color=RIGHT_BG, corner_radius=0)
        self.logo_wrap.grid(row=0, column=0, pady=(30, 10))
        self._render_logo()

        self.card = ctk.CTkFrame(
            self.right, fg_color=CARD_BG, corner_radius=RADIUS, border_color=BORDER, border_width=1,
            width=CARD_W, height=CARD_H
        )
        self.card.grid(row=1, column=0, sticky="n", padx=80, pady=(10, 40))
        self.card.grid_propagate(False)
        self.card.grid_columnconfigure(0, weight=1)

        self.show_signin()

    # left painting
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

        # pure white overlay text (no background)
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

    # actions
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
        if not getattr(self, "_verified_username", None):
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


# ======================================================================
# ===========================  ADMIN LAYER  =============================
# ======================================================================

class AdminDB:
    """Admin DB for categories/products/options/promotions/orders + also shares users."""
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
            name TEXT, phone TEXT, email TEXT, role TEXT DEFAULT 'customer'
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS categories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            country TEXT NOT NULL
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER,
            ptype TEXT NOT NULL,
            base_price REAL NOT NULL,
            image TEXT,
            is_active INTEGER DEFAULT 1
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS product_options(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            option_name TEXT NOT NULL,
            option_values_json TEXT
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS promotions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            value REAL NOT NULL,
            min_spend REAL DEFAULT 0,
            start_at TEXT, end_at TEXT,
            applies_to_product_id INTEGER,
            is_active INTEGER DEFAULT 1
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            order_datetime TEXT,
            status TEXT,
            subtotal REAL, discount REAL, vat REAL, total REAL,
            note TEXT
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS order_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            name TEXT,
            qty INTEGER,
            unit_price REAL,
            options_json TEXT,
            add_price REAL DEFAULT 0
        )""")
        self.conn.commit()

    def _seed(self):
        c = self.conn.cursor()
        # seed admin if missing (safety; AuthDB seeds too)
        if not c.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
            c.execute("INSERT INTO users(username,password_hash,name,role) VALUES(?,?,?,?)",
                      ("admin", sha256("admin123"), "Administrator", "admin"))
        # categories
        if c.execute("SELECT COUNT(*) n FROM categories").fetchone()['n'] == 0:
            c.executemany("INSERT INTO categories(name,country) VALUES(?,?)", [
                ("Pad Thai", "Thailand"),
                ("Sushi Set", "Japan"),
                ("Kimchi Stew", "Korea"),
                ("Burger", "USA"),
                ("Thai Milk Tea", "Thailand"),
                ("Matcha Latte", "Japan"),
            ])
        # products
        if c.execute("SELECT COUNT(*) n FROM products").fetchone()['n'] == 0:
            cats = {r['name']: r['id'] for r in c.execute("SELECT id,name FROM categories")}
            demo = [
                ("Pad Thai", cats.get("Pad Thai"), "FOOD", 60.0, "", 1),
                ("Kimchi Stew", cats.get("Kimchi Stew"), "FOOD", 80.0, "", 1),
                ("Thai Milk Tea", cats.get("Thai Milk Tea"), "DRINK", 35.0, "", 1),
                ("Matcha Latte", cats.get("Matcha Latte"), "DRINK", 55.0, "", 1),
            ]
            c.executemany("INSERT INTO products(name,category_id,ptype,base_price,image,is_active) VALUES(?,?,?,?,?,?)", demo)
        # options defaults
        for p in self.conn.execute("SELECT * FROM products").fetchall():
            pid, ptype = p['id'], p['ptype']
            if ptype == "FOOD":
                if not self.conn.execute("SELECT 1 FROM product_options WHERE product_id=? AND option_name='Meat'", (pid,)).fetchone():
                    self.conn.execute("INSERT INTO product_options(product_id,option_name,option_values_json) VALUES(?,?,?)",
                                      (pid, "Meat", json.dumps({"values":["Pork","Chicken","Beef","Seafood"]})))
                if not self.conn.execute("SELECT 1 FROM product_options WHERE product_id=? AND option_name='Spice'", (pid,)).fetchone():
                    self.conn.execute("INSERT INTO product_options(product_id,option_name,option_values_json) VALUES(?,?,?)",
                                      (pid, "Spice", json.dumps({"values":["Mild","Medium","Hot","Extra Hot"]})))
            else:
                if not self.conn.execute("SELECT 1 FROM product_options WHERE product_id=? AND option_name='Size'", (pid,)).fetchone():
                    self.conn.execute("INSERT INTO product_options(product_id,option_name,option_values_json) VALUES(?,?,?)",
                                      (pid, "Size", json.dumps({"values":["S","M","L"],"price_multipliers":{"S":1.0,"M":1.2,"L":1.5}})))
                if not self.conn.execute("SELECT 1 FROM product_options WHERE product_id=? AND option_name='Ice'", (pid,)).fetchone():
                    self.conn.execute("INSERT INTO product_options(product_id,option_name,option_values_json) VALUES(?,?,?)",
                                      (pid, "Ice", json.dumps({"values":["0%","25%","50%","75%","100%"]})))
                if not self.conn.execute("SELECT 1 FROM product_options WHERE product_id=? AND option_name='Sweetness'", (pid,)).fetchone():
                    self.conn.execute("INSERT INTO product_options(product_id,option_name,option_values_json) VALUES(?,?,?)",
                                      (pid, "Sweetness", json.dumps({"values":["0%","25%","50%","75%","100%"]})))
        self.conn.commit()

    # categories
    def list_categories(self):
        return self.conn.execute("SELECT * FROM categories ORDER BY country, name").fetchall()

    def add_category(self, name, country):
        self.conn.execute("INSERT INTO categories(name,country) VALUES(?,?)", (name, country)); self.conn.commit()

    def delete_category(self, cid):
        self.conn.execute("DELETE FROM categories WHERE id=?", (cid,)); self.conn.commit()

    # products
    def list_products(self):
        return self.conn.execute("""
            SELECT p.*, c.name AS category_name, c.country AS country
            FROM products p LEFT JOIN categories c ON c.id=p.category_id
            ORDER BY p.id DESC
        """).fetchall()

    def upsert_product(self, pid, name, cat_id, ptype, base_price, image, is_active):
        cur = self.conn.cursor()
        if pid:
            cur.execute("""UPDATE products SET name=?,category_id=?,ptype=?,base_price=?,image=?,is_active=? WHERE id=?""",
                        (name, cat_id, ptype, base_price, image, is_active, pid))
        else:
            cur.execute("""INSERT INTO products(name,category_id,ptype,base_price,image,is_active) VALUES(?,?,?,?,?,?)""",
                        (name, cat_id, ptype, base_price, image, is_active))
        self.conn.commit()

    def delete_product(self, pid):
        self.conn.execute("DELETE FROM products WHERE id=?", (pid,)); self.conn.commit()

    def get_options(self, pid) -> Dict[str, Any]:
        out = {}
        for r in self.conn.execute("SELECT * FROM product_options WHERE product_id=?", (pid,)).fetchall():
            try:
                out[r['option_name']] = json.loads(r['option_values_json'] or "{}")
            except Exception:
                out[r['option_name']] = {}
        return out

    def set_option(self, pid, opt_name, values_json_obj):
        data = json.dumps(values_json_obj)
        if self.conn.execute("SELECT 1 FROM product_options WHERE product_id=? AND option_name=?", (pid, opt_name)).fetchone():
            self.conn.execute("UPDATE product_options SET option_values_json=? WHERE product_id=? AND option_name=?", (data, pid, opt_name))
        else:
            self.conn.execute("INSERT INTO product_options(product_id,option_name,option_values_json) VALUES(?,?,?)", (pid, opt_name, data))
        self.conn.commit()

    # promotions
    def list_promos(self):
        return self.conn.execute("SELECT * FROM promotions ORDER BY id DESC").fetchall()

    def upsert_promo(self, pid, code, ptype, value, min_spend, start_at, end_at, applies_to_product_id, is_active):
        cur = self.conn.cursor()
        if pid:
            cur.execute("""UPDATE promotions SET code=?,type=?,value=?,min_spend=?,start_at=?,end_at=?,applies_to_product_id=?,is_active=? WHERE id=?""",
                        (code, ptype, value, min_spend, start_at, end_at, applies_to_product_id, is_active, pid))
        else:
            cur.execute("""INSERT INTO promotions(code,type,value,min_spend,start_at,end_at,applies_to_product_id,is_active)
                           VALUES(?,?,?,?,?,?,?,?)""",
                        (code, ptype, value, min_spend, start_at, end_at, applies_to_product_id, is_active))
        self.conn.commit()

    def delete_promo(self, pid):
        self.conn.execute("DELETE FROM promotions WHERE id=?", (pid,)); self.conn.commit()

    # orders
    def list_orders(self, status_filter=None, date_from=None, date_to=None):
        q = "SELECT * FROM orders WHERE 1=1"
        params = []
        if status_filter and status_filter != "ALL":
            q += " AND status=?"; params.append(status_filter)
        if date_from:
            q += " AND order_datetime >= ?"; params.append(date_from+" 00:00:00")
        if date_to:
            q += " AND order_datetime <= ?"; params.append(date_to+" 23:59:59")
        q += " ORDER BY id DESC"
        return self.conn.execute(q, params).fetchall()

    def order_items(self, oid):
        return self.conn.execute("SELECT * FROM order_items WHERE order_id=?", (oid,)).fetchall()

    def set_order_status(self, oid, status):
        self.conn.execute("UPDATE orders SET status=? WHERE id=?", (status, oid)); self.conn.commit()

    # dashboard
    def sales_by_day(self, start, end):
        return self.conn.execute("""
            SELECT substr(order_datetime,1,10) AS d, SUM(total) total
            FROM orders WHERE order_datetime BETWEEN ? AND ?
            GROUP BY d ORDER BY d
        """, (start+" 00:00:00", end+" 23:59:59")).fetchall()

    def sales_by_month(self, year):
        return self.conn.execute("""
            SELECT substr(order_datetime,1,7) AS ym, SUM(total) total
            FROM orders WHERE substr(order_datetime,1,4)=?
            GROUP BY ym ORDER BY ym
        """, (year,)).fetchall()

    def sales_by_year(self):
        return self.conn.execute("""
            SELECT substr(order_datetime,1,4) AS y, SUM(total) total
            FROM orders GROUP BY y ORDER BY y
        """).fetchall()

    def sales_by_menu(self, start, end):
        return self.conn.execute("""
            SELECT name, SUM(qty) qty, SUM((unit_price+add_price)*qty) sales
            FROM order_items oi JOIN orders o ON o.id=oi.order_id
            WHERE o.order_datetime BETWEEN ? AND ?
            GROUP BY name ORDER BY sales DESC
        """, (start+" 00:00:00", end+" 23:59:59")).fetchall()

    # demo order
    def create_demo_order(self):
        p = self.conn.execute("SELECT * FROM products ORDER BY RANDOM() LIMIT 1").fetchone()
        if not p: return
        subtotal = p['base_price']
        discount = 0.0
        vat = round((subtotal - discount) * 0.07, 2)
        total = round(subtotal - discount + vat, 2)
        cur = self.conn.cursor()
        cur.execute("""INSERT INTO orders(user_id, order_datetime, status, subtotal, discount, vat, total, note)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (None, now_ts(), "PAID", subtotal, discount, vat, total, "demo"))
        oid = cur.lastrowid
        cur.execute("""INSERT INTO order_items(order_id,product_id,name,qty,unit_price,options_json,add_price)
                       VALUES(?,?,?,?,?,?,?)""",
                    (oid, p['id'], p['name'], 1, p['base_price'], json.dumps({}), 0))
        self.conn.commit()


# ---------- Receipt ----------
def save_receipt(db: AdminDB, order_id: int, path_hint: Optional[str] = None) -> str:
    order = db.conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not order:
        raise ValueError("Order not found")
    items = db.order_items(order_id)

    pdfcanvas, A4, mm = try_import_reportlab()
    if pdfcanvas:
        path = path_hint or os.path.join(REPORTS_DIR, f"receipt_{order_id}.pdf")
        canv = pdfcanvas.Canvas(path, pagesize=A4)
        W, H = A4; x = 18*mm; y = H - 18*mm
        canv.setFont("Helvetica-Bold", 16); canv.drawString(x, y, "TASTE AND SIP - RECEIPT"); y -= 10*mm
        canv.setFont("Helvetica", 10)
        canv.drawString(x, y, f"Order ID: {order_id}"); y -= 5*mm
        canv.drawString(x, y, f"Date/Time: {order['order_datetime']}"); y -= 8*mm
        canv.setFont("Helvetica-Bold", 12); canv.drawString(x, y, "Items"); y -= 6*mm
        canv.setFont("Helvetica", 10)
        for it in items:
            opts = json.loads(it['options_json'] or "{}")
            canv.drawString(x, y, f"- {it['name']} x{it['qty']}  @ {it['unit_price']:.2f}"); y -= 5*mm
            if opts:
                canv.drawString(x+8*mm, y, f"Options: " + ", ".join(f"{k}:{v}" for k,v in opts.items())); y -= 5*mm
            if safe_float(it['add_price'])>0:
                canv.drawString(x+8*mm, y, f"Add-on: +{safe_float(it['add_price']):.2f}"); y -= 5*mm
            y -= 1*mm
        y -= 2*mm
        canv.setFont("Helvetica-Bold", 11)
        canv.drawString(x, y, f"Subtotal: {order['subtotal']:.2f}"); y -= 5*mm
        canv.drawString(x, y, f"Discount: {order['discount']:.2f}"); y -= 5*mm
        canv.drawString(x, y, f"VAT 7%: {order['vat']:.2f}"); y -= 5*mm
        canv.drawString(x, y, f"Total: {order['total']:.2f}"); y -= 8*mm
        canv.showPage(); canv.save()
        return path
    else:
        path = path_hint or os.path.join(REPORTS_DIR, f"receipt_{order_id}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("TASTE AND SIP - RECEIPT\n")
            f.write(f"Order ID: {order_id}\n")
            f.write(f"Date/Time: {order['order_datetime']}\n")
            f.write("Items:\n")
            for it in items:
                opts = json.loads(it['options_json'] or "{}")
                f.write(f"  - {it['name']} x{it['qty']}  @ {it['unit_price']:.2f}\n")
                if opts:
                    f.write("    Options: " + ", ".join(f"{k}:{v}" for k,v in opts.items()) + "\n")
                if safe_float(it['add_price'])>0:
                    f.write(f"    Add-on: +{safe_float(it['add_price']):.2f}\n")
            f.write(f"\nSubtotal: {order['subtotal']:.2f}\n")
            f.write(f"Discount: {order['discount']:.2f}\n")
            f.write(f"VAT 7%: {order['vat']:.2f}\n")
            f.write(f"Total: {order['total']:.2f}\n")
        return path


# ---------- Admin UI ----------
class AdminApp(ctk.CTk):
    def __init__(self, db: AdminDB, admin_row: sqlite3.Row):
        super().__init__()
        ctk.set_appearance_mode("light")
        self.title(f"{APP_TITLE} — ADMIN")
        try: self.state("zoomed")
        except: self.geometry("1400x820")
        self.configure(fg_color=RIGHT_BG)
        self.db = db
        self.admin = admin_row

        # Top bar
        top = ctk.CTkFrame(self, fg_color="transparent"); top.pack(side="top", fill="x", padx=12, pady=12)
        ctk.CTkLabel(top, text=f"ADMIN: {self.admin['username']}", text_color=TEXT_DARK,
                     fg_color="transparent", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        ctk.CTkButton(top, text="NEW DEMO ORDER", command=self._demo_order, corner_radius=RADIUS).pack(side="right")

        # Tabs
        tabs = ctk.CTkTabview(self, fg_color=CARD_BG, segmented_button_fg_color="#e8d4b2",
                              segmented_button_selected_color="#e2cda6", segmented_button_unselected_color="#f1e3ca",
                              text_color=TEXT_DARK, corner_radius=RADIUS)
        tabs.pack(fill="both", expand=True, padx=12, pady=12)

        self.tab_dash   = tabs.add("Dashboard")
        self.tab_menu   = tabs.add("Menu")
        self.tab_promo  = tabs.add("Promotions")
        self.tab_orders = tabs.add("Orders")

        self._dash_ui()
        self._menu_ui()
        self._promo_ui()
        self._orders_ui()

    # DASHBOARD
    def _dash_ui(self):
        self.var_start = tk.StringVar(value=dt.now().strftime("%Y-%m-01"))
        self.var_end   = tk.StringVar(value=dt.now().strftime("%Y-%m-%d"))
        self.var_year  = tk.StringVar(value=dt.now().strftime("%Y"))

        row1 = ctk.CTkFrame(self.tab_dash, fg_color="transparent"); row1.pack(fill="x", padx=10, pady=4)
        for lbl, var in [("Start (YYYY-MM-DD)", self.var_start), ("End", self.var_end), ("Year", self.var_year)]:
            b = ctk.CTkFrame(row1, fg_color="transparent"); b.pack(side="left", padx=6)
            ctk.CTkLabel(b, text=lbl, fg_color="transparent").pack(anchor="w")
            ctk.CTkEntry(b, textvariable=var, corner_radius=RADIUS).pack()

        btns = ctk.CTkFrame(self.tab_dash, fg_color="transparent"); btns.pack(fill="x", padx=10, pady=4)
        ctk.CTkButton(btns, text="Sales by Day", command=self._dash_day).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Sales by Month", command=self._dash_month).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Sales by Year", command=self._dash_year).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Sales by Menu", command=self._dash_menu).pack(side="left", padx=4)

        self.tv_dash = ttk.Treeview(self.tab_dash, columns=("c1","c2","c3"), show="headings", height=18)
        self.tv_dash.pack(fill="both", expand=True, padx=10, pady=10)
        for i,w in enumerate([200,180,160], start=1):
            self.tv_dash.heading(f"c{i}", text=f"COL{i}")
            self.tv_dash.column(f"c{i}", width=w, anchor="w")

    def _tv_fill(self, tv, headers: List[str], rows: List[List[Any]]):
        tv["columns"] = tuple(f"c{i}" for i in range(1, len(headers)+1))
        tv["show"] = "headings"
        for c in tv["columns"]:
            tv.heading(c, text=headers[int(c[1:])-1])
            tv.column(c, width=200, anchor="w")
        for i in tv.get_children(): tv.delete(i)
        for r in rows:
            tv.insert("", "end", values=tuple(r))

    def _dash_day(self):
        s, e = self.var_start.get().strip(), self.var_end.get().strip()
        rows = [(r['d'], f"{(r['total'] or 0):.2f}") for r in self.db.sales_by_day(s,e)]
        self._tv_fill(self.tv_dash, ["DATE","TOTAL"], rows)

    def _dash_month(self):
        y = self.var_year.get().strip()
        rows = [(r['ym'], f"{(r['total'] or 0):.2f}") for r in self.db.sales_by_month(y)]
        self._tv_fill(self.tv_dash, ["YEAR-MONTH","TOTAL"], rows)

    def _dash_year(self):
        rows = [(r['y'], f"{(r['total'] or 0):.2f}") for r in self.db.sales_by_year()]
        self._tv_fill(self.tv_dash, ["YEAR","TOTAL"], rows)

    def _dash_menu(self):
        s, e = self.var_start.get().strip(), self.var_end.get().strip()
        rows = [(r['name'], r['qty'], f"{(r['sales'] or 0):.2f}") for r in self.db.sales_by_menu(s,e)]
        self._tv_fill(self.tv_dash, ["MENU","QTY","SALES"], rows)

    def _demo_order(self):
        self.db.create_demo_order()
        messagebox.showinfo("Demo", "Created one paid order for dashboard demo.")

    # MENU
    def _menu_ui(self):
        wrapper = ctk.CTkFrame(self.tab_menu, fg_color="transparent"); wrapper.pack(fill="both", expand=True, padx=10, pady=10)
        left = ctk.CTkFrame(wrapper, fg_color=CARD_BG, corner_radius=RADIUS); left.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        right= ctk.CTkFrame(wrapper, fg_color=CARD_BG, corner_radius=RADIUS); right.pack(side="left", fill="both", expand=True, padx=6, pady=6)

        # Categories
        ctk.CTkLabel(left, text="CATEGORIES (by country)", fg_color="transparent",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=12, pady=(12,4))
        self.tv_cat = ttk.Treeview(left, columns=("id","name","country"), show="headings", height=10)
        for k,w in [("id",60), ("name",180), ("country",160)]:
            self.tv_cat.heading(k, text=k.upper()); self.tv_cat.column(k, width=w, anchor="w")
        self.tv_cat.pack(fill="x", padx=12, pady=6)

        frc = ctk.CTkFrame(left, fg_color="transparent"); frc.pack(fill="x", padx=12, pady=6)
        self.var_cat_name = tk.StringVar(); self.var_cat_country = tk.StringVar()
        ctk.CTkEntry(frc, placeholder_text="Category Name", textvariable=self.var_cat_name, corner_radius=RADIUS).pack(side="left", padx=4)
        ctk.CTkEntry(frc, placeholder_text="Country", textvariable=self.var_cat_country, corner_radius=RADIUS).pack(side="left", padx=4)
        ctk.CTkButton(frc, text="Add", command=self._cat_add, corner_radius=RADIUS).pack(side="left", padx=4)
        ctk.CTkButton(frc, text="Delete", command=self._cat_del, corner_radius=RADIUS).pack(side="left", padx=4)

        # Products
        ctk.CTkLabel(right, text="PRODUCTS", fg_color="transparent",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=12, pady=(12,4))
        self.tv_prod = ttk.Treeview(right, columns=("id","name","ptype","category","country","price","active","image"), show="headings", height=12)
        heads = [("id",60),("name",160),("ptype",70),("category",140),("country",120),("price",80),("active",60),("image",200)]
        for k,w in heads:
            self.tv_prod.heading(k, text=k.upper()); self.tv_prod.column(k, width=w, anchor="w")
        self.tv_prod.pack(fill="both", expand=True, padx=12, pady=6)

        frp = ctk.CTkFrame(right, fg_color="transparent"); frp.pack(fill="x", padx=12, pady=6)
        ctk.CTkButton(frp, text="Add / Edit", command=self._prod_edit, corner_radius=RADIUS).pack(side="left", padx=4)
        ctk.CTkButton(frp, text="Delete", command=self._prod_del, corner_radius=RADIUS).pack(side="left", padx=4)
        ctk.CTkButton(frp, text="Options", command=self._prod_opts, corner_radius=RADIUS).pack(side="left", padx=4)

        self._reload_categories(); self._reload_products()

    def _reload_categories(self):
        for i in self.tv_cat.get_children(): self.tv_cat.delete(i)
        for r in self.db.list_categories():
            self.tv_cat.insert("", "end", values=(r['id'], r['name'], r['country']))

    def _reload_products(self):
        for i in self.tv_prod.get_children(): self.tv_prod.delete(i)
        for r in self.db.list_products():
            self.tv_prod.insert("", "end", values=(r['id'], r['name'], r['ptype'], r['category_name'] or "-", r['country'] or "-", f"{r['base_price']:.2f}", r['is_active'], r['image'] or ""))

    def _cat_add(self):
        name = self.var_cat_name.get().strip()
        country = self.var_cat_country.get().strip()
        if not name or not country:
            messagebox.showerror("Category", "Fill name & country"); return
        self.db.add_category(name, country); self._reload_categories()
        self.var_cat_name.set(""); self.var_cat_country.set("")

    def _cat_del(self):
        sel = self.tv_cat.selection()
        if not sel: return
        cid = int(self.tv_cat.item(sel[0],"values")[0])
        if messagebox.askyesno("Delete", "Delete this category?"):
            self.db.delete_category(cid); self._reload_categories()

    def _prod_edit(self):
        sel = self.tv_prod.selection()
        pid = int(self.tv_prod.item(sel[0],"values")[0]) if sel else None
        ProductEditor(self, self.db, pid, self._reload_products)

    def _prod_del(self):
        sel = self.tv_prod.selection()
        if not sel: return
        pid = int(self.tv_prod.item(sel[0],"values")[0])
        if messagebox.askyesno("Delete", "Delete product?"):
            self.db.delete_product(pid); self._reload_products()

    def _prod_opts(self):
        sel = self.tv_prod.selection()
        if not sel:
            messagebox.showinfo("Options", "Select a product"); return
        pid = int(self.tv_prod.item(sel[0],"values")[0])
        ProductOptionEditor(self, self.db, pid)

    # PROMOTIONS
    def _promo_ui(self):
        wrap = ctk.CTkFrame(self.tab_promo, fg_color="transparent"); wrap.pack(fill="both", expand=True, padx=10, pady=10)
        top = ctk.CTkFrame(wrap, fg_color="transparent"); top.pack(fill="x")
        ctk.CTkButton(top, text="Add / Edit", command=self._promo_edit, corner_radius=RADIUS).pack(side="left", padx=4)
        ctk.CTkButton(top, text="Delete", command=self._promo_del, corner_radius=RADIUS).pack(side="left", padx=4)
        ctk.CTkButton(top, text="Refresh", command=self._promo_reload, corner_radius=RADIUS).pack(side="left", padx=4)

        self.tv_promo = ttk.Treeview(wrap, columns=("id","code","type","value","min","start","end","applies","active"), show="headings")
        for k,w in [("id",60),("code",120),("type",140),("value",80),("min",80),("start",140),("end",140),("applies",100),("active",60)]:
            self.tv_promo.heading(k, text=k.upper()); self.tv_promo.column(k, width=w, anchor="w")
        self.tv_promo.pack(fill="both", expand=True, pady=10)
        self._promo_reload()

    def _promo_reload(self):
        for i in self.tv_promo.get_children(): self.tv_promo.delete(i)
        for r in self.db.list_promos():
            self.tv_promo.insert("", "end",
                                 values=(r['id'], r['code'], r['type'], r['value'], r['min_spend'],
                                         r['start_at'], r['end_at'], r['applies_to_product_id'] or "-", r['is_active']))

    def _promo_edit(self):
        sel = self.tv_promo.selection()
        pid = int(self.tv_promo.item(sel[0],"values")[0]) if sel else None
        PromoEditor(self, self.db, pid, self._promo_reload)

    def _promo_del(self):
        sel = self.tv_promo.selection()
        if not sel: return
        pid = int(self.tv_promo.item(sel[0],"values")[0])
        if messagebox.askyesno("Delete", "Delete promotion?"):
            self.db.delete_promo(pid); self._promo_reload()

    # ORDERS
    def _orders_ui(self):
        wrap = ctk.CTkFrame(self.tab_orders, fg_color="transparent"); wrap.pack(fill="both", expand=True, padx=10, pady=10)
        filt = ctk.CTkFrame(wrap, fg_color="transparent"); filt.pack(fill="x")
        self.var_status = tk.StringVar(value="ALL")
        self.var_from   = tk.StringVar(value=dt.now().strftime("%Y-%m-01"))
        self.var_to     = tk.StringVar(value=dt.now().strftime("%Y-%m-%d"))
        for lbl, var in [("Status (ALL/PENDING/CONFIRMED/CANCELLED/PAID)", self.var_status),
                         ("From", self.var_from), ("To", self.var_to)]:
            b = ctk.CTkFrame(filt, fg_color="transparent"); b.pack(side="left", padx=6)
            ctk.CTkLabel(b, text=lbl).pack(anchor="w")
            ctk.CTkEntry(b, textvariable=var, corner_radius=RADIUS).pack()

        ctk.CTkButton(filt, text="Search", command=self._order_reload).pack(side="left", padx=8)
        top = ctk.CTkFrame(wrap, fg_color="transparent"); top.pack(fill="x", pady=(6,4))
        ctk.CTkButton(top, text="Confirm", command=lambda:self._order_set("CONFIRMED")).pack(side="left", padx=4)
        ctk.CTkButton(top, text="Cancel", command=lambda:self._order_set("CANCELLED")).pack(side="left", padx=4)
        ctk.CTkButton(top, text="Mark Paid + Receipt", command=self._order_paid_receipt).pack(side="left", padx=4)
        ctk.CTkButton(top, text="Refresh", command=self._order_reload).pack(side="left", padx=4)

        body = ctk.CTkFrame(wrap, fg_color="transparent"); body.pack(fill="both", expand=True)
        self.tv_orders = ttk.Treeview(body, columns=("id","dt","status","subtotal","discount","vat","total","note"), show="headings", height=14)
        for k,w in [("id",60),("dt",160),("status",120),("subtotal",100),("discount",100),("vat",90),("total",100),("note",220)]:
            self.tv_orders.heading(k, text=k.upper()); self.tv_orders.column(k, width=w, anchor="w")
        self.tv_orders.pack(side="left", fill="both", expand=True, padx=(0,6))
        self.tv_items  = ttk.Treeview(body, columns=("name","qty","price","addon","opts"), show="headings", height=14)
        for k,w in [("name",180),("qty",60),("price",90),("addon",80),("opts",260)]:
            self.tv_items.heading(k, text=k.upper()); self.tv_items.column(k, width=w, anchor="w")
        self.tv_items.pack(side="left", fill="both", expand=True)

        self._order_reload()

    def _order_reload(self):
        for i in self.tv_orders.get_children(): self.tv_orders.delete(i)
        rows = self.db.list_orders(self.var_status.get().strip() or None,
                                   self.var_from.get().strip() or None,
                                   self.var_to.get().strip() or None)
        for r in rows:
            self.tv_orders.insert("", "end", values=(r['id'], r['order_datetime'], r['status'],
                                                     f"{r['subtotal']:.2f}", f"{r['discount']:.2f}",
                                                     f"{r['vat']:.2f}", f"{r['total']:.2f}", r['note'] or ""))
        # clear items
        for i in self.tv_items.get_children(): self.tv_items.delete(i)
        self.tv_orders.bind("<<TreeviewSelect>>", self._order_select)

    def _order_select(self, _e=None):
        for i in self.tv_items.get_children(): self.tv_items.delete(i)
        sel = self.tv_orders.selection()
        if not sel: return
        oid = int(self.tv_orders.item(sel[0],"values")[0])
        for it in self.db.order_items(oid):
            opts = json.loads(it['options_json'] or "{}")
            opts_s = ", ".join(f"{k}:{v}" for k,v in opts.items())
            self.tv_items.insert("", "end", values=(it['name'], it['qty'], f"{it['unit_price']:.2f}",
                                                    f"{safe_float(it['add_price']):.2f}", opts_s))

    def _order_set(self, status):
        sel = self.tv_orders.selection()
        if not sel: return
        oid = int(self.tv_orders.item(sel[0],"values")[0])
        self.db.set_order_status(oid, status); self._order_reload()

    def _order_paid_receipt(self):
        sel = self.tv_orders.selection()
        if not sel: return
        oid = int(self.tv_orders.item(sel[0],"values")[0])
        self.db.set_order_status(oid, "PAID")
        path = save_receipt(self.db, oid)
        messagebox.showinfo("Receipt", f"Saved:\n{path}")
        self._order_reload()


# ---------- Sub editors ----------
class ProductEditor(ctk.CTkToplevel):
    def __init__(self, master, db: AdminDB, pid, on_done):
        super().__init__(master); self.db=db; self.pid=pid; self.on_done=on_done
        self.title("Product Editor"); self.geometry("640x420"); self.configure(fg_color=RIGHT_BG)
        frm = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=RADIUS); frm.pack(fill="both", expand=True, padx=12, pady=12)

        cats = self.db.list_categories()
        self.cat_map = {f"{r['name']} ({r['country']})": r['id'] for r in cats}
        self.var_name = tk.StringVar(); self.var_price = tk.StringVar(); self.var_image = tk.StringVar()
        self.var_active = tk.StringVar(value="1"); self.var_ptype = tk.StringVar(value="FOOD")
        self.var_cat = tk.StringVar(value=(list(self.cat_map.keys())[0] if self.cat_map else ""))

        grid = ctk.CTkFrame(frm, fg_color="transparent"); grid.pack(fill="x", padx=8, pady=8)
        for i in range(4): grid.grid_columnconfigure(i, weight=1, uniform="g")

        def row(r, c, text, widget):
            ctk.CTkLabel(grid, text=text).grid(row=r, column=c, sticky="w", padx=6, pady=4)
            widget.grid(row=r+1, column=c, sticky="ew", padx=6)

        row(0,0,"Name", ctk.CTkEntry(grid, textvariable=self.var_name, corner_radius=RADIUS))
        row(0,1,"Type (FOOD/DRINK)", ctk.CTkEntry(grid, textvariable=self.var_ptype, corner_radius=RADIUS))
        row(0,2,"Base Price", ctk.CTkEntry(grid, textvariable=self.var_price, corner_radius=RADIUS))
        row(0,3,"Active (1/0)", ctk.CTkEntry(grid, textvariable=self.var_active, corner_radius=RADIUS))

        ctk.CTkLabel(grid, text="Category").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        cb = ttk.Combobox(grid, values=list(self.cat_map.keys()), textvariable=self.var_cat, state="readonly")
        cb.grid(row=3, column=0, sticky="ew", padx=6)

        ctk.CTkLabel(grid, text="Image").grid(row=2, column=1, sticky="w", padx=6, pady=4)
        img_entry = ctk.CTkEntry(grid, textvariable=self.var_image, corner_radius=RADIUS); img_entry.grid(row=3, column=1, sticky="ew", padx=6)
        ctk.CTkButton(grid, text="Choose...", command=self._pick_image).grid(row=3, column=2, sticky="w", padx=6)

        ctk.CTkButton(frm, text="Save", corner_radius=RADIUS, command=self._save).pack(pady=12)

        if pid:
            r = self.db.conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
            if r:
                self.var_name.set(r['name']); self.var_ptype.set(r['ptype'])
                self.var_price.set(str(r['base_price'])); self.var_image.set(r['image'] or "")
                self.var_active.set(str(r['is_active']))
                cname = self.db.conn.execute("SELECT name,country FROM categories WHERE id=?", (r['category_id'],)).fetchone()
                label = f"{(cname['name'] if cname else '')} ({(cname['country'] if cname else '-')})"
                if label in self.cat_map: self.var_cat.set(label)

    def _pick_image(self):
        f = filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg")])
        if not f: return
        dest = os.path.join(IMG_PRODUCTS_DIR, os.path.basename(f))
        try:
            import shutil; shutil.copy2(f, dest); self.var_image.set(dest)
        except Exception as e:
            messagebox.showerror("Image", f"Copy failed: {e}")

    def _save(self):
        try:
            name = self.var_name.get().strip()
            ptype = self.var_ptype.get().strip().upper()
            price = safe_float(self.var_price.get().strip(), 0.0)
            active = 1 if (self.var_active.get().strip() or "1") != "0" else 0
            image = self.var_image.get().strip()
            cat_id = self.cat_map.get(self.var_cat.get().strip())
            if not name or ptype not in ("FOOD","DRINK") or not cat_id:
                messagebox.showerror("Error","Invalid inputs"); return
            self.db.upsert_product(self.pid, name, cat_id, ptype, price, image, active)
            messagebox.showinfo("Saved","Product saved"); self.on_done(); self.destroy()
        except Exception as e:
            messagebox.showerror("Save", str(e))

class ProductOptionEditor(ctk.CTkToplevel):
    def __init__(self, master, db: AdminDB, pid):
        super().__init__(master); self.db=db; self.pid=pid
        self.title("Product Options"); self.geometry("640x520"); self.configure(fg_color=RIGHT_BG)
        frm = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=RADIUS); frm.pack(fill="both", expand=True, padx=12, pady=12)
        p = self.db.conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
        ctk.CTkLabel(frm, text=f"{p['name']} ({p['ptype']})", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=12, pady=(10,6))

        self.opts = self.db.get_options(pid)

        # FOOD
        self.var_meat = tk.StringVar(value=",".join(self.opts.get("Meat",{}).get("values",["Pork","Chicken","Beef","Seafood"])))
        self.var_spice= tk.StringVar(value=",".join(self.opts.get("Spice",{}).get("values",["Mild","Medium","Hot","Extra Hot"])))

        # DRINK
        size_cfg = self.opts.get("Size", {"values":["S","M","L"], "price_multipliers":{"S":1.0,"M":1.2,"L":1.5}})
        self.var_sizes = tk.StringVar(value=",".join(size_cfg.get("values",["S","M","L"])))
        self.var_mults = tk.StringVar(value=json.dumps(size_cfg.get("price_multipliers",{"S":1.0,"M":1.2,"L":1.5})))
        self.var_ice   = tk.StringVar(value=",".join(self.opts.get("Ice",{}).get("values",["0%","25%","50%","75%","100%"])))
        self.var_sweet = tk.StringVar(value=",".join(self.opts.get("Sweetness",{}).get("values",["0%","25%","50%","75%","100%"])))

        grid = ctk.CTkFrame(frm, fg_color="transparent"); grid.pack(fill="x", padx=12, pady=8)
        for i in range(2): grid.grid_columnconfigure(i, weight=1, uniform="g")

        def row(r, c, label, var, hint=""):
            ctk.CTkLabel(grid, text=label).grid(row=r, column=c, sticky="w", padx=6, pady=2)
            ctk.CTkEntry(grid, textvariable=var, corner_radius=RADIUS).grid(row=r+1, column=c, sticky="ew", padx=6)
            if hint:
                ctk.CTkLabel(grid, text=hint, text_color="#6b7280").grid(row=r+2, column=c, sticky="w", padx=6, pady=(0,6))

        if p['ptype']=="FOOD":
            row(0,0,"Meat choices (comma)", self.var_meat)
            row(0,1,"Spice levels (comma)", self.var_spice)
        else:
            row(0,0,"Size values (comma)", self.var_sizes, "e.g. S,M,L")
            row(0,1,"Size multipliers (JSON)", self.var_mults, 'e.g. {"S":1.0,"M":1.2,"L":1.5}')
            row(3,0,"Ice levels (comma)", self.var_ice)
            row(3,1,"Sweetness levels (comma)", self.var_sweet)

        ctk.CTkButton(frm, text="Save Options", command=lambda:self._save(p['ptype']), corner_radius=RADIUS).pack(pady=10)

    def _save(self, ptype):
        try:
            if ptype=="FOOD":
                meats = [s.strip() for s in self.var_meat.get().split(",") if s.strip()]
                spices= [s.strip() for s in self.var_spice.get().split(",") if s.strip()]
                self.db.set_option(self.pid,"Meat",{"values":meats})
                self.db.set_option(self.pid,"Spice",{"values":spices})
            else:
                sizes = [s.strip() for s in self.var_sizes.get().split(",") if s.strip()]
                mults = json.loads(self.var_mults.get().strip() or "{}")
                ice   = [s.strip() for s in self.var_ice.get().split(",") if s.strip()]
                sweet = [s.strip() for s in self.var_sweet.get().split(",") if s.strip()]
                self.db.set_option(self.pid,"Size",{"values":sizes,"price_multipliers":mults})
                self.db.set_option(self.pid,"Ice",{"values":ice})
                self.db.set_option(self.pid,"Sweetness",{"values":sweet})
            messagebox.showinfo("Options","Saved")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Options", str(e))

class PromoEditor(ctk.CTkToplevel):
    def __init__(self, master, db: AdminDB, pid, on_done):
        super().__init__(master); self.db=db; self.pid=pid; self.on_done=on_done
        self.title("Promotion Editor"); self.geometry("720x360"); self.configure(fg_color=RIGHT_BG)
        frm = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=RADIUS); frm.pack(fill="both", expand=True, padx=12, pady=12)
        self.v = {k: tk.StringVar() for k in ["code","type","value","min","start","end","applies","active"]}
        grid = ctk.CTkFrame(frm, fg_color="transparent"); grid.pack(fill="x", padx=12, pady=8)
        for i in range(4): grid.grid_columnconfigure(i, weight=1, uniform="g")
        def cell(r,c,label,key,hint=""):
            ctk.CTkLabel(grid, text=label).grid(row=r, column=c, sticky="w", padx=6, pady=2)
            ctk.CTkEntry(grid, textvariable=self.v[key], corner_radius=RADIUS).grid(row=r+1, column=c, sticky="ew", padx=6)
            if hint: ctk.CTkLabel(grid, text=hint, text_color="#6b7280").grid(row=r+2, column=c, sticky="w", padx=6)
        cell(0,0,"Code","code")
        cell(0,1,"Type","type","PERCENT_BILL/FLAT_BILL/PERCENT_ITEM/FLAT_ITEM")
        cell(0,2,"Value","value")
        cell(0,3,"Min Spend","min")
        cell(3,0,"Start (YYYY-MM-DD HH:MM:SS)","start")
        cell(3,1,"End","end")
        cell(3,2,"Applies to Product ID (for *_ITEM)","applies")
        cell(3,3,"Active 1/0","active")
        ctk.CTkButton(frm, text="Save", command=self._save, corner_radius=RADIUS).pack(pady=10)

        if pid:
            r = self.db.conn.execute("SELECT * FROM promotions WHERE id=?", (pid,)).fetchone()
            if r:
                self.v["code"].set(r['code']); self.v["type"].set(r['type']); self.v["value"].set(str(r['value']))
                self.v["min"].set(str(r['min_spend'])); self.v["start"].set(r['start_at'] or ""); self.v["end"].set(r['end_at'] or "")
                self.v["applies"].set("" if r['applies_to_product_id'] is None else str(r['applies_to_product_id']))
                self.v["active"].set(str(r['is_active']))

    def _save(self):
        try:
            code = self.v["code"].get().strip().upper()
            ptype= self.v["type"].get().strip().upper()
            value= safe_float(self.v["value"].get().strip(), 0)
            minsp= safe_float(self.v["min"].get().strip(), 0)
            start= self.v["start"].get().strip() or dt.now().strftime("%Y-%m-%d 00:00:00")
            end  = self.v["end"].get().strip() or (dt.now()+timedelta(days=365)).strftime("%Y-%m-%d 23:59:59")
            ap_s = self.v["applies"].get().strip()
            applies = int(ap_s) if ap_s.isdigit() else None
            active = 1 if (self.v["active"].get().strip() or "1") != "0" else 0
            if not code or ptype not in ("PERCENT_BILL","FLAT_BILL","PERCENT_ITEM","FLAT_ITEM"):
                messagebox.showerror("Promo","Invalid code/type"); return
            self.db.upsert_promo(self.pid, code, ptype, value, minsp, start, end, applies, active)
            messagebox.showinfo("Promo","Saved"); self.on_done(); self.destroy()
        except Exception as e:
            messagebox.showerror("Promo", str(e))


# ==============================  MAIN  ================================
if __name__ == "__main__":
    LEFT_BG_PATH = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\AVIBRA_1.png"
    LOGO_PATH    = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\lologogo.png-removebg-preview.png"

    # สร้างหน้าล็อกอินก่อน (root ตัวแรก)
    root = AuthApp(db_path=DB_FILE, left_bg_path=LEFT_BG_PATH, logo_path=LOGO_PATH)

    def after_login(user_row: sqlite3.Row):
        role = (user_row["role"] or "customer").lower()
        if role == "admin":
            # ซ่อนหน้าล็อกอินชั่วคราว
            root.withdraw()

            # เปิดหน้าผู้ดูแล (รัน mainloop ของมันเองจนกว่าจะปิด)
            admin_db = AdminDB(DB_FILE)
            admin_app = AdminApp(admin_db, user_row)
            admin_app.mainloop()

            # เมื่อปิดหน้าผู้ดูแลแล้ว ค่อยทำความสะอาด/ปิดโปรแกรม
            root.destroy()
        else:
            # TODO: ต่อไปยังระบบลูกค้า/หน้าขาย (POS)
            messagebox.showinfo("Signed in", f"Hello, {user_row['username']} (role={role}).\nTODO: open POS/front-end here.")

    # ตั้ง callback (ไม่ destroy ที่นี่)
    root.on_login_success = after_login

    # เริ่มรันแอป
    root.mainloop()
# -*- coding: utf-8 -*-
"""
Auth screens using customtkinter (rounded/modern, cream theme, uppercase)
- Left: image cover on Canvas (draw image + white titles with no background).
- Right: rounded cream card; Sign Up uses 2-column compact form (balanced height).
- Validations: username/phone/email/password per spec.
- DB: SQLite users table (compatible). SHA-256 password.

AdminWindow:
- Opens as CTkToplevel after admin login (single mainloop pattern)
- Tabs: Dashboard / Menu / Promotions / Orders (skeleton UI ready to extend)

Run: python app.py
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
        self.db_path = path
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
        # ---- seed default admin if missing ----
        if not c.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
            c.execute(
                "INSERT INTO users(username, password_hash, name, role) VALUES(?,?,?,?)",
                ("admin", sha256("admin123"), "Administrator", "admin"),
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

# ====== Admin Window (Toplevel) ======
class AdminWindow(ctk.CTkToplevel):
    def __init__(self, master, user_row: sqlite3.Row, db: AuthDB):
        super().__init__(master)
        self.title(f"{APP_TITLE} — ADMIN")
        self.geometry("1400x820")
        self.configure(fg_color=RIGHT_BG)
        self.user = user_row
        self.db = db

        # Close behavior: on admin window close -> destroy root app
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Top bar
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(side="top", fill="x", padx=12, pady=12)
        ctk.CTkLabel(top, text=f"ADMIN: {self.user['username']}",
                     text_color=TEXT_DARK, fg_color="transparent",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        ctk.CTkButton(top, text="Sign out", corner_radius=RADIUS,
                      command=self._on_close).pack(side="right")

        # Tabs (skeleton, ready to extend)
        tabs = ctk.CTkTabview(self, fg_color=CARD_BG, segmented_button_fg_color="#e8d4b2",
                              segmented_button_selected_color="#e2cda6",
                              segmented_button_unselected_color="#f1e3ca",
                              text_color=TEXT_DARK, corner_radius=RADIUS)
        tabs.pack(fill="both", expand=True, padx=12, pady=12)

        self.tab_dash   = tabs.add("Dashboard")
        self.tab_menu   = tabs.add("Menu")
        self.tab_promo  = tabs.add("Promotions")
        self.tab_orders = tabs.add("Orders")

        # ---- Minimal content for each tab (placeholder) ----
        self._dash_ui()
        self._menu_ui()
        self._promo_ui()
        self._orders_ui()

        # Make the window modal-like (optional)
        self.transient(master)
        self.grab_set()
        self.focus()

    def _on_close(self):
        # close admin then close root app
        try:
            self.grab_release()
        except:
            pass
        # แสดง root กลับมาก่อนแล้วค่อย destroy ทั้งโปรแกรม
        root = self.master
        if root is not None:
            root.destroy()
        self.destroy()

    # ---- Placeholder UIs ----
    def _dash_ui(self):
        box = ctk.CTkFrame(self.tab_dash, fg_color="transparent")
        box.pack(fill="both", expand=True, padx=12, pady=12)
        ctk.CTkLabel(box, text="DASHBOARD (สรุปยอดขายรายวัน/เดือน/ปี — โครงพร้อมต่อยอด)",
                     text_color=TEXT_DARK, fg_color="transparent",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0,6))
        ctk.CTkLabel(box, text="(ภายหลังจะเพิ่มตาราง/กราฟและตัวกรองช่วงเวลา)",
                     text_color="#6b7280", fg_color="transparent").pack(anchor="w")

    def _menu_ui(self):
        box = ctk.CTkFrame(self.tab_menu, fg_color="transparent")
        box.pack(fill="both", expand=True, padx=12, pady=12)
        ctk.CTkLabel(box, text="MENU (จัดหมวดหมู่/เพิ่ม-ลบ-แก้ไขเมนู/ตั้งราคา/ออปชัน)",
                     text_color=TEXT_DARK, fg_color="transparent",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0,6))
        ctk.CTkLabel(box, text="(ภายหลังจะเพิ่มตารางหมวดหมู่/สินค้า และ dialog แก้ไข)",
                     text_color="#6b7280", fg_color="transparent").pack(anchor="w")

    def _promo_ui(self):
        box = ctk.CTkFrame(self.tab_promo, fg_color="transparent")
        box.pack(fill="both", expand=True, padx=12, pady=12)
        ctk.CTkLabel(box, text="PROMOTIONS (โค้ดส่วนลดตามบิล/ต่อเมนู, กำหนดช่วงเวลา)",
                     text_color=TEXT_DARK, fg_color="transparent",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0,6))
        ctk.CTkLabel(box, text="(ภายหลังจะเพิ่มฟอร์มสร้าง/แก้ไข/ลบโปรโมชัน)",
                     text_color="#6b7280", fg_color="transparent").pack(anchor="w")

    def _orders_ui(self):
        box = ctk.CTkFrame(self.tab_orders, fg_color="transparent")
        box.pack(fill="both", expand=True, padx=12, pady=12)
        ctk.CTkLabel(box, text="ORDERS (ดู/ยืนยัน/ยกเลิก/ออกใบเสร็จ + VAT 7%)",
                     text_color=TEXT_DARK, fg_color="transparent",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0,6))
        ctk.CTkLabel(box, text="(ภายหลังจะเพิ่มตารางออเดอร์ รายการอาหาร และปุ่มออกใบเสร็จ)",
                     text_color="#6b7280", fg_color="transparent").pack(anchor="w")

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
            # ถ้าเป็นแอดมิน เปิด AdminWindow (Toplevel) และซ่อนหน้าล็อกอิน
            role = (row["role"] or "customer").lower()
            if role == "admin":
                self.withdraw()
                AdminWindow(self, row, self.db)  # ใช้ mainloop เดียว (ของ AuthApp)
            else:
                if self.on_login_success:
                    self.on_login_success(row)
                else:
                    messagebox.showinfo("SUCCESS", f"WELCOME, {u}! (role={role})\nTODO: open customer/front-end app here.")
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
        # จะถูกใช้เฉพาะกรณี role != admin
        messagebox.showinfo("SIGNED IN", f"HELLO, {user_row['username']}!)")

    app = AuthApp(db_path="taste_and_sip.db", left_bg_path=LEFT_BG_PATH, logo_path=LOGO_PATH,
                  on_login_success=_demo_success)
    app.mainloop()
# ===== CUSTOMER STORE (Front) ===============================================
# วางตั้งแต่บรรทัดนี้ "ต่อท้าย" ไฟล์เดิมได้เลย

class StoreDB:
    """ตัวช่วยอ่านเมนู/ออปชัน/โปรโม/สร้างออเดอร์ สำหรับฝั่งลูกค้า"""
    def __init__(self, path="taste_and_sip.db"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row

    # --- catalog ---
    def categories(self):
        return self.conn.execute("SELECT id,name,country FROM categories ORDER BY country,name").fetchall()

    def products_by_category(self, cat_id: int):
        return self.conn.execute("""
          SELECT p.* FROM products p
          WHERE p.category_id=? AND p.is_active=1
          ORDER BY p.name
        """, (cat_id,)).fetchall()

    def product_options(self, pid: int) -> dict:
        out = {}
        for r in self.conn.execute("SELECT option_name, option_values_json FROM product_options WHERE product_id=?", (pid,)):
            try:
                out[r["option_name"]] = json.loads(r["option_values_json"] or "{}")
            except Exception:
                out[r["option_name"]] = {}
        return out

    # --- promotions ---
    def get_promo(self, code: str):
        code = (code or "").upper().strip()
        if not code: return None
        now = dt.now().strftime("%Y-%m-%d %H:%M:%S")
        return self.conn.execute("""
           SELECT * FROM promotions
           WHERE code=? AND is_active=1
             AND (start_at IS NULL OR start_at<=?)
             AND (end_at   IS NULL OR end_at  >=?)
        """, (code, now, now)).fetchone()

    # --- orders ---
    def create_order(self, user_id, items, promo_row):
        """
        items: list of dicts:
          {pid, name, qty, unit_price, add_price, options(dict)}
        คำนวณส่วนลดตาม promo (รองรับแบบทั้งบิล และต่อรายการ)
        """
        subtotal = sum((it["unit_price"] + it.get("add_price", 0.0)) * it["qty"] for it in items)
        discount = 0.0

        if promo_row:
            ptype = promo_row["type"]
            val   = float(promo_row["value"] or 0)
            minsp = float(promo_row["min_spend"] or 0)
            applies_pid = promo_row["applies_to_product_id"]

            def disc_percent(amount, pct): return amount * (pct/100.0)
            def disc_flat(amount, flat):    return min(amount, flat)

            if subtotal >= minsp:
                if ptype == "PERCENT_BILL":
                    discount = disc_percent(subtotal, val)
                elif ptype == "FLAT_BILL":
                    discount = disc_flat(subtotal, val)
                elif ptype in ("PERCENT_ITEM","FLAT_ITEM"):
                    for it in items:
                        if applies_pid and int(applies_pid) != int(it["pid"]): 
                            continue
                        line = (it["unit_price"] + it.get("add_price",0.0)) * it["qty"]
                        if ptype == "PERCENT_ITEM":
                            discount += disc_percent(line, val)
                        else:
                            discount += disc_flat(line, val)

        vat = round((subtotal - discount) * 0.07, 2)
        total = round(subtotal - discount + vat, 2)

        cur = self.conn.cursor()
        cur.execute("""INSERT INTO orders(user_id, order_datetime, status, subtotal, discount, vat, total, note)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (user_id, dt.now().strftime("%Y-%m-%d %H:%M:%S"), "PENDING",
                     round(subtotal,2), round(discount,2), vat, total, None))
        oid = cur.lastrowid

        for it in items:
            cur.execute("""INSERT INTO order_items(order_id, product_id, name, qty, unit_price, options_json, add_price)
                           VALUES(?,?,?,?,?,?,?)""",
                        (oid, it["pid"], it["name"], it["qty"], it["unit_price"],
                         json.dumps(it.get("options", {}), ensure_ascii=False),
                         round(it.get("add_price",0.0),2)))
        self.conn.commit()
        return oid, subtotal, discount, vat, total


class CustomerApp(ctk.CTkToplevel):
    """หน้าร้านแบบมินิมัล: เลือกเมนู/ออปชัน → ตะกร้า → สร้างออเดอร์ (PENDING)"""
    def __init__(self, master, user_row, db_path="taste_and_sip.db"):
        super().__init__(master)
        ctk.set_appearance_mode("light")
        self.title("TASTE AND SIP — STORE")
        try: self.state("zoomed")
        except: self.geometry("1200x720")
        self.configure(fg_color=RIGHT_BG)

        self.user = user_row
        self.db   = StoreDB(db_path)
        self.cart = []  # list of dict (pid,name,qty,unit_price,add_price,options)
        self.promo_row = None

        # Top bar
        top = ctk.CTkFrame(self, fg_color="transparent"); top.pack(fill="x", padx=12, pady=12)
        ctk.CTkLabel(top, text=f"CUSTOMER: {self.user['username']}", text_color=TEXT_DARK,
                     fg_color="transparent", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        self.promo_var = tk.StringVar()
        ctk.CTkEntry(top, placeholder_text="PROMO CODE", textvariable=self.promo_var,
                     corner_radius=RADIUS, width=180).pack(side="right", padx=(6,0))
        ctk.CTkButton(top, text="Apply", command=self._apply_promo, corner_radius=RADIUS).pack(side="right")

        # Body 3 คอลัมน์
        body = ctk.CTkFrame(self, fg_color="transparent"); body.pack(fill="both", expand=True, padx=12, pady=12)

        # 1) Categories
        left = ctk.CTkFrame(body, fg_color=CARD_BG, corner_radius=RADIUS); left.pack(side="left", fill="y", padx=6, pady=6)
        ctk.CTkLabel(left, text="CATEGORIES", font=ctk.CTkFont(size=14, weight="bold"),
                     fg_color="transparent").pack(anchor="w", padx=12, pady=(12,4))
        self.lb_cat = tk.Listbox(left, height=20)
        self.lb_cat.pack(fill="both", expand=True, padx=12, pady=(0,12))
        self.lb_cat.bind("<<ListboxSelect>>", lambda e: self._load_products())
        # load categories
        self._cat_rows = self.db.categories()
        for r in self._cat_rows:
            self.lb_cat.insert("end", f"{r['name']} ({r['country']})")
        if self._cat_rows: self.lb_cat.selection_set(0)

        # 2) Products + Options + Add
        mid = ctk.CTkFrame(body, fg_color=CARD_BG, corner_radius=RADIUS); mid.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ctk.CTkLabel(mid, text="PRODUCTS", font=ctk.CTkFont(size=14, weight="bold"),
                     fg_color="transparent").pack(anchor="w", padx=12, pady=(12,4))
        self.tv_prod = tk.ttk.Treeview(mid, columns=("name","ptype","price"), show="headings", height=12)
        for k,w in [("name",260),("ptype",80),("price",80)]:
            self.tv_prod.heading(k, text=k.upper()); self.tv_prod.column(k, width=w, anchor="w")
        self.tv_prod.pack(fill="both", expand=True, padx=12, pady=(0,8))
        self.tv_prod.bind("<<TreeviewSelect>>", lambda e: self._show_options())

        opt = ctk.CTkFrame(mid, fg_color="#f1e3ca", corner_radius=RADIUS); opt.pack(fill="x", padx=12, pady=(0,10))
        self.opt_title = ctk.CTkLabel(opt, text="OPTIONS", font=ctk.CTkFont(size=13, weight="bold"),
                                      fg_color="transparent")
        self.opt_title.grid(row=0, column=0, sticky="w", padx=10, pady=(8,4), columnspan=4)
        # widgets (สร้างไว้ก่อน)
        self.var_qty = tk.IntVar(value=1)
        self.sp_qty = ctk.CTkEntry(opt, textvariable=self.var_qty, width=60, corner_radius=RADIUS)
        ctk.CTkLabel(opt, text="QTY").grid(row=1, column=0, sticky="e", padx=8, pady=4)
        self.sp_qty.grid(row=1, column=1, sticky="w", padx=4, pady=4)

        self.cmb_meat = tk.ttk.Combobox(opt, state="readonly"); self.cmb_spice = tk.ttk.Combobox(opt, state="readonly")
        self.cmb_size = tk.ttk.Combobox(opt, state="readonly"); self.cmb_ice   = tk.ttk.Combobox(opt, state="readonly")
        self.cmb_sweet= tk.ttk.Combobox(opt, state="readonly")

        # ป้ายด้านซ้าย
        self.lb_meat  = ctk.CTkLabel(opt, text="Meat");  self.lb_spice = ctk.CTkLabel(opt, text="Spice")
        self.lb_size  = ctk.CTkLabel(opt, text="Size");  self.lb_ice   = ctk.CTkLabel(opt, text="Ice")
        self.lb_sweet = ctk.CTkLabel(opt, text="Sweet")

        # ตำแหน่ง grid
        self._opt_pairs = [
            (self.lb_meat,  self.cmb_meat, 2,0),
            (self.lb_spice, self.cmb_spice,2,2),
            (self.lb_size,  self.cmb_size, 3,0),
            (self.lb_ice,   self.cmb_ice,  3,2),
            (self.lb_sweet, self.cmb_sweet,4,0),
        ]
        for i in range(4): opt.grid_columnconfigure(i, weight=1)

        ctk.CTkButton(mid, text="ADD TO CART", command=self._add_to_cart,
                      corner_radius=RADIUS).pack(padx=12, pady=(0,10), anchor="e")

        # 3) Cart
        right = ctk.CTkFrame(body, fg_color=CARD_BG, corner_radius=RADIUS); right.pack(side="left", fill="both", padx=6, pady=6)
        ctk.CTkLabel(right, text="CART", font=ctk.CTkFont(size=14, weight="bold"),
                     fg_color="transparent").pack(anchor="w", padx=12, pady=(12,4))
        self.tv_cart = tk.ttk.Treeview(right, columns=("name","qty","price","opt"), show="headings", height=14)
        for k,w in [("name",240),("qty",60),("price",100),("opt",220)]:
            self.tv_cart.heading(k, text=k.upper()); self.tv_cart.column(k, width=w, anchor="w")
        self.tv_cart.pack(fill="both", expand=True, padx=12, pady=(0,8))

        btns = ctk.CTkFrame(right, fg_color="transparent"); btns.pack(fill="x", padx=12, pady=(0,10))
        ctk.CTkButton(btns, text="Remove", command=self._remove_cart, corner_radius=RADIUS).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Checkout", command=self._checkout, corner_radius=RADIUS).pack(side="right", padx=4)

        self._load_products()  # โหลดสินค้าตามหมวดแรกทันที

    # ---------- UI helpers ----------
    def _current_category_id(self):
        sel = self.lb_cat.curselection()
        if not sel: return None
        return self._cat_rows[sel[0]]["id"]

    def _load_products(self):
        for i in self.tv_prod.get_children(): self.tv_prod.delete(i)
        cid = self._current_category_id()
        if not cid: return
        self._prod_rows = self.db.products_by_category(cid)
        for p in self._prod_rows:
            self.tv_prod.insert("", "end", values=(p["name"], p["ptype"], f"{p['base_price']:.2f}"), iid=str(p["id"]))
        # clear options
        self._clear_options()

    def _clear_options(self):
        for lb, cmb, r, c in self._opt_pairs:
            lb.grid_remove(); cmb.grid_remove()
        self.var_qty.set(1)

    def _show_options(self):
        self._clear_options()
        sel = self.tv_prod.selection()
        if not sel: return
        pid = int(sel[0])
        row = next((p for p in self._prod_rows if p["id"]==pid), None)
        if not row: return
        opts = self.db.product_options(pid)
        # เติม combobox ตามชนิด
        if row["ptype"] == "FOOD":
            meats = opts.get("Meat",{}).get("values",["Pork","Chicken","Beef","Seafood"])
            spice = opts.get("Spice",{}).get("values",["Mild","Medium","Hot","Extra Hot"])
            self.cmb_meat["values"]  = meats; self.cmb_meat.current(0)
            self.cmb_spice["values"] = spice; self.cmb_spice.current(0)
            self.lb_meat.grid(row=2, column=0, sticky="e", padx=8, pady=4); self.cmb_meat.grid(row=2, column=1, sticky="ew", padx=4, pady=4)
            self.lb_spice.grid(row=2, column=2, sticky="e", padx=8, pady=4); self.cmb_spice.grid(row=2, column=3, sticky="ew", padx=4, pady=4)
        else:
            sizes = opts.get("Size",{}).get("values",["S","M","L"])
            self.size_mults = opts.get("Size",{}).get("price_multipliers",{"S":1.0,"M":1.2,"L":1.5})
            ice = opts.get("Ice",{}).get("values",["0%","25%","50%","75%","100%"])
            sweet = opts.get("Sweetness",{}).get("values",["0%","25%","50%","75%","100%"])
            self.cmb_size["values"]  = sizes; self.cmb_size.current(0)
            self.cmb_ice["values"]   = ice;   self.cmb_ice.current(2 if "50%" in ice else 0)
            self.cmb_sweet["values"] = sweet; self.cmb_sweet.current(2 if "50%" in sweet else 0)
            self.lb_size.grid(row=3, column=0, sticky="e", padx=8, pady=4); self.cmb_size.grid(row=3, column=1, sticky="ew", padx=4, pady=4)
            self.lb_ice.grid( row=3, column=2, sticky="e", padx=8, pady=4); self.cmb_ice.grid( row=3, column=3, sticky="ew", padx=4, pady=4)
            self.lb_sweet.grid(row=4, column=0, sticky="e", padx=8, pady=4); self.cmb_sweet.grid(row=4, column=1, sticky="ew", padx=4, pady=4)

    def _add_to_cart(self):
        sel = self.tv_prod.selection()
        if not sel: return
        pid = int(sel[0])
        p = next((x for x in self._prod_rows if x["id"]==pid), None)
        if not p: return

        qty = max(1, int(self.var_qty.get() or 1))
        unit_price = float(p["base_price"] or 0)
        add_price  = 0.0
        options = {}

        if p["ptype"]=="FOOD":
            options["Meat"]  = self.cmb_meat.get() if self.cmb_meat.winfo_ismapped() else None
            options["Spice"] = self.cmb_spice.get() if self.cmb_spice.winfo_ismapped() else None
        else:
            size = self.cmb_size.get() if self.cmb_size.winfo_ismapped() else "M"
            mult = float(self.size_mults.get(size, 1.2))
            unit_price = round(unit_price * mult, 2)
            options["Size"]  = size
            options["Ice"]   = self.cmb_ice.get() if self.cmb_ice.winfo_ismapped() else None
            options["Sweetness"] = self.cmb_sweet.get() if self.cmb_sweet.winfo_ismapped() else None

        # push to cart
        item = dict(pid=pid, name=p["name"], qty=qty, unit_price=unit_price,
                    add_price=add_price, options={k:v for k,v in options.items() if v})
        self.cart.append(item)
        self._render_cart()

    def _render_cart(self):
        for i in self.tv_cart.get_children(): self.tv_cart.delete(i)
        for i, it in enumerate(self.cart, 1):
            opt_s = ", ".join(f"{k}:{v}" for k,v in it.get("options",{}).items())
            self.tv_cart.insert("", "end", values=(
                it["name"], it["qty"], f"{(it['unit_price']+it.get('add_price',0.0))*it['qty']:.2f}", opt_s
            ), iid=str(i))

    def _remove_cart(self):
        sel = self.tv_cart.selection()
        if not sel: return
        idx = int(sel[0]) - 1
        if 0 <= idx < len(self.cart):
            del self.cart[idx]
            self._render_cart()

    def _apply_promo(self):
        row = self.db.get_promo(self.promo_var.get())
        if row:
            self.promo_row = row
            messagebox.showinfo("PROMO", f"APPLIED: {row['code']} ({row['type']} {row['value']})")
        else:
            self.promo_row = None
            messagebox.showwarning("PROMO", "INVALID OR EXPIRED CODE")

    def _checkout(self):
        if not self.cart:
            messagebox.showwarning("Checkout","Cart is empty"); return
        oid, sub, disc, vat, tot = self.db.create_order(self.user["id"] if "id" in self.user.keys() else None,
                                                        self.cart, self.promo_row)
        self.cart.clear(); self._render_cart()
        messagebox.showinfo("Order Created",
                            f"ORDER #{oid}\nSubtotal: {sub:.2f}\nDiscount: {disc:.2f}\nVAT 7%: {vat:.2f}\nTotal: {tot:.2f}\n\nStatus: PENDING")


# ===== ROUTER หลังล็อกอิน ==========================================
def after_login(user_row: sqlite3.Row):
    """เรียกใช้ใน on_login_success ของ AuthApp"""
    # ปิดหน้าล็อกอินหลักก่อน
    try:
        # self ที่เรียกจะเป็นอินสแตนซ์ AuthApp; เราเรียกจากภายนอกไม่ได้
        # ดังนั้นเวลา set on_login_success ให้ใช้ lambda ที่มี self อ้างในคลอเชอร์แทน (ดูตัวอย่างด้านล่าง)
        pass
    except:
        pass

# --- ตัวอย่างวิธีผูก on_login_success ตอนสร้าง AuthApp (แก้ใน main ของคุณ) ---
# def _router(user_row):
#     # ถ้าเป็น admin → เปิด AdminApp (ของคุณ); customer → เปิด CustomerApp
#     if user_row["role"] == "admin":
#         # เรียกแอปแอดมินของคุณ (สมมุติชื่อฟังก์ชัน launch_admin)
#         AdminAppLauncher(user_row)   # <-- คุณมีอยู่แล้วจากฝั่งแอดมิน
#     else:
#         # เปิด CustomerApp เป็นหน้าต่างใหม่ (Toplevel) และปิดหน้าล็อกอิน
#         cust = CustomerApp(app, user_row, db_path="taste_and_sip.db")
#         app.withdraw()  # ซ่อนหน้าล็อกอิน หรือ app.destroy() ถ้าต้องการปิดเลย

# app = AuthApp(..., on_login_success=_router)
# app.mainloop()