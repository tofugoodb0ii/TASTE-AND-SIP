# -*- coding: utf-8 -*-
"""
TASTE & SIP — Auth (customtkinter only, cream/minimal)
- ไม่มี OTP; ลืมรหัส = ยืนยัน USERNAME + EMAIL/PHONE -> ตั้งรหัสใหม่
- ทุกหน้าฟอร์มสูงเท่ากัน FIELD_H, โทนครีมมินิมอล
- ไม่ใช้ tkinter/ttk/messagebox/Canvas แล้ว (UI = customtkinter ทั้งหมด)
- DB: taste_and_sip.db (seed admin/admin123)

Run: python taste_and_sip_app.py
"""

import os, re, sqlite3, hashlib, json
from datetime import datetime as dt, timedelta
from typing import Optional, Callable

import customtkinter as ctk
from PIL import Image

APP_TITLE = "TASTE AND SIP"

# ===== Theme / Palette (Cream/Minimal) =====
RIGHT_BG   = "#f8eedb"   # page background
CARD_BG    = "#edd8b8"   # deeper cream for card
TEXT_DARK  = "#1f2937"
LINK_FG    = "#0057b7"
BORDER     = "#d3c6b4"
CARD_W     = 660
CARD_H     = 560
RADIUS     = 18

# ===== Size tokens =====
FIELD_W        = 380
FIELD_W_HALF   = 240
FIELD_W_DOUBLE = FIELD_W_HALF*2 + 20
FIELD_H        = 42
FORM_PADX      = 24

DB_FILE = "taste_and_sip.db"
ASSETS_DIR = "assets"
IMG_DIR    = os.path.join(ASSETS_DIR, "images")
os.makedirs(IMG_DIR, exist_ok=True)

# ===== Helpers =====
def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def now_ts() -> str:
    return dt.now().strftime("%Y-%m-%d %H:%M:%S")

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
    """Auth DB: focuses on users table. Seeds admin if missing."""
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

class InfoBar(ctk.CTkLabel):
    """ใช้แทน messagebox ทั้งหมด"""
    def __init__(self, master):
        super().__init__(master, text="", text_color="#1f2937",
                         fg_color="#f6e8d3",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         corner_radius=RADIUS, padx=8, pady=6)
    def set(self, text: str, ok: bool=False):
        self.configure(text=(text or "").upper(),
                       text_color=("#166534" if ok else "#b00020"),
                       fg_color=("#d9f99d" if ok else "#fde2e2"))

class LabeledEntry(ctk.CTkFrame):
    """ช่องกรอกพร้อมป้าย — ใช้ได้ทั้งคอลัมน์เดี่ยว/คู่"""
    def __init__(self, master, label: str, show: str = "", width: int = FIELD_W):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=label.upper(), text_color="#333333",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     fg_color="transparent").grid(row=0, column=0, sticky="w", padx=2, pady=(0,2))
        self.entry = ctk.CTkEntry(self, show=show, corner_radius=RADIUS,
                                  border_color=BORDER, fg_color="white",
                                  width=width, height=FIELD_H)
        self.entry.grid(row=1, column=0, sticky="w")

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

        # Left (ภาพ + ข้อความขาว) -> ใช้ CTkLabel + image (ไม่ใช้ tk.Canvas)
        self.left = ctk.CTkFrame(self, fg_color=RIGHT_BG, corner_radius=0)
        self.left.grid(row=0, column=0, sticky="nsew")
        self._left_img = None
        self._left_img_ctk = None
        self.left.bind("<Configure>", lambda e: self._draw_left_bg())

        # Right
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

    # left painting replacement (no Canvas)
    def _draw_left_bg(self):
        for w in self.left.winfo_children():
            w.destroy()
        holder = ctk.CTkFrame(self.left, fg_color="#000000")
        holder.place(relx=0, rely=0, relwidth=1, relheight=1)
        if self.left_bg_path and os.path.exists(self.left_bg_path):
            try:
                self._left_img = Image.open(self.left_bg_path).convert("RGB")
                w = max(300, int(self.left.winfo_width()))
                h = max(300, int(self.left.winfo_height()))
                img = self._left_img.copy()
                iw, ih = img.size
                scale = max(w/iw, h/ih)
                img = img.resize((int(iw*scale), int(ih*scale)), Image.LANCZOS)
                # crop center
                iw2, ih2 = img.size
                left = max(0, (iw2 - w)//2); top = max(0, (ih2 - h)//2)
                img = img.crop((left, top, left+w, top+h))
                self._left_img_ctk = ctk.CTkImage(light_image=img, size=(w, h))
                ctk.CTkLabel(holder, image=self._left_img_ctk, text="").place(relx=0, rely=0, relwidth=1, relheight=1)
            except Exception:
                pass
        # overlay texts
        overlay = ctk.CTkFrame(holder, fg_color=("black", "black"))
        overlay.configure(fg_color="#000000")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        ctk.CTkLabel(overlay, text=f"WELCOME TO\n{APP_TITLE}".upper(),
                     font=ctk.CTkFont(size=36, weight="bold"),
                     text_color="white").place(x=28, y=28)
        ctk.CTkLabel(overlay, text="FOOD AND DRINK!".upper(),
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="white").place(x=32, y=110)

    def _render_logo(self):
        for w in self.logo_wrap.winfo_children():
            w.destroy()
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                img = Image.open(self.logo_path)
                _logo = ctk.CTkImage(light_image=img, size=(220, 220))
                ctk.CTkLabel(self.logo_wrap, image=_logo, text="", fg_color="transparent").pack()
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

    # =================== SCREENS ===================
    def show_signin(self):
        self._clear_card()
        Title(self.card, "SIGN IN").pack(pady=(22, 6))
        self.si_info = InfoBar(self.card); self.si_info.pack(padx=FORM_PADX, fill="x", pady=(0,8))
        self.si_info.set("")  # clear

        self.si_user = LabeledEntry(self.card, "USERNAME", width=FIELD_W)
        self.si_user.pack(padx=FORM_PADX, pady=(6, 8), anchor="w")
        self.si_pwd  = LabeledEntry(self.card, "PASSWORD", show="•", width=FIELD_W)
        self.si_pwd.pack(padx=FORM_PADX, pady=(6, 12), anchor="w")
        SubmitBtn(self.card, "SIGN IN", command=self._signin).pack(
            padx=FORM_PADX, pady=(0, 12), anchor="w"
        )
        bottom = ctk.CTkFrame(self.card, fg_color="transparent"); bottom.pack(fill="x", pady=(4, 18))
        LinkBtn(bottom, "FORGOT PASSWORD?", command=self.show_forgot).pack(side="left", padx=4)
        LinkBtn(bottom, "CREATE ACCOUNT", command=self.show_signup).pack(side="right", padx=4)

    def show_signup(self):
        self._clear_card()
        Title(self.card, "CREATE ACCOUNT").pack(pady=(22, 6))
        self.su_info = InfoBar(self.card); self.su_info.pack(padx=FORM_PADX, fill="x", pady=(0,8))
        self.su_info.set("")

        form = ctk.CTkFrame(self.card, fg_color="transparent")
        form.pack(fill="x", padx=FORM_PADX, pady=(6, 10))
        form.grid_columnconfigure(0, weight=1, uniform="c")
        form.grid_columnconfigure(1, weight=1, uniform="c")

        self.su_user  = LabeledEntry(form, "USERNAME", width=FIELD_W_HALF)
        self.su_user.grid(row=0, column=0, padx=8, pady=6, sticky="w")
        self.su_phone = LabeledEntry(form, "PHONE", width=FIELD_W_HALF)
        self.su_phone.grid(row=0, column=1, padx=8, pady=6, sticky="w")

        self.su_email = LabeledEntry(form, "EMAIL", width=FIELD_W_DOUBLE)
        self.su_email.grid(row=1, column=0, columnspan=2, padx=8, pady=6, sticky="w")

        self.su_pwd1  = LabeledEntry(form, "PASSWORD", show="•", width=FIELD_W_HALF)
        self.su_pwd1.grid(row=2, column=0, padx=8, pady=6, sticky="w")
        self.su_pwd2  = LabeledEntry(form, "CONFIRM PASSWORD", show="•", width=FIELD_W_HALF)
        self.su_pwd2.grid(row=2, column=1, padx=8, pady=6, sticky="w")

        SubmitBtn(self.card, "REGISTER", command=self._signup).pack(
            padx=FORM_PADX, pady=(8, 12), anchor="w"
        )
        LinkBtn(self.card, "BACK TO LOGIN", command=self.show_signin).pack(pady=(0, 18))

    def show_forgot(self):
        self._clear_card()
        Title(self.card, "FORGOT PASSWORD").pack(pady=(22, 6))
        self.fp_info = InfoBar(self.card); self.fp_info.pack(padx=FORM_PADX, fill="x", pady=(0,8))
        self.fp_info.set("")
        self.fp_user = LabeledEntry(self.card, "USERNAME", width=FIELD_W)
        self.fp_user.pack(padx=FORM_PADX, pady=(6, 8), anchor="w")
        self.fp_contact = LabeledEntry(self.card, "EMAIL OR PHONE", width=FIELD_W)
        self.fp_contact.pack(padx=FORM_PADX, pady=(6, 10), anchor="w")
        SubmitBtn(self.card, "VERIFY", command=self._forgot_verify).pack(
            padx=FORM_PADX, pady=(0, 12), anchor="w"
        )

        self.fp_step2 = ctk.CTkFrame(self.card, fg_color="transparent"); self.fp_step2.pack(fill="x", padx=FORM_PADX, pady=(6, 12))
        self.fp_step2.grid_columnconfigure(0, weight=1)
        self.fp_step2.pack_forget()

        self.fp_pwd1 = LabeledEntry(self.fp_step2, "NEW PASSWORD", show="•", width=FIELD_W)
        self.fp_pwd1.pack(pady=(6, 8), anchor="w")
        self.fp_pwd2 = LabeledEntry(self.fp_step2, "CONFIRM NEW PASSWORD", show="•", width=FIELD_W)
        self.fp_pwd2.pack(pady=(6, 10), anchor="w")
        SubmitBtn(self.fp_step2, "CHANGE PASSWORD", command=self._forgot_change).pack(pady=(0, 10), anchor="w")

        LinkBtn(self.card, "BACK TO LOGIN", command=self.show_signin).pack(pady=(0, 18))
        self._verified_username = None

    # actions
    def _signin(self):
        self.si_info.set("")
        u = (self.si_user.get() or "").strip(); p = (self.si_pwd.get() or "").strip()
        if not u or not p:
            self.si_info.set("PLEASE ENTER USERNAME AND PASSWORD."); return
        row = self.db.find_user_for_login(u, p)
        if row:
            self.si_info.set(f"WELCOME, {u}!", ok=True)
            if self.on_login_success: self.on_login_success(row)
        else:
            self.si_info.set("INVALID CREDENTIALS.")

    def _signup(self):
        self.su_info.set("")
        u  = (self.su_user.get() or "").strip()
        ph = (self.su_phone.get() or "").strip()
        em = (self.su_email.get() or "").strip()
        p1 = (self.su_pwd1.get() or "").strip()
        p2 = (self.su_pwd2.get() or "").strip()
        for fn in (lambda: validate_username(u), lambda: validate_phone(ph), lambda: validate_email(em), lambda: validate_password(p1)):
            msg = fn()
            if msg: self.su_info.set(msg); return
        if p1 != p2:
            self.su_info.set("PASSWORDS DO NOT MATCH."); return
        if self.db.username_exists(u):
            self.su_info.set("USERNAME ALREADY EXISTS."); return
        try:
            self.db.create_user(u, ph, em, p1)
            self.su_info.set("ACCOUNT CREATED. PLEASE SIGN IN.", ok=True)
        except sqlite3.IntegrityError:
            self.su_info.set("USERNAME ALREADY EXISTS.")
        except Exception as e:
            self.su_info.set(f"FAILED TO REGISTER: {e}")

    def _forgot_verify(self):
        self.fp_info.set("")
        u = (self.fp_user.get() or "").strip(); cp = (self.fp_contact.get() or "").strip()
        if not u or not cp:
            self.fp_info.set("PLEASE FILL USERNAME AND EMAIL/PHONE."); return
        row = self.db.verify_user_contact(u, cp)
        if row:
            self._verified_username = u
            self.fp_info.set("VERIFIED. PLEASE SET A NEW PASSWORD BELOW.", ok=True)
            self.fp_step2.pack(fill="x", padx=FORM_PADX, pady=(6, 12))
        else:
            self.fp_info.set("NO MATCHING ACCOUNT FOR THE GIVEN USERNAME AND EMAIL/PHONE.")

    def _forgot_change(self):
        if not getattr(self, "_verified_username", None):
            self.fp_info.set("PLEASE VERIFY FIRST."); return
        p1 = (self.fp_pwd1.get() or "").strip(); p2 = (self.fp_pwd2.get() or "").strip()
        msg = validate_password(p1)
        if msg: self.fp_info.set(msg); return
        if p1 != p2: self.fp_info.set("PASSWORDS DO NOT MATCH."); return
        try:
            self.db.change_password(self._verified_username, p1)
            self.fp_info.set("PASSWORD CHANGED. YOU CAN SIGN IN NOW.", ok=True)
        except Exception as e:
            self.fp_info.set(f"FAILED TO CHANGE PASSWORD: {e}")

# ------------------- Placeholder Admin (CTk only) ---------------------
class AdminApp(ctk.CTk):
    """โครง Admin minimal (CTk-only) — ไว้ล็อกอิน admin แล้วขึ้นหน้าเปล่า ๆ สีครีม
    * ถ้าต้องการย้ายทุกตาราง/ออเดอร์/โปรโมชัน เป็น customtkinter เต็มรูปแบบ แจ้งได้เลย
    """
    def __init__(self, admin_row: sqlite3.Row):
        super().__init__()
        ctk.set_appearance_mode("light")
        self.title(f"{APP_TITLE} — ADMIN")
        try: self.state("zoomed")
        except: self.geometry("1280x800")
        self.configure(fg_color=RIGHT_BG)
        wrap = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=RADIUS, border_width=1, border_color=BORDER)
        wrap.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(wrap, text=f"ADMIN: {admin_row['username']}", font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=TEXT_DARK).pack(pady=(24,6))
        ctk.CTkLabel(wrap, text="(Admin Dashboard placeholder — CTk only)",
                     text_color="#6b7280").pack()
        ctk.CTkButton(wrap, text="CLOSE", command=self.destroy).pack(pady=24)

# ==============================  MAIN  ================================
if __name__ == "__main__":
    # ตั้ง path รูป (ใส่ภาพของคุณเองได้)
    LEFT_BG_PATH = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\AVIBRA_1.png"
    LOGO_PATH    = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\lologogo.png-removebg-preview.png"

    def after_login(user_row: sqlite3.Row):
        role = (user_row["role"] or "customer").lower()
        if role == "admin":
            app = AdminApp(user_row)
            app.mainloop()
        else:
            # ลูกค้าทั่วไป: โชว์ข้อความคอนเฟิร์มบนหน้า Sign-in อยู่แล้ว (ผ่าน InfoBar)
            pass

    root = AuthApp(db_path=DB_FILE, left_bg_path=LEFT_BG_PATH, logo_path=LOGO_PATH, on_login_success=after_login)
    root.mainloop()
