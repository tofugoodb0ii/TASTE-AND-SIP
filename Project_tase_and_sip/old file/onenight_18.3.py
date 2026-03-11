# -*- coding: utf-8 -*-
# TASTE AND SIP (Customer-simple version)
# - ปรับการ์ดล็อกอินให้ขนาดคงที่ทุกหน้า (Login/Signup/Forgot)
# - Forgot Password เป็น 2 คอลัมน์ ไม่ล้นกรอบ
# - เพิ่มช่องค้นหาในหน้า Shop
# - ปุ่ม Checkout ให้เห็นตัวอักษรชัดเจน

import os, sys, sqlite3, hashlib, shutil, re
from datetime import datetime as dt, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from typing import Optional, Callable
from PIL import Image, ImageTk
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.units import mm
import customtkinter as ctk

APP_TITLE = "TASTE AND SIP"
DB_FILE   = "taste_and_sip.db"
VAT_RATE  = 0.07

COMPANY_TEL   = "0954751704"
COMPANY_TAXID = "0123456789"

LEFT_BG_PATH = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\AVIBRA_1.png"
LOGO_PATH    = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\lologogo.png-removebg-preview.png"

ASSETS_DIR          = "assets"
IMG_DIR             = os.path.join(ASSETS_DIR, "images")
IMG_PRODUCTS_DIR    = os.path.join(IMG_DIR, "products")
IMG_QR_PATH         = os.path.join(IMG_DIR, "qrcode.jpg")
IMG_AVATARS_DIR     = os.path.join(ASSETS_DIR, "avatars")
REPORTS_DIR         = "reports"

def ensure_dirs():
    for p in [ASSETS_DIR, IMG_DIR, IMG_PRODUCTS_DIR, IMG_AVATARS_DIR, REPORTS_DIR]:
        os.makedirs(p, exist_ok=True)

def sha256(s: str) -> str: return hashlib.sha256(s.encode("utf-8")).hexdigest()
def now_ts(): return dt.now().strftime("%Y-%m-%d %H:%M:%S")

def load_photo(path, size):
    if not path or not os.path.exists(path): return None
    try:
        img = Image.open(path).convert("RGBA").resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

# ======================= DATABASE (ย่อเหลือส่วนที่ใช้) =======================
class DB:
    def __init__(self, path=DB_FILE):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._schema(); self._seed()

    def _schema(self):
        c = self.conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT, phone TEXT, email TEXT, birthdate TEXT, gender TEXT,
            avatar TEXT, role TEXT DEFAULT 'customer')""")
        c.execute("""CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, category_id INTEGER, base_price REAL,
            image TEXT, is_active INTEGER DEFAULT 1)""")
        c.execute("""CREATE TABLE IF NOT EXISTS promotions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE, type TEXT, value REAL,
            min_spend REAL DEFAULT 0, start_at TEXT, end_at TEXT,
            applies_to_product_id INTEGER, is_active INTEGER DEFAULT 1)""")
        c.execute("""CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, order_datetime TEXT,
            subtotal REAL, discount REAL, total REAL,
            payment_method TEXT, status TEXT, vat REAL DEFAULT 0)""")
        c.execute("""CREATE TABLE IF NOT EXISTS order_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER, product_id INTEGER,
            qty INTEGER, unit_price REAL, options_json TEXT, note TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS payments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER, method TEXT, amount REAL, paid_at TEXT, ref TEXT)""")
        self.conn.commit()

    def _seed(self):
        c = self.conn.cursor()
        if not c.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
            c.execute("INSERT INTO users(username,password_hash,name,role) VALUES(?,?,?,?)",
                      ("admin", sha256("admin123"), "Administrator", "admin"))
        if c.execute("SELECT COUNT(*) n FROM categories").fetchone()['n'] == 0:
            c.executemany("INSERT INTO categories(name) VALUES(?)", [("FOOD",),("DRINK",),("DESSERT",)])
        if c.execute("SELECT COUNT(*) n FROM products").fetchone()['n'] == 0:
            cats = {r['name']: r['id'] for r in c.execute("SELECT * FROM categories")}
            sample = [
                ("Pad Thai", cats["FOOD"], 60.0, "", 1),
                ("Thai Milk Tea", cats["DRINK"], 35.0, "", 1),
                ("Mango Sticky Rice", cats["DESSERT"], 50.0, "", 1),
            ]
            c.executemany("INSERT INTO products(name,category_id,base_price,image,is_active) VALUES(?,?,?,?,?)", sample)
        if c.execute("SELECT COUNT(*) n FROM promotions").fetchone()['n'] == 0:
            today = dt.now()
            st = (today - timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
            ed = (today + timedelta(days=365)).strftime("%Y-%m-%d 23:59:59")
            promos = [("WELCOME10","PERCENT_BILL",10,0,st,ed,None,1)]
            c.executemany("""INSERT INTO promotions(code,type,value,min_spend,start_at,end_at,applies_to_product_id,is_active)
                             VALUES(?,?,?,?,?,?,?,?)""", promos)
        self.conn.commit()

    # auth/profile
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

    # catalog
    def categories(self): return self.conn.execute("SELECT * FROM categories").fetchall()
    def products_by_cat(self, cid):
        return self.conn.execute("SELECT * FROM products WHERE category_id=? AND is_active=1",(cid,)).fetchall()

    # promo
    def find_promo(self, code):
        return self.conn.execute("SELECT * FROM promotions WHERE code=? AND is_active=1",(code,)).fetchone()

    # order
    def create_order(self, user_id, cart_items, promo_code, payment_method="SLIP", payment_ref=""):
        subtotal = sum(float(it['base_price']) * it['qty'] for it in cart_items)
        discount = 0.0
        promo = self.find_promo((promo_code or "").strip()) if (promo_code or "").strip() else None
        if promo:
            if promo['type']=="PERCENT_BILL": discount = subtotal * (float(promo['value'])/100.0)
            elif promo['type']=="FLAT_BILL": discount = min(float(promo['value']), subtotal)
        base_after = max(0.0, subtotal-discount)
        vat = round(base_after*VAT_RATE,2)
        total = base_after + vat

        cur = self.conn.cursor()
        cur.execute("""INSERT INTO orders(user_id,order_datetime,subtotal,discount,total,payment_method,status,vat)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (user_id, now_ts(), subtotal, discount, total, payment_method, "PAID", vat))
        oid = cur.lastrowid
        for it in cart_items:
            cur.execute("""INSERT INTO order_items(order_id,product_id,qty,unit_price,options_json,note)
                           VALUES(?,?,?,?,?,?)""",
                        (oid, it['product_id'], it['qty'], it['base_price'], "{}", ""))
        cur.execute("INSERT INTO payments(order_id,method,amount,paid_at,ref) VALUES(?,?,?,?,?)",
                    (oid, payment_method, total, now_ts(), payment_ref))
        self.conn.commit()
        return oid, subtotal, discount, vat, total

    def orders_of_user(self, uid, limit=200):
        return self.conn.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ?", (uid, limit)).fetchall()

    def order_detail(self, oid):
        o = self.conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        items = self.conn.execute("""SELECT oi.*, p.name AS product_name
                                     FROM order_items oi JOIN products p ON p.id=oi.product_id
                                     WHERE order_id=?""",(oid,)).fetchall()
        return o, items, []

# ======================= RECEIPT PDF =======================
def create_receipt_pdf(order_id, db: DB, user_row):
    ensure_dirs()
    path = os.path.join(REPORTS_DIR, f"receipt_{order_id}.pdf")
    c = pdfcanvas.Canvas(path, pagesize=A4)
    W, H = A4
    mx = 20*mm
    y0 = H - 25*mm

    if LOGO_PATH and os.path.exists(LOGO_PATH):
        try: c.drawImage(LOGO_PATH, mx, y0-18*mm, width=22*mm, height=18*mm, preserveAspectRatio=True, mask='auto')
        except Exception: pass

    c.setFont("Helvetica", 11)
    c.drawString(mx, y0-22*mm, f"TEL. {COMPANY_TEL}")
    c.drawString(mx+80*mm, y0-22*mm, f"TAX ID : {COMPANY_TAXID}")

    order, items, _ = db.order_detail(order_id)
    ts = order['order_datetime']
    try:
        dobj = dt.strptime(ts, "%Y-%m-%d %H:%M:%S")
        d_txt = dobj.strftime("%d/%m/%Y"); t_txt = dobj.strftime("%H:%M")
    except Exception:
        d_txt = ts.split(" ")[0]; t_txt = (ts.split(" ")[1] if " " in ts else "")

    c.drawString(mx, y0-32*mm, f"DATE {d_txt}")
    c.drawString(mx+80*mm, y0-32*mm, f"TIME {t_txt}")

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(mx+70*mm, y0-42*mm, "ORDER NO.")
    c.drawCentredString(mx+70*mm, y0-50*mm, f"#{order_id}")
    c.line(mx, y0-55*mm, mx+120*mm, y0-55*mm)

    y = y0-65*mm
    cols = [("No.", 12*mm), ("MENU", 58*mm), ("QTY.", 18*mm), ("PRICE", 25*mm), ("TOTAL", 25*mm)]
    c.setFont("Helvetica-Bold", 11)
    x = mx
    for t, w in cols:
        c.drawString(x+2, y, t); x += w

    y -= 8*mm
    c.setFont("Helvetica", 11)
    widths = [12*mm, 58*mm, 18*mm, 25*mm, 25*mm]
    for i, it in enumerate(items, 1):
        x = mx
        unit = float(it['unit_price']); qty = int(it['qty']); line = unit*qty
        row = [str(i), it['product_name'], str(qty), f"{unit:.2f}", f"{line:.2f}"]
        for val, w in zip(row, widths):
            c.drawString(x+2, y, val); x += w
        y -= 7*mm

    c.drawString(mx, y-6*mm, f"VAT ({int(VAT_RATE*100)}%)")
    c.drawRightString(mx+120*mm, y-6*mm, f"{order['vat']:.2f}")
    y -= 14*mm
    c.line(mx, y, mx+120*mm, y)
    y -= 10*mm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(mx, y, "TOTAL")
    c.drawRightString(mx+120*mm, y, f"{order['total']:.2f}")
    y -= 6*mm
    c.line(mx, y, mx+120*mm, y)

    c.showPage(); c.save()
    return path

# ======================= UI Components =======================
class ProductCard(ttk.Frame):
    def __init__(self, master, row, on_add):
        super().__init__(master, padding=6, style="Card.TFrame")
        self.row = row; self.on_add = on_add
        img = load_photo(row['image'], (160,120))
        ttk.Label(self, image=img if img else None, text="" if img else "[No Image]").pack()
        if img: self._img = img
        ttk.Label(self, text=row['name'], style="Title.TLabel").pack(pady=(6,0))
        ttk.Label(self, text=f"{row['base_price']:.2f} ฿", style="Price.TLabel").pack()
        ttk.Button(self, text="Add to Cart", command=lambda: self.on_add(row)).pack(pady=4)

# ======================= MAIN APP =======================
class App(tk.Tk):
    def __init__(self, on_logout_to_auth: Optional[Callable[[], None]] = None):
        super().__init__()
        self.title(APP_TITLE)
        try: self.state("zoomed")
        except Exception: self.geometry("1200x720")
        ensure_dirs()
        self.db = DB()
        self.user = None
        self.cart = []
        self.on_logout_to_auth = on_logout_to_auth
        self._styles(); self._layout()

    def _styles(self):
        st = ttk.Style(self)
        st.configure("Card.TFrame", relief="groove", borderwidth=1)
        st.configure("Title.TLabel", font=("Segoe UI", 11, "bold"))
        st.configure("Price.TLabel", foreground="#087", font=("Segoe UI", 10, "bold"))

    def _layout(self):
        top = ttk.Frame(self, padding=6); top.pack(side="top", fill="x")
        self.lbl_user = ttk.Label(top, text="Not signed in"); self.lbl_user.pack(side="left")
        ttk.Button(top, text="Shop", command=lambda:self.show("Shop")).pack(side="left", padx=4)
        ttk.Button(top, text="Orders", command=lambda:self.show("Orders")).pack(side="left", padx=4)
        ttk.Button(top, text="Profile", command=lambda:self.show("Profile")).pack(side="left", padx=4)
        self.btn_admin = ttk.Button(top, text="Admin", command=lambda:self.show("Admin")); self.btn_admin.pack(side="left", padx=4)
        self.btn_logout = ttk.Button(top, text="Logout", command=self.logout, state="disabled"); self.btn_logout.pack(side="right")

        self.content = ttk.Frame(self); self.content.pack(fill="both", expand=True)
        self.frames={}
        for F in (LoginView, RegisterView, ShopView, OrdersView, ProfileView, AdminView):
            f = F(self.content, self); self.frames[F.__name__]=f; f.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.show("Login")

    def show(self, name):
        target = {"Login":"LoginView","Register":"RegisterView","Shop":"ShopView","Orders":"OrdersView","Profile":"ProfileView","Admin":"AdminView"}[name]
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
        try: self.destroy()
        finally:
            if self.on_logout_to_auth: self.on_logout_to_auth()

# ---------- Views ----------
class LoginView(ttk.Frame):
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

        # แถวค้นหา
        topbar = ttk.Frame(self); topbar.pack(fill="x", pady=(0,4))
        ttk.Label(topbar, text="Search").pack(side="left")
        self.var_search = tk.StringVar()
        ent = ttk.Entry(topbar, textvariable=self.var_search, width=32)
        ent.pack(side="left", padx=6)
        ent.bind("<KeyRelease>", lambda e: self._build_tabs())

        self.nb=ttk.Notebook(self); self.nb.pack(side="left",fill="both",expand=True)
        right=ttk.Frame(self,padding=8); right.pack(side="left",fill="y")

        ttk.Label(right,text="Cart",font=("Segoe UI",14,"bold")).pack(anchor="w")
        self.tv=ttk.Treeview(right,columns=("name","qty","price"),show="headings",height=18)
        for k,w,anc in [("name",180,"w"),("qty",40,"e"),("price",90,"e")]:
            self.tv.heading(k,text=k.upper()); self.tv.column(k,width=w,anchor=anc)
        self.tv.pack(fill="y",pady=4)

        f1=ttk.Frame(right); f1.pack(fill="x",pady=4)
        ttk.Label(f1,text="Promo Code").grid(row=0,column=0,sticky="w")
        self.var_code=tk.StringVar(); ttk.Entry(f1,textvariable=self.var_code,width=12).grid(row=0,column=1,padx=4)
        ttk.Button(f1,text="Apply",command=self.refresh).grid(row=0,column=2)

        self.lbl_sub=ttk.Label(right,text="Subtotal: 0.00"); self.lbl_sub.pack(anchor="e")
        self.lbl_dis=ttk.Label(right,text="Discount: 0.00"); self.lbl_dis.pack(anchor="e")
        self.lbl_vat=ttk.Label(right,text=f"VAT {int(VAT_RATE*100)}%: 0.00"); self.lbl_vat.pack(anchor="e")
        self.lbl_tot=ttk.Label(right,text="Total: 0.00",font=("Segoe UI",12,"bold")); self.lbl_tot.pack(anchor="e")

        ttk.Separator(right).pack(fill="x",pady=6)
        ttk.Label(right,text="Payment").pack(anchor="w")

        pay = ttk.Frame(right); pay.pack(fill="x",pady=4)
        pay.grid_columnconfigure(0, weight=1)
        pay.grid_columnconfigure(1, weight=1)

        qr_wrap = ttk.LabelFrame(pay, text="Scan to Pay (ร้าน)")
        qr_wrap.grid(row=0, column=0, padx=(0,6), sticky="nsew")
        self.qr_canvas = tk.Canvas(qr_wrap, width=200, height=200, bg="#fff",
                                   highlightthickness=1, highlightbackground="#ddd")
        self.qr_canvas.pack(padx=6, pady=6)
        self._qr_imgtk=None
        if os.path.exists(IMG_QR_PATH):
            try:
                qimg = Image.open(IMG_QR_PATH).convert("RGB")
                qimg.thumbnail((200,200), Image.LANCZOS)
                self._qr_imgtk = ImageTk.PhotoImage(qimg)
                self.qr_canvas.create_image(100,100,image=self._qr_imgtk)
            except Exception:
                self.qr_canvas.create_text(100,100,text="QR load failed")
        else:
            self.qr_canvas.create_text(100,100,text="Put qrcode.jpg\nin assets/images")

        slip_wrap = ttk.LabelFrame(pay, text="Upload Slip (ลูกค้า)")
        slip_wrap.grid(row=0, column=1, padx=(6,0), sticky="nsew")
        self.slip_canvas = tk.Canvas(slip_wrap,width=200,height=200,bg="#fff",
                                     highlightthickness=1,highlightbackground="#ddd")
        self.slip_canvas.pack(padx=6, pady=(6,0))
        self._slip_imgtk=None; self.slip_path=None
        ttk.Button(slip_wrap,text="Upload Slip...",command=self.upload_slip).pack(fill="x",padx=6,pady=(6,6))

        # ปุ่ม Checkout สีชัดเจน (tk.Button เพื่อควบคุมสีได้)
        self.btn_checkout = tk.Button(right, text="CHECKOUT & PAY",
                                      bg="#2c7be5", fg="white",
                                      activebackground="#1f6fdd", activeforeground="white",
                                      font=("Segoe UI", 10, "bold"),
                                      relief="raised", command=self.checkout)
        self.btn_checkout.pack(fill="x",pady=(8,6))

        self.btn_receipt = ttk.Button(right, text="Download Receipt", command=self.download_receipt, state="disabled")
        self.btn_receipt.pack(fill="x")
        ttk.Button(right,text="Clear Cart",command=self.clear).pack(fill="x",pady=(6,0))

        self.last_order_id = None

    def on_show(self):
        self._build_tabs(); self.refresh()

    def _build_tabs(self):
        # กรองชื่อด้วยช่องค้นหา
        q = (self.var_search.get() or "").strip().lower()
        for t in self.nb.tabs(): self.nb.forget(t)
        for cat in self.app.db.categories():
            frm=ttk.Frame(self.nb); self.nb.add(frm,text=cat['name'])
            can=tk.Canvas(frm); vs=ttk.Scrollbar(frm,orient="vertical",command=can.yview)
            holder=ttk.Frame(can); holder.bind("<Configure>", lambda e, c=can: c.configure(scrollregion=c.bbox("all")))
            can.create_window((0,0),window=holder,anchor="nw"); can.configure(yscrollcommand=vs.set)
            can.pack(side="left",fill="both",expand=True); vs.pack(side="right",fill="y")
            rowf=None; col=0
            products = [p for p in self.app.db.products_by_cat(cat['id']) if (p['name'] or "").lower().find(q) != -1] if q else self.app.db.products_by_cat(cat['id'])
            for i,p in enumerate(products):
                if i%3==0: rowf=ttk.Frame(holder); rowf.pack(fill="x",pady=6); col=0
                ProductCard(rowf,p,self.add).grid(row=0,column=col,padx=6); col+=1

    def add(self, prod_row):
        for it in self.app.cart:
            if it['product_id']==prod_row['id']:
                it['qty']+=1; break
        else:
            self.app.cart.append({
                "product_id": prod_row['id'], "name": prod_row['name'],
                "base_price": float(prod_row['base_price']), "qty": 1
            })
        self.refresh()

    def _totals(self):
        subtotal=sum(it['base_price']*it['qty'] for it in self.app.cart)
        discount=0.0
        code=self.var_code.get().strip().upper()
        promo=self.app.db.find_promo(code) if code else None
        if promo:
            ptype=promo['type']; val=float(promo['value'] or 0)
            if ptype=="PERCENT_BILL": discount = subtotal*(val/100.0)
            elif ptype=="FLAT_BILL": discount = min(val, subtotal)
        base_after=max(0.0, subtotal-discount)
        vat=round(base_after*VAT_RATE,2)
        total=base_after+vat
        return subtotal, discount, vat, total

    def refresh(self):
        for i in self.tv.get_children(): self.tv.delete(i)
        for it in self.app.cart:
            line=it['base_price']*it['qty']
            self.tv.insert("", "end", values=(it['name'], it['qty'], f"{line:.2f}"))
        sub,dis,vat,tot=self._totals()
        self.lbl_sub.config(text=f"Subtotal: {sub:.2f}")
        self.lbl_dis.config(text=f"Discount: {dis:.2f}")
        self.lbl_vat.config(text=f"VAT {int(VAT_RATE*100)}%: {vat:.2f}")
        self.lbl_tot.config(text=f"Total: {tot:.2f}")

    def upload_slip(self):
        f=filedialog.askopenfilename(title="Select payment slip",
                                     filetypes=[("Images","*.png;*.jpg;*.jpeg;*.bmp;*.gif"),("All files","*.*")])
        if not f: return
        self.slip_path=f
        try:
            img=Image.open(f).convert("RGB")
            img.thumbnail((200,200), Image.LANCZOS)
            self._slip_imgtk=ImageTk.PhotoImage(img)
            self.slip_canvas.delete("all")
            self.slip_canvas.create_image(100,100,image=self._slip_imgtk)
        except Exception:
            self.slip_canvas.delete("all")
            self.slip_canvas.create_text(100,100,text="(preview failed)")

    def checkout(self):
        if not self.app.user: messagebox.showwarning("Login","Please sign in"); return
        if not self.app.cart: messagebox.showwarning("Cart","Cart empty"); return
        if not self.slip_path: messagebox.showwarning("Slip","Please upload payment slip before checkout"); return
        code=self.var_code.get().strip().upper()
        oid, sub, dis, vat, tot = self.app.db.create_order(
            user_id=self.app.user['id'],
            cart_items=self.app.cart,
            promo_code=code,
            payment_method="SLIP",
            payment_ref=self.slip_path
        )
        self.last_order_id = oid
        path = create_receipt_pdf(oid, self.app.db, self.app.user)
        self.btn_receipt['state'] = "normal"
        messagebox.showinfo("Success", f"Order #{oid} placed.\nReceipt saved:\n{path}")
        self.app.cart.clear(); self.slip_path=None; self.slip_canvas.delete("all"); self.refresh(); self.app.show("Orders")

    def download_receipt(self):
        if not self.last_order_id:
            messagebox.showinfo("Receipt", "No recent order. Please checkout first."); return
        path = create_receipt_pdf(self.last_order_id, self.app.db, self.app.user)
        try:
            if sys.platform.startswith("win"): os.startfile(path)
            elif sys.platform=="darwin": os.system(f"open '{path}'")
            else: os.system(f"xdg-open '{path}'")
        except: messagebox.showinfo("Receipt", f"Saved at: {path}")

    def clear(self):
        self.app.cart.clear()
        self.slip_path=None; self.slip_canvas.delete("all")
        self.btn_receipt['state'] = "disabled"
        self.last_order_id = None
        self.refresh()

class OrdersView(ttk.Frame):
    def __init__(self, master, app: App):
        super().__init__(master,padding=10); self.app=app
        ttk.Label(self,text="Order History",font=("Segoe UI",16,"bold")).pack(anchor="w")
        self.tv=ttk.Treeview(self,columns=("id","date","total"),show="headings")
        for k,w in [("id",80),("date",160),("total",90)]:
            self.tv.heading(k,text=k.upper()); self.tv.column(k,width=w,anchor="w")
        self.tv.pack(fill="both",expand=True,pady=6)
        fr=ttk.Frame(self); fr.pack(anchor="e")
        ttk.Button(fr,text="Refresh",command=self.refresh).pack(side="right",padx=4)
        ttk.Button(fr,text="Download Receipt",command=self.open).pack(side="right",padx=4)
    def on_show(self): self.refresh()
    def refresh(self):
        for i in self.tv.get_children(): self.tv.delete(i)
        if not self.app.user: return
        for r in self.app.db.orders_of_user(self.app.user['id']):
            self.tv.insert("", "end", values=(r['id'], r['order_datetime'], f"{r['total']:.2f}"))
    def open(self):
        sel=self.tv.selection()
        if not sel: messagebox.showinfo("Open","Select an order"); return
        oid=int(self.tv.item(sel[0],"values")[0]); path=create_receipt_pdf(oid,self.app.db,self.app.user)
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

# ======================= Auth (customtkinter) =======================
RIGHT_BG   = "#f8eedb"
CARD_BG    = "#edd8b8"
TEXT_DARK  = "#1f2937"
LINK_FG    = "#0057b7"
BORDER     = "#d3c6b4"
CARD_W     = 660
CARD_H     = 560
RADIUS     = 18

USERNAME_RE = re.compile(r"^[A-Za-z0-9]{6,}$")
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
        c.execute("""CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT, phone TEXT, email TEXT, birthdate TEXT, gender TEXT,
                avatar TEXT, role TEXT DEFAULT 'customer')""")
        self.conn.commit()
    def find_user_for_login(self, username: str, password: str) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM users WHERE username=? AND password_hash=?",
                                 (username, sha256(password))).fetchone()
    def username_exists(self, username: str) -> bool:
        return self.conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone() is not None
    def create_user(self, username: str, phone: str, email: str, password: str):
        self.conn.execute("INSERT INTO users(username, password_hash, phone, email, role) VALUES(?,?,?,?,?)",
                          (username, sha256(password), phone, email, "customer")); self.conn.commit()
    def verify_user_contact(self, username: str, email_or_phone: str) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM users WHERE username=? AND (email=? OR phone=?)",
                                 (username, email_or_phone, email_or_phone)).fetchone()
    def change_password(self, username: str, new_password: str):
        self.conn.execute("UPDATE users SET password_hash=? WHERE username=?",
                          (sha256(new_password), username)); self.conn.commit()

def validate_username(v: str) -> Optional[str]:
    return None if USERNAME_RE.match(v or "") else "USERNAME MUST BE AT LEAST 6 CHARACTERS AND CONTAIN ONLY A–Z AND 0–9."
def validate_phone(v: str) -> Optional[str]:
    return None if PHONE_RE.match(v or "") else "PHONE MUST BE 10 DIGITS."
def validate_email(v: str) -> Optional[str]:
    return None if EMAIL_RE.match(v or "") else "INVALID EMAIL FORMAT."
def validate_password(v: str) -> Optional[str]:
    return None if PWD_RE.match(v or "") else "PASSWORD MUST BE ≥ 8 CHARS, INCLUDE UPPERCASE, LOWERCASE AND A DIGIT (LETTERS/DIGITS ONLY)."

class AuthApp(ctk.CTk):
    def __init__(self, db_path: str = DB_FILE, left_bg_path: Optional[str] = None,
                 logo_path: Optional[str] = None,
                 on_login_success: Optional[Callable[[sqlite3.Row], None]] = None):
        super().__init__()
        ctk.set_appearance_mode("light")
        self.title(APP_TITLE)
        try: self.state("zoomed")
        except Exception: self.geometry("1200x720")
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
        self.left_canvas = tk.Canvas(self.left, highlightthickness=0, bd=0, bg=RIGHT_BG)
        self.left_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self._left_img_tk = None
        self.left.bind("<Configure>", lambda e: self._draw_left_bg())

        self.right = ctk.CTkFrame(self, fg_color=RIGHT_BG, corner_radius=0)
        self.right.grid(row=0, column=1, sticky="nsew")
        self.right.grid_rowconfigure(1, weight=1)
        self.right.grid_columnconfigure(0, weight=1)

        self.logo_wrap = ctk.CTkFrame(self.right, fg_color=RIGHT_BG, corner_radius=0)
        self.logo_wrap.grid(row=0, column=0, pady=(30, 10))
        self._render_logo()

        # การ์ดขนาดคงที่ทุกหน้า
        self.card = ctk.CTkFrame(self.right, fg_color=CARD_BG, corner_radius=RADIUS,
                                 border_color=BORDER, border_width=1,
                                 width=CARD_W, height=CARD_H)
        self.card.grid(row=1, column=0, sticky="n", padx=80, pady=(10, 40))
        self.card.grid_propagate(False)   # << คงที่จริง ไม่ยืด/หด
        self.card.grid_columnconfigure(0, weight=1)

        self.show_signin()

    # --- Left BG & Logo ---
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
                left = max(0, (nw - w) // 2); top  = max(0, (nh - h) // 2)
                img  = img.crop((left, top, left + w, top + h))
                self._left_img_tk = ImageTk.PhotoImage(img)
                c.create_image(0, 0, anchor="nw", image=self._left_img_tk)
            except Exception:
                pass
        t1 = c.create_text(28, 28, anchor="nw", fill="white",
                           font=("Segoe UI", 36, "bold"),
                           text=f"WELCOME TO\n{APP_TITLE}".upper())
        bbox = c.bbox(t1); y2 = (bbox[3] if bbox else 120) + 18
        c.create_text(32, y2, anchor="nw", fill="white",
                      font=("Segoe UI", 18, "bold"),
                      text="FOOD AND DRINK!".upper())

    def _render_logo(self):
        for w in self.logo_wrap.winfo_children(): w.destroy()
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                img = Image.open(self.logo_path)
                self._logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(220, 220))
                ctk.CTkLabel(self.logo_wrap, image=self._logo_img, text="", fg_color="transparent").pack()
                return
            except Exception: pass
        ctk.CTkLabel(self.logo_wrap, text=APP_TITLE.upper(),
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=TEXT_DARK,
                     fg_color="transparent").pack()

    def _clear_card(self):
        for w in self.card.winfo_children(): w.destroy()
        # รักษาพื้นที่ภายใน เพื่อไม่ให้ล้น
        self.card.grid_columnconfigure(0, weight=1)
        self.card.grid_rowconfigure(99, weight=1)

    # --- Screens ---
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

        # --- 2 คอลัมน์: USERNAME | EMAIL/PHONE ---
        row1 = ctk.CTkFrame(self.card, fg_color="transparent")
        row1.pack(fill="x", padx=16, pady=(6, 0))
        row1.grid_columnconfigure(0, weight=1, uniform="fg")
        row1.grid_columnconfigure(1, weight=1, uniform="fg")

        self.fp_user    = LabeledEntry(row1, "USERNAME");       self.fp_user.grid(row=0, column=0, padx=8, pady=6, sticky="ew")
        self.fp_contact = LabeledEntry(row1, "EMAIL OR PHONE"); self.fp_contact.grid(row=0, column=1, padx=8, pady=6, sticky="ew")

        SubmitBtn(self.card, "VERIFY", command=self._forgot_verify).pack(fill="x", padx=24, pady=(6, 4))

        # ขั้นตอน 2: ตั้งรหัสใหม่ (2 คอลัมน์)
        self.fp_step2 = ctk.CTkFrame(self.card, fg_color="transparent")
        self.fp_step2.pack(fill="x", padx=16, pady=(6, 10))
        self.fp_step2.grid_columnconfigure(0, weight=1, uniform="fg2")
        self.fp_step2.grid_columnconfigure(1, weight=1, uniform="fg2")
        self.fp_step2.pack_forget()

        self.fp_pwd1 = LabeledEntry(self.fp_step2, "NEW PASSWORD", show="•");        self.fp_pwd1.grid(row=0, column=0, padx=8, pady=6, sticky="ew")
        self.fp_pwd2 = LabeledEntry(self.fp_step2, "CONFIRM NEW PASSWORD", show="•");self.fp_pwd2.grid(row=0, column=1, padx=8, pady=6, sticky="ew")
        self.fp_change_btn = SubmitBtn(self.fp_step2, "CHANGE PASSWORD", command=self._forgot_change)
        self.fp_change_btn.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 6))

        LinkBtn(self.card, "BACK TO LOGIN", command=self.show_signin).pack(pady=(0, 18))
        self._verified_username = None

    # --- Actions for Auth ---
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
            # อัปเดตรหัสผ่านตาม username
            self.db.change_password(self._verified_username, p1)
            self.fp_err.set("PASSWORD CHANGED. YOU CAN SIGN IN NOW.")
        except Exception as e:
            self.fp_err.set(f"FAILED TO CHANGE PASSWORD: {e}")

# ===== Widgets (Auth) =====
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
                     font=ctk.CTkFont(size=11, weight="bold"),
                     fg_color="transparent").grid(row=0, column=0, sticky="w", padx=2, pady=(0,2))
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

# ===== Glue: AuthApp <-> Main App =====
def _start_main_app(user_row):
    def launch_auth(): _launch_auth()
    main_app = App(on_logout_to_auth=launch_auth)
    refreshed = main_app.db.conn.execute("SELECT * FROM users WHERE id=?", (user_row['id'],)).fetchone()
    main_app.login_ok(refreshed or user_row)
    main_app.mainloop()

def _launch_auth():
    def _on_login_success(row):
        auth.destroy()
        _start_main_app(row)
    auth = AuthApp(
        db_path=DB_FILE,
        left_bg_path=LEFT_BG_PATH,
        logo_path=LOGO_PATH,
        on_login_success=_on_login_success
    )
    auth.mainloop()

if __name__ == "__main__":
    ensure_dirs()
    _launch_auth()
