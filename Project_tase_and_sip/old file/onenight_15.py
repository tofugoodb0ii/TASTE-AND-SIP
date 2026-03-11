# -*- coding: utf-8 -*-
"""
TASTE & SIP — MERGED SINGLE FILE

สิ่งที่รวม/ปรับตามโจทย์:
1) นำ "หน้าล็อกอิน" (สไตล์ customtkinter + การลืมรหัสผ่านด้วย USERNAME + EMAIL/PHONE) จาก onenight05
   มาใส่ในแอป Taste & Sip ตัวเต็ม แล้วโยงเข้าหน้าหลักทันทีเมื่อเข้าสู่ระบบสำเร็จ
2) ลดการเลือกสินค้าให้เรียบง่าย: ไม่มีตัวเลือกเนื้อสัตว์/ระดับความหวาน/ท็อปปิ้ง
   — ลูกค้ากด Add > ใส่จำนวน > เข้าตะกร้า, พร้อมเพิ่ม/ลบ/ล้างตะกร้าได้
3) หน้าชำระเงินใช้สแกน QR จากพาธที่กำหนดไว้ (Windows path):
      C:\\Users\\thatt\\OneDrive\\Desktop\\python\\Project_tase_and_sip\\image\\qrcode.png.JPG
   — มีปุ่มอัปโหลดสลิปโอนเงิน (แนบรูปไฟล์) และหลังแนบสลิปแล้วจะมีปุ่ม "ดาวน์โหลดใบเสร็จ" (PDF)
4) ฝั่งแอดมินอิงตามไฟล์ tasteandsip_full003 (ย่อส่วนให้ใช้งานหลัก ๆ ได้: จัดการสินค้า ดูคำสั่งซื้อ)
5) ลืมรหัสผ่าน ไม่ใช้ OTP — ใช้ฟอร์ม USERNAME + EMAIL ตรวจคู่ในฐานข้อมูลแล้วตั้งรหัสใหม่ได้

หมายเหตุ:
- โค้ดนี้ย่อส่วนจากระบบใหญ่เพื่อให้ใช้งานได้ครบตามโจทย์ในไฟล์เดียว (production ควรแยกไฟล์/ชั้นข้อมูล)
- ฐานข้อมูล: SQLite (ไฟล์ taste_and_sip.db)
- รูปภาพ QR ใช้ path ของผู้ใช้ตามโจทย์ (ถ้าไม่มีจะขึ้นข้อความเตือน)
- จำเป็นต้องติดตั้ง: customtkinter, pillow, reportlab

"""

import os, sqlite3, hashlib, json, shutil, sys, subprocess
from datetime import datetime as dt

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import customtkinter as ctk

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.units import mm

APP_TITLE = "TASTE & SIP"
DB_FILE   = "taste_and_sip.db"

# ---------- PATHS ----------
# ภาพ QR ชำระเงินตามที่ผู้ใช้ระบุ
QR_IMAGE_PATH = r"C:\\Users\\thatt\\OneDrive\\Desktop\\python\\Project_tase_and_sip\\image\\qrcode.png.JPG"
ASSETS_DIR = "assets"
PROD_IMG_DIR = os.path.join(ASSETS_DIR, "products")
RECEIPT_DIR = "receipts"
AVATAR_DIR  = os.path.join(ASSETS_DIR, "avatars")

os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(PROD_IMG_DIR, exist_ok=True)
os.makedirs(RECEIPT_DIR, exist_ok=True)
os.makedirs(AVATAR_DIR,  exist_ok=True)

# ---------- HELPERS ----------
def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def now_ts() -> str:
    return dt.now().strftime("%Y-%m-%d %H:%M:%S")

# ---------- DATABASE LAYER ----------
class DB:
    def __init__(self, path=DB_FILE):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._schema(); self._seed()

    def _schema(self):
        c = self.conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                name TEXT,
                avatar TEXT,
                role TEXT DEFAULT 'customer'
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS products(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                price REAL,
                image TEXT,
                is_active INTEGER DEFAULT 1
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS orders(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                created_at TEXT,
                subtotal REAL,
                total REAL,
                status TEXT,
                slip_path TEXT
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS order_items(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                product_id INTEGER,
                name TEXT,
                qty INTEGER,
                unit_price REAL
            )
            """
        )
        self.conn.commit()

    def _seed(self):
        c = self.conn.cursor()
        # admin
        if not c.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
            c.execute("INSERT INTO users(username,password_hash,name,role,email) VALUES(?,?,?,?,?)",
                      ("admin", sha256("admin123"), "Administrator", "admin", "admin@example.com"))
        # sample products if empty
        if c.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            demo = [
                ("Thai Milk Tea", 35.0, ""),
                ("Pad Thai", 60.0, ""),
                ("Mango Sticky Rice", 50.0, ""),
            ]
            c.executemany("INSERT INTO products(name,price,image) VALUES(?,?,?)", demo)
        self.conn.commit()

    # ---- USERS ----
    def create_user(self, username: str, email: str, phone: str, password: str):
        self.conn.execute(
            "INSERT INTO users(username,password_hash,email,phone,role) VALUES(?,?,?,?,?)",
            (username, sha256(password), email, phone, "customer")
        ); self.conn.commit()

    def user_exists(self, username: str) -> bool:
        return self.conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone() is not None

    def auth(self, username: str, password: str):
        return self.conn.execute(
            "SELECT * FROM users WHERE username=? AND password_hash=?",
            (username, sha256(password))
        ).fetchone()

    def verify_user_contact(self, username: str, email_or_phone: str):
        return self.conn.execute(
            "SELECT * FROM users WHERE username=? AND (email=? OR phone=?)",
            (username, email_or_phone, email_or_phone)
        ).fetchone()

    def change_password(self, username: str, new_password: str):
        self.conn.execute("UPDATE users SET password_hash=? WHERE username=?",
                          (sha256(new_password), username))
        self.conn.commit()

    # ---- PRODUCTS ----
    def list_products(self):
        return self.conn.execute("SELECT * FROM products WHERE is_active=1 ORDER BY id DESC").fetchall()

    def upsert_product(self, pid, name, price, image, active=1):
        cur = self.conn.cursor()
        if pid:
            cur.execute("UPDATE products SET name=?, price=?, image=?, is_active=? WHERE id=?",
                        (name, price, image, active, pid))
        else:
            cur.execute("INSERT INTO products(name,price,image,is_active) VALUES(?,?,?,?)",
                        (name, price, image, active))
        self.conn.commit()

    def delete_product(self, pid):
        self.conn.execute("DELETE FROM products WHERE id=?", (pid,)); self.conn.commit()

    # ---- ORDERS ----
    def create_order(self, user_id: int, cart_items: list, slip_path: str | None) -> int:
        subtotal = sum(it['price'] * it['qty'] for it in cart_items)
        total = subtotal
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO orders(user_id,created_at,subtotal,total,status,slip_path) VALUES(?,?,?,?,?,?)",
            (user_id, now_ts(), subtotal, total, "PAID" if slip_path else "PENDING", slip_path)
        )
        oid = cur.lastrowid
        for it in cart_items:
            cur.execute(
                "INSERT INTO order_items(order_id,product_id,name,qty,unit_price) VALUES(?,?,?,?,?)",
                (oid, it['id'], it['name'], it['qty'], it['price'])
            )
        self.conn.commit(); return oid

    def orders_of_user(self, uid):
        return self.conn.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (uid,)).fetchall()

    def order_detail(self, order_id: int):
        o = self.conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        items = self.conn.execute("SELECT * FROM order_items WHERE order_id=?", (order_id,)).fetchall()
        return o, items

# ---------- RECEIPT (PDF) ----------
def create_receipt_pdf(db: DB, order_id: int, user_row) -> str:
    path = os.path.join(RECEIPT_DIR, f"receipt_{order_id}.pdf")
    canv = pdfcanvas.Canvas(path, pagesize=A4)
    W, H = A4
    x = 18*mm; y = H - 18*mm

    order, items = db.order_detail(order_id)

    canv.setFont("Helvetica-Bold", 16)
    canv.drawString(x, y, "TASTE & SIP — RECEIPT"); y -= 10*mm
    canv.setFont("Helvetica", 10)
    canv.drawString(x, y, f"Order ID: {order_id}"); y -= 5*mm
    canv.drawString(x, y, f"Date/Time: {order['created_at']}"); y -= 5*mm
    canv.drawString(x, y, f"Customer: {user_row['name'] or user_row['username']}"); y -= 8*mm

    canv.setFont("Helvetica-Bold", 12)
    canv.drawString(x, y, "Items"); y -= 6*mm
    canv.setFont("Helvetica", 10)
    for it in items:
        canv.drawString(x, y, f"- {it['name']} x{it['qty']} @ {it['unit_price']:.2f}"); y -= 5*mm
        y -= 1*mm

    canv.setFont("Helvetica-Bold", 11)
    canv.drawString(x, y, f"Subtotal: {order['subtotal']:.2f}    Total: {order['total']:.2f}"); y -= 8*mm
    canv.setFont("Helvetica", 10)
    canv.drawString(x, y, f"Payment: QR + SLIP"); y -= 10*mm

    if os.path.exists(QR_IMAGE_PATH):
        try:
            canv.drawImage(QR_IMAGE_PATH, x, y-45*mm, width=40*mm, height=40*mm, preserveAspectRatio=True, mask='auto')
            canv.drawString(x+45*mm, y-5*mm, "สแกนชำระเงิน (แสดงเท่านั้น)")
        except Exception:
            canv.drawString(x, y, "QR image error.")
    else:
        canv.drawString(x, y, "ไม่พบรูป QR ที่กำหนดไว้")

    canv.showPage(); canv.save()
    return path

# ---------- AUTH (นำสไตล์จาก onenight05) ----------
RIGHT_BG   = "#f8eedb"
CARD_BG    = "#edd8b8"
TEXT_DARK  = "#1f2937"
LINK_FG    = "#0057b7"
BORDER     = "#d3c6b4"
CARD_W     = 660
CARD_H     = 560
RADIUS     = 18

class ErrorLabel(ctk.CTkLabel):
    def __init__(self, master):
        super().__init__(master, text="", text_color="#b00020", wraplength=560, justify="left", fg_color="transparent")
    def set(self, text: str):
        self.configure(text=(text or "").upper())

class Title(ctk.CTkLabel):
    def __init__(self, master, text: str):
        super().__init__(master, text=text.upper(), font=ctk.CTkFont(size=20, weight="bold"), text_color=TEXT_DARK, fg_color="transparent")

class LinkBtn(ctk.CTkButton):
    def __init__(self, master, text, command):
        super().__init__(master, text=text, command=command, fg_color="transparent", hover_color="#e7d7bd", text_color=LINK_FG)

class SubmitBtn(ctk.CTkButton):
    def __init__(self, master, text, command):
        super().__init__(master, text=text, command=command, fg_color="#1f2937", hover_color="#111827")

class LabeledEntry(ctk.CTkEntry):
    def __init__(self, master, label: str, show: str | None = None):
        frame = ctk.CTkFrame(master, fg_color="transparent")
        frame.pack_propagate(False)
        frame.grid_columnconfigure(0, weight=1)
        self.label = ctk.CTkLabel(frame, text=label, text_color=TEXT_DARK)
        self.label.grid(row=0, column=0, sticky="w")
        super().__init__(frame, show=show or "")
        self.grid(row=1, column=0, sticky="ew", pady=(2, 8))
        self.container = frame

    def pack(self, *a, **k):
        return self.container.pack(*a, **k)

    def grid(self, *a, **k):
        return self.container.grid(*a, **k)

class AuthCard(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=CARD_BG, corner_radius=RADIUS, border_color=BORDER, border_width=1, width=CARD_W, height=CARD_H)
        self.app = app
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        self.show_signin()

    def clear(self):
        for w in self.winfo_children():
            w.destroy()
        self.grid_columnconfigure(0, weight=1)

    def show_signin(self):
        self.clear()
        Title(self, "SIGN IN").pack(pady=(22, 6))
        self.si_err = ErrorLabel(self); self.si_err.pack(padx=28, fill="x")
        self.si_user = LabeledEntry(self, "USERNAME"); self.si_user.pack(fill="x", padx=28, pady=(6, 8))
        self.si_pwd  = LabeledEntry(self, "PASSWORD", show="•"); self.si_pwd.pack(fill="x", padx=28, pady=(6, 12))
        SubmitBtn(self, "SIGN IN", command=self._signin).pack(fill="x", padx=28, pady=(0, 12))
        bottom = ctk.CTkFrame(self, fg_color="transparent"); bottom.pack(fill="x", pady=(4, 18))
        LinkBtn(bottom, "FORGOT PASSWORD?", command=self.show_forgot).pack(side="left", padx=4)
        LinkBtn(bottom, "CREATE ACCOUNT", command=self.show_signup).pack(side="right", padx=4)

    def show_signup(self):
        self.clear()
        Title(self, "CREATE ACCOUNT").pack(pady=(22, 6))
        self.su_err = ErrorLabel(self); self.su_err.pack(padx=24, fill="x")
        form = ctk.CTkFrame(self, fg_color="transparent"); form.pack(fill="x", padx=24, pady=(6, 10))
        form.grid_columnconfigure(0, weight=1, uniform="c"); form.grid_columnconfigure(1, weight=1, uniform="c")
        self.su_user  = LabeledEntry(form, "USERNAME");  self.su_user.grid(row=0, column=0, padx=8, pady=6, sticky="ew")
        self.su_email = LabeledEntry(form, "EMAIL");     self.su_email.grid(row=1, column=0, padx=8, pady=6, sticky="ew")
        self.su_phone = LabeledEntry(form, "PHONE");     self.su_phone.grid(row=1, column=1, padx=8, pady=6, sticky="ew")
        self.su_pwd1  = LabeledEntry(form, "PASSWORD", show="•"); self.su_pwd1.grid(row=2, column=0, padx=8, pady=6, sticky="ew")
        self.su_pwd2  = LabeledEntry(form, "CONFIRM PASSWORD", show="•"); self.su_pwd2.grid(row=2, column=1, padx=8, pady=6, sticky="ew")
        SubmitBtn(self, "REGISTER", command=self._signup).pack(fill="x", padx=24, pady=(8, 12))
        LinkBtn(self, "BACK TO LOGIN", command=self.show_signin).pack(pady=(0, 18))

    def show_forgot(self):
        self.clear()
        Title(self, "FORGOT PASSWORD").pack(pady=(22, 6))
        self.fp_err = ErrorLabel(self); self.fp_err.pack(padx=24, fill="x")
        self.fp_user = LabeledEntry(self, "USERNAME"); self.fp_user.pack(fill="x", padx=24, pady=(6, 8))
        self.fp_contact = LabeledEntry(self, "EMAIL OR PHONE"); self.fp_contact.pack(fill="x", padx=24, pady=(6, 10))
        SubmitBtn(self, "VERIFY", command=self._forgot_verify).pack(fill="x", padx=24, pady=(0, 12))
        self.fp_step2 = ctk.CTkFrame(self, fg_color="transparent"); self.fp_step2.pack(fill="x", padx=16, pady=(6, 12))
        self.fp_step2.grid_columnconfigure(0, weight=1); self.fp_step2.pack_forget()
        self.fp_pwd1 = LabeledEntry(self.fp_step2, "NEW PASSWORD", show="•"); self.fp_pwd1.pack(fill="x", padx=12, pady=(6, 8))
        self.fp_pwd2 = LabeledEntry(self.fp_step2, "CONFIRM NEW PASSWORD", show="•"); self.fp_pwd2.pack(fill="x", padx=12, pady=(6, 10))
        SubmitBtn(self.fp_step2, "CHANGE PASSWORD", command=self._forgot_change).pack(fill="x", padx=12, pady=(0, 10))
        LinkBtn(self, "BACK TO LOGIN", command=self.show_signin).pack(pady=(0, 18))
        self._verified_username = None

    # ---- actions ----
    def _signin(self):
        self.si_err.set("")
        u = (self.si_user.get() or "").strip(); p = (self.si_pwd.get() or "").strip()
        if not u or not p:
            self.si_err.set("PLEASE ENTER USERNAME AND PASSWORD."); return
        row = self.app.db.auth(u, p)
        if row:
            self.app.on_login_success(row)
        else:
            self.si_err.set("INVALID CREDENTIALS.")

    def _signup(self):
        self.su_err.set("")
        u  = (self.su_user.get() or "").strip()
        em = (self.su_email.get() or "").strip()
        ph = (self.su_phone.get() or "").strip()
        p1 = (self.su_pwd1.get() or "").strip()
        p2 = (self.su_pwd2.get() or "").strip()
        if not u or not em or not p1:
            self.su_err.set("PLEASE FILL USERNAME/EMAIL/PASSWORD"); return
        if p1 != p2:
            self.su_err.set("PASSWORDS DO NOT MATCH."); return
        if self.app.db.user_exists(u):
            self.su_err.set("USERNAME ALREADY EXISTS."); return
        try:
            self.app.db.create_user(u, em, ph, p1)
            self.su_err.set("ACCOUNT CREATED. PLEASE SIGN IN.")
        except sqlite3.IntegrityError:
            self.su_err.set("USERNAME ALREADY EXISTS.")
        except Exception as e:
            self.su_err.set(f"FAILED TO REGISTER: {e}")

    def _forgot_verify(self):
        self.fp_err.set("")
        u  = (self.fp_user.get() or "").strip(); cp = (self.fp_contact.get() or "").strip()
        if not u or not cp:
            self.fp_err.set("PLEASE FILL USERNAME AND EMAIL/PHONE."); return
        row = self.app.db.verify_user_contact(u, cp)
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
        if len(p1) < 8:
            self.fp_err.set("PASSWORD MUST BE AT LEAST 8 CHARACTERS."); return
        if p1 != p2:
            self.fp_err.set("PASSWORDS DO NOT MATCH."); return
        try:
            self.app.db.change_password(self._verified_username, p1)
            self.fp_err.set("PASSWORD CHANGED. YOU CAN SIGN IN NOW.")
        except Exception as e:
            self.fp_err.set(f"FAILED TO CHANGE PASSWORD: {e}")

# ---------- SIMPLE SHOP UI (ไม่มี size/sweetness/toppings) ----------
class ProductCard(ttk.Frame):
    def __init__(self, master, row, on_add):
        super().__init__(master, padding=8, style="Card.TFrame")
        self.row = row
        self.on_add = on_add
        # image
        img = None
        if row['image'] and os.path.exists(row['image']):
            try:
                pil = Image.open(row['image']).convert("RGBA").resize((160,120), Image.LANCZOS)
                img = ImageTk.PhotoImage(pil)
            except Exception:
                img = None
        ttk.Label(self, image=img if img else None, text="" if img else "[No Image]").pack()
        if img: self._img = img
        ttk.Label(self, text=row['name'], style="Title.TLabel").pack(pady=(6,0))
        ttk.Label(self, text=f"{row['price']:.2f} ฿", style="Price.TLabel").pack()
        # qty selector
        qty_row = ttk.Frame(self); qty_row.pack(pady=4)
        ttk.Label(qty_row, text="Qty").pack(side="left")
        self.qty_var = tk.StringVar(value="1")
        qty_e = ttk.Entry(qty_row, textvariable=self.qty_var, width=5, justify="center"); qty_e.pack(side="left", padx=6)
        ttk.Button(self, text="Add to Cart", command=self._add).pack(pady=4)

    def _add(self):
        try:
            q = max(1, int(self.qty_var.get()))
        except Exception:
            q = 1
        self.on_add(self.row, q)

class ShopView(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.nb = ttk.Notebook(self); self.nb.pack(fill="both", expand=True)
        self._rebuild()

    def _rebuild(self):
        for t in self.nb.tabs(): self.nb.forget(t)
        # แท็บเดียว "สินค้าทั้งหมด" เพื่อความเรียบง่าย
        frm = ttk.Frame(self.nb); self.nb.add(frm, text="สินค้าทั้งหมด")
        can = tk.Canvas(frm); vs = ttk.Scrollbar(frm, orient="vertical", command=can.yview)
        holder = ttk.Frame(can)
        holder.bind("<Configure>", lambda e: can.configure(scrollregion=can.bbox("all")))
        can.create_window((0,0), window=holder, anchor="nw")
        can.configure(yscrollcommand=vs.set)
        can.pack(side="left", fill="both", expand=True); vs.pack(side="right", fill="y")
        # การ์ดสินค้า
        row = 0; col = 0
        for p in self.app.db.list_products():
            card = ProductCard(holder, p, on_add=self.app.cart_add)
            card.grid(row=row, column=col, padx=8, pady=8)
            col += 1
            if col >= 4: col = 0; row += 1

class CartView(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=8)
        self.app = app
        self.tree = ttk.Treeview(self, columns=("name","qty","price","amount"), show="headings", height=12)
        for i,(w,t) in enumerate([(220,"สินค้า"),(60,"จำนวน"),(80,"ราคา"),(100,"รวม")]):
            self.tree.heading(i, text=t); self.tree.column(i, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True)
        btns = ttk.Frame(self); btns.pack(fill="x", pady=(6,0))
        ttk.Button(btns, text="ลบรายการที่เลือก", command=self._remove_selected).pack(side="left")
        ttk.Button(btns, text="ล้างตะกร้า", command=self.app.cart_clear).pack(side="left", padx=6)
        self.lbl_total = ttk.Label(self, text="รวมทั้งสิ้น: 0.00 ฿", font=("Segoe UI", 12, "bold"))
        self.lbl_total.pack(anchor="e", pady=6)

    def refresh(self):
        for x in self.tree.get_children(): self.tree.delete(x)
        total = 0.0
        for idx, it in enumerate(self.app.cart):
            amt = it['price']*it['qty']; total += amt
            self.tree.insert("", "end", iid=str(idx), values=(it['name'], it['qty'], f"{it['price']:.2f}", f"{amt:.2f}"))
        self.lbl_total.configure(text=f"รวมทั้งสิ้น: {total:.2f} ฿")

    def _remove_selected(self):
        sel = self.tree.selection()
        if not sel: return
        index = int(sel[0])
        self.app.cart_remove(index)

class PaymentPanel(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=8)
        self.app = app
        ttk.Label(self, text="ชำระเงินด้วย QR").pack(anchor="w")
        self.canvas_qr = tk.Canvas(self, width=180, height=180, bg="#fff", highlightthickness=1, highlightbackground="#ddd")
        self.canvas_qr.pack(pady=4)
        self._draw_qr()
        # สลิป
        row = ttk.Frame(self); row.pack(fill="x", pady=6)
        ttk.Button(row, text="อัปโหลดสลิป", command=self._upload_slip).pack(side="left")
        self.lbl_slip = ttk.Label(row, text="ยังไม่ได้อัปโหลดสลิป")
        self.lbl_slip.pack(side="left", padx=8)
        # ปุ่มชำระเงิน/ออกใบเสร็จ
        self.btn_checkout = ttk.Button(self, text="ยืนยันชำระเงิน", command=self._checkout)
        self.btn_checkout.pack(fill="x", pady=(10,4))
        self.btn_receipt = ttk.Button(self, text="ดาวน์โหลดใบเสร็จ (PDF)", command=self._download_receipt, state="disabled")
        self.btn_receipt.pack(fill="x")
        self._last_order_id = None
        self._slip_path = None

    def _draw_qr(self):
        self.canvas_qr.delete("all")
        if os.path.exists(QR_IMAGE_PATH):
            try:
                img = Image.open(QR_IMAGE_PATH).convert("RGBA").resize((180,180), Image.LANCZOS)
                self._qrimg = ImageTk.PhotoImage(img)
                self.canvas_qr.create_image(90, 90, image=self._qrimg)
                return
            except Exception:
                pass
        self.canvas_qr.create_text(90, 90, text="QR not found\ncheck path", justify="center")

    def _upload_slip(self):
        f = filedialog.askopenfilename(title="เลือกสลิปโอนเงิน", filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif")])
        if not f: return
        dest = os.path.join(ASSETS_DIR, os.path.basename(f))
        try:
            shutil.copy2(f, dest)
            self._slip_path = dest
            self.lbl_slip.configure(text=os.path.basename(dest))
        except Exception as e:
            messagebox.showerror("Slip", f"คัดลอกสลิปไม่สำเร็จ: {e}")

    def _checkout(self):
        if not self.app.user:
            messagebox.showwarning("Login", "กรุณาเข้าสู่ระบบก่อน")
            return
        if not self.app.cart:
            messagebox.showinfo("Cart", "ตะกร้าว่าง")
            return
        items = list(self.app.cart)
        oid = self.app.db.create_order(self.app.user['id'], items, self._slip_path)
        self._last_order_id = oid
        self.btn_receipt.configure(state="normal")
        messagebox.showinfo("Payment", f"บันทึกการชำระเงินแล้ว (Order #{oid})")
        # เคลียร์ตะกร้า
        self.app.cart_clear()

    def _download_receipt(self):
        if not self._last_order_id:
            messagebox.showinfo("Receipt", "ยังไม่มีออเดอร์ล่าสุด"); return
        pdf_path = create_receipt_pdf(self.app.db, self._last_order_id, self.app.user)
        # เปิดไฟล์ด้วยโปรแกรมเริ่มต้นของระบบ
        try:
            if sys.platform.startswith("win"):
                os.startfile(pdf_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", pdf_path])
            else:
                subprocess.Popen(["xdg-open", pdf_path])
        except Exception:
            messagebox.showinfo("Receipt", f"บันทึกแล้ว: {pdf_path}")

# ---------- MAIN APP SHELL ----------
class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        try:
            self.state("zoomed")
        except Exception:
            self.geometry("1200x720")
        ctk.set_appearance_mode("light")

        self.db = DB(DB_FILE)
        self.user = None
        self.cart: list[dict] = []  # [{'id','name','price','qty'}]

        # Layout: left auth canvas, right card for auth หรือ main
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left (ภาพพื้นหลัง + ข้อความ)
        self.left = ctk.CTkFrame(self, fg_color=RIGHT_BG, corner_radius=0)
        self.left.grid(row=0, column=0, sticky="nsew")
        self.left_canvas = tk.Canvas(self.left, highlightthickness=0, bd=0, bg=RIGHT_BG)
        self.left_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self._left_img_tk = None
        self.left.bind("<Configure>", lambda e: self._draw_left_bg())

        # Right container
        self.right = ctk.CTkFrame(self, fg_color=RIGHT_BG, corner_radius=0)
        self.right.grid(row=0, column=1, sticky="nsew")
        self.right.grid_rowconfigure(1, weight=1)
        self.right.grid_columnconfigure(0, weight=1)
        self.logo_wrap = ctk.CTkFrame(self.right, fg_color=RIGHT_BG, corner_radius=0)
        self.logo_wrap.grid(row=0, column=0, pady=(30, 10))
        ctk.CTkLabel(self.logo_wrap, text=APP_TITLE, font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT_DARK,
                     fg_color="transparent").pack()

        # Card zone (สลับระหว่าง AuthCard กับ Main)
        self.card_area = ctk.CTkFrame(self.right, fg_color=RIGHT_BG)
        self.card_area.grid(row=1, column=0)
        self.auth_card = AuthCard(self.card_area, self)
        self.auth_card.grid()

        # main area (สร้างแต่ซ่อนไว้ก่อน)
        self.main_area = ctk.CTkFrame(self.right, fg_color=RIGHT_BG)
        self._build_main()
        self.main_area.grid_remove()

    # ---- Left cover image & title ----
    def _draw_left_bg(self):
        c = self.left_canvas
        c.delete("all")
        w = max(300, int(self.winfo_width()*0.5))
        h = max(300, self.winfo_height())
        c.configure(width=w, height=h)
        c.create_rectangle(0,0,w,h, fill=RIGHT_BG, outline="")
        # (ปล่อยว่างภาพจริง - ผู้ใช้สามารถเติมเองถ้าต้องการ)
        t1 = c.create_text(28, 28, anchor="nw", fill="white", font=("Segoe UI", 36, "bold"),
                           text=f"WELCOME TO\n{APP_TITLE}".upper())
        bbox = c.bbox(t1); y2 = (bbox[3] if bbox else 120) + 18
        c.create_text(32, y2, anchor="nw", fill="white", font=("Segoe UI", 18, "bold"), text="FOOD AND DRINK!".upper())

    # ---- auth success ----
    def on_login_success(self, row):
        self.user = row
        self.auth_card.grid_remove()
        self.main_area.grid()
        self._refresh_all()

    # ---- build main views ----
    def _build_main(self):
        # toolbar
        bar = ctk.CTkFrame(self.main_area, fg_color=CARD_BG, corner_radius=RADIUS, border_color=BORDER, border_width=1)
        bar.pack(fill="x", pady=(0,6))
        ctk.CTkLabel(bar, text=f"สวัสดี: ", text_color=TEXT_DARK).pack(side="left", padx=(12,4))
        self.lbl_user = ctk.CTkLabel(bar, text="-", text_color=TEXT_DARK, font=ctk.CTkFont(weight="bold"))
        self.lbl_user.pack(side="left")
        ctk.CTkButton(bar, text="ออกจากระบบ", command=self.logout, fg_color="#933", hover_color="#722").pack(side="right", padx=8, pady=6)
        ctk.CTkButton(bar, text="Admin", command=self.show_admin).pack(side="right", padx=8)

        # split 2 cols
        body = ctk.CTkFrame(self.main_area, fg_color=RIGHT_BG)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        # left: shop
        shop_wrap = ctk.CTkFrame(body, fg_color=RIGHT_BG)
        shop_wrap.grid(row=0, column=0, sticky="nsew")
        self.shop = ShopView(shop_wrap, self)
        self.shop.pack(fill="both", expand=True)

        # right: cart + payment
        right = ctk.CTkFrame(body, fg_color=RIGHT_BG)
        right.grid(row=0, column=1, sticky="nsew")
        ttk.Label(right, text="ตะกร้าสินค้า", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=6)
        self.cart_view = CartView(right, self); self.cart_view.pack(fill="both", expand=True)
        self.payment = PaymentPanel(right, self); self.payment.pack(fill="x")

    def _refresh_all(self):
        try:
            uname = self.user['name'] or self.user['username']
        except Exception:
            uname = "-"
        self.lbl_user.configure(text=uname)
        self.shop._rebuild()
        self.cart_view.refresh()
        self.payment._draw_qr()

    # ---- cart ops ----
    def cart_add(self, prod_row, qty=1):
        if not self.user:
            messagebox.showerror("Add to Cart", "กรุณาล็อกอินก่อนเพิ่มสินค้าลงตะกร้า"); return
        try:
            qty = max(1, int(qty))
        except Exception:
            qty = 1
        self.cart.append({
            'id': prod_row['id'],
            'name': prod_row['name'],
            'price': float(prod_row['price'] or 0.0),
            'qty': qty,
        })
        self.cart_view.refresh()

    def cart_remove(self, index: int):
        if 0 <= index < len(self.cart):
            self.cart.pop(index)
            self.cart_view.refresh()

    def cart_clear(self):
        self.cart.clear(); self.cart_view.refresh()

    def logout(self):
        self.user = None
        self.main_area.grid_remove()
        self.auth_card.grid()

    # ---- admin (ย่อ) ----
    def show_admin(self):
        AdminDialog(self)

# ---------- ADMIN (ย่อส่วนจากระบบใหญ่) ----------
class AdminDialog(ctk.CTkToplevel):
    def __init__(self, app: MainApp):
        super().__init__(app)
        self.app = app
        self.title("Admin — Products & Orders")
        self.geometry("1000x700+200+60")
        self.transient(app)
        self.grab_set()

        tabs = ctk.CTkTabview(self); tabs.pack(fill="both", expand=True, padx=8, pady=8)
        self.tab_products = tabs.add("Products")
        self.tab_orders   = tabs.add("Orders")

        # products
        left = ctk.CTkFrame(self.tab_products); left.pack(fill="both", expand=True, padx=6, pady=6)
        top = ctk.CTkFrame(left); top.pack(fill="x")
        ctk.CTkButton(top, text="Add", command=self._add_product).pack(side="left")
        ctk.CTkButton(top, text="Edit", command=self._edit_selected).pack(side="left", padx=6)
        ctk.CTkButton(top, text="Delete", command=self._delete_selected).pack(side="left")
        self.tree_prod = ttk.Treeview(left, columns=("id","name","price"), show="headings", height=14)
        for i,(w,t) in enumerate([(60,"ID"),(300,"Name"),(120,"Price")]):
            self.tree_prod.heading(i, text=t); self.tree_prod.column(i, width=w, anchor="center")
        self.tree_prod.pack(fill="both", expand=True, pady=6)

        # orders
        orf = ctk.CTkFrame(self.tab_orders); orf.pack(fill="both", expand=True, padx=6, pady=6)
        self.tree_ord = ttk.Treeview(orf, columns=("id","user","when","total","status","slip"), show="headings", height=14)
        for i,(w,t) in enumerate([(60,"ID"),(160,"User"),(160,"When"),(100,"Total"),(120,"Status"),(200,"Slip")]):
            self.tree_ord.heading(i, text=t); self.tree_ord.column(i, width=w, anchor="center")
        self.tree_ord.pack(fill="both", expand=True)
        row = ctk.CTkFrame(orf); row.pack(fill="x", pady=6)
        ctk.CTkButton(row, text="Open Slip", command=self._open_slip).pack(side="left")
        ctk.CTkButton(row, text="Mark as Done", command=lambda: self._set_status("อาหารเสร็จแล้ว")).pack(side="left", padx=6)
        ctk.CTkButton(row, text="Mark Invalid Slip", command=lambda: self._set_status("สลิปไม่ถูกต้อง")).pack(side="left")

        self._refresh()

    def _refresh(self):
        # products
        for x in self.tree_prod.get_children(): self.tree_prod.delete(x)
        for r in self.app.db.list_products():
            self.tree_prod.insert("", "end", values=(r['id'], r['name'], f"{r['price']:.2f}"))
        # orders
        for x in self.tree_ord.get_children(): self.tree_ord.delete(x)
        rows = self.app.db.conn.execute(
            "SELECT o.*, u.username AS uname FROM orders o LEFT JOIN users u ON u.id=o.user_id ORDER BY o.id DESC"
        ).fetchall()
        for r in rows:
            self.tree_ord.insert("", "end", values=(r['id'], r['uname'] or '-', r['created_at'], f"{r['total']:.2f}", r['status'] or '-', r['slip_path'] or '-'))

    def _pick_product(self):
        sel = self.tree_prod.selection()
        if not sel: return None
        vals = self.tree_prod.item(sel[0], 'values')
        return int(vals[0])

    def _add_product(self):
        ProductEditor(self, None, self.app.db, on_saved=self._refresh)

    def _edit_selected(self):
        pid = self._pick_product()
        if not pid: return
        ProductEditor(self, pid, self.app.db, on_saved=self._refresh)

    def _delete_selected(self):
        pid = self._pick_product()
        if not pid: return
        if messagebox.askyesno("Delete", f"ลบสินค้า ID {pid} ?"):
            self.app.db.delete_product(pid)
            self._refresh()

    def _open_slip(self):
        sel = self.tree_ord.selection()
        if not sel: return
        vals = self.tree_ord.item(sel[0], 'values')
        p = vals[5]
        if p and os.path.exists(p):
            try:
                if sys.platform.startswith("win"): os.startfile(p)
                elif sys.platform == "darwin": subprocess.Popen(["open", p])
                else: subprocess.Popen(["xdg-open", p])
            except Exception as e:
                messagebox.showerror("Slip", f"ไม่สามารถเปิดสลิปได้: {e}")
        else:
            messagebox.showinfo("Slip", "ไม่พบไฟล์สลิป")

    def _set_status(self, status: str):
        sel = self.tree_ord.selection()
        if not sel: return
        oid = int(self.tree_ord.item(sel[0], 'values')[0])
        self.app.db.conn.execute("UPDATE orders SET status=? WHERE id=?", (status, oid))
        self.app.db.conn.commit(); self._refresh()

class ProductEditor(ctk.CTkToplevel):
    def __init__(self, master, pid, db: DB, on_saved):
        super().__init__(master)
        self.db = db; self.pid = pid; self.on_saved = on_saved
        self.title("Product Editor"); self.geometry("520x380+300+180"); self.transient(master); self.grab_set()
        frm = ctk.CTkFrame(self); frm.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(frm, text="Name").grid(row=0, column=0, sticky="e", padx=6, pady=6)
        self.e_name = ctk.CTkEntry(frm, width=320); self.e_name.grid(row=0, column=1)
        ctk.CTkLabel(frm, text="Price").grid(row=1, column=0, sticky="e", padx=6, pady=6)
        self.e_price = ctk.CTkEntry(frm, width=120); self.e_price.grid(row=1, column=1, sticky="w")
        ctk.CTkLabel(frm, text="Image").grid(row=2, column=0, sticky="e", padx=6, pady=6)
        self.e_img = ctk.CTkEntry(frm, width=320); self.e_img.grid(row=2, column=1)
        ctk.CTkButton(frm, text="Browse", command=self._browse_img).grid(row=2, column=2, padx=6)
        self.chk_active = tk.IntVar(value=1)
        ctk.CTkCheckBox(frm, text="Active", variable=self.chk_active).grid(row=3, column=1, sticky="w", pady=6)
        row = ctk.CTkFrame(frm); row.grid(row=4, column=0, columnspan=3, pady=12)
        ctk.CTkButton(row, text="Save", command=self._save).pack(side="left", padx=6)
        ctk.CTkButton(row, text="Cancel", command=self.destroy).pack(side="left")
        if pid:
            r = self.db.conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
            if r:
                self.e_name.insert(0, r['name'] or "")
                self.e_price.insert(0, str(r['price'] or 0))
                self.e_img.insert(0, r['image'] or "")
                self.chk_active.set(int(r['is_active'] or 1))

    def _browse_img(self):
        p = filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif")])
        if p:
            dest = os.path.join(PROD_IMG_DIR, os.path.basename(p))
            try:
                shutil.copy2(p, dest); self.e_img.delete(0, tk.END); self.e_img.insert(0, dest)
            except Exception as e:
                messagebox.showerror("Image", f"คัดลอกภาพไม่สำเร็จ: {e}")

    def _save(self):
        name = self.e_name.get().strip(); price = float(self.e_price.get().strip() or 0.0)
        img = self.e_img.get().strip(); act = 1 if self.chk_active.get() else 0
        self.db.upsert_product(self.pid, name, price, img, act)
        messagebox.showinfo("Saved", "บันทึกสินค้าแล้ว")
        self.on_saved(); self.destroy()

# ---------- RUN ----------
if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
