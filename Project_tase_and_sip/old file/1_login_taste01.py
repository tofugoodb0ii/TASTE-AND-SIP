import tkinter as tk
from tkinter import messagebox
import sqlite3, hashlib, os #, math 

APP_TITLE = "TASTE AND SIP"
DB_FILE = "taste_and_sip.db"

#image paths
LEFT_BG_PATH = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\AVIBRA_1.png" #background login
LOGO_PATH    = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\lologogo.png-removebg-preview.png"     #logo taste and sip

#database
def sha256(s: str) -> str: 
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
def init_db():
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL)""")
    conn.commit(); conn.close()
def create_user(username, password):
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    try:
        c.execute("INSERT INTO users(username,password_hash) VALUES(?,?)",(username,sha256(password)))
        conn.commit(); ok,msg=True,"Account created."
    except sqlite3.IntegrityError:
        ok,msg=False,"Username already exists."
    conn.close(); return ok,msg
def auth_user(username, password):
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE username=? AND password_hash=?",(username,sha256(password)))
    row=c.fetchone(); conn.close(); return row is not None

#image utilities
def load_photo(path):
    try:
        if os.path.exists(path):
            return tk.PhotoImage(file=path)  # NG/GIF
    except Exception:
        pass
    return None

def photo_cover(img, box_w, box_h):
    if not img: return None
    w, h = img.width(), img.height()
    if w == 0 or h == 0: return img
    r = max(box_w / w, box_h / h)
    if r >= 1:
        return img.zoom(max(1, round(r)))
    return img.subsample(max(1, int(1 / r)))

def load_and_cover(path, box_w, box_h):
    return photo_cover(load_photo(path), box_w, box_h)

def load_and_fit(path, max_w, max_h):
    img = load_photo(path)
    if not img: return None
    w, h = img.width(), img.height()
    k = max(1, int(max(w/max_w, h/max_h)))
    return img if k == 1 else img.subsample(k, k)

#GUI setup
class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.state("zoomed")  #maximize window
        self.configure(bg="#000000")
        init_db()

        #image left frame and texts setup
        LEFT_W, LEFT_H = 720, 680
        left = tk.Frame(self, width=LEFT_W, height=LEFT_H, bg="#ececec")
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        #setup left background image
        self.bg_img = load_and_cover(LEFT_BG_PATH, LEFT_W, LEFT_H)

        canvas = tk.Canvas(left, width=LEFT_W, height=LEFT_H,
                           highlightthickness=0, bg="#ececec")
        canvas.pack(fill="both", expand=True)

        if self.bg_img:
            canvas.create_image(LEFT_W // 2, LEFT_H // 2, image=self.bg_img)

        #texts on left background
        canvas.create_text(32, 36, text="WELCOME TO \nTASTE AND SIP",
                           fill="white", font=("Georgia", 32, "bold"), anchor="nw")
        canvas.create_text(36, 84, text="\n\nFOOD AND DRINK !",
                           fill="white", font=("Georgia", 16), anchor="nw")

        #left background overlay and logo removed background checked 
        right = tk.Frame(self, bg="#f8eedb") #bg color 
        right.pack(side="left", fill="both", expand=True) 
        self.logo_img = load_and_fit(LOGO_PATH, 220, 220)
        logo_wrap = tk.Frame(right, bg="#f5efe4"); logo_wrap.pack(pady=20)
        if self.logo_img:
            tk.Label(logo_wrap, image=self.logo_img, bg="#f8eedb").pack() #bg logo color
        else:
            tk.Label(logo_wrap, text="TASTE AND SIP", bg="#f5efe4",
                     font=("Segoe UI", 22, "bold")).pack()

        # login/register card
        self.card = tk.Frame(right, bg="#ffffff")
        self.card.pack(padx=40, pady=10, fill="x")
        self._make_login()


    #utilities
    def clear_card(self):
        for w in self.card.winfo_children(): w.destroy()

    def _field(self, parent, label_text, show=""):
        tk.Label(parent, text=label_text, bg="#ffffff", fg="#333",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=40)
        e = tk.Entry(parent, font=("Segoe UI", 12), relief="solid", bd=1,
                     show=show, justify="left")
        e.pack(pady=(6,16), ipady=8, padx=40, fill="x")
        return e

    #login and register forms on the right side
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
                  relief="flat", bg="#ffffff", command=self._make_register).pack(pady=(8,20))

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
                  relief="flat", bg="#ffffff", command=self._make_login).pack(pady=(8,20))

    #sign in and register logic checks errors
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
        if ok: messagebox.showinfo("Success", msg); self._make_login()
        else:  messagebox.showerror("Error", msg)


if __name__ == "__main__":
    LoginWindow().mainloop()