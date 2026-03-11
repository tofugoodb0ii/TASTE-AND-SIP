# -*- coding: utf-8 -*-
"""
Auth (tkinter) — สไตล์ครีม/การ์ดเหมือนโค้ดของคุณ แต่ใช้ฟังก์ชันเดิมของเรา
- LEFT: รูปภาพแบบ cover + ข้อความไม่ซ้อน (มีระยะห่าง)
- RIGHT: พื้นครีม (#F5ECD9), LOGO ด้านบน, การ์ดครีมเข้มกว่า (#E8DCC4) มีเส้นขอบ
- ฟอร์ม 3 หน้าจอ: SIGN IN / CREATE ACCOUNT (2 คอลัมน์) / FORGOT PASSWORD
- Validation/SQLite/เปลี่ยนรหัส เหมือนเดิม
"""

import os, re, sqlite3, hashlib, tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from typing import Optional, Callable

# ===== Paths (แก้เป็นของเครื่องคุณ) =====
LEFT_BG_PATH = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\AVIBRA_1.png"
LOGO_PATH    = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\lologogo.png-removebg-preview.png"

APP_TITLE = "TASTE AND SIP"

# ===== Theme (โทนเดียวกับโค้ด tkinter ของคุณ) =====
RIGHT_BG   = "#F5ECD9"   # ครีมอ่อน (พื้น)
CARD_BG    = "#E8DCC4"   # ครีมเข้มกว่า (การ์ด)
CARD_EDGE  = "#CDBE9A"   # สีเส้นขอบการ์ด
TXT        = "#1E293B"   # ตัวหนังสือ
ACCENT     = "#111111"
ENTRY_BG   = "#FFFFFF"

CARD_W     = 720   # ความกว้างการ์ด (ใหญ่ขึ้นให้บาลานซ์พื้นที่ขวา)
PADX_OUT   = 40    # padding ซ้ายขวาของการ์ดต่อฟิลด์
GUTTER_X   = 16    # ระยะคอลัมน์ซ้าย-ขวาของฟอร์ม 2 คอลัมน์

# ===== Validation =====
USERNAME_RE = re.compile(r"^[A-Za-z0-9]{6,}$")
PHONE_RE    = re.compile(r"^\d{10}$")
EMAIL_RE    = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PWD_RE      = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,}$")

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def v_username(v): return None if USERNAME_RE.match(v or "") else "USERNAME MUST BE ≥ 6 ALNUM CHARS."
def v_phone(v):    return None if PHONE_RE.match(v or "")    else "PHONE MUST BE 10 DIGITS."
def v_email(v):    return None if EMAIL_RE.match(v or "")    else "INVALID EMAIL."
def v_pwd(v):      return None if PWD_RE.match(v or "")      else "PASSWORD ≥8, UPPER/LOWER/DIGIT."

# ===== DB (เหมือนเดิม) =====
class AuthDB:
    def __init__(self, path="taste_and_sip.db"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._ensure()
    def _ensure(self):
        c=self.conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT, phone TEXT, email TEXT, birthdate TEXT, gender TEXT,
                avatar TEXT, role TEXT DEFAULT 'customer'
            )""")
        self.conn.commit()
    def find_user_for_login(self,u,p):
        return self.conn.execute(
            "SELECT * FROM users WHERE username=? AND password_hash=?",
            (u, sha256(p))
        ).fetchone()
    def username_exists(self,u):
        return self.conn.execute("SELECT 1 FROM users WHERE username=?",(u,)).fetchone() is not None
    def create_user(self,u,ph,em,p):
        self.conn.execute(
            "INSERT INTO users(username,password_hash,phone,email,role) VALUES(?,?,?,?,?)",
            (u, sha256(p), ph, em, "customer")
        ); self.conn.commit()
    def verify_user_contact(self,u,c):
        return self.conn.execute(
            "SELECT * FROM users WHERE username=? AND (email=? OR phone=?)",(u,c,c)
        ).fetchone()
    def change_password(self,u,newp):
        self.conn.execute("UPDATE users SET password_hash=? WHERE username=?",(sha256(newp),u)); self.conn.commit()

# ===== Image helpers =====
def load_cover(path, box_w, box_h) -> Optional[ImageTk.PhotoImage]:
    if not path or not os.path.exists(path): return None
    try:
        img=Image.open(path).convert("RGBA")
        # cover
        rw, rh = box_w/img.width, box_h/img.height
        r=max(rw, rh)
        img=img.resize((max(1,int(img.width*r)), max(1,int(img.height*r))), Image.LANCZOS)
        # crop center
        x=(img.width-box_w)//2; y=(img.height-box_h)//2
        img=img.crop((x, y, x+box_w, y+box_h))
        return ImageTk.PhotoImage(img)
    except: return None

def load_fit(path, max_w, max_h) -> Optional[ImageTk.PhotoImage]:
    if not path or not os.path.exists(path): return None
    try:
        img=Image.open(path).convert("RGBA")
        r=min(max_w/img.width, max_h/img.height)
        img=img.resize((int(img.width*r), int(img.height*r)), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except: return None

# ===== Widgets =====
def label(parent, text, size=12, bold=False, fg=TXT, bg=CARD_BG, anchor="w", pady=(2,0)):
    f=("Segoe UI", size, "bold" if bold else "normal")
    w=tk.Label(parent, text=text, font=f, fg=fg, bg=bg, anchor=anchor)
    w.pack(fill="x", padx=PADX_OUT, pady=pady)
    return w

def entry(parent, show=""):
    e=tk.Entry(parent, bg=ENTRY_BG, relief="solid", bd=1, font=("Segoe UI",12), show=show)
    e.pack(fill="x", padx=PADX_OUT, pady=(4,14), ipady=8)
    return e

def errlabel(parent):
    return label(parent, "", size=10, fg="#B00020", bg=CARD_BG, pady=(0,0))

# ===== App =====
class AuthApp(tk.Tk):
    def __init__(self, db_path="taste_and_sip.db", left_bg_path=None, logo_path=None,
                 on_login_success: Optional[Callable[[sqlite3.Row], None]]=None):
        super().__init__()
        self.title(APP_TITLE); self.state("zoomed"); self.configure(bg=RIGHT_BG)
        self.db=AuthDB(db_path); self.on_login_success=on_login_success
        self.left_bg_path=left_bg_path; self.logo_path=logo_path

        # Layout: left fixed, right flexible
        self.rowconfigure(0, weight=1); self.columnconfigure(1, weight=1)

        self.left=tk.Frame(self, bg=RIGHT_BG); self.left.grid(row=0,column=0,sticky="nsew")
        self.right=tk.Frame(self, bg=RIGHT_BG); self.right.grid(row=0,column=1,sticky="nsew")
        self.left.update_idletasks()

        self._build_left()
        self._build_right()
        self.show_signin()
        self.bind("<Configure>", self._redraw_left)

    # ---- Left (ภาพ + ข้อความไม่ซ้อน) ----
    def _build_left(self):
        self.left.configure(width=900)  # กินครึ่งจอโดยคร่าว ๆ
        self.canvas=tk.Canvas(self.left, bg=RIGHT_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

    def _redraw_left(self, _evt=None):
        w=self.left.winfo_width() or 900
        h=self.left.winfo_height() or self.winfo_height()
        self.canvas.delete("all")
        img=load_cover(self.left_bg_path, w, h)
        if img: 
            self._bgimg=img
            self.canvas.create_image(0,0,anchor="nw",image=self._bgimg)
        else:
            self.canvas.create_rectangle(0,0,w,h,fill=RIGHT_BG,outline="")
        # ข้อความเว้นระยะไม่ซ้อน
        self.canvas.create_text(
            32, 36, anchor="nw", fill="white",
            font=("Georgia", 34, "bold"),
            text="WELCOME TO\nTASTE AND SIP"
        )
        self.canvas.create_text(
            36, 128, anchor="nw", fill="white",
            font=("Georgia", 18, "normal"),
            text="FOOD AND DRINK!"
        )

    # ---- Right (โลโก้ + การ์ด) ----
    def _build_right(self):
        # โลโก้
        top=tk.Frame(self.right, bg=RIGHT_BG); top.pack(pady=(24,12))
        logo=load_fit(self.logo_path, 220, 220)
        if logo:
            self._logo=logo; tk.Label(top, image=self._logo, bg=RIGHT_BG).pack()
        else:
            tk.Label(top, text=APP_TITLE, font=("Segoe UI",22,"bold"), bg=RIGHT_BG, fg=ACCENT).pack()

        # การ์ด
        outer=tk.Frame(self.right, bg=RIGHT_BG); outer.pack(fill="both", expand=True)
        self.card=tk.Frame(outer, bg=CARD_BG, bd=1, relief="solid", highlightbackground=CARD_EDGE, highlightthickness=1)
        self.card.place(relx=0.5, rely=0.46, anchor="n", width=CARD_W)  # ใหญ่ขึ้น และจัดกึ่งกลาง

    def _clear_card(self):
        for w in self.card.winfo_children(): w.destroy()

    # ===== Screens =====
    def show_signin(self):
        self._clear_card()
        label(self.card, "SIGN IN", size=20, bold=True, fg=ACCENT)
        self.si_err = errlabel(self.card)
        label(self.card, "USERNAME", size=11, bold=True); self.si_user = entry(self.card)
        label(self.card, "PASSWORD", size=11, bold=True); self.si_pwd  = entry(self.card, show="•")
        tk.Button(self.card, text="SIGN IN", font=("Segoe UI",12,"bold"),
                  relief="solid", bd=1, command=self._signin)\
            .pack(fill="x", padx=PADX_OUT, pady=(6,10), ipady=8, bg="#E4E0D6", activebackground="#E4E0D6")
        # bottom links
        row=tk.Frame(self.card, bg=CARD_BG); row.pack(fill="x", padx=PADX_OUT, pady=(2,18))
        tk.Button(row, text="FORGOT PASSWORD?", relief="flat", bg=CARD_BG, command=self.show_forgot)\
            .pack(side="left")
        tk.Button(row, text="CREATE ACCOUNT", relief="flat", bg=CARD_BG, command=self.show_signup)\
            .pack(side="right")

    def show_signup(self):
        self._clear_card()
        label(self.card, "CREATE ACCOUNT", size=20, bold=True, fg=ACCENT)
        self.su_err = errlabel(self.card)

        # ฟอร์ม 2 คอลัมน์
        form=tk.Frame(self.card, bg=CARD_BG); form.pack(fill="x", padx=PADX_OUT, pady=(6,6))

        # แถว 1: USERNAME | PHONE
        r1=tk.Frame(form, bg=CARD_BG); r1.pack(fill="x")
        tk.Label(r1, text="USERNAME", bg=CARD_BG, fg=TXT, font=("Segoe UI",10,"bold")).grid(row=0,column=0,sticky="w")
        tk.Label(r1, text="PHONE",    bg=CARD_BG, fg=TXT, font=("Segoe UI",10,"bold")).grid(row=0,column=1,sticky="w", padx=(GUTTER_X,0))
        self.su_user=tk.Entry(r1, bg=ENTRY_BG, relief="solid"); self.su_user.grid(row=1,column=0,sticky="ew", pady=(4,12))
        self.su_phone=tk.Entry(r1, bg=ENTRY_BG, relief="solid"); self.su_phone.grid(row=1,column=1,sticky="ew", pady=(4,12), padx=(GUTTER_X,0))
        r1.grid_columnconfigure(0, weight=1); r1.grid_columnconfigure(1, weight=1)

        # แถว 2: EMAIL (เต็มแถว)
        label(self.card, "EMAIL", size=10, bold=True); self.su_email=entry(self.card)

        # แถว 3: PASSWORD | CONFIRM PASSWORD
        r3=tk.Frame(self.card, bg=CARD_BG); r3.pack(fill="x", padx=PADX_OUT)
        tk.Label(r3, text="PASSWORD", bg=CARD_BG, fg=TXT, font=("Segoe UI",10,"bold")).grid(row=0,column=0,sticky="w")
        tk.Label(r3, text="CONFIRM PASSWORD", bg=CARD_BG, fg=TXT, font=("Segoe UI",10,"bold")).grid(row=0,column=1,sticky="w", padx=(GUTTER_X,0))
        self.su_pwd1=tk.Entry(r3, bg=ENTRY_BG, relief="solid", show="•"); self.su_pwd1.grid(row=1,column=0,sticky="ew", pady=(4,14))
        self.su_pwd2=tk.Entry(r3, bg=ENTRY_BG, relief="solid", show="•"); self.su_pwd2.grid(row=1,column=1,sticky="ew", pady=(4,14), padx=(GUTTER_X,0))
        r3.grid_columnconfigure(0, weight=1); r3.grid_columnconfigure(1, weight=1)

        tk.Button(self.card, text="REGISTER", font=("Segoe UI",12,"bold"),
                  relief="solid", bd=1, command=self._signup)\
            .pack(fill="x", padx=PADX_OUT, pady=(6,8), ipady=8, bg="#E4E0D6", activebackground="#E4E0D6")
        tk.Button(self.card, text="BACK TO LOGIN", relief="flat", bg=CARD_BG, command=self.show_signin)\
            .pack(pady=(0,18))

    def show_forgot(self):
        self._clear_card()
        label(self.card, "FORGOT PASSWORD", size=20, bold=True, fg=ACCENT)
        self.fp_err = errlabel(self.card)

        label(self.card, "USERNAME", size=10, bold=True); self.fp_user = entry(self.card)
        label(self.card, "EMAIL OR PHONE", size=10, bold=True); self.fp_contact = entry(self.card)

        tk.Button(self.card, text="VERIFY", font=("Segoe UI",12,"bold"),
                  relief="solid", bd=1, command=self._forgot_verify)\
            .pack(fill="x", padx=PADX_OUT, pady=(4,10), ipady=8, bg="#E4E0D6", activebackground="#E4E0D6")

        self.fp_step2 = tk.Frame(self.card, bg=CARD_BG);  # ซ่อนก่อน
        self.fp_step2.pack(fill="x"); self.fp_step2.pack_forget()
        label(self.fp_step2, "NEW PASSWORD", size=10, bold=True); self.fp_pwd1 = entry(self.fp_step2, show="•")
        label(self.fp_step2, "CONFIRM NEW PASSWORD", size=10, bold=True); self.fp_pwd2 = entry(self.fp_step2, show="•")
        tk.Button(self.fp_step2, text="CHANGE PASSWORD", font=("Segoe UI",12,"bold"),
                  relief="solid", bd=1, command=self._forgot_change)\
            .pack(fill="x", padx=PADX_OUT, pady=(0,10), ipady=8, bg="#E4E0D6", activebackground="#E4E0D6")

        tk.Button(self.card, text="BACK TO LOGIN", relief="flat", bg=CARD_BG, command=self.show_signin)\
            .pack(pady=(0,18))

        self._verified_username = None

    # ===== Actions =====
    def _signin(self):
        self.si_err.config(text="")
        u=(self.si_user.get() or "").strip(); p=(self.si_pwd.get() or "").strip()
        if not u or not p: self.si_err.config(text="PLEASE ENTER USERNAME & PASSWORD."); return
        row=self.db.find_user_for_login(u,p)
        if row:
            if self.on_login_success: self.on_login_success(row)
            else: messagebox.showinfo("SUCCESS", f"WELCOME, {u}!")
        else:
            self.si_err.config(text="INVALID CREDENTIALS.")

    def _signup(self):
        self.su_err.config(text="")
        u=(self.su_user.get() or "").strip()
        ph=(self.su_phone.get() or "").strip()
        em=(self.su_email.get() or "").strip()
        p1=(self.su_pwd1.get() or "").strip()
        p2=(self.su_pwd2.get() or "").strip()

        for fn in (lambda: v_username(u), lambda: v_phone(ph), lambda: v_email(em), lambda: v_pwd(p1)):
            msg=fn()
            if msg: self.su_err.config(text=msg); return
        if p1!=p2: self.su_err.config(text="PASSWORDS DO NOT MATCH."); return
        if self.db.username_exists(u): self.su_err.config(text="USERNAME ALREADY EXISTS."); return
        try:
            self.db.create_user(u,ph,em,p1); self.su_err.config(text="ACCOUNT CREATED. PLEASE SIGN IN.")
        except sqlite3.IntegrityError:
            self.su_err.config(text="USERNAME ALREADY EXISTS.")
        except Exception as e:
            self.su_err.config(text=f"FAILED: {e}")

    def _forgot_verify(self):
        self.fp_err.config(text="")
        u=(self.fp_user.get() or "").strip()
        cp=(self.fp_contact.get() or "").strip()
        if not u or not cp: self.fp_err.config(text="FILL USERNAME & EMAIL/PHONE."); return
        row=self.db.verify_user_contact(u,cp)
        if row:
            self._verified_username=u
            self.fp_err.config(text="VERIFIED. SET NEW PASSWORD BELOW.")
            self.fp_step2.pack(fill="x")
        else:
            self.fp_err.config(text="NO MATCHING ACCOUNT.")

    def _forgot_change(self):
        if not self._verified_username:
            self.fp_err.config(text="PLEASE VERIFY FIRST."); return
        p1=(self.fp_pwd1.get() or "").strip()
        p2=(self.fp_pwd2.get() or "").strip()
        msg=v_pwd(p1)
        if msg: self.fp_err.config(text=msg); return
        if p1!=p2: self.fp_err.config(text="PASSWORDS DO NOT MATCH."); return
        try:
            self.db.change_password(self._verified_username, p1)
            self.fp_err.config(text="PASSWORD CHANGED. YOU CAN SIGN IN NOW.")
        except Exception as e:
            self.fp_err.config(text=f"FAILED: {e}")

# ===== Run demo =====
if __name__ == "__main__":
    def _demo_success(row):
        messagebox.showinfo("SIGNED IN", f"HELLO, {row['username']} (ROLE={row['role']})")
    app=AuthApp(db_path="taste_and_sip.db",
                left_bg_path=LEFT_BG_PATH,
                logo_path=LOGO_PATH,
                on_login_success=_demo_success)
    app.mainloop()
