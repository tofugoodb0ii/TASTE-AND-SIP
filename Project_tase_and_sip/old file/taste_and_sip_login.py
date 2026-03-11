import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3, hashlib, os

APP_TITLE = "TASTE AND SIP"
DB_FILE = "taste_and_sip.db"

# ---- THEME (ปรับสีได้ตามต้องการ) ----
THEME = {
    "bg": "#f6f5f3",
    "fg": "#1f2937",
    "primary": "#7c4dff",
    "accent": "#ffb74d",
    "card": "#ffffff",
    "muted": "#9aa1a9",
    "danger": "#e11d48",
    "success": "#16a34a"
}

# ---- External assets (PNG/GIF เท่านั้น เพราะไม่ใช้ PIL) ----
# แนะนำให้แปลงไฟล์ของคุณเป็น .png แล้วแก้พาธสองบรรทัดนี้
LOGO_PATH = r"C:\Users\thatt\Downloads\logo.png"
QR_PATH   = r"C:\Users\thatt\Downloads\qrcode.png"

# ---- Helpers ----
def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def money(v: float) -> str:
    return f"{v:,.2f}"

def safe_load_image(path):
    try:
        if os.path.exists(path):
            return tk.PhotoImage(file=path)  # PNG/GIF เท่านั้น
    except Exception:
        pass
    return None

# ---- Database ----
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

# ---- Menu Data ----
ADDON_PRICES = {
    "Extra Cheese": 15, "Bacon": 25, "Avocado": 25, "Fried Egg": 15,
    "Extra Noodles": 20, "Shrimp": 35, "Tofu": 15, "Mushroom": 15,
    "Extra Sauce": 10, "Garlic": 10, "Chili": 10, "Nori": 10
}
PROTEIN_CHOICES = ["Chicken", "Pork", "Beef", "Shrimp", "Tofu", "Mushroom"]

FOOD_MENU = [
    ("Pad Thai", 85, "Thai"), ("Pad Kra Pao", 80, "Thai"), ("Green Curry", 95, "Thai"),
    ("Tom Yum Goong", 120, "Thai"), ("Massaman Curry", 120, "Thai"), ("Khao Man Gai", 75, "Thai"),
    ("Som Tam", 60, "Thai"), ("Pad See Ew", 85, "Thai"), ("Boat Noodles", 90, "Thai"),
    ("Khao Pad", 70, "Thai"), ("Panang Curry", 110, "Thai"), ("Larb", 85, "Thai"),
    ("Khao Soi", 110, "Thai"), ("Crab Fried Rice", 140, "Thai"), ("BBQ Pork with Rice", 85, "Thai"),
    ("Margherita Pizza", 180, "Italian"), ("Pepperoni Pizza", 200, "Italian"),
    ("Carbonara", 170, "Italian"), ("Bolognese", 170, "Italian"), ("Lasagna", 190, "Italian"),
    ("Caesar Salad", 120, "Italian"), ("Minestrone Soup", 110, "Italian"),
    ("Sushi Set", 220, "Japanese"), ("Salmon Nigiri", 190, "Japanese"),
    ("Tonkotsu Ramen", 180, "Japanese"), ("Shoyu Ramen", 160, "Japanese"),
    ("Tempura Udon", 170, "Japanese"), ("Chicken Teriyaki", 160, "Japanese"),
    ("Beef Gyudon", 170, "Japanese"),
    ("Beef Burger", 160, "American"), ("Cheeseburger", 170, "American"),
    ("Chicken Sandwich", 140, "American"), ("BBQ Ribs", 260, "American"),
    ("Mac and Cheese", 130, "American"), ("Clam Chowder", 150, "American"),
    ("Fish and Chips", 170, "British"), ("Shepherd's Pie", 180, "British"),
    ("Butter Chicken", 180, "Indian"), ("Chicken Tikka Masala", 190, "Indian"),
    ("Paneer Makhani", 170, "Indian"), ("Chana Masala", 140, "Indian"),
    ("Biryani", 180, "Indian"),
    ("Beef Pho", 170, "Vietnamese"), ("Bun Cha", 160, "Vietnamese"),
    ("Banh Mi", 120, "Vietnamese"), ("Fresh Spring Rolls", 110, "Vietnamese"),
    ("Kimchi Jjigae", 160, "Korean"), ("Bibimbap", 170, "Korean"),
    ("Bulgogi", 200, "Korean"), ("Tteokbokki", 130, "Korean"), ("Jjajangmyeon", 160, "Korean"),
    ("Chicken Shawarma", 150, "Middle Eastern"), ("Falafel Wrap", 130, "Middle Eastern"),
    ("Hummus & Pita", 110, "Middle Eastern"),
    ("Grilled Salmon", 240, "Western"), ("Roast Chicken", 180, "Western"),
    ("Steak & Fries", 290, "Western"), ("Pork Chop", 220, "Western"),
    ("Greek Salad", 130, "Mediterranean"), ("Pesto Pasta", 170, "Italian"),
    ("Ceviche", 200, "Peruvian"), ("Taco Al Pastor", 150, "Mexican"),
    ("Chicken Quesadilla", 150, "Mexican"), ("Nachos", 140, "Mexican"),
    ("Tomato Soup", 100, "Western"), ("Club Sandwich", 150, "Western"),
]

DRINK_MENU = [
    ("Americano (Hot/Iced)", 70, False),
    ("Espresso", 65, False),
    ("Latte (Hot/Iced)", 85, True),
    ("Cappuccino", 85, True),
    ("Mocha", 90, True),
    ("Caramel Macchiato", 95, True),
    ("Thai Milk Tea", 75, True),
    ("Matcha Latte", 95, True),
    ("Black Tea (Iced)", 60, False),
    ("Peach Tea (Iced)", 70, False),
    ("Lemon Tea (Iced)", 70, False),
    ("Chocolate (Hot/Iced)", 85, True),
    ("Strawberry Smoothie", 95, False),
    ("Mango Smoothie", 95, False),
    ("Orange Juice", 70, False),
    ("Lychee Soda", 75, False),
    ("Passionfruit Soda", 75, False),
    ("Honey Lemon Soda", 75, False),
    ("Iced Cocoa Oat", 95, True),
    ("Iced Hojicha Latte", 95, True),
    ("Dirty Coffee (Iced)", 100, True),
    ("Banana Milkshake", 95, True),
    ("Oreo Frappe", 110, True),
    ("Rose Lychee Tea", 85, False),
    ("Iced Yuzu Americano", 95, False),
    ("Cold Brew", 90, False),
    ("Coconut Latte", 100, True),
    ("Vietnamese Iced Coffee", 95, True)
]

MILK_TYPES = ["Cow Milk", "Soy Milk", "Oat Milk", "Almond Milk", "Coconut Milk"]
ICE_LEVELS = ["No Ice", "Less Ice", "Regular Ice", "Extra Ice"]

# ---- App ----
class TasteAndSipApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1100x700")
        self.configure(bg=THEME["bg"])
        self.resizable(True, True)
        init_db()

        # โหลดรูป (ไม่มีการ resize หากต้องการเล็กลง ใช้ subsample ได้)
        self.logo_img = safe_load_image(LOGO_PATH)
        self.qr_img   = safe_load_image(QR_PATH)

        self.current_user = None
        self.cart = []  # items: dict -> name, type, options, qty, price

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self.apply_style()

        self.container = ttk.Frame(self, padding=10)
        self.container.pack(fill="both", expand=True)

        self.frames = {}
        for F in (LoginFrame, SignupFrame, MenuFrame, CheckoutFrame, PaymentFrame, FulfillmentFrame, ConfirmationFrame):
            frame = F(self.container, self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show("LoginFrame")

    def apply_style(self):
        s = self.style
        s.configure(".", background=THEME["bg"], foreground=THEME["fg"])
        s.configure("TFrame", background=THEME["bg"])
        s.configure("Card.TFrame", background=THEME["card"], relief="flat")
        s.configure("TLabel", background=THEME["bg"], foreground=THEME["fg"], font=("Segoe UI", 10))
        s.configure("H1.TLabel", font=("Segoe UI", 20, "bold"))
        s.configure("H2.TLabel", font=("Segoe UI", 14, "bold"))
        s.configure("Muted.TLabel", foreground=THEME["muted"])
        s.configure("Accent.TLabel", foreground=THEME["primary"])
        s.configure("TButton", padding=8)
        s.map("TButton", background=[("active", THEME["accent"])])
        s.configure("Primary.TButton", background=THEME["primary"], foreground="white", padding=10)
        s.configure("Danger.TButton", background=THEME["danger"], foreground="white", padding=10)
        s.configure("Success.TButton", background=THEME["success"], foreground="white", padding=10)
        s.configure("Card.TLabelframe", background=THEME["card"])
        s.configure("Card.TLabelframe.Label", background=THEME["card"], font=("Segoe UI", 11, "bold"))

    def show(self, name):
        self.frames[name].tkraise()

    def add_to_cart(self, item):
        self.cart.append(item)
        messagebox.showinfo("Added", f"Added to cart: {item['name']}")

    def remove_selected_from_cart(self, tree):
        sel = tree.selection()
        if not sel:
            return
        idxs = sorted([int(tree.item(i, 'values')[0]) for i in sel], reverse=True)
        for idx in idxs:
            if 0 <= idx < len(self.cart):
                self.cart.pop(idx)
        self.frames["CheckoutFrame"].refresh()
        messagebox.showinfo("Removed", "Selected items removed from cart.")

    def cart_total(self):
        return sum(i["price"] for i in self.cart)

# ---- Frames ----
class Header(ttk.Frame):
    def __init__(self, parent, app, title, show_user=True):
        super().__init__(parent)
        self.app = app
        left = ttk.Frame(self, style="TFrame")
        left.pack(side="left", anchor="w")
        if app.logo_img:
            ttk.Label(left, image=app.logo_img, style="TLabel").pack(side="left", padx=(0,10))
        ttk.Label(left, text=title, style="H1.TLabel").pack(side="left")

        right = ttk.Frame(self, style="TFrame")
        right.pack(side="right", anchor="e")
        if show_user:
            user_txt = f"Signed in as: {app.current_user or '-'}"
            self.user_lbl = ttk.Label(right, text=user_txt, style="Muted.TLabel")
            self.user_lbl.pack(side="right")

    def update_user(self):
        if hasattr(self, "user_lbl"):
            self.user_lbl.config(text=f"Signed in as: {self.app.current_user}")

class LoginFrame(ttk.Frame):
    def __init__(self, parent, app: TasteAndSipApp):
        super().__init__(parent)
        self.app = app
        card = ttk.Frame(self, padding=30, style="Card.TFrame")
        card.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(card, text=APP_TITLE, style="H1.TLabel").pack(pady=(0,10))
        ttk.Label(card, text="Welcome! Please sign in.", style="Muted.TLabel").pack(pady=(0,20))

        self.username = tk.StringVar()
        self.password = tk.StringVar()

        f = ttk.Frame(card, style="Card.TFrame")
        f.pack()
        ttk.Label(f, text="Username").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(f, textvariable=self.username, width=28).grid(row=0, column=1, pady=5)
        ttk.Label(f, text="Password").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(f, textvariable=self.password, width=28, show="*").grid(row=1, column=1, pady=5)

        btns = ttk.Frame(card, style="Card.TFrame")
        btns.pack(pady=15)
        ttk.Button(btns, text="Sign In", style="Primary.TButton", command=self.sign_in).pack(side="left", padx=5)
        ttk.Button(btns, text="Create Account", command=lambda: self.app.show("SignupFrame")).pack(side="left", padx=5)

    def sign_in(self):
        u, p = self.username.get().strip(), self.password.get().strip()
        if not u or not p:
            messagebox.showerror("Error", "Please enter username and password.")
        elif auth_user(u, p):
            self.app.current_user = u
            self.app.frames["MenuFrame"].header.update_user()
            self.app.show("MenuFrame")
        else:
            messagebox.showerror("Error", "Invalid credentials.")

class SignupFrame(ttk.Frame):
    def __init__(self, parent, app: TasteAndSipApp):
        super().__init__(parent)
        self.app = app
        card = ttk.Frame(self, padding=30, style="Card.TFrame")
        card.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(card, text="Create Account", style="H1.TLabel").pack(pady=(0,10))
        ttk.Label(card, text="Please register to continue.", style="Muted.TLabel").pack(pady=(0,20))

        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.password2 = tk.StringVar()

        f = ttk.Frame(card, style="Card.TFrame"); f.pack()
        ttk.Label(f, text="Username").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(f, textvariable=self.username, width=28).grid(row=0, column=1, pady=5)
        ttk.Label(f, text="Password").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(f, textvariable=self.password, width=28, show="*").grid(row=1, column=1, pady=5)
        ttk.Label(f, text="Confirm Password").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(f, textvariable=self.password2, width=28, show="*").grid(row=2, column=1, pady=5)

        btns = ttk.Frame(card, style="Card.TFrame"); btns.pack(pady=15)
        ttk.Button(btns, text="Register", style="Primary.TButton", command=self.register).pack(side="left", padx=5)
        ttk.Button(btns, text="Back to Sign In", command=lambda: self.app.show("LoginFrame")).pack(side="left", padx=5)

    def register(self):
        u, p1, p2 = self.username.get().strip(), self.password.get().strip(), self.password2.get().strip()
        if not u or not p1:
            messagebox.showerror("Error", "Please fill all fields.")
        elif p1 != p2:
            messagebox.showerror("Error", "Passwords do not match.")
        else:
            ok, msg = create_user(u, p1)
            if ok:
                messagebox.showinfo("Success", msg)
                self.app.show("LoginFrame")
            else:
                messagebox.showerror("Error", msg)

class MenuFrame(ttk.Frame):
    def __init__(self, parent, app: TasteAndSipApp):
        super().__init__(parent)
        self.app = app
        self.header = Header(self, app, "Menu", show_user=True)
        self.header.pack(fill="x", pady=(0,10))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body); left.pack(side="left", fill="both", expand=True)
        self.nb = ttk.Notebook(left); self.nb.pack(fill="both", expand=True)

        self.food_page = ttk.Frame(self.nb, padding=10)
        self.drink_page = ttk.Frame(self.nb, padding=10)
        self.nb.add(self.food_page, text="Food")
        self.nb.add(self.drink_page, text="Drinks")

        right = ttk.Frame(body); right.pack(side="right", fill="y")

        self.build_food_list(self.food_page)
        self.build_drink_list(self.drink_page)

        self.custom_panel = ttk.LabelFrame(right, text="Customization", style="Card.TLabelframe", padding=12)
        self.custom_panel.pack(fill="x")
        self.selected_item = None
        self.build_custom_panel()

        cart_bar = ttk.Frame(right)
        cart_bar.pack(fill="x", pady=10)
        ttk.Button(cart_bar, text="View Cart / Checkout", style="Primary.TButton",
                   command=lambda: (self.app.frames["CheckoutFrame"].refresh(),
                                    self.app.show("CheckoutFrame"))).pack(fill="x")
        ttk.Button(cart_bar, text="Sign Out", command=self.sign_out).pack(fill="x", pady=(8,0))

    def sign_out(self):
        if messagebox.askyesno("Sign Out", "Sign out and return to Sign In?"):
            self.app.current_user = None
            self.app.cart = []
            self.app.show("LoginFrame")

    def build_food_list(self, parent):
        top = ttk.Frame(parent); top.pack(fill="both", expand=True)
        cols = ("name", "price", "cat")
        self.food_tree = ttk.Treeview(top, columns=cols, show="headings", height=18)
        for c, w in zip(cols, (280, 80, 120)):
            self.food_tree.heading(c, text=c.title())
            self.food_tree.column(c, width=w, anchor="w")
        self.food_tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(top, orient="vertical", command=self.food_tree.yview)
        self.food_tree.configure(yscrollcommand=sb.set); sb.pack(side="right", fill="y")
        for name, price, cat in FOOD_MENU:
            self.food_tree.insert("", "end", values=(name, money(price), cat))
        self.food_tree.bind("<<TreeviewSelect>>", self.on_select_food)

    def build_drink_list(self, parent):
        top = ttk.Frame(parent); top.pack(fill="both", expand=True)
        cols = ("name", "price", "milk")
        self.drink_tree = ttk.Treeview(top, columns=cols, show="headings", height=18)
        for c, w in zip(cols, (280, 80, 120)):
            self.drink_tree.heading(c, text=c.title())
            self.drink_tree.column(c, width=w, anchor="w")
        self.drink_tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(top, orient="vertical", command=self.drink_tree.yview)
        self.drink_tree.configure(yscrollcommand=sb.set); sb.pack(side="right", fill="y")
        for name, price, milk in DRINK_MENU:
            self.drink_tree.insert("", "end", values=(name, money(price), "Milk" if milk else "No Milk"))
        self.drink_tree.bind("<<TreeviewSelect>>", self.on_select_drink)

    def build_custom_panel(self):
        self.var_qty = tk.IntVar(value=1)
        self.var_protein = tk.StringVar(value=PROTEIN_CHOICES[0])
        self.var_spice = tk.IntVar(value=2)
        self.var_allergy = tk.StringVar(value="")
        self.addon_vars = {k: tk.BooleanVar(value=False) for k in ADDON_PRICES}

        self.var_sweet = tk.IntVar(value=100)
        self.var_ice = tk.StringVar(value=ICE_LEVELS[2])
        self.var_milk = tk.StringVar(value=MILK_TYPES[0])
        self.var_separate_ice = tk.BooleanVar(value=False)

        self.sel_label = ttk.Label(self.custom_panel, text="Select a menu item", style="H2.TLabel")
        self.sel_label.pack(anchor="w", pady=(0,8))

        qty_row = ttk.Frame(self.custom_panel, style="Card.TFrame"); qty_row.pack(fill="x", pady=5)
        ttk.Label(qty_row, text="Quantity").pack(side="left")
        ttk.Spinbox(qty_row, from_=1, to=50, width=6, textvariable=self.var_qty).pack(side="left", padx=8)

        self.food_box = ttk.LabelFrame(self.custom_panel, text="Food Options", style="Card.TLabelframe", padding=10)
        self.food_box.pack(fill="x", pady=6)
        row1 = ttk.Frame(self.food_box, style="Card.TFrame"); row1.pack(fill="x", pady=3)
        ttk.Label(row1, text="Main Protein").pack(side="left")
        ttk.Combobox(row1, values=PROTEIN_CHOICES, textvariable=self.var_protein, state="readonly", width=16).pack(side="left", padx=8)

        row2 = ttk.Frame(self.food_box, style="Card.TFrame"); row2.pack(fill="x", pady=3)
        ttk.Label(row2, text="Spice Level (0-5)").pack(side="left")
        ttk.Spinbox(row2, from_=0, to=5, width=6, textvariable=self.var_spice).pack(side="left", padx=8)

        row3 = ttk.Frame(self.food_box, style="Card.TFrame"); row3.pack(fill="x", pady=3)
        ttk.Label(row3, text="Allergies / No-go").pack(side="left")
        ttk.Entry(row3, textvariable=self.var_allergy, width=30).pack(side="left", padx=8)

        addons = ttk.LabelFrame(self.food_box, text="Add-ons (price)", style="Card.TLabelframe", padding=8)
        addons.pack(fill="x", pady=4)
        col = ttk.Frame(addons, style="Card.TFrame"); col.pack(fill="x")
        sub1 = ttk.Frame(col, style="Card.TFrame"); sub1.pack(side="left", padx=(0,10))
        sub2 = ttk.Frame(col, style="Card.TFrame"); sub2.pack(side="left", padx=(10,0))
        half = len(ADDON_PRICES)//2
        for i,(k,price) in enumerate(ADDON_PRICES.items()):
            target = sub1 if i < half else sub2
            ttk.Checkbutton(target, text=f"{k} (+{money(price)})", variable=self.addon_vars[k]).pack(anchor="w")

        self.drink_box = ttk.LabelFrame(self.custom_panel, text="Drink Options", style="Card.TLabelframe", padding=10)
        self.drink_box.pack(fill="x", pady=6)
        d1 = ttk.Frame(self.drink_box, style="Card.TFrame"); d1.pack(fill="x", pady=3)
        ttk.Label(d1, text="Sweetness (0-200%)").pack(side="left")
        ttk.Scale(d1, from_=0, to=200, orient="horizontal", variable=self.var_sweet).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Label(d1, textvariable=self.var_sweet).pack(side="left")

        d2 = ttk.Frame(self.drink_box, style="Card.TFrame"); d2.pack(fill="x", pady=3)
        ttk.Label(d2, text="Ice Level").pack(side="left")
        ttk.Combobox(d2, values=ICE_LEVELS, textvariable=self.var_ice, state="readonly", width=16).pack(side="left", padx=8)
        ttk.Checkbutton(d2, text="Separate Ice", variable=self.var_separate_ice).pack(side="left", padx=8)

        d3 = ttk.Frame(self.drink_box, style="Card.TFrame"); d3.pack(fill="x", pady=3)
        ttk.Label(d3, text="Milk Type (if applicable)").pack(side="left")
        ttk.Combobox(d3, values=MILK_TYPES, textvariable=self.var_milk, state="readonly", width=18).pack(side="left", padx=8)

        ttk.Button(self.custom_panel, text="Add to Cart", style="Success.TButton", command=self.add_to_cart).pack(fill="x", pady=(8,0))
        self.set_mode(None)

    def set_mode(self, mode):
        self.food_box.pack_forget()
        self.drink_box.pack_forget()
        if mode == "food":
            self.food_box.pack(fill="x", pady=6)
        elif mode == "drink":
            self.drink_box.pack(fill="x", pady=6)

    def on_select_food(self, _):
        sel = self.food_tree.selection()
        if not sel: return
        name, price_str, cat = self.food_tree.item(sel[0], "values")
        price = float(price_str.replace(",", ""))
        self.selected_item = {"name": name, "base_price": price, "type": "food"}
        self.sel_label.config(text=f"Selected Food: {name} ({money(price)})")
        self.set_mode("food")

    def on_select_drink(self, _):
        sel = self.drink_tree.selection()
        if not sel: return
        name, price_str, milk = self.drink_tree.item(sel[0], "values")
        price = float(price_str.replace(",", ""))
        has_milk = milk == "Milk"
        self.selected_item = {"name": name, "base_price": price, "type": "drink", "milk": has_milk}
        self.sel_label.config(text=f"Selected Drink: {name} ({money(price)})")
        self.set_mode("drink")

    def add_to_cart(self):
        if not self.selected_item:
            messagebox.showerror("Error", "Please select a menu item first.")
            return
        qty = max(1, self.var_qty.get())
        item = {"name": self.selected_item["name"], "type": self.selected_item["type"], "qty": qty, "price": 0.0}
        details = {}
        price = self.selected_item["base_price"]

        if item["type"] == "food":
            details["protein"] = self.var_protein.get()
            details["spice"] = self.var_spice.get()
            details["allergy"] = self.var_allergy.get().strip()
            details["addons"] = [k for k,v in self.addon_vars.items() if v.get()]
            price += sum(ADDON_PRICES[a] for a in details["addons"])
            if details["protein"] in ("Beef","Shrimp"): price += 20
        else:
            details["sweetness"] = int(self.var_sweet.get())
            details["ice"] = self.var_ice.get()
            details["separate_ice"] = bool(self.var_separate_ice.get())
            milk_ok = self.selected_item.get("milk", False)
            details["milk_type"] = self.var_milk.get() if milk_ok else "None"
            if details["sweetness"] > 150: price += 5
            if milk_ok and details["milk_type"] in ("Oat Milk", "Almond Milk", "Coconut Milk"):
                price += 10

        item["details"] = details
        item["unit_price"] = price
        item["price"] = price * qty
        self.app.add_to_cart(item)

class CheckoutFrame(ttk.Frame):
    def __init__(self, parent, app: TasteAndSipApp):
        super().__init__(parent)
        self.app = app
        self.header = Header(self, app, "Cart & Checkout")
        self.header.pack(fill="x", pady=(0,10))
        body = ttk.Frame(self); body.pack(fill="both", expand=True)

        left = ttk.Frame(body); left.pack(side="left", fill="both", expand=True)
        right = ttk.Frame(body); right.pack(side="right", fill="y")

        cols = ("idx", "name", "qty", "options", "unit", "total")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=20)
        for c, w in zip(cols, (40, 240, 60, 380, 80, 80)):
            self.tree.heading(c, text=c.title())
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set); sb.pack(side="right", fill="y")

        btns = ttk.Frame(right); btns.pack(fill="x", pady=(0,8))
        ttk.Button(btns, text="Remove Selected", style="Danger.TButton",
                   command=lambda: self.app.remove_selected_from_cart(self.tree)).pack(fill="x", pady=(0,6))
        ttk.Button(btns, text="Back to Menu", command=lambda: self.app.show("MenuFrame")).pack(fill="x")
        ttk.Separator(right, orient="horizontal").pack(fill="x", pady=10)
        self.total_lbl = ttk.Label(right, text="Total: 0.00", style="H2.TLabel")
        self.total_lbl.pack(anchor="e", pady=6)
        ttk.Button(right, text="Proceed to Payment", style="Primary.TButton",
                   command=self.go_payment).pack(fill="x")

    def format_options(self, d):
        if "protein" in d:
            addons = ", ".join(d.get("addons", [])) or "-"
            return f"Protein: {d['protein']} | Spice: {d['spice']}/5 | No/Allergy: {d.get('allergy','-')} | Add-ons: {addons}"
        else:
            return f"Sweet: {d['sweetness']}% | Ice: {d['ice']}{' (separate)' if d.get('separate_ice') else ''} | Milk: {d.get('milk_type','-')}"

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for idx, item in enumerate(self.app.cart):
            self.tree.insert("", "end", values=(
                idx,
                item["name"] + (" [Drink]" if item["type"]=="drink" else " [Food]"),
                item["qty"],
                self.format_options(item["details"]),
                money(item["unit_price"]),
                money(item["price"])
            ))
        self.total_lbl.config(text=f"Total: {money(self.app.cart_total())}")

    def go_payment(self):
        if not self.app.cart:
            messagebox.showerror("Empty", "Your cart is empty.")
            return
        self.app.show("PaymentFrame")

class PaymentFrame(ttk.Frame):
    def __init__(self, parent, app: TasteAndSipApp):
        super().__init__(parent)
        self.app = app
        self.header = Header(self, app, "Payment (Scan QR)")
        self.header.pack(fill="x", pady=(0,10))

        card = ttk.Frame(self, padding=20, style="Card.TFrame"); card.pack(pady=10)
        ttk.Label(card, text="Please scan the QR code below to complete payment.", style="H2.TLabel").pack(pady=(0,10))
        if app.qr_img:
            ttk.Label(card, image=app.qr_img).pack(pady=6)
        else:
            ttk.Label(card, text="[QR Image Not Found - please set QR_PATH]", style="Accent.TLabel").pack(pady=6)

        ttk.Button(card, text="I have paid", style="Success.TButton", command=self.next_step).pack(side="left", padx=6)
        ttk.Button(card, text="Back to Cart", command=lambda: app.show("CheckoutFrame")).pack(side="left", padx=6)

    def next_step(self):
        self.app.show("FulfillmentFrame")

class FulfillmentFrame(ttk.Frame):
    def __init__(self, parent, app: TasteAndSipApp):
        super().__init__(parent)
        self.app = app
        self.header = Header(self, app, "Pickup or Delivery?")
        self.header.pack(fill="x", pady=(0,10))

        body = ttk.Frame(self, padding=12, style="Card.TFrame"); body.pack(pady=10)

        self.method = tk.StringVar(value="Pickup")
        ttk.Radiobutton(body, text="Pickup at Store", variable=self.method, value="Pickup").pack(anchor="w")
        ttk.Radiobutton(body, text="Delivery", variable=self.method, value="Delivery").pack(anchor="w")

        self.form = ttk.LabelFrame(body, text="Delivery Details", style="Card.TLabelframe", padding=10)
        self.form.pack(fill="x", pady=8)

        self.var_name = tk.StringVar()
        self.var_phone = tk.StringVar()
        self.var_addr = tk.StringVar()

        r1 = ttk.Frame(self.form, style="Card.TFrame"); r1.pack(fill="x", pady=3)
        ttk.Label(r1, text="Full Name").pack(side="left"); ttk.Entry(r1, textvariable=self.var_name, width=40).pack(side="left", padx=8)
        r2 = ttk.Frame(self.form, style="Card.TFrame"); r2.pack(fill="x", pady=3)
        ttk.Label(r2, text="Phone").pack(side="left"); ttk.Entry(r2, textvariable=self.var_phone, width=30).pack(side="left", padx=8)
        r3 = ttk.Frame(self.form, style="Card.TFrame"); r3.pack(fill="x", pady=3)
        ttk.Label(r3, text="Address").pack(side="left"); ttk.Entry(r3, textvariable=self.var_addr, width=60).pack(side="left", padx=8)

        ttk.Label(body, text="If Pickup is selected, delivery fields can be left blank.", style="Muted.TLabel").pack(anchor="w", pady=(0,6))

        btns = ttk.Frame(body, style="Card.TFrame"); btns.pack(fill="x", pady=6)
        ttk.Button(btns, text="Confirm Order", style="Primary.TButton", command=self.confirm).pack(side="left", padx=6)
        ttk.Button(btns, text="Back to Payment", command=lambda: app.show("PaymentFrame")).pack(side="left", padx=6)

    def confirm(self):
        method = self.method.get()
        if method == "Delivery":
            if not (self.var_name.get().strip() and self.var_phone.get().strip() and self.var_addr.get().strip()):
                messagebox.showerror("Missing", "Please fill Delivery details.")
                return
            message = (f"Order confirmed for delivery.\n"
                       f"Recipient: {self.var_name.get()}\n"
                       f"Phone: {self.var_phone.get()}\n"
                       f"Address: {self.var_addr.get()}\n"
                       f"Total: {money(self.app.cart_total())}")
        else:
            message = (f"Order confirmed for Pickup.\n"
                       f"Your order will be ready soon.\n"
                       f"Total: {money(self.app.cart_total())}\n"
                       f"Status: Completed ✅")

        self.app.frames["ConfirmationFrame"].set_message(message)
        self.app.cart = []
        self.app.show("ConfirmationFrame")

class ConfirmationFrame(ttk.Frame):
    def __init__(self, parent, app: TasteAndSipApp):
        super().__init__(parent)
        self.app = app
        self.header = Header(self, app, "Order Status")
        self.header.pack(fill="x", pady=(0,10))
        card = ttk.Frame(self, padding=24, style="Card.TFrame"); card.pack(pady=20)
        self.msg_lbl = ttk.Label(card, text="", style="H2.TLabel", justify="left")
        self.msg_lbl.pack()
        ttk.Button(card, text="Back to Menu", style="Success.TButton",
                   command=lambda: app.show("MenuFrame")).pack(pady=(12,0))

    def set_message(self, msg):
        self.msg_lbl.config(text=msg)

if __name__ == "__main__":
    app = TasteAndSipApp()
    app.mainloop()