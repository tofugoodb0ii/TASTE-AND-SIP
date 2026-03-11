# -*- coding: utf-8 -*-
"""
Auth screens using tkinter (balanced layout)
- Left: image cover + dynamic text spacing (no overlap). If image can't fill, fallback is cream background.
- Right: fixed-size card for visual balance; Sign Up uses 2-column compact form.
- Validations: username/phone/email/password per spec.
- DB: SQLite users table (compatible). SHA-256 password.

Run: python auth_m1_tk_v2.py
"""
import os
import re
import sqlite3
import hashlib
from typing import Optional, Callable
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import messagebox

APP_TITLE = "TASTE AND SIP"

# ===== Palette & sizing =====
RIGHT_BG = "#f5efe4"    # cream tone
CARD_BG  = "#ffffff"
TEXT_DARK = "#1f2937"
ACCENT = "#0f62fe"
CARD_W = 560
CARD_H = 520

# ====== Helpers ======
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
        return "Username must be at least 6 characters and contain only A–Z, a–z, 0–9."
    return None

def validate_phone(v: str) -> Optional[str]:
    if not PHONE_RE.match(v or ""):
        return "Phone must be 10 digits."
    return None

def validate_email(v: str) -> Optional[str]:
    if not EMAIL_RE.match(v or ""):
        return "Invalid email format."
    return None

def validate_password(v: str) -> Optional[str]:
    if not PWD_RE.match(v or ""):
        return "Password must be ≥ 8 chars, include uppercase, lowercase and a digit (letters and digits only)."
    return None

# ====== UI ======
class AuthApp(tk.Tk):
    def __init__(self, db_path: str = "taste_and_sip.db", left_bg_path: Optional[str] = None,
                 logo_path: Optional[str] = None,
                 on_login_success: Optional[Callable[[sqlite3.Row], None]] = None):
        super().__init__()
        self.title(APP_TITLE)
        self.state("zoomed")
        self.configure(bg=RIGHT_BG)

        self.db = AuthDB(db_path)
        self.on_login_success = on_login_success
        self.left_bg_path = left_bg_path
        self.logo_path = logo_path

        # grid layout: 2 columns
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left panel (image)
        self.left = tk.Frame(self, bg=RIGHT_BG)
        self.left.grid(row=0, column=0, sticky="nsew")
        self.left.bind("<Configure>", lambda e: self._draw_left_bg())
        self.left_canvas = tk.Canvas(self.left, highlightthickness=0, bg=RIGHT_BG)
        self.left_canvas.pack(fill="both", expand=True)

        # Right panel (logo + card)
        self.right = tk.Frame(self, bg=RIGHT_BG)
        self.right.grid(row=0, column=1, sticky="nsew")
        self.right.grid_rowconfigure(1, weight=1)
        self.right.grid_columnconfigure(0, weight=1)

        self.logo_wrap = tk.Frame(self.right, bg=RIGHT_BG)
        self.logo_wrap.grid(row=0, column=0, pady=(30, 10))
        self._render_logo()

        # fixed-size card for balance
        self.card = tk.Frame(self.right, bg=CARD_BG, bd=1, relief="solid", width=CARD_W, height=CARD_H)
        self.card.grid(row=1, column=0, sticky="n", padx=80, pady=(10, 40))
        self.card.grid_propagate(False)
        self.card.grid_columnconfigure(0, weight=1)

        self.show_signin()

    # --- Left image ---
    def _draw_left_bg(self):
        self.left_canvas.delete("all")
        w = max(300, int(self.winfo_width() * 0.5))
        h = max(300, self.winfo_height())
        self.left_canvas.configure(width=w, height=h)

        # Fill background with cream (so no black gap)
        self.left_canvas.create_rectangle(0, 0, w, h, fill=RIGHT_BG, outline="")

        if self.left_bg_path and os.path.exists(self.left_bg_path):
            try:
                img = Image.open(self.left_bg_path).convert("RGB")
                # Cover resize (crop center)
                img_w, img_h = img.size
                scale = max(w / img_w, h / img_h)
                new_w, new_h = int(img_w * scale), int(img_h * scale)
                img = img.resize((new_w, new_h), Image.LANCZOS)
                left = (new_w - w) // 2
                top = (new_h - h) // 2
                img = img.crop((left, top, left + w, top + h))
                self._left_img = ImageTk.PhotoImage(img)
                self.left_canvas.create_image(0, 0, anchor="nw", image=self._left_img)
            except Exception:
                pass

        # Dynamic spacing for welcome text
        t1 = self.left_canvas.create_text(
            28, 28, anchor="nw", fill="white", font=("Segoe UI", 34, "bold"),
            text=f"WELCOME TO\n{APP_TITLE}"
        )
        bbox = self.left_canvas.bbox(t1)
        y2 = (bbox[3] if bbox else 100) + 14
        self.left_canvas.create_text(32, y2, anchor="nw", fill="white", font=("Segoe UI", 18), text="FOOD AND DRINK!")

    def _render_logo(self):
        for w in self.logo_wrap.winfo_children():
            w.destroy()
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                img = Image.open(self.logo_path)
                img.thumbnail((240, 240), Image.LANCZOS)
                self._logo_img = ImageTk.PhotoImage(img)
                tk.Label(self.logo_wrap, image=self._logo_img, bg=RIGHT_BG).pack()
                return
            except Exception:
                pass
        tk.Label(self.logo_wrap, text=APP_TITLE, font=("Segoe UI", 22, "bold"), bg=RIGHT_BG, fg=TEXT_DARK).pack()

    # --- Card helpers ---
    def _clear_card(self):
        for w in self.card.winfo_children():
            w.destroy()
        self.card.grid_columnconfigure(0, weight=1)

    def show_signin(self):
        self._clear_card()
        Title(self.card, "Sign In").pack(pady=(22, 6))
        self.si_err = ErrorLabel(self.card); self.si_err.pack(padx=24, fill="x")
        self.si_user = LabeledEntry(self.card, "USERNAME"); self.si_user.pack(fill="x", padx=24, pady=(6, 8))
        self.si_pwd  = LabeledEntry(self.card, "PASSWORD", show="•"); self.si_pwd.pack(fill="x", padx=24, pady=(6, 12))
        SubmitBtn(self.card, "SIGN IN", command=self._signin).pack(fill="x", padx=24, pady=(0, 10))
        bottom = tk.Frame(self.card, bg=CARD_BG); bottom.pack(fill="x", pady=(4, 18))
        LinkBtn(bottom, "FORGOT PASSWORD?", command=self.show_forgot).pack(side="left", padx=4)
        LinkBtn(bottom, "CREATE ACCOUNT", command=self.show_signup).pack(side="right", padx=4)

    def show_signup(self):
        self._clear_card()
        Title(self.card, "Create Account").pack(pady=(22, 6))
        self.su_err = ErrorLabel(self.card); self.su_err.pack(padx=24, fill="x")
        form = tk.Frame(self.card, bg=CARD_BG)
        form.pack(fill="x", padx=24, pady=(6, 10))
        for i in (0,1):
            form.grid_columnconfigure(i, weight=1, uniform="c")
        self.su_user  = LabeledEntry(form, "USERNAME");  self.su_user.grid(row=0, column=0, padx=6, pady=6, sticky="ew")
        self.su_phone = LabeledEntry(form, "PHONE");     self.su_phone.grid(row=0, column=1, padx=6, pady=6, sticky="ew")
        self.su_email = LabeledEntry(form, "EMAIL");     self.su_email.grid(row=1, column=0, columnspan=2, padx=6, pady=6, sticky="ew")
        self.su_pwd1  = LabeledEntry(form, "PASSWORD", show="•"); self.su_pwd1.grid(row=2, column=0, padx=6, pady=6, sticky="ew")
        self.su_pwd2  = LabeledEntry(form, "CONFIRM PASSWORD", show="•"); self.su_pwd2.grid(row=2, column=1, padx=6, pady=6, sticky="ew")
        SubmitBtn(self.card, "REGISTER", command=self._signup).pack(fill="x", padx=24, pady=(8, 10))
        LinkBtn(self.card, "BACK TO LOGIN", command=self.show_signin).pack(pady=(0, 18))

    def show_forgot(self):
        self._clear_card()
        Title(self.card, "Forgot Password").pack(pady=(22, 6))
        self.fp_err = ErrorLabel(self.card); self.fp_err.pack(padx=24, fill="x")
        self.fp_user = LabeledEntry(self.card, "USERNAME"); self.fp_user.pack(fill="x", padx=24, pady=(6, 8))
        self.fp_contact = LabeledEntry(self.card, "EMAIL or PHONE"); self.fp_contact.pack(fill="x", padx=24, pady=(6, 10))
        SubmitBtn(self.card, "VERIFY", command=self._forgot_verify).pack(fill="x", padx=24, pady=(0, 10))
        self.fp_step2 = tk.Frame(self.card, bg=CARD_BG); self.fp_step2.pack(fill="x", padx=12, pady=(6, 12))
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
            self.si_err.set("Please enter username and password."); return
        row = self.db.find_user_for_login(u, p)
        if row:
            if self.on_login_success:
                self.on_login_success(row)
            else:
                messagebox.showinfo("Success", f"Welcome, {u}!")
        else:
            self.si_err.set("Invalid credentials.")

    def _signup(self):
        self.su_err.set("")
        u  = (self.su_user.get() or "").strip()
        ph = (self.su_phone.get() or "").strip()
        em = (self.su_email.get() or "").strip()
        p1 = (self.su_pwd1.get() or "").strip()
        p2 = (self.su_pwd2.get() or "").strip()
        for fn in (lambda: validate_username(u), lambda: validate_phone(ph), lambda: validate_email(em), lambda: validate_password(p1)):
            msg = fn()
            if msg:
                self.su_err.set(msg); return
        if p1 != p2:
            self.su_err.set("Passwords do not match."); return
        if self.db.username_exists(u):
            self.su_err.set("Username already exists."); return
        try:
            self.db.create_user(u, ph, em, p1)
            self.su_err.set("Account created. Please sign in.")
        except sqlite3.IntegrityError:
            self.su_err.set("Username already exists.")
        except Exception as e:
            self.su_err.set(f"Failed to register: {e}")

    def _forgot_verify(self):
        self.fp_err.set("")
        u = (self.fp_user.get() or "").strip(); cp = (self.fp_contact.get() or "").strip()
        if not u or not cp:
            self.fp_err.set("Please fill username and email/phone."); return
        row = self.db.verify_user_contact(u, cp)
        if row:
            self._verified_username = u
            self.fp_err.set("Verified. Please set a new password below.")
            self.fp_step2.pack(fill="x", padx=12, pady=(6, 12))
        else:
            self.fp_err.set("No matching account for the given username and email/phone.")

    def _forgot_change(self):
        if not self._verified_username:
            self.fp_err.set("Please verify first."); return
        p1 = (self.fp_pwd1.get() or "").strip(); p2 = (self.fp_pwd2.get() or "").strip()
        msg = validate_password(p1)
        if msg:
            self.fp_err.set(msg); return
        if p1 != p2:
            self.fp_err.set("Passwords do not match."); return
        try:
            self.db.change_password(self._verified_username, p1)
            self.fp_err.set("Password changed. You can sign in now.")
        except Exception as e:
            self.fp_err.set(f"Failed to change password: {e}")

# ====== UI helper widgets ======
class Title(tk.Label):
    def __init__(self, master, text: str):
        super().__init__(master, text=text, font=("Segoe UI", 20, "bold"), bg=CARD_BG, fg=TEXT_DARK)

class ErrorLabel(tk.Label):
    def __init__(self, master):
        super().__init__(master, text="", fg="#b00020", bg=CARD_BG, wraplength=520, justify="left")
    def set(self, text: str):
        self.config(text=text or "")

class LabeledEntry(tk.Frame):
    def __init__(self, master, label: str, show: str = ""):
        super().__init__(master, bg=CARD_BG)
        tk.Label(self, text=label, bg=CARD_BG, fg="#333").grid(row=0, column=0, sticky="w", padx=2)
        self.entry = tk.Entry(self, show=show, relief="solid", bd=1)
        self.entry.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        self.columnconfigure(0, weight=1)
    def get(self) -> str:
        return self.entry.get()
    def set(self, v: str):
        self.entry.delete(0, "end"); self.entry.insert(0, v)

class SubmitBtn(tk.Button):
    def __init__(self, master, text: str, command):
        super().__init__(master, text=text, command=command, height=2, relief="solid", bd=1, bg="#e5e7eb")

class LinkBtn(tk.Button):
    def __init__(self, master, text: str, command):
        super().__init__(master, text=text, command=command, relief="flat", bd=0, bg=CARD_BG, fg="#0066cc", cursor="hand2")

# ====== Standalone run ======
if __name__ == "__main__":
    LEFT_BG_PATH = r"C:\\Users\\thatt\\OneDrive\\Desktop\\python\\Project_tase_and_sip\\image\\AVIBRA_1.png"
    LOGO_PATH    = r"C:\\Users\\thatt\\OneDrive\\Desktop\\python\\Project_tase_and_sip\\image\\lologogo.png-removebg-preview.png"

    def _demo_success(user_row):
        messagebox.showinfo("Signed In", f"Hello, {user_row['username']}! Role={user_row['role']}")

    app = AuthApp(db_path="taste_and_sip.db", left_bg_path=LEFT_BG_PATH, logo_path=LOGO_PATH,
                  on_login_success=_demo_success)
    app.mainloop()
