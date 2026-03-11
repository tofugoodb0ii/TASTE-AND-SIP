# -*- coding: utf-8 -*-
"""
Auth screens using customtkinter (rounded/modern, cream theme, uppercase)
- Left: image cover via CTkLabel (no Canvas dependency) + fallback cream, titles overlay with spacing.
- Right: rounded cream card; Sign Up uses 2-column compact form (balanced height).
- Validations: username/phone/email/password per spec.
- DB: SQLite users table (compatible). SHA-256 password.

Run: python auth_ctk_round.py
"""

import os, re, sqlite3, hashlib
from typing import Optional, Callable
from PIL import Image
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

# ====== Validation ======
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

        # -------- Left (image & titles via CTkLabel) --------
        self.left = ctk.CTkFrame(self, fg_color=RIGHT_BG, corner_radius=0)
        self.left.grid(row=0, column=0, sticky="nsew")

        # background image holder (cover)
        self.left_bg_label = ctk.CTkLabel(self.left, text="", fg_color="transparent")
        self.left_bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        # overlay texts (ย้าย parent -> left_bg_label ตามที่ขอ)
        self.left_title = ctk.CTkLabel(
            self.left_bg_label,                          # <<<<< เปลี่ยนตรงนี้
            text=f"WELCOME TO\n{APP_TITLE}".upper(),
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color="white",
            fg_color="transparent",
        )
        self.left_sub = ctk.CTkLabel(
            self.left_bg_label,                          # <<<<< และตรงนี้
            text="FOOD AND DRINK!".upper(),
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white",
            fg_color="transparent",
        )
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

    # ---- Left image drawing (cover + titles) ----
    def _draw_left_bg(self):
        # compute half width/height for cover
        w = max(300, int(self.winfo_width() * 0.5))
        h = max(300, self.winfo_height())

        # fallback background
        self.left.configure(fg_color=RIGHT_BG)

        # cover-fit image using CTkImage on CTkLabel
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
                self._left_img = ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))
                self.left_bg_label.configure(image=self._left_img)
            except Exception:
                self.left_bg_label.configure(image=None)
        else:
            self.left_bg_label.configure(image=None)

        # place texts with spacing (บน label ของรูป)
        self.left_title.place(x=28, y=28)
        self.left_sub.place(x=32, y=28 + 36*2 + 18)  # ประมาณสองบรรทัดของขนาด 36

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
        messagebox.showinfo("SIGNED IN", f"HELLO, {user_row['username']}!")

    app = AuthApp(db_path="taste_and_sip.db", left_bg_path=LEFT_BG_PATH, logo_path=LOGO_PATH,
                  on_login_success=_demo_success)
    app.mainloop()
