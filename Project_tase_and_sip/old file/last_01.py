import os, sys, json, sqlite3, hashlib, shutil, re
from datetime import datetime as dt, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from typing import Optional, Callable, List, Dict
from PIL import Image, ImageTk
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.units import mm
import customtkinter as ctk

APP_TITLE = "TASTE AND SIP"
DB_FILE   = "taste_and_sip.db"
VAT_RATE  = 0.07

# ----- Login screen images (ปรับ path ให้ตรงเครื่อง) -----
LEFT_BG_PATH = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\AVIBRA_1.png"
LOGO_PATH    = r"C:\Users\thatt\OneDrive\Desktop\python\Project_tase_and_sip\image\lologogo.png-removebg-preview.png"

# ----- Assets -----
ASSETS_DIR          = "assets"
IMG_DIR             = os.path.join(ASSETS_DIR, "images")
IMG_PRODUCTS_DIR    = os.path.join(IMG_DIR, "products")
IMG_QR_PATH         = r"C:\Users\thatt\Downloads\qrcode.jpg"   # ใส่ไฟล์ QR ร้าน
IMG_AVATARS_DIR     = os.path.join(ASSETS_DIR, "avatars")
REPORTS_DIR         = "reports"

def ensure_dirs():
    for p in [ASSETS_DIR, IMG_DIR, IMG_PRODUCTS_DIR, IMG_AVATARS_DIR, REPORTS_DIR]:
        os.makedirs(p, exist_ok=True)

def sha256(s: str) -> str: return hashlib.sha256(s.encode("utf-8")).hexdigest()
def now_ts(): return dt.now().strftime("%Y-%m-%d %H:%M:%S")

def load_photo(path, size):
    if not path or not os.path.exists(path): return None
    try:
        img = Image.open(path).convert("RGBA").resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

# ======================= DB =======================
class DB:
    def __init__(self, path=DB_FILE):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._schema(); self._seed(); self._migrate()

    def _schema(self):
        c = self.conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT, phone TEXT, email TEXT, birthdate TEXT, gender TEXT,
            avatar TEXT, role TEXT DEFAULT 'customer')""")
        c.execute("""CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, category_id INTEGER, base_price REAL, image TEXT, is_active INTEGER DEFAULT 1)""")
        c.execute("""CREATE TABLE IF NOT EXISTS promotions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE, type TEXT, value REAL,
            min_spend REAL DEFAULT 0, start_at TEXT, end_at TEXT,
            applies_to_product_id INTEGER, is_active INTEGER DEFAULT 1)""")
        c.execute("""CREATE TABLE IF NOT EXISTS order_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER, product_id INTEGER, qty INTEGER, unit_price REAL, options_json TEXT, note TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, order_datetime TEXT,
            channel TEXT, pickup_time TEXT,
            subtotal REAL, discount REAL, total REAL,
            payment_method TEXT, status TEXT,
            vat REAL DEFAULT 0)""")
        c.execute("""CREATE TABLE IF NOT EXISTS payments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER, method TEXT, amount REAL, paid_at TEXT, ref TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS inventory_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, unit TEXT, qty_on_hand REAL DEFAULT 0,
            reorder_level REAL DEFAULT 0, cost_per_unit REAL DEFAULT 0)""")
        c.execute("""CREATE TABLE IF NOT EXISTS bom_links(
            product_id INTEGER, inventory_item_id INTEGER, qty_per_unit REAL,
            PRIMARY KEY(product_id,inventory_item_id))""")
        c.execute("""CREATE TABLE IF NOT EXISTS stock_movements(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inventory_item_id INTEGER, change_qty REAL, reason TEXT, ref_id INTEGER, created_at TEXT)""")
        self.conn.commit()

    def _migrate(self):
        pass

    def _seed(self):
        c = self.conn.cursor()
        if not c.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
            c.execute("INSERT INTO users(username,password_hash,name,role) VALUES(?,?,?,?)",
                      ("admin", sha256("admin123"), "Administrator", "admin"))
        if c.execute("SELECT COUNT(*) n FROM categories").fetchone()['n'] == 0:
            c.executemany("INSERT INTO categories(name) VALUES(?)", [("FOOD",),("DRINK",),("DESSERT",)])
        if c.execute("SELECT COUNT(*) n FROM products").fetchone()['n'] == 0:
            cats = {r['name']: r['id'] for r in c.execute("SELECT * FROM categories")}
            sample = [("Pad Thai", cats["FOOD"], 60.0, "", 1),
                      ("Thai Milk Tea", cats["DRINK"], 35.0, "", 1),
                      ("Mango Sticky Rice", cats["DESSERT"], 50.0, "", 1)]
            c.executemany("INSERT INTO products(name,category_id,base_price,image,is_active) VALUES(?,?,?,?,?)", sample)
        if c.execute("SELECT COUNT(*) n FROM promotions").fetchone()['n'] == 0:
            today = dt.now()
            st = (today - timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
            ed = (today + timedelta(days=365)).strftime("%Y-%m-%d 23:59:59")
            tea = c.execute("SELECT id FROM products WHERE name='Thai Milk Tea'").fetchone()
            tea_id = tea['id'] if tea else None
            promos=[("WELCOME10","PERCENT_BILL",10,0,st,ed,None,1),
                    ("TEA5","FLAT_ITEM",5,0,st,ed,tea_id,1)]
            c.executemany("""INSERT INTO promotions(code,type,value,min_spend,start_at,end_at,applies_to_product_id,is_active)
                             VALUES(?,?,?,?,?,?,?,?)""", promos)
        self.conn.commit()

    # ----- Admin helpers -----
    def list_products(self):
        q = """SELECT p.*, c.name AS category_name
               FROM products p LEFT JOIN categories c ON c.id=p.category_id"""
        return self.conn.execute(q).fetchall()
    def upsert_product(self, pid, name, category_id, price, img, active):
        cur = self.conn.cursor()
        if pid:
            cur.execute("""UPDATE products SET name=?,category_id=?,base_price=?,image=?,is_active=? WHERE id=?""",
                        (name, category_id, price, img, active, pid))
        else:
            cur.execute("""INSERT INTO products(name,category_id,base_price,image,is_active) VALUES(?,?,?,?,?)""",
                        (name, category_id, price, img, active))
        self.conn.commit()
    def delete_product(self, pid):
        self.conn.execute("DELETE FROM products WHERE id=?", (pid,))
        self.conn.commit()
    def list_promotions(self):
        return self.conn.execute("SELECT * FROM promotions").fetchall()
    def upsert_promotion(self, pid, code, ptype, value, min_spend, start, end, applies, act):
        cur = self.conn.cursor()
        if pid:
            cur.execute("""UPDATE promotions SET code=?,type=?,value=?,min_spend=?,start_at=?,end_at=?,applies_to_product_id=?,is_active=? WHERE id=?""",
                        (code, ptype, value, min_spend, start, end, applies, act, pid))
        else:
            cur.execute("""INSERT INTO promotions(code,type,value,min_spend,start_at,end_at,applies_to_product_id,is_active)
                           VALUES(?,?,?,?,?,?,?,?)""", (code, ptype, value, min_spend, start, end, applies, act))
        self.conn.commit()
    def delete_promotion(self, pid):
        self.conn.execute("DELETE FROM promotions WHERE id=?", (pid,))
        self.conn.commit()

    # --- users ---
    def auth(self, u, p): 
        return self.conn.execute("SELECT * FROM users WHERE username=? AND password_hash=?",(u,sha256(p))).fetchone()
    def create_user(self, u, p):
        try:
            self.conn.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)", (u,sha256(p),"customer"))
            self.conn.commit(); return True, "Account created."
        except sqlite3.IntegrityError: return False, "Username already exists."
    def update_profile(self, uid, fields:dict):
        if not fields: return
        cols=", ".join([f"{k}=?" for k in fields]); vals=list(fields.values())+[uid]
        self.conn.execute(f"UPDATE users SET {cols} WHERE id=?", vals); self.conn.commit()
    def change_password(self, uid, new): 
        self.conn.execute("UPDATE users SET password_hash=? WHERE id=?", (sha256(new), uid)); self.conn.commit()

    # --- catalog/promos ---
    def categories(self): return self.conn.execute("SELECT * FROM categories").fetchall()
    def products_by_cat(self, cid):
        return self.conn.execute("SELECT * FROM products WHERE category_id=? AND is_active=1",(cid,)).fetchall()
    def products_search(self, keyword:str):
        kw=f"%{keyword.strip()}%"
        return self.conn.execute("""SELECT * FROM products
                                    WHERE is_active=1 AND (name LIKE ?)""",(kw,)).fetchall()
    def _within(self, r):
        try: st=dt.strptime(r['start_at'],"%Y-%m-%d %H:%M:%S"); ed=dt.strptime(r['end_at'],"%Y-%m-%d %H:%M:%S")
        except: return True
        return st<=dt.now()<=ed
    def find_promo(self, code):
        r=self.conn.execute("SELECT * FROM promotions WHERE code=? AND is_active=1",(code,)).fetchone()
        return r if (r and self._within(r)) else None

    # --- order/payment ---
    def create_order(self, user_id:int, cart_items:List[Dict], promo_code:str, payment_method="SLIP", payment_ref=""):
        subtotal = sum(float(it['base_price'])*it['qty'] for it in cart_items)
        discount = 0.0
        promo=self.find_promo(promo_code) if promo_code else None
        if promo:
            ptype=promo['type']; val=float(promo['value'] or 0); pid=promo['applies_to_product_id']
            if ptype in ("PERCENT_BILL","FLAT_BILL") and subtotal>=float(promo['min_spend'] or 0):
                discount = subtotal*(val/100.0) if ptype=="PERCENT_BILL" else min(val, subtotal)
            elif ptype in ("PERCENT_ITEM","FLAT_ITEM") and pid:
                target=sum(float(it['base_price'])*it['qty'] for it in cart_items if it['product_id']==pid)
                discount = target*(val/100.0) if ptype=="PERCENT_ITEM" else min(val, target)
        base_after=max(0.0, subtotal-discount)
        vat=round(base_after*VAT_RATE,2)
        total=base_after+vat

        cur=self.conn.cursor()
        cur.execute("""INSERT INTO orders(user_id,order_datetime,channel,pickup_time,subtotal,discount,total,payment_method,status,vat)
                       VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (user_id, now_ts(), "", "", subtotal, discount, total, payment_method, "PAID", vat))
        oid=cur.lastrowid
        for it in cart_items:
            cur.execute("""INSERT INTO order_items(order_id,product_id,qty,unit_price,options_json,note)
                           VALUES(?,?,?,?,?,?)""", (oid, it['product_id'], it['qty'], it['base_price'], "{}", ""))
        cur.execute("INSERT INTO payments(order_id,method,amount,paid_at,ref) VALUES(?,?,?,?,?)",
                    (oid, payment_method, total, now_ts(), payment_ref))
        self.conn.commit()
        self._deduct_from_bom(oid)
        return oid, subtotal, discount, vat, total

    def _deduct_from_bom(self, order_id:int):
        rows = self.conn.execute("""
            SELECT oi.qty, bl.inventory_item_id, bl.qty_per_unit
            FROM order_items oi JOIN bom_links bl ON bl.product_id=oi.product_id
            WHERE oi.order_id=?""",(order_id,)).fetchall()
        cur=self.conn.cursor()
        for r in rows:
            dec=float(r['qty'])*float(r['qty_per_unit'])
            cur.execute("UPDATE inventory_items SET qty_on_hand=qty_on_hand-? WHERE id=?", (dec, r['inventory_item_id']))
            cur.execute("""INSERT INTO stock_movements(inventory_item_id,change_qty,reason,ref_id,created_at)
                           VALUES(?,?,?,?,?)""",(r['inventory_item_id'],-dec,'SALE',order_id, now_ts()))
        self.conn.commit()

    def orders_of_user(self, uid, limit=200):
        return self.conn.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ?", (uid,limit)).fetchall()

    def order_detail(self, oid):
        o = self.conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        items = self.conn.execute("""SELECT oi.*, p.name product_name
                                     FROM order_items oi JOIN products p ON p.id=oi.product_id
                                     WHERE order_id=?""",(oid,)).fetchall()
        return o, items

    # ----- รายงาน -----
    def report_total_by_date(self, start_date:str, end_date:str):
        q = """SELECT substr(order_datetime,1,10) AS d, SUM(total) AS total
               FROM orders
               WHERE date(order_datetime) BETWEEN date(?) AND date(?)
               GROUP BY substr(order_datetime,1,10)
               ORDER BY d"""
        return self.conn.execute(q,(start_date,end_date)).fetchall()
    def report_by_category(self, start_date:str, end_date:str):
        q = """SELECT c.name AS category, SUM(oi.qty*oi.unit_price) AS sales
               FROM order_items oi
               JOIN orders o ON o.id=oi.order_id
               JOIN products p ON p.id=oi.product_id
               JOIN categories c ON c.id=p.category_id
               WHERE date(o.order_datetime) BETWEEN date(?) AND date(?)
               GROUP BY c.id ORDER BY sales DESC"""
        return self.conn.execute(q,(start_date,end_date)).fetchall()
    def report_by_product(self, start_date:str, end_date:str):
        q = """SELECT p.name AS product, SUM(oi.qty) AS qty, SUM(oi.qty*oi.unit_price) AS sales
               FROM order_items oi
               JOIN orders o ON o.id=oi.order_id
               JOIN products p ON p.id=oi.product_id
               WHERE date(o.order_datetime) BETWEEN date(?) AND date(?)
               GROUP BY p.id ORDER BY sales DESC"""
        return self.conn.execute(q,(start_date,end_date)).fetchall()

# ======================= PDF =======================
def _items_table(canv, x, y, items):
    canv.setFont("Helvetica-Bold", 12); canv.drawString(x, y, "Items"); y -= 6*mm
    canv.setFont("Helvetica", 10)
    for it in items:
        canv.drawString(x, y, f"- {it['name']} x{it['qty']}  @ {it['base_price']:.2f}")
        y -= 5*mm
    return y

def create_receipt_pdf(order_id, db: DB, user_row):
    ensure_dirs()
    path=os.path.join(REPORTS_DIR, f"receipt_{order_id}.pdf")
    canv=pdfcanvas.Canvas(path, pagesize=A4); W,H=A4; x=18*mm; y=H-18*mm
    order, items = db.order_detail(order_id)

    canv.setFont("Helvetica-Bold", 16); canv.drawString(x,y,"TASTE AND SIP - RECEIPT"); y-=10*mm
    canv.setFont("Helvetica",10)
    canv.drawString(x,y,f"Order ID: {order_id}"); y-=5*mm
    canv.drawString(x,y,f"Date/Time: {order['order_datetime']}"); y-=5*mm
    canv.drawString(x,y,f"Customer: {user_row['name'] or user_row['username']}"); y-=8*mm

    y = _items_table(canv, x, y, [{"name": r['product_name'], "qty": r['qty'], "base_price": r['unit_price']} for r in items])
    y -= 4*mm
    canv.setFont("Helvetica-Bold", 11)
    canv.drawString(x,y,f"Subtotal: {order['subtotal']:.2f}"); y-=5*mm
    canv.drawString(x,y,f"Discount: {order['discount']:.2f}"); y-=5*mm
    canv.drawString(x,y,f"VAT {int(VAT_RATE*100)}%: {order['vat']:.2f}"); y-=6*mm
    canv.drawString(x,y,f"Total: {order['total']:.2f}"); y-=10*mm

    canv.setFont("Helvetica",10)
    canv.drawString(x,y,f"Payment Method: {order['payment_method']}")
    canv.showPage(); canv.save()
    return path

def create_bill_pdf(cart_items:List[Dict], promo_code:str, db:DB, user_row):
    ensure_dirs()
    ts = dt.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(REPORTS_DIR, f"bill_{ts}.pdf")
    canv=pdfcanvas.Canvas(path, pagesize=A4); W,H=A4; x=18*mm; y=H-18*mm

    canv.setFont("Helvetica-Bold", 16); canv.drawString(x,y,"TASTE AND SIP - BILL/PROFORMA"); y-=10*mm
    canv.setFont("Helvetica",10); canv.drawString(x,y,f"Created at: {now_ts()}"); y-=8*mm
    canv.drawString(x,y,f"Customer: {user_row['name'] or user_row['username']}"); y-=8*mm

    y = _items_table(canv, x, y, cart_items)

    subtotal = sum(it['base_price']*it['qty'] for it in cart_items)
    discount = 0.0
    promo=db.find_promo(promo_code) if promo_code else None
    if promo:
        ptype=promo['type']; val=float(promo['value'] or 0); pid=promo['applies_to_product_id']
        if ptype in ("PERCENT_BILL","FLAT_BILL") and subtotal>=float(promo['min_spend'] or 0):
            discount = subtotal*(val/100.0) if ptype=="PERCENT_BILL" else min(val, subtotal)
        elif ptype in ("PERCENT_ITEM","FLAT_ITEM") and pid:
            target=sum(it['base_price']*it['qty'] for it in cart_items if it['product_id']==pid)
            discount = target*(val/100.0) if ptype=="PERCENT_ITEM" else min(val, target)
    base_after=max(0.0, subtotal-discount)
    vat=round(base_after*VAT_RATE,2); total=base_after+vat

    y -= 4*mm; canv.setFont("Helvetica-Bold", 11)
    canv.drawString(x,y,f"Subtotal: {subtotal:.2f}"); y-=5*mm
    canv.drawString(x,y,f"Discount: {discount:.2f}"); y-=5*mm
    canv.drawString(x,y,f"VAT {int(VAT_RATE*100)}%: {vat:.2f}"); y-=6*mm
    canv.drawString(x,y,f"Total: {total:.2f}")

    canv.showPage(); canv.save()
    return path

# ======================= UI =======================
class ProductCard(ttk.Frame):
    def __init__(self, master, row, on_add):
        super().__init__(master, padding=6, style="Card.TFrame")
        self.row=row; self.on_add=on_add
        img=load_photo(row['image'], (160,120))
        ttk.Label(self, image=img if img else None, text="" if img else "[No Image]").pack()
        if img: self._img=img
        ttk.Label(self, text=row['name'], style="Title.TLabel").pack(pady=(6,0))
        ttk.Label(self, text=f"{row['base_price']:.2f} ฿", style="Price.TLabel").pack()
        ttk.Button(self, text="Add to Cart", command=lambda:self.on_add(row)).pack(pady=4)

# ---- Dialogs ----
class CartDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app); self.app=app
        self.title("Cart"); self.geometry("700x480")
        self.resizable(True, True)
        main=ttk.Frame(self,padding=8); main.pack(fill="both",expand=True)
        self.tv=ttk.Treeview(main,columns=("name","qty","price"),show="headings")
        for k,w,anc in [("name",380,"w"),("qty",80,"e"),("price",120,"e")]:
            self.tv.heading(k,text=k.upper()); self.tv.column(k,width=w,anchor=anc)
        self.tv.pack(fill="both",expand=True)
        act=ttk.Frame(main); act.pack(fill="x",pady=6)
        ttk.Button(act,text="Increase",command=self.increase).pack(side="left")
        ttk.Button(act,text="Decrease",command=self.decrease).pack(side="left",padx=4)
        ttk.Button(act,text="Remove",command=self.remove).pack(side="left",padx=4)
        ttk.Button(act,text="Clear",command=self.clear).pack(side="left",padx=4)
        promo=ttk.Frame(main); promo.pack(fill="x",pady=(6,2))
        ttk.Label(promo,text="Promo Code").pack(side="left")
        self.var_code=tk.StringVar(value=self.app.cart_promo or "")
        ttk.Entry(promo,textvariable=self.var_code,width=14).pack(side="left",padx=6)
        ttk.Button(promo,text="Apply",command=self.apply_code).pack(side="left")
        self.lbl_sub=ttk.Label(main,text="Subtotal: 0.00"); self.lbl_sub.pack(anchor="e")
        self.lbl_dis=ttk.Label(main,text="Discount: 0.00"); self.lbl_dis.pack(anchor="e")
        self.lbl_vat=ttk.Label(main,text=f"VAT {int(VAT_RATE*100)}%: 0.00"); self.lbl_vat.pack(anchor="e")
        self.lbl_tot=ttk.Label(main,text="Total: 0.00",font=("Segoe UI",12,"bold")); self.lbl_tot.pack(anchor="e")
        btns=ttk.Frame(main); btns.pack(fill="x",pady=6)
        ttk.Button(btns,text="Save Bill (PDF)",command=self.save_bill).pack(side="left")
        ttk.Button(btns,text="Checkout & Payment",command=self.goto_payment).pack(side="right")
        self.refresh()

    def _calc(self):
        subtotal=sum(it['base_price']*it['qty'] for it in self.app.cart)
        discount=0.0
        code=(self.var_code.get().strip().upper())
        promo=self.app.db.find_promo(code) if code else None
        if promo:
            ptype=promo['type']; val=float(promo['value'] or 0); pid=promo['applies_to_product_id']
            if ptype in ("PERCENT_BILL","FLAT_BILL") and subtotal>=float(promo['min_spend'] or 0):
                discount=subtotal*(val/100.0) if ptype=="PERCENT_BILL" else min(val, subtotal)
            elif ptype in ("PERCENT_ITEM","FLAT_ITEM") and pid:
                target=sum(it['base_price']*it['qty'] for it in self.app.cart if it['product_id']==pid)
                discount=target*(val/100.0) if ptype=="PERCENT_ITEM" else min(val, target)
        base=max(0.0, subtotal-discount)
        vat=round(base*VAT_RATE,2); total=base+vat
        return subtotal,discount,vat,total

    def refresh(self):
        for i in self.tv.get_children(): self.tv.delete(i)
        for it in self.app.cart:
            line=it['base_price']*it['qty']
            self.tv.insert("", "end", values=(it['name'], it['qty'], f"{line:.2f}"))
        s,d,v,t=self._calc()
        self.lbl_sub.config(text=f"Subtotal: {s:.2f}")
        self.lbl_dis.config(text=f"Discount: {d:.2f}")
        self.lbl_vat.config(text=f"VAT {int(VAT_RATE*100)}%: {v:.2f}")
        self.lbl_tot.config(text=f"Total: {t:.2f}")

    def _selected_index(self):
        sel=self.tv.selection()
        if not sel: return None
        idx=self.tv.index(sel[0])
        return idx if 0<=idx<len(self.app.cart) else None

    def increase(self):
        idx=self._selected_index()
        if idx is None: return
        self.app.cart[idx]['qty']+=1; self.refresh()
    def decrease(self):
        idx=self._selected_index()
        if idx is None: return
        self.app.cart[idx]['qty']=max(1, self.app.cart[idx]['qty']-1); self.refresh()
    def remove(self):
        idx=self._selected_index()
        if idx is None: return
        self.app.cart.pop(idx); self.refresh()
    def clear(self): self.app.cart.clear(); self.refresh()
    def apply_code(self): self.app.cart_promo = self.var_code.get().strip().upper(); self.refresh()
    def save_bill(self):
        if not self.app.cart:
            messagebox.showinfo("Save Bill","Cart is empty"); return
        path=create_bill_pdf(self.app.cart, self.var_code.get().strip().upper(), self.app.db, self.app.user)
        messagebox.showinfo("Saved", f"Bill saved:\n{path}")
    def goto_payment(self):
        self.apply_code()
        PaymentDialog(self.app)
        self.destroy()

class PaymentDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app); self.app=app
        self.title("Checkout & Payment")
        self.geometry("640x720")
        self.resizable(False, False)
        wrap=ttk.Frame(self,padding=12); wrap.pack(fill="both",expand=True)

        ttk.Label(wrap,text="Payment: QR").pack(anchor="w")
        self.qr_canvas=tk.Canvas(wrap,width=260,height=260,bg="#fff",highlightthickness=1,highlightbackground="#ddd")
        self.qr_canvas.pack(pady=(6,12))
        self._qr=None; self._draw_qr()

        ttk.Label(wrap,text="Customer Slip").pack(anchor="w")
        self.slip_canvas=tk.Canvas(wrap,width=260,height=260,bg="#fff",highlightthickness=1,highlightbackground="#ddd")
        self.slip_canvas.pack(pady=(6,8))
        btns=ttk.Frame(wrap); btns.pack()
        ttk.Button(btns,text="Upload Slip...",command=self.upload).pack(side="left", padx=4)
        self.btn_finish = ttk.Button(btns, text="เสร็จสิ้น", command=self.finish_upload, state="disabled")
        self.btn_finish.pack(side="left", padx=4)

        self._slip=None; self.slip_path=self.app.slip_path or None
        self._upload_finished=False
        if self.slip_path:
            self._show_slip(self.slip_path); self.btn_finish['state']="normal"

        ttk.Separator(wrap).pack(fill="x",pady=10)
        s,d,v,t = self._calc_totals()
        self.lbl_totals=ttk.Label(wrap, text=self._totals_text(s,d,v,t), justify="right"); self.lbl_totals.pack(fill="x")
        self.btn_checkout=ttk.Button(wrap,text="Confirm & Checkout",command=self.checkout, state="disabled")
        self.btn_checkout.pack(pady=10, fill="x")

    def _calc_totals(self):
        subtotal=sum(it['base_price']*it['qty'] for it in self.app.cart)
        discount=0.0; code=self.app.cart_promo or ""
        promo=self.app.db.find_promo(code) if code else None
        if promo:
            ptype=promo['type']; val=float(promo['value'] or 0); pid=promo['applies_to_product_id']
            if ptype in ("PERCENT_BILL","FLAT_BILL") and subtotal>=float(promo['min_spend'] or 0):
                discount=subtotal*(val/100.0) if ptype=="PERCENT_BILL" else min(val, subtotal)
            elif ptype in ("PERCENT_ITEM","FLAT_ITEM") and pid:
                target=sum(it['base_price']*it['qty'] for it in self.app.cart if it['product_id']==pid)
                discount=target*(val/100.0) if ptype=="PERCENT_ITEM" else min(val, target)
        base=max(0.0, subtotal-discount); vat=round(base*VAT_RATE,2); total=base+vat
        return subtotal,discount,vat,total
    def _totals_text(self,s,d,v,t):
        return f"Subtotal: {s:.2f}\nDiscount: {d:.2f}\nVAT {int(VAT_RATE*100)}%: {v:.2f}\nTotal: {t:.2f}"
    def _draw_qr(self):
        self.qr_canvas.delete("all")
        if os.path.exists(IMG_QR_PATH):
            try:
                img=Image.open(IMG_QR_PATH).convert("RGB"); img.thumbnail((260,260), Image.LANCZOS)
                self._qr=ImageTk.PhotoImage(img); self.qr_canvas.create_image(130,130,image=self._qr); return
            except: pass
        self.qr_canvas.create_text(130,130,text="QR Placeholder",justify="center")
    def _show_slip(self, path):
        try:
            img=Image.open(path).convert("RGB"); img.thumbnail((260,260), Image.LANCZOS)
            self._slip=ImageTk.PhotoImage(img); self.slip_canvas.delete("all"); self.slip_canvas.create_image(130,130,image=self._slip)
        except:
            self.slip_canvas.delete("all"); self.slip_canvas.create_text(130,130,text="preview failed")
    def upload(self):
        f=filedialog.askopenfilename(title="Select payment slip",
                                     filetypes=[("Images","*.png;*.jpg;*.jpeg;*.bmp;*.gif"),("All files","*.*")])
        if not f: return
        self.slip_path=f; self.app.slip_path=f
        self._show_slip(f)
        self.btn_finish['state']="normal"
    def finish_upload(self):
        if not self.slip_path:
            messagebox.showwarning("Slip","Please upload payment slip first"); return
        self._upload_finished=True
        messagebox.showinfo("Upload","อัปโหลดสลิปเรียบร้อย")
        self.btn_checkout['state']="normal"
    def checkout(self):
        if not self.app.user: messagebox.showwarning("Login","Please sign in"); return
        if not self.app.cart: messagebox.showwarning("Cart","Cart is empty"); return
        if not self.slip_path: messagebox.showwarning("Slip","Please upload payment slip"); return
        if not self._upload_finished:
            messagebox.showwarning("Slip","กรุณากด 'เสร็จสิ้น' หลังอัปโหลดสลิป"); return
        oid, s, d, v, t = self.app.db.create_order(
            user_id=self.app.user['id'], cart_items=self.app.cart,
            promo_code=self.app.cart_promo or "", payment_method="SLIP", payment_ref=self.slip_path
        )
        path=create_receipt_pdf(oid, self.app.db, self.app.user)
        messagebox.showinfo("Success", f"Order #{oid} placed.\nReceipt saved:\n{path}")
        self.app.cart.clear(); self.app.cart_promo=""; self.app.slip_path=None
        self.destroy()
        self.app.show("Orders")

# ---- Main App ----
class App(tk.Tk):
    def __init__(self, on_logout_to_auth: Optional[Callable[[], None]] = None):
        super().__init__()
        self.title(APP_TITLE)
        try: self.state("zoomed")
        except: self.geometry("1200x720")
        ensure_dirs()
        self.db=DB()
        self.user=None
        self.cart:List[Dict]=[]
        self.cart_promo=""
        self.slip_path=None
        self.on_logout_to_auth=on_logout_to_auth
        self._styles(); self._layout()

    def _styles(self):
        st=ttk.Style(self)
        st.configure("Card.TFrame", relief="groove", borderwidth=1)
        st.configure("Title.TLabel", font=("Segoe UI", 11, "bold"))
        st.configure("Price.TLabel", foreground="#087", font=("Segoe UI",10,"bold"))

    def _layout(self):
        top=ttk.Frame(self,padding=6); top.pack(side="top",fill="x")
        self.lbl_user=ttk.Label(top,text="Not signed in"); self.lbl_user.pack(side="left")

        ttk.Button(top,text="Shop",command=lambda:self.show("Shop")).pack(side="left",padx=4)
        ttk.Button(top,text="Cart",command=self.open_cart).pack(side="left",padx=4)
        ttk.Button(top,text="Checkout & Payment",command=self.open_payment).pack(side="left",padx=4)
        ttk.Button(top,text="Orders",command=lambda:self.show("Orders")).pack(side="left",padx=4)
        ttk.Button(top,text="Profile",command=lambda:self.show("Profile")).pack(side="left",padx=4)
        self.btn_admin=ttk.Button(top,text="Admin",command=lambda:self.show("Admin")); self.btn_admin.pack(side="left",padx=4)

        # Search bar
        ttk.Label(top,text="").pack(side="left",padx=8)
        self.var_search=tk.StringVar()
        self.ent_search=ttk.Entry(top,textvariable=self.var_search,width=28); self.ent_search.pack(side="left")
        ttk.Button(top,text="Search",command=self.do_search).pack(side="left",padx=4)

        self.btn_logout=ttk.Button(top,text="Logout",command=self.logout,state="disabled"); self.btn_logout.pack(side="right")

        self.content=ttk.Frame(self); self.content.pack(fill="both",expand=True)
        self.frames={}
        for F in (LoginView, RegisterView, ShopView, OrdersView, ProfileView, AdminView, SearchView):
            f=F(self.content,self); self.frames[F.__name__]=f; f.place(relx=0,rely=0,relwidth=1,relheight=1)
        self.show("Login")

    def do_search(self):
        kw=(self.var_search.get() or "").strip()
        if not kw: messagebox.showinfo("Search","กรุณาพิมพ์คำค้นหาเมนู"); return
        self.frames["SearchView"].run_search(kw); self.show("Search")

    def open_cart(self): 
        if not self.user: messagebox.showinfo("Cart","Please sign in first"); return
        CartDialog(self)
    def open_payment(self):
        if not self.user: messagebox.showinfo("Payment","Please sign in first"); return
        PaymentDialog(self)
    def show(self,name):
        target={"Login":"LoginView","Register":"RegisterView","Shop":"ShopView",
                "Orders":"OrdersView","Profile":"ProfileView","Admin":"AdminView","Search":"SearchView"}[name]
        self.frames[target].tkraise()
        if hasattr(self.frames[target],"on_show"): self.frames[target].on_show()
    def login_ok(self, user_row):
        self.user=user_row
        self.lbl_user.config(text=f"{user_row['username']} ({user_row['role']})")
        self.btn_logout['state']="normal"
        if user_row['role']=="admin":
            self.btn_admin.pack(side="left",padx=4)
        else:
            self.btn_admin.pack_forget()
        self.show("Shop")
    def logout(self):
        self.user=None; self.cart.clear(); self.cart_promo=""; self.slip_path=None
        try: self.destroy()
        finally:
            if self.on_logout_to_auth: self.on_logout_to_auth()

# ---- Views ----
class LoginView(ttk.Frame):
    def __init__(self, master, app: App):
        super().__init__(master,padding=20); self.app=app
        ttk.Label(self,text="Sign In",font=("Segoe UI",18,"bold")).pack(pady=8)
        frm=ttk.Frame(self); frm.pack()
        ttk.Label(frm,text="Username").grid(row=0,column=0,sticky="e",padx=6,pady=4)
        ttk.Label(frm,text="Password").grid(row=1,column=0,sticky="e",padx=6,pady=4)
        self.euser=ttk.Entry(frm,width=30); self.euser.grid(row=0,column=1,pady=4)
        self.epass=ttk.Entry(frm,width=30,show="•"); self.epass.grid(row=1,column=1,pady=4)
        ttk.Button(self,text="Sign In",command=self.signin).pack(pady=6)
        ttk.Button(self,text="Create Account",command=lambda:self.app.show("Register")).pack()
    def on_show(self): self.euser.focus_set()
    def signin(self):
        u=self.euser.get().strip(); p=self.epass.get().strip()
        if not u or not p: messagebox.showerror("Error","Fill username & password"); return
        row=self.app.db.auth(u,p)
        if row: self.app.login_ok(row)
        else: messagebox.showerror("Error","Invalid credentials")

class RegisterView(ttk.Frame):
    def __init__(self, master, app: App):
        super().__init__(master,padding=20); self.app=app
        ttk.Label(self,text="Create Account",font=("Segoe UI",18,"bold")).pack(pady=8)
        frm=ttk.Frame(self); frm.pack()
        self.euser=self._row(frm,"Username",0)
        self.ep1=self._row(frm,"Password",1,show="•")
        self.ep2=self._row(frm,"Confirm",2,show="•")
        ttk.Button(self,text="Register",command=self.reg).pack(pady=6)
        ttk.Button(self,text="Back to Login",command=lambda:self.app.show("Login")).pack()
    def _row(self,parent,label,r,show=""):
        ttk.Label(parent,text=label).grid(row=r,column=0,sticky="e",padx=6,pady=4)
        e=ttk.Entry(parent,width=30,show=show); e.grid(row=r,column=1,pady=4); return e
    def reg(self):
        u=self.euser.get().strip(); p1=self.ep1.get().strip(); p2=self.ep2.get().strip()
        if not u or not p1 or not p2: messagebox.showerror("Error","Fill all fields"); return
        if p1!=p2: messagebox.showerror("Error","Passwords do not match"); return
        ok,msg=self.app.db.create_user(u,p1)
        if ok: messagebox.showinfo("Success",msg); self.app.show("Login")
        else: messagebox.showerror("Error",msg)

class ShopView(ttk.Frame):
    def __init__(self, master, app: App):
        super().__init__(master,padding=8); self.app=app
        self.nb=ttk.Notebook(self); self.nb.pack(fill="both",expand=True)
    def on_show(self):
        for t in self.nb.tabs(): self.nb.forget(t)
        for cat in self.app.db.categories():
            frm=ttk.Frame(self.nb,padding=8); self.nb.add(frm,text=cat['name'])
            can=tk.Canvas(frm); vs=ttk.Scrollbar(frm,orient="vertical",command=can.yview)
            holder=ttk.Frame(can); holder.bind("<Configure>", lambda e,c=can:c.configure(scrollregion=c.bbox("all")))
            can.create_window((0,0),window=holder,anchor="nw"); can.configure(yscrollcommand=vs.set)
            can.pack(side="left",fill="both",expand=True); vs.pack(side="right",fill="y")
            rowf=None; col=0
            for i,p in enumerate(self.app.db.products_by_cat(cat['id'])):
                if i%4==0: rowf=ttk.Frame(holder); rowf.pack(fill="x",pady=6); col=0
                ProductCard(rowf,p,self.add).grid(row=0,column=col,padx=6); col+=1
    def add(self, prod_row):
        for it in self.app.cart:
            if it['product_id']==prod_row['id']:
                it['qty']+=1; break
        else:
            self.app.cart.append({"product_id":prod_row['id'],"name":prod_row['name'],
                                  "base_price":float(prod_row['base_price']),"qty":1})

class SearchView(ttk.Frame):
    def __init__(self, master, app: App):
        super().__init__(master,padding=10); self.app=app
        ttk.Label(self,text="Search Results",font=("Segoe UI",16,"bold")).pack(anchor="w")
        self.holder=ttk.Frame(self); self.holder.pack(fill="both",expand=True,pady=6)
    def on_show(self): pass
    def run_search(self, keyword:str):
        for w in self.holder.winfo_children(): w.destroy()
        rows=self.app.db.products_search(keyword)
        if not rows:
            ttk.Label(self.holder,text="ไม่พบเมนูที่ค้นหา").pack(anchor="w",pady=8); return
        grid=ttk.Frame(self.holder); grid.pack(fill="x")
        col=0; rowframe=None
        for i, p in enumerate(rows):
            if i%4==0:
                rowframe=ttk.Frame(grid); rowframe.pack(fill="x",pady=6); col=0
            ProductCard(rowframe, p, self._add).grid(row=0,column=col,padx=6); col+=1
    def _add(self, prod_row):
        for it in self.app.cart:
            if it['product_id']==prod_row['id']:
                it['qty']+=1; break
        else:
            self.app.cart.append({"product_id":prod_row['id'],"name":prod_row['name'],
                                  "base_price":float(prod_row['base_price']),"qty":1})

class OrdersView(ttk.Frame):
    def __init__(self, master, app: App):
        super().__init__(master,padding=10); self.app=app
        ttk.Label(self,text="Order History",font=("Segoe UI",16,"bold")).pack(anchor="w")
        self.tv=ttk.Treeview(self,columns=("id","date","total"),show="headings")
        for k,w in [("id",80),("date",160),("total",90)]:
            self.tv.heading(k,text=k.upper()); self.tv.column(k,width=w,anchor="w")
        self.tv.pack(fill="both",expand=True,pady=6)
        fr=ttk.Frame(self); fr.pack(anchor="e")
        ttk.Button(fr,text="Open Receipt",command=self.open).pack(side="right",padx=4)
        ttk.Button(fr,text="Refresh",command=self.refresh).pack(side="right",padx=4)
    def on_show(self): self.refresh()
    def refresh(self):
        for i in self.tv.get_children(): self.tv.delete(i)
        if not self.app.user: return
        for r in self.app.db.orders_of_user(self.app.user['id']):
            self.tv.insert("", "end", values=(r['id'], r['order_datetime'], f"{r['total']:.2f}"))
    def open(self):
        sel=self.tv.selection()
        if not sel: messagebox.showinfo("Open","Select an order"); return
        oid=int(self.tv.item(sel[0],"values")[0]); path=os.path.join(REPORTS_DIR,f"receipt_{oid}.pdf")
        if not os.path.exists(path): path=create_receipt_pdf(oid,self.app.db,self.app.user)
        try:
            if sys.platform.startswith("win"): os.startfile(path)
            elif sys.platform=="darwin": os.system(f"open '{path}'")
            else: os.system(f"xdg-open '{path}'")
        except: messagebox.showinfo("Receipt", f"Saved at: {path}")

class ProfileView(ttk.Frame):
    def __init__(self, master, app: App):
        super().__init__(master,padding=12); self.app=app
        ttk.Label(self,text="My Profile",font=("Segoe UI",16,"bold")).pack(anchor="w")
        container=ttk.Frame(self); container.pack(fill="x",pady=6)
        self.avatar_canvas=tk.Canvas(container,width=120,height=120,bg="#eee",highlightthickness=1,highlightbackground="#ddd")
        self.avatar_canvas.grid(row=0,column=0,rowspan=4,padx=8)
        ttk.Button(container,text="Change Avatar",command=self.change_avatar).grid(row=4,column=0,padx=8,pady=4)
        self.vars={}
        fields=[("name","Name"),("phone","Phone"),("email","Email"),("birthdate","Birthdate (YYYY-MM-DD)"),("gender","Gender")]
        for i,(k,label) in enumerate(fields):
            ttk.Label(container,text=label).grid(row=i,column=1,sticky="e",padx=6,pady=4)
            v=tk.StringVar(); ttk.Entry(container,textvariable=v,width=30).grid(row=i,column=2,pady=4)
            self.vars[k]=v
        fr=ttk.Frame(self); fr.pack(anchor="w",pady=6)
        ttk.Button(fr,text="Save Profile",command=self.save).pack(side="left")
        ttk.Button(fr,text="Change Password",command=self.change_pw).pack(side="left",padx=6)
    def on_show(self):
        u=self.app.user; 
        if not u: return
        for k in self.vars: self.vars[k].set(u[k] or "")
        self._draw_avatar(u['avatar'])
    def _draw_avatar(self, path):
        self.avatar_canvas.delete("all")
        img=load_photo(path,(120,120))
        if img:
            self._av=img; self.avatar_canvas.create_image(60,60,image=self._av)
        else:
            self.avatar_canvas.create_text(60,60,text="No Avatar")
    def change_avatar(self):
        if not self.app.user: return
        f=filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg")])
        if not f: return
        os.makedirs(IMG_AVATARS_DIR, exist_ok=True)
        dest=os.path.join(IMG_AVATARS_DIR, os.path.basename(f))
        try:
            shutil.copy2(f,dest)
            self.app.db.update_profile(self.app.user['id'], {"avatar":dest})
            self.app.user=self.app.db.conn.execute("SELECT * FROM users WHERE id=?", (self.app.user['id'],)).fetchone()
            self._draw_avatar(dest)
        except Exception as e: messagebox.showerror("Avatar", f"Copy failed: {e}")
    def save(self):
        if not self.app.user: return
        data={k:self.vars[k].get().strip() for k in self.vars}
        self.app.db.update_profile(self.app.user['id'], data)
        self.app.user=self.app.db.conn.execute("SELECT * FROM users WHERE id=?", (self.app.user['id'],)).fetchone()
        messagebox.showinfo("Saved","Profile updated")
    def change_pw(self):
        if not self.app.user: return
        np=simpledialog.askstring("Change Password","New password:", show="•")
        if not np: return
        self.app.db.change_password(self.app.user['id'], np)
        messagebox.showinfo("Password","Password updated")

class AdminView(ttk.Frame):
    def __init__(self, master, app: App):
        super().__init__(master,padding=8); self.app=app
        ttk.Label(self,text="Admin Panel",font=("Segoe UI",16,"bold")).pack(anchor="w")
        self.nb=ttk.Notebook(self); self.nb.pack(fill="both",expand=True)
        self.tab_products=ttk.Frame(self.nb,padding=8); self.nb.add(self.tab_products,text="Products")
        self.tab_promos=ttk.Frame(self.nb,padding=8); self.nb.add(self.tab_promos,text="Promotions")
        self.tab_reports=ttk.Frame(self.nb,padding=8); self.nb.add(self.tab_reports,text="Reports")
        self._products(); self._promos(); self._reports()
    def on_show(self):
        if not self.app.user or self.app.user['role']!="admin":
            messagebox.showwarning("Permission","Admin only"); return
        self.reload_products(); self.reload_promos()
    # products
    def _products(self):
        top=ttk.Frame(self.tab_products); top.pack(fill="x")
        ttk.Button(top,text="Add",command=lambda:ProductEditor(self,self.app.db,None,self.reload_products)).pack(side="left")
        ttk.Button(top,text="Edit",command=self._edit).pack(side="left",padx=4)
        ttk.Button(top,text="Delete",command=self._delete).pack(side="left",padx=4)
        ttk.Button(top,text="Refresh",command=self.reload_products).pack(side="left",padx=4)
        self.tvp=ttk.Treeview(self.tab_products,columns=("id","name","category","price","image","active"),show="headings")
        for k,w in [("id",50),("name",160),("category",100),("price",80),("image",240),("active",60)]:
            self.tvp.heading(k,text=k.upper()); self.tvp.column(k,width=w,anchor="w")
        self.tvp.pack(fill="both",expand=True,pady=6)
    def reload_products(self):
        for i in self.tvp.get_children(): self.tvp.delete(i)
        for r in self.app.db.list_products():
            self.tvp.insert("", "end", values=(r['id'], r['name'], r['category_name'], f"{r['base_price']:.2f}", r['image'], r['is_active']))
    def _edit(self):
        sel=self.tvp.selection()
        if not sel: messagebox.showinfo("Edit","Select a product"); return
        pid=int(self.tvp.item(sel[0],"values")[0]); ProductEditor(self,self.app.db,pid,self.reload_products)
    def _delete(self):
        sel=self.tvp.selection()
        if not sel: messagebox.showinfo("Delete","Select a product"); return
        pid=int(self.tvp.item(sel[0],"values")[0])
        if messagebox.askyesno("Confirm","Delete product?"):
            self.app.db.delete_product(pid); self.reload_products()
    # promos
    def _promos(self):
        top=ttk.Frame(self.tab_promos); top.pack(fill="x")
        ttk.Button(top,text="Add",command=lambda:PromoEditor(self,self.app.db,None,self.reload_promos)).pack(side="left")
        ttk.Button(top,text="Edit",command=self._edit_p).pack(side="left",padx=4)
        ttk.Button(top,text="Delete",command=self._del_p).pack(side="left",padx=4)
        ttk.Button(top,text="Refresh",command=self.reload_promos).pack(side="left",padx=4)
        self.tvpr=ttk.Treeview(self.tab_promos,columns=("id","code","type","value","min","start","end","prod","active"),show="headings")
        heads=[("id",50),("code",120),("type",120),("value",80),("min",80),("start",140),("end",140),("prod",80),("active",60)]
        for k,w in heads: self.tvpr.heading(k,text=k.upper()); self.tvpr.column(k,width=w,anchor="w")
        self.tvpr.pack(fill="both",expand=True,pady=6)
    def reload_promos(self):
        for i in self.tvpr.get_children(): self.tvpr.delete(i)
        for r in self.app.db.list_promotions():
            self.tvpr.insert("", "end", values=(r['id'],r['code'],r['type'],r['value'],r['min_spend'],r['start_at'],r['end_at'],r['applies_to_product_id'] or "-",r['is_active']))
    def _edit_p(self):
        sel=self.tvpr.selection()
        if not sel: messagebox.showinfo("Edit","Select a promotion"); return
        pid=int(self.tvpr.item(sel[0],"values")[0]); PromoEditor(self,self.app.db,pid,self.reload_promos)
    def _del_p(self):
        sel=self.tvpr.selection()
        if not sel: messagebox.showinfo("Delete","Select a promotion"); return
        pid=int(self.tvpr.item(sel[0],"values")[0])
        if messagebox.askyesno("Confirm","Delete promotion?"):
            self.app.db.delete_promotion(pid); self.reload_promos()
    # reports
    def _reports(self):
        fr=ttk.Frame(self.tab_reports); fr.pack(fill="x")
        self.var_start=tk.StringVar(value=dt.now().strftime("%Y-%m-01"))
        self.var_end=tk.StringVar(value=dt.now().strftime("%Y-%m-%d"))
        ttk.Label(fr,text="Start (YYYY-MM-DD)").grid(row=0,column=0,sticky="w")
        ttk.Entry(fr,textvariable=self.var_start,width=12).grid(row=0,column=1,padx=6)
        ttk.Label(fr,text="End").grid(row=0,column=2,sticky="w")
        ttk.Entry(fr,textvariable=self.var_end,width=12).grid(row=0,column=3,padx=6)
        ttk.Button(fr,text="Daily Total",command=self.run_daily).grid(row=0,column=4,padx=6)
        ttk.Button(fr,text="By Category",command=self.run_cat).grid(row=0,column=5,padx=6)
        ttk.Button(fr,text="By Product",command=self.run_prod).grid(row=0,column=6,padx=6)
        self.tvr=ttk.Treeview(self.tab_reports,columns=("c1","c2","c3"),show="headings")
        self.tvr.pack(fill="both",expand=True,pady=6)
    def _fill(self, headers, rows):
        self.tvr["columns"]=tuple(f"c{i}" for i in range(len(headers)))
        self.tvr["show"]="headings"
        for i in self.tvr.get_children(): self.tvr.delete(i)
        for i,h in enumerate(headers):
            self.tvr.heading(f"c{i}", text=h); self.tvr.column(f"c{i}", width=160, anchor="w")
        for r in rows: self.tvr.insert("", "end", values=tuple(r))
    def run_daily(self):
        s=self.var_start.get().strip(); e=self.var_end.get().strip()
        rows=[(r['d'], f"{(r['total'] or 0):.2f}") for r in self.app.db.report_total_by_date(s,e)]
        self._fill(["DATE","TOTAL"], rows)
    def run_cat(self):
        s=self.var_start.get().strip(); e=self.var_end.get().strip()
        rows=[(r['category'], f"{(r['sales'] or 0):.2f}") for r in self.app.db.report_by_category(s,e)]
        self._fill(["CATEGORY","SALES"], rows)
    def run_prod(self):
        s=self.var_start.get().strip(); e=self.var_end.get().strip()
        rows=[(r['product'], r['qty'], f"{(r['sales'] or 0):.2f}") for r in self.app.db.report_by_product(s,e)]
        self._fill(["PRODUCT","QTY","SALES"], rows)

# ---- Editors ----
class ProductEditor(tk.Toplevel):
    def __init__(self, master, db: DB, pid, on_done):
        super().__init__(master); self.db=db; self.pid=pid; self.on_done=on_done
        self.title("Product Editor"); self.geometry("460x400")
        frm=ttk.Frame(self,padding=10); frm.pack(fill="both",expand=True)
        ttk.Label(frm,text="Name").grid(row=0,column=0,sticky="e"); self.en=ttk.Entry(frm,width=30); self.en.grid(row=0,column=1,pady=4)
        ttk.Label(frm,text="Category").grid(row=1,column=0,sticky="e")
        cats=db.categories(); self.cat_map={c['name']:c['id'] for c in cats}
        self.ec=ttk.Combobox(frm,values=list(self.cat_map.keys()),state="readonly",width=27); self.ec.grid(row=1,column=1,pady=4)
        ttk.Label(frm,text="Base Price").grid(row=2,column=0,sticky="e"); self.ep=ttk.Entry(frm,width=30); self.ep.grid(row=2,column=1,pady=4)
        ttk.Label(frm,text="Image").grid(row=3,column=0,sticky="e"); self.ei=ttk.Entry(frm,width=30); self.ei.grid(row=3,column=1,pady=4)
        ttk.Button(frm,text="Choose Image...",command=self.choose_img).grid(row=3,column=2,padx=4)
        ttk.Label(frm,text="Active (1/0)").grid(row=4,column=0,sticky="e"); self.ea=ttk.Entry(frm,width=30); self.ea.grid(row=4,column=1,pady=4)
        ttk.Button(frm,text="Save",command=self.save).grid(row=5,column=1,pady=8)
        if pid:
            r=db.conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
            if r:
                self.en.insert(0,r['name'])
                cname=db.conn.execute("SELECT name FROM categories WHERE id=?", (r['category_id'],)).fetchone()
                self.ec.set(cname['name'] if cname else "")
                self.ep.insert(0,str(r['base_price'])); self.ei.insert(0,r['image'] or ""); self.ea.insert(0,str(r['is_active']))
    def choose_img(self):
        f=filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg")])
        if not f: return
        dest=os.path.join(IMG_PRODUCTS_DIR, os.path.basename(f))
        try: shutil.copy2(f,dest); self.ei.delete(0,"end"); self.ei.insert(0,dest)
        except Exception as e: messagebox.showerror("Image", f"Copy failed: {e}")
    def save(self):
        name=self.en.get().strip(); cat=self.ec.get().strip()
        price=float(self.ep.get().strip() or 0); img=self.ei.get().strip(); act=int(self.ea.get().strip() or 1)
        if not name or not cat: messagebox.showerror("Error","Name/Category required"); return
        self.db.upsert_product(self.pid, name, self.cat_map[cat], price, img, act)
        messagebox.showinfo("Saved","Product saved"); self.on_done(); self.destroy()

class PromoEditor(tk.Toplevel):
    def __init__(self, master, db: DB, pid, on_done):
        super().__init__(master); self.db=db; self.pid=pid; self.on_done=on_done
        self.title("Promotion Editor"); self.geometry("520x320")
        frm=ttk.Frame(self,padding=10); frm.pack(fill="both",expand=True)
        fields=[("Code","code"),("Type [PERCENT_BILL/FLAT_BILL/PERCENT_ITEM/FLAT_ITEM]","type"),
                ("Value","value"),("Min Spend","min"),
                ("Start (YYYY-MM-DD HH:MM:SS)","start"),("End","end"),
                ("Applies to Product ID (for *_ITEM)","prod"),("Active 1/0","act")]
        self.inp={}
        for i,(label,key) in enumerate(fields):
            ttk.Label(frm,text=label).grid(row=i,column=0,sticky="e"); e=ttk.Entry(frm,width=38); e.grid(row=i,column=1,pady=3); self.inp[key]=e
        ttk.Button(frm,text="Save",command=self.save).grid(row=len(fields),column=1,pady=8,sticky="e")
        if pid:
            r=db.conn.execute("SELECT * FROM promotions WHERE id=?", (pid,)).fetchone()
            if r:
                self.inp["code"].insert(0,r['code']); self.inp["type"].insert(0,r['type'])
                self.inp["value"].insert(0,str(r['value'])); self.inp["min"].insert(0,str(r['min_spend']))
                self.inp["start"].insert(0,r['start_at']); self.inp["end"].insert(0,r['end_at'])
                self.inp["prod"].insert(0, "" if r['applies_to_product_id'] is None else str(r['applies_to_product_id']))
                self.inp["act"].insert(0,str(r['is_active']))
    def save(self):
        code=self.inp["code"].get().strip().upper()
        ptype=self.inp["type"].get().strip()
        value=float(self.inp["value"].get().strip() or 0)
        min_spend=float(self.inp["min"].get().strip() or 0)
        start=self.inp["start"].get().strip() or (dt.now().strftime("%Y-%m-%d 00:00:00"))
        end=self.inp["end"].get().strip() or (dt.now()+timedelta(days=365)).strftime("%Y-%m-%d 23:59:59")
        prod=self.inp["prod"].get().strip(); applies=int(prod) if prod.isdigit() else None
        act=int(self.inp["act"].get().strip() or 1)
        if not code or ptype not in ("PERCENT_BILL","FLAT_BILL","PERCENT_ITEM","FLAT_ITEM"):
            messagebox.showerror("Error","Invalid code/type"); return
        self.db.upsert_promotion(self.pid, code, ptype, value, min_spend, start, end, applies, act)
        messagebox.showinfo("Saved","Promotion saved"); self.on_done(); self.destroy()

# ======================= Auth (customtkinter) =======================
RIGHT_BG="#e9dcc6"         # ครีมเข้ม
CARD_BG="#edd8b8"
TEXT_DARK="#1f2937"; LINK_FG="#0057b7"; BORDER="#d3c6b4"; CARD_W=660; CARD_H=560; RADIUS=18
USERNAME_RE=re.compile(r"^[A-Za-z0-9]{6,}$")
PHONE_RE=re.compile(r"^\d{10}$")
EMAIL_RE=re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PWD_RE=re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,}$")

class AuthDB:
    def __init__(self, path=DB_FILE):
        self.conn=sqlite3.connect(path); self.conn.row_factory=sqlite3.Row
        self.conn.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT, phone TEXT, email TEXT, birthdate TEXT, gender TEXT,
            avatar TEXT, role TEXT DEFAULT 'customer')"""); self.conn.commit()
    def find_user_for_login(self,u,p):
        return self.conn.execute("SELECT * FROM users WHERE username=? AND password_hash=?",(u,sha256(p))).fetchone()
    def username_exists(self,u): return self.conn.execute("SELECT 1 FROM users WHERE username=?", (u,)).fetchone() is not None
    def create_user(self,u,ph,em,p):
        self.conn.execute("INSERT INTO users(username,password_hash,phone,email,role) VALUES(?,?,?,?,?)",(u,sha256(p),ph,em,"customer")); self.conn.commit()
    def verify_user_contact(self,u,cp):
        return self.conn.execute("SELECT * FROM users WHERE username=? AND (email=? OR phone=?)",(u,cp,cp)).fetchone()
    def change_password(self,u,new):
        self.conn.execute("UPDATE users SET password_hash=? WHERE username=?",(sha256(new),u)); self.conn.commit()

def validate_username(v): return None if USERNAME_RE.match(v or "") else "USERNAME MUST BE AT LEAST 6 CHARACTERS AND CONTAIN ONLY A–Z AND 0–9."
def validate_phone(v): return None if PHONE_RE.match(v or "") else "PHONE MUST BE 10 DIGITS."
def validate_email(v): return None if EMAIL_RE.match(v or "") else "INVALID EMAIL FORMAT."
def validate_password(v): return None if PWD_RE.match(v or "") else "PASSWORD MUST BE ≥ 8 CHARS, INCLUDE UPPERCASE, LOWERCASE AND A DIGIT."

class AuthApp(ctk.CTk):
    """เวอร์ชันปรับปรุง: หน้าต่างขยายได้ + รูปซ้าย cover เต็ม + การ์ดขวาคงที่"""
    def __init__(self, db_path=DB_FILE, left_bg_path=None, logo_path=None, on_login_success=None):
        super().__init__(); ctk.set_appearance_mode("light")
        self.title(APP_TITLE)
        self.geometry("1200x720")
        self.minsize(1100, 680)
        self.configure(fg_color=RIGHT_BG)

        self.db=AuthDB(db_path); self.on_login_success=on_login_success
        self.left_bg_path=left_bg_path; self.logo_path=logo_path

        # layout 2 คอลัมน์
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ซ้าย: รูป (canvas)
        self.left=ctk.CTkFrame(self, fg_color=RIGHT_BG, corner_radius=0)
        self.left.grid(row=0,column=0,sticky="nsew")
        self.left_canvas=tk.Canvas(self.left, highlightthickness=0, bd=0, bg=RIGHT_BG)
        self.left_canvas.place(x=0,y=0,relwidth=1,relheight=1)
        self._left_img_tk=None
        self.left.bind("<Configure>", lambda e: self._draw_left_bg(e.width, e.height))
        self.bind("<Configure>", lambda e: self._draw_left_bg())

        # ขวา: โลโก้ + การ์ด
        self.right=ctk.CTkFrame(self, fg_color=RIGHT_BG, corner_radius=0)
        self.right.grid(row=0,column=1,sticky="nsew")
        self.right.grid_rowconfigure(1, weight=1)
        self.right.grid_columnconfigure(0, weight=1)

        self.logo_wrap=ctk.CTkFrame(self.right, fg_color=RIGHT_BG)
        self.logo_wrap.grid(row=0,column=0,pady=(30,10))
        self._render_logo()

        self.card=ctk.CTkFrame(self.right, fg_color=CARD_BG, corner_radius=RADIUS,
                                border_color=BORDER, border_width=1, width=CARD_W, height=CARD_H)
        self.card.grid(row=1,column=0,sticky="n",padx=80,pady=(10,40))
        self.card.grid_propagate(False)
        self.card.grid_columnconfigure(0, weight=1)

        self.show_signin()

    # ----- วาดรูปแบบ cover -----
    def _draw_left_bg(self, w=None, h=None):
        c=self.left_canvas
        if w is None or h is None:
            c.update_idletasks()
            w=c.winfo_width(); h=c.winfo_height()
            if w <= 1 or h <= 1:
                w=self.left.winfo_width(); h=self.left.winfo_height()
        c.delete("all")
        c.create_rectangle(0,0,w,h,fill=RIGHT_BG,outline="")
        if self.left_bg_path and os.path.exists(self.left_bg_path):
            try:
                img=Image.open(self.left_bg_path).convert("RGB")
                iw,ih=img.size
                scale=max(w/iw, h/ih)
                nw,nh=int(iw*scale), int(ih*scale)
                img=img.resize((nw,nh), Image.LANCZOS)
                left=max(0, (nw - w)//2); top=max(0, (nh - h)//2)
                img=img.crop((left, top, left + w, top + h))
                self._left_img_tk=ImageTk.PhotoImage(img)
                c.create_image(0,0,anchor="nw",image=self._left_img_tk)
            except: pass
        t1=c.create_text(28,28,anchor="nw",fill="white",font=("Segoe UI",36,"bold"),text=f"WELCOME TO\n{APP_TITLE}".upper())
        bbox=c.bbox(t1); y2=(bbox[3] if bbox else 120)+18
        c.create_text(32,y2,anchor="nw",fill="white",font=("Segoe UI",18,"bold"),text="FOOD AND DRINK!".upper())

    def _render_logo(self):
        for w in self.logo_wrap.winfo_children(): w.destroy()
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                img=Image.open(self.logo_path)
                self._logo_img=ctk.CTkImage(light_image=img,dark_image=img,size=(220,220))
                ctk.CTkLabel(self.logo_wrap,image=self._logo_img,text="",fg_color="transparent").pack(); return
            except: pass
        ctk.CTkLabel(self.logo_wrap,text=APP_TITLE.upper(),font=ctk.CTkFont(size=22,weight="bold"),
                     text_color=TEXT_DARK,fg_color="transparent").pack()

    def _clear_card(self):
        for w in self.card.winfo_children(): w.destroy()
        self.card.grid_columnconfigure(0, weight=1)

    # ----- Screens -----
    def show_signin(self):
        self._clear_card()
        Title(self.card,"SIGN IN").pack(pady=(22,6))
        self.si_err=ErrorLabel(self.card); self.si_err.pack(padx=28,fill="x")
        self.si_user=LabeledEntry(self.card,"USERNAME"); self.si_user.pack(fill="x",padx=28,pady=(6,8))
        self.si_pwd=LabeledEntry(self.card,"PASSWORD",show="•"); self.si_pwd.pack(fill="x",padx=28,pady=(6,12))
        SubmitBtn(self.card,"SIGN IN",command=self._signin).pack(fill="x",padx=28,pady=(0,12))
        bottom=ctk.CTkFrame(self.card,fg_color="transparent"); bottom.pack(fill="x",pady=(4,18))
        LinkBtn(bottom,"FORGOT PASSWORD?",command=self.show_forgot).pack(side="left",padx=4)
        LinkBtn(bottom,"CREATE ACCOUNT",command=self.show_signup).pack(side="right",padx=4)

    def show_signup(self):
        self._clear_card()
        Title(self.card,"CREATE ACCOUNT").pack(pady=(22,6))
        self.su_err=ErrorLabel(self.card); self.su_err.pack(padx=24,fill="x")
        form=ctk.CTkFrame(self.card,fg_color="transparent"); form.pack(fill="x",padx=24,pady=(6,10))
        form.grid_columnconfigure(0,weight=1,uniform="c"); form.grid_columnconfigure(1,weight=1,uniform="c")
        self.su_user=LabeledEntry(form,"USERNAME"); self.su_user.grid(row=0,column=0,padx=8,pady=6,sticky="ew")
        self.su_phone=LabeledEntry(form,"PHONE"); self.su_phone.grid(row=0,column=1,padx=8,pady=6,sticky="ew")
        self.su_email=LabeledEntry(form,"EMAIL"); self.su_email.grid(row=1,column=0,columnspan=2,padx=8,pady=6,sticky="ew")
        self.su_pwd1=LabeledEntry(form,"PASSWORD",show="•"); self.su_pwd1.grid(row=2,column=0,padx=8,pady=6,sticky="ew")
        self.su_pwd2=LabeledEntry(form,"CONFIRM PASSWORD",show="•"); self.su_pwd2.grid(row=2,column=1,padx=8,pady=6,sticky="ew")
        SubmitBtn(self.card,"REGISTER",command=self._signup).pack(fill="x",padx=24,pady=(8,12))
        LinkBtn(self.card,"BACK TO LOGIN",command=self.show_signin).pack(pady=(0,18))

    def show_forgot(self):
        self._clear_card()
        Title(self.card,"FORGOT PASSWORD").pack(pady=(22,6))
        self.fp_err=ErrorLabel(self.card); self.fp_err.pack(padx=24,fill="x")

        form=ctk.CTkFrame(self.card,fg_color="transparent"); form.pack(fill="x",padx=20,pady=(6,10))
        form.grid_columnconfigure(0,weight=1,uniform="f"); form.grid_columnconfigure(1,weight=1,uniform="f")

        self.fp_user=LabeledEntry(form,"USERNAME"); self.fp_user.grid(row=0,column=0,padx=8,pady=6,sticky="ew")
        self.fp_contact=LabeledEntry(form,"EMAIL OR PHONE"); self.fp_contact.grid(row=0,column=1,padx=8,pady=6,sticky="ew")

        btnrow=ctk.CTkFrame(form,fg_color="transparent"); btnrow.grid(row=1,column=0,columnspan=2,sticky="e",padx=8,pady=(0,6))
        SubmitBtn(btnrow,"VERIFY",command=self._forgot_verify).pack(side="right")

        self.fp_pwd1=LabeledEntry(form,"NEW PASSWORD",show="•"); self.fp_pwd1.grid(row=2,column=0,padx=8,pady=6,sticky="ew")
        self.fp_pwd2=LabeledEntry(form,"CONFIRM NEW PASSWORD",show="•"); self.fp_pwd2.grid(row=2,column=1,padx=8,pady=6,sticky="ew")
        for e in (self.fp_pwd1.entry, self.fp_pwd2.entry):
            e.configure(state="disabled")

        SubmitBtn(self.card,"CHANGE PASSWORD",command=self._forgot_change).pack(fill="x",padx=24,pady=(4,12))
        LinkBtn(self.card,"BACK TO LOGIN",command=self.show_signin).pack(pady=(0,18))
        self._verified_username=None

    # --- Auth flows ---
    def _signin(self):
        self.si_err.set(""); u=(self.si_user.get() or "").strip(); p=(self.si_pwd.get() or "").strip()
        if not u or not p: self.si_err.set("PLEASE ENTER USERNAME AND PASSWORD."); return
        row=self.db.find_user_for_login(u,p)
        if row: 
            if self.on_login_success: self.on_login_success(row)
        else: self.si_err.set("INVALID CREDENTIALS.")
    def _signup(self):
        self.su_err.set("")
        u=(self.su_user.get() or "").strip(); ph=(self.su_phone.get() or "").strip()
        em=(self.su_email.get() or "").strip(); p1=(self.su_pwd1.get() or "").strip(); p2=(self.su_pwd2.get() or "").strip()
        for fn in (lambda:validate_username(u), lambda:validate_phone(ph), lambda:validate_email(em), lambda:validate_password(p1)):
            msg=fn(); 
            if msg: self.su_err.set(msg); return
        if p1!=p2: self.su_err.set("PASSWORDS DO NOT MATCH."); return
        if self.db.username_exists(u): self.su_err.set("USERNAME ALREADY EXISTS."); return
        try: self.db.create_user(u,ph,em,p1); self.su_err.set("ACCOUNT CREATED. PLEASE SIGN IN.")
        except sqlite3.IntegrityError: self.su_err.set("USERNAME ALREADY EXISTS.")
        except Exception as e: self.su_err.set(f"FAILED TO REGISTER: {e}")
    def _forgot_verify(self):
        self.fp_err.set(""); u=(self.fp_user.get() or "").strip(); cp=(self.fp_contact.get() or "").strip()
        if not u or not cp: self.fp_err.set("PLEASE FILL USERNAME AND EMAIL/PHONE."); return
        row=self.db.verify_user_contact(u,cp)
        if row:
            self._verified_username=u; self.fp_err.set("VERIFIED. PLEASE SET A NEW PASSWORD BELOW.")
            for e in (self.fp_pwd1.entry, self.fp_pwd2.entry):
                e.configure(state="normal")
        else:
            self.fp_err.set("NO MATCHING ACCOUNT FOR THE GIVEN USERNAME AND EMAIL/PHONE.")
    def _forgot_change(self):
        if not self._verified_username: self.fp_err.set("PLEASE VERIFY FIRST."); return
        p1=(self.fp_pwd1.get() or "").strip(); p2=(self.fp_pwd2.get() or "").strip()
        msg=validate_password(p1); 
        if msg: self.fp_err.set(msg); return
        if p1!=p2: self.fp_err.set("PASSWORDS DO NOT MATCH."); return
        try: self.db.change_password(self._verified_username,p1); self.fp_err.set("PASSWORD CHANGED. YOU CAN SIGN IN NOW.")
        except Exception as e: self.fp_err.set(f"FAILED TO CHANGE PASSWORD: {e}")

class Title(ctk.CTkLabel):
    def __init__(self, master, text): super().__init__(master,text=text.upper(),font=ctk.CTkFont(size=20,weight="bold"),text_color=TEXT_DARK,fg_color="transparent")
class ErrorLabel(ctk.CTkLabel):
    def __init__(self, master): super().__init__(master,text="",text_color="#b00020",wraplength=560,justify="left",fg_color="transparent")
    def set(self, text): self.configure(text=(text or "").upper())
class LabeledEntry(ctk.CTkFrame):
    def __init__(self, master, label, show=""):
        super().__init__(master,fg_color="transparent"); self.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(self,text=label.upper(),text_color="#333",font=ctk.CTkFont(size=11,weight="bold"),fg_color="transparent").grid(row=0,column=0,sticky="w",padx=2,pady=(0,2))
        self.entry=ctk.CTkEntry(self,show=show,corner_radius=RADIUS,border_color=BORDER,fg_color="white"); self.entry.grid(row=1,column=0,sticky="ew")
    def get(self): return self.entry.get()
    def set(self,v): self.entry.delete(0,"end"); self.entry.insert(0,v)
class SubmitBtn(ctk.CTkButton):
    def __init__(self, master, text, command): super().__init__(master,text=text.upper(),command=command,height=44,corner_radius=RADIUS,fg_color="#f6e8d3",hover_color="#f6e8d3",text_color=TEXT_DARK,border_color=BORDER,border_width=1)
class LinkBtn(ctk.CTkButton):
    def __init__(self, master, text, command): super().__init__(master,text=text.upper(),command=command,height=36,corner_radius=RADIUS,fg_color="transparent",hover_color="#e9dcc6",text_color=LINK_FG)

# ===== Glue: Auth <-> Main =====
def _start_main_app(user_row):
    def back_to_auth(): _launch_auth()
    app=App(on_logout_to_auth=back_to_auth)
    refreshed=app.db.conn.execute("SELECT * FROM users WHERE id=?", (user_row['id'],)).fetchone()
    app.login_ok(refreshed or user_row)
    app.mainloop()

def _launch_auth():
    def on_ok(row):
        auth.destroy(); _start_main_app(row)
    auth=AuthApp(db_path=DB_FILE,left_bg_path=LEFT_BG_PATH,logo_path=LOGO_PATH,on_login_success=on_ok)
    auth.mainloop()

if __name__=="__main__":
    ensure_dirs(); _launch_auth()