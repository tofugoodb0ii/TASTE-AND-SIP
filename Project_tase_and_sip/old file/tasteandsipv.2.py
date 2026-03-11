import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3, hashlib, os, re, json, datetime

APP_TITLE = "TASTE AND SIP"
DB_FILE = "taste_and_sip.db"

# ---------------- Image paths (ใส่เอง) ----------------
LOGO_PATH = r"C:\path\to\logo.png"     # TODO: image path (โลโก้มุมซ้าย)
FOOD_ICON_PATHS = {                     # ไอคอนปุ่มหมวดอาหาร
    "Thai":     r"C:\path\to\thai.png",      # TODO
    "Italian":  r"C:\path\to\italian.png",   # TODO
    "Korean":   r"C:\path\to\korean.png",    # TODO
    "Chinese":  r"C:\path\to\chinese.png",   # TODO
    "Japanese": r"C:\path\to\japanese.png",  # TODO
}
DRINK_ICON_PATHS = {                    # ไอคอนปุ่มหมวดเครื่องดื่ม
    "Coffee":   r"C:\path\to\coffee.png",    # TODO
    "Matcha":   r"C:\path\to\matcha.png",    # TODO
    "Thai Tea": r"C:\path\to\thaitea.png",   # TODO
    "Soda":     r"C:\path\to\soda.png",      # TODO
}

# ---------------- Security helpers ----------------
def sha256(s:str)->str: return hashlib.sha256(s.encode("utf-8")).hexdigest()
PW_RE_LOWER = re.compile(r"[a-z]")
PW_RE_UPPER = re.compile(r"[A-Z]")
PW_RE_DIGIT = re.compile(r"[0-9]")
PW_RE_ONLY_EN = re.compile(r"^[A-Za-z0-9]+$")

def validate_password(pw:str):
    if len(pw)<9: return False,"รหัสผ่านต้องยาวอย่างน้อย 9 ตัว"
    if not PW_RE_ONLY_EN.match(pw): return False,"ใช้เฉพาะ A–Z, a–z, 0–9 (ห้ามสัญลักษณ์)"
    if not PW_RE_LOWER.search(pw): return False,"ต้องมีตัวพิมพ์เล็กอย่างน้อย 1 ตัว"
    if not PW_RE_UPPER.search(pw): return False,"ต้องมีตัวพิมพ์ใหญ่อย่างน้อย 1 ตัว"
    if not PW_RE_DIGIT.search(pw): return False,"ต้องมีตัวเลขอย่างน้อย 1 ตัว"
    return True,""

# ---------------- DB ----------------
def db(): return sqlite3.connect(DB_FILE)

def init_db():
    conn=db(); c=conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        kind TEXT CHECK(kind IN ('food','drink')) NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        image_path TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS carts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        status TEXT DEFAULT 'active',
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS cart_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cart_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        qty INTEGER NOT NULL,
        opts_json TEXT DEFAULT '{}',
        FOREIGN KEY(cart_id) REFERENCES carts(id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        total REAL NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS order_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        qty INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        opts_json TEXT DEFAULT '{}',
        FOREIGN KEY(order_id) REFERENCES orders(id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    )""")
    # seed เมนูตัวอย่างให้ครบหมวดตามไฟล์
    c.execute("SELECT COUNT(*) FROM products"); n=c.fetchone()[0]
    if n==0:
        seed = [
            # FOOD
            ("ผัดไทย", "food","Thai",79.0, r"C:\img\padthai.png"),
            ("ต้มยำกุ้ง", "food","Thai",95.0, r"C:\img\tomyum.png"),
            ("Margherita Pizza", "food","Italian",189.0, r"C:\img\pizza.png"),
            ("Carbonara", "food","Italian",159.0, r"C:\img\carbonara.png"),
            ("Bibimbap", "food","Korean",129.0, r"C:\img\bibimbap.png"),
            ("Kimchi Stew", "food","Korean",109.0, r"C:\img\kimchi.png"),
            ("Mapo Tofu", "food","Chinese",119.0, r"C:\img\mapotofu.png"),
            ("Kung Pao Chicken", "food","Chinese",129.0, r"C:\img\kungpao.png"),
            ("Sushi Set", "food","Japanese",199.0, r"C:\img\sushi.png"),
            ("Ramen", "food","Japanese",149.0, r"C:\img\ramen.png"),
            # DRINK
            ("Iced Americano", "drink","Coffee",60.0, r"C:\img\americano.png"),
            ("Latte", "drink","Coffee",70.0, r"C:\img\latte.png"),
            ("Matcha Latte", "drink","Matcha",75.0, r"C:\img\matcha_latte.png"),
            ("Matcha Frappe", "drink","Matcha",85.0, r"C:\img\matcha_frappe.png"),
            ("Thai Milk Tea", "drink","Thai Tea",55.0, r"C:\img\thaitea.png"),
            ("Thai Tea Frappe", "drink","Thai Tea",65.0, r"C:\img\thaitea_frappe.png"),
            ("Lemon Soda", "drink","Soda",45.0, r"C:\img\lemon_soda.png"),
            ("Blue Curacao Soda", "drink","Soda",55.0, r"C:\img\blue_soda.png"),
        ]
        for name,kind,cat,price,img in seed:
            c.execute("INSERT INTO products(name,kind,category,price,image_path) VALUES(?,?,?,?,?)",
                      (name,kind,cat,price,img))
    conn.commit(); conn.close()

def create_user(email, username, password):
    ok,msg=validate_password(password)
    if not ok: return False,msg
    conn=db(); c=conn.cursor()
    try:
        c.execute("INSERT INTO users(email,username,password_hash) VALUES(?,?,?)",
                  (email,username,sha256(password)))
        conn.commit(); conn.close(); return True,"สมัครสำเร็จ"
    except sqlite3.IntegrityError as e:
        conn.close()
        if "email" in str(e): return False,"อีเมลถูกใช้แล้ว"
        if "username" in str(e): return False,"ชื่อผู้ใช้ถูกใช้แล้ว"
        return False,"สมัครไม่สำเร็จ"

def auth_user(username,password):
    conn=db(); c=conn.cursor()
    c.execute("SELECT id FROM users WHERE username=? AND password_hash=?",
              (username,sha256(password)))
    row=c.fetchone(); conn.close()
    return row[0] if row else None

def get_or_create_active_cart(user_id):
    conn=db(); c=conn.cursor()
    c.execute("SELECT id FROM carts WHERE user_id=? AND status='active'", (user_id,))
    row=c.fetchone()
    if row: cid=row[0]
    else:
        c.execute("INSERT INTO carts(user_id,status,created_at) VALUES(?,?,?)",
                  (user_id,'active', datetime.datetime.now().isoformat()))
        conn.commit(); cid=c.lastrowid
    conn.close(); return cid

def list_categories(kind):
    conn=db(); c=conn.cursor()
    c.execute("SELECT DISTINCT category FROM products WHERE kind=? ORDER BY category",(kind,))
    rows=[r[0] for r in c.fetchall()]; conn.close(); return rows

def list_products(kind, category):
    conn=db(); c=conn.cursor()
    c.execute("""SELECT id,name,price,image_path FROM products
                 WHERE kind=? AND category=? ORDER BY name""",(kind,category))
    rows=c.fetchall(); conn.close(); return rows

def add_to_cart(user_id, product_id, qty, opts=None):
    cid=get_or_create_active_cart(user_id)
    conn=db(); c=conn.cursor()
    c.execute("INSERT INTO cart_items(cart_id,product_id,qty,opts_json) VALUES(?,?,?,?)",
              (cid,product_id,qty,json.dumps(opts or {}, ensure_ascii=False)))
    conn.commit(); conn.close()

def read_cart(user_id):
    conn=db(); c=conn.cursor()
    c.execute("""SELECT ci.id,p.name,p.price,ci.qty
                 FROM cart_items ci
                 JOIN carts ca ON ca.id=ci.cart_id
                 JOIN products p ON p.id=ci.product_id
                 WHERE ca.user_id=? AND ca.status='active'
                 ORDER BY ci.id DESC""",(user_id,))
    rows=c.fetchall(); conn.close(); return rows

def cart_total(user_id):
    return sum(price*qty for _id,name,price,qty in read_cart(user_id))

def remove_cart_item(item_id):
    conn=db(); c=conn.cursor()
    c.execute("DELETE FROM cart_items WHERE id=?", (item_id,))
    conn.commit(); conn.close()

def checkout(user_id):
    items=read_cart(user_id)
    if not items: return False,"ตะกร้าว่าง"
    total=sum(price*qty for _id,name,price,qty in items)
    conn=db(); c=conn.cursor()
    c.execute("INSERT INTO orders(user_id,total,created_at) VALUES(?,?,?)",
              (user_id,total,datetime.datetime.now().isoformat()))
    order_id=c.lastrowid
    # เก็บ order_items
    c.execute("""SELECT ci.product_id, ci.qty, p.price, ca.id
                 FROM cart_items ci
                 JOIN carts ca ON ca.id=ci.cart_id
                 JOIN products p ON p.id=ci.product_id
                 WHERE ca.user_id=? AND ca.status='active'""",(user_id,))
    for pid,qty,price,_ in c.fetchall():
        c.execute("INSERT INTO order_items(order_id,product_id,qty,unit_price) VALUES(?,?,?,?)",
                  (order_id,pid,qty,price))
    # ปิด cart
    c.execute("UPDATE carts SET status='checkedout' WHERE user_id=? AND status='active'",(user_id,))
    conn.commit(); conn.close()
    return True, f"สั่งซื้อสำเร็จ #{order_id}"

# ---------------- Image helpers ----------------
def load_img(path, max_w=96, max_h=96):
    try:
        if path and os.path.exists(path):
            img=tk.PhotoImage(file=path)
            w,h=img.width(), img.height()
            k=max(1,int(max(w/max_w, h/max_h)))
            return img if k==1 else img.subsample(k,k)
    except Exception:
        pass
    return None

# ---------------- GUI ----------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.state("zoomed")
        init_db()

        self.user_id=None  # ยังไม่ล็อกอิน
        self.header=tk.Frame(self,bg="#ffffff"); self.header.pack(fill="x")
        self.content=tk.Frame(self,bg="#f6f6f6"); self.content.pack(fill="both",expand=True)

        self._build_header()
        self.show_food_categories()  # เปิดมาที่ FOOD ตามเมนูหลักในไฟล์

    def _build_header(self):
        left=tk.Frame(self.header,bg="#ffffff"); left.pack(side="left",padx=10,pady=6)
        right=tk.Frame(self.header,bg="#ffffff"); right.pack(side="right",padx=10,pady=6)

        # logo + title
        self.logo_img=load_img(LOGO_PATH, 120, 120)
        if self.logo_img: tk.Label(left,image=self.logo_img,bg="#ffffff").pack(side="left")
        tk.Label(left,text="TASTE AND SIP",font=("Segoe UI",16,"bold"),bg="#ffffff").pack(side="left",padx=8)

        # top menu: FOOD / DRINK / PAYMENT (ตามไฟล์)
        ttk.Button(right,text="FOOD",command=self.show_food_categories).pack(side="left",padx=4)
        ttk.Button(right,text="DRINK",command=self.show_drink_categories).pack(side="left",padx=4)
        ttk.Button(right,text="PAYMENT",command=self.show_payment).pack(side="left",padx=4)

        # auth area
        self.auth_area=tk.Frame(right,bg="#ffffff"); self.auth_area.pack(side="left",padx=10)
        self._render_auth_area()

    def _render_auth_area(self):
        for w in self.auth_area.winfo_children(): w.destroy()
        if self.user_id:
            ttk.Button(self.auth_area,text="Logout",command=self.logout).pack(side="left")
        else:
            ttk.Button(self.auth_area,text="LOG IN",command=self.show_login).pack(side="left")
            ttk.Button(self.auth_area,text="REGISTER",command=self.show_register).pack(side="left",padx=4)

    def clear_content(self):
        for w in self.content.winfo_children(): w.destroy()

    # -------- Login/Register ----------
    def show_login(self):
        self.clear_content()
        frm=tk.Frame(self.content,bg="#ffffff"); frm.pack(pady=20)
        tk.Label(frm,text="LOG IN",font=("Segoe UI",16,"bold"),bg="#ffffff").grid(row=0,column=0,columnspan=2,pady=10)
        tk.Label(frm,text="USERNAME",bg="#ffffff").grid(row=1,column=0,sticky="e",padx=6,pady=6)
        tk.Label(frm,text="PASSWORD",bg="#ffffff").grid(row=2,column=0,sticky="e",padx=6,pady=6)
        e_user=tk.Entry(frm); e_pw=tk.Entry(frm,show="•")
        e_user.grid(row=1,column=1,padx=6,pady=6); e_pw.grid(row=2,column=1,padx=6,pady=6)
        def do_login():
            u,p=e_user.get().strip(), e_pw.get().strip()
            if not u or not p: messagebox.showerror("Error","กรอกข้อมูลให้ครบ"); return
            uid=auth_user(u,p)
            if uid: self.user_id=uid; messagebox.showinfo("สำเร็จ","เข้าสู่ระบบแล้ว"); self._render_auth_area(); self.show_food_categories()
            else: messagebox.showerror("Error","ชื่อผู้ใช้/รหัสผ่านไม่ถูกต้อง")
        ttk.Button(frm,text="LOG IN",command=do_login).grid(row=3,column=0,columnspan=2,pady=10)

    def show_register(self):
        self.clear_content()
        frm=tk.Frame(self.content,bg="#ffffff"); frm.pack(pady=20)
        tk.Label(frm,text="REGISTER",font=("Segoe UI",16,"bold"),bg="#ffffff").grid(row=0,column=0,columnspan=2,pady=10)
        labels=["EMAIL","USERNAME","PASSWORD","CONFIRM PASSWORD"]
        entries=[tk.Entry(frm) for _ in labels]
        for i,l in enumerate(labels):
            tk.Label(frm,text=l,bg="#ffffff").grid(row=i+1,column=0,sticky="e",padx=6,pady=6)
            entries[i].grid(row=i+1,column=1,padx=6,pady=6)
        entries[2].configure(show="•"); entries[3].configure(show="•")
        def do_register():
            email,username,p1,p2=(e.get().strip() for e in entries)
            if not email or not username or not p1 or not p2:
                messagebox.showerror("Error","กรอกข้อมูลให้ครบ"); return
            if p1!=p2: messagebox.showerror("Error","รหัสไม่ตรงกัน"); return
            ok,msg=create_user(email,username,p1)
            if ok: messagebox.showinfo("สำเร็จ",msg); self.show_login()
            else: messagebox.showerror("Error",msg)
        ttk.Button(frm,text="REGISTER",command=do_register).grid(row=5,column=0,columnspan=2,pady=10)

    def logout(self):
        self.user_id=None
        self._render_auth_area()
        messagebox.showinfo("ออกจากระบบ","เสร็จสิ้น")

    # -------- FOOD ----------
    def show_food_categories(self):
        self.clear_content()
        tk.Label(self.content,text="MENU - FOOD",font=("Segoe UI",16,"bold"),bg="#f6f6f6").pack(pady=10)

        # หมวดตามไฟล์: Thai/Italian/Korean/Chinese/Japanese
        want=["Thai","Italian","Korean","Chinese","Japanese"]
        grid=tk.Frame(self.content,bg="#f6f6f6"); grid.pack(pady=10)
        for i,name in enumerate(want):
            f=tk.Frame(grid,bg="#ffffff",bd=1,relief="solid"); f.grid(row=i//3,column=i%3,padx=10,pady=10,sticky="nsew")
            img=load_img(FOOD_ICON_PATHS.get(name),128,128)
            if img: tk.Label(f,image=img,bg="#ffffff").pack(padx=10,pady=6)
            tk.Label(f,text=f"{name} FOOD",bg="#ffffff",font=("Segoe UI",12,"bold")).pack()
            ttk.Button(f,text="เปิดเมนู",command=lambda n=name: self.show_food_list(n)).pack(pady=8)
            f.image_ref=img

    def show_food_list(self, category):
        self.clear_content()
        tk.Label(self.content,text=f"MENU - {category} FOOD",font=("Segoe UI",16,"bold"),bg="#f6f6f6").pack(pady=10)
        rows=list_products("food",category)
        if not rows:
            tk.Label(self.content,text="ยังไม่มีเมนู",bg="#f6f6f6").pack(); return
        for pid,name,price,imgp in rows:
            card=tk.Frame(self.content,bg="#ffffff",bd=1,relief="solid"); card.pack(padx=10,pady=8,fill="x")
            img=load_img(imgp,96,96)
            if img: tk.Label(card,image=img,bg="#ffffff").pack(side="left",padx=10,pady=6)
            info=tk.Frame(card,bg="#ffffff"); info.pack(side="left",fill="x",expand=True)
            tk.Label(info,text=name,bg="#ffffff",font=("Segoe UI",12,"bold")).pack(anchor="w")
            tk.Label(info,text=f"{price:.2f} ฿",bg="#ffffff").pack(anchor="w")
            def add(pid=pid):
                if not self.user_id:
                    messagebox.showwarning("ต้องล็อกอิน","กรุณาล็อกอินก่อนใส่ตะกร้า"); return
                add_to_cart(self.user_id,pid,1,opts={"from":"food"})
                messagebox.showinfo("เพิ่มลงตะกร้า","เรียบร้อย")
            ttk.Button(card,text="ใส่ตะกร้า",command=add).pack(side="right",padx=10,pady=10)
            card.image_ref=img

    # -------- DRINK ----------
    def show_drink_categories(self):
        self.clear_content()
        tk.Label(self.content,text="MENU - DRINK",font=("Segoe UI",16,"bold"),bg="#f6f6f6").pack(pady=10)

        # หมวดในไฟล์: Coffee / Matcha / Thai Tea / Soda
        want=["Coffee","Matcha","Thai Tea","Soda"]
        grid=tk.Frame(self.content,bg="#f6f6f6"); grid.pack(pady=10)
        for i,name in enumerate(want):
            f=tk.Frame(grid,bg="#ffffff",bd=1,relief="solid"); f.grid(row=i//3,column=i%3,padx=10,pady=10,sticky="nsew")
            img=load_img(DRINK_ICON_PATHS.get(name),128,128)
            if img: tk.Label(f,image=img,bg="#ffffff").pack(padx=10,pady=6)
            tk.Label(f,text=name.upper(),bg="#ffffff",font=("Segoe UI",12,"bold")).pack()
            ttk.Button(f,text="เปิดเมนู",command=lambda n=name: self.show_drink_list(n)).pack(pady=8)
            f.image_ref=img

    def show_drink_list(self, category):
        self.clear_content()
        tk.Label(self.content,text=f"MENU - {category}",font=("Segoe UI",16,"bold"),bg="#f6f6f6").pack(pady=10)
        rows=list_products("drink",category)
        if not rows:
            tk.Label(self.content,text="ยังไม่มีเมนู",bg="#f6f6f6").pack(); return
        for pid,name,price,imgp in rows:
            card=tk.Frame(self.content,bg="#ffffff",bd=1,relief="solid"); card.pack(padx=10,pady=8,fill="x")
            img=load_img(imgp,96,96)
            if img: tk.Label(card,image=img,bg="#ffffff").pack(side="left",padx=10,pady=6)
            info=tk.Frame(card,bg="#ffffff"); info.pack(side="left",fill="x",expand=True)
            tk.Label(info,text=name,bg="#ffffff",font=("Segoe UI",12,"bold")).pack(anchor="w")
            tk.Label(info,text=f"{price:.2f} ฿",bg="#ffffff").pack(anchor="w")
            def add(pid=pid):
                if not self.user_id:
                    messagebox.showwarning("ต้องล็อกอิน","กรุณาล็อกอินก่อนใส่ตะกร้า"); return
                add_to_cart(self.user_id,pid,1,opts={"from":"drink"})
                messagebox.showinfo("เพิ่มลงตะกร้า","เรียบร้อย")
            ttk.Button(card,text="ใส่ตะกร้า",command=add).pack(side="right",padx=10,pady=10)
            card.image_ref=img

    # -------- PAYMENT (Cart + Checkout) ----------
    def show_payment(self):
        self.clear_content()
        tk.Label(self.content,text="PAYMENT",font=("Segoe UI",16,"bold"),bg="#f6f6f6").pack(pady=10)
        if not self.user_id:
            tk.Label(self.content,text="กรุณาล็อกอินก่อนชำระเงิน",bg="#f6f6f6").pack()
            return
        items=read_cart(self.user_id)
        if not items:
            tk.Label(self.content,text="ตะกร้าของคุณว่างเปล่า",bg="#f6f6f6").pack(); return

        tree=ttk.Treeview(self.content,columns=("name","price","qty","sum"),show="headings",height=10)
        for col,hd in zip(("name","price","qty","sum"),("สินค้า","ราคา","จำนวน","รวม")):
            tree.heading(col,text=hd); tree.column(col,anchor="center",stretch=True,width=150)
        tree.pack(padx=10,pady=10,fill="x")
        sum_total=0.0
        for item_id,name,price,qty in items:
            s=price*qty; sum_total+=s
            tree.insert("", "end", iid=str(item_id), values=(name,f"{price:.2f}",qty,f"{s:.2f}"))

        def remove_selected():
            sel=tree.selection()
            if not sel: return
            for iid in sel:
                remove_cart_item(int(iid))
                tree.delete(iid)
            self.show_payment()

        btns=tk.Frame(self.content,bg="#f6f6f6"); btns.pack(pady=6)
        ttk.Button(btns,text="ลบที่เลือก",command=remove_selected).pack(side="left",padx=6)

        tk.Label(self.content,text=f"ยอดรวม: {sum_total:.2f} ฿",bg="#f6f6f6",font=("Segoe UI",12,"bold")).pack(pady=6)
        def do_checkout():
            ok,msg=checkout(self.user_id)
            if ok: messagebox.showinfo("ชำระเงิน",msg); self.show_payment()
            else: messagebox.showerror("ชำระเงิน",msg)
        ttk.Button(self.content,text="ยืนยันชำระเงิน",command=do_checkout).pack(pady=8)

if __name__=="__main__":
    App().mainloop()
