# Taste & Sip - Food & Drink Shop (Tkinter + SQLite, single-file)
# Requirements: Python 3.x, Pillow (PIL)
# Background image path used on auth screens:
#   /mnt/data/program design (1).png
# Product images: put files under ./assets/ and set image_path in Admin / during seed

import os
import sqlite3
import hashlib
import binascii
import re
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

DB_NAME = "taste_and_sip.db"
APP_TITLE = "TASTE & SIP — Food and Drink"
CREAM = "#c8b79e"      # โทนครีมตามภาพ
PAPER = "#f6f1e6"      # กรอบขาวนวล
INK = "#4a3d2b"        # น้ำตาลเข้มสำหรับตัวอักษร
ACCENT = "#b17b48"     # น้ำตาลทองสำหรับปุ่ม/เส้น
BG_IMAGE_PATH = "/mnt/data/program design (1).png"

USERNAME_RE = re.compile(r"^[A-Za-z0-9]{3,20}$")
PHONE_RE = re.compile(r"^\d{10}$")
PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{9,}$")

def connect_db():
    return sqlite3.connect(DB_NAME)

def init_db():
    con = connect_db()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL CHECK(category IN ('FOOD','DRINK')),
            price REAL NOT NULL,
            image_path TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total REAL NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            qty INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)
    con.commit()

    # seed admin account if not exists
    def ensure_user(username, phone, password_plain, is_admin=0):
        cur.execute("SELECT 1 FROM users WHERE username=?", (username,))
        if not cur.fetchone():
            salt, pwh = hash_password(password_plain)
            cur.execute(
                "INSERT INTO users(username, phone, password_hash, salt, is_admin, created_at) VALUES(?,?,?,?,?,?)",
                (username, phone, pwh, salt, is_admin, ts()))
    # admin with strong but allowed password (letters+digits only)
    ensure_user("admin", "0000000000", "Admin12345", 1)

    # seed products if table empty (no images -> you can add later in Admin)
    cur.execute("SELECT COUNT(*) FROM products")
    if cur.fetchone()[0] == 0:
        seed_items = [
            ("Fried Rice", "FOOD", 55.0, None),
            ("Pad Thai", "FOOD", 65.0, None),
            ("Green Curry", "FOOD", 79.0, None),
            ("Americano", "DRINK", 45.0, None),
            ("Lemon Tea", "DRINK", 35.0, None),
            ("Orange Juice", "DRINK", 40.0, None),
        ]
        cur.executemany(
            "INSERT INTO products(name, category, price, image_path) VALUES(?,?,?,?)",
            seed_items
        )
    con.commit()
    con.close()

def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def hash_password(plain: str):
    """Return (hex_salt, hex_hash) using SHA-256"""
    salt = os.urandom(16)
    salted = salt + plain.encode("utf-8")
    digest = hashlib.sha256(salted).digest()
    return binascii.hexlify(salt).decode(), binascii.hexlify(digest).decode()

def verify_password(plain: str, hex_salt: str, hex_hash: str) -> bool:
    salt = binascii.unhexlify(hex_salt.encode())
    digest = hashlib.sha256(salt + plain.encode("utf-8")).digest()
    return binascii.hexlify(digest).decode() == hex_hash

def validate_username(u: str) -> bool:
    return bool(USERNAME_RE.match(u))

def validate_phone(p: str) -> bool:
    return bool(PHONE_RE.match(p))

def validate_password(p: str) -> bool:
    return bool(PASSWORD_RE.match(p))

def load_bg_image(width, height):
    try:
        img = Image.open(BG_IMAGE_PATH).convert("RGB")
        img = img.resize((width, height), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        # fallback solid color
        canvas = Image.new("RGB", (width, height), CREAM)
        return ImageTk.PhotoImage(canvas)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1100x700")
        self.minsize(1000, 650)
        self.configure(bg=CREAM)
        self.iconphoto(False, self.get_small_icon())
        self.current_user = None
        self.cart = {}  # product_id -> qty

        container = tk.Frame(self, bg=CREAM)
        container.pack(fill="both", expand=True)

        self.frames = {}
        for F in (LoginPage, RegisterPage, ResetPage, HomePage, CatalogPage, CartPage, HistoryPage, AdminPage, SalesPage):
            frame = F(parent=container, controller=self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show("LoginPage")

    def get_small_icon(self):
        # small generated plain icon
        im = Image.new("RGB", (32, 32), (177, 123, 72))
        return ImageTk.PhotoImage(im)

    def show(self, name):
        frame = self.frames[name]
        frame.tkraise()
        if hasattr(frame, "on_show"):
            frame.on_show()

    def logout(self):
        self.current_user = None
        self.cart = {}
        self.show("LoginPage")

    # DB helpers
    def db(self):
        return connect_db()

    # cart helpers
    def add_to_cart(self, product_id, qty=1):
        self.cart[product_id] = self.cart.get(product_id, 0) + qty

    def set_cart_qty(self, product_id, qty):
        if qty <= 0:
            self.cart.pop(product_id, None)
        else:
            self.cart[product_id] = qty

    def cart_total(self):
        con = self.db()
        cur = con.cursor()
        total = 0.0
        for pid, qty in self.cart.items():
            cur.execute("SELECT price FROM products WHERE id=?", (pid,))
            row = cur.fetchone()
            if row:
                total += row[0] * qty
        con.close()
        return total

# ---------- Base Frame with split style ----------
class SplitAuthFrame(tk.Frame):
    """Left: image, Right: form box on cream background"""

    def __init__(self, parent, controller, title_text=None):
        super().__init__(parent, bg=CREAM)
        self.controller = controller
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self.left = tk.Label(self, bg=CREAM)
        self.left.grid(row=0, column=0, sticky="nsew")

        self.right = tk.Frame(self, bg=CREAM)
        self.right.grid(row=0, column=1, sticky="nsew")
        self.right.columnconfigure(0, weight=1)

        # form card
        self.card = tk.Frame(self.right, bg=PAPER, bd=0, highlightthickness=0)
        self.card.place(relx=0.55, rely=0.5, anchor="center", width=460, height=340)

        if title_text:
            t = tk.Label(self.right, text=title_text, bg=CREAM, fg=INK,
                         font=("Segoe UI", 36, "bold"))
            t.place(relx=0.55, rely=0.22, anchor="center")

        self.bg_photo = None
        self.bind("<Configure>", self._resize_bg)

    def _resize_bg(self, event):
        # update background left image to fill frame height
        w = max(400, int(self.winfo_width() * 0.5))
        h = max(400, self.winfo_height())
        self.bg_photo = load_bg_image(w, h)
        self.left.configure(image=self.bg_photo)

# ---------- Pages ----------
class LoginPage(SplitAuthFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller, title_text="TASTE & SIP")
        # Form
        self._build_form()

    def _build_form(self):
        f = self.card
        for child in f.winfo_children():
            child.destroy()

        lbl = tk.Label(f, text="USERNAME", bg=PAPER, fg=INK, anchor="w", font=("Segoe UI", 10, "bold"))
        lbl.place(x=40, y=30, width=380, height=20)
        self.ent_user = tk.Entry(f, bd=1, relief="solid", font=("Segoe UI", 11))
        self.ent_user.place(x=40, y=55, width=380, height=30)

        lbl2 = tk.Label(f, text="PASSWORD", bg=PAPER, fg=INK, anchor="w", font=("Segoe UI", 10, "bold"))
        lbl2.place(x=40, y=100, width=380, height=20)
        self.ent_pass = tk.Entry(f, show="•", bd=1, relief="solid", font=("Segoe UI", 11))
        self.ent_pass.place(x=40, y=125, width=380, height=30)

        btn = tk.Button(f, text="LOG IN", bg=ACCENT, fg="white", font=("Segoe UI", 11, "bold"),
                        bd=0, command=self.login)
        btn.place(x=40, y=180, width=380, height=36)

        link_forget = tk.Button(f, text="FORGET PASSWORD", bg=PAPER, fg=INK, bd=0,
                                font=("Segoe UI", 10, "underline"), cursor="hand2",
                                command=lambda: self.controller.show("ResetPage"))
        link_forget.place(x=40, y=235)

        link_register = tk.Button(f, text="REGISTER", bg=PAPER, fg=INK, bd=0,
                                  font=("Segoe UI", 10, "underline"), cursor="hand2",
                                  command=lambda: self.controller.show("RegisterPage"))
        link_register.place(x=340, y=235)

    def login(self):
        u = self.ent_user.get().strip()
        p = self.ent_pass.get().strip()
        if not u or not p:
            messagebox.showwarning("Warning", "กรุณากรอก Username และ Password")
            return
        con = self.controller.db()
        cur = con.cursor()
        cur.execute("SELECT id, phone, password_hash, salt, is_admin FROM users WHERE username=?", (u,))
        row = cur.fetchone()
        con.close()
        if not row:
            messagebox.showerror("Error", "ไม่พบบัญชีผู้ใช้")
            return
        user_id, phone, pwh, salt, is_admin = row
        if verify_password(p, salt, pwh):
            self.controller.current_user = {"id": user_id, "username": u, "phone": phone, "is_admin": bool(is_admin)}
            self.controller.show("HomePage")
        else:
            messagebox.showerror("Error", "รหัสผ่านไม่ถูกต้อง")

class RegisterPage(SplitAuthFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller, title_text="TASTE & SIP")
        self._build_form()

    def _build_form(self):
        f = self.card
        for c in f.winfo_children():
            c.destroy()

        y = 18
        def label(text, y):
            tk.Label(f, text=text, bg=PAPER, fg=INK, anchor="w", font=("Segoe UI", 10, "bold")).place(x=40, y=y, width=380, height=20)

        label("USERNAME", y); y+=25
        self.ent_user = tk.Entry(f, bd=1, relief="solid", font=("Segoe UI", 11)); self.ent_user.place(x=40, y=y, width=380, height=28); y+=38

        label("PHONE NUMBER", y); y+=25
        self.ent_phone = tk.Entry(f, bd=1, relief="solid", font=("Segoe UI", 11)); self.ent_phone.place(x=40, y=y, width=380, height=28); y+=38

        label("PASSWORD", y); y+=25
        self.ent_pass = tk.Entry(f, show="•", bd=1, relief="solid", font=("Segoe UI", 11)); self.ent_pass.place(x=40, y=y, width=380, height=28); y+=38

        label("CONFIRM PASSWORD", y); y+=25
        self.ent_confirm = tk.Entry(f, show="•", bd=1, relief="solid", font=("Segoe UI", 11)); self.ent_confirm.place(x=40, y=y, width=380, height=28); y+=38

        btn = tk.Button(f, text="CREATE ACCOUNT", bg=ACCENT, fg="white", font=("Segoe UI", 11, "bold"),
                        bd=0, command=self.create_account)
        btn.place(x=40, y=y+5, width=380, height=36)

    def create_account(self):
        u = self.ent_user.get().strip()
        ph = self.ent_phone.get().strip()
        pw = self.ent_pass.get().strip()
        cf = self.ent_confirm.get().strip()

        if not validate_username(u):
            messagebox.showerror("Error", "USERNAME ต้องเป็นตัวอักษรอังกฤษ/ตัวเลข 3–20 ตัว\nห้ามเว้นวรรคหรือสัญลักษณ์")
            return
        if not validate_phone(ph):
            messagebox.showerror("Error", "PHONE ต้องเป็นตัวเลข 10 หลัก")
            return
        if not validate_password(pw):
            messagebox.showerror("Error", "PASSWORD ต้องยาวอย่างน้อย 9 ตัวและต้องมีตัวใหญ่, ตัวเล็ก และตัวเลข เท่านั้น (ห้ามสัญลักษณ์)")
            return
        if pw != cf:
            messagebox.showerror("Error", "CONFIRM PASSWORD ไม่ตรงกัน")
            return

        con = self.controller.db()
        cur = con.cursor()
        try:
            salt, pwh = hash_password(pw)
            cur.execute("INSERT INTO users(username, phone, password_hash, salt, created_at) VALUES(?,?,?,?,?)",
                        (u, ph, pwh, salt, ts()))
            con.commit()
            messagebox.showinfo("Success", "สร้างบัญชีสำเร็จ!")
            self.controller.show("LoginPage")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "USERNAME นี้ถูกใช้แล้ว")
        finally:
            con.close()

class ResetPage(SplitAuthFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller, title_text="TASTE & SIP")
        self._build_form()

    def _build_form(self):
        f = self.card
        for c in f.winfo_children():
            c.destroy()
        y=18
        def label(text):
            nonlocal y
            tk.Label(f, text=text, bg=PAPER, fg=INK, anchor="w", font=("Segoe UI", 10, "bold")).place(x=40, y=y, width=380, height=20)
            y+=25
        label("USERNAME")
        self.ent_user = tk.Entry(f, bd=1, relief="solid", font=("Segoe UI", 11)); self.ent_user.place(x=40, y=y, width=380, height=28); y+=38
        label("PHONE NUMBER")
        self.ent_phone = tk.Entry(f, bd=1, relief="solid", font=("Segoe UI", 11)); self.ent_phone.place(x=40, y=y, width=380, height=28); y+=38
        label("NEW PASSWORD")
        self.ent_pass = tk.Entry(f, show="•", bd=1, relief="solid", font=("Segoe UI", 11)); self.ent_pass.place(x=40, y=y, width=380, height=28); y+=38
        label("CONFIRM PASSWORD")
        self.ent_confirm = tk.Entry(f, show="•", bd=1, relief="solid", font=("Segoe UI", 11)); self.ent_confirm.place(x=40, y=y, width=380, height=28); y+=38

        btn = tk.Button(f, text="BACK TO LOG IN", bg=ACCENT, fg="white", font=("Segoe UI", 11, "bold"),
                        bd=0, command=lambda: self.controller.show("LoginPage"))
        btn.place(x=40, y=y+50, width=180, height=36)

        btn2 = tk.Button(f, text="RESET PASSWORD", bg="#90714f", fg="white", font=("Segoe UI", 11, "bold"),
                        bd=0, command=self.reset_password)
        btn2.place(x=240, y=y+50, width=180, height=36)

    def reset_password(self):
        u = self.ent_user.get().strip()
        ph = self.ent_phone.get().strip()
        pw = self.ent_pass.get().strip()
        cf = self.ent_confirm.get().strip()

        if not u or not ph or not pw or not cf:
            messagebox.showerror("Error", "กรอกข้อมูลให้ครบ")
            return
        if not validate_phone(ph):
            messagebox.showerror("Error", "PHONE ต้องเป็นตัวเลข 10 หลัก")
            return
        if not validate_password(pw):
            messagebox.showerror("Error", "PASSWORD ใหม่ไม่ผ่านเกณฑ์")
            return
        if pw != cf:
            messagebox.showerror("Error", "CONFIRM PASSWORD ไม่ตรงกัน")
            return

        con = self.controller.db()
        cur = con.cursor()
        cur.execute("SELECT id, phone FROM users WHERE username=?", (u,))
        row = cur.fetchone()
        if not row:
            con.close()
            messagebox.showerror("Error", "ไม่พบบัญชีผู้ใช้")
            return
        user_id, phone = row
        if phone != ph:
            con.close()
            messagebox.showerror("Error", "เบอร์โทรไม่ตรงกับบัญชี")
            return
        salt, pwh = hash_password(pw)
        cur.execute("UPDATE users SET password_hash=?, salt=? WHERE id=?", (pwh, salt, user_id))
        con.commit()
        con.close()
        messagebox.showinfo("Success", "เปลี่ยนรหัสผ่านสำเร็จ")
        self.controller.show("LoginPage")

# ---------- Home ----------
class HomePage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CREAM)
        self.controller = controller
        # topbar
        top = tk.Frame(self, bg=CREAM)
        top.pack(fill="x", pady=10, padx=16)
        self.lbl_user = tk.Label(top, text="", bg=CREAM, fg=INK, font=("Segoe UI", 12, "bold"))
        self.lbl_user.pack(side="left")
        tk.Button(top, text="Order History", bg=PAPER, fg=INK, bd=0, font=("Segoe UI", 10, "bold"),
                  command=lambda: controller.show("HistoryPage")).pack(side="right", padx=6)
        tk.Button(top, text="Cart", bg=PAPER, fg=INK, bd=0, font=("Segoe UI", 10, "bold"),
                  command=lambda: controller.show("CartPage")).pack(side="right", padx=6)
        tk.Button(top, text="Log out", bg=PAPER, fg=INK, bd=0, font=("Segoe UI", 10, "bold"),
                  command=controller.logout).pack(side="right", padx=6)

        self.btn_admin = tk.Button(top, text="Admin", bg=PAPER, fg=INK, bd=0, font=("Segoe UI", 10, "bold"),
                                   command=lambda: controller.show("AdminPage"))
        # big round buttons
        center = tk.Frame(self, bg=CREAM)
        center.pack(expand=True)
        self._round_button(center, "FOOD", lambda: self.open_catalog("FOOD")).grid(row=0, column=0, padx=40, pady=40)
        self._round_button(center, "DRINK", lambda: self.open_catalog("DRINK")).grid(row=0, column=1, padx=40, pady=40)
        self._round_button(center, "CART", lambda: controller.show("CartPage")).grid(row=0, column=2, padx=40, pady=40)

    def _round_button(self, parent, text, cmd):
        frm = tk.Frame(parent, bg=CREAM)
        canvas = tk.Canvas(frm, width=180, height=180, bg=CREAM, highlightthickness=0)
        canvas.pack()
        # circle
        x0, y0, x1, y1 = 10, 10, 170, 170
        canvas.create_oval(x0, y0, x1, y1, fill=PAPER, outline=ACCENT, width=2)
        canvas.create_text(90, 90, text=text, font=("Segoe UI", 18, "bold"), fill=INK)
        btn = tk.Button(frm, text="", command=cmd)
        btn.place(x=10, y=10, width=160, height=160)
        btn.lift()
        btn.configure(bg=PAPER, bd=0, activebackground=PAPER, highlightthickness=0)
        btn.bind("<Enter>", lambda e: canvas.itemconfig(1, outline="#8d623c"))
        btn.bind("<Leave>", lambda e: canvas.itemconfig(1, outline=ACCENT))
        return frm

    def open_catalog(self, category):
        cat_page: CatalogPage = self.controller.frames["CatalogPage"]
        cat_page.set_category(category)
        self.controller.show("CatalogPage")

    def on_show(self):
        u = self.controller.current_user
        if not u:
            self.controller.show("LoginPage")
            return
        self.lbl_user.config(text=f"👤 {u['username']}")
        if u.get("is_admin"):
            self.btn_admin.pack(side="right", padx=6)
        else:
            self.btn_admin.pack_forget()

# ---------- Catalog ----------
class CatalogPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CREAM)
        self.controller = controller
        self.category = "FOOD"

        top = tk.Frame(self, bg=CREAM)
        top.pack(fill="x", padx=16, pady=8)
        self.lbl_title = tk.Label(top, text="CATALOG", bg=CREAM, fg=INK, font=("Segoe UI", 18, "bold"))
        self.lbl_title.pack(side="left")
        tk.Button(top, text="Back", bg=PAPER, fg=INK, bd=0, font=("Segoe UI", 10, "bold"),
                  command=lambda: controller.show("HomePage")).pack(side="right", padx=6)
        tk.Button(top, text="Cart", bg=PAPER, fg=INK, bd=0, font=("Segoe UI", 10, "bold"),
                  command=lambda: controller.show("CartPage")).pack(side="right", padx=6)

        # list frame
        self.list_frame = tk.Frame(self, bg=CREAM)
        self.list_frame.pack(fill="both", expand=True, padx=16, pady=8)

        self.tree = ttk.Treeview(self.list_frame, columns=("name", "price", "active"), show="headings", height=14)
        self.tree.heading("name", text="Name")
        self.tree.heading("price", text="Price")
        self.tree.heading("active", text="Active")
        self.tree.column("name", width=400, anchor="w")
        self.tree.column("price", width=120, anchor="e")
        self.tree.column("active", width=80, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")

        bottom = tk.Frame(self, bg=CREAM); bottom.pack(fill="x", padx=16, pady=8)
        tk.Button(bottom, text="Add to Cart", bg=ACCENT, fg="white", bd=0, font=("Segoe UI", 10, "bold"),
                  command=self.add_selected).pack(side="left")
        tk.Label(bottom, text="Quantity:", bg=CREAM, fg=INK).pack(side="left", padx=(16, 4))
        self.qty_var = tk.IntVar(value=1)
        tk.Spinbox(bottom, from_=1, to=99, width=5, textvariable=self.qty_var).pack(side="left")

        self.preview = tk.Label(self, bg=CREAM)
        self.preview.pack(pady=8)

    def set_category(self, category):
        self.category = category
        self.lbl_title.config(text=f"{'FOOD' if category=='FOOD' else 'DRINK'} MENU")
        self.reload()

    def reload(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        con = self.controller.db()
        cur = con.cursor()
        cur.execute("SELECT id, name, price, is_active, image_path FROM products WHERE category=? ORDER BY name", (self.category,))
        rows = cur.fetchall()
        con.close()
        for pid, name, price, active, imgp in rows:
            self.tree.insert("", "end", iid=str(pid), values=(name, f"{price:.2f}", "Yes" if active else "No"))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.preview.config(image="", text="(เลือกรายการเพื่อดูรูปตัวอย่าง)")
        self.preview.photo = None

    def _on_select(self, event):
        sel = self.tree.selection()
        if not sel: return
        pid = int(sel[0])
        con = self.controller.db()
        cur = con.cursor()
        cur.execute("SELECT image_path FROM products WHERE id=?", (pid,))
        row = cur.fetchone()
        con.close()
        imgp = row[0] if row else None
        if imgp and os.path.exists(imgp):
            try:
                im = Image.open(imgp).convert("RGB")
                im = im.resize((360, 240), Image.LANCZOS)
                ph = ImageTk.PhotoImage(im)
                self.preview.config(image=ph, text="")
                self.preview.photo = ph
            except Exception:
                self.preview.config(text="(ไม่สามารถโหลดรูปได้)", image="")
        else:
            self.preview.config(image="", text="(ยังไม่มีรูป — ใส่ path ใน Admin หรือแก้ไขสินค้านี้)")

    def add_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "กรุณาเลือกรายการ")
            return
        pid = int(sel[0])
        qty = max(1, int(self.qty_var.get()))
        # check active
        con = self.controller.db(); cur = con.cursor()
        cur.execute("SELECT is_active FROM products WHERE id=?", (pid,))
        row = cur.fetchone(); con.close()
        if row and row[0] == 1:
            self.controller.add_to_cart(pid, qty)
            messagebox.showinfo("Added", "ใส่ในตะกร้าแล้ว")
        else:
            messagebox.showwarning("Warning", "รายการนี้ถูกปิดใช้งาน")

# ---------- Cart ----------
class CartPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CREAM)
        self.controller = controller

        top = tk.Frame(self, bg=CREAM)
        top.pack(fill="x", padx=16, pady=8)
        tk.Label(top, text="YOUR CART", bg=CREAM, fg=INK, font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Button(top, text="Back", bg=PAPER, fg=INK, bd=0, font=("Segoe UI", 10, "bold"),
                  command=lambda: controller.show("HomePage")).pack(side="right")

        self.tree = ttk.Treeview(self, columns=("name","price","qty","sub"), show="headings", height=16)
        for h, w, an in [("name", 380, "w"), ("price", 100, "e"), ("qty", 80, "center"), ("sub", 120, "e")]:
            self.tree.heading(h, text=h.title())
            self.tree.column(h, width=w, anchor=an)
        self.tree.pack(fill="both", expand=True, padx=16, pady=8)

        bottom = tk.Frame(self, bg=CREAM); bottom.pack(fill="x", padx=16, pady=8)
        tk.Button(bottom, text="Remove", bg=PAPER, fg=INK, bd=0, command=self.remove).pack(side="left")
        tk.Label(bottom, text="Set Qty:", bg=CREAM, fg=INK).pack(side="left", padx=(10,4))
        self.qty_var = tk.IntVar(value=1)
        tk.Spinbox(bottom, from_=1, to=99, width=5, textvariable=self.qty_var).pack(side="left")
        tk.Button(bottom, text="Apply", bg=PAPER, fg=INK, bd=0, command=self.apply_qty).pack(side="left", padx=6)

        self.lbl_total = tk.Label(bottom, text="Total: 0.00", bg=CREAM, fg=INK, font=("Segoe UI", 12, "bold"))
        self.lbl_total.pack(side="right")
        tk.Button(bottom, text="Checkout", bg=ACCENT, fg="white", bd=0, font=("Segoe UI", 11, "bold"),
                  command=self.checkout).pack(side="right", padx=8)

    def on_show(self):
        self.reload()

    def reload(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        if not self.controller.cart:
            self.lbl_total.config(text="Total: 0.00")
            return
        con = self.controller.db(); cur = con.cursor()
        total = 0.0
        for pid, qty in self.controller.cart.items():
            cur.execute("SELECT name, price FROM products WHERE id=?", (pid,))
            row = cur.fetchone()
            if row:
                name, price = row
                sub = price * qty
                total += sub
                self.tree.insert("", "end", iid=str(pid),
                                 values=(name, f"{price:.2f}", qty, f"{sub:.2f}"))
        con.close()
        self.lbl_total.config(text=f"Total: {total:.2f}")

    def selected_pid(self):
        sel = self.tree.selection()
        if not sel: return None
        return int(sel[0])

    def remove(self):
        pid = self.selected_pid()
        if pid is None: return
        self.controller.cart.pop(pid, None)
        self.reload()

    def apply_qty(self):
        pid = self.selected_pid()
        if pid is None: return
        q = max(1, int(self.qty_var.get()))
        self.controller.set_cart_qty(pid, q)
        self.reload()

    def checkout(self):
        if not self.controller.current_user:
            messagebox.showerror("Error", "กรุณาเข้าสู่ระบบ")
            return
        if not self.controller.cart:
            messagebox.showwarning("Warning", "ตะกร้าว่าง")
            return
        con = self.controller.db(); cur = con.cursor()
        # compute total and record order
        total = 0.0
        items = []
        for pid, qty in self.controller.cart.items():
            cur.execute("SELECT price FROM products WHERE id=?", (pid,))
            row = cur.fetchone()
            if not row: continue
            price = row[0]; sub = price * qty; total += sub
            items.append((pid, qty, price))
        cur.execute("INSERT INTO orders(user_id, total, created_at) VALUES(?,?,?)",
                    (self.controller.current_user["id"], total, ts()))
        order_id = cur.lastrowid
        for pid, qty, price in items:
            cur.execute("INSERT INTO order_items(order_id, product_id, qty, price) VALUES(?,?,?,?)",
                        (order_id, pid, qty, price))
        con.commit(); con.close()
        self.controller.cart.clear()
        self.reload()
        messagebox.showinfo("Success", "ชำระเงินสำเร็จ! บันทึกออเดอร์แล้ว")

# ---------- Order History ----------
class HistoryPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CREAM)
        self.controller = controller
        top = tk.Frame(self, bg=CREAM); top.pack(fill="x", padx=16, pady=8)
        tk.Label(top, text="ORDER HISTORY", bg=CREAM, fg=INK, font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Button(top, text="Back", bg=PAPER, fg=INK, bd=0, command=lambda: controller.show("HomePage")).pack(side="right")
        self.tree = ttk.Treeview(self, columns=("id","created","total"), show="headings", height=18)
        for h, w, an in [("id",80,"center"), ("created",240,"w"), ("total",120,"e")]:
            self.tree.heading(h, text=h.upper()); self.tree.column(h, width=w, anchor=an)
        self.tree.pack(fill="both", expand=True, padx=16, pady=8)

    def on_show(self):
        u = self.controller.current_user
        if not u:
            self.controller.show("LoginPage"); return
        for i in self.tree.get_children():
            self.tree.delete(i)
        con = self.controller.db(); cur = con.cursor()
        cur.execute("SELECT id, created_at, total FROM orders WHERE user_id=? ORDER BY id DESC", (u["id"],))
        for oid, created, total in cur.fetchall():
            self.tree.insert("", "end", values=(oid, created, f"{total:.2f}"))
        con.close()

# ---------- Admin Manage Products ----------
class AdminPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CREAM)
        self.controller = controller

        top = tk.Frame(self, bg=CREAM); top.pack(fill="x", padx=16, pady=8)
        tk.Label(top, text="ADMIN — PRODUCTS", bg=CREAM, fg=INK, font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Button(top, text="Sales Summary", bg=PAPER, fg=INK, bd=0, command=lambda: controller.show("SalesPage")).pack(side="right", padx=6)
        tk.Button(top, text="Back", bg=PAPER, fg=INK, bd=0, command=lambda: controller.show("HomePage")).pack(side="right")

        self.tree = ttk.Treeview(self, columns=("id","name","category","price","active","image"), show="headings", height=16)
        for h, w, an in [("id",60,"center"), ("name",280,"w"), ("category",90,"center"),
                         ("price",80,"e"), ("active",70,"center"), ("image",260,"w")]:
            self.tree.heading(h, text=h.upper()); self.tree.column(h, width=w, anchor=an)
        self.tree.pack(fill="both", expand=True, padx=16, pady=8)

        bottom = tk.Frame(self, bg=CREAM); bottom.pack(fill="x", padx=16, pady=8)
        tk.Button(bottom, text="Add", bg=ACCENT, fg="white", bd=0, command=self.add).pack(side="left")
        tk.Button(bottom, text="Edit", bg=PAPER, fg=INK, bd=0, command=self.edit).pack(side="left", padx=6)
        tk.Button(bottom, text="Toggle Active", bg=PAPER, fg=INK, bd=0, command=self.toggle).pack(side="left", padx=6)
        tk.Button(bottom, text="Choose Image", bg=PAPER, fg=INK, bd=0, command=self.choose_image).pack(side="left", padx=6)
        tk.Button(bottom, text="Reload", bg=PAPER, fg=INK, bd=0, command=self.reload).pack(side="left", padx=6)

    def on_show(self):
        u = self.controller.current_user
        if not u or not u.get("is_admin"):
            messagebox.showerror("Error", "เฉพาะผู้ดูแลระบบ")
            self.controller.show("HomePage")
            return
        self.reload()

    def reload(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        con = self.controller.db(); cur = con.cursor()
        cur.execute("SELECT id, name, category, price, is_active, image_path FROM products ORDER BY category,name")
        for r in cur.fetchall():
            self.tree.insert("", "end", iid=str(r[0]), values=(r[0], r[1], r[2], f"{r[3]:.2f}", "Yes" if r[4] else "No", r[5] or ""))
        con.close()

    def selected_id(self):
        sel = self.tree.selection()
        if not sel: return None
        return int(sel[0])

    def add(self):
        ProductDialog(self, None).wait_window()
        self.reload()

    def edit(self):
        pid = self.selected_id()
        if pid is None: return
        ProductDialog(self, pid).wait_window()
        self.reload()

    def toggle(self):
        pid = self.selected_id()
        if pid is None: return
        con = self.controller.db(); cur = con.cursor()
        cur.execute("SELECT is_active FROM products WHERE id=?", (pid,))
        row = cur.fetchone()
        if row is None: con.close(); return
        cur.execute("UPDATE products SET is_active=? WHERE id=?", (0 if row[0]==1 else 1, pid))
        con.commit(); con.close()
        self.reload()

    def choose_image(self):
        pid = self.selected_id()
        if pid is None: return
        path = filedialog.askopenfilename(title="เลือกรูปสินค้า", filetypes=[("Image","*.jpg *.jpeg *.png")])
        if not path: return
        con = self.controller.db(); cur = con.cursor()
        cur.execute("UPDATE products SET image_path=? WHERE id=?", (path, pid))
        con.commit(); con.close()
        self.reload()

class ProductDialog(tk.Toplevel):
    def __init__(self, admin_page: AdminPage, product_id):
        super().__init__(admin_page)
        self.admin_page = admin_page
        self.product_id = product_id
        self.title("Product")
        self.configure(bg=PAPER)
        self.resizable(False, False)

        tk.Label(self, text="Name:", bg=PAPER).grid(row=0, column=0, sticky="e", padx=8, pady=8)
        tk.Label(self, text="Category:", bg=PAPER).grid(row=1, column=0, sticky="e", padx=8, pady=8)
        tk.Label(self, text="Price:", bg=PAPER).grid(row=2, column=0, sticky="e", padx=8, pady=8)
        tk.Label(self, text="Image Path:", bg=PAPER).grid(row=3, column=0, sticky="e", padx=8, pady=8)

        self.ent_name = tk.Entry(self, width=34); self.ent_name.grid(row=0, column=1, padx=8, pady=8)
        self.cmb_cat = ttk.Combobox(self, values=["FOOD","DRINK"], state="readonly", width=30); self.cmb_cat.grid(row=1, column=1, padx=8, pady=8)
        self.ent_price = tk.Entry(self, width=34); self.ent_price.grid(row=2, column=1, padx=8, pady=8)
        self.ent_img = tk.Entry(self, width=34); self.ent_img.grid(row=3, column=1, padx=8, pady=8)

        tk.Button(self, text="Browse", command=self.browse).grid(row=3, column=2, padx=8, pady=8)
        tk.Button(self, text="Save", bg=ACCENT, fg="white", command=self.save).grid(row=4, column=1, pady=12)
        tk.Button(self, text="Cancel", command=self.destroy).grid(row=4, column=2, pady=12)

        if product_id:
            con = admin_page.controller.db(); cur = con.cursor()
            cur.execute("SELECT name, category, price, image_path FROM products WHERE id=?", (product_id,))
            row = cur.fetchone(); con.close()
            if row:
                self.ent_name.insert(0, row[0])
                self.cmb_cat.set(row[1])
                self.ent_price.insert(0, f"{row[2]:.2f}")
                if row[3]: self.ent_img.insert(0, row[3])
        else:
            self.cmb_cat.set("FOOD")

    def browse(self):
        path = filedialog.askopenfilename(title="เลือกรูป", filetypes=[("Image","*.jpg *.jpeg *.png")])
        if path: self.ent_img.delete(0, tk.END); self.ent_img.insert(0, path)

    def save(self):
        name = self.ent_name.get().strip()
        cat = self.cmb_cat.get().strip()
        try:
            price = float(self.ent_price.get().strip())
        except ValueError:
            messagebox.showerror("Error","ราคาไม่ถูกต้อง"); return
        imgp = self.ent_img.get().strip() or None
        con = self.admin_page.controller.db(); cur = con.cursor()
        if self.product_id:
            cur.execute("UPDATE products SET name=?, category=?, price=?, image_path=? WHERE id=?",
                        (name, cat, price, imgp, self.product_id))
        else:
            cur.execute("INSERT INTO products(name, category, price, image_path) VALUES(?,?,?,?)",
                        (name, cat, price, imgp))
        con.commit(); con.close()
        self.destroy()

# ---------- Sales Summary ----------
class SalesPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CREAM)
        self.controller = controller
        top = tk.Frame(self, bg=CREAM); top.pack(fill="x", padx=16, pady=8)
        tk.Label(top, text="ADMIN — SALES SUMMARY", bg=CREAM, fg=INK, font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Button(top, text="Back", bg=PAPER, fg=INK, bd=0, command=lambda: controller.show("AdminPage")).pack(side="right")

        board = tk.Frame(self, bg=CREAM); board.pack(fill="both", expand=True, padx=16, pady=8)
        self.lbl_total = self._stat(board, "Total Revenue", 0, 0)
        self.lbl_orders = self._stat(board, "Orders", 0, 1)
        self.lbl_items = self._stat(board, "Items Sold", 1, 0)
        self.lbl_avg = self._stat(board, "Avg / Order", 1, 1)

        # recent orders table
        self.tree = ttk.Treeview(self, columns=("id","created","user","total"), show="headings", height=14)
        for h, w, an in [("id",80,"center"), ("created",240,"w"), ("user",200,"w"), ("total",120,"e")]:
            self.tree.heading(h, text=h.upper()); self.tree.column(h, width=w, anchor=an)
        self.tree.pack(fill="both", expand=True, padx=16, pady=8)

    def _stat(self, parent, title, r, c):
        frm = tk.Frame(parent, bg=PAPER, bd=0)
        frm.grid(row=r, column=c, sticky="nsew", padx=8, pady=8)
        for i in range(2):
            parent.grid_columnconfigure(i, weight=1)
            parent.grid_rowconfigure(i, weight=1)
        tk.Label(frm, text=title, bg=PAPER, fg=INK, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(10,0))
        lbl = tk.Label(frm, text="0", bg=PAPER, fg=ACCENT, font=("Segoe UI", 22, "bold"))
        lbl.pack(anchor="w", padx=12, pady=(0,12))
        return lbl

    def on_show(self):
        u = self.controller.current_user
        if not u or not u.get("is_admin"):
            self.controller.show("HomePage"); return
        con = self.controller.db(); cur = con.cursor()
        cur.execute("SELECT IFNULL(SUM(total),0), COUNT(*) FROM orders")
        total, orders = cur.fetchone()
        cur.execute("SELECT IFNULL(SUM(qty),0) FROM order_items")
        items = cur.fetchone()[0]
        avg = (total / orders) if orders else 0
        self.lbl_total.config(text=f"{total:.2f}")
        self.lbl_orders.config(text=str(orders))
        self.lbl_items.config(text=str(items))
        self.lbl_avg.config(text=f"{avg:.2f}")

        for i in self.tree.get_children(): self.tree.delete(i)
        cur.execute("""
            SELECT o.id, o.created_at, u.username, o.total
            FROM orders o JOIN users u ON o.user_id=u.id
            ORDER BY o.id DESC LIMIT 50
        """)
        for row in cur.fetchall():
            self.tree.insert("", "end", values=(row[0], row[1], row[2], f"{row[3]:.2f}"))
        con.close()

# ---------- main ----------
if __name__ == "__main__":
    init_db()
    app = App()
    app.mainloop()