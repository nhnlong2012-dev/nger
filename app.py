import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

"""
Ứng dụng PET STORE viết bằng PyQt6.

Ý tưởng tổ chức file:
- Các màn hình tĩnh như Login, Register, Home, Cart, User được thiết kế bằng Qt Designer
  rồi nạp trực tiếp từ file `.ui` bằng `uic.loadUi(...)`.
- Python trong file này chủ yếu làm 3 việc:
  1. Đọc/ghi dữ liệu JSON.
  2. Nối các nút, ô nhập với hành vi thực tế.
  3. Sinh ra các phần giao diện động từ dữ liệu, ví dụ danh sách sản phẩm từ `data.json`.

Vì dự án đang được viết để học, comment sẽ tập trung giải thích:
- Mỗi hàm nhận dữ liệu gì, trả về gì.
- Vì sao phải chuẩn hóa dữ liệu trước khi dùng.
- Luồng đi của một thao tác hoàn chỉnh, ví dụ đăng nhập hoặc thanh toán.
"""

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# ==================== Cau hinh chung ====================
BASE_DIR = Path(__file__).resolve().parent
UI_DIR = BASE_DIR / "ui"
DATA_DIR = BASE_DIR / "data"
ASSET_DIR = BASE_DIR / "assets"
AVATAR_DIR = DATA_DIR / "avatars"
PRODUCT_IMAGE_DIR = ASSET_DIR / "product_images"
DEFAULT_PRODUCT_IMAGE = PRODUCT_IMAGE_DIR / "placeholder.png"
USER_FILE = DATA_DIR / "user.json"
PRODUCT_FILE = DATA_DIR / "data.json"

ROLE_ADMIN = "admin"
ROLE_USER = "user"
SPECIES_OPTIONS = ["Mèo", "Chó", "Chung"]
CATEGORY_OPTIONS = ["Thức ăn", "Snack", "Đồ chơi", "Bổ sung", "Khác"]

CARD_STYLE = """
QFrame#productCard {background-color: rgba(255,252,247,245); border: 1px solid rgba(24,57,43,22); border-radius: 24px;}
QLabel#productImage {background-color: #eef3ee; border: 1px solid rgba(24,57,43,18); border-radius: 18px;}
QLabel#productTitle {color: #173326; font-size: 13pt; font-weight: 700;}
QLabel#productMeta, QLabel#productStock, QLabel#productId {color: #506056; font-size: 10pt;}
QLabel#productPrice {color: #b25b3a; font-size: 14pt; font-weight: 700;}
QPushButton {min-height: 36px; border-radius: 14px; font-size: 10pt; font-weight: 700; padding: 0 14px;}
QPushButton#btnDetail {background-color: rgba(24,57,43,10); color: #173326; border: 1px solid rgba(24,57,43,30);}
QPushButton#btnAddCart {background-color: #d96b43; color: white; border: none;}
QPushButton#btnEdit {background-color: #18392b; color: white; border: none;}
"""

# ==================== Ham ho tro ====================
def ui_path(filename):
    """Ghép tên file `.ui` thành đường dẫn tuyệt đối để `uic.loadUi` sử dụng."""
    return str(UI_DIR / filename)


def norm(value):
    """Chuẩn hóa chuỗi để so sánh không phân biệt hoa/thường và khoảng trắng thừa."""
    return str(value or "").strip().casefold()


def safe_int(value, default=0):
    """Ép dữ liệu về số nguyên. Nếu lỗi thì dùng giá trị mặc định để app không crash."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def next_id(records):
    """Tìm id lớn nhất hiện có rồi cộng thêm 1 để sinh id mới."""
    return max((safe_int(item.get("id"), 0) for item in records), default=0) + 1


def fmt_money(value):
    """Định dạng số tiền theo kiểu dễ đọc trên giao diện Việt Nam."""
    return f"{safe_int(value):,} đ".replace(",", ".")


def valid_email(email):
    """Kiểm tra email ở mức đơn giản, đủ cho bài tập nhỏ."""
    local_part, _, domain = email.strip().partition("@")
    return bool(local_part and domain and "." in domain)


def guess_category(name):
    text = norm(name)
    if any(key in text for key in ["hạt", "pate", "cá nục", "súp cá hồi"]):
        return "Thức ăn"
    if any(key in text for key in ["bánh thưởng", "súp thưởng", "thịt sấy", "xúc xích", "tôm sấy", "gan gà", "kẹo liếm", "thanh năng lượng", "phô mai", "thịt bò viên"]):
        return "Snack"
    if any(key in text for key in ["xương", "cỏ", "que gặm"]):
        return "Đồ chơi"
    if "sữa bột" in text:
        return "Bổ sung"
    return "Khác"


def read_list(path, label):
    """Đọc một file JSON dạng list và báo lỗi rõ ràng nếu cấu trúc sai."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} khong hop le.") from exc
    if not isinstance(data, list):
        raise ValueError(f"{label} phai la mot danh sach.")
    return data


def write_list(path, data):
    """Ghi dữ liệu list ra JSON theo UTF-8 để giữ nguyên tiếng Việt."""
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_project_dirs():
    """Tao san cac thu muc quan trong de app co the luu file an toan."""
    UI_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    PRODUCT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)


def user_display_name(user):
    """Neu user co ho ten thi uu tien hien thi ho ten, khong thi dung username."""
    full_name = str(user.get("full_name", "")).strip()
    username = str(user.get("username", "")).strip()
    return full_name or username


def format_datetime_text(value):
    """Chuyen ISO datetime thanh chuoi de doc hon tren giao dien."""
    text = str(value or "").strip()
    if not text:
        return "Khong ro"

    try:
        return datetime.fromisoformat(text).strftime("%d/%m/%Y %H:%M:%S")
    except ValueError:
        return text


def avatar_abs_path(avatar_value):
    """Doi duong dan avatar tu JSON thanh duong dan tuyet doi trong project."""
    avatar_text = str(avatar_value or "").strip()
    if not avatar_text:
        return None

    avatar_path = Path(avatar_text)
    if avatar_path.is_absolute():
        return avatar_path

    return (DATA_DIR / avatar_path).resolve()


def default_product_image_value():
    """Tra ve duong dan tuong doi cua anh mac dinh de luu vao JSON."""
    return DEFAULT_PRODUCT_IMAGE.relative_to(BASE_DIR).as_posix()


def product_image_abs_path(image_value):
    """Doi gia tri img trong data.json thanh duong dan tuyet doi."""
    image_text = str(image_value or "").strip()
    if not image_text:
        return DEFAULT_PRODUCT_IMAGE

    image_path = Path(image_text)
    if image_path.is_absolute():
        return image_path

    return (BASE_DIR / image_path).resolve()


def store_product_image(image_value, product_id):
    """Copy anh san pham ve assets/product_images va tra ve duong dan de luu lai."""
    ensure_project_dirs()
    source_path = product_image_abs_path(image_value)
    if source_path is None or not source_path.exists():
        return default_product_image_value()

    suffix = source_path.suffix.lower() or ".png"
    destination_path = PRODUCT_IMAGE_DIR / f"product_{product_id}{suffix}"
    resolved_source = source_path.resolve()
    resolved_destination = destination_path.resolve()

    for existing in PRODUCT_IMAGE_DIR.glob(f"product_{product_id}.*"):
        if existing.resolve() != resolved_destination:
            existing.unlink(missing_ok=True)

    if resolved_source != resolved_destination:
        shutil.copy2(resolved_source, resolved_destination)

    return resolved_destination.relative_to(BASE_DIR).as_posix()


def split_product_name(name, max_chars=22, max_lines=3):
    """Chia ten san pham thanh vai dong ngan de ve placeholder de doc hon."""
    words = str(name or "").split()
    lines = []
    current = ""

    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            lines.append(current)
        current = word
        if len(lines) == max_lines - 1:
            break

    if current and len(lines) < max_lines:
        lines.append(current)

    remaining_words = words[len(" ".join(lines).split()):]
    if remaining_words:
        lines[-1] = f"{lines[-1][:max(0, max_chars - 3)].rstrip()}..."

    return lines or ["Ảnh sản phẩm"]


def build_product_placeholder(product, width, height):
    """Ve placeholder ngay trong app de giao dien van dep khi anh bi thieu."""
    palettes = {
        "Thức ăn": ("#f6d7c4", "#d96b43"),
        "Snack": ("#fbe7b9", "#c7881b"),
        "Đồ chơi": ("#d6ebf7", "#2d7ea8"),
        "Bổ sung": ("#dce9d7", "#4f8a57"),
        "Khác": ("#e6e1f5", "#6b5fb1"),
    }
    background_color, accent_color = palettes.get(product.get("danh_muc"), palettes["Khác"])

    pixmap = QPixmap(width, height)
    pixmap.fill(QColor("#f9f6f2"))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(background_color))
    painter.drawRoundedRect(0, 0, width, height, 24, 24)

    painter.setBrush(QColor(accent_color))
    painter.drawEllipse(width - 132, -18, 150, 150)
    painter.setBrush(QColor(255, 255, 255, 72))
    painter.drawEllipse(width - 170, 48, 110, 110)

    painter.setPen(QColor("#173326"))
    painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
    painter.drawText(18, 28, f"{product.get('loai', 'Chung')} | {product.get('danh_muc', 'Khác')}")

    painter.setPen(QColor("#173326"))
    painter.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    y = 62
    for line in split_product_name(product.get("ten", "")):
        painter.drawText(18, y, line)
        y += 26

    painter.setPen(QColor(255, 255, 255, 220))
    painter.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
    painter.drawText(width - 98, 84, product.get("loai", "P")[:1].upper())

    painter.setPen(QColor("#173326"))
    painter.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
    painter.drawText(18, height - 22, fmt_money(product.get("gia", 0)))
    painter.end()
    return pixmap


def set_product_image(label, product, width, height):
    """Nap anh tu duong dan img. Neu loi thi tu ve placeholder de giao dien van hien thi."""
    image_path = product_image_abs_path(product.get("img", ""))
    pixmap = QPixmap(str(image_path)) if image_path and image_path.exists() else QPixmap()
    if pixmap.isNull():
        pixmap = build_product_placeholder(product, width, height)
    else:
        pixmap = pixmap.scaled(
            width,
            height,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )

    label.setPixmap(pixmap)
    label.setText("")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)


# ==================== User data ====================
def save_users(users):
    """
    Làm sạch dữ liệu user trước khi ghi xuống `user.json`.

    Vì JSON có thể bị sửa tay hoặc dữ liệu từ form có thể thiếu trường,
    hàm này luôn chuẩn hóa từng user về cùng một cấu trúc trước khi lưu.
    """
    cleaned = []
    for raw in users:
        user = {
            "id": safe_int(raw.get("id"), 0),
            "username": str(raw.get("username", "")).strip(),
            "full_name": str(raw.get("full_name", "")).strip(),
            "email": str(raw.get("email", "")).strip(),
            "phone": str(raw.get("phone", "")).strip(),
            "address": str(raw.get("address", "")).strip(),
            "password": str(raw.get("password", "")).strip(),
            "role": str(raw.get("role", ROLE_USER)).strip().lower(),
            "avatar": str(raw.get("avatar", "")).strip(),
            "created_at": str(raw.get("created_at", "")).strip() or datetime.now().isoformat(timespec="seconds"),
        }
        if user["role"] not in {ROLE_ADMIN, ROLE_USER}:
            user["role"] = ROLE_USER
        if not (user["username"] and user["email"] and user["password"]):
            continue
        if user["id"] <= 0:
            user["id"] = next_id(cleaned)
        cleaned.append(user)
    write_list(USER_FILE, cleaned)


def load_users():
    """
    Đọc `user.json`, chuẩn hóa từng bản ghi rồi trả về list user sạch.

    Ngoài ra hàm còn đảm bảo luôn có tài khoản `admin`.
    Điều này giúp app không rơi vào trạng thái mất hoàn toàn quyền quản trị.
    """
    users = []
    for raw in read_list(USER_FILE, "user.json"):
        user = {
            "id": safe_int(raw.get("id"), 0),
            "username": str(raw.get("username", "")).strip(),
            "full_name": str(raw.get("full_name", "")).strip(),
            "email": str(raw.get("email", "")).strip(),
            "phone": str(raw.get("phone", "")).strip(),
            "address": str(raw.get("address", "")).strip(),
            "password": str(raw.get("password", "")).strip(),
            "role": str(raw.get("role", ROLE_USER)).strip().lower(),
            "avatar": str(raw.get("avatar", "")).strip(),
            "created_at": str(raw.get("created_at", "")).strip() or datetime.now().isoformat(timespec="seconds"),
        }
        if user["role"] not in {ROLE_ADMIN, ROLE_USER}:
            user["role"] = ROLE_USER
        if not (user["username"] and user["email"] and user["password"]):
            continue
        if user["id"] <= 0:
            user["id"] = next_id(users)
        users.append(user)

    admin = next((user for user in users if norm(user["username"]) == "admin"), None)
    if admin is None:
        users.append({
            "id": next_id(users),
            "username": "admin",
            "full_name": "Administrator",
            "email": "admin@petstore.local",
            "phone": "",
            "address": "",
            "password": "admin",
            "role": ROLE_ADMIN,
            "avatar": "",
            "created_at": "2026-03-21T00:00:00",
        })
        save_users(users)
    else:
        changed = False
        if admin["role"] != ROLE_ADMIN:
            admin["role"] = ROLE_ADMIN
            changed = True
        if not admin["email"]:
            admin["email"] = "admin@petstore.local"
            changed = True
        if not admin["password"]:
            admin["password"] = "admin"
            changed = True
        if not admin["full_name"]:
            admin["full_name"] = "Administrator"
            changed = True
        if "phone" not in admin:
            admin["phone"] = ""
            changed = True
        if "address" not in admin:
            admin["address"] = ""
            changed = True
        if "avatar" not in admin:
            admin["avatar"] = ""
            changed = True
        if changed:
            save_users(users)
    return users


def find_user(users, identity):
    """Tìm user bằng username hoặc email trên cùng một ô đăng nhập."""
    lookup = norm(identity)
    for user in users:
        if lookup in {norm(user["username"]), norm(user["email"])}:
            return user
    return None


# ==================== Product data ====================
def clean_product(raw):
    """
    Chuẩn hóa một sản phẩm lấy từ JSON hoặc form admin.

    Mục tiêu của bước này là gom mọi nguồn dữ liệu về một schema cố định
    để các màn hình phía sau chỉ cần đọc đúng một kiểu dữ liệu duy nhất.
    """
    product = {
        "id": safe_int(raw.get("id"), 0),
        "ten": str(raw.get("ten", "")).strip(),
        "loai": str(raw.get("loai", "Chung")).strip(),
        "gia": max(0, safe_int(raw.get("gia"), 0)),
        "so_luong": max(0, safe_int(raw.get("so_luong"), 0)),
        "danh_muc": str(raw.get("danh_muc", "")).strip(),
        "img": str(raw.get("img", default_product_image_value())).strip() or default_product_image_value(),
    }
    if product["loai"] not in SPECIES_OPTIONS:
        product["loai"] = "Chung"
    if product["danh_muc"] not in CATEGORY_OPTIONS:
        product["danh_muc"] = guess_category(product["ten"])
    return product


def save_products(products):
    """Làm sạch danh sách sản phẩm rồi mới ghi xuống `data.json`."""
    cleaned = []
    for raw in products:
        product = clean_product(raw)
        if not product["ten"]:
            continue
        if product["id"] <= 0:
            product["id"] = next_id(cleaned)
        cleaned.append(product)
    cleaned.sort(key=lambda item: item["id"])
    write_list(PRODUCT_FILE, cleaned)


def load_products():
    """
    Đọc toàn bộ sản phẩm từ `data.json`.

    Nếu phát hiện dữ liệu cũ hoặc thiếu field mới, hàm sẽ tự chuẩn hóa
    và ghi lại để những lần chạy sau dùng dữ liệu đồng nhất hơn.
    """
    raw_products = read_list(PRODUCT_FILE, "data.json")
    products = []
    for raw in raw_products:
        product = clean_product(raw)
        if not product["ten"]:
            continue
        if product["id"] <= 0:
            product["id"] = next_id(products)
        products.append(product)
    products.sort(key=lambda item: item["id"])
    if products != raw_products:
        save_products(products)
    return products

# ==================== Dialog chi tiet san pham ====================
class ProductDetailDialog(QDialog):
    """Hộp thoại xem nhanh thông tin chi tiết của một sản phẩm."""
    def __init__(self, product, is_admin=False, parent=None):
        super().__init__(parent)
        self.product = product
        self.is_admin = is_admin
        self.selected_quantity = 1
        self.load_to_form_requested = False

        self.setWindowTitle(f"Chi tiet san pham | {product['ten']}")
        self.resize(620, 640)
        self.setStyleSheet(
            """
            QDialog {background-color: #fffaf4; font-family: "Segoe UI";}
            QLabel#title {color: #173326; font-size: 18pt; font-weight: 700;}
            QLabel#meta, QLabel#desc {color: #506056; font-size: 10.5pt;}
            QLabel#price {color: #b25b3a; font-size: 16pt; font-weight: 700;}
            QFrame#panel {background-color: white; border: 1px solid rgba(24,57,43,22); border-radius: 20px;}
            QLabel#detailImage {background-color: #eef3ee; border: 1px solid rgba(24,57,43,18); border-radius: 18px;}
            QSpinBox {min-height: 38px; border-radius: 14px; border: 1px solid #d8e1d8; padding: 0 12px;}
            QPushButton {min-height: 40px; border-radius: 14px; font-weight: 700; padding: 0 16px;}
            QPushButton#btnAdd {background-color: #d96b43; color: white; border: none;}
            QPushButton#btnEdit {background-color: #18392b; color: white; border: none;}
            QPushButton#btnClose {background-color: transparent; color: #173326; border: 1px solid rgba(24,57,43,30);}
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        # Ảnh chi tiết dùng chung logic với ảnh thẻ sản phẩm ngoài Home.
        image = QLabel()
        image.setObjectName("detailImage")
        image.setFixedHeight(240)
        set_product_image(image, product, 540, 240)

        title = QLabel(product["ten"])
        title.setObjectName("title")
        title.setWordWrap(True)

        meta = QLabel(f"ID: {product['id']} | Loài: {product['loai']} | Danh mục: {product['danh_muc']}")
        meta.setObjectName("meta")

        price = QLabel(fmt_money(product["gia"]))
        price.setObjectName("price")

        stock = QLabel(f"Tồn kho hiện tại: {product['so_luong']} sản phẩm")
        stock.setObjectName("meta")

        desc = QLabel(
            f"{product['ten']} thuộc nhóm {product['danh_muc']}, phù hợp cho {product['loai'].lower()}. "
            "Bạn có thể xem nhanh giá, tồn kho và thêm trực tiếp vào giỏ hàng."
        )
        desc.setObjectName("desc")
        desc.setWordWrap(True)

        self.spin_quantity = QSpinBox()
        self.spin_quantity.setMinimum(1)
        self.spin_quantity.setMaximum(max(1, product["so_luong"]))
        self.spin_quantity.setEnabled(product["so_luong"] > 0)

        button_row = QHBoxLayout()
        if is_admin:
            btn_edit = QPushButton("Nạp vào form sửa")
            btn_edit.setObjectName("btnEdit")
            btn_edit.clicked.connect(self.accept_for_edit)
            button_row.addWidget(btn_edit)

        btn_add = QPushButton("Thêm vào giỏ")
        btn_add.setObjectName("btnAdd")
        btn_add.setEnabled(product["so_luong"] > 0)
        btn_add.clicked.connect(self.accept_for_cart)
        button_row.addWidget(btn_add)

        btn_close = QPushButton("Đóng")
        btn_close.setObjectName("btnClose")
        btn_close.clicked.connect(self.reject)
        button_row.addWidget(btn_close)

        for widget in [image, title, meta, price, stock, desc, QLabel("Số lượng muốn thêm vào giỏ"), self.spin_quantity]:
            layout.addWidget(widget)
        layout.addStretch()
        layout.addLayout(button_row)
        root.addWidget(panel)

    def accept_for_cart(self):
        self.selected_quantity = self.spin_quantity.value()
        self.accept()

    def accept_for_edit(self):
        self.load_to_form_requested = True
        self.accept()


# ==================== Dang nhap / Dang ky ====================
class Login(QMainWindow):
    """Màn hình đăng nhập và điều hướng sang Register hoặc Home."""
    def __init__(self):
        super().__init__()
        uic.loadUi(ui_path("Login.ui"), self)
        self.register_window = None
        self.home_window = None
        self.createAccount.clicked.connect(self.show_register)
        self.btnLogin.clicked.connect(self.check_login)
        self.Email.returnPressed.connect(self.check_login)
        self.Password.returnPressed.connect(self.check_login)

    def set_windows(self, register_window, home_window):
        self.register_window = register_window
        self.home_window = home_window

    def show_register(self):
        if self.register_window is None:
            QMessageBox.warning(self, "Loi", "Khong mo duoc man hinh dang ky.")
            return
        self.register_window.reset_form()
        self.register_window.show()
        self.hide()

    def check_login(self):
        """Xác thực người dùng bằng username/email và mật khẩu."""
        identity = self.Email.text().strip()
        password = self.Password.text()
        if not identity:
            QMessageBox.warning(self, "Thieu thong tin", "Vui long nhap tai khoan hoac email.")
            self.Email.setFocus()
            return
        if not password:
            QMessageBox.warning(self, "Thieu thong tin", "Vui long nhap mat khau.")
            self.Password.setFocus()
            return

        try:
            users = load_users()
        except ValueError as exc:
            QMessageBox.critical(self, "Loi du lieu", str(exc))
            return

        # Một ô nhập duy nhất được phép nhận cả username lẫn email.
        user = find_user(users, identity)
        if user is None or user["password"] != password:
            QMessageBox.warning(self, "Dang nhap that bai", "Tai khoan hoac mat khau khong dung.")
            self.Password.clear()
            self.Password.setFocus()
            return

        if self.home_window is None:
            QMessageBox.warning(self, "Loi", "Khong tim thay man hinh Home.")
            return

        # Chuyển user hiện tại cho Home để các màn hình khác dùng lại cùng một phiên làm việc.
        self.Password.clear()
        self.home_window.set_current_user(user)
        self.home_window.show()
        self.hide()


class Register(QMainWindow):
    """Màn hình tạo tài khoản mới cho người dùng thường."""
    def __init__(self):
        super().__init__()
        uic.loadUi(ui_path("Register.ui"), self)
        self.login_window = None
        self.btnRegister.clicked.connect(self.register_user)
        self.loginAccount.clicked.connect(self.back_to_login)
        self.ConfirmPassword.returnPressed.connect(self.register_user)

    def set_login_window(self, login_window):
        self.login_window = login_window

    def reset_form(self):
        self.Username.clear()
        self.Email.clear()
        self.Password.clear()
        self.ConfirmPassword.clear()
        self.acceptTerms.setChecked(False)

    def back_to_login(self):
        if self.login_window is None:
            QMessageBox.warning(self, "Loi", "Khong mo duoc man hinh dang nhap.")
            return
        self.login_window.show()
        self.login_window.Email.setFocus()
        self.hide()

    def register_user(self):
        """Kiểm tra dữ liệu đăng ký rồi thêm user mới vào `user.json`."""
        username = self.Username.text().strip()
        email = self.Email.text().strip()
        password = self.Password.text()
        confirm_password = self.ConfirmPassword.text()

        if not username or not email or not password or not confirm_password:
            QMessageBox.warning(self, "Thieu thong tin", "Vui long dien day du tat ca truong.")
            return
        if len(username) < 3:
            QMessageBox.warning(self, "Du lieu khong hop le", "Ten tai khoan phai co it nhat 3 ky tu.")
            self.Username.setFocus()
            return
        if not valid_email(email):
            QMessageBox.warning(self, "Du lieu khong hop le", "Email khong dung dinh dang.")
            self.Email.setFocus()
            return
        if len(password) < 4:
            QMessageBox.warning(self, "Du lieu khong hop le", "Mat khau phai co it nhat 4 ky tu.")
            self.Password.setFocus()
            return
        if password != confirm_password:
            QMessageBox.warning(self, "Du lieu khong hop le", "Mat khau nhap lai khong khop.")
            self.ConfirmPassword.clear()
            self.ConfirmPassword.setFocus()
            return
        if not self.acceptTerms.isChecked():
            QMessageBox.warning(self, "Chua xac nhan", "Ban can dong y voi dieu khoan su dung.")
            return

        try:
            users = load_users()
        except ValueError as exc:
            QMessageBox.critical(self, "Loi du lieu", str(exc))
            return

        for user in users:
            if norm(user["username"]) == norm(username):
                QMessageBox.warning(self, "Trung du lieu", "Ten tai khoan da ton tai.")
                self.Username.setFocus()
                return
            if norm(user["email"]) == norm(email):
                QMessageBox.warning(self, "Trung du lieu", "Email da duoc su dung.")
                self.Email.setFocus()
                return

        # Các thông tin hồ sơ nâng cao sẽ để user bổ sung dần trong màn hình User.
        users.append({
            "id": next_id(users),
            "username": username,
            "full_name": "",
            "email": email,
            "phone": "",
            "address": "",
            "password": password,
            "role": ROLE_USER,
            "avatar": "",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })
        save_users(users)

        if self.login_window is not None:
            self.login_window.Email.setText(username)
            self.login_window.Password.clear()

        self.reset_form()
        QMessageBox.information(self, "Thanh cong", "Tao tai khoan thanh cong.")
        self.back_to_login()


# ==================== User profile ====================
class UserWindow(QMainWindow):
    """Màn hình cho phép user tự cập nhật hồ sơ cá nhân."""
    def __init__(self):
        super().__init__()
        uic.loadUi(ui_path("User.ui"), self)

        self.home_window = None
        self.current_user = None
        self.pending_avatar_source = None
        self.remove_avatar_requested = False

        self.btnChooseAvatar.clicked.connect(self.choose_avatar)
        self.btnClearAvatar.clicked.connect(self.clear_avatar)
        self.btnSaveUser.clicked.connect(self.save_profile)
        self.btnBackHome.clicked.connect(self.back_home)
        self.inputConfirmPassword.returnPressed.connect(self.save_profile)

    def set_home_window(self, home_window):
        self.home_window = home_window

    def set_current_user(self, user):
        """Nap thong tin user len form moi lan mo man hinh User."""
        self.current_user = dict(user)
        self.pending_avatar_source = None
        self.remove_avatar_requested = False

        # Form luôn được nạp lại từ dữ liệu user hiện tại để tránh sót dữ liệu cũ.
        self.inputUsername.setText(self.current_user.get("username", ""))
        self.inputFullName.setText(self.current_user.get("full_name", ""))
        self.inputEmail.setText(self.current_user.get("email", ""))
        self.inputPhone.setText(self.current_user.get("phone", ""))
        self.inputAddress.setText(self.current_user.get("address", ""))
        self.inputPassword.clear()
        self.inputConfirmPassword.clear()

        self.lblRoleValue.setText("Admin" if self.current_user.get("role") == ROLE_ADMIN else "User")
        self.lblCreatedAtValue.setText(format_datetime_text(self.current_user.get("created_at", "")))
        self.render_avatar()

    def render_avatar(self):
        """Hien preview avatar moi nhat. Neu chua co thi hien chu AVATAR."""
        preview_path = None

        if self.pending_avatar_source:
            preview_path = Path(self.pending_avatar_source)
        elif not self.remove_avatar_requested:
            preview_path = avatar_abs_path(self.current_user.get("avatar", "") if self.current_user else "")

        if preview_path and preview_path.exists():
            pixmap = QPixmap(str(preview_path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.lblAvatarPreview.width(),
                    self.lblAvatarPreview.height(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.lblAvatarPreview.setPixmap(scaled)
                self.lblAvatarPreview.setText("")
                return

        self.lblAvatarPreview.setPixmap(QPixmap())
        self.lblAvatarPreview.setText("AVATAR")

    def choose_avatar(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chon avatar",
            str(BASE_DIR),
            "Image Files (*.png *.jpg *.jpeg *.bmp)",
        )

        if not file_path:
            return

        self.pending_avatar_source = file_path
        self.remove_avatar_requested = False
        self.render_avatar()

    def clear_avatar(self):
        self.pending_avatar_source = None
        self.remove_avatar_requested = True
        self.render_avatar()

    def back_home(self):
        if self.home_window is not None:
            self.home_window.show()
        self.hide()

    def closeEvent(self, event):
        if self.home_window is not None:
            self.home_window.show()
        self.hide()
        event.ignore()

    def save_profile(self):
        """Luu thong tin moi cua user va dong bo ve Home."""
        if self.current_user is None:
            QMessageBox.warning(self, "Loi", "Khong co user nao dang duoc chinh sua.")
            return

        username = self.inputUsername.text().strip()
        full_name = self.inputFullName.text().strip()
        email = self.inputEmail.text().strip()
        phone = self.inputPhone.text().strip()
        address = self.inputAddress.text().strip()
        new_password = self.inputPassword.text()
        confirm_password = self.inputConfirmPassword.text()

        if not username:
            QMessageBox.warning(self, "Thieu thong tin", "Vui long nhap ten tai khoan.")
            self.inputUsername.setFocus()
            return

        if len(username) < 3:
            QMessageBox.warning(self, "Du lieu khong hop le", "Ten tai khoan phai co it nhat 3 ky tu.")
            self.inputUsername.setFocus()
            return

        if not email or not valid_email(email):
            QMessageBox.warning(self, "Du lieu khong hop le", "Email khong dung dinh dang.")
            self.inputEmail.setFocus()
            return

        phone_check = phone.replace(" ", "").replace("-", "").replace(".", "")
        if phone and not phone_check.lstrip("+").isdigit():
            QMessageBox.warning(self, "Du lieu khong hop le", "So dien thoai chi nen gom so va dau + - .")
            self.inputPhone.setFocus()
            return

        if new_password or confirm_password:
            if len(new_password) < 4:
                QMessageBox.warning(self, "Du lieu khong hop le", "Mat khau moi phai co it nhat 4 ky tu.")
                self.inputPassword.setFocus()
                return

            if new_password != confirm_password:
                QMessageBox.warning(self, "Du lieu khong hop le", "Mat khau moi va mat khau xac nhan khong khop.")
                self.inputConfirmPassword.clear()
                self.inputConfirmPassword.setFocus()
                return

        # Đọc lại từ file để tránh ghi đè lên dữ liệu đã bị thay đổi ở nơi khác.
        try:
            users = load_users()
        except ValueError as exc:
            QMessageBox.critical(self, "Loi du lieu", str(exc))
            return

        user_id = self.current_user["id"]
        target_user = next((user for user in users if user["id"] == user_id), None)
        if target_user is None:
            QMessageBox.warning(self, "Khong tim thay", "User hien tai khong con ton tai trong user.json.")
            return

        for user in users:
            if user["id"] == user_id:
                continue

            if norm(user["username"]) == norm(username):
                QMessageBox.warning(self, "Trung du lieu", "Ten tai khoan nay da duoc su dung.")
                self.inputUsername.setFocus()
                return

            if norm(user["email"]) == norm(email):
                QMessageBox.warning(self, "Trung du lieu", "Email nay da duoc su dung.")
                self.inputEmail.setFocus()
                return

        avatar_value = str(target_user.get("avatar", "")).strip()
        old_avatar_path = avatar_abs_path(avatar_value)

        if self.remove_avatar_requested:
            avatar_value = ""

        # Nếu user vừa chọn avatar mới thì copy ảnh về thư mục project để tránh lỗi mất file.
        if self.pending_avatar_source:
            ensure_project_dirs()
            source_path = Path(self.pending_avatar_source)
            suffix = source_path.suffix.lower() or ".png"
            destination_path = AVATAR_DIR / f"user_{user_id}_avatar{suffix}"

            try:
                shutil.copy2(source_path, destination_path)
            except OSError as exc:
                QMessageBox.critical(self, "Loi file", f"Khong the copy avatar: {exc}")
                return

            avatar_value = f"avatars/{destination_path.name}"

        if self.remove_avatar_requested and old_avatar_path and old_avatar_path.exists():
            try:
                if AVATAR_DIR in old_avatar_path.parents:
                    old_avatar_path.unlink(missing_ok=True)
            except OSError:
                pass

        if self.pending_avatar_source and old_avatar_path and old_avatar_path.exists():
            try:
                new_avatar_path = avatar_abs_path(avatar_value)
                if new_avatar_path and old_avatar_path != new_avatar_path and AVATAR_DIR in old_avatar_path.parents:
                    old_avatar_path.unlink(missing_ok=True)
            except OSError:
                pass

        # Chỉ khi toàn bộ kiểm tra hợp lệ thì mới ghi ngược vào bản ghi thật.
        target_user["username"] = username
        target_user["full_name"] = full_name
        target_user["email"] = email
        target_user["phone"] = phone
        target_user["address"] = address
        target_user["avatar"] = avatar_value

        if new_password:
            target_user["password"] = new_password

        save_users(users)

        self.current_user = dict(target_user)
        self.pending_avatar_source = None
        self.remove_avatar_requested = False
        self.inputPassword.clear()
        self.inputConfirmPassword.clear()
        self.render_avatar()

        # Sau khi lưu xong, báo về Home để mọi màn hình đang mở cập nhật lại theo user mới.
        if self.home_window is not None:
            self.home_window.handle_user_updated(self.current_user)

        QMessageBox.information(self, "Thanh cong", "Da cap nhat thong tin user.")


# ==================== Gio hang ====================
class CartWindow(QMainWindow):
    """Màn hình giỏ hàng, nơi user sửa số lượng và thực hiện thanh toán."""
    def __init__(self):
        super().__init__()
        uic.loadUi(ui_path("Cart.ui"), self)
        self.home_window = None
        self.current_user = None

        self.tableCart.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableCart.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tableCart.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableCart.verticalHeader().setVisible(False)

        self.btnBackHome.clicked.connect(self.hide)
        self.btnCheckout.clicked.connect(self.checkout)
        self.btnUpdateCart.clicked.connect(self.update_cart_quantities)
        self.btnRemoveSelected.clicked.connect(self.remove_selected_row)
        self.btnClearCart.clicked.connect(self.clear_cart)

    def set_home_window(self, home_window):
        self.home_window = home_window

    def set_current_user(self, user):
        self.current_user = user
        self.lblCartOwner.setText(f"Giỏ hàng của: {user_display_name(user)}")

    def show_cart(self):
        self.refresh_table()
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        self.hide()
        event.ignore()

    def refresh_table(self):
        """Đổ dữ liệu giỏ hàng từ Home sang bảng hiển thị."""
        if self.home_window is None:
            return

        entries = self.home_window.get_cart_entries()
        self.tableCart.setRowCount(len(entries))

        for row_index, entry in enumerate(entries):
            # Mỗi dòng là một snapshot của sản phẩm tại thời điểm hiện tại.
            product = entry["product"]
            quantity = entry["quantity"]
            amount = product["gia"] * quantity

            name_item = QTableWidgetItem(product["ten"])
            name_item.setData(Qt.ItemDataRole.UserRole, product["id"])
            self.tableCart.setItem(row_index, 0, name_item)
            self.tableCart.setItem(row_index, 1, QTableWidgetItem(product["loai"]))
            self.tableCart.setItem(row_index, 2, QTableWidgetItem(product["danh_muc"]))
            self.tableCart.setItem(row_index, 3, QTableWidgetItem(fmt_money(product["gia"])))
            self.tableCart.setItem(row_index, 5, QTableWidgetItem(fmt_money(amount)))

            # Người dùng chỉ được chỉnh số lượng trong ngưỡng tồn kho hiện còn.
            spin = QSpinBox()
            spin.setMinimum(1)
            spin.setMaximum(max(1, product["so_luong"]))
            spin.setValue(quantity)
            self.tableCart.setCellWidget(row_index, 4, spin)

        total_items = sum(entry["quantity"] for entry in entries)
        total_money = sum(entry["product"]["gia"] * entry["quantity"] for entry in entries)
        self.lblItemCount.setText(f"{total_items} sản phẩm trong giỏ")
        self.lblTotalMoney.setText(f"Tổng tiền: {fmt_money(total_money)}")
        self.tableCart.resizeColumnsToContents()
        self.tableCart.horizontalHeader().setStretchLastSection(True)

    def get_selected_product_id(self):
        row = self.tableCart.currentRow()
        if row < 0:
            return None
        item = self.tableCart.item(row, 0)
        return None if item is None else item.data(Qt.ItemDataRole.UserRole)

    def update_cart_quantities(self):
        """Lấy giá trị mới từ các QSpinBox rồi ghi ngược lại vào giỏ hàng ở Home."""
        if self.home_window is None:
            return
        for row in range(self.tableCart.rowCount()):
            item = self.tableCart.item(row, 0)
            spin = self.tableCart.cellWidget(row, 4)
            if item is None or spin is None:
                continue
            self.home_window.cart_items[item.data(Qt.ItemDataRole.UserRole)] = spin.value()
        self.home_window.cleanup_cart()
        self.refresh_table()

    def remove_selected_row(self):
        if self.home_window is None:
            return
        product_id = self.get_selected_product_id()
        if product_id is None:
            QMessageBox.warning(self, "Chua chon", "Vui long chon mot dong trong gio hang.")
            return
        self.home_window.cart_items.pop(product_id, None)
        self.refresh_table()

    def clear_cart(self):
        if self.home_window is None:
            return
        if not self.home_window.cart_items:
            QMessageBox.information(self, "Thong bao", "Gio hang hien dang rong.")
            return
        answer = QMessageBox.question(self, "Xac nhan", "Ban co chac muon xoa toan bo gio hang khong?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.home_window.cart_items.clear()
        self.refresh_table()

    def get_latest_user_record(self):
        """Doc lai user tu user.json de thong tin thanh toan luon la ban moi nhat."""
        if self.current_user is None:
            return None
        try:
            users = load_users()
        except ValueError as exc:
            QMessageBox.critical(self, "Loi du lieu", str(exc))
            return None
        return next((user for user in users if user["id"] == self.current_user["id"]), None)

    def checkout(self):
        """Thanh toan don gian: hien thong tin nguoi mua, tru ton kho va xoa gio hang."""
        if self.home_window is None:
            return
        if self.current_user is None:
            QMessageBox.warning(self, "Loi", "Ban chua dang nhap.")
            return

        self.update_cart_quantities()
        entries = self.home_window.get_cart_entries()
        if not entries:
            QMessageBox.information(self, "Thong bao", "Gio hang hien dang rong.")
            return

        latest_user = self.get_latest_user_record()
        if latest_user is None:
            QMessageBox.warning(self, "Khong tim thay", "Khong tim thay thong tin user trong user.json.")
            return

        buyer_name = user_display_name(latest_user)
        buyer_phone = str(latest_user.get("phone", "")).strip()
        buyer_address = str(latest_user.get("address", "")).strip()

        if not buyer_name:
            QMessageBox.warning(self, "Thieu thong tin", "Vui long cap nhat ten nguoi mua trong trang User.")
            return
        if not buyer_phone:
            QMessageBox.warning(self, "Thieu thong tin", "Vui long cap nhat so dien thoai trong trang User truoc khi thanh toan.")
            return
        if not buyer_address:
            QMessageBox.warning(self, "Thieu thong tin", "Vui long cap nhat dia chi nhan hang trong trang User truoc khi thanh toan.")
            return

        # Tồn kho phải đọc lại từ file để chắc chắn số lượng hiện tại là mới nhất.
        try:
            latest_products = load_products()
        except ValueError as exc:
            QMessageBox.critical(self, "Loi du lieu", str(exc))
            return

        product_map = {product["id"]: dict(product) for product in latest_products}
        for entry in entries:
            product_id = entry["product"]["id"]
            quantity = entry["quantity"]
            latest_product = product_map.get(product_id)
            if latest_product is None:
                QMessageBox.warning(self, "Khong tim thay", f"San pham '{entry['product']['ten']}' khong con ton tai.")
                return
            # Nếu một sản phẩm bị người khác mua mất trước đó thì chặn thanh toán.
            if latest_product["so_luong"] < quantity:
                QMessageBox.warning(
                    self,
                    "Khong du ton kho",
                    f"San pham '{latest_product['ten']}' chi con {latest_product['so_luong']} san pham trong kho.",
                )
                self.home_window.reload_products()
                self.refresh_table()
                return

        # Chỉ sau khi mọi dòng đều hợp lệ mới bắt đầu trừ kho.
        for entry in entries:
            product_id = entry["product"]["id"]
            quantity = entry["quantity"]
            product_map[product_id]["so_luong"] -= quantity

        updated_products = sorted(product_map.values(), key=lambda item: item["id"])
        save_products(updated_products)

        total_items = sum(entry["quantity"] for entry in entries)
        total_money = sum(entry["product"]["gia"] * entry["quantity"] for entry in entries)

        # Thanh toán thành công thì làm trống giỏ và reload lại Home để số tồn kho mới xuất hiện ngay.
        self.home_window.cart_items.clear()
        self.home_window.reload_products()
        self.set_current_user(latest_user)
        self.refresh_table()

        QMessageBox.information(
            self,
            "Thanh toan thanh cong",
            "\n".join(
                [
                    "Thanh toán thành công.",
                    f"Tên người mua: {buyer_name}",
                    f"Địa chỉ nhận: {buyer_address}",
                    f"Số điện thoại: {buyer_phone}",
                    f"Tổng số lượng: {total_items}",
                    f"Tổng tiền: {fmt_money(total_money)}",
                ]
            ),
        )


# ==================== Home ====================
class HomeWindow(QMainWindow):
    """
    Màn hình trung tâm của ứng dụng.

    Đây là nơi gom hầu hết hành vi nghiệp vụ:
    - Hiển thị sản phẩm từ JSON.
    - Lọc / sắp xếp / tìm kiếm.
    - Xem chi tiết và thêm vào giỏ.
    - CRUD sản phẩm nếu user là admin.
    """
    def __init__(self):
        super().__init__()
        uic.loadUi(ui_path("Home.ui"), self)

        self.login_window = None
        self.cart_window = None
        self.user_window = None
        self.current_user = None
        self.products = []
        self.cart_items = {}
        self.selected_product_id = None

        self.comboSpecies.clear()
        self.comboSpecies.addItems(["Tất cả loài"] + SPECIES_OPTIONS)
        self.comboSort.clear()
        self.comboSort.addItems(["Mặc định", "A -> Z", "Giá cao đến thấp", "Giá thấp đến cao"])
        self.comboAdminSpecies.clear()
        self.comboAdminSpecies.addItems(SPECIES_OPTIONS)
        self.comboAdminCategory.clear()
        self.comboAdminCategory.addItems(CATEGORY_OPTIONS)

        # Toàn bộ bộ lọc đều đổ về cùng một hàm render lại danh sách sản phẩm.
        self.inputSearch.textChanged.connect(self.refresh_product_tabs)
        self.comboSort.currentTextChanged.connect(self.refresh_product_tabs)
        self.comboSpecies.currentTextChanged.connect(self.refresh_product_tabs)
        self.btnResetFilters.clicked.connect(self.reset_filters)
        self.btnOpenCart.clicked.connect(self.open_cart)
        self.btnOpenUser.clicked.connect(self.open_user_profile)
        self.btnLogout.clicked.connect(self.logout)
        self.btnBrowseProductImage.clicked.connect(self.browse_product_image)
        self.btnAddProduct.clicked.connect(self.add_product)
        self.btnUpdateProduct.clicked.connect(self.update_product)
        self.btnDeleteProduct.clicked.connect(self.delete_product)
        self.btnClearProductForm.clicked.connect(self.clear_product_form)

        self.adminPanel.setVisible(False)
        self.update_admin_buttons_state()

    def set_login_window(self, login_window):
        self.login_window = login_window

    def set_cart_window(self, cart_window):
        self.cart_window = cart_window

    def set_user_window(self, user_window):
        self.user_window = user_window

    def is_admin(self):
        return bool(self.current_user and self.current_user.get("role") == ROLE_ADMIN)

    def set_current_user(self, user):
        """Luu user hien tai, cap nhat nhan dien tren Home va dong bo sang cac man hinh phu."""
        self.current_user = dict(user)

        # Giỏ hàng đang được quản lý theo phiên đăng nhập, nên khi đổi user sẽ reset về rỗng.
        self.cart_items = {}
        self.selected_product_id = None
        display_name = user_display_name(user)
        self.lblWelcome.setText(f"Xin chào, {display_name}")
        self.lblCurrentUser.setText(display_name)
        self.lblCurrentRole.setText("Admin" if user["role"] == ROLE_ADMIN else "User")
        if user["role"] == ROLE_ADMIN:
            self.lblSessionNote.setText("Bạn đang đăng nhập bằng quyền admin. Bạn có thể xem sản phẩm, giỏ hàng và CRUD sản phẩm.")
        else:
            self.lblSessionNote.setText("Bạn đang đăng nhập bằng quyền user. Bạn có thể tìm kiếm, lọc, xem chi tiết và thêm vào giỏ hàng.")
        self.adminPanel.setVisible(self.is_admin())
        self.clear_product_form(update_view=False)
        self.update_admin_buttons_state()
        if self.cart_window is not None:
            self.cart_window.set_current_user(self.current_user)
        if self.user_window is not None:
            self.user_window.set_current_user(self.current_user)
        self.reload_products()

    def handle_user_updated(self, updated_user):
        """Nhan user moi tu UserWindow va cap nhat cac widget dang hien thi."""
        self.current_user = dict(updated_user)
        display_name = user_display_name(self.current_user)

        self.lblWelcome.setText(f"Xin chào, {display_name}")
        self.lblCurrentUser.setText(display_name)
        self.lblCurrentRole.setText("Admin" if self.current_user["role"] == ROLE_ADMIN else "User")
        if self.current_user["role"] == ROLE_ADMIN:
            self.lblSessionNote.setText("Bạn đang đăng nhập bằng quyền admin. Bạn có thể xem sản phẩm, giỏ hàng và CRUD sản phẩm.")
        else:
            self.lblSessionNote.setText("Bạn đang đăng nhập bằng quyền user. Bạn có thể tìm kiếm, lọc, xem chi tiết và thêm vào giỏ hàng.")

        self.adminPanel.setVisible(self.is_admin())
        self.update_admin_buttons_state()

        if self.cart_window is not None:
            self.cart_window.set_current_user(self.current_user)
        if self.user_window is not None and self.user_window is not self.sender():
            self.user_window.set_current_user(self.current_user)

    def reload_products(self):
        """Nạp lại danh sách sản phẩm từ file rồi render lại toàn bộ Home."""
        try:
            self.products = load_products()
        except ValueError as exc:
            QMessageBox.critical(self, "Loi du lieu", str(exc))
            self.products = []
        self.cleanup_cart()
        self.refresh_product_tabs()

    def get_product_by_id(self, product_id):
        return next((product for product in self.products if product["id"] == product_id), None)

    def cleanup_cart(self):
        """Loại các sản phẩm không còn tồn tại hoặc vượt quá tồn kho khỏi giỏ hàng."""
        valid_products = {product["id"]: product for product in self.products}
        cleaned = {}
        for product_id, quantity in self.cart_items.items():
            product = valid_products.get(product_id)
            if product is None or product["so_luong"] <= 0:
                continue
            cleaned[product_id] = min(quantity, product["so_luong"])
        self.cart_items = cleaned
        if self.cart_window is not None and self.cart_window.isVisible():
            self.cart_window.refresh_table()

    def get_filtered_products(self):
        """Áp toàn bộ điều kiện search, filter và sort lên danh sách sản phẩm hiện có."""
        products = list(self.products)
        keyword = norm(self.inputSearch.text())
        species = self.comboSpecies.currentText()
        sort_mode = self.comboSort.currentText()

        if keyword:
            products = [product for product in products if keyword in norm(product["ten"])]
        if species != "Tất cả loài":
            products = [product for product in products if product["loai"] == species]

        if sort_mode == "A -> Z":
            products.sort(key=lambda item: norm(item["ten"]))
        elif sort_mode == "Giá cao đến thấp":
            products.sort(key=lambda item: item["gia"], reverse=True)
        elif sort_mode == "Giá thấp đến cao":
            products.sort(key=lambda item: item["gia"])
        else:
            products.sort(key=lambda item: item["id"])
        return products

    def refresh_product_tabs(self):
        """
        Render lại các tab danh mục.

        Mỗi lần search/filter/sort thay đổi, Home sẽ xây lại danh sách tab từ đầu
        để dữ liệu trên màn hình luôn khớp với trạng thái mới nhất.
        """
        products = self.get_filtered_products()
        current_tab = "Tất cả"
        if self.categoryTabs.count() > 0:
            current_tab = self.categoryTabs.tabText(self.categoryTabs.currentIndex())
        self.lblProductCounter.setText(f"{len(products)} sản phẩm")
        self.categoryTabs.clear()

        tab_groups = [("Tất cả", products)]
        for category in CATEGORY_OPTIONS:
            tab_groups.append((category, [product for product in products if product["danh_muc"] == category]))

        for title, group_products in tab_groups:
            self.categoryTabs.addTab(self.create_product_tab(group_products), title)

        for index in range(self.categoryTabs.count()):
            if self.categoryTabs.tabText(index) == current_tab:
                self.categoryTabs.setCurrentIndex(index)
                break

    def create_product_tab(self, products):
        """Tạo một tab chứa nhiều product card trong QGridLayout."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        grid = QGridLayout(content)
        grid.setContentsMargins(18, 18, 18, 18)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        if products:
            for index, product in enumerate(products):
                row = index // 3
                col = index % 3
                grid.addWidget(self.create_product_card(product), row, col)
        else:
            empty = QLabel("Khong co san pham phu hop voi bo loc hien tai.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: #506056; font-size: 11pt;")
            grid.addWidget(empty, 0, 0)

        scroll.setWidget(content)
        layout.addWidget(scroll)
        return tab

    def create_product_card(self, product):
        """Sinh một thẻ sản phẩm động từ dữ liệu JSON."""
        card = QFrame()
        card.setObjectName("productCard")
        card.setStyleSheet(CARD_STYLE)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        image_label = QLabel()
        image_label.setObjectName("productImage")
        image_label.setFixedHeight(170)
        set_product_image(image_label, product, 280, 170)
        layout.addWidget(image_label)

        # Phần text của card được tạo động để không phải thiết kế 50 card cố định trong Designer.
        labels = [
            (QLabel(f"Mã sản phẩm: {product['id']}"), "productId"),
            (QLabel(product["ten"]), "productTitle"),
            (QLabel(f"Loài: {product['loai']} | Nhóm: {product['danh_muc']}"), "productMeta"),
            (QLabel(fmt_money(product["gia"])), "productPrice"),
            (QLabel(f"Tồn kho: {product['so_luong']}"), "productStock"),
        ]
        for label, object_name in labels:
            label.setObjectName(object_name)
            label.setWordWrap(True)
            layout.addWidget(label)

        row = QHBoxLayout()
        btn_detail = QPushButton("Chi tiết")
        btn_detail.setObjectName("btnDetail")
        btn_detail.clicked.connect(lambda _=False, product_id=product["id"]: self.show_product_detail(product_id))
        row.addWidget(btn_detail)

        btn_add = QPushButton("Thêm giỏ")
        btn_add.setObjectName("btnAddCart")
        btn_add.setEnabled(product["so_luong"] > 0)
        btn_add.clicked.connect(lambda _=False, product_id=product["id"]: self.add_to_cart(product_id, 1))
        row.addWidget(btn_add)

        if self.is_admin():
            btn_edit = QPushButton("Nạp form")
            btn_edit.setObjectName("btnEdit")
            btn_edit.clicked.connect(lambda _=False, product_id=product["id"]: self.load_product_into_form(product_id))
            row.addWidget(btn_edit)

        layout.addStretch()
        layout.addLayout(row)
        return card

    def show_product_detail(self, product_id):
        """Mở dialog chi tiết. Kết quả dialog có thể là thêm vào giỏ hoặc nạp vào form admin."""
        product = self.get_product_by_id(product_id)
        if product is None:
            QMessageBox.warning(self, "Khong tim thay", "San pham khong ton tai.")
            return

        dialog = ProductDetailDialog(product, is_admin=self.is_admin(), parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.load_to_form_requested:
            self.load_product_into_form(product_id)
            return
        self.add_to_cart(product_id, dialog.selected_quantity)

    def add_to_cart(self, product_id, quantity):
        """Thêm sản phẩm vào giỏ nhưng vẫn tôn trọng giới hạn tồn kho."""
        product = self.get_product_by_id(product_id)
        if product is None:
            QMessageBox.warning(self, "Khong tim thay", "San pham khong ton tai.")
            return
        if product["so_luong"] <= 0:
            QMessageBox.warning(self, "Het hang", "San pham nay hien da het hang.")
            return

        current = self.cart_items.get(product_id, 0)
        new_quantity = min(current + quantity, product["so_luong"])
        if new_quantity == current:
            QMessageBox.information(self, "Thong bao", "So luong trong gio hang da dat toi gioi han ton kho.")
            return

        self.cart_items[product_id] = new_quantity
        if self.cart_window is not None and self.cart_window.isVisible():
            self.cart_window.refresh_table()
        QMessageBox.information(self, "Da them", f"Da them {product['ten']} vao gio hang.")

    def get_cart_entries(self):
        """Chuyển dict cart_items thành list thuận tiện cho CartWindow hiển thị."""
        entries = []
        for product_id, quantity in self.cart_items.items():
            product = self.get_product_by_id(product_id)
            if product is not None:
                entries.append({"product": product, "quantity": quantity})
        return entries

    def open_cart(self):
        if self.cart_window is None:
            QMessageBox.warning(self, "Loi", "Khong mo duoc man hinh gio hang.")
            return
        if self.current_user is None:
            QMessageBox.warning(self, "Loi", "Ban chua dang nhap.")
            return
        self.cleanup_cart()
        self.cart_window.set_current_user(self.current_user)
        self.cart_window.show_cart()

    def open_user_profile(self):
        """Mo man hinh User de user tu cap nhat thong tin ca nhan."""
        if self.user_window is None:
            QMessageBox.warning(self, "Loi", "Khong mo duoc man hinh thong tin user.")
            return
        if self.current_user is None:
            QMessageBox.warning(self, "Loi", "Ban chua dang nhap.")
            return

        self.user_window.set_current_user(self.current_user)
        self.user_window.show()
        self.user_window.raise_()
        self.user_window.activateWindow()
        self.hide()

    def logout(self):
        answer = QMessageBox.question(self, "Dang xuat", "Ban co chac muon dang xuat khong?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.current_user = None
        self.cart_items.clear()
        self.selected_product_id = None
        if self.cart_window is not None:
            self.cart_window.hide()
        if self.user_window is not None:
            self.user_window.hide()
        if self.login_window is not None:
            self.login_window.Email.clear()
            self.login_window.Password.clear()
            self.login_window.show()
        self.hide()

    def reset_filters(self):
        self.inputSearch.clear()
        self.comboSort.setCurrentText("Mặc định")
        self.comboSpecies.setCurrentText("Tất cả loài")
        self.refresh_product_tabs()

    def update_admin_buttons_state(self):
        """Bật/tắt nút admin tùy theo quyền hiện tại và trạng thái chọn sản phẩm."""
        is_admin = self.is_admin()
        has_selection = self.selected_product_id is not None
        self.btnAddProduct.setEnabled(is_admin)
        self.btnUpdateProduct.setEnabled(is_admin and has_selection)
        self.btnDeleteProduct.setEnabled(is_admin and has_selection)
        self.btnClearProductForm.setEnabled(is_admin)
        self.btnBrowseProductImage.setEnabled(is_admin)

    def clear_product_form(self, update_view=True):
        """Đưa form admin về trạng thái trống để thêm sản phẩm mới."""
        self.selected_product_id = None
        self.lblSelectedProduct.setText("Chưa chọn sản phẩm")
        self.inputProductName.clear()
        self.inputProductImage.clear()
        self.comboAdminSpecies.setCurrentText(SPECIES_OPTIONS[0])
        self.comboAdminCategory.setCurrentText(CATEGORY_OPTIONS[0])
        self.spinProductPrice.setValue(0)
        self.spinProductStock.setValue(0)
        self.update_admin_buttons_state()
        if update_view:
            self.refresh_product_tabs()

    def load_product_into_form(self, product_id):
        """Nạp thông tin một sản phẩm vào form admin để sửa."""
        product = self.get_product_by_id(product_id)
        if product is None:
            QMessageBox.warning(self, "Khong tim thay", "San pham khong ton tai.")
            return
        self.selected_product_id = product_id
        self.lblSelectedProduct.setText(f"[{product['id']}] {product['ten']}")
        self.inputProductName.setText(product["ten"])
        self.inputProductImage.setText(product.get("img", ""))
        self.comboAdminSpecies.setCurrentText(product["loai"])
        self.comboAdminCategory.setCurrentText(product["danh_muc"])
        self.spinProductPrice.setValue(product["gia"])
        self.spinProductStock.setValue(product["so_luong"])
        self.update_admin_buttons_state()

    def browse_product_image(self):
        """Cho admin chon nhanh file anh san pham tu may."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chon anh san pham",
            str(BASE_DIR),
            "Image Files (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if file_path:
            self.inputProductImage.setText(file_path)

    def collect_product_form_data(self):
        """Đọc dữ liệu từ form admin và trả ra dict sản phẩm đã kiểm tra cơ bản."""
        name = self.inputProductName.text().strip()
        image_path = self.inputProductImage.text().strip()
        species = self.comboAdminSpecies.currentText()
        category = self.comboAdminCategory.currentText()
        price = self.spinProductPrice.value()
        stock = self.spinProductStock.value()
        if not name:
            QMessageBox.warning(self, "Thieu thong tin", "Vui long nhap ten san pham.")
            self.inputProductName.setFocus()
            return None
        if price <= 0:
            QMessageBox.warning(self, "Du lieu khong hop le", "Gia san pham phai lon hon 0.")
            self.spinProductPrice.setFocus()
            return None
        if image_path:
            image_file = product_image_abs_path(image_path)
            if image_file is None or not image_file.exists():
                QMessageBox.warning(self, "Anh khong hop le", "Duong dan anh san pham khong ton tai.")
                self.inputProductImage.setFocus()
                return None

        return {
            "ten": name,
            "loai": species,
            "gia": price,
            "so_luong": stock,
            "danh_muc": category,
            "img": image_path or default_product_image_value(),
        }

    def add_product(self):
        """Admin thêm sản phẩm mới vào `data.json`."""
        if not self.is_admin():
            QMessageBox.warning(self, "Khong du quyen", "Chi admin moi co quyen them san pham.")
            return
        product = self.collect_product_form_data()
        if product is None:
            return
        if any(norm(item["ten"]) == norm(product["ten"]) for item in self.products):
            QMessageBox.warning(self, "Trung du lieu", "Ten san pham da ton tai.")
            self.inputProductName.setFocus()
            return
        # id chỉ được sinh sau khi form hợp lệ để tránh nhảy số vô ích.
        product["id"] = next_id(self.products)
        try:
            product["img"] = store_product_image(product.get("img", ""), product["id"])
        except OSError as exc:
            QMessageBox.critical(self, "Loi file", f"Khong the luu anh san pham: {exc}")
            return
        self.products.append(product)
        save_products(self.products)
        self.reload_products()
        self.load_product_into_form(product["id"])
        QMessageBox.information(self, "Thanh cong", "Da them san pham moi.")

    def update_product(self):
        """Admin cập nhật sản phẩm đang được chọn trong form."""
        if not self.is_admin():
            QMessageBox.warning(self, "Khong du quyen", "Chi admin moi co quyen sua san pham.")
            return
        if self.selected_product_id is None:
            QMessageBox.warning(self, "Chua chon", "Vui long chon mot san pham de cap nhat.")
            return
        product = self.collect_product_form_data()
        if product is None:
            return
        for item in self.products:
            if item["id"] != self.selected_product_id and norm(item["ten"]) == norm(product["ten"]):
                QMessageBox.warning(self, "Trung du lieu", "Ten san pham nay da ton tai o mot san pham khac.")
                self.inputProductName.setFocus()
                return
        for index, item in enumerate(self.products):
            if item["id"] == self.selected_product_id:
                product["id"] = self.selected_product_id
                try:
                    product["img"] = store_product_image(product.get("img", ""), product["id"])
                except OSError as exc:
                    QMessageBox.critical(self, "Loi file", f"Khong the luu anh san pham: {exc}")
                    return
                self.products[index] = product
                break
        save_products(self.products)
        self.reload_products()
        self.load_product_into_form(self.selected_product_id)
        QMessageBox.information(self, "Thanh cong", "Da cap nhat san pham.")

    def delete_product(self):
        """Admin xóa sản phẩm và dọn luôn ảnh riêng của sản phẩm đó nếu có."""
        if not self.is_admin():
            QMessageBox.warning(self, "Khong du quyen", "Chi admin moi co quyen xoa san pham.")
            return
        if self.selected_product_id is None:
            QMessageBox.warning(self, "Chua chon", "Vui long chon mot san pham de xoa.")
            return
        product = self.get_product_by_id(self.selected_product_id)
        if product is None:
            QMessageBox.warning(self, "Khong tim thay", "San pham khong ton tai.")
            return
        answer = QMessageBox.question(self, "Xac nhan xoa", f"Ban co chac muon xoa san pham '{product['ten']}' khong?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        deleted_id = self.selected_product_id
        deleted_image = product_image_abs_path(product.get("img", ""))
        self.products = [item for item in self.products if item["id"] != deleted_id]
        self.cart_items.pop(deleted_id, None)
        save_products(self.products)
        try:
            if deleted_image and deleted_image.exists() and deleted_image.parent == PRODUCT_IMAGE_DIR and deleted_image != DEFAULT_PRODUCT_IMAGE:
                deleted_image.unlink(missing_ok=True)
        except OSError:
            pass
        self.reload_products()
        self.clear_product_form(update_view=False)
        QMessageBox.information(self, "Thanh cong", f"Da xoa san pham ma {deleted_id}.")


# ==================== Main ====================
def main():
    """
    Điểm khởi động của chương trình.

    Hàm này tạo toàn bộ cửa sổ rồi nối chúng lại với nhau:
    Login <-> Register <-> Home <-> Cart / User
    """
    ensure_project_dirs()
    app = QApplication(sys.argv)
    login_window = Login()
    register_window = Register()
    home_window = HomeWindow()
    cart_window = CartWindow()
    user_window = UserWindow()

    # Đây là bước "ghép dây" giữa các cửa sổ để chúng có thể gọi qua lại.
    login_window.set_windows(register_window, home_window)
    register_window.set_login_window(login_window)
    home_window.set_login_window(login_window)
    home_window.set_cart_window(cart_window)
    home_window.set_user_window(user_window)
    cart_window.set_home_window(home_window)
    user_window.set_home_window(home_window)

    login_window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
