# -*- coding: utf-8 -*-

# -----+ END 13/11/2025 03:04 AM +------#

# ================== Imports ==================
import os, sys, json, sqlite3, hashlib, shutil, re
from datetime import datetime as dt, timedelta
from typing import Optional, Callable, List, Dict

# ==== 3rd party ====
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.units import mm
import customtkinter as ctk
from tkinter import filedialog, messagebox  # ใช้งาน dialog จาก tkinter ได้ตามปกติ
# ==== เพิ่มสำหรับกราฟ ====
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ================== App Constants ==================
APP_TITLE = "TASTE AND SIP"
DB_FILE   = "finaltastse.db"
REPORTS_DIR = "reports"
VAT_RATE  = 0.07

# ---- Assets ----
ASSETS_DIR       = "assets"
IMG_DIR          = os.path.join(ASSETS_DIR, "images")
IMG_PRODUCTS_DIR = os.path.join(IMG_DIR, "products")
IMG_AVATARS_DIR  = os.path.join(ASSETS_DIR, "avatars")
# ให้เอาไฟล์ qrcode.jpg วางไว้ที่ assets/images/qrcode.jpg 
IMG_QR_PATH      = os.path.join(IMG_DIR,  r"C:\Users\thatt\Downloads\qrcode.jpg")
ABOUT_IMG_PATH = os.path.join(IMG_DIR, r"C:\Users\thatt\Downloads\contact.jpg")  # ใส่รูป about_us.jpg ไว้ใน assets/images


LEFT_BG_PATH = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\AVIBRA_1.png"
LOGO_PATH    = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\lologogo.png-removebg-preview.png"

COMPANY_TEL   = "0954751704"
COMPANY_TAXID = "01075557001234"
COMPANY_ADDRESS = "123/45 Moo 6, Sukhumvit Rd., Bangna, Bangkok 10260"

def ensure_dirs():
    for p in (ASSETS_DIR, IMG_DIR, IMG_PRODUCTS_DIR, IMG_AVATARS_DIR, REPORTS_DIR):
        os.makedirs(p, exist_ok=True)

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def now_ts() -> str:
    return dt.now().strftime("%Y-%m-%d %H:%M:%S")

# ================== Color Palette ==================
PALETTE = {
    "bistre":        "#372414",  # title/dark
    "antique":       "#F7EBDF",  # main bg
    "pale_taupe":    "#B7A087",
    "milk":          "#825A3C",
    "van_dyke":      "#674831",
    "white":         "#FFFFFF"
}

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")  # ไม่ใช้สีจากธีม ปรับสี component เองทั้งหมด

# ================== DB Layer ==================
class DB:
    # ใน class DB:
    def is_admin(self, user_id:int) -> bool:
        r = self.conn.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
        return (r and (r["role"] or "").lower() == "admin")

    def create_order(self, user_id, cart_items, promo_code, payment_method="SLIP", payment_ref=""):
        # --- กันแอดมินสร้างออเดอร์ ---
        if self.is_admin(user_id):
            raise PermissionError("Admins are not allowed to create orders.")
        # ... โค้ดเดิมต่อจากนี้ ...
    def __init__(self, path=DB_FILE):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._schema()
        self._seed()
        self._migrate()

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
        c.execute("""CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, category_id INTEGER, base_price REAL,
            image TEXT, is_active INTEGER DEFAULT 1
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS promotions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE, type TEXT, value REAL,
            min_spend REAL DEFAULT 0,
            start_at TEXT, end_at TEXT,
            applies_to_product_id INTEGER,
            is_active INTEGER DEFAULT 1
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, order_datetime TEXT,
            channel TEXT, pickup_time TEXT,
            subtotal REAL, discount REAL, total REAL,
            payment_method TEXT, status TEXT, vat REAL DEFAULT 0
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS order_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER, product_id INTEGER,
            qty INTEGER, unit_price REAL, options_json TEXT, note TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS payments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER, method TEXT, amount REAL, paid_at TEXT, ref TEXT
        )""")
        self.conn.commit()

    def _migrate(self):
        cols = [r["name"] for r in self.conn.execute("PRAGMA table_info(orders)")]
        if "vat" not in cols:
            try:
                self.conn.execute("ALTER TABLE orders ADD COLUMN vat REAL DEFAULT 0")
                self.conn.commit()
            except Exception:
                pass

    def _seed(self):
        c = self.conn.cursor()
        if not c.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
            c.execute("INSERT INTO users(username,password_hash,name,role) VALUES(?,?,?,?)",
                      ("admin", sha256("admin123"), "Administrator", "admin"))
        if c.execute("SELECT COUNT(*) n FROM categories").fetchone()['n'] == 0:
            c.executemany("INSERT INTO categories(name) VALUES(?)", [("FOOD",),("DRINK",),("DESSERT",)])
        if c.execute("SELECT COUNT(*) n FROM products").fetchone()['n'] == 0:
            cats = {r['name']: r['id'] for r in c.execute("SELECT * FROM categories")}
            data = [
                ("Pad Thai", cats["FOOD"], 60.0, "", 1),
                ("Thai Milk Tea", cats["DRINK"], 35.0, "", 1),
                ("Mango Sticky Rice", cats["DESSERT"], 50.0, "", 1),
            ]
            c.executemany("INSERT INTO products(name,category_id,base_price,image,is_active) VALUES(?,?,?,?,?)", data)
        if c.execute("SELECT COUNT(*) n FROM promotions").fetchone()['n'] == 0:
            today = dt.now()
            st = (today - timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
            ed = (today + timedelta(days=365)).strftime("%Y-%m-%d 23:59:59")
            tea_id = c.execute("SELECT id FROM products WHERE name='Thai Milk Tea'").fetchone()
            tea_id = tea_id['id'] if tea_id else None
            promos = [
                ("WELCOME10","PERCENT_BILL",10,0,st,ed,None,1),
                ("TEA5","FLAT_ITEM",5,0,st,ed,tea_id,1),
            ]
            c.executemany("""INSERT INTO promotions(code,type,value,min_spend,start_at,end_at,applies_to_product_id,is_active)
                             VALUES(?,?,?,?,?,?,?,?)""", promos)
        self.conn.commit()

    # --- auth/profile ---
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
        self.conn.execute("UPDATE users SET password_hash=? WHERE id=?", (sha256(newpass), uid)); self.conn.commit()

    # --- catalog ---
    def categories(self): 
        return self.conn.execute("SELECT * FROM categories").fetchall()

    def products_by_cat(self, cid): 
        return self.conn.execute(
            "SELECT * FROM products WHERE category_id=? AND is_active=1", (cid,)).fetchall()

    # (เพิ่ม) ใช้ในหน้า Admin
    def list_products(self):
        return self.conn.execute("""
            SELECT p.*, c.name AS category_name
            FROM products p LEFT JOIN categories c ON c.id=p.category_id
            ORDER BY p.id
        """).fetchall()

    def upsert_product(self, pid, name, category_id, base_price, image, is_active):
        cur = self.conn.cursor
        cur = self.conn.cursor()
        if pid:
            cur.execute("""UPDATE products 
                           SET name=?, category_id=?, base_price=?, image=?, is_active=?
                           WHERE id=?""", (name, category_id, base_price, image, is_active, pid))
        else:
            cur.execute("""INSERT INTO products(name, category_id, base_price, image, is_active)
                           VALUES(?,?,?,?,?)""", (name, category_id, base_price, image, is_active))
        self.conn.commit()

    def delete_product(self, pid):
        self.conn.execute("DELETE FROM products WHERE id=?", (pid,))
        self.conn.commit()

    # --- promos ---
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

    # (เพิ่ม) ใช้ในหน้า Admin Promos
    def list_promotions(self):
        return self.conn.execute("SELECT * FROM promotions ORDER BY id DESC").fetchall()

    def delete_promotion(self, pid):
        self.conn.execute("DELETE FROM promotions WHERE id=?", (pid,))
        self.conn.commit()

    # --- orders/payments ---
    def create_order(self, user_id, cart_items, promo_code, payment_method="SLIP", payment_ref=""):
        subtotal = 0.0
        item_totals = []
        for it in cart_items:
            base = float(it['base_price'])
            line = base * it['qty']
            subtotal += line
            item_totals.append((it['product_id'], line))

        discount = 0.0
        promo = self.find_promo(promo_code) if promo_code else None
        if promo:
            msp = float(promo['min_spend'] or 0)
            ptype = promo['type']; val = float(promo['value'] or 0)
            pid = promo['applies_to_product_id']
            if ptype in ("PERCENT_BILL","FLAT_BILL") and subtotal >= msp:
                discount = subtotal*(val/100.0) if ptype=="PERCENT_BILL" else min(val, subtotal)
            elif ptype in ("PERCENT_ITEM","FLAT_ITEM") and pid:
                target = sum(line for (prod,line) in item_totals if prod==pid)
                if target>0:
                    discount = target*(val/100.0) if ptype=="PERCENT_ITEM" else min(val, target)

        base_after = max(0.0, subtotal - discount)
        vat = round(base_after * VAT_RATE, 2)
        total = base_after + vat

        cur = self.conn.cursor()
        cur.execute("""INSERT INTO orders(user_id,order_datetime,channel,pickup_time,subtotal,discount,total,payment_method,status,vat)
                       VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (user_id, now_ts(), "", "", subtotal, discount, total, payment_method, "PAID", vat))
        order_id = cur.lastrowid
        for it in cart_items:
            cur.execute("""INSERT INTO order_items(order_id,product_id,qty,unit_price,options_json,note)
                           VALUES(?,?,?,?,?,?)""",
                        (order_id, it['product_id'], it['qty'], it['base_price'], "{}", ""))

        cur.execute("INSERT INTO payments(order_id,method,amount,paid_at,ref) VALUES(?,?,?,?,?)",
                    (order_id, payment_method, total, now_ts(), payment_ref))
        self.conn.commit()
        return order_id, subtotal, discount, vat, total

    def orders_of_user(self, uid, limit=200):
        return self.conn.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ?", (uid, limit)).fetchall()

    def order_detail(self, oid):
        o = self.conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        items = self.conn.execute("""SELECT oi.*, p.name AS product_name
                                     FROM order_items oi JOIN products p ON p.id=oi.product_id
                                     WHERE order_id=?""",(oid,)).fetchall()
        return o, items, []

    def list_orders(self, limit=300):
        return self.conn.execute("""
            SELECT o.*, u.username
            FROM orders o
            LEFT JOIN users u ON u.id = o.user_id
            ORDER BY o.id DESC
            LIMIT ?
        """, (limit,)).fetchall()

    def order_payments(self, oid):
        return self.conn.execute("""SELECT * FROM payments WHERE order_id=? ORDER BY id DESC""",(oid,)).fetchall()

    def set_order_status(self, oid, status):
        self.conn.execute("UPDATE orders SET status=? WHERE id=?", (status, oid)); self.conn.commit()

    # --- reports ---
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
            GROUP BY p.id
            ORDER BY qty DESC, sales DESC
        """,(start+" 00:00:00", end+" 23:59:59")).fetchall()


    def report_top_customers(self, start, end, limit=10):
        return self.conn.execute("""
            SELECT u.username, u.name, SUM(o.total) total
            FROM orders o JOIN users u ON u.id=o.user_id
            WHERE o.order_datetime BETWEEN ? AND ?
            GROUP BY u.id ORDER BY total DESC LIMIT ?
        """,(start+" 00:00:00", end+" 23:59:59", limit)).fetchall()

    def report_sales_monthly(self, start, end):
        return self.conn.execute("""
            SELECT strftime('%Y-%m', order_datetime) AS period,
                   SUM(total) AS revenue,
                   COUNT(*) AS orders,
                   CASE WHEN COUNT(*)=0 THEN 0 ELSE ROUND(SUM(total)/COUNT(*),2) END AS aov
            FROM orders
            WHERE order_datetime BETWEEN ? AND ? AND COALESCE(status,'') NOT IN ('CANCELLED')
            GROUP BY period ORDER BY period
        """,(start+" 00:00:00", end+" 23:59:59")).fetchall()

    def report_sales_yearly(self, start, end):
        return self.conn.execute("""
            SELECT strftime('%Y', order_datetime) AS period,
                   SUM(total) AS revenue,
                   COUNT(*) AS orders,
                   CASE WHEN COUNT(*)=0 THEN 0 ELSE ROUND(SUM(total)/COUNT(*),2) END AS aov
            FROM orders
            WHERE order_datetime BETWEEN ? AND ? AND COALESCE(status,'') NOT IN ('CANCELLED')
            GROUP BY period ORDER BY period
        """,(start+" 00:00:00", end+" 23:59:59")).fetchall()


# ================== Receipt (PDF) ==================
def create_receipt_pdf(order_id, db: DB, user_row):
    ensure_dirs()
    path = os.path.join(REPORTS_DIR, f"receipt_{order_id}.pdf")
    c = pdfcanvas.Canvas(path, pagesize=A4)
    W, H = A4

    # --- โลโก้กึ่งกลาง ---
    if LOGO_PATH and os.path.exists(LOGO_PATH):
        try:
            iw, ih = 36*mm, 32*mm
            c.drawImage(LOGO_PATH, (W - iw)/2, H - 35*mm, width=iw, height=ih,
                        preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # --- ข้อมูลบริษัท/ลูกค้า ---
    order, items, _ = db.order_detail(order_id)
    ts = order['order_datetime']
    try:
        dobj = dt.strptime(ts, "%Y-%m-%d %H:%M:%S")
        d_txt = dobj.strftime("%d/%m/%Y"); t_txt = dobj.strftime("%H:%M")
    except Exception:
        d_txt = ts.split(" ")[0]; t_txt = (ts.split(" ")[1] if " " in ts else "")

    customer_name = (user_row.get("name") or user_row.get("username") or "").strip()

    mx = 25*mm
    y0 = H - 45*mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(mx, y0,             f"TEL. {COMPANY_TEL}")
    c.drawRightString(W - mx, y0,    f"TAX ID : {COMPANY_TAXID}")
    c.drawString(mx, y0 - 8*mm,      f"ADDRESS : {COMPANY_ADDRESS}")
    c.drawString(mx, y0 - 16*mm,     f"DATE {d_txt}")
    c.drawRightString(W - mx, y0 - 16*mm, f"TIME {t_txt}")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(mx, y0 - 24*mm,     f"NAME : {customer_name}")

    # --- หัวข้อเลขที่ออเดอร์ ---
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W/2, y0 - 34*mm, "ORDER NO.")
    c.drawCentredString(W/2, y0 - 42*mm, f"#TAS{order_id}")
    c.line(mx, y0 - 47*mm, W - mx, y0 - 47*mm)

    # --- ตารางรายการ ---
    y = y0 - 56*mm
    cols = [("No.", 12*mm), ("MENU", 80*mm), ("QTY.", 18*mm), ("PRICE", 25*mm), ("TOTAL", 25*mm)]
    widths = [w for _, w in cols]
    c.setFont("Helvetica-Bold", 11)
    x = mx
    for t, w in cols:
        c.drawString(x+2, y, t); x += w
    y -= 8*mm
    c.setFont("Helvetica", 11)
    for i, it in enumerate(items, 1):
        x = mx
        unit = float(it['unit_price']); qty = int(it['qty']); line = unit*qty
        row = [str(i), it['product_name'], str(qty), f"{unit:,.2f}", f"{line:,.2f}"]
        for val, w in zip(row, widths):
            c.drawString(x+2, y, val); x += w
        y -= 7*mm

    # --- สรุปยอด (มีคอมมา) ---
    c.drawString(mx, y-6*mm, "VAT (7%)")
    c.drawRightString(W - mx, y-6*mm, f"{float(order['vat'] or 0):,.2f}")
    y -= 8*mm
    c.drawString(mx, y-6*mm, "DISCOUNT")
    c.drawRightString(W - mx, y-6*mm, f"{float(order['discount'] or 0):,.2f}")
    y -= 14*mm; c.line(mx, y, W - mx, y); y -= 10*mm
    c.setFont("Helvetica-Bold", 12); c.drawString(mx, y, "TOTAL")
    c.drawRightString(W - mx, y, f"{float(order['total'] or 0):,.2f}")
    y -= 6*mm; c.line(mx, y, W - mx, y)

    c.showPage(); c.save()
    return path

# ================== Auth (customtkinter) ==================
RIGHT_BG   = PALETTE["antique"]
CARD_BG    = "#EEDCC6"
TEXT_DARK  = PALETTE["bistre"]
LINK_FG    = PALETTE["van_dyke"]
BORDER     = PALETTE["pale_taupe"]
CARD_W     = 660
CARD_H     = 560
RADIUS     = 18

USERNAME_RE = re.compile(r"^(?=.*[A-Z])[A-Za-z0-9]{8,}$")
PHONE_RE    = re.compile(r"^\d{10}$")
EMAIL_RE    = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PWD_RE      = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,}$")

class AuthDB:
    def __init__(self, path: str = DB_FILE):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._ensure_schema()
    def _ensure_schema(self):
        c = self.conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT, phone TEXT, email TEXT, birthdate TEXT, gender TEXT,
            avatar TEXT, role TEXT DEFAULT 'customer'
        )""")
        self.conn.commit()
    def find_user_for_login(self, username: str, password: str):
        return self.conn.execute("SELECT * FROM users WHERE username=? AND password_hash=?",
                                 (username, sha256(password))).fetchone()
    def username_exists(self, username: str) -> bool:
        return self.conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone() is not None
    def create_user(self, username: str, phone: str, email: str, password: str):
        self.conn.execute("INSERT INTO users(username,password_hash,phone,email,role) VALUES(?,?,?,?,?)",
                          (username, sha256(password), phone, email, "customer"))
        self.conn.commit()
    def verify_user_contact(self, username: str, email_or_phone: str):
        return self.conn.execute("SELECT * FROM users WHERE username=? AND (email=? OR phone=?)",
                                 (username, email_or_phone, email_or_phone)).fetchone()
    def change_password(self, username: str, new_password: str):
        self.conn.execute("UPDATE users SET password_hash=? WHERE username=?",
                          (sha256(new_password), username)); self.conn.commit()

def validate_username(v): return None if USERNAME_RE.match(v or "") else "USERNAME MUST BE AT LEAST 8 CHARACTERS AND CONTAIN UPPERCASE , LOWERCASE AND 0–9."
def validate_phone(v):    return None if PHONE_RE.match(v or "") else "PHONE MUST BE 10 DIGITS."
def validate_email(v):    return None if EMAIL_RE.match(v or "") else "INVALID EMAIL FORMAT."
def validate_password(v): return None if PWD_RE.match(v or "") else "PASSWORD MUST BE ≥ 8 CHARS, INCLUDE UPPERCASE, LOWERCASE AND A DIGIT."

class AuthApp(ctk.CTk):
    """หน้า Login/Signup/Forget"""
    def __init__(self, db_path: str = DB_FILE, left_bg_path: Optional[str] = None,
                 logo_path: Optional[str] = None, on_login_success: Optional[Callable[[sqlite3.Row], None]] = None):
        super().__init__()
        ctk.set_appearance_mode("light")
        self.title(APP_TITLE)
        self._force_zoomed()  # << บังคับเต็มจอเสมอ
        self.configure(fg_color=RIGHT_BG)

        self.db = AuthDB(db_path)
        self.on_login_success = on_login_success
        self.left_bg_path = left_bg_path
        self.logo_path = logo_path

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.left = ctk.CTkFrame(self, fg_color=RIGHT_BG, corner_radius=0)
        self.left.grid(row=0, column=0, sticky="nsew")
        self.left_img = None
        self.left.bind("<Configure>", self._draw_left_bg)

        self.right = ctk.CTkFrame(self, fg_color=RIGHT_BG, corner_radius=0)
        self.right.grid(row=0, column=1, sticky="nsew")
        self.right.grid_rowconfigure(1, weight=1)
        self.right.grid_columnconfigure(0, weight=1)

        self.logo_wrap = ctk.CTkFrame(self.right, fg_color=RIGHT_BG); self.logo_wrap.grid(row=0, column=0, pady=(30, 10))
        self._render_logo()

        self.card = ctk.CTkFrame(self.right, fg_color=CARD_BG, corner_radius=RADIUS,
                                 border_color=BORDER, border_width=1, width=660, height=560)
        self.card.grid(row=1, column=0, sticky="n", padx=80, pady=(10, 40))
        self.card.grid_propagate(False)
        self.card.grid_columnconfigure(0, weight=1)

        self.show_signin()

    # NEW: force zoomed helper
    def _force_zoomed(self):
        def _z():
            try:
                self.state("zoomed")
            except:
                sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
                self.geometry(f"{sw}x{sh}+0+0")
        self.bind("<Map>", lambda e: self.after(50, _z))
        self.after(50, _z)

    def _draw_left_bg(self, *_):
        if self.left_bg_path and os.path.exists(self.left_bg_path):
            try:
                img = Image.open(self.left_bg_path).convert("RGB")
                w = self.left.winfo_width() or 600
                h = self.left.winfo_height() or 700
                iw, ih = img.size; scale = max(w/iw, h/ih)
                img = img.resize((int(iw*scale), int(ih*scale)))
                self.left_img = ctk.CTkImage(light_image=img, size=(w, h))
                ctk.CTkLabel(self.left, image=self.left_img, text="", fg_color="transparent").place(x=0, y=0, relwidth=1, relheight=1)
            except: 
                pass
        ctk.CTkLabel(self.left,
                     text=f"WELCOME TO\n{APP_TITLE}".upper(),
                     font=ctk.CTkFont(size=28, weight="bold"),
                     text_color="black",
                     fg_color="transparent"
                     ).place(x=28, y=28)

    def _render_logo(self):
        for w in self.logo_wrap.winfo_children(): w.destroy()
        if self.logo_path and os.path.exists(self.logo_path):
            img = Image.open(self.logo_path)
            self._logo = ctk.CTkImage(light_image=img, size=(220,220))
            ctk.CTkLabel(self.logo_wrap, image=self._logo, text="", fg_color="transparent").pack()
        else:
            ctk.CTkLabel(self.logo_wrap, text=APP_TITLE.upper(),
                         font=ctk.CTkFont(size=22, weight="bold"),
                         text_color=TEXT_DARK, fg_color="transparent").pack()

    # ------- Signin/Signup/Forgot -------
    def _clear_card(self):
        for w in self.card.winfo_children(): w.destroy()
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

        form = ctk.CTkFrame(self.card, fg_color="transparent"); form.pack(fill="x", padx=24, pady=(6, 10))
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

        form = ctk.CTkFrame(self.card, fg_color="transparent"); form.pack(fill="x", padx=16, pady=(6, 6))
        form.grid_columnconfigure(0, weight=1, uniform="g")
        form.grid_columnconfigure(1, weight=1, uniform="g")

        self.fp_user    = LabeledEntry(form, "USERNAME");        self.fp_user.grid(row=0, column=0, padx=8, pady=6, sticky="ew")
        self.fp_contact = LabeledEntry(form, "EMAIL OR PHONE");  self.fp_contact.grid(row=0, column=1, padx=8, pady=6, sticky="ew")
        SubmitBtn(form, "VERIFY", command=self._forgot_verify).grid(row=1, column=0, columnspan=2, padx=8, pady=(0, 6), sticky="ew")

        self.fp_step2 = ctk.CTkFrame(self.card, fg_color="transparent"); self.fp_step2.pack(fill="x", padx=16, pady=(6, 12))
        self.fp_step2.grid_columnconfigure(0, weight=1, uniform="gg")
        self.fp_step2.grid_columnconfigure(1, weight=1, uniform="gg")
        self.fp_step2.pack_forget()

        self.fp_pwd1 = LabeledEntry(self.fp_step2, "NEW PASSWORD", show="•"); self.fp_pwd1.grid(row=0, column=0, padx=8, pady=6, sticky="ew")
        self.fp_pwd2 = LabeledEntry(self.fp_step2, "CONFIRM NEW PASSWORD", show="•"); self.fp_pwd2.grid(row=0, column=1, padx=8, pady=6, sticky="ew")
        SubmitBtn(self.fp_step2, "CHANGE PASSWORD", command=self._forgot_change).grid(row=1, column=0, columnspan=2, padx=8, pady=(0, 8), sticky="ew")

        LinkBtn(self.card, "BACK TO LOGIN", command=self.show_signin).pack(pady=(0, 18))
        self._verified_username = None

    def _signin(self):
        self.si_err.set("")
        u = (self.si_user.get() or "").strip(); p = (self.si_pwd.get() or "").strip()
        if not u or not p: self.si_err.set("PLEASE ENTER USERNAME AND PASSWORD."); return
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
        if p1 != p2: self.su_err.set("PASSWORDS DO NOT MATCH."); return
        if self.db.username_exists(u): self.su_err.set("USERNAME ALREADY EXISTS."); return
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
        if not u or not cp: self.fp_err.set("PLEASE FILL USERNAME AND EMAIL/PHONE."); return
        row = self.db.verify_user_contact(u, cp)
        if row:
            self._verified_username = u
            self.fp_err.set("VERIFIED. PLEASE SET A NEW PASSWORD BELOW.")
            self.fp_step2.pack(fill="x", padx=16, pady=(6, 12))
        else:
            self.fp_err.set("NO MATCHING ACCOUNT FOR THE GIVEN USERNAME AND EMAIL/PHONE.")

    def _forgot_change(self):
        if not self._verified_username: self.fp_err.set("PLEASE VERIFY FIRST."); return
        p1 = (self.fp_pwd1.get() or "").strip(); p2 = (self.fp_pwd2.get() or "").strip()
        msg = validate_password(p1)
        if msg: self.fp_err.set(msg); return
        if p1 != p2: self.fp_err.set("PASSWORDS DO NOT MATCH."); return
        try:
            self.db.change_password(self._verified_username, p1)
            self.fp_err.set("PASSWORD CHANGED. YOU CAN SIGN IN NOW.")
        except Exception as e:
            self.fp_err.set(f"FAILED TO CHANGE PASSWORD: {e}")

class Title(ctk.CTkLabel):
    def __init__(self, master, text: str):
        super().__init__(master, text=text.upper(), font=ctk.CTkFont(size=20, weight="bold"),
                         text_color=TEXT_DARK, fg_color="transparent")

class ErrorLabel(ctk.CTkLabel):
    def __init__(self, master):
        super().__init__(master, text="", text_color="#b00020", wraplength=560, justify="left", fg_color="transparent")
    def set(self, text: str): self.configure(text=(text or "").upper())

class LabeledEntry(ctk.CTkFrame):
    def __init__(self, master, label: str, show: str = ""):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=label.upper(), text_color="#333333",
                     font=ctk.CTkFont(size=11, weight="bold"), fg_color="transparent").grid(row=0, column=0, sticky="w", padx=2, pady=(0,2))
        self.entry = ctk.CTkEntry(self, show=show, corner_radius=RADIUS,
                                  border_color=BORDER, fg_color="white")
        self.entry.grid(row=1, column=0, sticky="ew")
    def get(self) -> str: return self.entry.get()
    def set(self, v: str): self.entry.delete(0, "end"); self.entry.insert(0, v)

class SubmitBtn(ctk.CTkButton):
    def __init__(self, master, text: str, command):
        super().__init__(master, text=text.upper(), command=command, height=44, corner_radius=RADIUS,
                         fg_color="#f6e8d3", hover_color="#f6e8d3",
                         text_color=TEXT_DARK, border_color=BORDER, border_width=1)

class LinkBtn(ctk.CTkButton):
    def __init__(self, master, text: str, command):
        super().__init__(master, text=text.upper(), command=command, height=36, corner_radius=RADIUS,
                         fg_color="transparent", hover_color="#e9dcc6", text_color=LINK_FG)

# ================== Main App (customtkinter ทั้งหมด) ==================
def ctk_img(path: Optional[str], size) -> Optional[ctk.CTkImage]:
    if not path or not os.path.exists(path): return None
    try:
        img = Image.open(path)
        return ctk.CTkImage(light_image=img, size=size)
    except Exception:
        return None

class CTkMain(ctk.CTk):
    def __init__(self, db: DB, qr_path: str, on_logout: Optional[Callable]=None):
        super().__init__()
        self.title(APP_TITLE)
        self._force_zoomed()  # << บังคับเต็มจอเสมอ
        self.configure(fg_color=PALETTE["antique"])

        self.db = db
        self.qr_path = qr_path
        self.on_logout = on_logout
        self.user: Optional[Dict] = None   # เก็บเป็น dict เสมอ
        self.cart: List[Dict] = []  # [{product_id,name,base_price,qty}]

        # Layout: topbar + body
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.topbar = ctk.CTkFrame(self, fg_color=PALETTE["antique"]); self.topbar.grid(row=0, column=0, sticky="ew", padx=16, pady=(10,0))
        self.body   = ctk.CTkFrame(self, fg_color=PALETTE["antique"]); self.body.grid(row=1, column=0, sticky="nsew", padx=16, pady=10)

        # Topbar: Profile (ซ้าย), Nav (ขวา)
        self.profile_btn = ctk.CTkButton(self.topbar, text="  USERNAME", image=None, anchor="w",
                                         height=42, corner_radius=22, width=280,
                                         fg_color=PALETTE["white"], text_color=PALETTE["bistre"],
                                         hover_color=PALETTE["pale_taupe"], command=lambda:self.go("profile"))
        self.profile_btn.pack(side="left", padx=6, pady=8)

        def nav_btn(text, key):
            return ctk.CTkButton(self.topbar, text=text, width=110, corner_radius=22,
                                 fg_color=PALETTE["van_dyke"], hover_color=PALETTE["milk"],
                                 text_color=PALETTE["antique"], command=lambda:self.go(key))
        self.btn_home   = nav_btn("HOME", "home");   self.btn_home.pack(side="right", padx=6, pady=8)
        self.btn_orders = nav_btn("MY ORDERS", "orders"); self.btn_orders.pack(side="right", padx=6, pady=8)
        self.btn_cart   = nav_btn("CART", "cart");   self.btn_cart.pack(side="right", padx=6, pady=8)
        self.btn_admin  = nav_btn("ADMIN", "admin"); self.btn_admin.pack_forget()  # โชว์เฉพาะแอดมิน

        self.pages = {}
        self.btn_about = nav_btn("ABOUT", "about"); self.btn_about.pack(side="right", padx=6, pady=8)
        self.register("about",    AboutPage(self))
        self.register("home",     HomePage(self))
        self.register("profile",  ProfilePage(self))
        self.register("category", CategoryPage(self))
        self.register("cart",     CartPage(self))
        self.register("orders",   OrdersPage(self))
        self.register("admin",    AdminPage(self))   # มี role check ตอน on_show

    # NEW: force zoomed helper
    def _force_zoomed(self):
        def _z():
            try:
                self.state("zoomed")
            except:
                sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
                self.geometry(f"{sw}x{sh}+0+0")
        self.bind("<Map>", lambda e: self.after(50, _z))
        self.after(50, _z)

    # Navigation
    def register(self, key, widget: ctk.CTkFrame):
        self.pages[key] = widget
        widget.place(in_=self.body, relx=0, rely=0, relwidth=1, relheight=1)

    def go(self, key: str, replace: bool=False):
        if key not in self.pages: return
        self.pages[key].tkraise()
        if hasattr(self.pages[key], "on_show"): self.pages[key].on_show()

    # --- อัปเดตแถบผู้ใช้ด้านบน ---
    # ใน CTkMain.refresh_topbar_user()
    def refresh_topbar_user(self):
        u = self.user or {}
        img = ctk_img(u.get("avatar"), (32,32))
        name = u.get("username", "USERNAME")
        self.profile_btn.configure(text=f"  {name}", image=img)

        is_admin = (u.get("role") == "admin")

        # ปุ่ม ADMIN
        if is_admin:
            if not self.btn_admin.winfo_ismapped():
                self.btn_admin.pack(side="right", padx=6, pady=8)
        else:
            if self.btn_admin.winfo_ismapped():
                self.btn_admin.pack_forget()

        # ซ่อนปุ่ม CART/MY ORDERS สำหรับแอดมิน
        if is_admin:
            if self.btn_cart.winfo_ismapped():   self.btn_cart.pack_forget()
            if self.btn_orders.winfo_ismapped(): self.btn_orders.pack_forget()
        else:
            if not self.btn_orders.winfo_ismapped(): self.btn_orders.pack(side="right", padx=6, pady=8)
            if not self.btn_cart.winfo_ismapped():   self.btn_cart.pack(side="right", padx=6, pady=8)


    # session
    def login_ok(self, user_row):
        # บังคับเป็น dict เสมอ
        if isinstance(user_row, sqlite3.Row):
            user_row = dict(user_row)
        self.user = user_row
        self.refresh_topbar_user()
        self.go("home")

    def do_logout(self):
        if messagebox.askyesno("Logout", "Sign out?"):
            self.destroy()
            if self.on_logout: self.on_logout()

    # ---- cart utils ----
    # ใน CTkMain.cart_add()
    def cart_add(self, prod_row):
        # กันแอดมิน
        if self.user and (self.user.get("role") == "admin"):
            messagebox.showwarning("Permission", "Admin cannot add items to cart.")
            return
        # โค้ดเดิม
        for it in self.cart:
            if it['product_id']==prod_row['id']:
                it['qty']+=1; break
        else:
            self.cart.append({"product_id":prod_row['id'],"name":prod_row['name'],
                            "base_price":float(prod_row['base_price']),"qty":1})
        if "cart" in self.pages: self.pages["cart"].refresh_badges()


    def cart_change(self, pid: int, delta: int):
        new = []
        for it in self.cart:
            if it["product_id"] == pid:
                it["qty"] += delta
                if it["qty"] <= 0: continue
            new.append(it)
        self.cart = new

    def totals(self, code: str):
        subtotal = sum(it['base_price']*it['qty'] for it in self.cart)
        discount=0.0
        promo = self.db.find_promo(code) if code else None
        if promo:
            ptype=promo['type']; val=float(promo['value'] or 0); pid=promo['applies_to_product_id']
            if ptype in ("PERCENT_BILL","FLAT_BILL") and subtotal>=float(promo['min_spend'] or 0):
                discount = subtotal*(val/100.0) if ptype=="PERCENT_BILL" else min(val, subtotal)
            elif ptype in ("PERCENT_ITEM","FLAT_ITEM") and pid:
                target=sum(it['base_price']*it['qty'] for it in self.cart if it['product_id']==pid)
                discount = target*(val/100.0) if ptype=="PERCENT_ITEM" else min(val, target)
        base_after=max(0.0, subtotal-discount)
        vat=round(base_after*VAT_RATE,2)
        total=base_after+vat
        return subtotal, discount, vat, total
    # ในคลาส CTkMain (เช่น main.py)
    def login_ok(self, user_row):
        if isinstance(user_row, sqlite3.Row):
            user_row = dict(user_row)
        self.user = user_row
        self.refresh_topbar_user()
        
        # ถ้าเป็น admin ไปหน้า admin ทันที
        if self.user.get("role") == "admin":
            self.go("admin")
        else:
            self.go("home")


# ---------------- Pages ----------------
class HomePage(ctk.CTkFrame):
    """ปุ่มวงกลม FOOD / DRINK / DESSERT"""
    def __init__(self, app: CTkMain):
        super().__init__(app.body, fg_color=PALETTE["antique"]); self.app=app
        self.grid_columnconfigure((0,1,2), weight=1); self.grid_rowconfigure(1, weight=1)

        # big 3 buttons
        wrap = ctk.CTkFrame(self, fg_color=PALETTE["antique"])
        wrap.grid(row=1, column=0, columnspan=3, pady=20)
        def circle(text, catname):
            b = ctk.CTkButton(wrap, text=text, width=220, height=220, corner_radius=110,
                              fg_color=PALETTE["white"], text_color=PALETTE["bistre"],
                              hover_color=PALETTE["pale_taupe"],
                              font=ctk.CTkFont(size=22, weight="bold"),
                              command=lambda:self._go_cat(catname))
            return b
        circle("FOOD", "FOOD").grid(row=0, column=0, padx=40, pady=10)
        circle("DRINK", "DRINK").grid(row=0, column=1, padx=40, pady=10)
        circle("DESSERT", "DESSERT").grid(row=0, column=2, padx=40, pady=10)

        # bottom actions
        bottom = ctk.CTkFrame(self, fg_color="transparent"); bottom.grid(row=2, column=0, columnspan=3, pady=20)
        ctk.CTkButton(bottom, text="MY ORDERS", width=200, corner_radius=24,
                      fg_color=PALETTE["white"], text_color=PALETTE["bistre"],
                      command=lambda:self.app.go("orders")).pack(side="left", padx=8)
        ctk.CTkButton(bottom, text="CART", width=200, corner_radius=24,
                      fg_color=PALETTE["white"], text_color=PALETTE["bistre"],
                      command=lambda:self.app.go("cart")).pack(side="left", padx=8)
        ctk.CTkButton(bottom, text="LOGOUT", width=200, corner_radius=24,
                      fg_color=PALETTE["van_dyke"], text_color=PALETTE["antique"],
                      command=self.app.do_logout).pack(side="left", padx=8)

    def on_show(self): pass

    def _go_cat(self, name):
        cat_map = {r["name"]: r["id"] for r in self.app.db.categories()}
        cid = cat_map.get(name)
        page: CategoryPage = self.app.pages["category"]  # type: ignore
        page.set_category(cid, name)
        self.app.go("category")

class ProfilePage(ctk.CTkFrame):
    """Profile editor – 2-column layout, labels above fields, with Gender & Email."""
    def __init__(self, app: CTkMain):
        super().__init__(app.body, fg_color=PALETTE["antique"]); self.app=app

        ctk.CTkLabel(self, text="PROFILE", font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=PALETTE["bistre"]).pack(anchor="w", padx=20, pady=(10, 6))

        card = ctk.CTkFrame(self, fg_color=PALETTE["white"], corner_radius=16,
                            border_color=PALETTE["pale_taupe"], border_width=1)
        card.pack(fill="x", padx=20, pady=10)
        # กริดหลัก: คอลัมน์ซ้ายเป็นรูป+ปุ่ม, ขวาเป็นฟอร์มสองคอลัมน์
        card.grid_columnconfigure(0, weight=0)
        card.grid_columnconfigure(1, weight=1)

        # ---- Left (Avatar) ----
        left = ctk.CTkFrame(card, fg_color="transparent")
        left.grid(row=0, column=0, sticky="n", padx=16, pady=16)

        self.avatar_lbl = ctk.CTkLabel(left, text="", width=120, height=120,
                                       corner_radius=60, fg_color="#eee")
        self.avatar_lbl.pack(pady=(0, 10))
        ctk.CTkButton(left, text="Add Profile Pic", corner_radius=16,
                      fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                      command=self.change_avatar).pack()

        # ---- Right (Form) ----
        form = ctk.CTkFrame(card, fg_color="transparent")
        form.grid(row=0, column=1, sticky="ew", padx=10, pady=16)
        # สองคอลัมน์สมดุล
        form.grid_columnconfigure(0, weight=1, uniform="f")
        form.grid_columnconfigure(1, weight=1, uniform="f")

        def field(row, col, label, widget="entry"):
            ctk.CTkLabel(form, text=label, text_color=PALETTE["bistre"],
                         font=ctk.CTkFont(size=12, weight="bold")).grid(row=row*2, column=col, sticky="w", padx=6, pady=(0, 2))
            if widget == "entry":
                e = ctk.CTkEntry(form, corner_radius=10, fg_color="white", border_color=PALETTE["pale_taupe"])
                e.grid(row=row*2+1, column=col, sticky="ew", padx=6, pady=(0, 10))
                return e
            elif widget == "pwd":
                e = ctk.CTkEntry(form, show="•", corner_radius=10, fg_color="white", border_color=PALETTE["pale_taupe"])
                e.grid(row=row*2+1, column=col, sticky="ew", padx=6, pady=(0, 10))
                return e
            elif widget == "combo":
                e = ctk.CTkComboBox(form, values=["Male", "Female", "Other"])
                e.grid(row=row*2+1, column=col, sticky="ew", padx=6, pady=(0, 10))
                return e

        # แถว 0
        self.e_username = field(0, 0, "Username")
        self.e_email    = field(0, 1, "Email")
        # แถว 1
        self.e_phone    = field(1, 0, "Phone Number")
        self.e_birth    = field(1, 1, "Date of Birth (YYYY-MM-DD)")
        # แถว 2
        self.e_gender   = field(2, 0, "Gender", widget="combo")
        self.e_pass     = field(2, 1, "Password (leave blank to keep)", widget="pwd")

        # Save
        ctk.CTkButton(form, text="Save Change", corner_radius=18,
                      fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                      command=self.save).grid(row=6, column=1, sticky="e", padx=6, pady=(8, 0))

        ctk.CTkButton(self, text="HOME", width=160, corner_radius=22,
                      fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                      command=lambda:self.app.go("home")).pack(pady=8)

    def on_show(self):
        u = self.app.user or {}
        # เติมค่าลงช่อง — ไม่ล้างเพื่อให้ “คงอยู่”
        self.e_username.delete(0, "end"); self.e_username.insert(0, u.get("name") or u.get("username") or "")
        self.e_email.delete(0, "end");    self.e_email.insert(0, u.get("email") or "")
        self.e_phone.delete(0, "end");    self.e_phone.insert(0, u.get("phone") or "")
        self.e_birth.delete(0, "end");    self.e_birth.insert(0, u.get("birthdate") or "")
        self.e_gender.set((u.get("gender") or "Other"))
        # รูปโปรไฟล์
        img = ctk_img(u.get("avatar"), (120, 120))
        if img:
            self.avatar_lbl.configure(image=img, text=""); self.avatar_lbl.image = img
        else:
            self.avatar_lbl.configure(image=None, text="")

    def change_avatar(self):
        if not self.app.user: return
        f = filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg")])
        if not f: return
        os.makedirs(IMG_AVATARS_DIR, exist_ok=True)
        dest = os.path.join(IMG_AVATARS_DIR, os.path.basename(f))
        try:
            shutil.copy2(f, dest)
            self.app.db.update_profile(self.app.user["id"], {"avatar": dest})
            self.app.user = dict(self.app.db.conn.execute("SELECT * FROM users WHERE id=?", (self.app.user["id"],)).fetchone())
            self.on_show()
            # อัปเดตปุ่มบน Topbar ด้วย
            img = ctk_img(self.app.user.get("avatar"), (32, 32))
            self.app.profile_btn.configure(text=f"  {self.app.user.get('username')}", image=img)
        except Exception as e:
            messagebox.showerror("Avatar", f"Copy failed: {e}")

    def save(self):
        if not self.app.user: return
        fields = {
            "name": self.e_username.get().strip(),
            "email": self.e_email.get().strip(),
            "phone": self.e_phone.get().strip(),
            "birthdate": self.e_birth.get().strip(),
            "gender": self.e_gender.get().strip(),
        }
        self.app.db.update_profile(self.app.user["id"], fields)
        pwd = self.e_pass.get().strip()
        if pwd:
            self.app.db.change_password(self.app.user["id"], pwd)
        # รีเฟรชสถานะปัจจุบัน + ไม่ล้างช่อง (on_show จะแทนค่าใหม่)
        self.app.user = dict(self.app.db.conn.execute("SELECT * FROM users WHERE id=?", (self.app.user["id"],)).fetchone())
        messagebox.showinfo("Saved", "Profile updated.")
        self.on_show()

class CategoryPage(ctk.CTkFrame):
    def __init__(self, app: CTkMain):
        super().__init__(app.body, fg_color=PALETTE["antique"]); self.app=app
        self.cid=None; self.cname=""
        self._current_cols=None
        self._last_query=""
        self._resize_job=None
        self._rendering=False

        top = ctk.CTkFrame(self, fg_color="transparent"); top.pack(fill="x", padx=16, pady=(8,4))
        self.title_lbl = ctk.CTkLabel(top, text="FOOD", font=ctk.CTkFont(size=24, weight="bold"),
                                      text_color=PALETTE["bistre"], fg_color="transparent"); self.title_lbl.pack(side="left")

        self.search = ctk.CTkEntry(top, placeholder_text="Search menu..."); self.search.pack(side="right", padx=6)
        self.search.bind("<KeyRelease>", lambda e: self.render(force=True))

        btns = ctk.CTkFrame(self, fg_color="transparent"); btns.pack(fill="x", padx=16, pady=(2,8))
        def small(text, cb):
            return ctk.CTkButton(btns, text=text, width=120, corner_radius=18,
                                 fg_color=PALETTE["milk"], text_color=PALETTE["antique"], command=cb)
        small("HOME", lambda:self.app.go("home")).pack(side="left", padx=4)
        small("CART", lambda:self.app.go("cart")).pack(side="left", padx=4)

        self.gridf = ctk.CTkScrollableFrame(self, fg_color=PALETTE["antique"])
        self.gridf.pack(fill="both", expand=True, padx=16, pady=(0,12))

    def _cols_for(self, w:int)->int:
        if   w >= 1450: return 6
        elif w >= 1200: return 5
        elif w >= 980:  return 4
        else:           return 3

    def set_category(self, cid:int, name:str):
        self.cid=cid; self.cname=name; self.title_lbl.configure(text=name.upper())
        self.render(force=True)

    def on_show(self):
        self.after_idle(lambda: self.render(force=True))
        # debounce resize on toplevel (ไม่จับกับ gridf เพื่อลดลูป)
        def _debounce(_):
            if self._resize_job: self.after_cancel(self._resize_job)
            self._resize_job = self.after(150, self._maybe_rerender)
        self.winfo_toplevel().bind("<Configure>", _debounce)

    def _maybe_rerender(self):
        w = self.winfo_width() or self.gridf.winfo_width() or 0
        cols = self._cols_for(w)
        if cols != self._current_cols:
            self.render(force=True)

    def render(self, force=False):
        if not self.cid or self._rendering: return
        self._rendering=True
        try:
            q = (self.search.get() or "").strip().lower()
            w = self.winfo_width() or self.gridf.winfo_width() or 0
            cols = self._cols_for(w)

            if not force and q==self._last_query and cols==self._current_cols:
                return
            self._last_query = q
            self._current_cols = cols

            for wdg in self.gridf.winfo_children(): wdg.destroy()
            for i in range(cols):
                self.gridf.grid_columnconfigure(i, weight=1, uniform="prod")

            products = [p for p in self.app.db.products_by_cat(self.cid)
                        if q in (p["name"] or "").lower()]

            if not products:
                ctk.CTkLabel(self.gridf, text="No items found.",
                             text_color=PALETTE["bistre"], fg_color="transparent")\
                    .grid(row=0, column=0, padx=8, pady=16, sticky="w")
                return

            card_w, card_h = 220, 260
            img_size = (200, 120)
            btn_w, btn_h = 120, 32
            pad_x, pad_y = 10, 12
            is_admin = (self.app.user and self.app.user.get("role") == "admin")

            row = col = 0
            for p in products:
                card = ctk.CTkFrame(self.gridf, fg_color=PALETTE["white"], corner_radius=16,
                                    border_color=PALETTE["pale_taupe"], border_width=1,
                                    width=card_w, height=card_h)
                card.grid(row=row, column=col, padx=pad_x, pady=pad_y, sticky="n")
                card.grid_propagate(False)

                img = ctk_img(p["image"], img_size)
                ctk.CTkLabel(card, image=img, text=("No Image" if not img else ""),
                             fg_color="transparent").pack(pady=(10,6))
                ctk.CTkLabel(card, text=p["name"], font=ctk.CTkFont(size=13, weight="bold"),
                             text_color=PALETTE["bistre"], fg_color="transparent").pack(pady=(0,2))
                ctk.CTkLabel(card, text=f"{float(p['base_price']):,.2f} ฿",
                             text_color=PALETTE["milk"], fg_color="transparent").pack()
                if not is_admin:
                    ctk.CTkButton(card, text="ADD TO CART", width=btn_w, height=btn_h,
                                  corner_radius=14, fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                                  command=lambda pr=p: self.app.cart_add(pr)).pack(pady=(8,10))

                col += 1
                if col >= cols: col = 0; row += 1
        finally:
            self._rendering=False


class CartPage(ctk.CTkFrame):
    """ตะกร้า + QR + Upload Slip + Checkout (sticky footer buttons)"""
    def __init__(self, app: CTkMain):
        super().__init__(app.body, fg_color=PALETTE["antique"]); self.app=app
        self.slip_path = None
        self.receipt_path = None

        # ==== Title ====
        ctk.CTkLabel(self, text="YOUR CART", font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=PALETTE["bistre"], fg_color="transparent").pack(anchor="w", padx=16, pady=(10,2))

        # ==== Main 2-column layout ====
        main = ctk.CTkFrame(self, fg_color=PALETTE["antique"]); 
        main.pack(fill="both", expand=True, padx=16, pady=(0,8))
        main.grid_columnconfigure(0, weight=3)
        main.grid_columnconfigure(1, weight=2)
        main.grid_rowconfigure(0, weight=1)

        # Left: cart list
        self.listf = ctk.CTkScrollableFrame(main, fg_color=PALETTE["antique"])
        self.listf.grid(row=0, column=0, sticky="nsew", padx=(0,8))

        # Right: payment card (content scrollable + sticky footer)
        pay = ctk.CTkFrame(main, fg_color=PALETTE["white"], corner_radius=16,
                           border_color=PALETTE["pale_taupe"], border_width=1)
        pay.grid(row=0, column=1, sticky="nsew", padx=(8,0))
        pay.grid_rowconfigure(0, weight=1)     # content scroll
        pay.grid_rowconfigure(1, weight=0)     # footer stays visible
        pay.grid_columnconfigure(0, weight=1)

        # ---- Scrollable content on the right ----
        content = ctk.CTkScrollableFrame(pay, fg_color="white")
        content.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        content.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(content, text="QR CODE", text_color=PALETTE["bistre"],
                     fg_color="transparent").pack(pady=(6,4))
        if os.path.exists(self.app.qr_path):
            img = ctk_img(self.app.qr_path, (210,210))
            ctk.CTkLabel(content, image=img, text="", fg_color="transparent").pack()
        else:
            ctk.CTkLabel(content, text="(put qrcode.jpg in assets/images)", fg_color="transparent").pack()

        ctk.CTkLabel(content, text="UPLOAD SLIP", text_color=PALETTE["bistre"],
                     fg_color="transparent").pack(pady=(12,6))
        self.slip_preview = ctk.CTkLabel(content, width=220, height=220,
                                         fg_color="#f5f5f5", corner_radius=12, text="")
        self.slip_preview.pack()
        ctk.CTkButton(content, text="Upload Slip...", corner_radius=16,
                      fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                      command=self.upload).pack(pady=10)

        # Promo code row
        promo = ctk.CTkFrame(content, fg_color="transparent")
        promo.pack(fill="x", padx=6, pady=(6,2))
        ctk.CTkLabel(promo, text="Promo Code", fg_color="transparent").pack(side="left")
        self.e_code = ctk.CTkEntry(promo, width=140); self.e_code.pack(side="left", padx=6)
        self.btn_apply = ctk.CTkButton(promo, text="Apply", width=80, corner_radius=14,
                                       fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                                       command=self.apply_promo)
        self.btn_apply.pack(side="left", padx=6)

        # Totals (right aligned)
        totals = ctk.CTkFrame(content, fg_color="transparent")
        totals.pack(fill="x", padx=6, pady=(8,0))
        self.lbl_sub = ctk.CTkLabel(totals, text="", fg_color="transparent")
        self.lbl_dis = ctk.CTkLabel(totals, text="", fg_color="transparent")
        self.lbl_vat = ctk.CTkLabel(totals, text="", fg_color="transparent")
        self.lbl_tot = ctk.CTkLabel(totals, text="", font=ctk.CTkFont(size=16, weight="bold"),
                                    fg_color="transparent")
        for w in (self.lbl_sub, self.lbl_dis, self.lbl_vat, self.lbl_tot):
            w.pack(anchor="e")

        # ---- Sticky footer with buttons (always visible) ----
        footer = ctk.CTkFrame(pay, fg_color="white")
        footer.grid(row=1, column=0, sticky="ew", padx=8, pady=(0,8))
        footer.grid_columnconfigure((0,1), weight=1)

        self.btn_confirm = ctk.CTkButton(
            footer, text="CONFIRM ORDER", height=44, corner_radius=18,
            fg_color=PALETTE["van_dyke"], text_color=PALETTE["antique"],
            command=self.checkout
        )
        self.btn_confirm.grid(row=0, column=0, sticky="ew", padx=(0,6))

        self.btn_receipt = ctk.CTkButton(
            footer, text="DOWNLOAD RECEIPT (PDF)", height=44, corner_radius=18,
            fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
            state="disabled", command=self.open_receipt
        )
        self.btn_receipt.grid(row=0, column=1, sticky="ew", padx=(6,0))

        # Back/Home
        ctk.CTkButton(self, text="HOME", width=160, corner_radius=22,
                      fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                      command=lambda:self.app.go("home")).pack(pady=6)

    def on_show(self):
        self.refresh_badges()
        self.render_list()

    def refresh_badges(self):
        pass

    def render_list(self):
        for w in self.listf.winfo_children(): w.destroy()

        # Header
        header = ctk.CTkFrame(self.listf, fg_color="transparent")
        header.pack(fill="x", pady=(0, 4))
        cols = [("NAME", 260), ("QTY", 60), ("PRICE", 100), ("TOTAL", 120)]
        for title, w in cols:
            ctk.CTkLabel(header, text=title, width=w, anchor="w",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=PALETTE["bistre"]).pack(side="left",
                                                            padx=(8 if title=="NAME" else 0), pady=2)

        if not self.app.cart:
            ctk.CTkLabel(self.listf, text="Cart is empty.", text_color=PALETTE["bistre"],
                         fg_color="transparent").pack(pady=12)
        else:
            for it in self.app.cart:
                row = ctk.CTkFrame(self.listf, fg_color=PALETTE["white"], corner_radius=12,
                                   border_color=PALETTE["pale_taupe"], border_width=1)
                row.pack(fill="x", pady=4)

                total_line = it["base_price"] * it["qty"]
                ctk.CTkLabel(row, text=it["name"], width=260, anchor="w",
                             text_color=PALETTE["bistre"]).pack(side="left", padx=8, pady=8)
                ctk.CTkLabel(row, text=f"x{it['qty']}", width=60).pack(side="left")
                ctk.CTkLabel(row, text=f"{it['base_price']:,.2f} ฿", width=100).pack(side="left")
                ctk.CTkLabel(row, text=f"{total_line:,.2f} ฿", width=120).pack(side="left")

                ctr = ctk.CTkFrame(row, fg_color="transparent"); ctr.pack(side="right", padx=6)
                ctk.CTkButton(ctr, text="+", width=36, corner_radius=12,
                              fg_color=PALETTE["milk"], command=lambda pid=it["product_id"]: self._chg(pid, +1)).pack(side="left", padx=2)
                ctk.CTkButton(ctr, text="–", width=36, corner_radius=12,
                              fg_color=PALETTE["milk"], command=lambda pid=it["product_id"]: self._chg(pid, -1)).pack(side="left", padx=2)
                ctk.CTkButton(ctr, text="Remove", width=80, corner_radius=12,
                              fg_color=PALETTE["pale_taupe"], text_color=PALETTE["bistre"],
                              command=lambda pid=it["product_id"]: self._remove(pid)).pack(side="left", padx=4)

        self._update_totals()

    def _chg(self, pid, d): 
        self.app.cart_change(pid, d); 
        self.render_list()

    def _remove(self, pid):
        self.app.cart_change(pid, -9999); 
        self.render_list()

    # Apply promo button
    def apply_promo(self):
        self._update_totals()
        messagebox.showinfo("Promo", "Applied")

    def _update_totals(self):
        sub, dis, vat, tot = self.app.totals((self.e_code.get() or "").strip().upper())
        self.lbl_sub.configure(text=f"Subtotal: {sub:,.2f} ฿")
        self.lbl_dis.configure(text=f"Discount: {dis:,.2f} ฿")
        self.lbl_vat.configure(text=f"VAT {int(VAT_RATE*100)}%: {vat:,.2f} ฿")
        self.lbl_tot.configure(text=f"Total: {tot:,.2f} ฿")


    def upload(self):
        f = filedialog.askopenfilename(title="Select payment slip",
                                       filetypes=[("Images","*.png;*.jpg;*.jpeg;*.bmp;*.gif"),("All files","*.*")])
        if not f: return
        self.slip_path = f
        img = ctk_img(f, (220,220))
        self.slip_preview.configure(image=img, text=""); self.slip_preview.image = img

    def checkout(self):
        if not self.app.user:
            messagebox.showwarning("Login","Please sign in"); return
        if not self.app.cart:
            messagebox.showwarning("Cart","Cart empty"); return
        if not self.slip_path:
            messagebox.showwarning("Slip","Please upload payment slip before checkout"); return

        code = (self.e_code.get() or "").strip().upper()
        oid, sub, dis, vat, tot = self.app.db.create_order(
            user_id=self.app.user['id'],
            cart_items=self.app.cart,
            promo_code=code, payment_method="SLIP", payment_ref=self.slip_path
        )
        path = create_receipt_pdf(oid, self.app.db, self.app.user)
        self.receipt_path = path
        self.btn_receipt.configure(state="normal")
        messagebox.showinfo("Success", f"Order #{oid} placed.\nReceipt saved:\n{path}")

        self.app.cart.clear()
        self.slip_path=None
        self.slip_preview.configure(image=None, text="")
        self.render_list()
        self.app.go("orders")

    def open_receipt(self):
        if not self.receipt_path or not os.path.exists(self.receipt_path):
            messagebox.showinfo("Receipt", "No receipt available yet."); return
        try:
            if sys.platform.startswith("win"): os.startfile(self.receipt_path)
            elif sys.platform=="darwin": os.system(f"open '{self.receipt_path}'")
            else: os.system(f"xdg-open '{self.receipt_path}'")
        except:
            messagebox.showinfo("Receipt", f"Saved at: {self.receipt_path}")


class OrdersPage(ctk.CTkFrame):
    def __init__(self, app: CTkMain):
        super().__init__(app.body, fg_color=PALETTE["antique"]); self.app=app
        ctk.CTkLabel(self, text="ORDER HISTORY", font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=PALETTE["bistre"], fg_color="transparent").pack(anchor="w", padx=16, pady=(10,2))
        self.listf = ctk.CTkScrollableFrame(self, fg_color=PALETTE["antique"])
        self.listf.pack(fill="both", expand=True, padx=16, pady=8)
        ctk.CTkButton(self, text="HOME", width=160, corner_radius=22,
                      fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                      command=lambda:self.app.go("home")).pack(pady=8)

    def on_show(self): self.render()

    def render(self):
        for w in self.listf.winfo_children(): w.destroy()
        if not self.app.user: return
        for r in self.app.db.orders_of_user(self.app.user["id"]):
            row = ctk.CTkFrame(self.listf, fg_color=PALETTE["white"], corner_radius=12,
                               border_color=PALETTE["pale_taupe"], border_width=1)
            row.pack(fill="x", pady=6)
            ctk.CTkLabel(row, text=f"#{r['id']}  |  {r['order_datetime']}  |  TOTAL ฿{float(r['total']):,.2f}",
                        text_color=PALETTE["bistre"], fg_color="transparent").pack(side="left", padx=10, pady=10)
            ctk.CTkButton(row, text="DOWNLOAD RECEIPT", width=180, corner_radius=16,
                          fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                          command=lambda oid=r['id']: self._open(oid)).pack(side="right", padx=10, pady=10)

    def _open(self, oid:int):
        path=create_receipt_pdf(oid,self.app.db,self.app.user)
        try:
            if sys.platform.startswith("win"): os.startfile(path)
            elif sys.platform=="darwin": os.system(f"open '{path}'")
            else: os.system(f"xdg-open '{path}'")
        except: messagebox.showinfo("Receipt", f"Saved at: {path}")

# -------- Admin (customtkinter) ----------
class AdminPage(ctk.CTkFrame):
    def __init__(self, app: CTkMain):
        super().__init__(app.body, fg_color=PALETTE["antique"]); self.app=app
        self.current = "dashboard"  # เปิดมาที่ Dashboard ก่อน

        top = ctk.CTkFrame(self, fg_color="transparent"); top.pack(fill="x", padx=16, pady=(10,6))
        ctk.CTkLabel(top, text="ADMIN PANEL", font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=PALETTE["bistre"], fg_color="transparent").pack(side="left")

        def tab(text, key):
            return ctk.CTkButton(top, text=text, corner_radius=18, width=130,
                                 fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                                 hover_color=PALETTE["van_dyke"], command=lambda:self.show(key))
        self.btns = {
            "dashboard": tab("Dashboard","dashboard"),
            "products":  tab("Products","products"),
            "promos":    tab("Promotions","promos"),
            "orders":    tab("Orders","orders"),
            "reports":   tab("Reports","reports"),
        }
        for b in self.btns.values(): b.pack(side="left", padx=4)

        self.holder = ctk.CTkFrame(self, fg_color=PALETTE["antique"])
        self.holder.pack(fill="both", expand=True, padx=16, pady=(0,10))

        # views
        self.v_dash     = AdminDashboard(self.holder, self.app.db)
        self.v_products = AdminProducts(self.holder, self.app.db)
        self.v_promos   = AdminPromos(self.holder, self.app.db)
        self.v_orders   = AdminOrders(self.holder, self.app.db)
        self.v_reports  = AdminReports(self.holder, self.app.db)

        ctk.CTkButton(self, text="HOME", width=160, corner_radius=22,
                      fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                      command=lambda:self.app.go("home")).pack(pady=6)

    def on_show(self):
        # role guard
        if not self.app.user or (self.app.user.get("role") != "admin"):
            messagebox.showwarning("Permission","Admin only")
            self.app.go("home"); return
        self.show(self.current)

    def show(self, key):
        for w in self.holder.winfo_children(): w.pack_forget()
        self.current = key
        view = {
            "dashboard": self.v_dash,
            "products":  self.v_products,
            "promos":    self.v_promos,
            "orders":    self.v_orders,
            "reports":   self.v_reports,
        }[key]
        view.pack(fill="both", expand=True)
        if hasattr(view, "refresh"): view.refresh()


# --- Admin sub-views ---
class AdminProducts(ctk.CTkFrame):
    def __init__(self, master, db: DB):
        super().__init__(master, fg_color=PALETTE["antique"]); self.db=db
        top = ctk.CTkFrame(self, fg_color="transparent"); top.pack(fill="x")
        ctk.CTkButton(top, text="ADD", corner_radius=16, fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                      command=self.add).pack(side="left", padx=6, pady=6)
        ctk.CTkButton(top, text="REFRESH", corner_radius=16, fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                      command=self.refresh).pack(side="left", padx=6, pady=6)
        self.listf = ctk.CTkScrollableFrame(self, fg_color=PALETTE["antique"]); self.listf.pack(fill="both", expand=True)

    def refresh(self):
        for w in self.listf.winfo_children(): w.destroy()
        rows = self.db.list_products()
        for r in rows:
            row = ctk.CTkFrame(self.listf, fg_color=PALETTE["white"], corner_radius=12,
                               border_color=PALETTE["pale_taupe"], border_width=1)
            row.pack(fill="x", pady=4)
            txt = f"{r['id']:>3} | {r['name']} | {r['category_name'] or '-'} | ฿{float(r['base_price']):.2f} | active={r['is_active']}"
            ctk.CTkLabel(row, text=txt, text_color=PALETTE["bistre"], fg_color="transparent").pack(side="left", padx=10, pady=10)
            ctk.CTkButton(row, text="EDIT", width=70, corner_radius=14,
                          fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                          command=lambda pid=r["id"]: self.edit(pid)).pack(side="right", padx=6, pady=8)
            ctk.CTkButton(row, text="DELETE", width=80, corner_radius=14,
                          fg_color=PALETTE["pale_taupe"], text_color=PALETTE["bistre"],
                          command=lambda pid=r["id"]: self.delete(pid)).pack(side="right", padx=6, pady=8)

    def add(self):  ProductEditorCTk(self, self.db, None, self.refresh)
    def edit(self, pid): ProductEditorCTk(self, self.db, pid, self.refresh)
    def delete(self, pid):
        if messagebox.askyesno("Confirm", "Delete product?"):
            self.db.delete_product(pid); self.refresh()

class ProductEditorCTk(ctk.CTkToplevel):
    def __init__(self, master, db: DB, pid, on_done):
        super().__init__(master); self.db=db; self.pid=pid; self.on_done=on_done
        self.title("Product Editor"); self.geometry("520x420"); self.configure(fg_color=PALETTE["antique"])
        frm=ctk.CTkFrame(self, fg_color=PALETTE["antique"]); frm.pack(fill="both",expand=True,padx=16,pady=16)
        frm.grid_columnconfigure(1, weight=1)

        def row(r, label, entry=True):
            ctk.CTkLabel(frm, text=label, text_color=PALETTE["bistre"], fg_color="transparent").grid(row=r, column=0, sticky="e", padx=6, pady=6)
            w = ctk.CTkEntry(frm) if entry else ctk.CTkComboBox(frm, values=[])
            w.grid(row=r, column=1, sticky="ew", padx=6, pady=6); return w

        self.en = row(0,"Name")
        cats = self.db.categories(); self.cat_map = {c["name"]: c["id"] for c in cats}
        self.ec = ctk.CTkComboBox(frm, values=list(self.cat_map.keys())); self.ec.grid(row=1,column=1,sticky="ew",padx=6,pady=6)
        ctk.CTkLabel(frm, text="Category", text_color=PALETTE["bistre"], fg_color="transparent").grid(row=1, column=0, sticky="e", padx=6, pady=6)
        self.ep = row(2,"Base Price"); self.ei = row(3,"Image path"); self.ea = row(4,"Active (1/0)")
        ctk.CTkButton(frm, text="Choose Image", corner_radius=14,
                      fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                      command=self.pick).grid(row=3, column=2, padx=6)
        ctk.CTkButton(frm, text="Save", height=40, corner_radius=18,
                      fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                      command=self.save).grid(row=5, column=1, sticky="e", pady=(12,0))

        if pid:
            r=db.conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
            if r:
                self.en.insert(0, r['name'])
                cname=db.conn.execute("SELECT name FROM categories WHERE id=?", (r['category_id'],)).fetchone()
                self.ec.set(cname['name'] if cname else "")
                self.ep.insert(0, str(r['base_price'])); self.ei.insert(0, r['image'] or ""); self.ea.insert(0, str(r['is_active']))

    def pick(self):
        f=filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg")])
        if not f: return
        dest=os.path.join(IMG_PRODUCTS_DIR, os.path.basename(f))
        try: shutil.copy2(f, dest); self.ei.delete(0,"end"); self.ei.insert(0,dest)
        except Exception as e: messagebox.showerror("Image", f"Copy failed: {e}")

    def save(self):
        name=self.en.get().strip(); cat=self.ec.get().strip()
        price=float(self.ep.get().strip() or 0); img=self.ei.get().strip(); act=int(self.ea.get().strip() or 1)
        if not name or not cat: messagebox.showerror("Error","Name/Category required"); return
        self.db.upsert_product(self.pid, name, self.cat_map[cat], price, img, act)
        messagebox.showinfo("Saved","Product saved"); self.on_done(); self.destroy()

class AdminPromos(ctk.CTkFrame):
    def __init__(self, master, db: DB):
        super().__init__(master, fg_color=PALETTE["antique"]); self.db=db
        top=ctk.CTkFrame(self, fg_color="transparent"); top.pack(fill="x")
        ctk.CTkButton(top, text="ADD", corner_radius=16, fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                      command=self.add).pack(side="left", padx=6, pady=6)
        ctk.CTkButton(top, text="REFRESH", corner_radius=16, fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                      command=self.refresh).pack(side="left", padx=6, pady=6)
        self.listf = ctk.CTkScrollableFrame(self, fg_color=PALETTE["antique"]); self.listf.pack(fill="both", expand=True)

    def refresh(self):
        for w in self.listf.winfo_children(): w.destroy()
        for r in self.db.list_promotions():
            row = ctk.CTkFrame(self.listf, fg_color=PALETTE["white"], corner_radius=12,
                               border_color=PALETTE["pale_taupe"], border_width=1)
            row.pack(fill="x", pady=4)
            txt = f"{r['id']} | {r['code']} | {r['type']} | v={r['value']} | min={r['min_spend']} | {r['start_at']} ~ {r['end_at']} | prod={r['applies_to_product_id'] or '-'} | active={r['is_active']}"
            ctk.CTkLabel(row, text=txt, text_color=PALETTE["bistre"], fg_color="transparent").pack(side="left", padx=10, pady=10)
            ctk.CTkButton(row, text="EDIT", width=70, corner_radius=14,
                          fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                          command=lambda pid=r["id"]: self.edit(pid)).pack(side="right", padx=6, pady=8)
            ctk.CTkButton(row, text="DELETE", width=80, corner_radius=14,
                          fg_color=PALETTE["pale_taupe"], text_color=PALETTE["bistre"],
                          command=lambda pid=r["id"]: self.delete(pid)).pack(side="right", padx=6, pady=8)

    def add(self):  PromoEditorCTk(self, self.db, None, self.refresh)
    def edit(self, pid): PromoEditorCTk(self, self.db, pid, self.refresh)
    def delete(self, pid):
        if messagebox.askyesno("Confirm","Delete promotion?"):
            self.db.delete_promotion(pid); self.refresh()

class PromoEditorCTk(ctk.CTkToplevel):
    def __init__(self, master, db: DB, pid, on_done):
        super().__init__(master); self.db=db; self.pid=pid; self.on_done=on_done
        self.title("Promotion Editor"); self.geometry("640x420"); self.configure(fg_color=PALETTE["antique"])
        frm=ctk.CTkFrame(self, fg_color=PALETTE["antique"]); frm.pack(fill="both",expand=True,padx=16,pady=16)
        frm.grid_columnconfigure(1, weight=1)
        def row(r,label):
            ctk.CTkLabel(frm,text=label,text_color=PALETTE["bistre"], fg_color="transparent").grid(row=r,column=0,sticky="e",padx=6,pady=6)
            e=ctk.CTkEntry(frm); e.grid(row=r,column=1,sticky="ew",padx=6,pady=6); return e
        self.e_code=row(0,"Code"); self.e_type=row(1,"Type (PERCENT_BILL/FLAT_BILL/PERCENT_ITEM/FLAT_ITEM)")
        self.e_val=row(2,"Value"); self.e_min=row(3,"Min Spend")
        self.e_start=row(4,"Start (YYYY-MM-DD HH:MM:SS)"); self.e_end=row(5,"End")
        self.e_prod=row(6,"Applies to Product ID (for *_ITEM)"); self.e_act=row(7,"Active 1/0")
        ctk.CTkButton(frm,text="Save",height=40,corner_radius=18,
                      fg_color=PALETTE["milk"],text_color=PALETTE["antique"],
                      command=self.save).grid(row=8,column=1,sticky="e",pady=(12,0))
        if pid:
            r=db.conn.execute("SELECT * FROM promotions WHERE id=?", (pid,)).fetchone()
            if r:
                self.e_code.insert(0,r['code']); self.e_type.insert(0,r['type'])
                self.e_val.insert(0,str(r['value'])); self.e_min.insert(0,str(r['min_spend']))
                self.e_start.insert(0,r['start_at']); self.e_end.insert(0,r['end_at'])
                self.e_prod.insert(0,"" if r['applies_to_product_id'] is None else str(r['applies_to_product_id']))
                self.e_act.insert(0,str(r['is_active']))
    def save(self):
        code=self.e_code.get().strip().upper(); ptype=self.e_type.get().strip()
        value=float(self.e_val.get().strip() or 0); min_spend=float(self.e_min.get().strip() or 0)
        start=self.e_start.get().strip() or (dt.now().strftime("%Y-%m-%d 00:00:00"))
        end=self.e_end.get().strip() or (dt.now()+timedelta(days=365)).strftime("%Y-%m-%d 23:59:59")
        prod=self.e_prod.get().strip(); applies=int(prod) if prod.isdigit() else None
        act=int(self.e_act.get().strip() or 1)
        if not code or ptype not in ("PERCENT_BILL","FLAT_BILL","PERCENT_ITEM","FLAT_ITEM"):
            messagebox.showerror("Error","Invalid code/type"); return
        cur = self.db.conn.cursor()
        if self.pid:
            cur.execute("""UPDATE promotions SET code=?,type=?,value=?,min_spend=?,start_at=?,end_at=?,applies_to_product_id=?,is_active=? WHERE id=?""",
                        (code,ptype,value,min_spend,start,end,applies,act,self.pid))
        else:
            cur.execute("""INSERT INTO promotions(code,type,value,min_spend,start_at,end_at,applies_to_product_id,is_active)
                           VALUES(?,?,?,?,?,?,?,?)""", (code,ptype,value,min_spend,start,end,applies,act))
        self.db.conn.commit()
        messagebox.showinfo("Saved","Promotion saved"); self.on_done(); self.destroy()
def money(x):
    return f"{float(x or 0):,.2f}"
class AdminOrders(ctk.CTkFrame):
    def money(x): return f"{float(x or 0):,.2f}"
    def __init__(self, master, db: DB):
        super().__init__(master, fg_color=PALETTE["antique"]); self.db=db
        top=ctk.CTkFrame(self, fg_color="transparent"); top.pack(fill="x")
        ctk.CTkButton(top, text="REFRESH", corner_radius=16, fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                      command=self.refresh).pack(side="left", padx=6, pady=6)
        ctk.CTkLabel(top, text="Auto refresh 3s", text_color=PALETTE["bistre"], fg_color="transparent").pack(side="left", padx=6, pady=6)
        body = ctk.CTkFrame(self, fg_color=PALETTE["antique"]); body.pack(fill="both", expand=True, padx=4, pady=4)
        body.grid_columnconfigure((0,1), weight=1); body.grid_rowconfigure(0, weight=1)
        self.left = ctk.CTkScrollableFrame(body, fg_color=PALETTE["antique"]); self.left.grid(row=0, column=0, sticky="nsew", padx=(0,6))
        self.right= ctk.CTkFrame(body, fg_color=PALETTE["antique"]); self.right.grid(row=0, column=1, sticky="nsew", padx=(6,0))
        self.lbl = ctk.CTkLabel(self.right, text="", fg_color="transparent"); self.lbl.pack(anchor="w", pady=(6,2))
        self.itemsf = ctk.CTkScrollableFrame(self.right, fg_color=PALETTE["antique"]); self.itemsf.pack(fill="both", expand=True)
        ctr = ctk.CTkFrame(self.right, fg_color="transparent"); ctr.pack(fill="x", pady=6)
        self.cb = ctk.CTkComboBox(ctr, values=["PAID","PREPARING","READY","COMPLETED","CANCELLED"]); self.cb.pack(side="left", padx=6)
        ctk.CTkButton(ctr, text="Set Status", corner_radius=14, fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                      command=self.set_status).pack(side="left", padx=6)
        ctk.CTkButton(ctr, text="Open Slip", corner_radius=14, fg_color=PALETTE["pale_taupe"], text_color=PALETTE["bistre"],
                      command=self.open_slip).pack(side="left", padx=6)
        self.selected_oid=None; self._job=None

    def on_show(self): self.refresh(); self._schedule()
    def _schedule(self):
        if self._job: self.after_cancel(self._job)
        self._job = self.after(3000, self._tick)
    def _tick(self): self.refresh(keep=True); self._schedule()

    def refresh(self, keep=False):
        cur_sel = self.selected_oid if keep else None
        for w in self.left.winfo_children(): w.destroy()
        for r in self.db.list_orders(limit=300):
            card = ctk.CTkFrame(self.left, fg_color=PALETTE["white"], corner_radius=10,
                                border_color=PALETTE["pale_taupe"], border_width=1)
            card.pack(fill="x", pady=4)
            ctk.CTkLabel(card, text=f"#{r['id']} | {r['order_datetime']} | {r['username'] or '-'} | ฿{float(r['total'] or 0):,.2f}",
                         text_color=PALETTE["bistre"], fg_color="transparent").pack(side="left", padx=8, pady=8)
            ctk.CTkButton(card, text="DETAIL", width=80, corner_radius=14,
                          fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                          command=lambda oid=r['id']: self.show_detail(oid)).pack(side="right", padx=8, pady=8)
            if cur_sel and cur_sel==r['id']: self.show_detail(cur_sel)

    def show_detail(self, oid):
        self.selected_oid = oid
        o, items, _ = self.db.order_detail(oid)
        self.lbl.configure(text=f"Order #{oid} | {o['order_datetime']} | TOTAL ฿{float(o['total']):,.2f} | STATUS {o['status']}")
        self.cb.set(o['status'] or "PAID")
        for w in self.itemsf.winfo_children(): w.destroy()
        for it in items:
            line = float(it['unit_price']) * int(it['qty'])
            ctk.CTkLabel(self.itemsf, text=f"{it['product_name']}  x{it['qty']}  —  ฿{line:,.2f}",
                         text_color=PALETTE["bistre"], fg_color="transparent").pack(anchor="w", padx=8, pady=2)

    def open_slip(self):
        if not self.selected_oid: return
        pays = self.db.order_payments(self.selected_oid)
        slip_path = None
        for p in pays:
            if (p['method'] or "").upper() == "SLIP":
                slip_path = p['ref']; break
        if not slip_path or not os.path.exists(slip_path):
            messagebox.showinfo("Slip", "No slip found for this order."); return
        try:
            if sys.platform.startswith("win"): os.startfile(slip_path)
            elif sys.platform=="darwin": os.system(f"open '{slip_path}'")
            else: os.system(f"xdg-open '{slip_path}'")
        except Exception as e:
            messagebox.showerror("Slip", f"Cannot open: {e}")

    def set_status(self):
        if not self.selected_oid: return
        st = (self.cb.get() or "PAID").upper()
        self.db.set_order_status(self.selected_oid, st)
        self.refresh(keep=True)

class AdminReports(ctk.CTkFrame):
    def __init__(self, master, db: DB):
        super().__init__(master, fg_color=PALETTE["antique"]); self.db=db

        top=ctk.CTkFrame(self, fg_color="transparent"); top.pack(fill="x", pady=(0,6))
        self.e_start = ctk.CTkEntry(top, placeholder_text="YYYY-MM-DD"); self.e_start.pack(side="left", padx=6)
        self.e_end   = ctk.CTkEntry(top, placeholder_text="YYYY-MM-DD"); self.e_end.pack(side="left", padx=6)

        # ค่าเริ่มต้น = ตั้งแต่ต้นเดือนนี้ถึงวันนี้
        today = dt.now()
        self.e_start.insert(0, today.strftime("%Y-%m-01"))
        self.e_end.insert(0, today.strftime("%Y-%m-%d"))

        ctk.CTkButton(top, text="Apply", corner_radius=16,
                      fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                      command=self.run_apply).pack(side="left", padx=(6,12))

        def btn(txt, cb):
            ctk.CTkButton(top, text=txt, corner_radius=16,
                          fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                          command=cb).pack(side="left", padx=6)
        btn("Daily Total",  self.run_daily)
        btn("By Category",  self.run_cat)
        btn("By Product",   self.run_prod)
        btn("Top Customers",self.run_top)
        btn("By Month",     self.run_monthly)
        btn("By Year",      self.run_yearly)

        self.status = ctk.CTkLabel(self, text="", text_color="#b00020",
                                   fg_color="transparent")  # โชว์ error ถ้ามี
        self.status.pack(fill="x", padx=10)

        self.out = ctk.CTkScrollableFrame(self, fg_color=PALETTE["antique"])
        self.out.pack(fill="both", expand=True, pady=6)

    # ---------- helpers ----------
    def _range(self):
        s = (self.e_start.get().strip() or dt.now().strftime("%Y-%m-01"))
        e = (self.e_end.get().strip()   or dt.now().strftime("%Y-%m-%d"))
        return s, e

    def _clear(self):
        for w in self.out.winfo_children(): w.destroy()

    def _fill(self, headers, rows):
        self._clear()
        # header
        head = ctk.CTkFrame(self.out, fg_color="transparent"); head.pack(fill="x")
        widths = [ max(120, int(900/len(headers))) ]*len(headers)
        for h, w in zip(headers, widths):
            ctk.CTkLabel(head, text=h, width=w, anchor="w",
                         text_color=PALETTE["bistre"], fg_color="transparent",
                         font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=6, pady=4)
        # rows
        if not rows:
            ctk.CTkLabel(self.out, text="(No data)", fg_color="transparent",
                         text_color=PALETTE["bistre"]).pack(pady=8)
            return
        for r in rows:
            row = ctk.CTkFrame(self.out, fg_color=PALETTE["white"], corner_radius=10,
                               border_color=PALETTE["pale_taupe"], border_width=1)
            row.pack(fill="x", pady=4)
            for val, w in zip(r, widths):
                ctk.CTkLabel(row, text=str(val), width=w, anchor="w",
                             text_color=PALETTE["bistre"], fg_color="transparent").pack(side="left", padx=6, pady=6)

    def _safe_run(self, fn, headers):
        try:
            self.status.configure(text="")
            rows = fn()
            self._fill(headers, rows)
        except Exception as e:
            self._clear()
            self.status.configure(text=f"ERROR: {e}")

    # ---------- actions ----------
    def run_apply(self):
        def work():
            s,e=self._range()
            row = self.db.conn.execute(
                "SELECT COUNT(*) AS orders, COALESCE(SUM(total),0) AS revenue "
                "FROM orders WHERE order_datetime BETWEEN ? AND ?",
                (s+" 00:00:00", e+" 23:59:59")
            ).fetchone()
            return [(f"{s} ~ {e}", int(row['orders'] or 0), f"{float(row['revenue'] or 0):,.2f}")]
        self._safe_run(work, ["DATE RANGE","ORDERS","REVENUE (฿)"])

    def run_daily(self):
        def work():
            s,e=self._range()
            data=self.db.report_total_by_date(s,e)
            return [(r['d'], f"{(r['total'] or 0):,.2f}") for r in data]
        self._safe_run(work, ["DATE","TOTAL (฿)"])

    def run_cat(self):
        def work():
            s,e=self._range()
            data=self.db.report_by_category(s,e)
            return [(r['category'], f"{(r['sales'] or 0):,.2f}") for r in data]
        self._safe_run(work, ["CATEGORY","SALES (฿)"])

    def run_prod(self):
        def work():
            s, e = self._range()
            data = self.db.report_by_product(s, e)  # qty DESC แล้ว
            rows = []
            for i, r in enumerate(data, start=1):
                # ไอคอนลำดับ
                if   i == 1: rank = "🥇"
                elif i == 2: rank = "🥈"
                elif i == 3: rank = "🥉"
                elif i in (4, 5): rank = "🏅"
                else: rank = str(i)
                rows.append((rank, r['product'], int(r['qty'] or 0), f"{(r['sales'] or 0):,.2f}"))
            return rows
        self._safe_run(work, ["RANK", "PRODUCT", "QTY", "SALES (฿)"])


    def run_top(self):
        def work():
            s,e=self._range()
            data=self.db.report_top_customers(s,e)
            return [(r['username'] or "", r['name'] or "", f"{(r['total'] or 0):,.2f}") for r in data]
        self._safe_run(work, ["USERNAME","NAME","TOTAL (฿)"])

    def run_monthly(self):
        def work():
            s,e=self._range()
            data=self.db.report_sales_monthly(s,e)
            return [(r['period'], f"{(r['revenue'] or 0):,.2f}", int(r['orders'] or 0), f"{(r['aov'] or 0):,.2f}") for r in data]
        self._safe_run(work, ["PERIOD (YYYY-MM)","REVENUE (฿)","ORDERS","AOV (฿)"])

    def run_yearly(self):
        def work():
            s,e=self._range()
            data=self.db.report_sales_yearly(s,e)
            return [(r['period'], f"{(r['revenue'] or 0):,.2f}", int(r['orders'] or 0), f"{(r['aov'] or 0):,.2f}") for r in data]
        self._safe_run(work, ["YEAR","REVENUE (฿)","ORDERS","AOV (฿)"])


class AdminDashboard(ctk.CTkFrame):
    """
    Dashboard แบบช่วงวันที่ + กราฟฝั่งขวา:
    - ช่อง Start (DD/MM/YYYY) และ End (DD/MM/YY)
    - ปุ่ม Apply
    - ซ้าย: การ์ด 3 ใบ (Range / Monthly / All-time)
    - ขวา: กราฟ bar รายวันของช่วงวันที่ที่เลือก
    """
    def __init__(self, master, db: DB):
        super().__init__(master, fg_color=PALETTE["antique"]); self.db = db

        # ====== โครง 2 คอลัมน์ (ซ้ายการ์ด / ขวากราฟ) ======
        main = ctk.CTkFrame(self, fg_color="transparent"); main.pack(fill="both", expand=True)
        main.grid_columnconfigure(0, weight=3)   # ซ้ายกว้าง
        main.grid_columnconfigure(1, weight=2)   # ขวากราฟ
        main.grid_rowconfigure(1, weight=1)

        # ---------- แถวฟิลเตอร์ (บนสุด ชิดซ้าย) ----------
        top = ctk.CTkFrame(main, fg_color="transparent")
        top.grid(row=0, column=0, sticky="w", padx=6, pady=(0,6))
        self.e_start = ctk.CTkEntry(top, width=160, placeholder_text="DD/MM/YYYY")
        self.e_end   = ctk.CTkEntry(top, width=160, placeholder_text="DD/MM/YY")
        self.e_start.pack(side="left", padx=(6,4))
        ctk.CTkLabel(top, text="to", fg_color="transparent",
                     text_color=PALETTE["bistre"]).pack(side="left", padx=2)
        self.e_end.pack(side="left", padx=(4,6))
        ctk.CTkButton(top, text="Apply", corner_radius=16,
                      fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                      command=self.refresh).pack(side="left", padx=6)

        # ---------- พื้นที่ซ้าย: การ์ด ----------
        self.left_wrap = ctk.CTkFrame(main, fg_color="transparent")
        self.left_wrap.grid(row=1, column=0, sticky="nsew", padx=(6,8), pady=(0,6))

        self._cards = []
        for color_name, title in [("#fcc19f", "Daily Sales"),
                                  ("#f29c71", "Monthly Sales"),
                                  ("#f9ae54", "Sales Overview")]:
            card = ctk.CTkFrame(self.left_wrap, fg_color=PALETTE["white"],
                                corner_radius=16, border_color=PALETTE["pale_taupe"], border_width=1)
            card.pack(fill="x", pady=8)
            tag = ctk.CTkLabel(card, text=title, fg_color=color_name,
                               corner_radius=12, text_color=PALETTE["bistre"], padx=10, pady=4)
            tag.pack(anchor="w", padx=10, pady=(10,0))
            body = ctk.CTkFrame(card, fg_color="transparent"); body.pack(fill="x", padx=10, pady=10)
            o_lbl = ctk.CTkLabel(body, text="", anchor="w")
            r_lbl = ctk.CTkLabel(body, text="", anchor="w", font=ctk.CTkFont(weight="bold"))
            o_lbl.pack(anchor="w"); r_lbl.pack(anchor="w")
            self._cards.append((tag, o_lbl, r_lbl))

        # ---------- พื้นที่ขวา: กราฟ ----------
        self.right_wrap = ctk.CTkFrame(main, fg_color=PALETTE["white"],
                                       corner_radius=16, border_color=PALETTE["pale_taupe"], border_width=1)
        self.right_wrap.grid(row=1, column=1, sticky="nsew", padx=(8,6), pady=(0,6))
        self.right_wrap.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self.right_wrap, text="Sales Chart", text_color=PALETTE["bistre"],
                     font=ctk.CTkFont(size=14, weight="bold"),
                     fg_color="transparent").grid(row=0, column=0, sticky="w", padx=10, pady=(10,0))
        self.chart_frame = ctk.CTkFrame(self.right_wrap, fg_color="white")
        self.chart_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)

        # ค่า default วันนี้
        today = dt.now().strftime("%d/%m/%Y")
        self.e_start.insert(0, today)
        self.e_end.insert(0, today)

        # ตัวแปรกราฟ
        self._fig = None
        self._canvas = None

        self.refresh()

    # -------- helpers --------
    def _parse_dmy(self, s: str) -> dt:
        """รับ DD/MM/YYYY หรือ DD/MM/YY (YY -> 2000+YY)"""
        s = (s or "").strip()
        for fmt in ("%d/%m/%Y", "%d/%m/%y"):
            try:
                d = dt.strptime(s, fmt)
                if fmt == "%d/%m/%y" and d.year < 2000:
                    d = d.replace(year=d.year + 2000)
                return d
            except Exception:
                pass
        return dt.now()

    def _draw_chart(self, rows, title):
        # rows: list of sqlite3.Row with keys d (YYYY-MM-DD), total
        # เตรียมข้อมูล
        xs = [r["d"] for r in rows]
        ys = [float(r["total"] or 0) for r in rows]
        if not xs:  # ถ้าไม่มีข้อมูล ให้ทำแกนว่าง
            xs = [""]
            ys = [0.0]

        # ล้างกราฟเก่า
        for w in self.chart_frame.winfo_children(): w.destroy()

        self._fig = Figure(figsize=(5, 3), dpi=100)  # ขนาดพอดีช่องขวา
        ax = self._fig.add_subplot(111)
        ax.bar(xs, ys, color="#DEC283")  # โทนน้ำตาลเข้ม
        ax.set_title(title)
        ax.set_ylabel("Revenue (฿)")
        ax.set_xlabel("Date")
        ax.tick_params(axis='x', rotation=45)

        self._canvas = FigureCanvasTkAgg(self._fig, master=self.chart_frame)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(fill="both", expand=True)

    def refresh(self):
        # ---- parse inputs ----
        sd = self._parse_dmy(self.e_start.get())
        ed = self._parse_dmy(self.e_end.get())
        if ed < sd: sd, ed = ed, sd

        start_date = sd.strftime("%Y-%m-%d")
        end_date   = ed.strftime("%Y-%m-%d")
        range_txt  = f"{sd.strftime('%d/%m/%Y')} ~ {ed.strftime('%d/%m/%Y')}"

        # ---------- 1) Range ----------
        row = self.db.conn.execute(
            "SELECT COUNT(*) AS orders, COALESCE(SUM(total),0) AS revenue "
            "FROM orders WHERE order_datetime BETWEEN ? AND ?",
            (start_date + " 00:00:00", end_date + " 23:59:59")
        ).fetchone()
        r_orders, r_rev = int(row["orders"] or 0), float(row["revenue"] or 0)

        # ---------- 2) Monthly (อิงเดือน start) ----------
        ym = sd.strftime("%Y-%m")
        row = self.db.conn.execute(
            "SELECT COUNT(*) AS orders, COALESCE(SUM(total),0) AS revenue "
            "FROM orders WHERE substr(order_datetime,1,7)=?",
            (ym,)
        ).fetchone()
        m_orders, m_rev = int(row["orders"] or 0), float(row["revenue"] or 0)

        # ---------- 3) All-time ----------
        row = self.db.conn.execute(
            "SELECT COUNT(*) AS orders, COALESCE(SUM(total),0) AS revenue FROM orders"
        ).fetchone()
        a_orders, a_rev = int(row["orders"] or 0), float(row["revenue"] or 0)

        # ---------- render cards ----------
        (tag1, o1, r1), (tag2, o2, r2), (tag3, o3, r3) = self._cards
        tag1.configure(text=("Daily Sales" if sd.date() == ed.date() else "Range Sales"))
        o1.configure(text=f"ORDER : {r_orders} Orders  ({range_txt})")
        r1.configure(text=f"TOTAL : {r_rev:,.2f} Baht")

        o2.configure(text=f"ORDER : {m_orders} Orders  ({ym})")
        r2.configure(text=f"TOTAL : {m_rev:,.2f} Baht")

        o3.configure(text=f"ORDER (all-time): {a_orders} Orders")
        r3.configure(text=f"TOTAL (all-time): {a_rev:,.2f} Baht")

        # ---------- draw chart on the right (รายวันในช่วง) ----------
        rows = self.db.report_total_by_date(start_date, end_date)  # ใช้ฟังก์ชันใน DB ที่มีอยู่แล้ว
        self._draw_chart(rows, f"Revenue per Day ({range_txt})")

# ================== About Page ==================
# === ตั้งค่าพาธรูปให้ตรงไฟล์ของคุณ ===
# ถ้าไฟล์ชื่อ contact.jpg ตามที่ส่งมา ให้ตั้งแบบนี้:
ABOUT_IMG_PATH = os.path.join(IMG_DIR, r"C:\Users\thatt\Downloads\pg design (5).jpg")  # หรือชี้เป็นพาธเต็มของไฟล์ที่คุณใช้

class AboutPage(ctk.CTkFrame):
    """หน้า ABOUT US: แสดงภาพเต็มพื้นที่ + ปุ่มกลับ"""
    def __init__(self, app: CTkMain):
        super().__init__(app.body, fg_color=PALETTE["antique"]); self.app = app
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="ABOUT US", font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=PALETTE["bistre"], fg_color="transparent").grid(row=0, column=0, sticky="w", padx=16, pady=(10,6))

        self.img_wrap = ctk.CTkFrame(self, fg_color=PALETTE["antique"])
        self.img_wrap.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        self.img_label = ctk.CTkLabel(self.img_wrap, text=""); self.img_label.pack(fill="both", expand=True)

        ctk.CTkButton(self, text="HOME", width=160, corner_radius=22,
                      fg_color=PALETTE["milk"], text_color=PALETTE["antique"],
                      command=lambda: self.app.go("home")).grid(row=2, column=0, pady=8)

        # render เมื่อปรับขนาด + หน่วงครั้งแรกเล็กน้อย
        self.bind("<Configure>", lambda e: self._render_image())
        self.after(120, self._render_image)

    def _render_image(self):
        # ถ้ายังไม่มีขนาด ให้ลองใหม่ภายหลัง
        w = self.img_wrap.winfo_width()
        h = self.img_wrap.winfo_height()
        if w < 50 or h < 50:
            self.after(100, self._render_image)
            return

        if not ABOUT_IMG_PATH or not os.path.exists(ABOUT_IMG_PATH):
            self.img_label.configure(text=f"(Image not found)\n{ABOUT_IMG_PATH}", image=None)
            return

        try:
            from PIL import Image
            img = Image.open(ABOUT_IMG_PATH).convert("RGB")

            img_ratio = img.width / img.height
            box_ratio = w / h
            if box_ratio > img_ratio:
                # เต็มความสูง
                new_h = h
                new_w = int(max(1, img_ratio * new_h))
            else:
                # เต็มความกว้าง
                new_w = w
                new_h = int(max(1, new_w / img_ratio))

            self._about_img = ctk.CTkImage(light_image=img.resize((new_w, new_h)), size=(new_w, new_h))
            self.img_label.configure(image=self._about_img, text="")
        except Exception as e:
            self.img_label.configure(text=f"Cannot load image:\n{e}", image=None)

# ================== Glue: launch Auth -> Main ==================
def _start_main_app(user_row):
    def back_to_auth(): _launch_auth()
    main = CTkMain(DB(), IMG_QR_PATH, on_logout=back_to_auth)
    refreshed = main.db.conn.execute("SELECT * FROM users WHERE id=?", (user_row['id'],)).fetchone()
    main.login_ok(dict(refreshed or user_row))
    main.mainloop()

def _launch_auth():
    _ = DB()  # ensure schema/seed
    def _on_login_success(row):
        auth.destroy()
        _start_main_app(row)
    auth = AuthApp(db_path=DB_FILE, left_bg_path=LEFT_BG_PATH, logo_path=LOGO_PATH, on_login_success=_on_login_success)
    auth.mainloop()

if __name__ == "__main__":
    ensure_dirs()
    _launch_auth()

# -----+ END 13/11/2025 03:04 AM +------#