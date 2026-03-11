import sys, os, sqlite3, hashlib, shutil
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *

# ❗ (เพิ่ม Imports สำหรับฟีเจอร์ใหม่)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox, QHBoxLayout,
    QFrame, QSizePolicy, QGraphicsDropShadowEffect, QScrollArea, QGridLayout,
    QTableWidget, QHeaderView, QTableWidgetItem, QAbstractItemView, QTextEdit,
    QStackedWidget, QMainWindow,
    QComboBox, QSpinBox, QDialog  # (เพิ่ม QDialog)
)
from PyQt6.QtGui import (
    QFont, QPixmap, QColor, QResizeEvent, QBitmap, QPainter, QIntValidator, 
    QRegularExpressionValidator
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QRect, QRegularExpression, QSize, QDateTime # (เพิ่ม QDateTime)
)

# ❗ (เพิ่ม Import สำหรับการพิมพ์)
try:
    from PyQt6.QtPrintSupport import QPrintPreviewDialog, QPrinter
except ImportError:
    print("Warning: PyQt6.QtPrintSupport module not found. Printing will be disabled.")


# =========================
# 🔹 Database Helper (Users)
# =========================
def ensure_profile_pic_column():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cur.fetchall()]
    if "profile_pic" not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN profile_pic TEXT")
        conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_user_database(db_path="users.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT,
            last_name TEXT,
            username TEXT UNIQUE,
            password TEXT,
            email TEXT,
            phone TEXT,
            profile_pic TEXT 
        )
    """)
    conn.commit()

    cur.execute("SELECT * FROM users WHERE username='admin'")
    if cur.fetchone() is None:
        cur.execute("""
            INSERT INTO users (first_name, last_name, username, password, email, phone)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "System", "Administrator", "admin",
            hash_password("12345678"), "admin@shop.com", "0000000000"
        ))
        conn.commit()
        print("✅ Admin account created: username='admin', password='12345678'")

    conn.close()
    ensure_profile_pic_column() # (ย้ายมาเรียกหลัง init)

# =========================
# 🔹 Database Helper (Orders) - (เพิ่มใหม่)
# =========================
def init_orders_database(db_path="orders.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # 1. ตารางเก็บคำสั่งซื้อหลัก
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'Pending Payment',
            slip_image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 2. ตารางเก็บรายการสินค้าในคำสั่งซื้อนั้นๆ
    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            size TEXT,
            quantity INTEGER NOT NULL,
            price_per_item REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (id)
        )
    """)
    
    conn.commit()
    conn.close()


# =========================
# 🔹 Sidebar
# =========================
class Sidebar(QFrame):
    menu_clicked = pyqtSignal(str)

    def __init__(self, image_folder):
        super().__init__()
        self.image_folder = image_folder
        self.initUI()

    def initUI(self):
        self.setFixedHeight(80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("""
            QFrame {
                background-color: #1a0033;
                border: none;
                color: white;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(25, 10, 25, 10)
        layout.setSpacing(25)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        logo_label = QLabel()
        logo_path = os.path.join(self.image_folder, "logo.png")
        if os.path.exists(logo_path):
            logo_pix = QPixmap(logo_path)
            logo_label.setPixmap(
                logo_pix.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation)
            )
        else:
            logo_label.setText("Logo")
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)

        shop_label = QLabel("Arai Football Shop")
        shop_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        shop_label.setStyleSheet("color: white;")
        layout.addWidget(shop_label)

        layout.addStretch()

        # ❗ (เพิ่ม "Orders")
        menu_items = ["Homepage", "Products", "Cart", "Orders", "Contact",
                      "Contact Admin", "Profile", "Login", "Logout"]

        self.buttons = {}
        for item in menu_items:
            btn = QPushButton(item)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.setFont(QFont("Segoe UI", 11))
            btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    padding: 8px 14px;
                    border-radius: 6px;
                    color: white;
                    background-color: transparent;
                }
                QPushButton:hover {
                    background-color: #5b5b58;
                }
                QPushButton:checked {
                    background-color: #004aad;
                    color: white;
                    font-weight: bold;
                }
            """)
            btn.clicked.connect(lambda checked, b=btn, name=item: self.handle_menu_click(b, name))
            self.buttons[item] = btn
            layout.addWidget(btn)

    def handle_menu_click(self, btn, name):
        for b in self.buttons.values():
            if b is not btn:
                b.setChecked(False)
        btn.setChecked(True)
        self.menu_clicked.emit(name)


# =========================
# 🔹 Home Page
# =========================
class HomePage(QWidget):
    def __init__(self, image_folder):
        super().__init__()
        self.image_folder = image_folder
        self.initUI()

    def initUI(self):
        self.bg_label = QLabel(self) 
        self.bg_label.setScaledContents(True)
        bg_path = "C:/project/picture/145.png" 
        
        if os.path.exists(bg_path):
            self.bg_label.setPixmap(QPixmap(bg_path)) 
        else:
            self.bg_label.setStyleSheet("background-color: #f0f0f0;")
            print(f"Warning: ไม่พบรูปพื้นหลัง {bg_path}")
        
        layout = QVBoxLayout(self)
        
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter) 
        
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20) 
        self.setStyleSheet("background-color: transparent; border: none;") 

        layout.addSpacing(250) 

        best_sellers = [
            ("Manchater united", "฿3,000", "miami.png"),
            ("Liverpool", "฿2,500", "liverpool.png"),
            ("Inter maimi", "฿2,800", "newcastle.png"),
        ]

        grid = QHBoxLayout()
        grid.setSpacing(40) 
        grid.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for name, price, img_filename in best_sellers: 
            card = QFrame()
            card.setFixedSize(280, 370)
            
            card.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 0.95);
                    border-radius: 18px;
                    border: 1px solid #e0e0e0;
                }
            """)
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(20)
            shadow.setXOffset(0)
            shadow.setYOffset(4)
            shadow.setColor(QColor(0, 0, 0, 60))
            card.setGraphicsEffect(shadow)
            
            v = QVBoxLayout(card)
            v.setContentsMargins(10, 10, 10, 10)
            v.setAlignment(Qt.AlignmentFlag.AlignTop)
            v.setSpacing(10)

            pic = QLabel()
            img_path = os.path.join(self.image_folder, img_filename) 
            
            if os.path.exists(img_path):
                pix = QPixmap(img_path).scaled(240, 240, Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation)
                pic.setPixmap(pix)
            else:
                pic.setStyleSheet("background-color: #e0e0e0; border: 1px dashed #888;") 
                print(f"Warning: ไม่พบรูปสินค้า {img_path}")
            
            pic.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.addWidget(pic) 

            lbl_name = QLabel(name)
            lbl_name.setFont(QFont("Tex Gyre Adventor", 14, QFont.Weight.Bold))
            lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_name.setStyleSheet("color: #004aad; border: none; background: transparent;")

            lbl_price = QLabel(price)
            lbl_price.setFont(QFont("Tex Gyre Adventor", 13, QFont.Weight.Bold))
            lbl_price.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_price.setStyleSheet("color: #ff0000; border: none; background: transparent;")

            v.addWidget(lbl_name)
            v.addWidget(lbl_price)
            grid.addWidget(card)

        layout.addLayout(grid)
        layout.addStretch() 

        self.setLayout(layout)
        self.bg_label.lower() 
        
    def resizeEvent(self, event: QResizeEvent):
        if hasattr(self, 'bg_label'):
            self.bg_label.resize(self.size())
            self.bg_label.setPixmap(QPixmap("C:/project/picture/145.png").scaled(
                self.size(), 
                Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                Qt.TransformationMode.SmoothTransformation
            ))
        super().resizeEvent(event)


# =========================
# 🔹 Products Page
# =========================
# =========================
# 🔹 Products Page
# =========================
class ProductsPage(QWidget):
    add_to_cart_signal = pyqtSignal(dict)
    view_details_signal = pyqtSignal(dict) 
    
    def __init__(self, image_folder, db_path="products.db"):
        super().__init__()
        self.image_folder = image_folder
        self.db_path = db_path
        self.products = []
        self.init_database() 
        self.load_products() 
        self.initUI()

    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # ❗ (แก้ไข) เพิ่ม quantity (INTEGER DEFAULT 10)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                image_path TEXT,
                price TEXT,
                description TEXT,
                quantity INTEGER DEFAULT 10 
            )
        """)
        conn.commit()

        cur.execute("PRAGMA table_info(products)")
        columns = [col[1] for col in cur.fetchall()]
        if "price" not in columns:
            cur.execute("ALTER TABLE products ADD COLUMN price TEXT")
        if "description" not in columns:
            cur.execute("ALTER TABLE products ADD COLUMN description TEXT")
        
        # ❗ (แก้ไข) เพิ่มการตรวจสอบและเพิ่มคอลัมน์ quantity ถ้ายังไม่มี
        if "quantity" not in columns:
            cur.execute("ALTER TABLE products ADD COLUMN quantity INTEGER DEFAULT 10")
            
        conn.commit()

    def load_products(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        # ❗ (แก้ไข) เลือก quantity ออกมาด้วย
        cur.execute("SELECT id, name, image_path, price, description, quantity FROM products")
        self.products = cur.fetchall()
        conn.close()

    def initUI(self):
        # ... (โค้ดส่วน initUI, search_layout, scroll area เหมือนเดิม) ...
        # (ขอข้ามส่วนที่ไม่แก้นะครับ)
        
        self.setStyleSheet("background-color: #f5f5f5;") 
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("ค้นหาเสื้อ...")
        self.search_input.setFont(QFont("Arial", 14))
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #ccc;
                border-radius: 15px;
                background-color: white;
            }
        """)
        self.search_input.textChanged.connect(self.filter_products)
        
        search_btn = QPushButton("ค้นหา")
        search_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #004aad;
                color: white;
                padding: 8px 20px;
                border-radius: 15px;
            }
            QPushButton:hover { background-color: #003580; }
        """)
        search_btn.clicked.connect(self.filter_products)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background-color: transparent; 
            }
            QScrollBar:vertical {
                border: none;
                background: #f5f5f5;
                width: 10px; 
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #cccccc;
                border-radius: 5px; 
                min-height: 25px; 
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: #004aad;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
                border: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """) 
        
        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet("background-color: transparent;")
        
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setSpacing(25) 
        scroll.setWidget(self.grid_widget)
        layout.addWidget(scroll)

        self.product_widgets = []
        self.display_products(self.products)

    def display_products(self, products):
        for i in reversed(range(self.grid.count())):
            item = self.grid.itemAt(i)
            w = item.widget() if item else None
            if w:
                w.setParent(None)
        self.product_widgets.clear()

        # ❗ (แก้ไข) เพิ่ม quantity (ตัวแปรที่ 6)
        for i, (prod_id, name, image_path, price, description, quantity) in enumerate(products):
            
            card = QFrame()
            card.setFixedSize(240, 420) # ❗ (แก้ไข) เพิ่มความสูงของการ์ดเล็กน้อย
            card.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border-radius: 10px;
                    border: 1px solid #f0f0f0; 
                }
                QFrame:hover {
                    border: 2px solid #004aad; 
                }
            """)
            
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(25) 
            shadow.setXOffset(0)
            shadow.setYOffset(4) 
            shadow.setColor(QColor(0, 0, 0, 60)) 
            card.setGraphicsEffect(shadow)

            v_layout = QVBoxLayout(card)
            v_layout.setContentsMargins(10, 10, 10, 10)
            v_layout.setSpacing(10)
            v_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            pic_btn = QPushButton()
            pic_btn.setFixedSize(220, 220)
            pic_btn.setIconSize(QSize(220, 220)) 
            pic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            pic_btn.setStyleSheet("border: none; background-color: transparent;")
            
            full_path = os.path.join(self.image_folder, image_path)
            
            if os.path.exists(full_path):
                pix = QPixmap(full_path)
                scaled = pix.scaled(220, 220, Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)
                pic_btn.setIcon(QIcon(scaled))
            else:
                pic_btn.setText(f"ไม่พบรูป\n{image_path}")
                
            v_layout.addWidget(pic_btn)

            name_label = QLabel(name)
            name_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            name_label.setStyleSheet("""
                color: #333;
                border: none;
                background-color: transparent;
            """)
            name_label.setWordWrap(True) 
            v_layout.addWidget(name_label)

            price_label = QLabel(price)
            price_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
            price_label.setStyleSheet("color: #e74c3c; border: none; background-color: transparent;")
            v_layout.addWidget(price_label)

            # ❗ (เพิ่ม) Label สำหรับแสดงสต็อก
            quantity_label = QLabel()
            quantity_label.setFont(QFont("Arial", 11))
            if quantity > 0:
                quantity_label.setText(f"สต็อก: {quantity} ชิ้น")
                quantity_label.setStyleSheet("color: #555; border: none; background: transparent;")
            else:
                quantity_label.setText("สินค้าหมด (Out of Stock)")
                quantity_label.setStyleSheet("color: #e74c3c; font-weight: bold; border: none; background: transparent;")
            v_layout.addWidget(quantity_label)
            
            
            v_layout.addStretch() 

            cart_btn = QPushButton("🛒 เพิ่มลงตะกร้า") 
            cart_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            cart_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            cart_btn.setStyleSheet("""
                QPushButton {
                    background-color: #004aad;
                    color: white;
                    padding: 8px;
                    border-radius: 8px;
                }
                QPushButton:hover { background-color: #003580; }
                QPushButton:disabled { background-color: #ccc; }
            """)
            
            # ❗ (เพิ่ม) ปิดปุ่มถ้าสินค้าหมด
            if quantity <= 0:
                cart_btn.setDisabled(True)
                cart_btn.setText("สินค้าหมด")

            
            product_data = {
                'id': prod_id,
                'name': name,
                'image_path': image_path,
                'price_str': price,
                'description': description,
                'quantity_stock': quantity # ❗ (เพิ่ม) ส่งจำนวนสต็อกไปด้วย
            }
            
            pic_btn.clicked.connect(lambda ch, data=product_data: self.view_details_signal.emit(data))
            cart_btn.clicked.connect(lambda ch, data=product_data: self.add_to_cart_signal.emit(data))

            v_layout.addWidget(cart_btn)

            self.product_widgets.append((card, name))
            self.grid.addWidget(card, i // 4, i % 4)

    def filter_products(self):
        query = self.search_input.text().lower()
        # ❗ (แก้ไข) p[1] คือ name (index 1 ของ tuple)
        filtered = [p for p in self.products if query in p[1].lower()] 
        self.display_products(filtered)
        

# =========================
# 🛒 Cart Page (แก้ไข)
# =========================
# =========================
# 🛒 Cart Page (❗ แก้ไขพื้นหลัง Label)
# =========================
class CartPage(QWidget):
    item_removed = pyqtSignal(tuple)
    checkout_signal = pyqtSignal()
    
    def __init__(self, image_folder):
        super().__init__()
        self.image_folder = image_folder
        
        self.current_subtotal = 0 
        self.current_vat = 0
        self.current_grand_total = 0 
        
        self.initUI()

    def initUI(self):
        self.setStyleSheet("background-color: #f5f5f5;") 
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # ---------- 1. ส่วนรายการสินค้า (ฝั่งซ้าย) ----------
        left_frame = QFrame()
        left_frame.setStyleSheet("background-color: transparent; border: none;") # (พื้นหลังโปร่งใส)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        title = QLabel("🛒 ตะกร้าสินค้าของคุณ")
        title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        left_layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #ddd; background-color: white; }")
        
        self.scroll_widget = QWidget()
        self.items_layout = QVBoxLayout(self.scroll_widget)
        self.items_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.items_layout.setSpacing(10)
        
        scroll.setWidget(self.scroll_widget)
        left_layout.addWidget(scroll)
        
        # ---------- 2. ส่วนสรุปยอด (ฝั่งขวา) ----------
        right_frame = QFrame()
        right_frame.setFixedSize(350, 400) 
        
        # ❗❗❗ [แก้ไข] เพิ่ม QSS สำหรับ QLabel ที่นี่ ❗❗❗
        right_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 10px;
            }
            /* สั่งให้ Label *ภายใน* Frame นี้ ไม่มีพื้นหลังและไม่มีกรอบ */
            QLabel {
                background-color: transparent;
                border: none;
            }
        """)
        # ❗❗❗ [จบส่วนแก้ไข] ❗❗❗
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 80))
        right_frame.setGraphicsEffect(shadow)
        
        summary_layout = QVBoxLayout(right_frame)
        summary_layout.setContentsMargins(25, 25, 25, 25)
        summary_layout.setSpacing(15)
        summary_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        summary_title = QLabel("สรุปคำสั่งซื้อ")
        summary_title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        # (เราไม่ต้องแก้ QLabel ทีละอันแล้ว เพราะ QSS ของ right_frame คุมไว้หมด)
        summary_layout.addWidget(summary_title)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        summary_layout.addWidget(line)

        # (ราคาสินค้า - Subtotal)
        subtotal_layout = QHBoxLayout()
        subtotal_label = QLabel("ราคาสินค้า:")
        subtotal_label.setFont(QFont("Arial", 14))
        self.subtotal_price_label = QLabel("฿0.00") 
        self.subtotal_price_label.setFont(QFont("Arial", 14))
        subtotal_layout.addWidget(subtotal_label)
        subtotal_layout.addStretch()
        subtotal_layout.addWidget(self.subtotal_price_label)
        summary_layout.addLayout(subtotal_layout)

        # (VAT 7%)
        vat_layout = QHBoxLayout()
        vat_label = QLabel("VAT (7%):")
        vat_label.setFont(QFont("Arial", 14))
        self.vat_price_label = QLabel("฿0.00") 
        self.vat_price_label.setFont(QFont("Arial", 14))
        vat_layout.addWidget(vat_label)
        vat_layout.addStretch()
        vat_layout.addWidget(self.vat_price_label)
        summary_layout.addLayout(vat_layout)
        
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        line2.setStyleSheet("border-top: 1px solid #eee;")
        summary_layout.addWidget(line2)

        # (ราคารวมสุทธิ - Grand Total)
        total_layout = QHBoxLayout()
        total_label = QLabel("ยอดสุทธิ:") 
        total_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.total_price_label = QLabel("฿0.00") 
        self.total_price_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        # (QSS ที่คุมกรอบ จะจัดการพื้นหลังให้ แต่เรายังต้องกำหนดสีตัวอักษร)
        self.total_price_label.setStyleSheet("color: #e74c3c;") 
        total_layout.addWidget(total_label)
        total_layout.addStretch()
        total_layout.addWidget(self.total_price_label)
        summary_layout.addLayout(total_layout)

        summary_layout.addStretch()

        # (ปุ่มชำระเงิน)
        checkout_btn = QPushButton("ดำเนินการชำระเงิน")
        checkout_btn.setFixedHeight(45)
        checkout_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        checkout_btn.setStyleSheet("""
            QPushButton {
                background-color: #008c4a; color: white; border-radius: 8px;
            }
            QPushButton:hover { background-color: #006a38; }
        """)
        checkout_btn.clicked.connect(self.checkout)
        summary_layout.addWidget(checkout_btn)

        # ---------- 3. รวม Layout ซ้าย-ขวา ----------
        main_layout.addWidget(left_frame, 1) 
        main_layout.addWidget(right_frame, 0) 

    # (ฟังก์ชันที่เหลือ load_cart_items, create_cart_item_widget, checkout เหมือนเดิม)
    def load_cart_items(self, cart_data):
        for i in reversed(range(self.items_layout.count())):
            widget = self.items_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        subtotal = 0

        if not cart_data:
            empty_label = QLabel("ตะกร้าของคุณว่างเปล่า")
            empty_label.setFont(QFont("Arial", 14))
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.items_layout.addWidget(empty_label)
            
            self.subtotal_price_label.setText("฿0.00")
            self.vat_price_label.setText("฿0.00")
            self.total_price_label.setText("฿0.00")
            self.current_subtotal = 0
            self.current_vat = 0
            self.current_grand_total = 0
            return

        for item in cart_data:
            item_total = item['price'] * item['quantity']
            subtotal += item_total
            
            item_widget = self.create_cart_item_widget(item, item_total)
            self.items_layout.addWidget(item_widget)

        vat = subtotal * 0.07
        grand_total = subtotal + vat
        
        self.current_subtotal = subtotal
        self.current_vat = vat
        self.current_grand_total = grand_total

        self.subtotal_price_label.setText(f"฿{subtotal:,.2f}")
        self.vat_price_label.setText(f"฿{vat:,.2f}")
        self.total_price_label.setText(f"฿{grand_total:,.2f}")


    def create_cart_item_widget(self, item_data, item_total):
        item_frame = QFrame()
        item_frame.setFixedHeight(120)
        item_frame.setStyleSheet("border-bottom: 1px solid #eee; background: white;")
        
        layout = QHBoxLayout(item_frame)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        pic_label = QLabel()
        pic_label.setFixedSize(100, 100)
        full_path = os.path.join(self.image_folder, item_data['image_path'])
        if os.path.exists(full_path):
            pix = QPixmap(full_path).scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation)
            pic_label.setPixmap(pix)
        else:
            pic_label.setText("No Img")
        layout.addWidget(pic_label)

        info_layout = QVBoxLayout()
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        name_label = QLabel(item_data['name'])
        name_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        
        size_label = QLabel(f"Size: {item_data.get('size', 'N/A')}")
        size_label.setFont(QFont("Arial", 11))
        size_label.setStyleSheet("color: #777;")

        price_label = QLabel(f"@{item_data['price']:,.0f} x {item_data['quantity']}")
        price_label.setFont(QFont("Arial", 12))
        price_label.setStyleSheet("color: #555;")
        
        info_layout.addWidget(name_label)
        info_layout.addWidget(size_label) 
        info_layout.addWidget(price_label)
        layout.addLayout(info_layout)

        layout.addStretch()

        row_total_label = QLabel(f"฿{item_total:,.0f}")
        row_total_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        row_total_label.setFixedWidth(120) 
        row_total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(row_total_label)

        remove_btn = QPushButton("🗑️ ลบ")
        remove_btn.setFixedSize(80, 35)
        remove_btn.setFont(QFont("Arial", 10))
        remove_btn.setStyleSheet("""
            QPushButton { background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 5px; }
            QPushButton:hover { background-color: #e74c3c; color: white; border-color: #e74c3c; }
        """)
        
        product_id = item_data['id']
        product_size = item_data.get('size', 'N/A')
        
        remove_btn.clicked.connect(
            lambda ch, pid=product_id, psize=product_size: self.item_removed.emit((pid, psize))
        )
        
        layout.addWidget(remove_btn)

        return item_frame

    def checkout(self):
        if self.current_grand_total <= 0:
            QMessageBox.warning(self, "ตะกร้าว่างเปล่า", "กรุณาเพิ่มสินค้าลงในตะกร้าก่อน")
            return
            
        self.checkout_signal.emit()


# =========================
# 🔹 Product Detail Page (แก้ไข - เพิ่มปุ่ม Buy Now)
# =========================
class ProductDetailPage(QWidget):
    # สัญญาณสำหรับบอก MainApp
    back_to_products_signal = pyqtSignal()
    add_to_cart_signal = pyqtSignal(dict)
    buy_now_signal = pyqtSignal(dict) 
    
    def __init__(self, image_folder):
        super().__init__()
        self.image_folder = image_folder
        self.current_product_data = None
        self.current_stock = 0 # ❗ (เพิ่ม) ตัวแปรเก็บสต็อกปัจจุบัน
        self.initUI()

    def initUI(self):
        self.setStyleSheet("background-color: #ffffff;")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 20, 40, 40)
        main_layout.setSpacing(20)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 1. ปุ่มย้อนกลับ (เหมือนเดิม)
        back_btn = QPushButton("⬅️ กลับไปหน้าสินค้า")
        # ... (ข้ามโค้ดปุ่ม back_btn ที่ไม่แก้) ...
        back_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet("""
            QPushButton {
                border: none;
                padding: 8px 12px;
                border-radius: 8px;
                background-color: #f0f0f0;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        back_btn.setFixedWidth(200)
        back_btn.clicked.connect(self.back_to_products_signal.emit)
        main_layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # 2. ส่วนเนื้อหา (รูป + รายละเอียด) (เหมือนเดิม)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(30)
        content_layout.setContentsMargins(20, 20, 20, 20)
        
        # 2.1 ฝั่งซ้าย (รูป) (เหมือนเดิม)
        self.pic_label = QLabel()
        self.pic_label.setFixedSize(450, 450)
        self.pic_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pic_label.setStyleSheet("border: 1px solid #eee; border-radius: 10px; background-color: white;")
        content_layout.addWidget(self.pic_label, 0)

        # 2.2 ฝั่งขวา (รายละเอียด) (เหมือนเดิม)
        details_layout = QVBoxLayout()
        details_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        details_layout.setSpacing(15)
        
        self.name_label = QLabel("ชื่อสินค้า (Product Name)")
        self.name_label.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        self.name_label.setWordWrap(True)
        details_layout.addWidget(self.name_label)
        
        self.price_label = QLabel("฿0")
        self.price_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.price_label.setStyleSheet("color: #e74c3c;")
        details_layout.addWidget(self.price_label)

        # ❗ (เพิ่ม) Label แสดงสต็อก
        self.stock_label = QLabel("สต็อก: 0 ชิ้น")
        self.stock_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.stock_label.setStyleSheet("color: #555;")
        details_layout.addWidget(self.stock_label)


        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        details_layout.addWidget(line)

        self.description_label = QLabel("รายละเอียดสินค้าจะแสดงที่นี่...")
        self.description_label.setFont(QFont("Arial", 14))
        self.description_label.setStyleSheet("color: #333;")
        self.description_label.setWordWrap(True)
        details_layout.addWidget(self.description_label)
        
        # 3. ส่วนเลือกตัวเลือก (Size & Quantity) (เหมือนเดิม)
        options_layout = QHBoxLayout()
        options_layout.setSpacing(20)
        options_layout.setContentsMargins(0, 10, 0, 10) # (ระยะห่างบนล่าง)
        
        size_label = QLabel("ขนาด:")
        size_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        
        self.size_combo = QComboBox()
        self.size_combo.setFont(QFont("Arial", 14))
        self.size_combo.addItems(["S", "M", "L", "XL", "XXL"])
        self.size_combo.setFixedWidth(150)
        self.size_combo.setStyleSheet("""
            QComboBox { 
                padding: 8px 12px; 
                border: 1px solid #ccc; 
                border-radius: 8px;
                background-color: white;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        options_layout.addWidget(size_label)
        options_layout.addWidget(self.size_combo)

        quantity_label = QLabel("จำนวน:")
        quantity_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        
        self.quantity_spinbox = QSpinBox()
        self.quantity_spinbox.setFont(QFont("Arial", 14))
        # ❗ (แก้ไข) - ตั้งค่าเริ่มต้น Range (จะถูก override ตอน load_product_details)
        self.quantity_spinbox.setRange(1, 99) 
        self.quantity_spinbox.setValue(1) 
        self.quantity_spinbox.setFixedWidth(100)
        self.quantity_spinbox.setStyleSheet("""
            QSpinBox { 
                padding: 8px 12px; 
                border: 1px solid #ccc; 
                border-radius: 8px;
                background-color: white;
            }
            QSpinBox:disabled {
                background-color: #f0f0f0;
            }
        """)
        options_layout.addWidget(quantity_label)
        options_layout.addWidget(self.quantity_spinbox)
        
        options_layout.addStretch()
        
        details_layout.addLayout(options_layout)
        # ----------------------------------------
        
        
        # ❗ 4. (แก้ไข) ย้ายปุ่มมาไว้ *ก่อน* addStretch
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        button_layout.setContentsMargins(0, 15, 0, 0) # (เพิ่มระยะห่างด้านบน)

        # 4.1 ปุ่มเพิ่มลงตะกร้า
        self.cart_btn = QPushButton("🛒 เพิ่มลงตะกร้า")
        self.cart_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.cart_btn.setFixedHeight(50)
        self.cart_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cart_btn.setStyleSheet("""
            QPushButton {
                background-color: #004aad; color: white;
                padding: 12px; border-radius: 8px;
            }
            QPushButton:hover { background-color: #003580; }
            QPushButton:disabled { background-color: #ccc; }
        """)
        self.cart_btn.clicked.connect(self.handle_add_to_cart)
        
        # 4.2 ปุ่มซื้อเลย
        self.buy_now_btn = QPushButton("💳 ซื้อเลย (Buy Now)")
        self.buy_now_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.buy_now_btn.setFixedHeight(50)
        self.buy_now_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.buy_now_btn.setStyleSheet("""
            QPushButton {
                background-color: #008c4a; color: white; /* (สีเขียว) */
                padding: 12px; border-radius: 8px;
            }
            QPushButton:hover { background-color: #006a38; }
            QPushButton:disabled { background-color: #ccc; }
        """)
        self.buy_now_btn.clicked.connect(self.handle_buy_now)

        button_layout.addWidget(self.cart_btn, 1) 
        button_layout.addWidget(self.buy_now_btn, 1) 
        
        details_layout.addLayout(button_layout) # ❗ เพิ่มปุ่มตรงนี้

        # ❗ 5. (แก้ไข) ย้าย addStretch() มาไว้ล่างสุด
        #   ตัวยืดนี้จะดันทุกอย่าง (รวมถึงปุ่ม) ขึ้นไปด้านบน
        details_layout.addStretch() 

        
        content_layout.addLayout(details_layout, 1) 
        main_layout.addLayout(content_layout)

    def load_product_details(self, product_data):
        self.current_product_data = product_data
        
        full_path = os.path.join(self.image_folder, product_data['image_path'])
        if os.path.exists(full_path):
            pix = QPixmap(full_path)
            scaled = pix.scaled(450, 450, Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation)
            self.pic_label.setPixmap(scaled)
        else:
            self.pic_label.setText("ไม่พบรูปภาพ")
            
        self.name_label.setText(product_data['name'])
        self.price_label.setText(product_data['price_str'])
        
        desc = product_data.get('description', 'ยังไม่มีรายละเอียดสำหรับสินค้านี้')
        if not desc:
             desc = 'ยังไม่มีรายละเอียดสำหรับสินค้านี้'
        self.description_label.setText(desc)
        
        self.size_combo.setCurrentIndex(0) 
        self.quantity_spinbox.setValue(1)
        
        # ❗ (เพิ่ม) ส่วนจัดการสต็อก
        self.current_stock = product_data.get('quantity_stock', 0)
        
        if self.current_stock > 0:
            self.stock_label.setText(f"สต็อก: {self.current_stock} ชิ้น")
            self.stock_label.setStyleSheet("color: #555; font-weight: bold;")
            
            # จำกัด SpinBox ให้ไม่เกินจำนวนสต็อก
            self.quantity_spinbox.setRange(1, self.current_stock)
            
            # เปิดใช้งานปุ่มและ SpinBox
            self.quantity_spinbox.setEnabled(True)
            self.cart_btn.setEnabled(True)
            self.cart_btn.setText("🛒 เพิ่มลงตะกร้า")
            self.buy_now_btn.setEnabled(True)
            self.buy_now_btn.setText("💳 ซื้อเลย (Buy Now)")
            
        else:
            # กรณีสินค้าหมด
            self.stock_label.setText("สินค้าหมด (Out of Stock)")
            self.stock_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            
            # ปิดการใช้งานปุ่มและ SpinBox
            self.quantity_spinbox.setRange(0, 0) # ตั้งค่า range เป็น 0
            self.quantity_spinbox.setEnabled(False)
            self.cart_btn.setEnabled(False)
            self.cart_btn.setText("สินค้าหมด")
            self.buy_now_btn.setEnabled(False)
            self.buy_now_btn.setText("สินค้าหมด")

    
    def _prepare_data_for_signal(self):
        """(แก้ไข) รวบรวมข้อมูลสินค้า, Size, Quantity และ Stock เพื่อส่ง Signal"""
        if not self.current_product_data:
            return None
            
        selected_size = self.size_combo.currentText()
        selected_quantity = self.quantity_spinbox.value()

        cart_data = self.current_product_data.copy()
        
        cart_data['selected_size'] = selected_size
        cart_data['quantity_to_add'] = selected_quantity
        
        # ❗ (เพิ่ม) ส่งสต็อกไปด้วย (แม้ว่า product_data จะมีอยู่แล้ว แต่เพื่อความชัดเจน)
        cart_data['quantity_stock'] = self.current_stock
        
        return cart_data

    def handle_add_to_cart(self):
        """(เหมือนเดิม) ส่งสัญญาณ 'เพิ่มลงตะกร้า'"""
        data = self._prepare_data_for_signal()
        if data:
            self.add_to_cart_signal.emit(data)

    def handle_buy_now(self):
        """(เหมือนเดิม) ส่งสัญญาณ 'ซื้อเลย'"""
        data = self._prepare_data_for_signal()
        if data:
            self.buy_now_signal.emit(data)


# =========================
# 🔹 Payment Page 
# =========================
class PaymentPage(QWidget):
    # สัญญาณ: (order_id, receipt_text)
    payment_confirmed_signal = pyqtSignal(int, str, list)
    payment_cancelled_signal = pyqtSignal()
    
    def __init__(self, image_folder):
        super().__init__()
        self.image_folder = image_folder
        self.current_user = None
        self.cart_items = []
        self.total_info = {}
        self.slip_path = None # ที่อยู่ของไฟล์สลิปที่อัปโหลด
        self.initUI()

    def initUI(self):
        self.setStyleSheet("background-color: #f5f5f5;")
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.setContentsMargins(40, 30, 40, 40)
        main_layout.setSpacing(20)

        title = QLabel("💳 ชำระเงิน (Payment)")
        title.setFont(QFont("Arial", 26, QFont.Weight.Bold))
        main_layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        # ---------- Layout 2 ฝั่ง (ซ้าย: สรุป, ขวา: โอนเงิน) ----------
        content_layout = QHBoxLayout()
        content_layout.setSpacing(30)

        # 1. ฝั่งซ้าย: สรุปรายการ
        left_frame = QFrame()
        left_frame.setStyleSheet("background-color: white; border-radius: 10px; border: 1px solid #ddd;")
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(10)

        summary_title = QLabel("สรุปรายการสั่งซื้อ:")
        summary_title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        left_layout.addWidget(summary_title)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setFont(QFont("Arial", 12))
        self.summary_text.setStyleSheet("border: 1px solid #eee;")
        left_layout.addWidget(self.summary_text)

        self.total_label = QLabel("ยอดชำระสุทธิ: ฿0.00")
        self.total_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.total_label.setStyleSheet("color: #e74c3c; margin-top: 10px;")
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        left_layout.addWidget(self.total_label)
        
        content_layout.addWidget(left_frame, 1) # (ขยาย 1 ส่วน)

        # 2. ฝั่งขวา: ช่องโอนเงินและอัปโหลด
        right_frame = QFrame()
        right_frame.setStyleSheet("background-color: white; border-radius: 10px; border: 1px solid #ddd;")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(25, 20, 25, 20)
        right_layout.setSpacing(15)
        
        transfer_title = QLabel("ขั้นตอนการชำระเงิน:")
        transfer_title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        right_layout.addWidget(transfer_title)

        bank_info = QLabel(
            "1. กรุณาโอนเงินมาที่บัญชี:\n"
            "   - ธนาคาร Arai Bank\n"
            "   - เลขที่บัญชี: 123-456-7890\n"
            "   - ชื่อบัญชี: Arai Football Shop\n\n"
            "2. อัปโหลดสลิปการโอนเงินด้านล่าง"
        )
        bank_info.setFont(QFont("Arial", 13))
        bank_info.setWordWrap(True)
        right_layout.addWidget(bank_info)
        
        right_layout.addStretch() 

        upload_layout = QHBoxLayout()
        self.upload_btn = QPushButton("📁 เลือกสลิป (Upload Slip)")
        self.upload_btn.setFont(QFont("Arial", 12))
        self.upload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.upload_btn.clicked.connect(self.handle_upload_slip)
        upload_layout.addWidget(self.upload_btn)

        self.slip_status_label = QLabel("ยังไม่ได้เลือกไฟล์")
        self.slip_status_label.setFont(QFont("Arial", 11))
        self.slip_status_label.setStyleSheet("color: #888; padding-left: 10px;")
        upload_layout.addWidget(self.slip_status_label)
        upload_layout.addStretch()
        right_layout.addLayout(upload_layout)

        right_layout.addStretch() 

        confirm_btn = QPushButton("ยืนยันการชำระเงิน")
        confirm_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        confirm_btn.setFixedHeight(45)
        confirm_btn.setStyleSheet("background-color: #008c4a; color: white; border-radius: 8px;")
        confirm_btn.clicked.connect(self.handle_confirm_payment)
        
        cancel_btn = QPushButton("ยกเลิก (กลับไปหน้าตะกร้า/สินค้า)")
        cancel_btn.setFont(QFont("Arial", 12))
        cancel_btn.setFixedHeight(40)
        cancel_btn.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 8px;")
        cancel_btn.clicked.connect(self.payment_cancelled_signal.emit)

        right_layout.addWidget(confirm_btn)
        right_layout.addWidget(cancel_btn)
        
        content_layout.addWidget(right_frame, 1) 
        
        main_layout.addLayout(content_layout, 1) 

    def load_order_details(self, username, cart_items, total_info):
        self.current_user = username
        self.cart_items = cart_items
        self.total_info = total_info
        self.slip_path = None 
        self.slip_status_label.setText("ยังไม่ได้เลือกไฟล์")
        self.slip_status_label.setStyleSheet("color: #888;")

        receipt_text = f"ผู้ใช้: {username}\n"
        receipt_text += "=" * 40 + "\n"
        receipt_text += "รายการสินค้า:\n\n"
        
        for item in cart_items:
            receipt_text += (
                f"- {item['name']} (Size: {item.get('size', 'N/A')})\n"
                f"  (จำนวน: {item['quantity']} x ฿{item['price']:,.2f}) = ฿{item['quantity'] * item['price']:,.2f}\n"
            )
            
        receipt_text += "\n" + "=" * 40 + "\n"
        receipt_text += f"ราคาสินค้า (Subtotal): ฿{total_info['subtotal']:,.2f}\n"
        receipt_text += f"VAT 7%:             ฿{total_info['vat']:,.2f}\n"
        receipt_text += f"ยอดสุทธิ:              ฿{total_info['grand_total']:,.2f}\n"
        
        self.summary_text.setText(receipt_text)
        
        self.total_label.setText(f"ยอดชำระสุทธิ: ฿{total_info['grand_total']:,.2f}")
        
        self.current_receipt_text = receipt_text

    def handle_upload_slip(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "เลือกสลิปการโอนเงิน", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            save_dir = "slips"
            os.makedirs(save_dir, exist_ok=True)
            timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_hhmmss")
            filename = f"{self.current_user}_{timestamp}_{os.path.basename(file_path)}"
            save_path = os.path.join(save_dir, filename)
            
            try:
                shutil.copy(file_path, save_path)
                self.slip_path = save_path 
                self.slip_status_label.setText(f"✅ {os.path.basename(save_path)}")
                self.slip_status_label.setStyleSheet("color: green;")
            except Exception as e:
                QMessageBox.warning(self, "Upload Error", f"ไม่สามารถบันทึกสลิปได้: {e}")
                self.slip_path = None

    def handle_confirm_payment(self):
        if not self.current_user:
            QMessageBox.warning(self, "Error", "เกิดข้อผิดพลาด: ไม่พบข้อมูลผู้ใช้ กรุณาล็อกอินใหม่")
            return
            
        if not self.slip_path:
            QMessageBox.warning(self, "ข้อมูลไม่ครบ", "⚠️ กรุณาอัปโหลดสลิปการโอนเงินก่อน")
            return

        try:
            conn = sqlite3.connect("orders.db")
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO orders (username, total_amount, slip_image_path, status)
                VALUES (?, ?, ?, ?)
            """, (
                self.current_user,
                self.total_info['grand_total'],
                self.slip_path,
                'Pending Confirmation'
            ))
            
            new_order_id = cur.lastrowid
            
            items_to_save = []
            for item in self.cart_items:
                items_to_save.append((
                    new_order_id,
                    item['name'],
                    item.get('size', 'N/A'),
                    item['quantity'],
                    item['price']
                ))
            
            cur.executemany("""
                INSERT INTO order_items (order_id, product_name, size, quantity, price_per_item)
                VALUES (?, ?, ?, ?, ?)
            """, items_to_save)
            
            conn.commit()
            conn.close()
            
            QMessageBox.information(self, "สำเร็จ", f"✅ เราได้รับคำสั่งซื้อของคุณแล้ว (Order ID: {new_order_id})\nกำลังรอการตรวจสอบสลิป")
            
            final_receipt_text = f"Order ID: {new_order_id}\n" + self.current_receipt_text
            
            self.payment_confirmed_signal.emit(new_order_id, final_receipt_text, self.cart_items)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"เกิดข้อผิดพลาดในการบันทึกคำสั่งซื้อ: {e}")


# =========================
# 🔹 Receipt Dialog 
# =========================
class ReceiptDialog(QDialog):
    def __init__(self, receipt_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ใบเสร็จรับเงิน (Receipt)")
        self.setMinimumSize(500, 600)
        
        layout = QVBoxLayout(self)
        
        title = QLabel("ใบเสร็จรับเงิน / สรุปคำสั่งซื้อ")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        layout.addWidget(title)
        
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        font = QFont("Courier New", 12) 
        self.text_edit.setFont(font)
        self.text_edit.setText(receipt_text)
        layout.addWidget(self.text_edit)
        
        btn_layout = QHBoxLayout()
        
        print_btn = QPushButton("🖨️ พิมพ์ (Print)")
        print_btn.clicked.connect(self.handle_print)
        btn_layout.addWidget(print_btn)
        
        close_btn = QPushButton("ปิด")
        close_btn.clicked.connect(self.accept) 
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)

    def handle_print(self):
        try:
            # (ต้อง import QPrintPreviewDialog, QPrinter ด้านบน)
            printer = QPrinter()
            preview_dialog = QPrintPreviewDialog(printer, self)
            
            preview_dialog.paintRequested.connect(self.text_edit.print_)
            
            preview_dialog.exec()

        except Exception as e:
             # (กรณีที่ import ล้มเหลว)
            print(f"Print Error: {e}")
            QMessageBox.warning(self, "Print Error", "ไม่สามารถโหลดโมดูลการพิมพ์ (PyQt6.QtPrintSupport) ได้")


# =========================
# 🔹 Orders Page 
# =========================

class OrdersPage(QWidget):
    """(ใหม่) หน้านี้สำหรับให้ User ดูประวัติการสั่งซื้อของตัวเอง (ดีไซน์ใหม่)"""
    
    def __init__(self):
        super().__init__()
        self.current_user = None
        self.initUI()

    def initUI(self):
        self.setStyleSheet("background-color: #f5f5f5;")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 30)
        main_layout.setSpacing(15)

        # 1. ส่วนหัว (Title + Refresh)
        title_layout = QHBoxLayout()
        title = QLabel("📜 ประวัติการสั่งซื้อ (My Orders)")
        title.setFont(QFont("Arial", 26, QFont.Weight.Bold))
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 โหลดใหม่")
        refresh_btn.setFixedWidth(120)
        refresh_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        refresh_btn.setStyleSheet("""
            QPushButton { background-color: #004aad; color: white; border-radius: 8px; padding: 8px;}
            QPushButton:hover { background-color: #003580; }
        """)
        refresh_btn.clicked.connect(lambda: self.load_my_orders(self.current_user))
        title_layout.addWidget(refresh_btn)
        
        main_layout.addLayout(title_layout)

        # 2. ส่วนแสดงผล (Scroll Area)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical {
                border: none; background: #f5f5f5; width: 10px; margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #cccccc; border-radius: 5px; min-height: 25px;
            }
            QScrollBar::handle:vertical:hover { background-color: #004aad; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none; border: none; height: 0px;
            }
        """)

        scroll_content_widget = QWidget()
        scroll_content_widget.setStyleSheet("background-color: transparent;")
        
        self.orders_list_layout = QVBoxLayout(scroll_content_widget)
        self.orders_list_layout.setContentsMargins(10, 10, 10, 10)
        self.orders_list_layout.setSpacing(20)
        
        scroll.setWidget(scroll_content_widget)
        main_layout.addWidget(scroll, 1) # (ขยาย 1 ส่วน)

    def load_my_orders(self, username):
        """โหลด Order ทั้งหมดของ User แล้วสร้างเป็น Card"""
        self.current_user = username
        
        # 1. ล้าง Layout เก่า
        for i in reversed(range(self.orders_list_layout.count())):
            item = self.orders_list_layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()
            
        if not username:
            empty_label = QLabel("กรุณาล็อกอินเพื่อดูประวัติการสั่งซื้อ")
            empty_label.setFont(QFont("Arial", 16))
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.orders_list_layout.addWidget(empty_label)
            return

        try:
            conn = sqlite3.connect("orders.db")
            cur = conn.cursor()
            
            # 2. ดึง Order หลัก
            cur.execute(
                "SELECT id, created_at, total_amount, status FROM orders WHERE username=? ORDER BY id DESC",
                (username,)
            )
            orders = cur.fetchall()
            
            if not orders:
                empty_label = QLabel("คุณยังไม่มีคำสั่งซื้อ")
                empty_label.setFont(QFont("Arial", 16))
                empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.orders_list_layout.addWidget(empty_label)
                conn.close()
                return

            # 3. สร้าง Card ทีละ Order
            for order_data in orders:
                order_id = order_data[0]
                
                # 4. ดึง Item ของ Order นั้นๆ
                cur.execute(
                    "SELECT product_name, size, quantity, price_per_item FROM order_items WHERE order_id=?",
                    (order_id,)
                )
                items_data = cur.fetchall()
                
                # 5. สร้าง Card
                order_card = self.create_order_card(order_data, items_data)
                self.orders_list_layout.addWidget(order_card)
                
            conn.close()
            
            # 6. เพิ่มตัวยืด (Stretch) เพื่อให้ Card ดันขึ้นบน
            self.orders_list_layout.addStretch()

        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"ไม่สามารถโหลดประวัติการสั่งซื้อได้: {e}")

    def create_order_card(self, order_data, items_data):
        """สร้าง Widget Card สำหรับ 1 Order"""
        
        order_id, created_at, total_amount, status = order_data
        
        # 1. กรอบ Card หลัก
        card = QFrame()
        card.setMinimumHeight(150)
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 12px;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 40))
        card.setGraphicsEffect(shadow)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 15, 20, 15)
        card_layout.setSpacing(10)

        # 2. ส่วนหัวของ Card (ID, Date, Status, Total)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)

        id_label = QLabel(f"Order ID: #{order_id}")
        id_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        
        date_label = QLabel(f"วันที่: {created_at.split(' ')[0]}")
        date_label.setFont(QFont("Arial", 12))
        date_label.setStyleSheet("color: #555;")

        status_widget = self.get_status_widget(status)

        total_label = QLabel(f"ยอดรวม: ฿{total_amount:,.2f}")
        total_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        total_label.setStyleSheet("color: #e74c3c;")

        header_layout.addWidget(id_label)
        header_layout.addWidget(date_label)
        header_layout.addStretch()
        header_layout.addWidget(status_widget)
        header_layout.addWidget(total_label)
        
        card_layout.addLayout(header_layout)

        # 3. เส้นคั่น
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("border-top: 1px solid #eee;")
        card_layout.addWidget(line)

        # 4. รายการสินค้า (Items)
        items_layout = QVBoxLayout()
        items_layout.setSpacing(8)
        
        items_title = QLabel("รายการสินค้า:")
        items_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        items_layout.addWidget(items_title)

        for item in items_data:
            name, size, qty, price = item
            
            item_row = QHBoxLayout()
            
            # (หมายเหตุ: เราไม่มีรูปภาพใน DB 'order_items' เลยแสดงแต่ข้อความ)
            item_name_label = QLabel(f"- {name} (Size: {size})")
            item_name_label.setFont(QFont("Arial", 12))
            
            item_qty_label = QLabel(f"จำนวน: {qty}")
            item_qty_label.setFont(QFont("Arial", 12))
            item_qty_label.setStyleSheet("color: #333;")

            item_price_label = QLabel(f"฿{price:,.2f} / ชิ้น")
            item_price_label.setFont(QFont("Arial", 12))
            item_price_label.setStyleSheet("color: #777;")
            
            item_row.addWidget(item_name_label)
            item_row.addStretch()
            item_row.addWidget(item_qty_label)
            item_row.addWidget(item_price_label)
            
            items_layout.addLayout(item_row)
            
        card_layout.addLayout(items_layout)
        return card

    def get_status_widget(self, status_text):
        """สร้าง QLabel พร้อมสีพื้นหลังตามสถานะ"""
        status_label = QLabel(status_text)
        status_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        status_label.setFixedSize(160, 30)
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        base_style = "color: white; border-radius: 15px; padding: 5px;"
        
        if status_text == 'Pending Confirmation':
            style = f"background-color: #f39c12; {base_style}" # สีส้ม
        elif status_text == 'Completed':
            style = f"background-color: #2ecc71; {base_style}" # สีเขียว
        elif status_text == 'Cancelled':
            style = f"background-color: #e74c3c; {base_style}" # สีแดง
        else: # (รวมถึง Pending Payment)
            style = f"background-color: #bdc3c7; color: #333; border-radius: 15px; padding: 5px;" # สีเทา
            
        status_label.setStyleSheet(style)
        return status_label
        
    def load_order_items(self):
        # (ฟังก์ชันนี้ไม่จำเป็นต้องใช้อีกต่อไปในดีไซน์ใหม่)
        pass


# =========================
# 🔹 Contact Page
# =========================
class ContactPage(QWidget):
    def __init__(self, image_folder=None):
        super().__init__()
        self.image_folder = image_folder or "C:/project/picture/"
        self.current_user_data = None
        self.create_contact_table() # (ฟังก์ชันนี้ยังจำเป็นต้องมี)
        self.initUI()
        self.apply_styles() # (เพิ่มฟังก์ชันสำหรับ QSS)

    def create_contact_table(self):
        # (ฟังก์ชันนี้เหมือนเดิมทุกประการ)
        conn = sqlite3.connect("contact.db")
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS contact_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                username TEXT,
                email TEXT,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def initUI(self):
        # ---- 1. Layout หลัก (VBox) ----
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 30, 40, 40)
        main_layout.setSpacing(25)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # ---- 2. Title (ย้ายมาอยู่ด้านบนสุด) ----
        title = QLabel("ติดต่อเรา (Contact Us)")
        title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        title.setObjectName("PageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main_layout.addWidget(title)

        # ---- 3. Content Layout (HBox: ซ้าย-ขวา) ----
        content_layout = QHBoxLayout()
        content_layout.setSpacing(30)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.addLayout(content_layout, 1) # (ให้ยืดเต็มพื้นที่)

        # ---- 4. แผงด้านซ้าย (ข้อมูลติดต่อ) ----
        left_card = QFrame()
        left_card.setObjectName("InfoCard")
        
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(30, 25, 30, 30)
        left_layout.setSpacing(25)
        
        info_title = QLabel("ข้อมูลการติดต่อ")
        info_title.setObjectName("CardTitle")
        left_layout.addWidget(info_title)

        # (สร้างแถวข้อมูลติดต่อโดยใช้ฟังก์ชัน Helper)
        left_layout.addWidget(
            self.create_info_row("📍", "ที่อยู่", "23 หมู่ 16 ถ.มิตรภาพ ต.ในเมือง\nอ.เมืองขอนแก่น ขอนแก่น 40002")
        )
        left_layout.addWidget(
            self.create_info_row("📞", "โทร", "084-5807362")
        )
        left_layout.addWidget(
            self.create_info_row("✉️", "อีเมล", "support@araifootballshop.com")
        )
        left_layout.addWidget(
            self.create_info_row("🕘", "เวลาทำการ", "ทุกวัน 09.00 - 20.00 น.")
        )
        
        left_layout.addStretch()
        content_layout.addWidget(left_card, 1) # (สัดส่วน 1)

        # (เพิ่ม Shadow ให้การ์ดซ้าย)
        shadow_left = QGraphicsDropShadowEffect(self)
        shadow_left.setBlurRadius(25)
        shadow_left.setXOffset(0)
        shadow_left.setYOffset(4)
        shadow_left.setColor(QColor(0, 0, 0, 60))
        left_card.setGraphicsEffect(shadow_left)

        # ---- 5. แผงด้านขวา (ฟอร์มส่งข้อความ) ----
        right_card = QFrame()
        right_card.setObjectName("FormCard")
        
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(30, 25, 30, 30)
        right_layout.setSpacing(15)
        
        form_title = QLabel("ส่งข้อความถึงเรา")
        form_title.setObjectName("CardTitle")
        right_layout.addWidget(form_title)
        
        # (Label บอกสถานะ User)
        self.user_info_label = QLabel("กำลังส่งในนาม: ...")
        self.user_info_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.user_info_label.setObjectName("UserInfoLabel")
        right_layout.addWidget(self.user_info_label)

        # (Label "ข้อความของคุณ")
        message_label = QLabel("ข้อความของคุณ:")
        message_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        message_label.setObjectName("FieldLabel")
        right_layout.addWidget(message_label)

        # (กล่องข้อความ)
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("กรอกข้อความสอบถามของคุณที่นี่...")
        self.message_input.setMinimumHeight(200) # (ปรับความสูงได้ตามต้องการ)
        self.message_input.setObjectName("MessageInput")
        right_layout.addWidget(self.message_input, 1) # (ยืด 1 ส่วน)

        # (ปุ่มส่ง)
        send_btn = QPushButton("ส่งข้อความ")
        send_btn.setObjectName("SendButton")
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.setMinimumHeight(45)
        send_btn.clicked.connect(self.send_message)
        right_layout.addWidget(send_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        content_layout.addWidget(right_card, 2) # (สัดส่วน 2 - ให้ฝั่งนี้กว้างกว่า)

        # (เพิ่ม Shadow ให้การ์ดขวา)
        shadow_right = QGraphicsDropShadowEffect(self)
        shadow_right.setBlurRadius(25)
        shadow_right.setXOffset(0)
        shadow_right.setYOffset(4)
        shadow_right.setColor(QColor(0, 0, 0, 60))
        right_card.setGraphicsEffect(shadow_right)

    def create_info_row(self, icon_text, title_text, body_text):
        """(ใหม่) ฟังก์ชัน Helper สร้างแถวข้อมูลติดต่อ (Icon + Title + Body)"""
        row_widget = QWidget()
        row_widget.setStyleSheet("background-color: transparent;")
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(15)
        
        icon_label = QLabel(icon_text)
        icon_label.setFont(QFont("Arial", 22))
        icon_label.setObjectName("InfoIcon")
        row_layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignTop)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        title_label = QLabel(title_text)
        title_label.setObjectName("InfoTitle")
        text_layout.addWidget(title_label)
        
        body_label = QLabel(body_text)
        body_label.setObjectName("InfoBody")
        body_label.setWordWrap(True)
        text_layout.addWidget(body_label)
        
        row_layout.addLayout(text_layout, 1)
        return row_widget

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget { 
                background-color: #f5f5f5; 
                color: #333;
            }
            QLabel#PageTitle { 
                color: #2c3e50; 
                background-color: transparent; 
            }
            
            /* --- การ์ด (ซ้ายและขวา) --- */
            QFrame#InfoCard, QFrame#FormCard {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
            }
            QLabel#CardTitle {
                font-size: 22px;
                font-weight: bold;
                color: #2c3e50;
                background-color: transparent;
                padding-bottom: 10px;
                border-bottom: 1px solid #f0f0f0;
            }
            
            /* --- สไตล์การ์ดซ้าย (Info) --- */
            QLabel#InfoIcon {
                color: #004aad;
                background-color: transparent;
            }
            QLabel#InfoTitle {
                font-size: 16px;
                font-weight: bold;
                color: #333;
                background-color: transparent;
            }
            QLabel#InfoBody {
                font-size: 14px;
                color: #555;
                background-color: transparent;
                line-height: 1.4;
            }

            /* --- สไตล์การ์ดขวา (Form) --- */
            QLabel#UserInfoLabel {
                color: #004aad;
                background-color: transparent;
            }
            QLabel#FieldLabel {
                color: #333;
                background-color: transparent;
            }
            QTextEdit#MessageInput {
                border: 1px solid #d5d5d5; /* ❗ (แก้) มีกรอบบางๆ แต่ไม่มีตอน Focus */
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                color: black;
                background-color: white;
            }
            QTextEdit#MessageInput:focus {
                border: 1px solid #004aad; /* ❗ (แก้) เปลี่ยนสีตอน Focus */
            }
            
            QPushButton#SendButton {
                font-size: 14px;
                font-weight: bold;
                padding: 12px 30px;
                border-radius: 8px;
                background-color: #004aad; 
                color: white;
            }
            QPushButton#SendButton:hover { 
                background-color: #003580; 
            }
        """)

    def load_user_data(self, username):
        # (ฟังก์ชันนี้เหมือนเดิม)
        if not username:
            self.clear_user_data()
            return

        conn = sqlite3.connect("users.db")
        cur = conn.cursor()
        cur.execute("SELECT first_name, last_name, email FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        conn.close()

        if row:
            full_name = f"{row[0] or ''} {row[1] or ''}".strip()
            self.current_user_data = {
                "name": full_name or username,
                "username": username,
                "email": row[2] or "N/A"
            }
            self.user_info_label.setText(f"✅ กำลังส่งในนาม: {self.current_user_data['name']} ({self.current_user_data['email']})")
        else:
            self.clear_user_data()

    def clear_user_data(self):
        # (ฟังก์ชันนี้เหมือนเดิม)
        self.current_user_data = None
        self.user_info_label.setText("🔴 ไม่ได้เข้าสู่ระบบ (กรุณาล็อกอินเพื่อส่งข้อความ)")
        self.message_input.clear() 

    def send_message(self):
        # (ฟังก์ชันนี้เหมือนเดิม)
        if not self.current_user_data:
            QMessageBox.warning(self, "ยังไม่ได้เข้าสู่ระบบ", "⚠️ กรุณาล็อกอินก่อนส่งข้อความ")
            return
            
        name = self.current_user_data["name"]
        username = self.current_user_data["username"]
        email = self.current_user_data["email"]
        message = self.message_input.toPlainText().strip()

        if not message:
            QMessageBox.warning(self, "ข้อมูลไม่ครบ", "⚠️ กรุณากรอกข้อความที่ต้องการส่ง")
            return

        conn = sqlite3.connect("contact.db")
        c = conn.cursor()
        c.execute(
            "INSERT INTO contact_messages (name, username, email, message) VALUES (?, ?, ?, ?)",
            (name, username, email, message)
        )
        conn.commit()
        conn.close()

        QMessageBox.information(
            self, "ส่งข้อความแล้ว",
            f"✅ ขอบคุณ {name}! เราได้รับข้อความของคุณแล้ว"
        )
        
        self.message_input.clear()

# =========================
# 🔹 Contact Admin Page
# =========================
class ContactAdminPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #ffffff;")
        self.initUI()
        self.load_messages()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("📬 ข้อความจากลูกค้า (Admin)")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        header.addWidget(title)
        header.addStretch()

        refresh_btn = QPushButton("🔄 โหลดใหม่")
        refresh_btn.setFixedSize(120, 36)
        refresh_btn.clicked.connect(self.load_messages)
        header.addWidget(refresh_btn)

        delete_btn = QPushButton("🗑️ ลบที่เลือก")
        delete_btn.setFixedSize(120, 36)
        delete_btn.clicked.connect(self.delete_selected)
        header.addWidget(delete_btn)

        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Username", "Email", "Message", "Created At"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def load_messages(self):
        self.table.setRowCount(0)
        if not os.path.exists("contact.db"):
            return
        conn = sqlite3.connect("contact.db")
        c = conn.cursor()
        c.execute("SELECT id, name, username, email, message, created_at FROM contact_messages ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()

        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(i, j, item)

    def delete_selected(self):
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.information(self, "ไม่มีการเลือก", "⚠️ กรุณาเลือกอย่างน้อย 1 รายการที่จะลบ")
            return

        ids = []
        for idx in selected:
            row = idx.row()
            id_item = self.table.item(row, 0)
            if id_item:
                ids.append(id_item.text())

        confirm = QMessageBox.question(self, "ยืนยันการลบ",
                                       f"คุณต้องการลบ {len(ids)} รายการที่เลือกใช่หรือไม่?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                       QMessageBox.StandardButton.No)
        if confirm != QMessageBox.StandardButton.Yes:
            return

        conn = sqlite3.connect("contact.db")
        c = conn.cursor()
        placeholders = ",".join("?" for _ in ids)
        c.execute(f"DELETE FROM contact_messages WHERE id IN ({placeholders})", ids)
        conn.commit()
        conn.close()
        QMessageBox.information(self, "ลบสำเร็จ", f"✅ ลบ {len(ids)} รายการเรียบร้อยแล้ว")
        self.load_messages()


# =========================
# 🔹 Login / Signup / Forgot Password
# =========================
class LoginPage(QWidget):
    switch_to_signup = pyqtSignal()
    switch_to_forgot = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.bg_label = QLabel(self)
        self.bg_label.setScaledContents(True)
        bg_path = "C:/project/picture/back.png"
        
        if os.path.exists(bg_path):
            self.bg_label.setPixmap(QPixmap(bg_path))
        else:
            self.bg_label.setStyleSheet("background-color: #e0e0e0;") 
            print(f"Warning: ไม่พบรูปพื้นหลัง {bg_path}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(900, 180, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(18)

        title = QLabel("Login")
        title.setFont(QFont("Tex Gyre Adventor", 38, QFont.Weight.Bold))
        title.setStyleSheet("color: black; background: transparent;") 
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        self.add_field(layout, "Username", "user")
        self.add_field(layout, "Password", "pass", password=True)

        layout.addSpacing(25)

        login_btn = QPushButton("Login")
        login_btn.setFixedWidth(450)
        login_btn.setFixedHeight(40)
        login_btn.setFont(QFont("Tex Gyre Adventor", 16, QFont.Weight.Bold))
        login_btn.setStyleSheet("""
            QPushButton {
                background-color: #004aad; color: white; border-radius: 10px;
            }
            QPushButton:hover { background-color: #003580; }
        """)
        layout.addWidget(login_btn)

        self.forgot_link = QPushButton("Forgot Password?", self)
        self.forgot_link.setFont(QFont("Tex Gyre Adventor", 13, QFont.Weight.Bold))
        self.forgot_link.setStyleSheet("""
            QPushButton { border:none; background:transparent; color:black; } 
            QPushButton:hover { text-decoration:underline; }
        """)
        self.forgot_link.setGeometry(1180, 480, 200, 30)

        self.signup_link = QPushButton("Don't have an account?", self)
        self.signup_link.setFont(QFont("Tex Gyre Adventor", 13, QFont.Weight.Bold))
        self.signup_link.setStyleSheet("""
            QPushButton { border:none; background:transparent; color:black; } 
            QPushButton:hover { text-decoration:underline; }
        """)
        self.signup_link.setGeometry(850, 480, 300, 30)

        self.forgot_link.clicked.connect(self.switch_to_forgot)
        self.signup_link.clicked.connect(self.switch_to_signup)
        
        self.bg_label.lower()

    def add_field(self, layout, label_text, attr_name, password=False):
        label = QLabel(label_text)
        label.setFont(QFont("Tex Gyre Adventor", 16, QFont.Weight.Bold))
        label.setStyleSheet("color: black; background: transparent;") 
        layout.addWidget(label)
        
        line = QLineEdit()
        line.setFixedWidth(450)
        line.setFixedHeight(40)
        line.setFont(QFont("Arial", 14))
        line.setStyleSheet(
            "QLineEdit { border:1px solid #ccc; border-radius:10px; padding:8px 10px; background-color: white; }"
        )
        if password:
            line.setEchoMode(QLineEdit.EchoMode.Password)
        setattr(self, attr_name + "_input", line)
        layout.addWidget(line)

    def resizeEvent(self, event: QResizeEvent):
        if hasattr(self, 'bg_label'):
             self.bg_label.resize(self.size())
        super().resizeEvent(event)


class SignupPage(QWidget):
    switch_to_login = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.profile_pic_path = None
        self.initUI()

    def initUI(self):
        self.bg_label = QLabel(self)
        self.bg_label.setScaledContents(True)
        bg_path = "C:/project/picture/back.png" 
        
        if os.path.exists(bg_path):
            self.bg_label.setPixmap(QPixmap(bg_path))
        else:
            self.bg_label.setStyleSheet("background-color: #f0f0f0;") 
            print(f"Warning: ไม่พบรูปพื้นหลัง {bg_path}")

        title = QLabel("Sign Up", self) 
        title.setFont(QFont("Tex Gyre Adventor", 38, QFont.Weight.Bold))
        title.setStyleSheet("color: black; background: transparent;") 
        title.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        title.setGeometry(975, 20, 400, 80)

        self.pic_preview = QLabel(self) 
        self.pic_preview.setFixedSize(120, 120)
        self.pic_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pic_preview.setStyleSheet(
            "border: 2px dashed #888; border-radius: 60px; background: transparent;" 
        )
        self.pic_preview.setGeometry(1115, 110, 120, 120) 

        upload_btn = QPushButton("เลือกรูปโปรไฟล์", self) 
        upload_btn.setFixedWidth(180)
        upload_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        upload_btn.setStyleSheet("""
            QPushButton { background-color: #004aad; color: white; border-radius: 8px; padding: 6px; }
            QPushButton:hover { background-color: #003580; }
        """)
        upload_btn.clicked.connect(self.select_profile_pic)
        upload_btn.setGeometry(1085, 240, 180, 40) 

        self.inputs = {}
        fields = ["First Name", "Last Name", "Username", "Password", "Email", "Phone Number"]
        
        current_y = 300
        x_label = 780 
        x_input = 950 
        label_width = 160 
        input_width = 450
        row_height = 40 
        row_spacing = 15 
        
        for field in fields:
            label = QLabel(field + ":", self) 
            label.setFont(QFont("Arial", 15, QFont.Weight.Bold)) 
            label.setStyleSheet("color: black; background: transparent;") 
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter) 
            label.setGeometry(x_label, current_y, label_width, row_height) 
            
            line = QLineEdit(self) 
            line.setFixedWidth(input_width)
            line.setFixedHeight(row_height)
            line.setFont(QFont("Arial", 13))
            line.setStyleSheet(
                "background-color: white; border: 1px solid #ccc; border-radius: 8px; padding: 5px;"
            )
            
            if field == "Password":
                line.setEchoMode(QLineEdit.EchoMode.Password)
                
                regex = QRegularExpression("[\\x00-\\x7F]+")
                validator = QRegularExpressionValidator(regex, self)
                line.setValidator(validator)

            if field == "Phone Number":
                validator = QIntValidator()
                line.setValidator(validator)
            
            line.setGeometry(x_input, current_y, input_width, row_height) 
            
            self.inputs[field] = line
            
            current_y += row_height + row_spacing 

        signup_btn = QPushButton("Create Account", self) 
        signup_btn.setFixedWidth(input_width)
        signup_btn.setFixedHeight(45)
        signup_btn.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        signup_btn.setStyleSheet("""
            QPushButton { background:#004aad; color:white; border-radius:10px; }
            QPushButton:hover { background:#003580; }
        """)
        signup_btn.clicked.connect(self.validate_signup)
        signup_btn.setGeometry(x_input, current_y + 10, input_width, 45) 

        login_link = QPushButton("Already have an account? Login", self) 
        login_link.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        login_link.setStyleSheet("""
            QPushButton { border:none; background:transparent; color:black; } 
            QPushButton:hover { text-decoration:underline; }
        """)
        login_link.clicked.connect(self.switch_to_login.emit)
        login_link.setGeometry(x_input, current_y + 60, input_width, 30) 
        
        self.bg_label.lower()

    def select_profile_pic(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "เลือกภาพโปรไฟล์", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            pixmap = QPixmap(file_path).scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.pic_preview.setPixmap(pixmap)
            self.pic_preview.setStyleSheet(
                "border: 2px solid #004aad; border-radius: 60px; background: transparent;" 
            )
            self.profile_pic_path = file_path

    def validate_signup(self):
        data = {f: self.inputs[f].text().strip() for f in self.inputs}
        if not all(data.values()):
            QMessageBox.warning(self, "Missing Info", "⚠️ กรุณากรอกข้อมูลให้ครบทุกช่อง")
            return
        
        password = data["Password"] 

        if len(password) < 8:
            QMessageBox.warning(self, "Invalid Password", "⚠️ รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร")
            return
            
        if not ('A' <= password[0] <= 'Z'):
            QMessageBox.warning(self, "Invalid Password", "⚠️ รหัสผ่านต้องเริ่มต้นด้วยตัวอักษรภาษาอังกฤษพิมพ์ใหญ่ (A-Z)")
            return

        profile_pic_db_path = None
        if self.profile_pic_path:
            save_dir = "profile_pics"
            os.makedirs(save_dir, exist_ok=True)
            filename = f"{data['Username']}_profile.png"
            save_path = os.path.join(save_dir, filename)
            shutil.copy(self.profile_pic_path, save_path)
            profile_pic_db_path = save_path

        conn = sqlite3.connect("users.db")
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO users (first_name, last_name, username, password, email, phone, profile_pic)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data["First Name"], data["Last Name"], data["Username"],
                hash_password(password), data["Email"], data["Phone Number"], profile_pic_db_path
            ))
            conn.commit()
            QMessageBox.information(self, "Success", "✅ สมัครสมาชิกสำเร็จ!")
            self.switch_to_login.emit()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Duplicate Username", "⚠️ ชื่อผู้ใช้นี้มีอยู่แล้ว กรุณาใช้ชื่ออื่น")
        finally:
            conn.close()

    def resizeEvent(self, event: QResizeEvent):
        if hasattr(self, 'bg_label'):
            self.bg_label.resize(self.size())
        super().resizeEvent(event)


class ForgotPasswordPage(QWidget):
    switch_to_login = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.bg_label = QLabel(self)
        self.bg_label.setScaledContents(True)
        bg_path = "C:/project/picture/back.png"
        
        if os.path.exists(bg_path):
            self.bg_label.setPixmap(QPixmap(bg_path))
        else:
            self.bg_label.setStyleSheet("background-color: #f0f0f0;") 
            print(f"Warning: ไม่พบรูปพื้นหลัง {bg_path}")

        title = QLabel("Forgot Password", self)
        title.setFont(QFont("Tex Gyre Adventor", 35, QFont.Weight.Bold)) 
        title.setStyleSheet("color: black; background: transparent;") 
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setGeometry(975, 150, 400, 80)

        self.user_input = QLineEdit(self)
        self.email_input = QLineEdit(self)
        self.new_pass_input = QLineEdit(self)
        self.confirm_pass_input = QLineEdit(self)
        
        self.new_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pass_input.setEchoMode(QLineEdit.EchoMode.Password)

        current_y = 280
        
        x_label = 740   
        x_input = 950
        label_width = 200 
        input_width = 450
        row_height = 40
        row_spacing = 15

        fields_map = {
            "Username": self.user_input,
            "Email": self.email_input,
            "New Password": self.new_pass_input,
            "Confirm Password": self.confirm_pass_input
        }
        
        for label_text, field in fields_map.items():
            label = QLabel(label_text + ":", self) 
            label.setFont(QFont("Arial", 15, QFont.Weight.Bold))
            label.setStyleSheet("color: black; background: transparent;")
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter) 
            label.setGeometry(x_label, current_y, label_width, row_height) 
            
            field.setFixedWidth(input_width)
            field.setFixedHeight(row_height)
            field.setFont(QFont("Arial", 14))
            field.setStyleSheet(
                "background-color: white; border: 1px solid #ccc; border-radius: 8px; padding: 5px;"
            )
            field.setGeometry(x_input, current_y, input_width, row_height)
            
            current_y += row_height + row_spacing 

        reset_btn = QPushButton("Save New Password", self) 
        reset_btn.setFixedWidth(input_width)
        reset_btn.setFixedHeight(45)
        reset_btn.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        reset_btn.setStyleSheet(
            "QPushButton { background:#004aad; color:white; border-radius:10px; } QPushButton:hover { background:#003580; }"
        )
        reset_btn.clicked.connect(self.perform_reset) 
        reset_btn.setGeometry(x_input, current_y + 10, input_width, 45)

        back_link = QPushButton("Back to Login", self) 
        back_link.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        back_link.setStyleSheet("""
            QPushButton { border:none; background:transparent; color:black; } 
            QPushButton:hover { text-decoration:underline; }
        """)
        back_link.clicked.connect(self.switch_to_login.emit)
        back_link.setGeometry(x_input, current_y + 60, input_width, 30) 
        
        self.bg_label.lower()

    def clear_fields(self):
        self.user_input.clear()
        self.email_input.clear()
        self.new_pass_input.clear()
        self.confirm_pass_input.clear()

    def perform_reset(self):
        username = self.user_input.text().strip()
        email = self.email_input.text().strip()
        new_pass = self.new_pass_input.text().strip()
        confirm_pass = self.confirm_pass_input.text().strip()

        if not username or not email or not new_pass or not confirm_pass:
            QMessageBox.warning(self, "ข้อมูลไม่ครบ", "⚠️ กรุณากรอกข้อมูลให้ครบทุกช่อง")
            return

        conn = sqlite3.connect("users.db")
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND email=?", (username, email))
        row = cur.fetchone()
        
        if not row:
            conn.close()
            QMessageBox.warning(self, "Error", "⚠️ Username หรือ Email ไม่ถูกต้อง")
            self.clear_fields()
            return
            
        if len(new_pass) < 8:
            QMessageBox.warning(self, "รหัสสั้นเกินไป", "❌ รหัสผ่านใหม่ต้องมีอย่างน้อย 8 ตัวอักษร")
            self.new_pass_input.clear()
            self.confirm_pass_input.clear()
            conn.close()
            return
            
        if new_pass != confirm_pass:
            QMessageBox.warning(self, "รหัสไม่ตรงกัน", "❌ รหัสผ่านใหม่และการยืนยันไม่ตรงกัน")
            self.new_pass_input.clear()
            self.confirm_pass_input.clear()
            conn.close()
            return

        try:
            hashed_new_pass = hash_password(new_pass)
            cur.execute("UPDATE users SET password=? WHERE username=?", (hashed_new_pass, username))
            conn.commit()
            conn.close()
            
            QMessageBox.information(self, "สำเร็จ", "✅ เปลี่ยนรหัสผ่านสำเร็จ! กรุณาเข้าสู่ระบบใหม่")
            self.clear_fields()
            self.switch_to_login.emit() 
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"เกิดข้อผิดพลาด: {e}")
            conn.close()

    def resizeEvent(self, event: QResizeEvent):
        if hasattr(self, 'bg_label'):
            self.bg_label.resize(self.size())
        super().resizeEvent(event)


# =========================
# 🔹 Profile Page
# =========================
class ProfilePage(QWidget):
    def __init__(self):
        super().__init__()
        self.username = None
        self.edit_mode = False
        self.profile_pic_path = None
        self.initUI()
        self.apply_styles() # (เพิ่มฟังก์ชันสำหรับ QSS)

    def initUI(self):
        # ---- 1. Layout หลัก (VBox) ----
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 30, 40, 40) # (เพิ่มระยะขอบ)
        main_layout.setSpacing(25)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setStyleSheet("background-color: #f5f5f5;") # (สีพื้นหลัง)

        # ---- 2. Title ----
        title = QLabel("My Profile")
        title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        title.setObjectName("ProfileTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main_layout.addWidget(title)

        # ---- 3. Content Layout (HBox: ซ้าย-ขวา) ----
        content_layout = QHBoxLayout()
        content_layout.setSpacing(30)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.addLayout(content_layout, 1) # (ให้ยืดเต็มพื้นที่)

        # ---- 4. แผงด้านซ้าย (รูป & ชื่อ) ----
        left_panel = QFrame()
        left_panel.setObjectName("ProfileCard")
        left_panel.setFixedWidth(350)
        
        left_panel_layout = QVBoxLayout(left_panel)
        left_panel_layout.setContentsMargins(25, 30, 25, 30)
        left_panel_layout.setSpacing(15)
        left_panel_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # (รูปโปรไฟล์)
        self.profile_pic = QLabel()
        self.profile_pic.setFixedSize(180, 180) # (ขนาดรูป)
        self.profile_pic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.profile_pic.setObjectName("ProfilePicLabel")
        # ❗ [แก้ไข] เปลี่ยนเป็นสี่เหลี่ยม
        self.profile_pic.setStyleSheet("border-radius: 0px; background-color: #e0e0e0; border: 4px solid #f0f0f0;")
        left_panel_layout.addWidget(self.profile_pic, alignment=Qt.AlignmentFlag.AlignCenter)

        # (ปุ่มเปลี่ยนรูป)
        self.change_pic_btn = QPushButton("เปลี่ยนรูปโปรไฟล์")
        self.change_pic_btn.setObjectName("ChangePicButton")
        self.change_pic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.change_pic_btn.clicked.connect(self.change_profile_picture)
        left_panel_layout.addWidget(self.change_pic_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        left_panel_layout.addSpacing(10)
        
        # ❗ (ลบ @username และ full_name ออกแล้ว)
        
        left_panel_layout.addStretch()
        content_layout.addWidget(left_panel)
        
        # (เพิ่ม Shadow ให้การ์ดซ้าย)
        shadow_left = QGraphicsDropShadowEffect(self)
        shadow_left.setBlurRadius(25)
        shadow_left.setXOffset(0)
        shadow_left.setYOffset(4)
        shadow_left.setColor(QColor(0, 0, 0, 60))
        left_panel.setGraphicsEffect(shadow_left)


        # ---- 5. แผงด้านขวา (ฟอร์มแก้ไข) ----
        right_panel = QFrame()
        right_panel.setObjectName("DetailsCard")
        
        right_panel_layout = QVBoxLayout(right_panel)
        right_panel_layout.setContentsMargins(30, 25, 30, 30)
        right_panel_layout.setSpacing(20)
        right_panel_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # (Header ของการ์ดขวา + ปุ่ม Edit)
        details_header_layout = QHBoxLayout()
        details_title = QLabel("ข้อมูลส่วนตัว")
        details_title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        details_title.setObjectName("DetailsTitle")
        details_header_layout.addWidget(details_title)
        details_header_layout.addStretch()
        
        self.edit_btn = QPushButton("✏️ แก้ไขข้อมูล")
        self.edit_btn.setObjectName("EditButton")
        self.edit_btn.setCheckable(True) # (ทำให้เป็นปุ่ม Toggle)
        self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_btn.clicked.connect(self.toggle_edit_mode)
        details_header_layout.addWidget(self.edit_btn)
        
        right_panel_layout.addLayout(details_header_layout)

        # (เส้นคั่น)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("SeparatorLine")
        right_panel_layout.addWidget(line)
        
        # (Grid Layout สำหรับฟอร์ม)
        self.form_layout = QGridLayout()
        self.form_layout.setSpacing(20)
        self.form_layout.setColumnStretch(1, 1) # (ให้ช่องกรอกยืดได้)
        right_panel_layout.addLayout(self.form_layout)

        self.fields = {
            "first_name": ("ชื่อจริง:", QLineEdit()),
            "last_name": ("นามสกุล:", QLineEdit()),
            "email": ("อีเมล:", QLineEdit()),
            "phone": ("เบอร์โทรศัพท์:", QLineEdit())
        }
        
        row = 0
        for key, (label_text, widget) in self.fields.items():
            label = QLabel(label_text)
            label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            label.setObjectName("FieldLabel")
            
            widget.setFont(QFont("Arial", 14))
            widget.setReadOnly(True) # (เริ่มแบบอ่านอย่างเดียว)
            
            if key == "phone":
                widget.setValidator(QIntValidator())

            # ❗ [แก้ไข] จัดชิดขวา และ กลางแนวตั้ง
            self.form_layout.addWidget(label, row, 0, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.form_layout.addWidget(widget, row, 1)
            row += 1

        right_panel_layout.addStretch()
        
        # (ปุ่ม Save / Cancel - ซ่อนไว้)
        self.save_cancel_widget = QWidget()
        save_cancel_layout = QHBoxLayout(self.save_cancel_widget)
        save_cancel_layout.setContentsMargins(0, 0, 0, 0)
        save_cancel_layout.addStretch()
        
        self.cancel_btn = QPushButton("ยกเลิก")
        self.cancel_btn.setObjectName("CancelButton")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.disable_edit_mode)
        
        self.save_btn = QPushButton("💾 บันทึกการเปลี่ยนแปลง")
        self.save_btn.setObjectName("SaveButton")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_profile)
        
        save_cancel_layout.addWidget(self.cancel_btn)
        save_cancel_layout.addWidget(self.save_btn)
        
        right_panel_layout.addWidget(self.save_cancel_widget)
        self.save_cancel_widget.setVisible(False) # (ซ่อนไว้ก่อน)

        content_layout.addWidget(right_panel, 1) # (ยืด 1 ส่วน)
        
        # (เพิ่ม Shadow ให้การ์ดขวา)
        shadow_right = QGraphicsDropShadowEffect(self)
        shadow_right.setBlurRadius(25)
        shadow_right.setXOffset(0)
        shadow_right.setYOffset(4)
        shadow_right.setColor(QColor(0, 0, 0, 60))
        right_panel.setGraphicsEffect(shadow_right)
        
    def apply_styles(self):
        self.setStyleSheet("""
            QWidget { background-color: #f5f5f5; }
            QLabel#ProfileTitle { 
                color: #2c3e50; 
                background-color: transparent; /* ❗ (แก้พื้นหลังโปร่งใส) */
            }
            
            /* --- การ์ดซ้าย (โปรไฟล์) --- */
            QFrame#ProfileCard {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
            }
            QLabel#ProfilePicLabel {
                border: 4px solid #f0f0f0;
                background-color: #e0e0e0;
                border-radius: 0px; /* ❗ [แก้ไข] เป็นสี่เหลี่ยม */
            }
            QPushButton#ChangePicButton {
                background-color: #f0f0f0;
                color: #333;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 8px;
                border: 1px solid #ccc;
            }
            QPushButton#ChangePicButton:hover {
                background-color: #e0e0e0;
            }

            /* --- การ์ดขวา (รายละเอียด) --- */
            QFrame#DetailsCard {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
            }
            QLabel#DetailsTitle {
                color: #2c3e50;
                background-color: transparent; /* ❗ (แก้พื้นหลังโปร่งใส) */
            }
            QLabel#FieldLabel {
                color: #004aad;
                border: none;
                background-color: transparent; /* ❗ (แก้พื้นหลังโปร่งใส) */
            }
            QFrame#SeparatorLine {
                background-color: #f0f0f0;
                height: 1px;
                border: none;
            }
            QLineEdit {
                background-color: #fdfdfd;
                border: 1px solid #d5d5d5;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                color: #333;
            }
            QLineEdit:read-only {
                background-color: #f5f5f5;
                color: #444;
                border: 1px solid #f5f5f5;
            }
            QLineEdit:focus {
                border: 2px solid #004aad;
            }

            /* --- ปุ่ม Actions --- */
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 8px;
            }
            QPushButton#EditButton {
                background-color: #004aad;
                color: white;
            }
            QPushButton#EditButton:hover { background-color: #003580; }
            QPushButton#EditButton:checked {
                background-color: #f0f0f0;
                color: #555;
                border: 1px solid #ccc;
            }
            
            QPushButton#SaveButton {
                background-color: #008c4a;
                color: white;
            }
            QPushButton#SaveButton:hover { background-color: #006a38; }
            
            QPushButton#CancelButton {
                background-color: #f0f0f0;
                color: #333;
                border: 1px solid #ccc;
            }
            QPushButton#CancelButton:hover { background-color: #e0e0e0; }
        """)

    def load_user(self, username):
        self.username = username
        if not username:
            self.clear()
            # ❗ (ลบการอ้างอิง username_label)
            return

        conn = sqlite3.connect("users.db")
        cur = conn.cursor()
        cur.execute("""
            SELECT first_name, last_name, email, phone, profile_pic
            FROM users WHERE username=?
        """, (username,))
        row = cur.fetchone()
        conn.close()

        if row:
            first, last, email, phone, pic = row
            # ❗ (ลบการอ้างอิง full_name)
            
            self.fields["first_name"][1].setText(first or "")
            self.fields["last_name"][1].setText(last or "")
            self.fields["email"][1].setText(email or "")
            self.fields["phone"][1].setText(phone or "")
            
            # ❗ (ลบการอ้างอิง username_label และ full_name_label)
            
            self.profile_pic_path = pic
            self.display_profile_picture()
        else:
            self.clear()
            # ❗ (ลบการอ้างอิง username_label และ full_name_label)

    def display_profile_picture(self):
        if self.profile_pic_path and os.path.exists(self.profile_pic_path):
            # ❗ [แก้ไข] เปลี่ยนไปใช้ set_square_image
            self.set_square_image(self.profile_pic_path) 
            # ❗ [แก้ไข] เปลี่ยน border-radius เป็น 0px
            self.profile_pic.setStyleSheet("border: 4px solid #004aad; border-radius: 0px;") 
        else:
            self.profile_pic.clear()
            self.profile_pic.setText("👤") # (Icon Placeholder)
            self.profile_pic.setFont(QFont("Arial", 80))
            # ❗ [แก้ไข] เปลี่ยน border-radius เป็น 0px
            self.profile_pic.setStyleSheet("border: 4px solid #e0e0e0; border-radius: 0px; background-color: #f9f9f9; color: #ccc;")

    def toggle_edit_mode(self, checked):
        if checked:
            # (กำลังเข้าสู่โหมด Edit)
            self.edit_mode = True
            self.save_cancel_widget.setVisible(True)
            self.edit_btn.setText("...กำลังแก้ไข")
            for _, widget in self.fields.values():
                widget.setReadOnly(False)
        else:
            # (กำลังออกจากโหมด Edit - เหมือนกดยกเลิก)
            self.disable_edit_mode()

    def disable_edit_mode(self):
        """(ยกเลิก) โหลดข้อมูลเดิมกลับมาและล็อกฟอร์ม"""
        self.edit_mode = False
        self.save_cancel_widget.setVisible(False)
        self.edit_btn.setChecked(False) # (เอาติ๊กถูกออกจากปุ่ม Edit)
        self.edit_btn.setText("✏️ แก้ไขข้อมูล")
        for _, widget in self.fields.values():
            widget.setReadOnly(True)
        self.load_user(self.username) # (โหลดข้อมูลเดิมทับ)

    def save_profile(self):
        data = {key: widget.text().strip() for key, (_, widget) in self.fields.items()}
        
        if not data["first_name"] or not data["last_name"] or not data["email"]:
            QMessageBox.warning(self, "ข้อมูลไม่ครบ", "⚠️ กรุณากรอกชื่อ, นามสกุล และอีเมล")
            return

        conn = sqlite3.connect("users.db")
        cur = conn.cursor()
        cur.execute("""
            UPDATE users
            SET first_name=?, last_name=?, email=?, phone=?, profile_pic=?
            WHERE username=?
        """, (
            data["first_name"], data["last_name"], data["email"],
            data["phone"], self.profile_pic_path, self.username
        ))
        conn.commit()
        conn.close()

        QMessageBox.information(self, "สำเร็จ", "✅ บันทึกข้อมูลเรียบร้อยแล้ว")
        self.disable_edit_mode() # (ปิดโหมดแก้ไข)

    def change_profile_picture(self):
        # (ฟังก์ชันนี้ควรทำงานได้ไม่ว่า
        if not self.username:
             QMessageBox.warning(self, "Error", "กรุณาล็อกอินก่อนเปลี่ยนรูปภาพ")
             return

        file_path, _ = QFileDialog.getOpenFileName(self, "เลือกรูปโปรไฟล์", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            os.makedirs("profile_pics", exist_ok=True)
            # (ตั้งชื่อไฟล์ให้ไม่ซ้ำกัน)
            timestamp = QDateTime.currentDateTime().toString("yyyyMMddhhmmss")
            _, ext = os.path.splitext(file_path)
            new_name = f"{self.username}_{timestamp}{ext}"
            new_path = os.path.join("profile_pics", new_name)
            
            try:
                shutil.copy(file_path, new_path)
                
                # (อัปเดต DB ทันที)
                conn = sqlite3.connect("users.db")
                cur = conn.cursor()
                cur.execute("UPDATE users SET profile_pic=? WHERE username=?", (new_path, self.username))
                conn.commit()
                conn.close()
                
                self.profile_pic_path = new_path
                self.display_profile_picture()
                QMessageBox.information(self, "สำเร็จ", "✅ อัปเดตรูปโปรไฟล์เรียบร้อยแล้ว")
                
            except Exception as e:
                QMessageBox.critical(self, "เกิดข้อผิดพลาด", f"ไม่สามารถบันทึกรูปภาพได้: {e}")

    def clear(self):
        for _, widget in self.fields.values():
            widget.setText("")
        self.profile_pic.clear()
        self.profile_pic.setText("👤")
        self.profile_pic.setFont(QFont("Arial", 80))
        # ❗ [แก้ไข] เปลี่ยน border-radius เป็น 0px
        self.profile_pic.setStyleSheet("border: 4px solid #e0e0e0; border-radius: 0px; background-color: #f9f9f9; color: #ccc;")
        # ❗ (ลบการอ้างอิง username_label และ full_name_label)

    # ❗ [แก้ไข] เปลี่ยนชื่อฟังก์ชันจาก set_circle_image เป็น set_square_image
    def set_square_image(self, image_path): 
        # (ขนาดคงที่ 180x180)
        original_pixmap = QPixmap(image_path)
        
        if original_pixmap.isNull():
            # (ถ้าโหลดภาพไม่ได้ ให้ใช้ภาพ placeholder)
            placeholder = QPixmap(180, 180)
            placeholder.fill(Qt.GlobalColor.lightGray)
            self.profile_pic.setPixmap(placeholder)
            return

        # (ปรับขนาดภาพให้พอดีกับ 180x180 โดยไม่บิดเบี้ยว)
        # (จะย่อ/ขยายรูปให้ด้านที่สั้นที่สุดพอดีกับ 180px แล้วครอบตัดส่วนเกินออก)
        scaled_pixmap = original_pixmap.scaled(
            180, 180, 
            Qt.AspectRatioMode.KeepAspectRatioByExpanding, # ❗ [แก้ไข] ให้ขยายและครอบตัด
            Qt.TransformationMode.SmoothTransformation
        )

        # (ครอบตัดตรงกลางเพื่อให้ได้ขนาด 180x180 พอดี)
        x_offset = (scaled_pixmap.width() - 180) // 2
        y_offset = (scaled_pixmap.height() - 180) // 2
        
        cropped_pixmap = scaled_pixmap.copy(
            x_offset, y_offset, 
            180, 180
        )
        
        self.profile_pic.setPixmap(cropped_pixmap)

# =========================
# 🔹 MainApp (แก้ไข - รวมทุกอย่าง)
# =========================
class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Arai Football Shop")
        self.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                color: black;
            }
        """)
        self.image_folder = "C:/project/picture/"
        self.current_user = None
        
        self.cart = [] 
        
        self.is_buy_now_flow = False # (เหมือนเดิม)

        # ==================================================
        # 🔹 Layout
        # ==================================================
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0) 

        self.sidebar = Sidebar(self.image_folder)
        self.sidebar.menu_clicked.connect(self.handle_menu)
        main_layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)
        
        main_layout.setStretch(1, 1)
        # ==================================================

        # ✅ สร้างหน้าต่างๆ
        self.home_page = HomePage(self.image_folder)
        self.products_page = ProductsPage(self.image_folder)
        self.cart_page = CartPage(self.image_folder)
        
        self.product_detail_page = ProductDetailPage(self.image_folder)
        
        self.payment_page = PaymentPage(self.image_folder)
        self.orders_page = OrdersPage() # (เหมือนเดิม)

        self.login_page = LoginPage()
        self.signup_page = SignupPage()
        self.forgot_page = ForgotPasswordPage()
        self.profile_page = ProfilePage()
        self.contact_page = ContactPage(self.image_folder)
        self.contact_admin_page = ContactAdminPage()

        # ✅ เชื่อมสัญญาณเปลี่ยนหน้า
        self.login_page.switch_to_signup.connect(lambda: self.stack.setCurrentWidget(self.signup_page))
        self.signup_page.switch_to_login.connect(lambda: self.stack.setCurrentWidget(self.login_page))
        self.login_page.switch_to_forgot.connect(lambda: self.stack.setCurrentWidget(self.forgot_page))
        self.forgot_page.switch_to_login.connect(lambda: self.stack.setCurrentWidget(self.login_page))

        # (เหมือนเดิม) เชื่อมสัญญาณจาก ProductsPage และ CartPage และ DetailPage
        self.products_page.add_to_cart_signal.connect(self.add_item_to_cart)
        self.products_page.view_details_signal.connect(self.show_product_details) 
        
        self.cart_page.item_removed.connect(self.remove_item_from_cart) 
        self.cart_page.checkout_signal.connect(self.show_payment_page) 
        
        self.product_detail_page.back_to_products_signal.connect(self.show_products_page) 
        self.product_detail_page.add_to_cart_signal.connect(self.add_item_to_cart) 
        self.product_detail_page.buy_now_signal.connect(self.handle_buy_now) 

        # (เหมือนเดิม) เชื่อมสัญญาณจาก PaymentPage
        self.payment_page.payment_cancelled_signal.connect(self.show_cart_page)
        self.payment_page.payment_confirmed_signal.connect(self.handle_payment_success)


        # ✅ เพิ่มทุกหน้าลงใน stack (ครั้งเดียว)
        for page in [
            self.home_page,
            self.products_page,
            self.cart_page,
            self.product_detail_page, 
            self.payment_page, # (เหมือนเดิม)
            self.orders_page, # (เหมือนเดิม)
            self.contact_page,
            self.contact_admin_page,
            self.profile_page,
            self.login_page,
            self.signup_page,
            self.forgot_page
        ]:
            self.stack.addWidget(page)

        self.setCentralWidget(central)

        self._hook_login_button()

        self.stack.setCurrentWidget(self.home_page)
        if "Homepage" in self.sidebar.buttons:
             self.sidebar.buttons["Homepage"].setChecked(True)

        self.update_sidebar_buttons()

    # -----------------------------
    # ฟังก์ชันจัดการตะกร้า
    # -----------------------------
    
    def add_item_to_cart(self, product_data):
        product_id = product_data['id']
        
        selected_size = product_data.get('selected_size', 'N/A') 
        quantity_to_add = product_data.get('quantity_to_add', 1) 
        
        # ❗ (เพิ่ม) ดึงสต็อกสูงสุดที่มี
        quantity_stock = product_data.get('quantity_stock', 0)
        
        # ❗ (เพิ่ม) ตรวจสอบสต็อกก่อนเพิ่ม
        
        # 1. หาสินค้าตัวนี้ (ID และ Size เดียวกัน) ที่มีในตะกร้าอยู่แล้ว
        found_item = None
        current_cart_qty = 0
        for item in self.cart:
            if item['id'] == product_id and item['size'] == selected_size:
                found_item = item
                current_cart_qty = item['quantity']
                break
        
        # 2. เช็คว่าถ้าเพิ่มเข้าไปแล้ว จะเกินสต็อกหรือไม่
        if (current_cart_qty + quantity_to_add) > quantity_stock:
            QMessageBox.warning(self, "สินค้าในสต็อกไม่พอ",
                f"ไม่สามารถเพิ่ม '{product_data['name']}' (Size: {selected_size}) ได้\n\n"
                f"- สต็อกคงเหลือ: {quantity_stock} ชิ้น\n"
                f"- มีในตะกร้าแล้ว: {current_cart_qty} ชิ้น\n"
                f"- คุณพยายามเพิ่มอีก: {quantity_to_add} ชิ้น"
            )
            return # ❗ หยุดการทำงานทันที
            

        # 3. (ส่วนนี้เหมือนเดิม) ถ้าไม่เกิน ก็เพิ่ม/อัปเดตตะกร้า
        try:
            price_str = product_data.get('price_str')
            if price_str:
                cleaned_price = int(price_str.replace('฿', '').replace(',', ''))
            else:
                price_int = product_data.get('price')
                if price_int:
                    cleaned_price = int(price_int)
                else:
                    price_str = product_data.get('price_str', "฿0")
                    cleaned_price = int(price_str.replace('฿', '').replace(',', ''))
        
        except Exception as e:
             print(f"Error parsing price {product_data.get('price_str')}: {e}")
             QMessageBox.warning(self, "Error", "⚠️ เกิดข้อผิดพลาดเรื่องราคา")
             return

        if found_item:
            found_item['quantity'] += quantity_to_add
        else:
            new_item = {
                'id': product_id,
                'name': product_data['name'],
                'image_path': product_data['image_path'],
                'price': cleaned_price, 
                'quantity': quantity_to_add, 
                'size': selected_size,
                'quantity_stock': quantity_stock # ❗ (เพิ่ม) เก็บสต็อกไว้ในตะกร้าด้วย
            }
            self.cart.append(new_item)
            
        QMessageBox.information(self, "เพิ่มสินค้าแล้ว", 
                                f"✅ เพิ่ม '{product_data['name']} (Size: {selected_size})' \nจำนวน {quantity_to_add} ชิ้น ลงในตะกร้า")
        
        if self.stack.currentWidget() == self.cart_page:
            self.cart_page.load_cart_items(self.cart)

    def remove_item_from_cart(self, cart_key):
        # ... (ส่วนนี้เหมือนเดิมครับ) ...
        product_id, product_size = cart_key 
        
        item_to_remove = None
        for item in self.cart:
            if item['id'] == product_id and item.get('size', 'N/A') == product_size:
                item_to_remove = item
                break
        
        if item_to_remove:
            self.cart.remove(item_to_remove)
            self.cart_page.load_cart_items(self.cart)
            QMessageBox.information(self, "ลบสินค้าแล้ว", f"ลบ '{item_to_remove['name']} (Size: {product_size})' ออกจากตะกร้า")

    # -----------------------------
    # ฟังก์ชันสลับหน้า
    # -----------------------------
    def show_product_details(self, product_data):
        # ... (ส่วนนี้เหมือนเดิมครับ) ...
        self.product_detail_page.load_product_details(product_data)
        self.stack.setCurrentWidget(self.product_detail_page)
        
        if "Products" in self.sidebar.buttons:
            self.sidebar.buttons["Products"].setChecked(True)

    def show_products_page(self):
        # ... (ส่วนนี้เหมือนเดิมครับ) ...
        self.stack.setCurrentWidget(self.products_page)
        if "Products" in self.sidebar.buttons:
            self.sidebar.buttons["Products"].setChecked(True)
    
    # -----------------------------
    # ❗ ฟังก์ชันใหม่สำหรับ Payment Workflow
    # -----------------------------
    def show_payment_page(self):
        """(แก้ไข) ถูกเรียกโดย CartPage เมื่อกด 'ดำเนินการชำระเงิน'"""
        
        self.is_buy_now_flow = False # ❗ (ตั้งสถานะว่า มาจากตะกร้า)
        
        if not self.current_user:
            QMessageBox.warning(self, "จำเป็นต้องเข้าสู่ระบบ", "⚠️ กรุณาเข้าสู่ระบบก่อนดำเนินการชำระเงิน")
            self.sidebar.buttons["Cart"].setChecked(False)
            self.sidebar.buttons["Login"].setChecked(True)
            self.stack.setCurrentWidget(self.login_page)
            return

        cart_items = self.cart
        
        # ❗ (เพิ่ม) ตรวจสอบสต็อกในตะกร้าทั้งหมดอีกครั้ง ก่อนไปหน้าชำระเงิน
        insufficient_items = []
        for item in cart_items:
            # (เราเก็บ quantity_stock ไว้ใน cart ตอน add_item_to_cart แล้ว)
            stock = item.get('quantity_stock', 0)
            if item['quantity'] > stock:
                insufficient_items.append(
                    f"- {item['name']} (Size: {item['size']})\n"
                    f"  (ต้องการ: {item['quantity']}, มีในสต็อก: {stock})"
                )
        
        if insufficient_items:
            msg = "ขออภัย, สินค้าในสต็อกไม่พอ:\n\n" + "\n".join(insufficient_items) + \
                  "\n\nกรุณากลับไปที่ตะกร้าเพื่อแก้ไขจำนวน"
            QMessageBox.warning(self, "สต็อกไม่พอ", msg)
            
            # บังคับกลับไปหน้าตะกร้า
            self.stack.setCurrentWidget(self.cart_page) 
            self.sidebar.buttons["Cart"].setChecked(True)
            return # ❗ หยุด ไม่ไปหน้า Payment
            

        # (ถ้าสต็อกพอ ก็ไปต่อตามปกติ)
        total_info = {
            'subtotal': self.cart_page.current_subtotal,
            'vat': self.cart_page.current_vat,
            'grand_total': self.cart_page.current_grand_total
        }
        
        self.payment_page.load_order_details(
            self.current_user, 
            cart_items, 
            total_info
        )
        
        self.stack.setCurrentWidget(self.payment_page)
        self.sidebar.buttons["Cart"].setChecked(True)

    def show_cart_page(self):
        # ... (ส่วนนี้เหมือนเดิมครับ) ...
        
        if self.is_buy_now_flow:
            self.is_buy_now_flow = False # (รีเซ็ตสถานะ)
            self.stack.setCurrentWidget(self.product_detail_page) # กลับไปหน้า Detail
            if "Products" in self.sidebar.buttons:
                self.sidebar.buttons["Products"].setChecked(True)
        else:
            # (ถ้ามาจากตะกร้าปกติ ก็กลับไปหน้าตะกร้า)
            self.stack.setCurrentWidget(self.cart_page)
            if "Cart" in self.sidebar.buttons:
                self.sidebar.buttons["Cart"].setChecked(True)


    def handle_payment_success(self, order_id, receipt_text, cart_items): # ❗ (1. เพิ่ม cart_items)
        """(แก้ไข) ถูกเรียกโดย PaymentPage เมื่อยืนยันสำเร็จ"""
        
        # ❗ (2. เพิ่ม) นี่คือส่วน "ตัดสต็อก" ที่เพิ่มเข้ามา
        try:
            # (เชื่อมต่อกับ products.db)
            conn = sqlite3.connect(self.products_page.db_path) 
            cur = conn.cursor()
            
            for item in cart_items:
                product_id = item['id']
                quantity_purchased = item['quantity']
                
                # คำสั่ง SQL: ลด quantity ลงตามจำนวนที่ซื้อ โดยอ้างอิงจาก id
                # (เราเช็ค AND quantity >= ? เพื่อป้องกันสต็อกติดลบหากเกิดข้อผิดพลาด)
                cur.execute("""
                    UPDATE products 
                    SET quantity = quantity - ? 
                    WHERE id = ? AND quantity >= ?
                """, (quantity_purchased, product_id, quantity_purchased))
                
                print(f"Stock updated for ID {product_id}, removed {quantity_purchased}")

            conn.commit()
            conn.close()
            
            # (รีเฟรชข้อมูลสินค้าในหน้า ProductsPage ทันที)
            self.products_page.load_products()
            self.products_page.display_products(self.products_page.products)

        except Exception as e:
            print(f"!!! CRITICAL ERROR: FAILED TO UPDATE STOCK !!! - {e}")
            QMessageBox.critical(self, "Stock Update Error",
                f"เกิดข้อผิดพลาดร้ายแรงในการตัดสต็อก: {e}\n\n"
                f"กรุณาตรวจสอบฐานข้อมูลสินค้า (products.db) ด้วยตนเอง!")
        
        if not self.is_buy_now_flow:
            # 1. ล้างตะกร้า (เฉพาะเมื่อซื้อจากตะกร้า)
            self.cart = []
            # 2. อัปเดตหน้าตะกร้า (ให้มันโล่ง)
            self.cart_page.load_cart_items(self.cart)
        
        # (รีเซ็ตสถานะกลับเป็นปกติ)
        self.is_buy_now_flow = False 
        
        # 3. แสดงใบเสร็จ (เหมือนเดิม)
        self.show_receipt_dialog(receipt_text)
        
        # 4. กลับไปหน้า Home (เหมือนเดิม)
        self.stack.setCurrentWidget(self.home_page)
        if "Homepage" in self.sidebar.buttons:
            self.sidebar.buttons["Homepage"].setChecked(True)

    def show_receipt_dialog(self, receipt_text):
        # ... (ส่วนนี้เหมือนเดิมครับ) ...
        dialog = ReceiptDialog(receipt_text, self)
        dialog.exec()
        
    def handle_buy_now(self, product_data):
        """(แก้ไข) ถูกเรียกโดย ProductDetailPage เมื่อกด 'ซื้อเลย'"""
        
        self.is_buy_now_flow = True # ❗ (ตั้งสถานะว่า "ซื้อเลย")

        if not self.current_user:
            QMessageBox.warning(self, "จำเป็นต้องเข้าสู่ระบบ", "⚠️ กรุณาเข้าสู่ระบบก่อนดำเนินการชำระเงิน")
            if "Products" in self.sidebar.buttons:
                self.sidebar.buttons["Products"].setChecked(True) 
            self.stack.setCurrentWidget(self.login_page)
            return
        
        # ❗ (เพิ่ม) ตรวจสอบสต็อกทันที
        quantity_stock = product_data.get('quantity_stock', 0)
        quantity_to_add = product_data.get('quantity_to_add', 1)
        
        # (SpinBox ใน DetailPage ป้องกันการเลือกเกินอยู่แล้ว แต่เช็คอีกครั้งกันเหนียว)
        if quantity_to_add > quantity_stock:
            QMessageBox.warning(self, "สินค้าไม่พอ",
                f"ไม่สามารถซื้อ '{product_data['name']}' ได้\n\n"
                f"- สต็อกคงเหลือ: {quantity_stock} ชิ้น\n"
                f"- คุณพยายามซื้อ: {quantity_to_add} ชิ้น"
            )
            self.is_buy_now_flow = False # ยกเลิกสถานะ
            return
            
        # (ถ้าสต็อกพอ ก็ไปต่อ)
        
        try:
            price_str = product_data.get('price_str', "฿0")
            cleaned_price = int(price_str.replace('฿', '').replace(',', ''))
        except Exception as e:
            print(f"Error parsing price {price_str}: {e}")
            QMessageBox.warning(self, "Error", "⚠️ เกิดข้อผิดพลาดเรื่องราคา")
            self.is_buy_now_flow = False # ยกเลิกสถานะ
            return

        quantity = product_data.get('quantity_to_add', 1)
        
        temp_cart_items = [{
            'id': product_data['id'],
            'name': product_data['name'],
            'image_path': product_data['image_path'],
            'price': cleaned_price,
            'quantity': quantity,
            'size': product_data.get('selected_size', 'N/A'),
            'quantity_stock': quantity_stock # ❗ (เพิ่ม) ส่งสต็อกไปหน้า Payment
        }]

        subtotal = cleaned_price * quantity
        vat = subtotal * 0.07
        grand_total = subtotal + vat
        
        temp_total_info = {
            'subtotal': subtotal,
            'vat': vat,
            'grand_total': grand_total
        }

        self.payment_page.load_order_details(
            self.current_user, 
            temp_cart_items, 
            temp_total_info
        )
        
        self.stack.setCurrentWidget(self.payment_page)
        
        if "Products" in self.sidebar.buttons:
            self.sidebar.buttons["Products"].setChecked(True)
    # -----------------------------
    
    # ... (ส่วนที่เหลือของ MainApp เช่น _hook_login_button, perform_login, 
    # handle_menu, pages_mapping, update_user_status, update_sidebar_buttons
    # ไม่มีการเปลี่ยนแปลงครับ) ...
    
    # -----------------------------
    # Hook login button
    # -----------------------------
    def _hook_login_button(self):
        for btn in self.login_page.findChildren(QPushButton):
            try:
                if btn.text().strip().lower() == "login":
                    try:
                        btn.clicked.disconnect()
                    except Exception:
                        pass
                    btn.clicked.connect(self.perform_login)
                    break
            except Exception:
                continue

    # -----------------------------
    # perform login -> set current_user
    # -----------------------------
    def perform_login(self):
        username = self.login_page.user_input.text().strip()
        password = self.login_page.pass_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Missing Info", "⚠️ กรุณากรอกชื่อผู้ใช้และรหัสผ่าน")
            return

        conn = sqlite3.connect("users.db")
        cur = conn.cursor()
        cur.execute("SELECT password FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        conn.close()

        if row is None:
            QMessageBox.warning(self, "User Not Found", "❌ ไม่พบบัญชีผู้ใช้นี้")
            self.login_page.user_input.clear() 
            self.login_page.pass_input.clear()
            return
        elif row[0] != hash_password(password):
            QMessageBox.warning(self, "Wrong Password", "❌ รหัสผ่านไม่ถูกต้อง")
            self.login_page.pass_input.clear()
            return

        self.current_user = username
        
        self.cart = [] # ❗ (ล้างตะกร้าของ Guest เมื่อล็อกอิน)
        if self.stack.currentWidget() == self.cart_page:
            self.cart_page.load_cart_items(self.cart)

        if username == "admin":
            QMessageBox.information(self, "Admin Login", "👑 เข้าสู่ระบบในฐานะผู้ดูแล (Admin)")
            import subprocess, sys, os
            admin_path = "C:/project/new/addedit.py" 
            if os.path.exists(admin_path):
                subprocess.Popen([sys.executable, admin_path])
                QApplication.instance().quit()
            else:
                QMessageBox.warning(self, "Error", f"❌ ไม่พบไฟล์ {admin_path}")
            return
        else:
            QMessageBox.information(self, "Login Success", f"✅ ยินดีต้อนรับ {username}")
            self.update_sidebar_buttons() 
            self.update_user_status()   
            
            self.login_page.user_input.clear()
            self.login_page.pass_input.clear()
            
            self.stack.setCurrentWidget(self.home_page)
            if "Homepage" in self.sidebar.buttons:
                self.sidebar.buttons["Homepage"].setChecked(True)

    # -----------------------------
    # handle menu clicks
    # -----------------------------
    def handle_menu(self, name):
        # (รีเซ็ตสถานะ "ซื้อเลย" ทุกครั้งที่คลิกเมนู)
        self.is_buy_now_flow = False
        
        if name == "Profile":
            if self.current_user is None:
                QMessageBox.information(self, "ยังไม่ได้เข้าสู่ระบบ", "⚠️ กรุณาเข้าสู่ระบบเพื่อดูหน้าโปรไฟล์")
                self.sidebar.buttons["Profile"].setChecked(False)
                if "Homepage" in self.sidebar.buttons:
                    self.sidebar.buttons["Homepage"].setChecked(True) 
                self.stack.setCurrentWidget(self.home_page)
                return
            else:
                self.profile_page.load_user(self.current_user)
                self.stack.setCurrentWidget(self.profile_page)
                return

        if name == "Cart":
            self.cart_page.load_cart_items(self.cart)
            self.stack.setCurrentWidget(self.cart_page)
            return

        if name == "Contact":
            self.contact_page.load_user_data(self.current_user)
            self.stack.setCurrentWidget(self.contact_page)
            return

        if name == "Logout":
            if self.current_user is None:
                QMessageBox.information(self, "ยังไม่ได้เข้าสู่ระบบ", "⚠️ คุณยังไม่ได้เข้าสู่ระบบ")
                self.sidebar.buttons["Logout"].setChecked(False) 
                return
            reply = QMessageBox.question(
                self,
                "ยืนยันการออกจากระบบ",
                f"คุณต้องการออกจากระบบจากบัญชี '{self.current_user}' ใช่หรือไม่?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                QMessageBox.information(self, "ออกจากระบบแล้ว", "✅ คุณได้ออกจากระบบเรียบร้อยแล้ว")
                self.current_user = None
                
                self.cart = [] # ❗ (ล้างตะกร้าเมื่อ Logout)

                self.update_user_status()
                self.update_sidebar_buttons()
                self.stack.setCurrentWidget(self.home_page)
                if "Homepage" in self.sidebar.buttons:
                    self.sidebar.buttons["Homepage"].setChecked(True)
            else:
                 self.sidebar.buttons["Logout"].setChecked(False) 
                 current_widget = self.stack.currentWidget()
                 page_map = {v: k for k, v in self.pages_mapping().items()}
                
                 current_page_name = page_map.get(current_widget, "Homepage")
                
                 if current_widget == self.product_detail_page:
                     current_page_name = "Products"

                 if current_page_name in self.sidebar.buttons:
                    self.sidebar.buttons[current_page_name].setChecked(True)
                 else:
                    self.sidebar.buttons["Homepage"].setChecked(True)
            return
        
        if name == "Orders":
            if self.current_user is None:
                QMessageBox.information(self, "ยังไม่ได้เข้าสู่ระบบ", "⚠️ กรุณาเข้าสู่ระบบเพื่อดูประวัติการสั่งซื้อ")
                self.sidebar.buttons["Orders"].setChecked(False) # ยกเลิกการติ๊ก
                self.sidebar.buttons["Login"].setChecked(True)  # ไปหน้า Login
                self.stack.setCurrentWidget(self.login_page)
                return
            else:
                # ถ้าล็อกอินแล้ว: โหลดข้อมูลและเปิดหน้า
                self.orders_page.load_my_orders(self.current_user)
                self.stack.setCurrentWidget(self.orders_page)
                return

        pages = self.pages_mapping()

        if name == "Contact Admin" and self.current_user != "admin":
            QMessageBox.warning(self, "สิทธิ์ไม่พอ", "⚠️ เฉพาะผู้ดูแลระบบ (admin) เท่านั้นที่เข้าหน้านี้ได้")
            self.sidebar.buttons["Contact Admin"].setChecked(False)
            if "Homepage" in self.sidebar.buttons:
                self.sidebar.buttons["Homepage"].setChecked(True)
            self.stack.setCurrentWidget(self.home_page)
            return

        if name in pages:
            if name == "Products":
                self.stack.setCurrentWidget(self.products_page)
            else:
                self.stack.setCurrentWidget(pages[name])
        else:
            QMessageBox.information(self, "ยังไม่เปิดใช้งาน", f"🔧 หน้านี้ยังไม่เปิดใช้งาน: {name}")

    def pages_mapping(self):
       return {
            "Homepage": self.home_page,
            "Products": self.products_page,
            "Cart": self.cart_page, 
            "Orders": self.orders_page, # (เหมือนเดิม)
            "Contact": self.contact_page, 
            "Contact Admin": self.contact_admin_page,
            "Login": self.login_page,
       }

    def update_user_status(self):
        if self.current_user:
            self.setWindowTitle(f"Arai Football Shop - {self.current_user}")
            if self.stack.currentWidget() == self.contact_page:
                self.contact_page.load_user_data(self.current_user)
        else:
            self.setWindowTitle("Arai Football Shop")
            if self.stack.currentWidget() == self.contact_page:
                self.contact_page.clear_user_data()

    def update_sidebar_buttons(self):
        for text, btn in self.sidebar.buttons.items():
            if text == "Login":
                btn.setVisible(self.current_user is None)
            elif text == "Logout":
                btn.setVisible(self.current_user is not None)
            elif text == "Profile":
                btn.setVisible(self.current_user is not None)
            elif text == "Contact Admin":
                btn.setVisible(self.current_user == "admin")
            else:
                btn.setVisible(True)
        

if __name__ == "__main__":
    init_user_database()
    init_orders_database() 
    app = QApplication(sys.argv)
    window = MainApp()
    window.showMaximized() 
    sys.exit(app.exec())
เอาข้อมูลข้างล่างไปเชื่อมต่อให้เข้ากับข้อมูลด้านบน 
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas                                                                                                                                                                                                                                     def _generate_receipt_pdf(self, payment_id: int) -> str | None:
        """
        สร้างไฟล์ใบเสร็จ PDF จาก payment_id
        ดึงข้อมูลผู้ใช้ + รายการสินค้าที่สั่งซื้อจาก sales ตาม order_ref
        คืนค่า path ของไฟล์ PDF ที่สร้าง หรือ None ถ้าไม่สำเร็จ
        """
        # 1) ดึงข้อมูล payment + user
        with sqlite3.connect(db) as con:
            c = con.cursor()
            c.execute("""
                SELECT p.id,
                       p.user_id,
                       p.amount,
                       p.payment_slip,
                       p.status,
                       p.created_at,
                       p.order_ref,
                       u.fname,
                       u.lname,
                       u.username,
                       u.email
                FROM payments p
                LEFT JOIN users u ON p.user_id = u.id
                WHERE p.id = ?
            """, (payment_id,))
            row = c.fetchone()

        if not row:
            messagebox.showerror("Receipt", "ไม่พบข้อมูลการชำระเงิน")
            return None

        (pid, user_id, amount, slip, status, created_at,
         order_ref, fname, lname, username, email) = row

        # ถ้าใน payments ยังไม่ได้เก็บ order_ref ก็ fallback เป็น PAY-<id>
        order_ref = order_ref or f"PAY-{pid}"

        # 2) ดึงรายการสินค้าที่ผู้ใช้ซื้อจาก sales โดยใช้ user_id + order_ref
        with sqlite3.connect(db) as con:
            c = con.cursor()
            c.execute("""
                SELECT s.product_id,
                       p.name,
                       p.brand,
                       s.size,
                       s.qty,
                       s.unit_price,
                       s.ts
                FROM sales s
                LEFT JOIN products p ON s.product_id = p.id
                WHERE s.user_id = ? AND s.order_ref = ?
                ORDER BY s.id
            """, (user_id, order_ref))
            items = c.fetchall()

        if not items:
            # ถ้าไม่มีข้อมูล sales เลย ให้เตือน แต่ยังสร้างใบเสร็จเปล่า ๆ ได้
            messagebox.showwarning(
                "Receipt",
                "ไม่พบรายการสินค้าในคำสั่งซื้อ แต่จะสร้างใบเสร็จสรุปยอดให้"
            )

        # 3) สร้างโฟลเดอร์เก็บไฟล์ใบเสร็จ
                # 3) สร้างโฟลเดอร์เก็บไฟล์ใบเสร็จ
        receipts_dir = Path("receipts")
        receipts_dir.mkdir(exist_ok=True)

        pdf_path = receipts_dir / f"receipt_{order_ref}.pdf"

        # 4) เริ่มสร้าง PDF
        cpdf = canvas.Canvas(str(pdf_path), pagesize=A4)
        width, height = A4

        # ---- layout แบบกำหนดเหมือน GUI ----
        left_margin   = 40
        right_margin  = 540
        line_height   = 14
        top_after_logo = height - 100

        # คอลัมน์ของตารางสินค้า
        col_product = left_margin
        col_size    = left_margin + 210
        col_qty     = left_margin + 260
        col_unit    = left_margin + 310
        col_total   = left_margin + 390

        y = height  # จะเซ็ตใหม่หลังวาดโลโก้

        # ---------- 1) วาดโลโก้ซ้ายบน ----------
        logo_path = r"C:\Users\User\Downloads\pitchfit_black.png"   # ไฟล์โลโก้สีดำที่เตรียมไว้
        if os.path.exists(logo_path):
            cpdf.drawImage(logo_path, 30, height - 130, width=100, height=100, mask='auto')
            y = top_after_logo
        else:
            cpdf.setFont("Helvetica-Bold", 20)
            cpdf.drawString(left_margin, height - 70, "PITCHFIT FOOTBALL STORE")
            y = height - 110

        # ---------- 2) ข้อความหัวใบเสร็จ / ข้อมูลร้าน ----------
        cpdf.setFont("Helvetica", 10)

        y -= 10
        cpdf.drawString(left_margin, y, "Online Football Boots Store - Thailand")
        y -= line_height
        cpdf.drawString(left_margin, y,
                        "Tel: 012-345-6789  |  Line: @pitchfit  |  IG: @pitchfit.official")

        y -= 20
        cpdf.line(left_margin, y, right_margin, y)   # เส้นคั่น header
        y -= (line_height + 10)

        # ---------- 3) ข้อมูลใบเสร็จ / ลูกค้า ----------
        cpdf.setFont("Helvetica-Bold", 12)
        cpdf.drawString(left_margin, y, f"Receipt No.: {order_ref}")
        y -= line_height

        cpdf.setFont("Helvetica", 10)
        cpdf.drawString(left_margin, y, f"Customer: {fname} {lname} (@{username})")
        y -= line_height
        cpdf.drawString(left_margin, y, f"Email: {email}")
        y -= line_height
        cpdf.drawString(left_margin, y, f"Payment Date: {created_at}")
        y -= (line_height + 10)

        # --- จัดรูปชื่อเต็ม ---
        full_name = ((fname or "") + (" " + lname if lname else "")).strip()
        if not full_name:
            full_name = username or "-"

        cpdf.setFont("Helvetica-Bold", 12)
        cpdf.drawString(left_margin, y, "Customer Information")
        y -= (line_height + 4)

        cpdf.setFont("Helvetica", 11)
        cpdf.drawString(left_margin, y, f"Name : {full_name}")
        y -= (line_height + 2)
        cpdf.drawString(left_margin, y, f"Email: {email or '-'}")
        y -= (line_height + 10)

        # ---------- ฟังก์ชันย่อย: หัวตารางสินค้า ----------
        def draw_items_header():
            nonlocal y
            cpdf.setFont("Helvetica-Bold", 12)
            cpdf.drawString(left_margin, y, "Items Purchased")
            y -= (line_height + 4)

            cpdf.setFont("Helvetica-Bold", 10)
            cpdf.drawString(col_product, y, "Product")
            cpdf.drawString(col_size,    y, "Size")
            cpdf.drawString(col_qty,     y, "Qty")
            cpdf.drawString(col_unit,    y, "Unit")
            cpdf.drawString(col_total,   y, "Line Total")
            y -= line_height
            cpdf.line(left_margin, y, right_margin, y)
            y -= line_height
            cpdf.setFont("Helvetica", 10)

        # --- หัวตารางสินค้าครั้งแรก ---
        draw_items_header()

        grand_total = 0

        # ---------- 4) วนแสดงสินค้า ----------
        for pid_, name, brand, size, qty, unit_price, ts in items:
            # ถ้าพื้นที่หน้าไม่พอ -> ขึ้นหน้าใหม่ + วาดหัวตารางอีกครั้ง
            if y < 80:
                cpdf.showPage()
                y = height - 80
                cpdf.setFont("Helvetica-Bold", 12)
                cpdf.drawString(left_margin, y, "Items Purchased (continued)")
                y -= (line_height + 4)
                draw_items_header()

            qty = int(qty)
            unit_price = int(unit_price)
            line_total = qty * unit_price
            grand_total += line_total

            title = f"{brand} {name}" if brand else (name or "")
            if not title:
                title = f"Product #{pid_}"
            if len(title) > 40:
                title = title[:37] + "..."

            cpdf.setFont("Helvetica", 10)
            cpdf.drawString(col_product, y, title)
            cpdf.drawString(col_size,    y, str(size or "-"))
            cpdf.drawString(col_qty,     y, str(qty))
            cpdf.drawRightString(col_unit + 30,  y, f"{unit_price:,}")
            cpdf.drawRightString(col_total + 40, y, f"{line_total:,}")
            y -= line_height

        # ---------- 5) รวมยอด ----------
        y -= 10
        cpdf.line(col_total - 10, y, right_margin, y)
        y -= (line_height + 4)

        cpdf.setFont("Helvetica-Bold", 11)
        cpdf.drawRightString(col_total + 10, y, "Grand Total:")

        total_to_show = grand_total if grand_total > 0 else int(amount or 0)
        cpdf.drawRightString(right_margin, y, f"{total_to_show:,} THB")
        y -= (line_height + 10)

        # ---------- 6) โน้ต / ข้อความปิดท้าย ----------
        cpdf.setFont("Helvetica", 9)
        cpdf.drawString(left_margin, y, "Payment Status: " + (status or "-"))
        y -= (line_height + 2)
        cpdf.drawString(left_margin, y, "Thank you for shopping with PitchFit.")

        # ปิดไฟล์ PDF
        cpdf.save()

        abs_path = os.path.abspath(pdf_path)
        webbrowser.open_new(rf"file://{abs_path}")

        return str(pdf_path)