import tkinter as tk
from tkinter import messagebox
import sqlite3, hashlib, os

APP_TITLE = "TASTE AND SIP"
DB_FILE = "taste_and_sip.db"

# image paths (แก้ path ให้ตรงเครื่องคุณ)
LEFT_BG_PATH = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\AVIBRA_1.png"
LOGO_PATH    = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\lologogo.png-removebg-preview.png"

# ---------- database ----------
def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    conn.commit(); conn.close()

def create_user(username, password):
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    try:
        c.execute("INSERT INTO users(username,password_hash) VALUES(?,?)",
                  (username, sha256(password)))
        conn.commit(); ok,msg=True,"Account created."
    except sqlite3.IntegrityError:
        ok,msg=False,"Username already exists."
    conn.close(); return ok,msg

def auth_user(username, password):
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE username=? AND password_hash=?",
              (username, sha256(password)))
    row = c.fetchone(); conn.close()
    return row is not None

# ---------- image utilities ----------
def load_photo(path):
    try:
        if os.path.exists(path):
            return tk.PhotoImage(file=path)
    except Exception:
        pass
    return None

# ---- Better cover scale with PIL ----
try:
    from PIL import Image, ImageTk
except Exception:
    Image = ImageTk = None

def pil_cover_image(path, box_w, box_h):
    if not Image or not ImageTk or not os.path.exists(path):
        return load_photo(path)
    im = Image.open(path).convert("RGB")
    if box_w <= 0 or box_h <= 0:
        return None
    img_ratio = im.width / im.height
    box_ratio = box_w / box_h
    # resize ให้ครอบเต็ม
    if img_ratio > box_ratio:
        new_h = box_h
        new_w = int(new_h * img_ratio)
    else:
        new_w = box_w
        new_h = int(new_w / img_ratio)
    im = im.resize((new_w, new_h), Image.LANCZOS)
    # crop ตรงกลาง
    left = (new_w - box_w) // 2
    top  = (new_h - box_h) // 2
    im = im.crop((left, top, left + box_w, top + box_h))
    return ImageTk.PhotoImage(im)

# ---------- GUI setup ----------
class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.state("zoomed")
        self.configure(bg="#000000")
        init_db()

        # --- LEFT area ---
        LEFT_W, LEFT_H = 720, 680
        left = tk.Frame(self, width=LEFT_W, height=LEFT_H, bg="#ececec")
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        canvas = tk.Canvas(left, width=LEFT_W, height=LEFT_H,
                           highlightthickness=0, bg="#ececec")
        canvas.pack(fill="both", expand=True)

        # วาดภาพ cover
        def paint_bg(w, h):
            img = pil_cover_image(LEFT_BG_PATH, w, h)
            canvas.delete("all")
            if img:
                canvas.create_image(w//2, h//2, image=img, tags="bg")
                canvas.image = img
            # ข้อความ
            canvas.create_text(32, 36, text="WELCOME TO \nTASTE AND SIP",
                               fill="white", font=("Georgia", 32, "bold"),
                               anchor="nw", tags="txt")
            canvas.create_text(36, 84, text="\n\nFOOD AND DRINK !",
                               fill="white", font=("Georgia", 16),
                               anchor="nw", tags="txt")
            canvas.tag_raise("txt")

        paint_bg(LEFT_W, LEFT_H)

        def on_resize(event):
            if event.width > 0 and event.height > 0:
                paint_bg(event.width, event.height)

        canvas.bind("<Configure>", on_resize)

        # --- RIGHT side ---
        right = tk.Frame(self, bg="#f8eedb")
        right.pack(side="left", fill="both", expand=True)
        # logo
        self.logo_img = None
        if os.path.exists(LOGO_PATH):
            try:
                self.logo_img = tk.PhotoImage(file=LOGO_PATH)
            except Exception:
                pass
        logo_wrap = tk.Frame(right, bg="#f5efe4"); logo_wrap.pack(pady=20)
        if self.logo_img:
            tk.Label(logo_wrap, image=self.logo_img, bg="#f8eedb").pack()
        else:
            tk.Label(logo_wrap, text="TASTE AND SIP",
                     bg="#f5efe4", font=("Segoe UI", 22, "bold")).pack()

        # login/register card
        self.card = tk.Frame(right, bg="#ffffff")
        self.card.pack(padx=40, pady=10, fill="x")
        self._make_login()

    # ---------- utilities ----------
    def clear_card(self):
        for w in self.card.winfo_children():
            w.destroy()

    def _field(self, parent, label_text, show=""):
        tk.Label(parent, text=label_text, bg="#ffffff", fg="#333",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=40)
        e = tk.Entry(parent, font=("Segoe UI", 12), relief="solid", bd=1,
                     show=show, justify="left")
        e.pack(pady=(6,16), ipady=8, padx=40, fill="x")
        return e

    # ---------- login/register ----------
    def _make_login(self):
        self.clear_card()
        tk.Label(self.card, text="Sign In", bg="#ffffff", fg="#000000",
                 font=("Segoe UI", 16, "bold")).pack(pady=(22,6))
        self.login_user = self._field(self.card, "USERNAME")
        self.login_pass = self._field(self.card, "PASSWORD", show="•")
        tk.Button(self.card, text="SIGN IN", font=("Segoe UI", 12, "bold"),
                  relief="solid", bd=1, command=self.sign_in).pack(
                      pady=6, ipady=8, padx=40, fill="x")
        tk.Button(self.card, text="CREATE ACCOUNT", font=("Segoe UI", 11),
                  relief="flat", bg="#ffffff",
                  command=self._make_register).pack(pady=(8,20))

    def _make_register(self):
        self.clear_card()
        tk.Label(self.card, text="Create Account", bg="#ffffff", fg="#1f2937",
                 font=("Segoe UI", 16, "bold")).pack(pady=(22,6))
        self.reg_user = self._field(self.card, "USERNAME")
        self.reg_pass1 = self._field(self.card, "PASSWORD", show="•")
        self.reg_pass2 = self._field(self.card, "CONFIRM PASSWORD", show="•")
        tk.Button(self.card, text="REGISTER", font=("Segoe UI", 12, "bold"),
                  relief="solid", bd=1, command=self.register).pack(
                      pady=6, ipady=8, padx=40, fill="x")
        tk.Button(self.card, text="BACK TO LOGIN", font=("Segoe UI", 11),
                  relief="flat", bg="#ffffff",
                  command=self._make_login).pack(pady=(8,20))

    # ---------- logic ----------
    def sign_in(self):
        u, p = self.login_user.get().strip(), self.login_pass.get().strip()
        if not u or not p:
            messagebox.showerror("Error", "Please enter username and password."); return
        if auth_user(u, p):
            messagebox.showinfo("Success", f"Welcome, {u}!")
        else:
            messagebox.showerror("Error", "Invalid credentials.")

    def register(self):
        u, p1, p2 = self.reg_user.get().strip(), self.reg_pass1.get().strip(), self.reg_pass2.get().strip()
        if not u or not p1 or not p2:
            messagebox.showerror("Error", "Please fill all fields."); return
        if p1 != p2:
            messagebox.showerror("Error", "Passwords do not match."); return
        ok, msg = create_user(u, p1)
        if ok:
            messagebox.showinfo("Success", msg)
            self._make_login()
        else:
            messagebox.showerror("Error", msg)

if __name__ == "__main__":
    LoginWindow().mainloop()
