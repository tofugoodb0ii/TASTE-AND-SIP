#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TASTE AND SIP – ร้านอาหารหลายชาติ + เครื่องดื่ม (Python + Tkinter + SQLite)
เวอร์ชันสตาร์ทเตอร์ไฟล์เดียว (ปรับขยายเป็นหลายไฟล์ได้ภายหลัง)

สิ่งที่มีให้:
- สร้างฐานข้อมูลและตาราง (users, menu_items, orders, order_items)
- ระบบสมัคร/ล็อกอิน/โปรไฟล์ (นโยบายรหัสผ่านตามที่กำหนด)
- โครงสร้าง GUI แบบสลับหน้า + Header (โลโก้มุมซ้าย, เมนูฝั่งขวา)
- หน้า Home พร้อมแครูเซลรูป (อ่านจากโฟลเดอร์)
- หน้า FOOD / DRINK (อ่านเมนูจาก DB + เพิ่มลงตะกร้าได้ *ต้องล็อกอินก่อน*)
- หน้า CART (ดู ปรับจำนวน ลบ ยืนยันสั่งซื้อ => เขียนลง DB)
- หน้า ABOUT (ข้อมูลร้าน)
- ส่วน ADMIN: ล็อกอินแอดมิน, จัดการเมนูอย่างง่าย (เพิ่ม/แก้/ลบ/เปิดปิด), ดูออเดอร์และอัปเดตสถานะ, รายงานยอดพื้นฐาน

จุดใส่ path รูป:
- โลโก้ร้าน: LOGO_PATH = 'assets/logo.png'
- สไลด์หน้าแรก: CAROUSEL_DIR = 'assets/home_carousel/' (อ่านไฟล์รูปทั้งหมดในโฟลเดอร์)
- รูปเมนู: เก็บเป็น path ในคอลัมน์ image_path ของตาราง menu_items (เพิ่ม/แก้ผ่านหน้า Admin > เมนู)

สิ่งที่ต้องมีเพิ่มในเครื่อง:
- Python 3.10+
- pillow (PIL) -> pip install pillow

หมายเหตุ: โค้ดนี้เป็นสตาร์ทให้ครบฟีเจอร์หลักตามสเปก สามารถแตกไฟล์เป็นแพ็กเกจได้ภายหลัง
"""

import os
import re
import sqlite3
import hashlib
import binascii
import time
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    from PIL import Image, ImageTk
    PIL_OK = True
except Exception:
    PIL_OK = False

# ===================== CONFIG =====================
APP_TITLE = "TASTE AND SIP"
DB_PATH = "taste_and_sip.db"
ASSETS_DIR = Path("assets")
LOGO_PATH = Path(r"C:\Users\...\logo.png")
CAROUSEL_DIR = Path(r"C:\Users\thatt\Downloads\food album")

PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{9,}$")

# ===================== DB LAYER =====================
class DB:
    def __init__(self, path: str):
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              email TEXT UNIQUE NOT NULL,
              username TEXT UNIQUE NOT NULL,
              password_hash TEXT NOT NULL,
              salt TEXT NOT NULL,
              avatar_path TEXT,
              role TEXT NOT NULL DEFAULT 'user',
              created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS menu_items (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              category TEXT NOT NULL,
              cuisine TEXT,
              price REAL NOT NULL,
              image_path TEXT,
              is_active INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              status TEXT NOT NULL DEFAULT 'pending',
              total REAL NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS order_items (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              order_id INTEGER NOT NULL,
              item_id INTEGER NOT NULL,
              quantity INTEGER NOT NULL,
              base_price REAL NOT NULL,
              spice_level TEXT,
              meat_type TEXT,
              allergen_note TEXT,
              sweetness TEXT,
              ice_level TEXT,
              milk_type TEXT,
              note TEXT,
              subtotal REAL NOT NULL,
              FOREIGN KEY (order_id) REFERENCES orders(id),
              FOREIGN KEY (item_id) REFERENCES menu_items(id)
            )
            """
        )
        self.conn.commit()
        self._seed()

    def _seed(self):
        cur = self.conn.cursor()
        # สร้างแอดมินเริ่มต้นถ้ายังไม่มี
        cur.execute("SELECT COUNT(*) c FROM users WHERE role='admin'")
        if cur.fetchone()[0] == 0:
            self.create_user("admin@example.com", "admin", "AdminPass123", role="admin")
        # เติมเมนูตัวอย่างถ้ายังว่าง
        cur.execute("SELECT COUNT(*) FROM menu_items")
        if cur.fetchone()[0] == 0:
            sample = [
                ("Pad Thai", "food", "Thai", 80.0, str(ASSETS_DIR/"food"/"pad_thai.jpg"), 1),
                ("Green Curry", "food", "Thai", 95.0, str(ASSETS_DIR/"food"/"green_curry.jpg"), 1),
                ("Sushi Set", "food", "Japanese", 150.0, str(ASSETS_DIR/"food"/"sushi.jpg"), 1),
                ("Americano", "drink", None, 45.0, str(ASSETS_DIR/"drink"/"americano.jpg"), 1),
                ("Milk Tea", "drink", None, 55.0, str(ASSETS_DIR/"drink"/"milk_tea.jpg"), 1),
            ]
            cur.executemany(
                "INSERT INTO menu_items(name,category,cuisine,price,image_path,is_active) VALUES(?,?,?,?,?,?)",
                sample,
            )
            self.conn.commit()

    # ---------- USERS ----------
    @staticmethod
    def _hash_password(password: str, salt: bytes) -> str:
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
        return binascii.hexlify(dk).decode()

    def create_user(self, email: str, username: str, password: str, role: str = "user"):
        if not PASSWORD_REGEX.match(password):
            raise ValueError("รหัสผ่านไม่ผ่านนโยบาย")
        salt = os.urandom(16)
        pwh = self._hash_password(password, salt)
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO users(email,username,password_hash,salt,role) VALUES(?,?,?,?,?)",
            (email, username, pwh, binascii.hexlify(salt).decode(), role),
        )
        self.conn.commit()

    def auth_user(self, username_or_email: str, password: str):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE username=? OR email=?",
            (username_or_email, username_or_email),
        )
        row = cur.fetchone()
        if not row:
            return None
        salt = binascii.unhexlify(row["salt"])  # bytes
        pwh = self._hash_password(password, salt)
        if pwh == row["password_hash"]:
            return row
        return None

    def update_profile(self, user_id: int, new_username: str = None, avatar_path: str = None):
        cur = self.conn.cursor()
        if new_username and avatar_path:
            cur.execute("UPDATE users SET username=?, avatar_path=? WHERE id=?", (new_username, avatar_path, user_id))
        elif new_username:
            cur.execute("UPDATE users SET username=? WHERE id=?", (new_username, user_id))
        elif avatar_path:
            cur.execute("UPDATE users SET avatar_path=? WHERE id=?", (avatar_path, user_id))
        self.conn.commit()

    def change_password(self, user_id: int, new_password: str):
        if not PASSWORD_REGEX.match(new_password):
            raise ValueError("รหัสผ่านใหม่ไม่ผ่านนโยบาย")
        salt = os.urandom(16)
        pwh = self._hash_password(new_password, salt)
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE users SET password_hash=?, salt=? WHERE id=?",
            (pwh, binascii.hexlify(salt).decode(), user_id),
        )
        self.conn.commit()

    # ---------- MENU ----------
    def list_menu(self, category: str):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM menu_items WHERE category=? AND is_active=1 ORDER BY name",
            (category,),
        )
        return cur.fetchall()

    def upsert_menu_item(self, item_id, name, category, cuisine, price, image_path, is_active=1):
        cur = self.conn.cursor()
        if item_id:
            cur.execute(
                """
                UPDATE menu_items
                SET name=?, category=?, cuisine=?, price=?, image_path=?, is_active=?
                WHERE id=?
                """,
                (name, category, cuisine, price, image_path, is_active, item_id),
            )
        else:
            cur.execute(
                "INSERT INTO menu_items(name,category,cuisine,price,image_path,is_active) VALUES(?,?,?,?,?,?)",
                (name, category, cuisine, price, image_path, is_active),
            )
        self.conn.commit()

    def delete_menu_item(self, item_id):
        # เปลี่ยนเป็น inactive แทนลบจริง เพื่อความปลอดภัยข้อมูล
        cur = self.conn.cursor()
        cur.execute("UPDATE menu_items SET is_active=0 WHERE id=?", (item_id,))
        self.conn.commit()

    # ---------- ORDERS ----------
    def create_order(self, user_id: int, items: list):
        # items: [{item_id, quantity, base_price, spice_level, meat_type, allergen_note, sweetness, ice_level, milk_type, note, subtotal}]
        total = sum(x.get("subtotal", 0) for x in items)
        cur = self.conn.cursor()
        cur.execute("INSERT INTO orders(user_id, status, total) VALUES(?,?,?)", (user_id, "paid", total))
        order_id = cur.lastrowid
        for it in items:
            cur.execute(
                """
                INSERT INTO order_items(order_id,item_id,quantity,base_price,spice_level,meat_type,allergen_note,sweetness,ice_level,milk_type,note,subtotal)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    order_id,
                    it.get("item_id"),
                    it.get("quantity", 1),
                    it.get("base_price", 0.0),
                    it.get("spice_level"),
                    it.get("meat_type"),
                    it.get("allergen_note"),
                    it.get("sweetness"),
                    it.get("ice_level"),
                    it.get("milk_type"),
                    it.get("note"),
                    it.get("subtotal", 0.0),
                ),
            )
        self.conn.commit()
        return order_id, total

    def list_orders(self, status=None):
        cur = self.conn.cursor()
        if status:
            cur.execute("SELECT * FROM orders WHERE status=? ORDER BY created_at DESC", (status,))
        else:
            cur.execute("SELECT * FROM orders ORDER BY created_at DESC")
        return cur.fetchall()

    def update_order_status(self, order_id: int, new_status: str):
        cur = self.conn.cursor()
        cur.execute("UPDATE orders SET status=? WHERE id=?", (new_status, order_id))
        self.conn.commit()

    # ---------- REPORTS ----------
    def top_selling(self, limit=10):
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT m.name, SUM(oi.quantity) qty
            FROM order_items oi
            JOIN menu_items m ON m.id = oi.item_id
            JOIN orders o ON o.id = oi.order_id
            WHERE o.status IN ('paid','preparing','completed')
            GROUP BY oi.item_id
            ORDER BY qty DESC
            LIMIT ?
            """,
            (limit,),
        )
        return cur.fetchall()

    def revenue_by_day(self, days=30):
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT date(created_at) d, SUM(total) revenue
            FROM orders
            WHERE status IN ('paid','preparing','completed')
              AND created_at >= datetime('now', ?)
            GROUP BY date(created_at)
            ORDER BY d
            """,
            (f"-{days} days",),
        )
        return cur.fetchall()

# ===================== APP STATE =====================
class SessionState:
    def __init__(self):
        self.current_user = None  # sqlite3.Row
        self.cart = []  # list[dict]

    def require_login(self, on_fail):
        if self.current_user is None:
            messagebox.showinfo("กรุณาเข้าสู่ระบบ", "ต้องล็อกอินก่อนเพิ่มลงตะกร้าหรือสั่งซื้อ")
            on_fail()  # e.g. ไปหน้า SignIn
            return False
        return True

# ===================== UI HELPERS =====================
def load_image(path: Path, size=(64, 64)):
    if not PIL_OK:
        return None
    try:
        img = Image.open(path)
        img.thumbnail(size)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

# ===================== FRAMES =====================
class Header(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.configure(padding=8)

        # left: logo + title
        left = ttk.Frame(self)
        left.pack(side=tk.LEFT, fill=tk.Y)
        if LOGO_PATH.exists() and PIL_OK:
            self.logo_img = load_image(LOGO_PATH, size=(36, 36))
            if self.logo_img:
                ttk.Label(left, image=self.logo_img).pack(side=tk.LEFT, padx=(0,6))
        ttk.Label(left, text=APP_TITLE, style="Title.TLabel", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)

        # right: nav buttons
        right = ttk.Frame(self)
        right.pack(side=tk.RIGHT)
        for text, cmd in [
            ("HOME", lambda: app.show_frame(HomeFrame)),
            ("FOOD", lambda: app.show_frame(FoodFrame)),
            ("DRINK", lambda: app.show_frame(DrinkFrame)),
            ("CART", lambda: app.show_frame(CartFrame)),
            ("ABOUT", lambda: app.show_frame(AboutFrame)),
        ]:
            ttk.Button(right, text=text, command=cmd).pack(side=tk.LEFT, padx=4)

        self.auth_btn = ttk.Button(right, text="SIGN IN", command=lambda: app.show_frame(SignInFrame))
        self.auth_btn.pack(side=tk.LEFT, padx=(10,0))

        self.admin_btn = ttk.Button(right, text="ADMIN", command=lambda: app.show_frame(AdminLoginFrame))
        self.admin_btn.pack(side=tk.LEFT, padx=4)

        self.refresh()

    def refresh(self):
        if self.app.state.current_user is None:
            self.auth_btn.config(text="SIGN IN", command=lambda: self.app.show_frame(SignInFrame))
        else:
            username = self.app.state.current_user["username"]
            self.auth_btn.config(text=f"{username} (SIGN OUT)", command=self._signout)

    def _signout(self):
        self.app.state.current_user = None
        self.app.state.cart.clear()
        self.refresh()
        self.app.show_frame(HomeFrame)

class HomeFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.configure(padding=16)
        ttk.Label(self, text="Welcome to TASTE AND SIP", font=("Segoe UI", 20, "bold")).pack(pady=(8,16))
        self.canvas = tk.Label(self)
        self.canvas.pack(pady=8)
        self._carousel_images = []
        self._carousel_index = 0

        nav = ttk.Frame(self)
        nav.pack()
        ttk.Button(nav, text="<<", command=self.prev_img).pack(side=tk.LEFT, padx=8)
        ttk.Button(nav, text=">>", command=self.next_img).pack(side=tk.LEFT, padx=8)

        tips = ttk.Label(self, text="* หากยังไม่ล็อกอิน สามารถเลื่อนดูเมนูได้ แต่ยังเพิ่มลงตะกร้าไม่ได้ *")
        tips.pack(pady=(10,0))

        self.load_carousel()

    def load_carousel(self):
        self._carousel_images.clear()
        if CAROUSEL_DIR.exists() and PIL_OK:
            for p in sorted(CAROUSEL_DIR.iterdir()):
                if p.suffix.lower() in (".png",".jpg",".jpeg",".gif"):
                    img = load_image(p, size=(560, 320))
                    if img:
                        self._carousel_images.append(img)
        if not self._carousel_images:
            # fallback – ข้อความแทนรูป
            self.canvas.config(text="วางรูปสไลด์ใน assets/home_carousel/ เพื่อแสดงสไลด์หน้าแรก", image="")
        else:
            self.canvas.config(image=self._carousel_images[0], text="")

    def prev_img(self):
        if not self._carousel_images:
            return
        self._carousel_index = (self._carousel_index - 1) % len(self._carousel_images)
        self.canvas.config(image=self._carousel_images[self._carousel_index])

    def next_img(self):
        if not self._carousel_images:
            return
        self._carousel_index = (self._carousel_index + 1) % len(self._carousel_images)
        self.canvas.config(image=self._carousel_images[self._carousel_index])

class SignInFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.configure(padding=24)

        ttk.Label(self, text="เข้าสู่ระบบ", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=(0,12))
        ttk.Label(self, text="อีเมลหรือชื่อผู้ใช้").grid(row=1, column=0, sticky=tk.W)
        self.username = ttk.Entry(self, width=30)
        self.username.grid(row=1, column=1, pady=6)
        ttk.Label(self, text="รหัสผ่าน").grid(row=2, column=0, sticky=tk.W)
        self.password = ttk.Entry(self, width=30, show="*")
        self.password.grid(row=2, column=1, pady=6)

        ttk.Button(self, text="เข้าสู่ระบบ", command=self.do_login).grid(row=3, column=0, columnspan=2, pady=8)
        ttk.Button(self, text="สมัครบัญชี", command=lambda: app.show_frame(SignUpFrame)).grid(row=4, column=0, columnspan=2)

    def do_login(self):
        u = self.username.get().strip()
        p = self.password.get().strip()
        user = self.app.db.auth_user(u, p)
        if user:
            self.app.state.current_user = user
            messagebox.showinfo("สำเร็จ", f"ยินดีต้อนรับ {user['username']}")
            self.app.header.refresh()
            self.app.show_frame(HomeFrame)
        else:
            messagebox.showerror("ผิดพลาด", "ข้อมูลเข้าสู่ระบบไม่ถูกต้อง")

class SignUpFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.configure(padding=24)

        ttk.Label(self, text="สมัครบัญชีใหม่", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=(0,12))
        ttk.Label(self, text="อีเมล").grid(row=1, column=0, sticky=tk.W)
        self.email = ttk.Entry(self, width=32)
        self.email.grid(row=1, column=1, pady=4)
        ttk.Label(self, text="ชื่อผู้ใช้").grid(row=2, column=0, sticky=tk.W)
        self.username = ttk.Entry(self, width=32)
        self.username.grid(row=2, column=1, pady=4)
        ttk.Label(self, text="รหัสผ่าน (ตัวอักษรอังกฤษ, มีเล็ก/ใหญ่/ตัวเลข, ≥9, ไม่มีสัญลักษณ์พิเศษ)").grid(row=3, column=0, columnspan=2, sticky=tk.W)
        self.password = ttk.Entry(self, width=32, show="*")
        self.password.grid(row=4, column=0, columnspan=2, pady=4)

        ttk.Button(self, text="สมัคร", command=self.do_signup).grid(row=5, column=0, columnspan=2, pady=8)
        ttk.Button(self, text="กลับไปหน้าเข้าสู่ระบบ", command=lambda: app.show_frame(SignInFrame)).grid(row=6, column=0, columnspan=2)

    def do_signup(self):
        email = self.email.get().strip()
        username = self.username.get().strip()
        password = self.password.get().strip()
        try:
            self.app.db.create_user(email, username, password)
            messagebox.showinfo("สำเร็จ", "สมัครบัญชีเรียบร้อย ลองเข้าสู่ระบบได้เลย")
            self.app.show_frame(SignInFrame)
        except sqlite3.IntegrityError:
            messagebox.showerror("ผิดพลาด", "อีเมลหรือชื่อผู้ใช้ซ้ำ")
        except ValueError as e:
            messagebox.showerror("ผิดพลาด", str(e))

class ProfileFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.configure(padding=24)

        ttk.Label(self, text="โปรไฟล์", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=3, pady=(0,12))
        ttk.Label(self, text="ชื่อผู้ใช้ใหม่").grid(row=1, column=0, sticky=tk.W)
        self.new_un = ttk.Entry(self, width=28)
        self.new_un.grid(row=1, column=1)
        ttk.Button(self, text="เลือกภาพโปรไฟล์", command=self.pick_avatar).grid(row=2, column=0, sticky=tk.W, pady=6)
        self.avatar_lbl = ttk.Label(self, text="(ยังไม่ได้เลือก)")
        self.avatar_lbl.grid(row=2, column=1, sticky=tk.W)

        ttk.Separator(self, orient=tk.HORIZONTAL).grid(row=3, column=0, columnspan=3, sticky="ew", pady=8)
        ttk.Label(self, text="เปลี่ยนรหัสผ่านใหม่").grid(row=4, column=0, sticky=tk.W)
        self.new_pw = ttk.Entry(self, width=28, show="*")
        self.new_pw.grid(row=4, column=1)

        ttk.Button(self, text="บันทึกการเปลี่ยนแปลง", command=self.save_profile).grid(row=5, column=0, columnspan=3, pady=10)

    def pick_avatar(self):
        path = filedialog.askopenfilename(title="เลือกรูปภาพ", filetypes=[("Images","*.png;*.jpg;*.jpeg;*.gif")])
        if path:
            self.avatar_lbl.config(text=path)

    def save_profile(self):
        if not self.app.state.current_user:
            messagebox.showinfo("โปรดเข้าสู่ระบบ", "ต้องเข้าสู่ระบบก่อน")
            self.app.show_frame(SignInFrame)
            return
        uid = self.app.state.current_user["id"]
        new_un = self.new_un.get().strip() or None
        av = self.avatar_lbl.cget("text")
        avatar = av if av and av != "(ยังไม่ได้เลือก)" else None
        if new_un or avatar:
            self.app.db.update_profile(uid, new_username=new_un, avatar_path=avatar)
        if self.new_pw.get().strip():
            try:
                self.app.db.change_password(uid, self.new_pw.get().strip())
            except ValueError as e:
                messagebox.showerror("ผิดพลาด", str(e))
                return
        # refresh current_user from DB
        user = self.app.db.auth_user(self.app.state.current_user["username"], self.new_pw.get().strip() or "")
        cur = self.app.db.conn.cursor()
        cur.execute("SELECT * FROM users WHERE id=?", (uid,))
        self.app.state.current_user = cur.fetchone()
        self.app.header.refresh()
        messagebox.showinfo("สำเร็จ", "บันทึกโปรไฟล์แล้ว")

# -------- Menu List + Add to Cart dialogs --------
class MenuListBase(ttk.Frame):
    CATEGORY = None
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.configure(padding=16)
        ttk.Label(self, text=self.CATEGORY.upper(), font=("Segoe UI", 16, "bold")).pack(anchor=tk.W)

        self.container = ttk.Frame(self)
        self.container.pack(fill=tk.BOTH, expand=True, pady=10)
        self.populate()

    def populate(self):
        for w in self.container.winfo_children():
            w.destroy()
        items = self.app.db.list_menu(self.CATEGORY)
        if not items:
            ttk.Label(self.container, text="ยังไม่มีเมนู").pack()
            return
        for row in items:
            card = ttk.Frame(self.container, padding=8, relief=tk.RIDGE)
            card.pack(fill=tk.X, pady=6)
            left = ttk.Frame(card)
            left.pack(side=tk.LEFT)
            right = ttk.Frame(card)
            right.pack(side=tk.RIGHT)

            # image
            if PIL_OK and row["image_path"] and Path(row["image_path"]).exists():
                img = load_image(Path(row["image_path"]), size=(96,96))
                if img:
                    lbl = ttk.Label(left, image=img)
                    lbl.image = img
                    lbl.pack()
            ttk.Label(left, text=f"฿{row['price']:.2f}").pack()

            ttk.Label(card, text=row["name"], font=("Segoe UI", 12, "bold")).pack(anchor=tk.W)
            if row["cuisine"]:
                ttk.Label(card, text=f"{row['cuisine']}").pack(anchor=tk.W)

            ttk.Button(right, text="เพิ่มลงตะกร้า", command=lambda r=row: self.add_to_cart_dialog(r)).pack()

    def add_to_cart_dialog(self, item_row):
        if not self.app.state.require_login(lambda: self.app.show_frame(SignInFrame)):
            return
        d = tk.Toplevel(self)
        d.title(f"เพิ่ม: {item_row['name']}")
        d.grab_set()

        ttk.Label(d, text=item_row["name"], font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(6,10))
        ttk.Label(d, text=f"ราคา ฿{item_row['price']:.2f}").grid(row=1, column=0, columnspan=2)

        qty_var = tk.IntVar(value=1)
        ttk.Label(d, text="จำนวน").grid(row=2, column=0, sticky=tk.W, pady=4)
        ttk.Spinbox(d, from_=1, to=99, textvariable=qty_var, width=5).grid(row=2, column=1, sticky=tk.W)

        spice_var = tk.StringVar(value="ไม่ระบุ")
        meat_var = tk.StringVar(value="ไม่ระบุ")
        allergen_var = tk.StringVar(value="")
        sweet_var = tk.StringVar(value="ปกติ")
        ice_var = tk.StringVar(value="ปกติ")
        milk_var = tk.StringVar(value="ไม่มี")
        note_var = tk.StringVar(value="")

        if self.CATEGORY == "food":
            ttk.Label(d, text="ระดับความเผ็ด").grid(row=3, column=0, sticky=tk.W)
            ttk.Combobox(d, textvariable=spice_var, values=["ไม่เผ็ด","น้อย","ปานกลาง","มาก"], width=18, state="readonly").grid(row=3, column=1)
            ttk.Label(d, text="ประเภทเนื้อสัตว์").grid(row=4, column=0, sticky=tk.W)
            ttk.Combobox(d, textvariable=meat_var, values=["หมู","ไก่","เนื้อ","ทะเล","มังสวิรัติ","ไม่ระบุ"], width=18, state="readonly").grid(row=4, column=1)
            ttk.Label(d, text="แพ้อาหาร (ระบุได้)").grid(row=5, column=0, sticky=tk.W)
            ttk.Entry(d, textvariable=allergen_var, width=20).grid(row=5, column=1)
        else:
            ttk.Label(d, text="ระดับความหวาน").grid(row=3, column=0, sticky=tk.W)
            ttk.Combobox(d, textvariable=sweet_var, values=["ไม่หวาน","25%","50%","75%","ปกติ"], width=18, state="readonly").grid(row=3, column=1)
            ttk.Label(d, text="ระดับน้ำแข็ง").grid(row=4, column=0, sticky=tk.W)
            ttk.Combobox(d, textvariable=ice_var, values=["ไม่ใส่","น้อย","ปานกลาง","มาก","ปกติ"], width=18, state="readonly").grid(row=4, column=1)
            ttk.Label(d, text="ประเภทนม").grid(row=5, column=0, sticky=tk.W)
            ttk.Combobox(d, textvariable=milk_var, values=["ไม่มี","นมสด","นมถั่วเหลือง","อัลมอนด์"], width=18, state="readonly").grid(row=5, column=1)

        ttk.Label(d, text="โน้ตเพิ่มเติม").grid(row=6, column=0, sticky=tk.W)
        ttk.Entry(d, textvariable=note_var, width=26).grid(row=6, column=1)

        def add():
            qty = max(1, int(qty_var.get()))
            base = float(item_row["price"])  # ราคาไม่บวกตัวเลือก (ปรับสูตรได้ภายหลัง)
            subtotal = base * qty
            item = {
                "item_id": item_row["id"],
                "name": item_row["name"],
                "quantity": qty,
                "base_price": base,
                "spice_level": spice_var.get() if self.CATEGORY=="food" else None,
                "meat_type": meat_var.get() if self.CATEGORY=="food" else None,
                "allergen_note": allergen_var.get() if self.CATEGORY=="food" else None,
                "sweetness": sweet_var.get() if self.CATEGORY=="drink" else None,
                "ice_level": ice_var.get() if self.CATEGORY=="drink" else None,
                "milk_type": milk_var.get() if self.CATEGORY=="drink" else None,
                "note": note_var.get() or None,
                "subtotal": subtotal,
            }
            self.app.state.cart.append(item)
            messagebox.showinfo("ตะกร้า", f"เพิ่ม {item_row['name']} x{qty}")
            d.destroy()

        ttk.Button(d, text="เพิ่มลงตะกร้า", command=add).grid(row=7, column=0, columnspan=2, pady=8)

class FoodFrame(MenuListBase):
    CATEGORY = "food"

class DrinkFrame(MenuListBase):
    CATEGORY = "drink"

class CartFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.configure(padding=16)
        ttk.Label(self, text="ตะกร้าสินค้า", font=("Segoe UI", 16, "bold")).pack(anchor=tk.W)

        self.tree = ttk.Treeview(self, columns=("qty","price","subtotal"), show="headings", height=10)
        self.tree.heading("qty", text="จำนวน")
        self.tree.heading("price", text="ราคา/หน่วย")
        self.tree.heading("subtotal", text="รวม")
        self.tree.column("qty", width=80)
        self.tree.column("price", width=120)
        self.tree.column("subtotal", width=120)
        self.tree.pack(fill=tk.X, pady=8)

        btns = ttk.Frame(self)
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="ลบรายการ", command=self.remove_selected).pack(side=tk.LEFT)
        ttk.Button(btns, text="ล้างตะกร้า", command=self.clear_cart).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="ยืนยันสั่งซื้อ", command=self.checkout).pack(side=tk.RIGHT)

        self.total_lbl = ttk.Label(self, text="รวม: ฿0.00", font=("Segoe UI", 12, "bold"))
        self.total_lbl.pack(anchor=tk.E, pady=6)

        self.refresh()

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        total = 0.0
        for idx, it in enumerate(self.app.state.cart):
            self.tree.insert("", tk.END, iid=str(idx), values=(it["quantity"], f"฿{it['base_price']:.2f}", f"฿{it['subtotal']:.2f}"), text=it["name"])
            total += it["subtotal"]
        self.total_lbl.config(text=f"รวม: ฿{total:.2f}")

    def remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(self.app.state.cart):
            self.app.state.cart.pop(idx)
        self.refresh()

    def clear_cart(self):
        self.app.state.cart.clear()
        self.refresh()

    def checkout(self):
        if not self.app.state.require_login(lambda: self.app.show_frame(SignInFrame)):
            return
        if not self.app.state.cart:
            messagebox.showinfo("ตะกร้า", "ยังไม่มีสินค้าในตะกร้า")
            return
        uid = self.app.state.current_user["id"]
        oid, total = self.app.db.create_order(uid, self.app.state.cart)
        self.app.state.cart.clear()
        self.refresh()
        messagebox.showinfo("สั่งซื้อสำเร็จ", f"หมายเลขออเดอร์ #{oid}\nยอดรวม ฿{total:.2f}")

class AboutFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.configure(padding=20)
        ttk.Label(self, text="About TASTE AND SIP", font=("Segoe UI", 16, "bold")).pack(anchor=tk.W)
        ttk.Label(
            self,
            text=(
                "ร้านอาหารหลากหลายประเทศและเครื่องดื่ม\n"
                "เปิดทุกวัน 10:00–21:00\n"
                "ติดต่อ: 012-345-6789 | tasteandsip@example.com\n"
                "Facebook/IG: @tasteandsip"
            ),
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=8)

# ===================== ADMIN =====================
class AdminLoginFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.configure(padding=24)
        ttk.Label(self, text="ผู้ดูแลระบบ – เข้าสู่ระบบ", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=(0,12))
        ttk.Label(self, text="อีเมลหรือชื่อผู้ใช้").grid(row=1, column=0, sticky=tk.W)
        self.u = ttk.Entry(self, width=30)
        self.u.grid(row=1, column=1, pady=4)
        ttk.Label(self, text="รหัสผ่าน").grid(row=2, column=0, sticky=tk.W)
        self.p = ttk.Entry(self, width=30, show="*")
        self.p.grid(row=2, column=1, pady=4)
        ttk.Button(self, text="เข้าสู่ระบบแอดมิน", command=self.do_login).grid(row=3, column=0, columnspan=2, pady=8)

    def do_login(self):
        user = self.app.db.auth_user(self.u.get().strip(), self.p.get().strip())
        if user and user["role"] == "admin":
            self.app.state.current_user = user
            self.app.header.refresh()
            self.app.show_frame(AdminDashboardFrame)
        else:
            messagebox.showerror("ผิดพลาด", "สิทธิ์ไม่ถูกต้อง หรือข้อมูลไม่ถูกต้อง")

class AdminDashboardFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.configure(padding=16)
        ttk.Label(self, text="Admin Dashboard", font=("Segoe UI", 16, "bold")).pack(anchor=tk.W)

        nav = ttk.Frame(self)
        nav.pack(fill=tk.X, pady=8)
        ttk.Button(nav, text="จัดการเมนู", command=lambda: app.show_frame(AdminMenuFrame)).pack(side=tk.LEFT, padx=4)
        ttk.Button(nav, text="ดูออเดอร์", command=lambda: app.show_frame(AdminOrdersFrame)).pack(side=tk.LEFT, padx=4)
        ttk.Button(nav, text="รายงาน", command=lambda: app.show_frame(AdminReportsFrame)).pack(side=tk.LEFT, padx=4)

        # quick glance report
        box = ttk.Frame(self, padding=8, relief=tk.GROOVE)
        box.pack(fill=tk.BOTH, expand=True)
        # top selling
        ttk.Label(box, text="เมนูขายดี (Top 5)", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W)
        tv = ttk.Treeview(box, columns=("name","qty"), show="headings", height=6)
        tv.heading("name", text="เมนู")
        tv.heading("qty", text="จำนวน")
        tv.column("name", width=240)
        tv.column("qty", width=100, anchor=tk.E)
        tv.pack(fill=tk.X, pady=6)
        for r in self.app.db.top_selling(limit=5):
            tv.insert("", tk.END, values=(r["name"], r["qty"]))

class AdminMenuFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.configure(padding=16)
        ttk.Label(self, text="จัดการเมนู", font=("Segoe UI", 16, "bold")).pack(anchor=tk.W)

        form = ttk.Frame(self)
        form.pack(fill=tk.X, pady=8)
        self.item_id = None
        self.name_var = tk.StringVar()
        self.cat_var = tk.StringVar(value="food")
        self.cui_var = tk.StringVar()
        self.price_var = tk.DoubleVar(value=0.0)
        self.img_var = tk.StringVar()
        self.active_var = tk.IntVar(value=1)

        for i,(label,var) in enumerate([
            ("ชื่อเมนู", self.name_var),
            ("หมวด (food/drink)", self.cat_var),
            ("สัญชาติ", self.cui_var),
            ("ราคา", self.price_var),
            ("รูป (path)", self.img_var),
        ]):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky=tk.W)
            ent = ttk.Entry(form, textvariable=var, width=40)
            ent.grid(row=i, column=1, sticky=tk.W, pady=3)
        ttk.Checkbutton(form, text="แสดงในร้าน (is_active)", variable=self.active_var).grid(row=5, column=1, sticky=tk.W, pady=3)

        btns = ttk.Frame(self)
        btns.pack(fill=tk.X, pady=6)
        ttk.Button(btns, text="บันทึก/แก้ไข", command=self.save_item).pack(side=tk.LEFT)
        ttk.Button(btns, text="ลบ (ปิดการแสดง)", command=self.delete_item).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="รีเฟรช", command=self.refresh_list).pack(side=tk.LEFT)

        self.tv = ttk.Treeview(self, columns=("id","name","cat","price","active"), show="headings", height=12)
        for c, text, w in [("id","ID",50),("name","ชื่อ",200),("cat","หมวด",80),("price","ราคา",80),("active","แสดง",60)]:
            self.tv.heading(c, text=text)
            self.tv.column(c, width=w)
        self.tv.pack(fill=tk.BOTH, expand=True, pady=6)
        self.tv.bind("<<TreeviewSelect>>", self.on_select)

        self.refresh_list()

    def refresh_list(self):
        for i in self.tv.get_children():
            self.tv.delete(i)
        cur = self.app.db.conn.cursor()
        cur.execute("SELECT id,name,category,price,is_active FROM menu_items ORDER BY category,name")
        for r in cur.fetchall():
            self.tv.insert("", tk.END, values=(r["id"], r["name"], r["category"], f"{r['price']:.2f}", r["is_active"]))

    def on_select(self, _):
        sel = self.tv.selection()
        if not sel: return
        vals = self.tv.item(sel[0], "values")
        iid = int(vals[0])
        cur = self.app.db.conn.cursor()
        cur.execute("SELECT * FROM menu_items WHERE id=?", (iid,))
        r = cur.fetchone()
        self.item_id = r["id"]
        self.name_var.set(r["name"])
        self.cat_var.set(r["category"])
        self.cui_var.set(r["cuisine"] or "")
        self.price_var.set(r["price"])
        self.img_var.set(r["image_path"] or "")
        self.active_var.set(r["is_active"])

    def save_item(self):
        try:
            self.app.db.upsert_menu_item(
                self.item_id,
                self.name_var.get().strip(),
                self.cat_var.get().strip(),
                self.cui_var.get().strip() or None,
                float(self.price_var.get()),
                self.img_var.get().strip() or None,
                int(self.active_var.get()),
            )
            messagebox.showinfo("สำเร็จ", "บันทึกเมนูแล้ว")
            self.refresh_list()
        except Exception as e:
            messagebox.showerror("ผิดพลาด", str(e))

    def delete_item(self):
        if self.item_id:
            self.app.db.delete_menu_item(self.item_id)
            messagebox.showinfo("สำเร็จ", "ปิดการแสดงเมนูแล้ว")
            self.refresh_list()

class AdminOrdersFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.configure(padding=16)
        ttk.Label(self, text="ออเดอร์", font=("Segoe UI", 16, "bold")).pack(anchor=tk.W)

        self.filter_var = tk.StringVar(value="all")
        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=6)
        ttk.Label(top, text="สถานะ:").pack(side=tk.LEFT)
        ttk.Combobox(top, textvariable=self.filter_var, state="readonly", values=["all","pending","paid","preparing","completed","cancelled"], width=12).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="รีเฟรช", command=self.refresh).pack(side=tk.LEFT)

        self.tv = ttk.Treeview(self, columns=("id","user","status","total","created"), show="headings", height=14)
        for c,t,w in [("id","ID",60),("user","UserID",80),("status","สถานะ",100),("total","ยอด",100),("created","เวลา",160)]:
            self.tv.heading(c, text=t)
            self.tv.column(c, width=w)
        self.tv.pack(fill=tk.BOTH, expand=True, pady=6)

        bottom = ttk.Frame(self)
        bottom.pack(fill=tk.X)
        self.new_status = tk.StringVar(value="preparing")
        ttk.Label(bottom, text="เปลี่ยนสถานะเป็น:").pack(side=tk.LEFT)
        ttk.Combobox(bottom, textvariable=self.new_status, state="readonly", values=["pending","paid","preparing","completed","cancelled"], width=14).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text="อัปเดต", command=self.update_status).pack(side=tk.LEFT)

        self.refresh()

    def refresh(self):
        for i in self.tv.get_children(): self.tv.delete(i)
        f = self.filter_var.get()
        rows = self.app.db.list_orders(None if f=="all" else f)
        for r in rows:
            self.tv.insert("", tk.END, values=(r["id"], r["user_id"], r["status"], f"{r['total']:.2f}", r["created_at"]))

    def update_status(self):
        sel = self.tv.selection()
        if not sel: return
        order_id = int(self.tv.item(sel[0], "values")[0])
        self.app.db.update_order_status(order_id, self.new_status.get())
        self.refresh()

class AdminReportsFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.configure(padding=16)
        ttk.Label(self, text="รายงานยอดขาย", font=("Segoe UI", 16, "bold")).pack(anchor=tk.W)

        top = ttk.Frame(self)
        top.pack(fill=tk.X)
        self.days_var = tk.IntVar(value=30)
        ttk.Label(top, text="ช่วงวันล่าสุด").pack(side=tk.LEFT)
        ttk.Spinbox(top, from_=7, to=365, textvariable=self.days_var, width=6).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="รีเฟรช", command=self.refresh).pack(side=tk.LEFT)

        self.tv_daily = ttk.Treeview(self, columns=("date","revenue"), show="headings", height=8)
        self.tv_daily.heading("date", text="วันที่")
        self.tv_daily.heading("revenue", text="ยอดรวม")
        self.tv_daily.column("date", width=120)
        self.tv_daily.column("revenue", width=120)
        self.tv_daily.pack(fill=tk.X, pady=6)

        ttk.Label(self, text="Top 10 เมนูขายดี").pack(anchor=tk.W, pady=(10,0))
        self.tv_top = ttk.Treeview(self, columns=("name","qty"), show="headings", height=8)
        self.tv_top.heading("name", text="เมนู")
        self.tv_top.heading("qty", text="จำนวน")
        self.tv_top.column("name", width=240)
        self.tv_top.column("qty", width=100)
        self.tv_top.pack(fill=tk.X, pady=6)

        self.refresh()

    def refresh(self):
        for i in self.tv_daily.get_children(): self.tv_daily.delete(i)
        for i in self.tv_top.get_children(): self.tv_top.delete(i)
        for r in self.app.db.revenue_by_day(days=int(self.days_var.get())):
            self.tv_daily.insert("", tk.END, values=(r["d"], f"{r['revenue']:.2f}"))
        for r in self.app.db.top_selling(limit=10):
            self.tv_top.insert("", tk.END, values=(r["name"], r["qty"]))

# ===================== APP ROOT / ROUTER =====================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("960x640")
        self.minsize(900, 600)

        # ttk theme
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        self.db = DB(DB_PATH)
        self.state = SessionState()

        self.header = Header(self, self)
        self.header.pack(side=tk.TOP, fill=tk.X)

        self.container = ttk.Frame(self)
        self.container.pack(fill=tk.BOTH, expand=True)

        self.frames = {}
        for F in (HomeFrame, SignInFrame, SignUpFrame, ProfileFrame, FoodFrame, DrinkFrame, CartFrame, AboutFrame,
                  AdminLoginFrame, AdminDashboardFrame, AdminMenuFrame, AdminOrdersFrame, AdminReportsFrame):
            frame = F(self.container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(HomeFrame)

    def show_frame(self, cls):
        frame = self.frames[cls]
        frame.tkraise()
        # call refresh if available
        if hasattr(frame, "refresh"):
            try:
                frame.refresh()
            except Exception:
                pass
        self.header.refresh()

# ===================== MAIN =====================
if __name__ == "__main__":
    ASSETS_DIR.mkdir(exist_ok=True)
    (ASSETS_DIR/"home_carousel").mkdir(parents=True, exist_ok=True)
    (ASSETS_DIR/"food").mkdir(parents=True, exist_ok=True)
    (ASSETS_DIR/"drink").mkdir(parents=True, exist_ok=True)

    app = App()
    app.mainloop()
