import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3, hashlib, os, binascii, re
from datetime import datetime

# ---------- App config ----------
APP_TITLE = "TASTE AND SIP"
DB_FILE = "taste_and_sip.db"

# image paths (ปรับให้ตรงเครื่องคุณ)
LEFT_BG_PATH = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\AVIBRA_1.png"
LOGO_PATH    = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\lologogo.png-removebg-preview.png"

# color theme (โทนครีมตามภาพ)
CREAM = "#f8eedb"
PAPER = "#ffffff"
INK   = "#2a2520"
ACCENT= "#b17b48"
SOFT  = "#f5efe4"

# ---------- Optional PIL (สำหรับแสดง JPEG/Resize คุณภาพดี) ----------
USE_PIL = False
try:
    from PIL import Image, ImageTk
    USE_PIL = True
except Exception:
    USE_PIL = False

# ---------- Validation ----------
USERNAME_RE = re.compile(r"^[A-Za-z0-9]{3,20}$")
PHONE_RE    = re.compile(r"^\d{10}$")
PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{9,}$")

def valid_user(u:str)->bool: return bool(USERNAME_RE.match(u))
def valid_phone(p:str)->bool: return bool(PHONE_RE.match(p))
def valid_pass(p:str)->bool: return bool(PASSWORD_RE.match(p))

# ---------- Crypto (salted sha256) ----------
def gen_salt(n: int = 16) -> str:
    return binascii.hexlify(os.urandom(n)).decode()

def hash_password(plain: str, hex_salt: str) -> str:
    salt = binascii.unhexlify(hex_salt.encode())
    return binascii.hexlify(hashlib.sha256(salt + plain.encode("utf-8")).digest()).decode()

# ---------- DB ----------
def ts() -> str: return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def connect_db(): return sqlite3.connect(DB_FILE)

def init_db():
    con = connect_db(); cur = con.cursor()
    # users
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
    # products / orders
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
    migrate_db(con)

    # seed admin
    cur.execute("SELECT 1 FROM users WHERE username='admin'")
    if not cur.fetchone():
        salt = gen_salt(); pwh = hash_password("Admin12345", salt)
        cur.execute("INSERT INTO users(username,phone,password_hash,salt,is_admin,created_at) VALUES(?,?,?,?,?,?)",
                    ("admin","0000000000",pwh,salt,1,ts()))
    # seed menu
    cur.execute("SELECT COUNT(*) FROM products")
    if cur.fetchone()[0] == 0:
        items = [("Fried Rice","FOOD",55.0,None),
                 ("Pad Thai","FOOD",65.0,None),
                 ("Green Curry","FOOD",79.0,None),
                 ("Americano","DRINK",45.0,None),
                 ("Lemon Tea","DRINK",35.0,None),
                 ("Orange Juice","DRINK",40.0,None)]
        cur.executemany("INSERT INTO products(name,category,price,image_path) VALUES(?,?,?,?)", items)
    con.commit(); con.close()

def migrate_db(con):
    cur = con.cursor()
    cur.execute("PRAGMA table_info(users)")
    cols = {r[1] for r in cur.fetchall()}
    if "phone" not in cols:      cur.execute("ALTER TABLE users ADD COLUMN phone TEXT DEFAULT '0000000000'")
    if "salt" not in cols:       cur.execute("ALTER TABLE users ADD COLUMN salt TEXT DEFAULT ''")
    if "is_admin" not in cols:   cur.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
    if "created_at" not in cols: cur.execute("ALTER TABLE users ADD COLUMN created_at TEXT DEFAULT ''")
    con.commit()

def create_user(username: str, phone: str, password: str):
    if not valid_user(username):
        return False, "USERNAME ต้องเป็นอังกฤษ/ตัวเลข 3–20 ตัว"
    if not valid_phone(phone):
        return False, "PHONE ต้องเป็นตัวเลข 10 หลัก"
    if not valid_pass(password):
        return False, "PASSWORD ≥ 9 ตัว มีตัวเล็ก/ใหญ่/ตัวเลข และห้ามสัญลักษณ์"
    con = connect_db(); cur = con.cursor()
    try:
        salt = gen_salt(); pwh = hash_password(password, salt)
        cur.execute("INSERT INTO users(username,phone,password_hash,salt,created_at) VALUES(?,?,?,?,?)",
                    (username, phone, pwh, salt, ts()))
        con.commit(); ok, msg = True, "Account created."
    except sqlite3.IntegrityError:
        ok, msg = False, "Username already exists."
    con.close(); return ok, msg

def auth_user(username: str, password: str):
    con = connect_db(); cur = con.cursor()
    cur.execute("SELECT id, phone, password_hash, salt, is_admin FROM users WHERE username=?", (username,))
    row = cur.fetchone(); con.close()
    if not row: return None
    uid, phone, pwh, salt, is_admin = row
    if hash_password(password, salt) == pwh:
        return {"id":uid, "username":username, "phone":phone, "is_admin":bool(is_admin)}
    return None

def reset_password(username: str, phone: str, new_password: str):
    if not valid_phone(phone): return False, "เบอร์โทรต้อง 10 หลัก"
    if not valid_pass(new_password): return False, "รหัสผ่านใหม่ไม่ผ่านเงื่อนไข"
    con = connect_db(); cur = con.cursor()
    cur.execute("SELECT id FROM users WHERE username=? AND phone=?", (username, phone))
    row = cur.fetchone()
    if not row:
        con.close(); return False, "ไม่พบบัญชีหรือเบอร์โทรไม่ตรงกัน"
    uid = row[0]; salt = gen_salt(); pwh = hash_password(new_password, salt)
    cur.execute("UPDATE users SET password_hash=?, salt=? WHERE id=?", (pwh, salt, uid))
    con.commit(); con.close()
    return True, "เปลี่ยนรหัสผ่านสำเร็จ"

# ---------- Image utils ----------
def load_photo(path, fit_w=None, fit_h=None, cover=False):
    """โหลดรูปแบบยืดหยุ่น: ถ้ามี PIL รองรับ JPG/PNG, ถ้าไม่มีใช้ PhotoImage (PNG/GIF)"""
    if not path or not os.path.exists(path): return None
    try:
        if USE_PIL:
            im = Image.open(path)
            if fit_w and fit_h:
                if cover:
                    r = max(fit_w/im.width, fit_h/im.height)
                    im = im.resize((max(1,int(im.width*r)), max(1,int(im.height*r))), Image.LANCZOS)
                    # crop center
                    x = (im.width - fit_w)//2; y = (im.height - fit_h)//2
                    im = im.crop((x, y, x+fit_w, y+fit_h))
                else:
                    r = min(fit_w/im.width, fit_h/im.height)
                    im = im.resize((max(1,int(im.width*r)), max(1,int(im.height*r))), Image.LANCZOS)
            return ImageTk.PhotoImage(im)
        else:
            img = tk.PhotoImage(file=path)  # PNG/GIF เท่านั้น
            return img
    except Exception:
        return None

# ---------- App / Pages ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.state("zoomed")
        self.configure(bg=CREAM)
        init_db()
        self.current_user = None
        self.cart = {}  # product_id -> qty

        self.container = tk.Frame(self, bg=CREAM)
        self.container.pack(fill="both", expand=True)

        self.frames = {}
        for F in (LoginPage, RegisterPage, ResetPage, HomePage, CatalogPage, CartPage, HistoryPage, AdminPage, SalesPage):
            frame = F(self.container, self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        self.show("LoginPage")

    def show(self, name):
        frame = self.frames[name]
        frame.tkraise()
        if hasattr(frame, "on_show"): frame.on_show()

    # cart helpers
    def add_to_cart(self, pid, qty=1):
        self.cart[pid] = self.cart.get(pid, 0) + qty

    def set_cart_qty(self, pid, qty):
        if qty <= 0: self.cart.pop(pid, None)
        else: self.cart[pid] = qty

# ---------- Shared split layout ----------
class SplitAuthBase(tk.Frame):
    def __init__(self, parent, app, card_height=360, title_text=None):
        super().__init__(parent, bg=CREAM)
        self.app = app
        # left
        self.left = tk.Frame(self, width=720, height=680, bg="#ececec")
        self.left.pack(side="left", fill="y")
        self.left.pack_propagate(False)
        self.bg_img = load_photo(LEFT_BG_PATH, 720, 680, cover=True)
        canvas = tk.Canvas(self.left, width=720, height=680, highlightthickness=0, bg="#ececec")
        canvas.pack(fill="both", expand=True)
        if self.bg_img: canvas.create_image(360, 340, image=self.bg_img)
        canvas.create_text(32, 36, text="WELCOME TO \nTASTE AND SIP",
                           fill="white", font=("Georgia", 32, "bold"), anchor="nw")
        canvas.create_text(36, 84, text="\n\nFOOD AND DRINK !",
                           fill="white", font=("Georgia", 16), anchor="nw")
        # right
        right = tk.Frame(self, bg=CREAM)
        right.pack(side="left", fill="both", expand=True)
        self.logo_img = load_photo(LOGO_PATH, 220, 220)
        lw = tk.Frame(right, bg=SOFT); lw.pack(pady=20)
        if self.logo_img:
            tk.Label(lw, image=self.logo_img, bg=CREAM).pack()
        else:
            tk.Label(lw, text="TASTE & SIP", bg=SOFT, font=("Segoe UI", 22, "bold")).pack()

        self.card = tk.Frame(right, bg=PAPER)
        self.card.pack(padx=40, pady=10, fill="x")
        self.card.config(height=card_height)

    def clear_card(self):
        for w in self.card.winfo_children(): w.destroy()

    def field(self, label, show=""):
        tk.Label(self.card, text=label, bg=PAPER, fg="#333", font=("Segoe UI",10,"bold")).pack(anchor="w", padx=40)
        e = tk.Entry(self.card, font=("Segoe UI",12), relief="solid", bd=1, show=show)
        e.pack(pady=(6,16), ipady=8, padx=40, fill="x")
        return e

# ---------- Auth pages ----------
class LoginPage(SplitAuthBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.build()

    def build(self):
        self.clear_card()
        tk.Label(self.card, text="Sign In", bg=PAPER, fg=INK, font=("Segoe UI",16,"bold")).pack(pady=(22,6))
        self.e_user = self.field("USERNAME")
        self.e_pass = self.field("PASSWORD", show="•")
        tk.Button(self.card, text="SIGN IN", font=("Segoe UI",12,"bold"), relief="solid", bd=1,
                  command=self.sign_in).pack(pady=6, ipady=8, padx=40, fill="x")
        row = tk.Frame(self.card, bg=PAPER); row.pack(fill="x", pady=(8,20))
        tk.Button(row, text="FORGET PASSWORD", font=("Segoe UI",10), relief="flat", bg=PAPER,
                  command=lambda:self.app.show("ResetPage")).pack(side="left", padx=40)
        tk.Button(row, text="REGISTER", font=("Segoe UI",10), relief="flat", bg=PAPER,
                  command=lambda:self.app.show("RegisterPage")).pack(side="right", padx=40)

    def sign_in(self):
        u, p = self.e_user.get().strip(), self.e_pass.get().strip()
        if not u or not p:
            messagebox.showerror("Error", "Please enter username and password."); return
        user = auth_user(u, p)
        if user:
            self.app.current_user = user
            self.app.cart = {}
            self.app.show("HomePage")
        else:
            messagebox.showerror("Error", "Invalid credentials.")

class RegisterPage(SplitAuthBase):
    def __init__(self, parent, app):
        super().__init__(parent, app, card_height=420)
        self.build()

    def build(self):
        self.clear_card()
        tk.Label(self.card, text="Create Account", bg=PAPER, fg=INK, font=("Segoe UI",16,"bold")).pack(pady=(22,6))
        self.e_user  = self.field("USERNAME")
        self.e_phone = self.field("PHONE NUMBER")
        self.e_p1    = self.field("PASSWORD", show="•")
        self.e_p2    = self.field("CONFIRM PASSWORD", show="•")
        tk.Button(self.card, text="CREATE ACCOUNT", font=("Segoe UI",12,"bold"), relief="solid", bd=1,
                  command=self.create).pack(pady=6, ipady=8, padx=40, fill="x")
        tk.Button(self.card, text="BACK TO LOGIN", font=("Segoe UI",11), relief="flat", bg=PAPER,
                  command=lambda:self.app.show("LoginPage")).pack(pady=(8,20))

    def create(self):
        u, ph, p1, p2 = self.e_user.get().strip(), self.e_phone.get().strip(), self.e_p1.get().strip(), self.e_p2.get().strip()
        if not u or not ph or not p1 or not p2:
            messagebox.showerror("Error","Please fill all fields."); return
        if p1 != p2:
            messagebox.showerror("Error","Passwords do not match."); return
        ok, msg = create_user(u, ph, p1)
        if ok:
            messagebox.showinfo("Success", msg)
            self.app.show("LoginPage")
        else:
            messagebox.showerror("Error", msg)

class ResetPage(SplitAuthBase):
    def __init__(self, parent, app):
        super().__init__(parent, app, card_height=420)
        self.build()

    def build(self):
        self.clear_card()
        tk.Label(self.card, text="Reset Password", bg=PAPER, fg=INK, font=("Segoe UI",16,"bold")).pack(pady=(22,6))
        self.e_user  = self.field("USERNAME")
        self.e_phone = self.field("PHONE NUMBER")
        self.e_p1    = self.field("NEW PASSWORD", show="•")
        self.e_p2    = self.field("CONFIRM PASSWORD", show="•")
        row = tk.Frame(self.card, bg=PAPER); row.pack(fill="x", pady=(6,20))
        tk.Button(row, text="BACK TO LOGIN", font=("Segoe UI",11), relief="solid", bd=1,
                  command=lambda:self.app.show("LoginPage")).pack(side="left", padx=40, ipadx=10, ipady=6)
        tk.Button(row, text="RESET PASSWORD", font=("Segoe UI",11,"bold"), relief="solid", bd=1,
                  command=self.do_reset).pack(side="right", padx=40, ipadx=10, ipady=6)

    def do_reset(self):
        u, ph, p1, p2 = self.e_user.get().strip(), self.e_phone.get().strip(), self.e_p1.get().strip(), self.e_p2.get().strip()
        if not u or not ph or not p1 or not p2:
            messagebox.showerror("Error","กรอกข้อมูลให้ครบ"); return
        if p1 != p2:
            messagebox.showerror("Error","รหัสผ่านยืนยันไม่ตรงกัน"); return
        ok, msg = reset_password(u, ph, p1)
        if ok:
            messagebox.showinfo("Success", msg)
            self.app.show("LoginPage")
        else:
            messagebox.showerror("Error", msg)

# ---------- After login ----------
class HomePage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=CREAM); self.app = app
        top = tk.Frame(self, bg=CREAM); top.pack(fill="x", pady=10, padx=16)
        self.lbl_user = tk.Label(top, text="", bg=CREAM, fg=INK, font=("Segoe UI",12,"bold"))
        self.lbl_user.pack(side="left")
        tk.Button(top, text="Order History", bg=PAPER, fg=INK, bd=0, command=lambda:app.show("HistoryPage")).pack(side="right", padx=6)
        tk.Button(top, text="Cart", bg=PAPER, fg=INK, bd=0, command=lambda:app.show("CartPage")).pack(side="right", padx=6)
        tk.Button(top, text="Log out", bg=PAPER, fg=INK, bd=0, command=lambda:(setattr(app,'current_user',None), app.show("LoginPage"))).pack(side="right", padx=6)
        self.btn_admin = tk.Button(top, text="Admin", bg=PAPER, fg=INK, bd=0, command=lambda:app.show("AdminPage"))

        center = tk.Frame(self, bg=CREAM); center.pack(expand=True)
        self._round(center, "FOOD", lambda:self.open_cat("FOOD")).grid(row=0, column=0, padx=40, pady=40)
        self._round(center, "DRINK", lambda:self.open_cat("DRINK")).grid(row=0, column=1, padx=40, pady=40)
        self._round(center, "CART", lambda:app.show("CartPage")).grid(row=0, column=2, padx=40, pady=40)

    def _round(self, parent, text, cmd):
        f = tk.Frame(parent, bg=CREAM)
        c = tk.Canvas(f, width=180, height=180, bg=CREAM, highlightthickness=0)
        c.pack()
        cid = c.create_oval(10,10,170,170, fill=PAPER, outline=ACCENT, width=2)
        c.create_text(90,90, text=text, font=("Segoe UI",18,"bold"), fill=INK)
        btn = tk.Button(f, text="", command=cmd, bg=PAPER, activebackground=PAPER, bd=0, highlightthickness=0)
        btn.place(x=10,y=10,width=160,height=160)
        btn.bind("<Enter>", lambda e:c.itemconfig(cid, outline="#8d623c"))
        btn.bind("<Leave>", lambda e:c.itemconfig(cid, outline=ACCENT))
        return f

    def open_cat(self, cat):
        page: CatalogPage = self.app.frames["CatalogPage"]
        page.set_category(cat)
        self.app.show("CatalogPage")

    def on_show(self):
        u = self.app.current_user
        if not u: self.app.show("LoginPage"); return
        self.lbl_user.config(text=f"👤 {u['username']}")
        if u.get("is_admin"): self.btn_admin.pack(side="right", padx=6)
        else: self.btn_admin.pack_forget()

class CatalogPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=CREAM); self.app = app; self.category="FOOD"
        top = tk.Frame(self, bg=CREAM); top.pack(fill="x", padx=16, pady=8)
        self.lbl = tk.Label(top, text="CATALOG", bg=CREAM, fg=INK, font=("Segoe UI",18,"bold")); self.lbl.pack(side="left")
        tk.Button(top, text="Back", bg=PAPER, fg=INK, bd=0, command=lambda:app.show("HomePage")).pack(side="right", padx=6)
        tk.Button(top, text="Cart", bg=PAPER, fg=INK, bd=0, command=lambda:app.show("CartPage")).pack(side="right", padx=6)

        body = tk.Frame(self, bg=CREAM); body.pack(fill="both", expand=True, padx=16, pady=8)
        self.tree = ttk.Treeview(body, columns=("name","price","active"), show="headings", height=16)
        self.tree.heading("name", text="Name"); self.tree.column("name", width=420, anchor="w")
        self.tree.heading("price", text="Price"); self.tree.column("price", width=120, anchor="e")
        self.tree.heading("active", text="Active"); self.tree.column("active", width=80, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)
        sc = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=sc.set); sc.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.preview_selected)

        bottom = tk.Frame(self, bg=CREAM); bottom.pack(fill="x", padx=16, pady=8)
        tk.Button(bottom, text="Add to Cart", bg=ACCENT, fg="white", bd=0, command=self.add_selected).pack(side="left")
        tk.Label(bottom, text="Quantity:", bg=CREAM, fg=INK).pack(side="left", padx=(12,4))
        self.qty = tk.IntVar(value=1); tk.Spinbox(bottom, from_=1, to=99, width=5, textvariable=self.qty).pack(side="left")

        self.preview_lbl = tk.Label(self, bg=CREAM); self.preview_lbl.pack(pady=8)
        self.preview_img = None

    def set_category(self, cat):
        self.category = cat
        self.lbl.config(text=f"{'FOOD' if cat=='FOOD' else 'DRINK'} MENU")
        self.reload()

    def reload(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        con = connect_db(); cur = con.cursor()
        cur.execute("SELECT id,name,price,is_active,image_path FROM products WHERE category=? ORDER BY name", (self.category,))
        self.rows = cur.fetchall(); con.close()
        for pid,name,price,active,img in self.rows:
            self.tree.insert("", "end", iid=str(pid), values=(name, f"{price:.2f}", "Yes" if active else "No"))
        self.preview_lbl.config(image="", text="(เลือกรายการเพื่อดูรูป)")
        self.preview_img = None

    def preview_selected(self, *_):
        sel = self.tree.selection()
        if not sel: return
        pid = int(sel[0])
        row = next((r for r in self.rows if r[0]==pid), None)
        if not row: return
        imgp = row[4]
        if imgp and os.path.exists(imgp):
            self.preview_img = load_photo(imgp, 360, 240, cover=False)
            if self.preview_img:
                self.preview_lbl.config(image=self.preview_img, text="")
            else:
                self.preview_lbl.config(image="", text="(โหลดรูปไม่ได้)")
        else:
            self.preview_lbl.config(image="", text="(ยังไม่มีรูป)")

    def add_selected(self):
        sel = self.tree.selection()
        if not sel: messagebox.showwarning("Warning","กรุณาเลือกรายการ"); return
        pid = int(sel[0])
        qty = max(1, int(self.qty.get()))
        # active?
        con = connect_db(); cur = con.cursor()
        cur.execute("SELECT is_active FROM products WHERE id=?", (pid,))
        r = cur.fetchone(); con.close()
        if r and r[0]==1:
            self.app.add_to_cart(pid, qty)
            messagebox.showinfo("Added","ใส่ในตะกร้าแล้ว")
        else:
            messagebox.showwarning("Warning","รายการนี้ถูกปิดใช้งาน")

class CartPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=CREAM); self.app = app
        top = tk.Frame(self, bg=CREAM); top.pack(fill="x", padx=16, pady=8)
        tk.Label(top, text="YOUR CART", bg=CREAM, fg=INK, font=("Segoe UI",18,"bold")).pack(side="left")
        tk.Button(top, text="Back", bg=PAPER, fg=INK, bd=0, command=lambda:app.show("HomePage")).pack(side="right")
        self.tree = ttk.Treeview(self, columns=("name","price","qty","sub"), show="headings", height=18)
        for h,w,a in [("name",420,"w"),("price",100,"e"),("qty",80,"center"),("sub",120,"e")]:
            self.tree.heading(h, text=h.title()); self.tree.column(h, width=w, anchor=a)
        self.tree.pack(fill="both", expand=True, padx=16, pady=8)
        bottom = tk.Frame(self, bg=CREAM); bottom.pack(fill="x", padx=16, pady=8)
        tk.Button(bottom, text="Remove", bg=PAPER, fg=INK, bd=0, command=self.remove).pack(side="left")
        tk.Label(bottom, text="Set Qty:", bg=CREAM, fg=INK).pack(side="left", padx=(10,4))
        self.qty = tk.IntVar(value=1); tk.Spinbox(bottom, from_=1, to=99, width=5, textvariable=self.qty).pack(side="left")
        tk.Button(bottom, text="Apply", bg=PAPER, fg=INK, bd=0, command=self.apply_qty).pack(side="left", padx=6)
        self.lbl_total = tk.Label(bottom, text="Total: 0.00", bg=CREAM, fg=INK, font=("Segoe UI",12,"bold")); self.lbl_total.pack(side="right")
        tk.Button(bottom, text="Checkout", bg=ACCENT, fg="white", bd=0, font=("Segoe UI",11,"bold"),
                  command=self.checkout).pack(side="right", padx=8)

    def on_show(self): self.reload()

    def reload(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        total = 0.0
        if not self.app.cart:
            self.lbl_total.config(text="Total: 0.00"); return
        con = connect_db(); cur = con.cursor()
        for pid, qty in self.app.cart.items():
            cur.execute("SELECT name, price FROM products WHERE id=?", (pid,))
            row = cur.fetchone()
            if row:
                name, price = row
                sub = price * qty; total += sub
                self.tree.insert("", "end", iid=str(pid), values=(name, f"{price:.2f}", qty, f"{sub:.2f}"))
        con.close()
        self.lbl_total.config(text=f"Total: {total:.2f}")

    def selected_pid(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def remove(self):
        pid = self.selected_pid()
        if pid is None: return
        self.app.cart.pop(pid, None)
        self.reload()

    def apply_qty(self):
        pid = self.selected_pid()
        if pid is None: return
        q = max(1, int(self.qty.get()))
        self.app.set_cart_qty(pid, q)
        self.reload()

    def checkout(self):
        if not self.app.current_user:
            messagebox.showerror("Error","กรุณาเข้าสู่ระบบ"); return
        if not self.app.cart:
            messagebox.showwarning("Warning","ตะกร้าว่าง"); return
        con = connect_db(); cur = con.cursor()
        total = 0.0; items=[]
        for pid, qty in self.app.cart.items():
            cur.execute("SELECT price FROM products WHERE id=?", (pid,))
            row = cur.fetchone()
            if not row: continue
            price = row[0]; total += price*qty; items.append((pid, qty, price))
        cur.execute("INSERT INTO orders(user_id,total,created_at) VALUES(?,?,?)",
                    (self.app.current_user["id"], total, ts()))
        oid = cur.lastrowid
        for pid, qty, price in items:
            cur.execute("INSERT INTO order_items(order_id,product_id,qty,price) VALUES(?,?,?,?)",
                        (oid, pid, qty, price))
        con.commit(); con.close()
        self.app.cart.clear()
        self.reload()
        messagebox.showinfo("Success","ชำระเงินสำเร็จ!")

class HistoryPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=CREAM); self.app = app
        top = tk.Frame(self, bg=CREAM); top.pack(fill="x", padx=16, pady=8)
        tk.Label(top, text="ORDER HISTORY", bg=CREAM, fg=INK, font=("Segoe UI",18,"bold")).pack(side="left")
        tk.Button(top, text="Back", bg=PAPER, fg=INK, bd=0, command=lambda:app.show("HomePage")).pack(side="right")
        self.tree = ttk.Treeview(self, columns=("id","created","total"), show="headings", height=18)
        for h,w,a in [("id",80,"center"),("created",240,"w"),("total",120,"e")]:
            self.tree.heading(h, text=h.upper()); self.tree.column(h, width=w, anchor=a)
        self.tree.pack(fill="both", expand=True, padx=16, pady=8)

    def on_show(self):
        u = self.app.current_user
        if not u: self.app.show("LoginPage"); return
        for i in self.tree.get_children(): self.tree.delete(i)
        con = connect_db(); cur = con.cursor()
        cur.execute("SELECT id, created_at, total FROM orders WHERE user_id=? ORDER BY id DESC", (u["id"],))
        for oid, created, total in cur.fetchall():
            self.tree.insert("", "end", values=(oid, created, f"{total:.2f}"))
        con.close()

# ---------- Admin ----------
class AdminPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=CREAM); self.app = app
        top = tk.Frame(self, bg=CREAM); top.pack(fill="x", padx=16, pady=8)
        tk.Label(top, text="ADMIN — PRODUCTS", bg=CREAM, fg=INK, font=("Segoe UI",18,"bold")).pack(side="left")
        tk.Button(top, text="Sales Summary", bg=PAPER, fg=INK, bd=0, command=lambda:app.show("SalesPage")).pack(side="right", padx=6)
        tk.Button(top, text="Back", bg=PAPER, fg=INK, bd=0, command=lambda:app.show("HomePage")).pack(side="right")
        self.tree = ttk.Treeview(self, columns=("id","name","category","price","active","image"), show="headings", height=16)
        for h,w,a in [("id",60,"center"),("name",280,"w"),("category",90,"center"),("price",80,"e"),("active",70,"center"),("image",260,"w")]:
            self.tree.heading(h, text=h.upper()); self.tree.column(h, width=w, anchor=a)
        self.tree.pack(fill="both", expand=True, padx=16, pady=8)
        bottom = tk.Frame(self, bg=CREAM); bottom.pack(fill="x", padx=16, pady=8)
        tk.Button(bottom, text="Add", bg=ACCENT, fg="white", bd=0, command=self.add).pack(side="left")
        tk.Button(bottom, text="Edit", bg=PAPER, fg=INK, bd=0, command=self.edit).pack(side="left", padx=6)
        tk.Button(bottom, text="Toggle Active", bg=PAPER, fg=INK, bd=0, command=self.toggle).pack(side="left", padx=6)
        tk.Button(bottom, text="Choose Image", bg=PAPER, fg=INK, bd=0, command=self.choose_image).pack(side="left", padx=6)
        tk.Button(bottom, text="Reload", bg=PAPER, fg=INK, bd=0, command=self.reload).pack(side="left", padx=6)

    def on_show(self):
        u = self.app.current_user
        if not u or not u.get("is_admin"):
            messagebox.showerror("Error","เฉพาะผู้ดูแลระบบ")
            self.app.show("HomePage"); return
        self.reload()

    def reload(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        con = connect_db(); cur = con.cursor()
        cur.execute("SELECT id,name,category,price,is_active,image_path FROM products ORDER BY category,name")
        for r in cur.fetchall():
            self.tree.insert("", "end", iid=str(r[0]), values=(r[0], r[1], r[2], f"{r[3]:.2f}", "Yes" if r[4] else "No", r[5] or ""))
        con.close()

    def selected_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def add(self):
        ProductDialog(self, None).wait_window(); self.reload()

    def edit(self):
        pid = self.selected_id()
        if pid is None: return
        ProductDialog(self, pid).wait_window(); self.reload()

    def toggle(self):
        pid = self.selected_id()
        if pid is None: return
        con = connect_db(); cur = con.cursor()
        cur.execute("UPDATE products SET is_active=CASE is_active WHEN 1 THEN 0 ELSE 1 END WHERE id=?", (pid,))
        con.commit(); con.close(); self.reload()

    def choose_image(self):
        pid = self.selected_id()
        if pid is None: return
        path = filedialog.askopenfilename(title="เลือกรูปสินค้า", filetypes=[("Images","*.png;*.jpg;*.jpeg;*.gif")])
        if not path: return
        con = connect_db(); cur = con.cursor()
        cur.execute("UPDATE products SET image_path=? WHERE id=?", (path, pid))
        con.commit(); con.close(); self.reload()

class ProductDialog(tk.Toplevel):
    def __init__(self, admin_page: AdminPage, product_id):
        super().__init__(admin_page)
        self.admin_page = admin_page; self.product_id = product_id
        self.title("Product"); self.configure(bg=PAPER); self.resizable(False, False)
        tk.Label(self, text="Name:", bg=PAPER).grid(row=0, column=0, sticky="e", padx=8, pady=8)
        tk.Label(self, text="Category:", bg=PAPER).grid(row=1, column=0, sticky="e", padx=8, pady=8)
        tk.Label(self, text="Price:", bg=PAPER).grid(row=2, column=0, sticky="e", padx=8, pady=8)
        tk.Label(self, text="Image Path:", bg=PAPER).grid(row=3, column=0, sticky="e", padx=8, pady=8)
        self.ent_name = tk.Entry(self, width=34); self.ent_name.grid(row=0, column=1, padx=8, pady=8)
        self.cmb_cat = ttk.Combobox(self, values=["FOOD","DRINK"], state="readonly", width=30); self.cmb_cat.grid(row=1, column=1, padx=8, pady=8)
        self.ent_price= tk.Entry(self, width=34); self.ent_price.grid(row=2, column=1, padx=8, pady=8)
        self.ent_img  = tk.Entry(self, width=34); self.ent_img.grid(row=3, column=1, padx=8, pady=8)
        tk.Button(self, text="Browse", command=self.browse).grid(row=3, column=2, padx=8, pady=8)
        tk.Button(self, text="Save", bg=ACCENT, fg="white", command=self.save).grid(row=4, column=1, pady=12)
        tk.Button(self, text="Cancel", command=self.destroy).grid(row=4, column=2, pady=12)
        if product_id:
            con = connect_db(); cur = con.cursor()
            cur.execute("SELECT name,category,price,image_path FROM products WHERE id=?", (product_id,))
            r = cur.fetchone(); con.close()
            if r:
                self.ent_name.insert(0, r[0]); self.cmb_cat.set(r[1]); self.ent_price.insert(0, f"{r[2]:.2f}")
                if r[3]: self.ent_img.insert(0, r[3])
        else:
            self.cmb_cat.set("FOOD")

    def browse(self):
        path = filedialog.askopenfilename(title="เลือกรูป", filetypes=[("Images","*.png;*.jpg;*.jpeg;*.gif")])
        if path: self.ent_img.delete(0, tk.END); self.ent_img.insert(0, path)

    def save(self):
        name = self.ent_name.get().strip(); cat = self.cmb_cat.get().strip()
        try: price = float(self.ent_price.get().strip())
        except: messagebox.showerror("Error","ราคาไม่ถูกต้อง"); return
        imgp = self.ent_img.get().strip() or None
        con = connect_db(); cur = con.cursor()
        if self.product_id:
            cur.execute("UPDATE products SET name=?,category=?,price=?,image_path=? WHERE id=?",
                        (name, cat, price, imgp, self.product_id))
        else:
            cur.execute("INSERT INTO products(name,category,price,image_path) VALUES(?,?,?,?)",
                        (name, cat, price, imgp))
        con.commit(); con.close(); self.destroy()

class SalesPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=CREAM); self.app = app
        top = tk.Frame(self, bg=CREAM); top.pack(fill="x", padx=16, pady=8)
        tk.Label(top, text="ADMIN — SALES SUMMARY", bg=CREAM, fg=INK, font=("Segoe UI",18,"bold")).pack(side="left")
        tk.Button(top, text="Back", bg=PAPER, fg=INK, bd=0, command=lambda:app.show("AdminPage")).pack(side="right")
        board = tk.Frame(self, bg=CREAM); board.pack(fill="both", expand=True, padx=16, pady=8)
        self.lbl_total = self._stat(board, "Total Revenue", 0, 0)
        self.lbl_orders= self._stat(board, "Orders", 0, 1)
        self.lbl_items = self._stat(board, "Items Sold", 1, 0)
        self.lbl_avg   = self._stat(board, "Avg / Order", 1, 1)
        self.tree = ttk.Treeview(self, columns=("id","created","user","total"), show="headings", height=14)
        for h,w,a in [("id",80,"center"),("created",240,"w"),("user",200,"w"),("total",120,"e")]:
            self.tree.heading(h, text=h.upper()); self.tree.column(h, width=w, anchor=a)
        self.tree.pack(fill="both", expand=True, padx=16, pady=8)

    def _stat(self, parent, title, r, c):
        frm = tk.Frame(parent, bg=PAPER); frm.grid(row=r, column=c, sticky="nsew", padx=8, pady=8)
        parent.grid_columnconfigure(c, weight=1); parent.grid_rowconfigure(r, weight=1)
        tk.Label(frm, text=title, bg=PAPER, fg=INK, font=("Segoe UI",12,"bold")).pack(anchor="w", padx=12, pady=(10,0))
        lbl = tk.Label(frm, text="0", bg=PAPER, fg=ACCENT, font=("Segoe UI",22,"bold")); lbl.pack(anchor="w", padx=12, pady=(0,12))
        return lbl

    def on_show(self):
        u = self.app.current_user
        if not u or not u.get("is_admin"):
            self.app.show("HomePage"); return
        con = connect_db(); cur = con.cursor()
        cur.execute("SELECT IFNULL(SUM(total),0), COUNT(*) FROM orders")
        total, orders = cur.fetchone()
        cur.execute("SELECT IFNULL(SUM(qty),0) FROM order_items")
        items = cur.fetchone()[0]
        avg = (total/orders) if orders else 0
        self.lbl_total.config(text=f"{total:.2f}")
        self.lbl_orders.config(text=str(orders))
        self.lbl_items.config(text=str(items))
        self.lbl_avg.config(text=f"{avg:.2f}")
        for i in self.tree.get_children(): self.tree.delete(i)
        cur.execute("""SELECT o.id,o.created_at,u.username,o.total
                       FROM orders o JOIN users u ON o.user_id=u.id
                       ORDER BY o.id DESC LIMIT 50""")
        for r in cur.fetchall():
            self.tree.insert("", "end", values=(r[0], r[1], r[2], f"{r[3]:.2f}"))
        con.close()

# ---------- Run ----------
if __name__ == "__main__":
    App().mainloop()
