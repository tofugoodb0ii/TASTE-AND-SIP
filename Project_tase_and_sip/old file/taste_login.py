import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3, hashlib

APP_TITLE = "TASTE AND SIP"
DB_FILE = "taste_and_sip.db"

# --- Helper ---
def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

# --- Database ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def create_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users(username, password_hash) VALUES (?, ?)",
                  (username, sha256(password)))
        conn.commit()
        return True, "Account created."
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    finally:
        conn.close()

def auth_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=? AND password_hash=?",
              (username, sha256(password)))
    row = c.fetchone()
    conn.close()
    return row is not None

# --- GUI ---
class LoginApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("400x300")
        init_db()
        self.current_user = None
        self.show_login()

    def show_login(self):
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Login", font=("Segoe UI", 16, "bold")).pack(pady=10)

        self.username = tk.StringVar()
        self.password = tk.StringVar()

        ttk.Label(frame, text="Username").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.username).pack(fill="x", pady=5)

        ttk.Label(frame, text="Password").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.password, show="*").pack(fill="x", pady=5)

        ttk.Button(frame, text="Sign In", command=self.sign_in).pack(pady=10)
        ttk.Button(frame, text="Create Account", command=self.show_signup).pack()

    def show_signup(self):
        for widget in self.winfo_children():
            widget.destroy()
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Create Account", font=("Segoe UI", 16, "bold")).pack(pady=10)

        self.new_username = tk.StringVar()
        self.new_password = tk.StringVar()
        self.new_password2 = tk.StringVar()

        ttk.Label(frame, text="Username").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.new_username).pack(fill="x", pady=5)

        ttk.Label(frame, text="Password").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.new_password, show="*").pack(fill="x", pady=5)

        ttk.Label(frame, text="Confirm Password").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.new_password2, show="*").pack(fill="x", pady=5)

        ttk.Button(frame, text="Register", command=self.register).pack(pady=10)
        ttk.Button(frame, text="Back to Login", command=self.back_to_login).pack()

    def back_to_login(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.show_login()

    def sign_in(self):
        u, p = self.username.get().strip(), self.password.get().strip()
        if not u or not p:
            messagebox.showerror("Error", "Please enter username and password.")
        elif auth_user(u, p):
            self.current_user = u
            messagebox.showinfo("Success", f"Welcome, {u}!")
        else:
            messagebox.showerror("Error", "Invalid credentials.")

    def register(self):
        u, p1, p2 = self.new_username.get().strip(), self.new_password.get().strip(), self.new_password2.get().strip()
        if not u or not p1:
            messagebox.showerror("Error", "Please fill all fields.")
        elif p1 != p2:
            messagebox.showerror("Error", "Passwords do not match.")
        else:
            ok, msg = create_user(u, p1)
            if ok:
                messagebox.showinfo("Success", msg)
                self.back_to_login()
            else:
                messagebox.showerror("Error", msg)

if __name__ == "__main__":
    app = LoginApp()
    app.mainloop()
