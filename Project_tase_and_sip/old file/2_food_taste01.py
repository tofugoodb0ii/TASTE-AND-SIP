# TASTE AND SIP — Desktop App (customtkinter + SQLite)
# ---------------------------------------------------
# Features
# - Public home with image carousel and top navigation (Sign In, About Us, Cart, Drink, Food)
# - Browse menus without login; must log in to add items to cart or checkout
# - User auth (login / signup). Admin role can manage menu, orders, and see sales reports
# - Cart with item options (food: spiciness, protein, allergy note; drink: sweetness, ice, milk type)
# - SQLite storage for users, menu items, orders, order items
# - Seed data on first run
#
# Requirements:
#   pip install customtkinter Pillow
#
# Run:
#   python taste_and_sip.py
#
# Notes:
# - Place any images in an ./assets folder (e.g., assets/logo.png, assets/home1.jpg ...). Placeholders are used if missing.
# - Default admin: username=admin  password=admin123  (Change in-app via Manage Users or update DB.)

import os
import json
import sqlite3
import hashlib
from datetime import datetime, date
from collections import defaultdict

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw

DB_PATH = "taste_and_sip.db"
ASSETS_DIR = "assets"

APP_TITLE = "TASTE AND SIP"
APP_SLOGAN = "Taste and Sip — where every flavor tells a story and every sip sparks connection."
PHONE = "095-475-1704"

# -----------------------------
# Database helpers
# -----------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(pw: str) -> str:
    # Lightweight hash (not for production).
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user','admin'))
        );
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL CHECK(category IN ('FOOD','DRINK')),
            price REAL NOT NULL,
            image_path TEXT,
            has_milk INTEGER NOT NULL DEFAULT 0
        );
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total REAL NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            options_json TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (item_id) REFERENCES menu_items(id)
        );
        """
    )

    # Seed admin
    c.execute("SELECT COUNT(*) AS n FROM users WHERE role='admin'")
    if c.fetchone()[0] == 0:
        c.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
            ("admin", hash_password("admin123"), "admin"),
        )

    # Seed sample menu if empty
    c.execute("SELECT COUNT(*) AS n FROM menu_items")
    if c.fetchone()[0] == 0:
        seed_items = [
            ("ต้มยำกุ้ง (Tom Yum Kung)", "FOOD", 150.0, os.path.join(ASSETS_DIR, "food_tomyum.jpg"), 0),
            ("ข้าวผัดกุ้ง (Shrimp Fried Rice)", "FOOD", 120.0, os.path.join(ASSETS_DIR, "food_friedrice.jpg"), 0),
            ("Pad Thai", "FOOD", 130.0, os.path.join(ASSETS_DIR, "food_padthai.jpg"), 0),
            ("Green Curry", "FOOD", 160.0, os.path.join(ASSETS_DIR, "food_green_curry.jpg"), 0),
            ("Milk Tea", "DRINK", 65.0, os.path.join(ASSETS_DIR, "drink_milktea.jpg"), 1),
            ("Americano", "DRINK", 60.0, os.path.join(ASSETS_DIR, "drink_americano.jpg"), 0),
            ("Matcha Latte", "DRINK", 70.0, os.path.join(ASSETS_DIR, "drink_matcha.jpg"), 1),
            ("Lemon Soda", "DRINK", 55.0, os.path.join(ASSETS_DIR, "drink_lemon_soda.jpg"), 0),
        ]
        c.executemany(
            "INSERT INTO menu_items (name, category, price, image_path, has_milk) VALUES (?,?,?,?,?)",
            seed_items,
        )

    conn.commit()
    conn.close()


# -----------------------------
# UI Utilities
# -----------------------------

def ensure_assets():
    if not os.path.isdir(ASSETS_DIR):
        os.makedirs(ASSETS_DIR, exist_ok=True)


def load_image(path: str, size=(120, 90)):
    try:
        img = Image.open(path)
    except Exception:
        # Create placeholder
        img = Image.new("RGB", size, (200, 200, 200))
        draw = ImageDraw.Draw(img)
        draw.text((10, size[1]//2 - 7), "No Image", fill=(80, 80, 80))
        return ImageTk.PhotoImage(img)
    img = img.copy()
    img.thumbnail(size, Image.LANCZOS)
    return ImageTk.PhotoImage(img)


# -----------------------------
# App
# -----------------------------

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title(APP_TITLE)
        self.geometry("1100x720")
        self.minsize(980, 640)

        self.current_user = None  # dict: {id, username, role}
        self.session_cart = []  # list of dicts: {item_row, qty, options}

        ensure_assets()
        init_db()

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.navbar = TopNav(self, on_nav=self.navigate, get_user=self.get_user, sign_out=self.sign_out)
        self.navbar.grid(row=0, column=0, sticky="ew")

        self.container = ctk.CTkFrame(self)
        self.container.grid(row=1, column=0, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.pages = {}
        self.show_page(HomePage)

    # Navigation
    def navigate(self, target: str):
        mapping = {
            "HOME": HomePage,
            "FOOD": FoodPage,
            "DRINK": DrinkPage,
            "CART": CartPage,
            "ABOUT": AboutPage,
            "LOGIN": LoginPage,
            "SIGNUP": SignupPage,
            "ADMIN": AdminDashboard,
        }
        page_cls = mapping.get(target, HomePage)
        self.show_page(page_cls)

    def show_page(self, page_cls):
        # Destroy current
        for child in self.container.winfo_children():
            child.destroy()
        page = page_cls(self.container, app=self)
        page.grid(row=0, column=0, sticky="nsew")
        self.pages[page_cls.__name__] = page
        # Update nav (e.g., account button state)
        self.navbar.refresh()

    def get_user(self):
        return self.current_user

    def sign_out(self):
        self.current_user = None
        self.session_cart.clear()
        messagebox.showinfo("Signed out", "คุณได้ออกจากระบบแล้ว")
        self.navigate("HOME")

    # Cart logic
    def require_login(self):
        if not self.current_user:
            messagebox.showwarning("ต้องล็อกอินก่อน", "กรุณาเข้าสู่ระบบก่อนสั่งซื้อ")
            self.navigate("LOGIN")
            return False
        return True

    def add_to_cart(self, item_row: sqlite3.Row, qty: int, options: dict):
        if not self.require_login():
            return
        self.session_cart.append({"item": dict(item_row), "qty": qty, "options": options})
        messagebox.showinfo("เพิ่มลงตะกร้า", f"เพิ่ม {item_row['name']} x{qty} ในตะกร้าแล้ว")

    def place_order(self):
        if not self.current_user:
            return
        if not self.session_cart:
            messagebox.showwarning("ตะกร้าว่าง", "กรุณาเพิ่มสินค้าในตะกร้า")
            return
        conn = get_db()
        c = conn.cursor()
        total = 0.0
        for line in self.session_cart:
            total += line["item"]["price"] * line["qty"]
        c.execute(
            "INSERT INTO orders (user_id, total, created_at) VALUES (?,?,?)",
            (self.current_user["id"], total, datetime.now().isoformat(timespec="seconds")),
        )
        order_id = c.lastrowid
        for line in self.session_cart:
            c.execute(
                "INSERT INTO order_items (order_id, item_id, quantity, unit_price, options_json) VALUES (?,?,?,?,?)",
                (
                    order_id,
                    line["item"]["id"],
                    line["qty"],
                    float(line["item"]["price"]),
                    json.dumps(line["options"], ensure_ascii=False),
                ),
            )
        conn.commit()
        conn.close()
        self.session_cart.clear()
        messagebox.showinfo("สั่งซื้อสำเร็จ", "ขอบคุณสำหรับการสั่งซื้อ! คำสั่งซื้อของคุณถูกบันทึกแล้ว")
        self.navigate("HOME")


# -----------------------------
# Top Navigation
# -----------------------------

class TopNav(ctk.CTkFrame):
    def __init__(self, master, on_nav, get_user, sign_out):
        super().__init__(master)
        self.on_nav = on_nav
        self.get_user = get_user
        self.sign_out = sign_out

        self.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w", padx=10, pady=8)
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e", padx=10)

        # Logo + Title
        self.logo_img = load_image(os.path.join(ASSETS_DIR, "logo.png"), size=(32, 32))
        self.logo_lbl = ctk.CTkLabel(left, image=self.logo_img, text="")
        self.logo_lbl.pack(side="left", padx=(0, 8))
        self.title_lbl = ctk.CTkLabel(left, text=APP_TITLE, font=("Helvetica", 18, "bold"))
        self.title_lbl.pack(side="left")

        # Right menu buttons
        self.btn_food = ctk.CTkButton(right, text="FOOD", command=lambda: self.on_nav("FOOD"), width=90)
        self.btn_drink = ctk.CTkButton(right, text="DRINK", command=lambda: self.on_nav("DRINK"), width=90)
        self.btn_cart = ctk.CTkButton(right, text="CART", command=lambda: self.on_nav("CART"), width=90)
        self.btn_about = ctk.CTkButton(right, text="ABOUT US", command=lambda: self.on_nav("ABOUT"), width=110)
        self.account_menu = ctk.CTkOptionMenu(right, values=["SIGN IN", "SIGN UP"], command=self._account_action, width=110)
        self.btn_admin = ctk.CTkButton(right, text="ADMIN", command=lambda: self.on_nav("ADMIN"), width=90)

        for w in [self.btn_food, self.btn_drink, self.btn_cart, self.btn_about, self.account_menu, self.btn_admin]:
            w.pack(side="left", padx=6)

        self.refresh()

    def _account_action(self, choice):
        if choice == "SIGN IN":
            self.on_nav("LOGIN")
        elif choice == "SIGN UP":
            self.on_nav("SIGNUP")

    def refresh(self):
        user = self.get_user()
        if user:
            # Replace account menu with username + Sign out
            if hasattr(self, "user_menu"):
                self.user_menu.destroy()
            if hasattr(self, "signout_btn"):
                self.signout_btn.destroy()
            try:
                self.account_menu.pack_forget()
            except Exception:
                pass
            self.user_menu = ctk.CTkLabel(self, text=f"Hi, {user['username']} ({user['role']})", font=("Helvetica", 12))
            self.user_menu.grid(row=0, column=2, sticky="e", padx=10)
            self.signout_btn = ctk.CTkButton(self, text="Sign out", command=self.sign_out, width=90)
            self.signout_btn.grid(row=0, column=3, sticky="e", padx=(0, 10))
            self.btn_admin.configure(state=("normal" if user["role"] == "admin" else "disabled"))
        else:
            # Show account dropdown
            if hasattr(self, "user_menu"):
                self.user_menu.destroy()
            if hasattr(self, "signout_btn"):
                self.signout_btn.destroy()
            self.account_menu.set("SIGN IN")
            self.account_menu.pack(side="left", padx=6)
            self.btn_admin.configure(state="disabled")


# -----------------------------
# Pages
# -----------------------------

class HomePage(ctk.CTkFrame):
    def __init__(self, master, app: App):
        super().__init__(master)
        self.app = app
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Hero / Carousel
        self.carousel = Carousel(self, image_paths=self._gather_home_images())
        self.carousel.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)

    def _gather_home_images(self):
        # Collect some image paths; fallback to menu item images
        paths = []
        for fname in ["home1.jpg", "home2.jpg", "home3.jpg"]:
            p = os.path.join(ASSETS_DIR, fname)
            if os.path.exists(p):
                paths.append(p)
        if paths:
            return paths
        # fallback from DB
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT image_path FROM menu_items WHERE image_path IS NOT NULL")
        rows = [r[0] for r in c.fetchall() if r[0]]
        conn.close()
        return rows[:6]


class Carousel(ctk.CTkFrame):
    def __init__(self, master, image_paths):
        super().__init__(master)
        self.image_paths = image_paths if image_paths else []
        self.index = 0
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.prev_btn = ctk.CTkButton(self, text="<", width=40, command=self.prev)
        self.next_btn = ctk.CTkButton(self, text=">", width=40, command=self.next)
        self.prev_btn.grid(row=0, column=0, sticky="nsw", padx=(8, 4))
        self.next_btn.grid(row=0, column=2, sticky="nse", padx=(4, 8))

        self.canvas = ctk.CTkLabel(self, text="", width=800, height=420)
        self.canvas.grid(row=0, column=1, sticky="nsew")
        self.render()

    def render(self):
        if not self.image_paths:
            img = load_image("", size=(860, 420))
            self.canvas.configure(image=img)
            self.canvas.image = img
            return
        path = self.image_paths[self.index % len(self.image_paths)]
        img = load_image(path, size=(860, 420))
        self.canvas.configure(image=img)
        self.canvas.image = img

    def prev(self):
        if self.image_paths:
            self.index = (self.index - 1) % len(self.image_paths)
            self.render()

    def next(self):
        if self.image_paths:
            self.index = (self.index + 1) % len(self.image_paths)
            self.render()


class MenuListPage(ctk.CTkScrollableFrame):
    CATEGORY = ""  # override

    def __init__(self, master, app: App):
        super().__init__(master)
        self.app = app
        self.render()

    def _fetch_items(self):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM menu_items WHERE category=? ORDER BY id DESC", (self.CATEGORY,))
        rows = c.fetchall()
        conn.close()
        return rows

    def render(self):
        for child in self.winfo_children():
            child.destroy()
        rows = self._fetch_items()
        if not rows:
            ctk.CTkLabel(self, text="No items yet.").pack(pady=30)
            return
        for r in rows:
            self._render_card(r)

    def _render_card(self, row):
        card = ctk.CTkFrame(self)
        card.pack(fill="x", padx=16, pady=10)
        img = load_image(row["image_path"] if row["image_path"] else "", size=(140, 100))
        img_lbl = ctk.CTkLabel(card, image=img, text="")
        img_lbl.image = img
        img_lbl.pack(side="left", padx=10, pady=10)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(side="left", fill="x", expand=True, padx=10)
        name_lbl = ctk.CTkLabel(body, text=row["name"], font=("Helvetica", 15, "bold"))
        name_lbl.pack(anchor="w")
        price_lbl = ctk.CTkLabel(body, text=f"฿{row['price']:.2f}")
        price_lbl.pack(anchor="w")

        action = ctk.CTkFrame(card, fg_color="transparent")
        action.pack(side="right", padx=10)
        qty_var = tk.IntVar(value=1)
        qty_spin = ctk.CTkSpinbox(action, from_=1, to=20, width=90, variable=qty_var)
        qty_spin.pack(pady=(12, 6))
        add_btn = ctk.CTkButton(action, text="Add to cart", command=lambda r=row, q=qty_var: self._add_clicked(r, q.get()))
        add_btn.pack(pady=(0, 12))

    def _add_clicked(self, row, qty):
        # Show options dialog depending on category
        if self.CATEGORY == "FOOD":
            OptionsDialogFood(self, on_confirm=lambda opts: self.app.add_to_cart(row, qty, opts))
        else:
            OptionsDialogDrink(self, has_milk=bool(row["has_milk"]), on_confirm=lambda opts: self.app.add_to_cart(row, qty, opts))


class FoodPage(MenuListPage):
    CATEGORY = "FOOD"


class DrinkPage(MenuListPage):
    CATEGORY = "DRINK"


class CartPage(ctk.CTkFrame):
    def __init__(self, master, app: App):
        super().__init__(master)
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.render()

    def render(self):
        for child in self.winfo_children():
            child.destroy()

        title = ctk.CTkLabel(self, text="CART", font=("Helvetica", 18, "bold"))
        title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 0))

        if not self.app.session_cart:
            ctk.CTkLabel(self, text="ตะกร้าว่าง").grid(row=1, column=0, padx=16, pady=40, sticky="w")
            return

        total = 0.0
        rowi = 1
        for line in self.app.session_cart:
            item = line["item"]
            qty = line["qty"]
            opts = line["options"]
            total += item["price"] * qty
            txt = f"{item['name']}  x{qty}  — ฿{item['price']*qty:.2f}\nตัวเลือก: {json.dumps(opts, ensure_ascii=False)}"
            ctk.CTkLabel(self, text=txt, anchor="w", justify="left").grid(row=rowi, column=0, sticky="ew", padx=16, pady=6)
            rowi += 1

        ctk.CTkLabel(self, text=f"รวมทั้งหมด: ฿{total:.2f}", font=("Helvetica", 14, "bold")).grid(row=rowi, column=0, sticky="e", padx=16, pady=12)
        rowi += 1

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=rowi, column=0, sticky="e", padx=16, pady=(6, 16))
        ctk.CTkButton(btns, text="ล้างตะกร้า", fg_color="#999999", command=self._clear).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="ชำระเงิน", command=self._checkout).pack(side="left", padx=6)

    def _clear(self):
        self.app.session_cart.clear()
        self.render()

    def _checkout(self):
        if not self.app.require_login():
            return
        self.app.place_order()


class AboutPage(ctk.CTkFrame):
    def __init__(self, master, app: App):
        super().__init__(master)
        ctk.CTkLabel(self, text="ABOUT US", font=("Helvetica", 18, "bold")).pack(anchor="w", padx=16, pady=(16, 8))
        ctk.CTkLabel(self, text=APP_SLOGAN, wraplength=860, justify="left").pack(anchor="w", padx=16)
        ctk.CTkLabel(self, text=f"ติดต่อ: {PHONE}").pack(anchor="w", padx=16, pady=8)


class LoginPage(ctk.CTkFrame):
    def __init__(self, master, app: App):
        super().__init__(master)
        self.app = app

        ctk.CTkLabel(self, text="SIGN IN", font=("Helvetica", 18, "bold")).pack(pady=(20, 10))

        self.u_entry = ctk.CTkEntry(self, placeholder_text="USERNAME", width=320)
        self.p_entry = ctk.CTkEntry(self, placeholder_text="PASSWORD", show="*", width=320)
        self.u_entry.pack(pady=6)
        self.p_entry.pack(pady=6)

        ctk.CTkButton(self, text="SIGN IN", command=self._login).pack(pady=12)
        link_frame = ctk.CTkFrame(self, fg_color="transparent")
        link_frame.pack(pady=6)
        ctk.CTkButton(link_frame, text="Create account", width=140, command=lambda: self.app.navigate("SIGNUP")).pack(side="left", padx=6)
        ctk.CTkButton(link_frame, text="Forgot password", width=140, command=self._forgot).pack(side="left", padx=6)

    def _login(self):
        u = self.u_entry.get().strip()
        p = self.p_entry.get().strip()
        if not u or not p:
            messagebox.showwarning("กรอกข้อมูลไม่ครบ", "กรุณากรอกชื่อผู้ใช้และรหัสผ่าน")
            return
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (u,))
        row = c.fetchone()
        conn.close()
        if row and row["password_hash"] == hash_password(p):
            self.app.current_user = {"id": row["id"], "username": row["username"], "role": row["role"]}
            messagebox.showinfo("ยินดีต้อนรับ", f"สวัสดี {row['username']}")
            self.app.navigate("HOME")
        else:
            messagebox.showerror("เข้าสู่ระบบไม่สำเร็จ", "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

    def _forgot(self):
        messagebox.showinfo("ลืมรหัสผ่าน", "โปรดติดต่อผู้ดูแลร้านเพื่อรีเซ็ตรหัสผ่าน")


class SignupPage(ctk.CTkFrame):
    def __init__(self, master, app: App):
        super().__init__(master)

        self.app = app
        ctk.CTkLabel(self, text="CREATE ACCOUNT", font=("Helvetica", 18, "bold")).pack(pady=(20, 10))
        self.u = ctk.CTkEntry(self, placeholder_text="USERNAME", width=320)
        self.p = ctk.CTkEntry(self, placeholder_text="PASSWORD", show="*", width=320)
        self.u.pack(pady=6)
        self.p.pack(pady=6)
        ctk.CTkButton(self, text="SIGN UP", command=self._create).pack(pady=12)

    def _create(self):
        u = self.u.get().strip()
        p = self.p.get().strip()
        if not u or not p:
            messagebox.showwarning("กรอกข้อมูลไม่ครบ", "กรุณากรอกชื่อผู้ใช้และรหัสผ่าน")
            return
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password_hash, role) VALUES (?,?,?)", (u, hash_password(p), "user"))
            conn.commit()
        except sqlite3.IntegrityError:
            messagebox.showerror("สมัครไม่สำเร็จ", "ชื่อผู้ใช้ถูกใช้แล้ว")
            conn.close()
            return
        conn.close()
        messagebox.showinfo("สำเร็จ", "สร้างบัญชีเรียบร้อย กรุณาเข้าสู่ระบบ")
        self.app.navigate("LOGIN")


# -----------------------------
# Options dialogs
# -----------------------------

class OptionsDialogFood(tk.Toplevel):
    def __init__(self, master, on_confirm):
        super().__init__(master)
        self.title("ตัวเลือกอาหาร")
        self.geometry("360x320")
        self.resizable(False, False)
        self.transient(master)
        self.on_confirm = on_confirm

        self.spicy_var = tk.StringVar(value="Medium")
        self.protein_var = tk.StringVar(value="Chicken")
        self.note_var = tk.StringVar()

        frm = ctk.CTkFrame(self)
        frm.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(frm, text="ระดับความเผ็ด").pack(anchor="w")
        self.spicy = ctk.CTkOptionMenu(frm, values=["None","Mild","Medium","Hot"], variable=self.spicy_var)
        self.spicy.pack(fill="x", pady=6)

        ctk.CTkLabel(frm, text="ประเภทเนื้อสัตว์").pack(anchor="w")
        self.protein = ctk.CTkOptionMenu(frm, values=["Chicken","Beef","Pork","Shrimp","Tofu"], variable=self.protein_var)
        self.protein.pack(fill="x", pady=6)

        ctk.CTkLabel(frm, text="แพ้อาหาร/โน้ตเพิ่มเติม").pack(anchor="w")
        self.note = ctk.CTkEntry(frm, textvariable=self.note_var, placeholder_text="เช่น ไม่เอาถั่วงอก")
        self.note.pack(fill="x", pady=6)

        ctk.CTkButton(frm, text="ยืนยัน", command=self._ok).pack(pady=10)

        self.grab_set()
        self.wait_visibility()

    def _ok(self):
        opts = {
            "spiciness": self.spicy_var.get(),
            "protein": self.protein_var.get(),
            "note": self.note_var.get().strip(),
        }
        self.on_confirm(opts)
        self.destroy()


class OptionsDialogDrink(tk.Toplevel):
    def __init__(self, master, has_milk: bool, on_confirm):
        super().__init__(master)
        self.title("ตัวเลือกเครื่องดื่ม")
        self.geometry("360x360")
        self.resizable(False, False)
        self.transient(master)
        self.on_confirm = on_confirm

        self.sweet_var = tk.StringVar(value="50%")
        self.ice_var = tk.StringVar(value="Regular")
        self.milk_var = tk.StringVar(value="None" if not has_milk else "Whole")

        frm = ctk.CTkFrame(self)
        frm.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(frm, text="ระดับความหวาน").pack(anchor="w")
        self.sweet = ctk.CTkOptionMenu(frm, values=["0%","25%","50%","75%","100%"], variable=self.sweet_var)
        self.sweet.pack(fill="x", pady=6)

        ctk.CTkLabel(frm, text="ระดับน้ำแข็ง").pack(anchor="w")
        self.ice = ctk.CTkOptionMenu(frm, values=["No Ice","Less","Regular","Extra"], variable=self.ice_var)
        self.ice.pack(fill="x", pady=6)

        ctk.CTkLabel(frm, text="ประเภทนม").pack(anchor="w")
        milk_values = ["None","Whole","Oat","Almond"] if has_milk else ["None"]
        self.milk = ctk.CTkOptionMenu(frm, values=milk_values, variable=self.milk_var)
        self.milk.pack(fill="x", pady=6)

        ctk.CTkButton(frm, text="ยืนยัน", command=self._ok).pack(pady=10)

        self.grab_set()
        self.wait_visibility()

    def _ok(self):
        opts = {
            "sweetness": self.sweet_var.get(),
            "ice": self.ice_var.get(),
            "milk": self.milk_var.get(),
        }
        self.on_confirm(opts)
        self.destroy()


# -----------------------------
# Admin
# -----------------------------

class AdminDashboard(ctk.CTkFrame):
    def __init__(self, master, app: App):
        super().__init__(master)
        self.app = app
        if not self.app.current_user or self.app.current_user["role"] != "admin":
            ctk.CTkLabel(self, text="กรุณาเข้าสู่ระบบแอดมิน", font=("Helvetica", 16)).pack(pady=40)
            ctk.CTkButton(self, text="ไปหน้าเข้าสู่ระบบ", command=lambda: self.app.navigate("LOGIN")).pack()
            return

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=12, pady=12)

        self.tab_menu = tabs.add("Manage Menu")
        self.tab_orders = tabs.add("Orders")
        self.tab_reports = tabs.add("Reports")

        self._build_menu_tab()
        self._build_orders_tab()
        self._build_reports_tab()

    # Manage Menu
    def _build_menu_tab(self):
        frm = ctk.CTkFrame(self.tab_menu)
        frm.pack(fill="both", expand=True, padx=10, pady=10)
        frm.grid_columnconfigure(1, weight=1)

        self.m_name = ctk.CTkEntry(frm, placeholder_text="Name")
        self.m_cat = ctk.CTkOptionMenu(frm, values=["FOOD","DRINK"])
        self.m_price = ctk.CTkEntry(frm, placeholder_text="Price (฿)")
        self.m_img = ctk.CTkEntry(frm, placeholder_text="Image path (optional)")
        self.m_milk = tk.IntVar(value=0)
        self.m_has_milk = ctk.CTkCheckBox(frm, text="Has milk (drinks)", variable=self.m_milk)
        add_btn = ctk.CTkButton(frm, text="Add / Update", command=self._add_update_item)

        self.m_id_hidden = tk.StringVar(value="")

        self.m_name.grid(row=0, column=0, padx=6, pady=6, sticky="ew", columnspan=2)
        self.m_cat.grid(row=1, column=0, padx=6, pady=6, sticky="ew")
        self.m_price.grid(row=1, column=1, padx=6, pady=6, sticky="ew")
        self.m_img.grid(row=2, column=0, padx=6, pady=6, sticky="ew", columnspan=2)
        self.m_has_milk.grid(row=3, column=0, padx=6, pady=6, sticky="w")
        add_btn.grid(row=3, column=1, padx=6, pady=6, sticky="e")

        # Table
        self.tree = ttk.Treeview(frm, columns=("id","name","cat","price"), show="headings", height=12)
        for col, w in [("id",50),("name",260),("cat",80),("price",80)]:
            self.tree.heading(col, text=col.upper())
            self.tree.column(col, width=w, anchor="center")
        self.tree.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=6, pady=10)
        frm.grid_rowconfigure(4, weight=1)

        btns = ctk.CTkFrame(frm, fg_color="transparent")
        btns.grid(row=5, column=0, columnspan=2, sticky="e", pady=(0, 8))
        ctk.CTkButton(btns, text="Load", command=self._load_items).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Edit Selected", command=self._edit_selected).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Delete Selected", fg_color="#b3261e", command=self._delete_selected).pack(side="left", padx=6)

        self._load_items()

    def _load_items(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, name, category, price FROM menu_items ORDER BY id DESC")
        for r in c.fetchall():
            self.tree.insert("", "end", values=(r[0], r[1], r[2], f"{r[3]:.2f}"))
        conn.close()

    def _add_update_item(self):
        name = self.m_name.get().strip()
        cat = self.m_cat.get()
        price = self.m_price.get().strip()
        imgp = self.m_img.get().strip() or None
        has_milk = 1 if self.m_milk.get() == 1 else 0
        if not name or not price:
            messagebox.showwarning("ข้อมูลไม่ครบ", "กรุณากรอกชื่อและราคา")
            return
        try:
            pricef = float(price)
        except ValueError:
            messagebox.showerror("ราคาไม่ถูกต้อง", "กรุณากรอกตัวเลข")
            return
        conn = get_db()
        c = conn.cursor()
        if self.m_id_hidden.get():
            mid = int(self.m_id_hidden.get())
            c.execute("UPDATE menu_items SET name=?, category=?, price=?, image_path=?, has_milk=? WHERE id=?",
                      (name, cat, pricef, imgp, has_milk, mid))
            conn.commit()
            conn.close()
            messagebox.showinfo("แก้ไขแล้ว", "บันทึกรายการสำเร็จ")
        else:
            c.execute("INSERT INTO menu_items (name, category, price, image_path, has_milk) VALUES (?,?,?,?,?)",
                      (name, cat, pricef, imgp, has_milk))
            conn.commit()
            conn.close()
            messagebox.showinfo("เพิ่มแล้ว", "เพิ่มเมนูสำเร็จ")
        self.m_id_hidden.set("")
        self.m_name.delete(0, tk.END)
        self.m_price.delete(0, tk.END)
        self.m_img.delete(0, tk.END)
        self._load_items()

    def _edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], 'values')
        mid = int(vals[0])
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM menu_items WHERE id=?", (mid,))
        r = c.fetchone()
        conn.close()
        if r:
            self.m_id_hidden.set(str(r["id"]))
            self.m_name.delete(0, tk.END); self.m_name.insert(0, r["name"])
            self.m_cat.set(r["category"])
            self.m_price.delete(0, tk.END); self.m_price.insert(0, str(r["price"]))
            self.m_img.delete(0, tk.END); self.m_img.insert(0, r["image_path"] or "")
            self.m_milk.set(int(r["has_milk"]))

    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], 'values')
        mid = int(vals[0])
        if not messagebox.askyesno("ยืนยัน", f"ลบเมนู #{mid} ?"):
            return
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM menu_items WHERE id=?", (mid,))
        conn.commit(); conn.close()
        self._load_items()

    # Orders
    def _build_orders_tab(self):
        frm = ctk.CTkFrame(self.tab_orders)
        frm.pack(fill="both", expand=True, padx=10, pady=10)
        frm.grid_columnconfigure(0, weight=1)
        frm.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(frm, text="Orders", font=("Helvetica", 16, "bold")).grid(row=0, column=0, sticky="w", pady=(0,6))
        self.order_tree = ttk.Treeview(frm, columns=("id","user","total","created"), show="headings")
        for col, w in [("id",60),("user",160),("total",100),("created",220)]:
            self.order_tree.heading(col, text=col.upper())
            self.order_tree.column(col, width=w, anchor="center")
        self.order_tree.grid(row=1, column=0, sticky="nsew")

        btns = ctk.CTkFrame(frm, fg_color="transparent")
        btns.grid(row=2, column=0, sticky="e", pady=8)
        ctk.CTkButton(btns, text="Reload", command=self._load_orders).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="View Items", command=self._view_order_items).pack(side="left", padx=6)

        self._load_orders()

    def _load_orders(self):
        for i in self.order_tree.get_children():
            self.order_tree.delete(i)
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            SELECT o.id, u.username, o.total, o.created_at
            FROM orders o JOIN users u ON o.user_id=u.id
            ORDER BY o.id DESC
        """)
        for r in c.fetchall():
            self.order_tree.insert("", "end", values=(r[0], r[1], f"{r[2]:.2f}", r[3]))
        conn.close()

    def _view_order_items(self):
        sel = self.order_tree.selection()
        if not sel:
            return
        oid = int(self.order_tree.item(sel[0], 'values')[0])
        OrderItemsDialog(self, order_id=oid)

    # Reports
    def _build_reports_tab(self):
        frm = ctk.CTkFrame(self.tab_reports)
        frm.pack(fill="both", expand=True, padx=10, pady=10)
        frm.grid_columnconfigure(0, weight=1)

        self.rep_range = ctk.CTkOptionMenu(frm, values=["Daily","Monthly","Yearly"])
        self.rep_range.set("Daily")
        self.rep_range.grid(row=0, column=0, sticky="w", pady=6)
        ctk.CTkButton(frm, text="Generate", command=self._gen_report).grid(row=0, column=1, sticky="w", padx=8)

        self.rep_text = tk.Text(frm, height=22)
        self.rep_text.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=8)
        frm.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(frm, text="* เมนูขายดีจะแสดงจากข้อมูลคำสั่งซื้อ", text_color="#444444").grid(row=2, column=0, columnspan=2, sticky="w")

    def _gen_report(self):
        scope = self.rep_range.get()
        conn = get_db()
        c = conn.cursor()
        # Sum totals per date/month/year
        if scope == "Daily":
            key_fmt = "%Y-%m-%d"
        elif scope == "Monthly":
            key_fmt = "%Y-%m"
        else:
            key_fmt = "%Y"
        c.execute("SELECT id, total, created_at FROM orders")
        totals = defaultdict(float)
        order_ids = []
        for oid, tot, ts in c.fetchall():
            key = datetime.fromisoformat(ts).strftime(key_fmt)
            totals[key] += float(tot)
            order_ids.append(oid)
        # Best sellers
        q_marks = ",".join(["?"]*len(order_ids)) if order_ids else "?"
        if order_ids:
            c.execute(f"SELECT item_id, SUM(quantity) q FROM order_items WHERE order_id IN ({q_marks}) GROUP BY item_id", order_ids)
        else:
            c.execute("SELECT item_id, SUM(quantity) q FROM order_items WHERE 1=0")
        qty_by_item = {row[0]: row[1] for row in c.fetchall()}
        names = {}
        if qty_by_item:
            c.execute(f"SELECT id, name FROM menu_items WHERE id IN ({','.join(['?']*len(qty_by_item))})", list(qty_by_item.keys()))
            names = {row[0]: row[1] for row in c.fetchall()}
        conn.close()

        lines = [f"Sales Report — {scope}", "="*36]
        if totals:
            for k in sorted(totals.keys()):
                lines.append(f"{k}: ฿{totals[k]:.2f}")
        else:
            lines.append("No sales yet.")
        lines.append("")
        lines.append("Best Sellers:")
        if qty_by_item:
            top = sorted(qty_by_item.items(), key=lambda x: x[1], reverse=True)[:10]
            for iid, q in top:
                nm = names.get(iid, f"Item #{iid}")
                lines.append(f"- {nm}: {q} sold")
        else:
            lines.append("- (no data)")
        self.rep_text.delete("1.0", tk.END)
        self.rep_text.insert(tk.END, "\n".join(lines))


class OrderItemsDialog(tk.Toplevel):
    def __init__(self, master, order_id: int):
        super().__init__(master)
        self.title(f"Order #{order_id}")
        self.geometry("520x420")
        self.resizable(False, False)
        frm = ctk.CTkFrame(self)
        frm.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ("item","qty","price","options")
        tree = ttk.Treeview(frm, columns=cols, show="headings", height=14)
        for col, w in [("item",200),("qty",70),("price",90),("options",200)]:
            tree.heading(col, text=col.upper())
            tree.column(col, width=w, anchor="center")
        tree.pack(fill="both", expand=True)

        conn = get_db()
        c = conn.cursor()
        c.execute("""
            SELECT mi.name, oi.quantity, oi.unit_price, oi.options_json
            FROM order_items oi JOIN menu_items mi ON oi.item_id=mi.id
            WHERE oi.order_id=?
        """, (order_id,))
        for r in c.fetchall():
            tree.insert("", "end", values=(r[0], r[1], f"{r[2]:.2f}", r[3]))
        conn.close()


# -----------------------------
# App entry
# -----------------------------

if __name__ == "__main__":
    app = App()
    app.mainloop()