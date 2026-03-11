# filename: homewood_cafe.py
# One-file Flask app for "Achi & Friends — Homewood Café"
# Features: SQLite, customer/admin auth, menu (bakery+drinks), toppings, drink customizations,
# pickup/delivery, cart, QR payment placeholder, cozy minimal woody UI (pure CSS from Python).

import io
import os
import uuid
import json
import sqlite3
import datetime
from functools import wraps

from flask import (
    Flask, request, session, redirect, url_for,
    render_template, flash, send_file, g, Response
)
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode
from jinja2 import DictLoader

APP_NAME = "Achi & Friends — Homewood Café"
DB_PATH = "cafe.db"
SECRET_KEY = os.getenv("HOMEWOOD_SECRET", "please-change-me")

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

# -----------------------------
# In-memory templates & CSS (DictLoader)
# -----------------------------
STYLE_CSS = r"""
:root{
  --bg:#f7f3ef;
  --wood:#6b4f3a;
  --accent:#9d7e63;
  --ink:#2a2a2a;
  --muted:#7b7b7b;
  --card:#ffffffcc;
  --radius:14px;
  --shadow:0 10px 30px rgba(0,0,0,.06);
}

/* cozy wood-ish background with gradients only (no images) */
body{
  margin:0; font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
  color:var(--ink);
  background:
    linear-gradient(90deg, #efe5db 12px, transparent 12px) 0 0/44px 100%,
    linear-gradient(#f8f2ec, #efe6dd);
}
a{ color:var(--wood); text-decoration:none }
.container{ max-width:1100px; margin:auto; padding:20px }
.nav{ display:flex; gap:16px; align-items:center; justify-content:space-between; padding:14px 0; }
.brand{ font-weight:700; letter-spacing:.5px; color:var(--wood); font-size:20px }
.card{ background:var(--card); border-radius:var(--radius); box-shadow:var(--shadow); padding:20px; backdrop-filter: blur(8px); }
.grid{ display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:18px }
.btn{ background:var(--wood); color:white; padding:10px 14px; border-radius:10px; border:none; cursor:pointer }
.btn.alt{ background:var(--accent) }
.badge{ background:#0000000f; padding:4px 10px; border-radius:999px; font-size:12px; color:var(--muted) }
.input, select, textarea{ width:100%; padding:10px 12px; border-radius:10px; border:1px solid #0000001a; background:white; }
.table{ width:100%; border-collapse: collapse }
.table th,.table td{ padding:10px; border-bottom:1px solid #00000014; text-align:left }
.footer{ color:var(--muted); text-align:center; padding:30px 0 }
.flash{ background:#fff7e6; border:1px solid #ffe4b3; padding:10px 12px; border-radius:10px; margin:12px 0 }
"""

TEMPLATES = {
"base.html": r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{{ APP_NAME }}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="{{ url_for('static_css') }}" rel="stylesheet">
</head>
<body>
  <div class="container">
    <div class="nav">
      <a class="brand" href="{{ url_for('index') }}">{{ APP_NAME }}</a>
      <div style="display:flex; gap:10px; align-items:center;">
        <a href="{{ url_for('menu') }}">Menu</a>
        <a href="{{ url_for('cart') }}">Cart</a>
        {% if user %}
          {% if user['role']=='admin' %}<a href="{{ url_for('admin_dashboard') }}">Admin</a>{% endif %}
          <span class="badge">Hi, {{ user['username'] }}</span>
          <a href="{{ url_for('logout') }}">Logout</a>
        {% else %}
          <a href="{{ url_for('login') }}">Login</a>
          <a href="{{ url_for('register') }}">Register</a>
        {% endif %}
      </div>
    </div>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for m in messages %}<div class="flash">{{ m }}</div>{% endfor %}
      {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
    <div class="footer">© {{ APP_NAME }} — crafted for cozy moments.</div>
  </div>
</body>
</html>
""",
"index.html": r"""
{% extends "base.html" %}
{% block content %}
  <div class="card">
    <h2>Welcome to {{ APP_NAME }}</h2>
    <p>Chill • Minimal • Homey • Woody. Grab a sweet slice or a custom drink — and make it yours.</p>
  </div>
  <div style="height:12px"></div>
  <div class="grid">
    {% for it in featured %}
    <div class="card">
      <div class="badge">{{ it['category']|capitalize }}</div>
      <h3 style="margin:6px 0">{{ it['name'] }}</h3>
      <div style="color:#555">฿{{ '%.2f'|format(it['base_price']) }}</div>
      <form action="{{ url_for('add_to_cart') }}" method="post" style="margin-top:10px">
        <input type="hidden" name="item_id" value="{{ it['id'] }}">
        <input type="hidden" name="qty" value="1">
        {% if it['is_drink'] %}
          <select name="size" class="input">
            {% for s in SIZES %}<option value="{{ s }}">{{ s }}</option>{% endfor %}
          </select>
        {% endif %}
        <button class="btn" type="submit">Add</button>
      </form>
    </div>
    {% endfor %}
  </div>
{% endblock %}
""",
"auth_login.html": r"""
{% extends "base.html" %}
{% block content %}
<div class="card" style="max-width:480px; margin:auto">
  <h3>Login</h3>
  <form method="post">
    <label>Username</label>
    <input class="input" name="username" required>
    <label>Password</label>
    <input class="input" type="password" name="password" required>
    <div style="height:10px"></div>
    <button class="btn" type="submit">Login</button>
  </form>
  <div style="height:10px"></div>
  <a href="{{ url_for('register') }}">Create a customer account</a>
</div>
{% endblock %}
""",
"auth_register.html": r"""
{% extends "base.html" %}
{% block content %}
<div class="card" style="max-width:480px; margin:auto">
  <h3>Create Account</h3>
  <form method="post">
    <label>Username</label>
    <input class="input" name="username" required>
    <label>Password</label>
    <input class="input" type="password" name="password" required>
    <div style="height:10px"></div>
    <button class="btn" type="submit">Register</button>
  </form>
</div>
{% endblock %}
""",
"menu.html": r"""
{% extends "base.html" %}
{% block content %}
<div class="card">
  <h2>Menu</h2>
  <p class="badge">Customize drinks: sweetness • syrup • ice • milk (only milk-drinks) • size | Add toppings to drinks/bakery</p>
  <div style="height:10px"></div>

  <div class="grid">
    {% for it in items %}
      <div class="card">
        <div class="badge">{{ it['category']|capitalize }}</div>
        <h3 style="margin:6px 0">{{ it['name'] }}</h3>
        <div style="color:#555">Base: ฿{{ '%.2f'|format(it['base_price']) }}</div>
        <form action="{{ url_for('add_to_cart') }}" method="post" style="margin-top:8px">
          <input type="hidden" name="item_id" value="{{ it['id'] }}">
          <label>Qty</label>
          <input class="input" type="number" min="1" name="qty" value="1">
          
          {% if it['is_drink'] %}
          <label>Size</label>
          <select name="size" class="input">
            {% for s in SIZES %}<option value="{{ s }}">{{ s }}</option>{% endfor %}
          </select>
          <label>Sweetness</label>
          <select name="sweetness" class="input">
            {% for s in SWEET_LEVELS %}<option value="{{ s }}">{{ s }}</option>{% endfor %}
          </select>
          <label>Syrup</label>
          <select name="syrup" class="input">
            {% for s in SYRUPS %}<option value="{{ s }}">{{ s }}</option>{% endfor %}
          </select>
          <label>Ice</label>
          <select name="ice" class="input">
            {% for s in ICE_LEVELS %}<option value="{{ s }}">{{ s }}</option>{% endfor %}
          </select>
          {% if it['name'] in MILK_DRINK_NAMES %}
          <label>Milk</label>
          <select name="milk" class="input">
            {% for s in MILKS %}<option value="{{ s }}">{{ s }}</option>{% endfor %}
          </select>
          {% endif %}
          {% endif %}

          <label>Toppings</label>
          <div style="display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap:8px">
            {% for t in toppings %}
              {% if t['applies_to'] in ('both', 'drink' if it['is_drink'] else 'bakery') %}
              <label style="display:flex; gap:8px; align-items:center;">
                <input type="checkbox" name="toppings" value="{{ t['id'] }}">
                <span>{{ t['name'] }} (฿{{ '%.0f'|format(t['price']) }})</span>
              </label>
              {% endif %}
            {% endfor %}
          </div>

          <div style="height:10px"></div>
          <button class="btn" type="submit">Add to Cart</button>
        </form>
      </div>
    {% endfor %}
  </div>
</div>
{% endblock %}
""",
"cart.html": r"""
{% extends "base.html" %}
{% block content %}
<div class="card">
  <h2>Your Cart</h2>
  {% if not cart %}
    <p>Cart is empty. <a href="{{ url_for('menu') }}">Browse menu</a></p>
  {% else %}
  <form method="post" action="{{ url_for('cart_update') }}">
    <table class="table">
      <thead><tr><th>Item</th><th>Options</th><th>Qty</th><th>Price</th><th>Subtotal</th><th></th></tr></thead>
      <tbody>
        {% for l in cart %}
        <tr>
          <td>
            <div><strong>{{ l.name }}</strong> <span class="badge">{{ l.category|capitalize }}</span></div>
            {% if l.toppings and l.toppings|length %}
              <div style="font-size:12px; color:#555">Toppings:
                {{ l.toppings | map(attribute='name') | join(', ') }}
              </div>
            {% endif %}
          </td>
          <td style="font-size:12px; color:#555">
            {% if l.is_drink %}
              Size: {{ l.drink_opts.size }} |
              Sweet: {{ l.drink_opts.sweetness }} |
              Syrup: {{ l.drink_opts.syrup }} |
              Ice: {{ l.drink_opts.ice }} |
              Milk: {{ l.drink_opts.milk }}
            {% else %}-{% endif %}
          </td>
          <td>
            <input class="input" type="number" name="qty_{{ l.line_id }}" min="1" value="{{ l.qty }}" style="width:80px">
          </td>
          <td>฿{{ "%.2f"|format(l.unit_price) }}</td>
          <td>฿{{ "%.2f"|format(l.subtotal) }}</td>
          <td><a class="btn alt" href="{{ url_for('cart_delete', line_id=l.line_id) }}">Delete</a></td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    <div style="display:flex; justify-content:space-between; align-items:center;">
      <button class="btn" type="submit">Update Cart</button>
      <div><strong>Total: ฿{{ "%.2f"|format(total) }}</strong></div>
    </div>
  </form>
  <div style="height:10px"></div>
  <a class="btn" href="{{ url_for('checkout') }}">Proceed to Checkout</a>
  {% endif %}
</div>
{% endblock %}
""",
"checkout.html": r"""
{% extends "base.html" %}
{% block content %}
<div class="card">
  <h2>Checkout</h2>
  <p>Total: <strong>฿{{ "%.2f"|format(total) }}</strong></p>
  <form method="post">
    <label>Receive method</label>
    <select class="input" name="method" id="method">
      <option value="pickup">Pickup at café</option>
      <option value="delivery">Delivery</option>
    </select>
    <div id="addr" style="display:none">
      <label>Delivery address</label>
      <textarea class="input" name="address" placeholder="Address"></textarea>
    </div>
    <label>Phone</label>
    <input class="input" name="phone" placeholder="08x-xxx-xxxx">
    <div style="height:10px"></div>
    <button class="btn" type="submit">Place Order & Pay</button>
  </form>
</div>
<script>
  const m = document.getElementById('method');
  const a = document.getElementById('addr');
  function toggleAddr(){ a.style.display = m.value==='delivery' ? 'block':'none'; }
  m.addEventListener('change', toggleAddr); toggleAddr();
</script>
{% endblock %}
""",
"order_success.html": r"""
{% extends "base.html" %}
{% block content %}
<div class="card" style="text-align:center">
  <h2>Order placed! 🎉</h2>
  <p>Order ID: <strong>{{ order['id'] }}</strong></p>
  <p>Amount: <strong>฿{{ "%.2f"|format(order['total']) }}</strong></p>
  <p>Scan the bank QR to pay:</p>
  <img src="{{ url_for('qr', order_id=order['id']) }}" alt="Bank QR" style="max-width:260px; width:100%; border-radius:12px; box-shadow: var(--shadow);">
  <p class="badge">Method: {{ order['method']|capitalize }}</p>
  {% if order['address'] %}<p style="color:#555">Address: {{ order['address'] }}</p>{% endif %}
  <p>We’ll confirm your payment at the counter/admin. Thank you!</p>
</div>
{% endblock %}
""",
"admin_dashboard.html": r"""
{% extends "base.html" %}
{% block content %}
<div class="card">
  <h2>Admin — Dashboard</h2>
  <div class="grid">
    <div class="card"><h3>Users</h3><div style="font-size:28px">{{ stats.users }}</div></div>
    <div class="card"><h3>Items</h3><div style="font-size:28px">{{ stats.items }}</div></div>
    <div class="card"><h3>Toppings</h3><div style="font-size:28px">{{ stats.toppings }}</div></div>
    <div class="card"><h3>Orders</h3><div style="font-size:28px">{{ stats.orders }}</div></div>
    <div class="card"><h3>Sales (฿)</h3><div style="font-size:28px">{{ "%.2f"|format(stats.sales) }}</div></div>
  </div>
</div>

<div class="card" style="margin-top:12px">
  <h3>Latest Orders</h3>
  <table class="table">
    <thead><tr><th>Time</th><th>Order ID</th><th>Total</th><th>Method</th><th>Status</th><th>Action</th></tr></thead>
    <tbody>
      {% for o in latest %}
      <tr>
        <td>{{ o['created_at'] }}</td>
        <td>{{ o['id'] }}</td>
        <td>฿{{ "%.2f"|format(o['total']) }}</td>
        <td>{{ o['method'] }}</td>
        <td>{{ o['status'] }}</td>
        <td>
          <form method="post" action="{{ url_for('admin_order_status', order_id=o['id']) }}" style="display:flex; gap:8px">
            <select name="status" class="input">
              <option {{ 'selected' if o['status']=='pending' }}>pending</option>
              <option {{ 'selected' if o['status']=='paid' }}>paid</option>
              <option {{ 'selected' if o['status']=='preparing' }}>preparing</option>
              <option {{ 'selected' if o['status']=='ready' }}>ready</option>
              <option {{ 'selected' if o['status']=='delivering' }}>delivering</option>
              <option {{ 'selected' if o['status']=='completed' }}>completed</option>
              <option {{ 'selected' if o['status']=='cancelled' }}>cancelled</option>
            </select>
            <button class="btn" type="submit">Update</button>
          </form>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
""",
"admin_items.html": r"""
{% extends "base.html" %}
{% block content %}
<div class="card">
  <h2>Admin — Items</h2>
  <form method="post" style="display:grid; grid-template-columns:1fr 1fr 1fr 1fr auto; gap:8px">
    <input class="input" name="name" placeholder="Name" required>
    <select name="category" class="input">
      <option>cake</option><option>cookie</option><option>bread</option><option>tart</option><option>pie</option>
      <option>coffee</option><option>tea</option><option>chocolate</option><option>soda</option><option>juice</option><option>non-caffeine</option>
    </select>
    <input class="input" type="number" step="0.01" name="price" placeholder="Base Price" required>
    <label style="display:flex; align-items:center; gap:6px"><input type="checkbox" name="is_drink"> Is drink?</label>
    <button class="btn" type="submit">Add</button>
  </form>
</div>

<div class="card" style="margin-top:12px">
  <table class="table">
    <thead><tr><th>Name</th><th>Category</th><th>Price</th><th>Drink?</th><th>Available</th><th></th></tr></thead>
    <tbody>
      {% for it in items %}
      <tr>
        <td>{{ it['name'] }}</td>
        <td>{{ it['category'] }}</td>
        <td>฿{{ "%.2f"|format(it['base_price']) }}</td>
        <td>{{ 'Yes' if it['is_drink'] else 'No' }}</td>
        <td>{{ 'Yes' if it['available'] else 'No' }}</td>
        <td><a class="btn alt" href="{{ url_for('admin_items_toggle', item_id=it['id']) }}">Toggle</a></td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
""",
"admin_users.html": r"""
{% extends "base.html" %}
{% block content %}
<div class="card">
  <h2>Admin — Users</h2>
  <form method="post" style="display:grid; grid-template-columns:1fr 1fr 1fr auto; gap:8px">
    <input class="input" name="username" placeholder="username" required>
    <input class="input" name="password" placeholder="password" required>
    <select name="role" class="input"><option value="customer">customer</option><option value="admin">admin</option></select>
    <button class="btn" type="submit">Create</button>
  </form>
</div>

<div class="card" style="margin-top:12px">
  <table class="table">
    <thead><tr><th>ID</th><th>Username</th><th>Role</th></tr></thead>
    <tbody>
      {% for u in users %}
      <tr><td>{{ u['id'] }}</td><td>{{ u['username'] }}</td><td>{{ u['role'] }}</td></tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
"""
}

app.jinja_loader = DictLoader(TEMPLATES)

# Serve CSS from memory (no files needed)
@app.route("/static/style.css")
def static_css():
    return Response(STYLE_CSS, mimetype="text/css")

# -----------------------------
# DB helpers
# -----------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(_=None):
    db = g.pop("db", None)
    if db:
        db.close()

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('customer','admin'))
    );

    CREATE TABLE IF NOT EXISTS items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        base_price REAL NOT NULL,
        is_drink INTEGER NOT NULL DEFAULT 0,
        available INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS toppings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        applies_to TEXT NOT NULL CHECK(applies_to IN ('drink','bakery','both'))
    );

    CREATE TABLE IF NOT EXISTS orders(
        id TEXT PRIMARY KEY,
        user_id INTEGER,
        cart_json TEXT NOT NULL,
        total REAL NOT NULL,
        method TEXT NOT NULL,
        address TEXT,
        phone TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    db.commit()

def seed_data():
    db = get_db()
    # admin account
    if not db.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
        db.execute(
            "INSERT INTO users(username,password_hash,role) VALUES (?,?,?)",
            ("admin", generate_password_hash("admin123"), "admin")
        )

    def add_item(name, category, price, is_drink):
        db.execute("INSERT INTO items(name,category,base_price,is_drink) VALUES (?,?,?,?)",
                   (name, category, price, 1 if is_drink else 0))

    if not db.execute("SELECT 1 FROM items").fetchone():
        # Bakery
        add_item("Classic Butter Cake", "cake", 85, False)
        add_item("Chocolate Fudge Cake", "cake", 95, False)
        add_item("Strawberry Shortcake", "cake", 105, False)
        add_item("Almond Cookies", "cookie", 55, False)
        add_item("Choco Chunk Cookies", "cookie", 60, False)
        add_item("Brioche Bread", "bread", 65, False)
        add_item("Garlic Butter Bread", "bread", 70, False)
        add_item("Lemon Tart", "tart", 90, False)
        add_item("Blueberry Tart", "tart", 95, False)
        add_item("Apple Pie", "pie", 95, False)

        # Drinks — caffeine
        add_item("Americano", "coffee", 65, True)
        add_item("Cappuccino", "coffee", 75, True)
        add_item("Latte", "coffee", 75, True)
        add_item("Mocha", "coffee", 85, True)
        add_item("Espresso", "coffee", 60, True)
        add_item("Green Tea Latte", "tea", 75, True)
        add_item("Thai Tea Latte", "tea", 70, True)
        add_item("Chocolate (Hot/Iced)", "chocolate", 70, True)

        # Drinks — fruity / soda / non-caffeine
        add_item("Yuzu Soda", "soda", 75, True)
        add_item("Strawberry Soda", "soda", 70, True)
        add_item("Lemon Soda", "soda", 65, True)
        add_item("Lime Soda", "soda", 65, True)
        add_item("Blueberry Soda", "soda", 75, True)
        add_item("Orange Juice", "juice", 65, True)
        add_item("Yuzu Juice", "juice", 75, True)
        add_item("Strawberry Juice", "juice", 70, True)
        add_item("Lemon Juice", "juice", 60, True)
        add_item("Lime Juice", "juice", 60, True)
        add_item("Blueberry Juice", "juice", 75, True)
        add_item("Milk (Hot/Iced)", "non-caffeine", 60, True)

    if not db.execute("SELECT 1 FROM toppings").fetchone():
        db.executemany(
            "INSERT INTO toppings(name,price,applies_to) VALUES (?,?,?)",
            [
                ("Whipped Cream", 10, "both"),
                ("Extra Shot Espresso", 20, "drink"),
                ("Caramel Drizzle", 15, "drink"),
                ("Chocolate Drizzle", 15, "both"),
                ("Oreo Crumbs", 15, "both"),
                ("Almond Flakes", 15, "both"),
                ("Boba Pearls", 20, "drink"),
                ("Jelly Cubes", 15, "drink"),
                ("Cheese Foam", 25, "drink"),
                ("Fresh Strawberries", 25, "bakery"),
            ]
        )
    db.commit()

@app.before_request
def ensure_db():
    init_db()
    seed_data()

# -----------------------------
# Auth helpers
# -----------------------------
def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    db = get_db()
    return db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                flash("Please log in.")
                return redirect(url_for("login"))
            if role and user["role"] != role:
                flash("Not authorized.")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return wrapped
    return decorator

# -----------------------------
# Cart utilities (session)
# -----------------------------
def get_cart():
    return session.setdefault("cart", [])

def save_cart(cart):
    session["cart"] = cart

def cart_total(cart):
    return sum(line["subtotal"] for line in cart)

# -----------------------------
# Routes — Public
# -----------------------------
@app.route("/")
def index():
    user = current_user()
    db = get_db()
    featured = db.execute("SELECT * FROM items WHERE available=1 ORDER BY RANDOM() LIMIT 8").fetchall()
    return render_template("index.html", user=user, featured=featured)

@app.route("/menu")
def menu():
    user = current_user()
    db = get_db()
    cat = request.args.get("category")
    if cat:
        items = db.execute("SELECT * FROM items WHERE available=1 AND category=? ORDER BY name", (cat,)).fetchall()
    else:
        items = db.execute("SELECT * FROM items WHERE available=1 ORDER BY category, name").fetchall()
    toppings_all = db.execute("SELECT * FROM toppings ORDER BY name").fetchall()
    return render_template("menu.html", user=user, items=items, toppings=toppings_all)

@app.route("/add-to-cart", methods=["POST"])
def add_to_cart():
    db = get_db()
    item_id = int(request.form["item_id"])
    qty = max(1, int(request.form.get("qty", 1)))
    item = db.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if not item or not item["available"]:
        flash("Item not available.")
        return redirect(url_for("menu"))

    # Customization
    is_drink = bool(item["is_drink"])
    # toppings
    toppings_ids = [int(t) for t in request.form.getlist("toppings")]
    chosen_toppings = []
    toppings_total = 0.0
    for t_id in toppings_ids:
        t = db.execute("SELECT * FROM toppings WHERE id=?", (t_id,)).fetchone()
        if t and (t["applies_to"] in ("both", "drink" if is_drink else "bakery")):
            chosen_toppings.append({"id": t["id"], "name": t["name"], "price": float(t["price"])})
            toppings_total += float(t["price"])

    drink_opts = {}
    size_up = 0
    if is_drink:
        # Only some drinks are milk-drinks
        milk_val = request.form.get("milk", "none") if item["name"] in MILK_DRINK_NAMES else "none"
        drink_opts = {
            "sweetness": request.form.get("sweetness", "normal"),
            "syrup": request.form.get("syrup", "none"),
            "ice": request.form.get("ice", "normal"),
            "milk": milk_val,
            "size": request.form.get("size", "M")
        }
        size_up = {"S": 0, "M": 0, "L": 10}.get(drink_opts["size"], 0)

    unit_price = float(item["base_price"]) + toppings_total + size_up
    line = {
        "line_id": str(uuid.uuid4()),
        "item_id": item["id"],
        "name": item["name"],
        "category": item["category"],
        "is_drink": is_drink,
        "qty": qty,
        "unit_price": unit_price,
        "toppings": chosen_toppings,
        "drink_opts": drink_opts,
        "subtotal": unit_price * qty
    }

    cart = get_cart()
    cart.append(line)
    save_cart(cart)
    flash(f"Added {qty} × {item['name']} to cart.")
    return redirect(url_for("cart"))

@app.route("/cart")
def cart():
    user = current_user()
    cart = get_cart()
    total = cart_total(cart)
    return render_template("cart.html", user=user, cart=cart, total=total)

@app.route("/cart/delete/<line_id>")
def cart_delete(line_id):
    cart = get_cart()
    cart = [l for l in cart if l["line_id"] != line_id]
    save_cart(cart)
    flash("Item removed.")
    return redirect(url_for("cart"))

@app.route("/cart/update", methods=["POST"])
def cart_update():
    cart = get_cart()
    for l in cart:
        new_qty = int(request.form.get(f"qty_{l['line_id']}", l["qty"]))
        l["qty"] = max(1, new_qty)
        l["subtotal"] = l["unit_price"] * l["qty"]
    save_cart(cart)
    flash("Cart updated.")
    return redirect(url_for("cart"))

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    user = current_user()
    cart = get_cart()
    if not cart:
        flash("Your cart is empty.")
        return redirect(url_for("menu"))

    if request.method == "POST":
        method = request.form.get("method", "pickup")
        address = request.form.get("address") if method == "delivery" else ""
        phone = request.form.get("phone", "")
        total = round(cart_total(cart), 2)

        order_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]
        db = get_db()
        db.execute(
            "INSERT INTO orders(id,user_id,cart_json,total,method,address,phone,status,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (order_id, user["id"] if user else None, json.dumps(cart), total, method, address, phone, "pending", datetime.datetime.now().isoformat())
        )
        db.commit()

        session["last_order_id"] = order_id
        save_cart([])
        return redirect(url_for("order_success"))

    total = round(cart_total(cart), 2)
    return render_template("checkout.html", user=user, cart=cart, total=total)

@app.route("/order/success")
def order_success():
    user = current_user()
    order_id = session.get("last_order_id")
    if not order_id:
        return redirect(url_for("index"))
    db = get_db()
    order = db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not order:
        return redirect(url_for("index"))
    return render_template("order_success.html", user=user, order=order)

# Generate a bank QR (placeholder string — replace with your real bank/PromptPay payload)
@app.route("/qr/<order_id>.png")
def qr(order_id):
    db = get_db()
    o = db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not o:
        return "Not found", 404
    amount = float(o["total"])
    payload = f"BANK:HOMEWOOD|ACC:1234567890|ORDER:{order_id}|AMOUNT:{amount:.2f}|CURRENCY:THB"
    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

# -----------------------------
# Auth
# -----------------------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        db = get_db()
        u = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if u and check_password_hash(u["password_hash"], password):
            session["user_id"] = u["id"]
            flash("Welcome back!")
            return redirect(url_for("index"))
        flash("Invalid credentials.")
    return render_template("auth_login.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        db = get_db()
        if db.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            flash("Username already taken.")
            return redirect(url_for("register"))
        db.execute("INSERT INTO users(username,password_hash,role) VALUES (?,?,?)",
                   (username, generate_password_hash(password), "customer"))
        db.commit()
        flash("Registered! Please log in.")
        return redirect(url_for("login"))
    return render_template("auth_register.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out.")
    return redirect(url_for("index"))

# -----------------------------
# Admin
# -----------------------------
@app.route("/admin")
@login_required(role="admin")
def admin_dashboard():
    db = get_db()
    stats = {
        "users": db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"],
        "items": db.execute("SELECT COUNT(*) c FROM items").fetchone()["c"],
        "toppings": db.execute("SELECT COUNT(*) c FROM toppings").fetchone()["c"],
        "orders": db.execute("SELECT COUNT(*) c FROM orders").fetchone()["c"],
        "sales": db.execute("SELECT IFNULL(SUM(total),0) s FROM orders WHERE status!='cancelled'").fetchone()["s"],
    }
    latest = db.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 10").fetchall()
    return render_template("admin_dashboard.html", stats=stats, latest=latest)

@app.route("/admin/items", methods=["GET","POST"])
@login_required(role="admin")
def admin_items():
    db = get_db()
    if request.method == "POST":
        name = request.form["name"].strip()
        category = request.form["category"]
        price = float(request.form["price"])
        is_drink = 1 if request.form.get("is_drink") == "on" else 0
        db.execute("INSERT INTO items(name,category,base_price,is_drink) VALUES (?,?,?,?)",
                   (name, category, price, is_drink))
        db.commit()
        flash("Item added.")
        return redirect(url_for("admin_items"))
    items = db.execute("SELECT * FROM items ORDER BY category,name").fetchall()
    return render_template("admin_items.html", items=items)

@app.route("/admin/items/toggle/<int:item_id>")
@login_required(role="admin")
def admin_items_toggle(item_id):
    db = get_db()
    it = db.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if not it:
        flash("Not found.")
        return redirect(url_for("admin_items"))
    new_avail = 0 if it["available"] else 1
    db.execute("UPDATE items SET available=? WHERE id=?", (new_avail, item_id))
    db.commit()
    flash("Availability updated.")
    return redirect(url_for("admin_items"))

@app.route("/admin/users", methods=["GET","POST"])
@login_required(role="admin")
def admin_users():
    db = get_db()
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        role = request.form["role"]
        db.execute("INSERT INTO users(username,password_hash,role) VALUES (?,?,?)",
                   (username, generate_password_hash(password), role))
        db.commit()
        flash("User created.")
        return redirect(url_for("admin_users"))
    users = db.execute("SELECT id,username,role FROM users ORDER BY role,username").fetchall()
    return render_template("admin_users.html", users=users)

@app.route("/admin/orders/<order_id>/status", methods=["POST"])
@login_required(role="admin")
def admin_order_status(order_id):
    status = request.form["status"]
    db = get_db()
    db.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    db.commit()
    flash("Order status updated.")
    return redirect(url_for("admin_dashboard"))

# -----------------------------
# Constants & template globals
# -----------------------------
SWEET_LEVELS = ["zero", "25%", "50%", "75%", "normal", "125%"]
SYRUPS = ["none", "caramel", "vanilla", "hazelnut", "yuzu", "strawberry", "blueberry"]
ICE_LEVELS = ["no ice", "less", "normal", "extra"]
MILKS = ["dairy", "oat", "almond", "soy"]
SIZES = ["S", "M", "L"]

# Names of drinks that logically offer milk choice
MILK_DRINK_NAMES = {
    "Latte", "Cappuccino", "Mocha",
    "Green Tea Latte", "Thai Tea Latte",
    "Chocolate (Hot/Iced)", "Milk (Hot/Iced)"
}

@app.context_processor
def inject_globals():
    return dict(
        APP_NAME=APP_NAME,
        SWEET_LEVELS=SWEET_LEVELS,
        SYRUPS=SYRUPS,
        ICE_LEVELS=ICE_LEVELS,
        MILKS=MILKS,
        SIZES=SIZES,
        MILK_DRINK_NAMES=MILK_DRINK_NAMES
    )

# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
