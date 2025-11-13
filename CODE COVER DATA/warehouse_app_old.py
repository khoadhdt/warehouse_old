"""
    ĐÂY LÀ PHẦN MỀM QUẢN LÝ KHO --> update 2025-10-30
    >> cải thiện search nhanh hơn (29-09-2025, tìm 1 lần nhiều lựa chọn)
    >> Đã cải tiến lại tốc độ xử lý dữ liệu
    >> Tab Xuất kho thêm nút search (13-03-2025)
    >> Cải thiện phần mềm để dữ liệu hoạt động theo group EOL, FOL, TEST, SMT (13-03-2025)
    >> Bỏ cột cập nhật link hình ảnh >> lấy theo mặc định mã ID (11-04-2025)
    >> Thêm tab Chat (15-04-2025)
    Nội dung file config_settings.ini
        [SETTINGS]
        DB_OTHER_PATH = \\172.23.10.230\map-eng\8. BAO CAO THIET BI EOL\2.SOFTWARE\Data\Inventory_management\Inventory_management_OTHER.db
        LINK_SMT = \\172.23.10.230\map-eng\6. SMT\1. SOFTWARE\Inventory_management
        LINK_FOL = \\172.23.10.230\map-eng\7. FOL\1. SOFTWARE\Inventory_management
        LINK_TEST = \\172.23.10.230\map-eng\9. TEST\1. SOFTWARE\Inventory_management
        LINK_EOL = D:\Laptrinh\Python\.WSE\Inventory Management\LINH KIEN KHO EOL
    Hướng dẫn setup:
        Thư viện hình nhân viên : \\172.23.10.230\map-eng\8. BAO CAO THIET BI EOL\2.SOFTWARE\Data\Employee_images
        file config_settings.ini : \\172.23.10.230\map-eng\8. BAO CAO THIET BI EOL\2.SOFTWARE\Data\Inventory_management\config_settings.ini
        Setup cho địa chỉ của các nhóm SMT, FOL, TEST, EOL :
            Trong đường link chính cần tạo các folder sau :
                tạo folder "Machine" --> bỏ dữ liệu database vào Inventory_management_EOL.db
                Tạo folder Other\inventory_management_images_EOL --> chứa hình ảnh

"""

from constants import *         # Thư viện đường dẫn setup
from db_utils import get_db_connection, safe_execute
from screen_InventoryManager import Ui_InventoryManager
# from circular_progress import CircularProgress
import PySide6.QtWidgets as QtWidgets
from PySide6.QtWidgets import (QApplication, QMainWindow, QHBoxLayout, QVBoxLayout,
                               QSizePolicy, QTableWidgetItem, QFileDialog, QListWidget,
                               QMessageBox, QPushButton, QLabel, QCompleter, QDialog,
                               QLineEdit, QGroupBox, QListWidgetItem, QInputDialog, QProgressDialog, QWidget)
from PySide6.QtGui import QPixmap, QGuiApplication, QPainter, QColor, QPen, QMouseEvent, QKeyEvent
from PySide6.QtCore import Qt, QTimer, QSize, QEvent, QRectF, QThread, Signal, QRect
from datetime import datetime
import shutil
import os
import re
from rapidfuzz import fuzz
import pandas as pd
import sys
import bcrypt
import sqlite3
from typing import List, Tuple, Any
import configparser
import json
from PIL import Image  # Cần cài đặt thư viện Pillow: pip install Pillow
from io import StringIO
import csv
import subprocess
from typing import List, Optional
import time

# Đọc file config_settings.ini
config = configparser.ConfigParser()
config.read(FILE_SETUP)  # FILE_SETUP đã được định nghĩa trong constants_try.py

# Lấy các đường dẫn từ section [SETTINGS]
LINK_SMT = config['SETTINGS']['LINK_SMT']
LINK_FOL = config['SETTINGS']['LINK_FOL']
LINK_TEST = config['SETTINGS']['LINK_TEST']
LINK_EOL = config['SETTINGS']['LINK_EOL']
LINK_INVOICE_SMT = config['SETTINGS']['LINK_INVOICE_SMT']
LINK_INVOICE_FOL = config['SETTINGS']['LINK_INVOICE_FOL']
LINK_INVOICE_TEST = config['SETTINGS']['LINK_INVOICE_TEST']
LINK_INVOICE_EOL = config['SETTINGS']['LINK_INVOICE_EOL']
DB_OTHER_PATH = config['SETTINGS']['DB_OTHER_PATH']

# Class danh sách chọn nhiều mục


class MultiSelectListWidget(QListWidget):
    """Custom QListWidget for multi-select dropdown functionality."""

    def __init__(self, parent=None, dropdown_widget=None):
        super().__init__(parent)
        self.dropdown_widget = dropdown_widget
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setSelectionMode(QListWidget.MultiSelection)
        self.itemClicked.connect(self.handle_item_clicked)
        # Thiết lập cho list widget
        self.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 2px;
                color: #1e3a8a; /* màu chữ xanh dương */
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
        """)

    def handle_item_clicked(self, item: QListWidgetItem):
        """Handle item click and update dropdown."""
        if self.dropdown_widget:
            self.dropdown_widget.update_selected_items()

    def leaveEvent(self, event: QEvent):
        """Hide list when mouse leaves."""
        self.hide()
        super().leaveEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard navigation."""
        super().keyPressEvent(event)
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.dropdown_widget.update_selected_items()
            self.hide()
        elif event.key() == Qt.Key_Escape:
            self.hide()


class MultiSelectDropdown(QWidget):
    """Custom multi-select dropdown widget with chip display."""

    def __init__(self, parent: QMainWindow, items: List[str], object_name: str):
        super().__init__(parent)
        self.parent = parent
        self.items = items
        self.object_name = object_name
        self.selected_items: List[str] = []
        self.init_ui()

    def init_ui(self):
        """Initialize the UI components."""
        self.setObjectName(self.object_name)

        # Main layout
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(6, 6, 6, 6)
        self.main_layout.setSpacing(6)

        # Chips container
        self.chips_container = QWidget()
        self.chips_layout = QHBoxLayout(self.chips_container)
        self.chips_layout.setContentsMargins(0, 0, 0, 0)
        self.chips_layout.setSpacing(6)
        # Ensure chips align to the left
        self.chips_layout.setAlignment(Qt.AlignLeft)
        self.main_layout.addWidget(self.chips_container)

        # Dropdown button
        self.dropdown_button = QPushButton("▼")
        self.dropdown_button.setFixedSize(26, 28)
        self.dropdown_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #d1d5db;
                background-color: #f3f4f6;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 14px;
                font-weight: 500;
                color: #374151;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
            }
            QPushButton:pressed {
                background-color: #d1d5db;
            }
        """)
        self.dropdown_button.clicked.connect(self.toggle_list_widget)
        self.main_layout.addWidget(
            self.dropdown_button, alignment=Qt.AlignRight)

        # List widget
        self.list_widget = MultiSelectListWidget(self.parent, self)
        self.list_widget.addItems(self.items)
        self.list_widget.hide()

        # Widget styling
        self.setStyleSheet("""
            QWidget {
                border: 1px solid #d1d5db;
                background-color: #ffffff;
                border-radius: 6px;
                padding: 6px;
            }
            QWidget:focus {
                border: 2px solid #3b82f6;
            }
        """)
        self.setFocusPolicy(Qt.StrongFocus)

    def toggle_list_widget(self):
        """Toggle visibility of the list widget."""
        try:
            if self.list_widget.isVisible():
                self.list_widget.hide()
            else:
                self.load_items()
                pos = self.mapToGlobal(self.rect().bottomLeft())
                self.list_widget.setGeometry(
                    QRect(pos.x(), pos.y(), self.width(), min(200, len(self.items) * 32)))
                self.list_widget.show()
                self.list_widget.setFocus()
        except Exception as e:
            print(f"Error toggling list widget: {str(e)}")

    def load_items(self):
        """Load or refresh items in the list widget."""
        try:
            self.list_widget.clear()
            self.list_widget.addItems(self.items)
            for i in range(self.list_widget.count()):
                if self.list_widget.item(i).text() in self.selected_items:
                    self.list_widget.item(i).setSelected(True)
        except Exception as e:
            print(f"Error loading items: {str(e)}")

    def update_selected_items(self):
        """Update selected items and refresh chips."""
        try:
            self.selected_items = [item.text()
                                   for item in self.list_widget.selectedItems()]
            self.update_chips()
            # print(f"Selected items for {self.object_name}: {self.selected_items}")
        except Exception as e:
            print(f"Error updating selected items: {str(e)}")

    def update_chips(self):
        """Update chip display for selected items."""
        try:
            # Clear existing chips and spacers
            while self.chips_layout.count() > 0:
                item = self.chips_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # Add new chips
            for item in self.selected_items:
                chip_widget = QWidget()
                chip_layout = QHBoxLayout(chip_widget)
                chip_layout.setContentsMargins(4, 2, 4, 2)
                chip_layout.setSpacing(4)

                chip_label = QLabel(item)
                chip_label.setStyleSheet("""
                    QLabel {
                        background-color: #dbeafe;
                        color: #1e3a8a;
                        border-radius: 12px;
                        padding: 4px 8px;
                        font-size: 13px;
                        font-weight: 500;
                    }
                """)
                chip_layout.addWidget(chip_label)

                remove_button = QPushButton("✕")
                remove_button.setFixedSize(20, 20)
                remove_button.setStyleSheet("""
                    QPushButton {
                        border: none;
                        background-color: #ef4444;
                        color: white;
                        border-radius: 10px;
                        font-size: 12px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #dc2626;
                    }
                    QPushButton:pressed {
                        background-color: #b91c1c;
                    }
                """)
                remove_button.clicked.connect(
                    lambda _, i=item: self.remove_item(i))
                chip_layout.addWidget(remove_button)

                self.chips_layout.addWidget(chip_widget)

            self.chips_layout.addStretch()  # Push chips to the left
        except Exception as e:
            print(f"Error updating chips: {str(e)}")

    def remove_item(self, item: str):
        """Remove an item from selection."""
        try:
            for i in range(self.list_widget.count()):
                if self.list_widget.item(i).text() == item:
                    self.list_widget.item(i).setSelected(False)
            self.update_selected_items()
        except Exception as e:
            print(f"Error removing item: {str(e)}")

    def get_selected_items(self) -> List[str]:
        """Return list of selected items."""
        return self.selected_items

    def set_selected_items(self, items: List[str]):
        """Set selected items programmatically."""
        try:
            self.list_widget.clearSelection()
            self.selected_items = [
                item for item in items if item in self.items]
            self.load_items()
            self.update_chips()
        except Exception as e:
            print(f"Error setting selected items: {str(e)}")

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events."""
        try:
            if self.list_widget.isVisible() and not self.list_widget.geometry().contains(event.globalPos()):
                self.list_widget.hide()
            super().mousePressEvent(event)
        except Exception as e:
            print(f"Error in mouse press event: {str(e)}")

    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard events."""
        if event.key() == Qt.Key_Down:
            self.toggle_list_widget()
        super().keyPressEvent(event)


# Lớp CopyWorker để chạy lệnh copy trong luồng nền, tránh làm đơ giao diện
class CopyWorker(QThread):
    finished = Signal(str, int)
    progress = Signal(int)

    def __init__(self, source_files, destination_folder):
        super().__init__()
        self.source_files = source_files
        self.destination_folder = destination_folder

    def run(self):
        total = len(self.source_files)
        copied = 0
        failed = 0
        for index, src_path in enumerate(self.source_files):
            try:
                filename = os.path.basename(src_path)
                dest_path = os.path.join(self.destination_folder, filename)
                shutil.copy2(src_path, dest_path)
                copied += 1
            except Exception as e:
                failed += 1
                print(f"Lỗi copy {src_path}: {e}")
            percent = int((index + 1) / total * 100)
            self.progress.emit(percent)

        if copied > 0:
            message = f"✅ Đã copy {copied}/{total} hình ảnh vào:\n{self.destination_folder}"
        else:
            message = "❌ Không copy được hình nào."

        self.finished.emit(message, copied)


class MyOther:
    """Class này chứa các hàm tiện ích khác nhau."""

    @staticmethod
    def extract_excel_clipboard():
        app = QApplication.instance() or QApplication(sys.argv)
        clipboard = app.clipboard()
        copied_text = clipboard.text()

        # Dùng csv.reader để xử lý dữ liệu có dấu ngoặc kép, tab
        reader = csv.reader(StringIO(copied_text), delimiter='\t')
        results = []

        for values in reader:
            if len(values) >= 11:
                a = values[0].strip()
                d = values[3].strip()
                e = values[4].strip()
                j = values[9].strip()
                k = values[10].strip()
                result_str = f'{j}{k}_{a}_{d}-{e}'
                results.append(result_str)
        return results

# Đây phần xử lý kích thước (Dài x Rộng x Cao)


class SizeHandler:
    """Xử lý kích thước (Dài x Rộng x Cao)."""

    @staticmethod
    def to_string(length_widget, width_widget, height_widget):
        """Chuyển 3 giá trị từ QLineEdit thành chuỗi."""
        length = length_widget.text().strip()
        width = width_widget.text().strip()
        height = height_widget.text().strip()
        if length and width and height:
            return f"{length} x {width} x {height}"
        return ""

    @staticmethod
    def to_fields(size_str, length_widget, width_widget, height_widget):
        """Tách chuỗi kích thước và điền vào 3 QLineEdit."""
        size_parts = size_str.split(" x ") if size_str else ["", "", ""]
        length_widget.setText(size_parts[0].strip())
        width_widget.setText(
            size_parts[1].strip() if len(size_parts) > 1 else "")
        height_widget.setText(
            size_parts[2].strip() if len(size_parts) > 2 else "")

    @staticmethod
    def build_size_regex(length, width, height):
        # Hàm build regex cho size lọc theo kiểu 3 chiều

        def part_to_regex(val):
            if val == '' or val == '?':
                # phần này có thể là bất kỳ số (integer hoặc float)
                return r'\d+(\.\d+)?'
            else:
                # Escape dấu chấm nếu có, để regex hiểu đúng số
                val_escaped = re.escape(val)
                return val_escaped

        regex_pattern = f"^{part_to_regex(length)} x {part_to_regex(width)} x {part_to_regex(height)}$"
        return regex_pattern


class UserManager:
    def __init__(self):
        self.db_path = DB_OTHER_PATH
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self._create_table()

    def _create_table(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            level TEXT NOT NULL,
            team TEXT NOT NULL
        )
        """)
        self.conn.commit()
        pass

    def add_user(self, username, password, level, team):
        hashed_password = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt())
        try:
            self.cursor.execute("""
            INSERT INTO user_inventory (username, password, level, team)
            VALUES (?, ?, ?, ?)""", (username, hashed_password, level, team))
            self.conn.commit()
            self.show_message("Success", "Thêm tài khoản thành công!", "info")
        except sqlite3.IntegrityError:
            self.show_message("Error", "Đăng ký tài khoản bị lỗi!", "error")

    def login(self, username, password):
        self.cursor.execute(
            "SELECT password, level, team FROM user_inventory WHERE username = ?", (username,))
        result = self.cursor.fetchone()
        if result and bcrypt.checkpw(password.encode('utf-8'), result[0]):
            return True, result[1], result[2]
        return False, None, None

    def change_password(self, username, old_password, new_password, new_password2):
        if new_password != new_password2:
            self.show_message(
                "Error", "Nhập mật khẩu mới không trùng khớp!", "error")
            return

        self.cursor.execute(
            "SELECT password FROM user_inventory WHERE username = ?", (username,))
        result = self.cursor.fetchone()
        if result and bcrypt.checkpw(old_password.encode('utf-8'), result[0]):
            hashed_new_password = bcrypt.hashpw(
                new_password.encode('utf-8'), bcrypt.gensalt())
            self.cursor.execute("UPDATE user_inventory SET password = ? WHERE username = ?",
                                (hashed_new_password, username))
            self.conn.commit()
            self.show_message(
                "Success", "Thay đổi mật khẩu thành công!", "info")
        else:
            self.show_message("Error", "Mật khẩu cũ nhập không đúng!", "error")

    def show_message(self, title, message, message_type):
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setIcon(QMessageBox.Information if message_type ==
                        "info" else QMessageBox.Critical)
        msg_box.setText(message)
        msg_box.exec()

    def close(self):
        self.conn.close()


class DatabaseHandler:
    def __init__(self):
        self.db_path = DB_DATA_PATH
        self.cache = {}  # Bộ nhớ đệm cho dữ liệu bảng

    def set_db_path(self, db_path):
        """Phương thức để cập nhật đường dẫn cơ sở dữ liệu."""
        self.db_path = db_path
        self.cache.clear()  # Xóa cache khi thay đổi đường dẫn

    def connect(self):
        return get_db_connection(self.db_path)

    def read_data(self, table_name: str, columns: List[str] = None) -> pd.DataFrame:
        if table_name not in self.cache:
            conn = self.connect()
            cursor = conn.cursor()

            # Kiểm tra cấu trúc bảng
            cursor.execute(f"PRAGMA table_info({table_name})")
            actual_columns = {col[1] for col in cursor.fetchall()}

            # Nếu không có cột nào, trả về DataFrame rỗng với cột mong muốn
            if not actual_columns:
                conn.close()
                return pd.DataFrame(columns=columns or [])

            # Xử lý truy vấn với danh sách cột
            if columns:
                missing_columns = [
                    col for col in columns if col not in actual_columns]
                if missing_columns:
                    raise ValueError(f"Các cột {missing_columns} không tồn tại trong bảng {table_name}. "
                                     f"Các cột hiện có: {list(actual_columns)}")
                query = f"SELECT {', '.join(columns)} FROM {table_name}"
            else:
                query = f"SELECT * FROM {table_name}"

            try:
                df = pd.read_sql_query(query, conn)
                self.cache[table_name] = df
            except Exception as e:
                raise RuntimeError(f"Lỗi khi đọc dữ liệu từ {table_name}: {e}")
            finally:
                conn.close()

            # Kiểm tra lại cột trong DataFrame
            if columns and not all(col in df.columns for col in columns):
                raise ValueError(f"Truy vấn không trả về đầy đủ cột yêu cầu. "
                                 f"Cột yêu cầu: {columns}, Cột nhận được: {df.columns.tolist()}")

        return self.cache[table_name].copy()

    def get_column_names(self, table_name: str) -> List[str]:
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        conn.close()
        return columns

    def insert_data(self, table_name: str, data: Tuple[Any, ...]):
        placeholders = ", ".join("?" for _ in data)
        query = f"INSERT INTO {table_name} VALUES ({placeholders})"
        with self.connect() as conn:
            safe_execute(conn, query, data)
        self.cache.pop(table_name, None)  # XÓA CACHE

    def update_data(self, table_name: str, column_values: dict, condition: str):
        set_clause = ", ".join([f"{col} = ?" for col in column_values.keys()])
        query = f"UPDATE {table_name} SET {set_clause} WHERE {condition}"
        with self.connect() as conn:
            safe_execute(conn, query, tuple(column_values.values()))
            # conn.commit() ĐÃ CÓ TRONG safe_execute → OK
        self.cache.pop(table_name, None)

    def delete_data(self, table_name: str, condition: str):
        query = f"DELETE FROM {table_name} WHERE {condition}"
        with self.connect() as conn:
            safe_execute(conn, query)
        self.cache.pop(table_name, None)

    def load_combo_box_data(self, table_name: str) -> dict:
        columns = ['model', 'process', 'groups',
                   'material', 'unit', 'storage_location', 'status']
        combo_data = {col: [] for col in columns}
        df = self.read_data(table_name, columns)
        for col in columns:
            combo_data[col] = df[col].dropna().unique().tolist()
        return combo_data


class InputManager:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def add_item(self, data):
        self.db_handler.insert_data(TABLE_INPUT, data)

    def search_items(self, filters, sort_by="date_time", ascending=False):
        columns_needed = ["id", "component_id", "component_name",
                          "process", "model", "size",
                          "quantity", "unit", "groups", "material", "storage_location", "invoice", "desinvoice", "status",
                          "note", "date_time", "username"]
        df = self.db_handler.read_data(TABLE_INPUT, columns_needed)
        conditions = []
        for key, (value, active) in filters.items():
            if active and value:
                conditions.append(df[key].str.contains(
                    value, case=False, na=False))
        if conditions:
            final_condition = conditions[0]
            for condition in conditions[1:]:
                final_condition &= condition
            df = df.loc[final_condition]
        df.sort_values(by=sort_by, ascending=ascending, inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df


class InventoryManagerApp(QMainWindow, Ui_InventoryManager):
    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self.db_handler = DatabaseHandler()  # Khởi tạo self.db_handler trước
        self.db_handler.cache.clear()       # Xóa cache sau khi đã khởi tạo
        self.setupUi(self)
        self.setWindowTitle(WINDOW_TITLE)
        self.IMAGE_LABEL_SIZE_ZOOM = list(DEFAULT_IMAGE_LABEL_SIZE_ZOOM)
        self.input_manager = InputManager(self.db_handler)

        # Khởi tạo các thuộc tính hình ảnh
        self.selected_image_path_input = DEFAULT_IMAGE_PATH
        self.selected_image_path_output = DEFAULT_IMAGE_PATH
        self.selected_image_path_inventory = DEFAULT_IMAGE_PATH

        self.link_invoice = INVOICE_FOLDER_PATH

        self.user_levels = 0

        # Không cần đọc .ini nữa, sử dụng các biến toàn cục
        self.team_links = {
            "SMT": {
                "main": LINK_SMT,
                "invoice": LINK_INVOICE_SMT
            },
            "FOL": {
                "main": LINK_FOL,
                "invoice": LINK_INVOICE_FOL
            },
            "TEST": {
                "main": LINK_TEST,
                "invoice": LINK_INVOICE_TEST
            },
            "EOL": {
                "main": LINK_EOL,
                "invoice": LINK_INVOICE_EOL
            }
        }

        self.setupUI()

        self.images_zoom_label.hide()
        self.image_user_label.mouseDoubleClickEvent = self.dang_xuat_login
        self.tabWidget_main.currentChanged.connect(self.on_tab_changed)
        self.tabWidget_main.setCurrentIndex(0)

        # Kiểm tra nếu widget đã có layout
        if self.centralWidget() is None:
            self.setCentralWidget(self.MyWidget)
            self.MyWidget.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.showMaximized()

    def closeEvent(self, event):
        # self.mark_user_offline()
        print("[INFO] Đã đăng xuất tài khoản.")
        event.accept()  # Cho phép đóng

    def update_paths_by_team(self, team):
        global DB_DATA_PATH, IMAGES_FOLDER_PATH, INVOICE_FOLDER_PATH

        if team not in self.team_links:
            raise ValueError(
                f"Team '{team}' không được định nghĩa trong config_settings.ini")

        base_paths = self.team_links[team]
        base_path_main = base_paths["main"]
        base_path_invoice = base_paths["invoice"]

        DB_DATA_PATH = rf"{base_path_main}\Machine\Inventory_management_{team}.db"
        IMAGES_FOLDER_PATH = rf"{base_path_main}\Other\inventory_management_images_{team}"
        INVOICE_FOLDER_PATH = base_path_invoice

        self.db_path = DB_DATA_PATH
        self.link_invoice = base_path_invoice

    def setupUI(self):
        self.setup_login()

    def setup_login(self):
        self.hide_tabs_except_login()
        self.login_login_button.clicked.connect(self.dang_nhap_login)
        self.change_changing_button.clicked.connect(self.change_password_login)
        # Thêm sự kiện cho các QLineEdit để tự động hoàn thành
        self.login_msnv_lineedit.installEventFilter(self)
        self.login_password_lineedit.installEventFilter(self)

    def setupUI_in(self):
        self.db_handler.cache.pop(TABLE_INPUT, None)
        self.load_data_to_tablewidget(self.db_handler.read_data(
            TABLE_INPUT), self.input_data_tablewidget)
        self.reset_buttons_input()
        self.setup_connections_input()
        self.input_data_tablewidget.selectionModel(
        ).selectionChanged.connect(self.on_row_selected)
        self.selected_image_path_input = DEFAULT_IMAGE_PATH
        self.setup_autocomplete_on_input(
            TABLE_INPUT, "component_id", self.input_component_id_lineedit)
        self.setup_autocomplete_on_input(
            TABLE_INPUT, "component_name", self.input_component_name_lineedit)
        self.input_check_id_auto_checkBox.stateChanged.connect(
            self.input_component_id_lineedit_load_auto)
        self.input_check_id_info_checkBox.stateChanged.connect(
            self.check_input_component_id)
        self.input_filter_component_id_checkBox.stateChanged.connect(
            self.filter_component_id_input)
        self.input_images_label.enterEvent = self.show_zoom_image
        self.input_images_label.leaveEvent = self.hide_zoom_image
        self.input_zoom_inc_button.clicked.connect(self.increase_zoom)
        self.input_zoom_dec_button.clicked.connect(self.decrease_zoom)

        # Tải dữ liệu cho các MultiSelectDropdown và QComboBox
        combo_data = self.db_handler.load_combo_box_data(TABLE_KEY_ALL)

        # Khởi tạo MultiSelectDropdown cho model, material, process, groups
        self.model_selector = MultiSelectDropdown(
            self, combo_data['model'], "input_model")
        self.input_model_widget.layout().addWidget(self.model_selector)

        self.material_selector = MultiSelectDropdown(
            self, combo_data['material'], "input_material")
        self.input_material_widget.layout().addWidget(self.material_selector)

        self.process_selector = MultiSelectDropdown(
            self, combo_data['process'], "input_process")
        self.input_process_widget.layout().addWidget(self.process_selector)

        self.groups_selector = MultiSelectDropdown(
            self, combo_data['groups'], "input_groups")
        self.input_groups_widget.layout().addWidget(self.groups_selector)

        # Tải dữ liệu cho QComboBox
        self.input_storage_location_combobox.clear()
        self.input_storage_location_combobox.addItems(
            combo_data['storage_location'])
        self.input_status_combobox.clear()
        self.input_status_combobox.addItems(combo_data['status'])
        self.input_unit_combobox.clear()
        self.input_unit_combobox.addItems(combo_data['unit'])

        self.reset_qlineedit_input()  # Gọi sau khi khởi tạo tất cả selector và combobox

        # Đặt vị trí của zoom labels
        input_label_rect = self.input_images_label.geometry()
        self.images_zoom_label.setGeometry(
            input_label_rect.right() - 50,
            input_label_rect.top() + 200,
            self.IMAGE_LABEL_SIZE_ZOOM[0],
            self.IMAGE_LABEL_SIZE_ZOOM[1]
        )

        # Gán sự kiện cho các nút Zoom
        self.input_images_label.enterEvent = self.show_zoom_image
        self.output_images_label.enterEvent = self.show_zoom_image
        self.inventory_images_label.enterEvent = self.show_zoom_image

        self.input_zoom_inc_button.enterEvent = self.show_zoom_image
        self.input_zoom_dec_button.enterEvent = self.show_zoom_image
        self.output_zoom_inc_button.enterEvent = self.show_zoom_image
        self.output_zoom_dec_button.enterEvent = self.show_zoom_image
        self.inventory_zoom_inc_button.enterEvent = self.show_zoom_image
        self.inventory_zoom_dec_button.enterEvent = self.show_zoom_image

        self.input_images_label.leaveEvent = self.hide_zoom_image
        self.output_images_label.leaveEvent = self.hide_zoom_image
        self.inventory_images_label.leaveEvent = self.hide_zoom_image

        self.input_zoom_inc_button.leaveEvent = self.hide_zoom_image
        self.input_zoom_dec_button.leaveEvent = self.hide_zoom_image
        self.output_zoom_inc_button.leaveEvent = self.hide_zoom_image
        self.output_zoom_dec_button.leaveEvent = self.hide_zoom_image
        self.inventory_zoom_inc_button.leaveEvent = self.hide_zoom_image
        self.inventory_zoom_dec_button.leaveEvent = self.hide_zoom_image

    def setupUI_out(self):
        self.db_handler.cache.pop(TABLE_OUTPUT, None)
        self.load_data_to_tablewidget(self.db_handler.read_data(
            TABLE_OUTPUT), self.output_data_tablewidget)
        self.reset_buttons_output()
        self.output_data_tablewidget.selectionModel(
        ).selectionChanged.connect(self.on_row_selected_output)
        self.selected_image_path_output = DEFAULT_IMAGE_PATH
        self.setup_autocomplete_on_input(
            TABLE_INPUT, "component_id", self.output_component_id_lineedit)
        self.output_check_id_auto_checkBox.stateChanged.connect(
            self.calculate_inventory)
        self.output_quantity_lineedit.textChanged.connect(
            self.check_output_quantity)
        self.output_new_button.clicked.connect(self.add_new_item_output)
        self.output_delete_button.clicked.connect(
            self.delete_selected_item_output)
        self.output_zoom_inc_button.clicked.connect(self.increase_zoom)
        self.output_zoom_dec_button.clicked.connect(self.decrease_zoom)

        # Thêm kết nối cho nút search
        self.output_search_button.clicked.connect(
            self.search_output_data)  # Kết nối nút với hàm tìm kiếm
        self.output_export_button.clicked.connect(self.export_to_excel_output)

    def search_output_data(self):
        """Lọc dữ liệu xuất kho dựa trên component_id khi nhấn nút Search."""
        search_component_id = self.output_component_id_lineedit.text().strip().upper()
        search_note = self.output_note_textedit.toPlainText().strip()

        # Nếu chuỗi tìm kiếm rỗng hoặc quá ngắn, hiển thị toàn bộ dữ liệu
        if not search_component_id or len(search_component_id) < 1:
            self.load_data_to_tablewidget(self.db_handler.read_data(
                TABLE_OUTPUT), self.output_data_tablewidget)
            return

        # Lấy dữ liệu từ bảng output_inventory
        self.db_handler.cache.pop(TABLE_OUTPUT, None)
        df_output = self.db_handler.read_data(TABLE_OUTPUT)

        if df_output.empty:
            print(f"[INFO] Bảng {TABLE_OUTPUT} không có dữ liệu.")
            self.load_data_to_tablewidget(pd.DataFrame(
                columns=df_output.columns), self.output_data_tablewidget)
            return

        conditions = []
        if len(search_component_id) > 5 and self.output_search_component_id_checkBox.isChecked():
            conditions.append(df_output["component_id"].str.contains(
                search_component_id, case=False, na=False))
        else:
            if self.output_search_note_checkBox.isChecked():
                conditions.append(df_output["note"].str.contains(
                    search_note, case=False, na=False))

        if conditions:
            final_condition = conditions[0]
            for condition in conditions[1:]:
                final_condition &= condition
            df_filtered = df_output.loc[final_condition]
            df_filtered = df_filtered.reset_index(drop=True)
        else:
            df_filtered = df_output

        df_filtered.sort_values(by="date_time", ascending=False, inplace=True)
        df_filtered = df_filtered.reset_index(drop=True)

        # Hiển thị dữ liệu lên bảng
        self.load_data_to_tablewidget(
            df_filtered, self.output_data_tablewidget)
        self.on_row_selected_output()

    def setupUI_inventory(self):
        """Initialize UI components for Inventory tab."""
        # Clear cache and set up initial state
        self.db_handler.cache.pop(TABLE_OUTPUT, None)
        self.inventory_data_tablewidget.selectionModel(
        ).selectionChanged.connect(self.on_row_selected_inventory)
        self.selected_image_path_inventory = DEFAULT_IMAGE_PATH
        self.inventory_filter_component_id_checkBox.stateChanged.connect(
            self.search_items_inventory)
        self.inventory_search_button.clicked.connect(
            self.search_items_inventory)
        self.inventory_export_button.clicked.connect(
            self.export_to_excel_inventory)
        self.inventory_zoom_inc_button.clicked.connect(self.increase_zoom)
        self.inventory_zoom_dec_button.clicked.connect(self.decrease_zoom)

        # Load combo box data
        combo_data = self.db_handler.load_combo_box_data(TABLE_KEY_ALL)

        # Initialize MultiSelectDropdown for model, material, process, groups
        self.inventory_model_selector = MultiSelectDropdown(
            self, combo_data['model'], "inventory_model")
        self.inventory_model_widget.setLayout(QHBoxLayout())
        self.inventory_model_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.inventory_model_widget.layout().addWidget(self.inventory_model_selector)

        self.inventory_material_selector = MultiSelectDropdown(
            self, combo_data['material'], "inventory_material")
        self.inventory_material_widget.setLayout(QHBoxLayout())
        self.inventory_material_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.inventory_material_widget.layout().addWidget(
            self.inventory_material_selector)

        self.inventory_process_selector = MultiSelectDropdown(
            self, combo_data['process'], "inventory_process")
        self.inventory_process_widget.setLayout(QHBoxLayout())
        self.inventory_process_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.inventory_process_widget.layout().addWidget(self.inventory_process_selector)

        self.inventory_groups_selector = MultiSelectDropdown(
            self, combo_data['groups'], "inventory_groups")
        self.inventory_groups_widget.setLayout(QHBoxLayout())
        self.inventory_groups_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.inventory_groups_widget.layout().addWidget(self.inventory_groups_selector)

        # Load data for other QComboBox
        self.inventory_storage_location_combobox.clear()
        self.inventory_storage_location_combobox.addItems(
            combo_data['storage_location'])
        self.inventory_status_combobox.clear()
        self.inventory_status_combobox.addItems(combo_data['status'])
        self.inventory_unit_combobox.clear()
        self.inventory_unit_combobox.addItems(combo_data['unit'])

        # Set zoom label position
        inventory_label_rect = self.inventory_images_label.geometry()
        self.images_zoom_label.setGeometry(
            inventory_label_rect.right() - 50,
            inventory_label_rect.top() + 200,
            self.IMAGE_LABEL_SIZE_ZOOM[0],
            self.IMAGE_LABEL_SIZE_ZOOM[1]
        )

        # Assign zoom events
        self.inventory_images_label.enterEvent = self.show_zoom_image
        self.inventory_images_label.leaveEvent = self.hide_zoom_image
        self.inventory_zoom_inc_button.enterEvent = self.show_zoom_image
        self.inventory_zoom_dec_button.enterEvent = self.show_zoom_image
        self.inventory_zoom_inc_button.leaveEvent = self.hide_zoom_image
        self.inventory_zoom_dec_button.leaveEvent = self.hide_zoom_image

        # Load initial data
        self.search_items_inventory()

    def setupUI_layout(self):
        df_layout = self.db_handler.read_data(
            TABLE_LAYOUT).drop(columns=['created_at'])
        warehouse = {}
        for _, row in df_layout.iterrows():  # Lặp qua các hàng của DataFrame
            row_number = row['row_number']
            shelf_level = row['shelf_level']
            box_number = row['box_number']
            storage_location = row['storage_location']
            warehouse.setdefault(row_number, {}).setdefault(
                shelf_level, {})[box_number] = storage_location

        self.label_cache = {}
        for row_number in range(1, 7):
            group_box = QGroupBox(f"Dãy {row_number}")
            group_layout = QHBoxLayout()
            for shelf_level in range(1, 4):
                vbox_layout = QVBoxLayout()
                for box_number in range(1, 9):
                    label_name = f"row{row_number}_shelf{shelf_level}_box{box_number}"
                    if label_name not in self.label_cache:
                        label = QLabel()
                        label.setFixedSize(50, 50)
                        label.setAlignment(Qt.AlignCenter)
                        label.setStyleSheet(
                            "border: 1px solid black; background-color: #f0f0f0;")
                        label.setObjectName(label_name)
                        self.label_cache[label_name] = label
                    label = self.label_cache[label_name]
                    storage = warehouse.get(row_number, {}).get(
                        shelf_level, {}).get(box_number, "Empty")
                    label.setText(storage)
                    vbox_layout.addWidget(label)
                group_layout.addLayout(vbox_layout)
            group_box.setLayout(group_layout)
            self.gridLayout_boxs.addWidget(group_box, 0, row_number - 1)

        self.layout_search_button.clicked.connect(self.on_search_layout)

    def setupUI_adduser(self):
        self.adduser_them_button.clicked.connect(self.them_user_login)
        self.tabadduser_level_combobox.addItems(["1", "2", "3", "4", "5"])
        self.tabadduser_team_combobox.addItems(["SMT", "FOL", "TEST", "EOL"])

    def setup_connections_input(self):
        checkbox_mapping = {
            self.input_search_storage_location_checkBox: self.reset_qlineedit_input,
            self.input_search_component_id_checkBox: self.reset_qlineedit_input,
            self.input_search_component_name_checkBox: self.reset_qlineedit_input,
            self.input_search_size_checkBox: self.reset_qlineedit_input,
            self.input_search_material_checkBox: self.reset_qlineedit_input,
            self.input_search_groups_checkBox: self.reset_qlineedit_input,
            self.input_search_model_checkBox: self.reset_qlineedit_input,
            self.input_search_process_checkBox: self.reset_qlineedit_input,
            self.input_search_status_checkBox: self.reset_qlineedit_input,
            self.input_search_note_checkBox: self.reset_qlineedit_input,
            self.input_search_invoice_checkBox: self.reset_qlineedit_input,
            self.input_search_desinvoice_checkBox: self.reset_qlineedit_input,
        }
        for checkbox, handler in checkbox_mapping.items():
            checkbox.stateChanged.connect(handler)
        self.input_images_label.mouseDoubleClickEvent = self.select_image
        self.input_new_button.clicked.connect(self.add_new_item_input)
        self.input_edit_button.clicked.connect(self.edit_selected_item)
        self.input_delete_button.clicked.connect(self.delete_selected_item)
        self.input_search_button.clicked.connect(self.search_items)
        self.input_export_button.clicked.connect(
            self.export_to_excel_input)
        self.input_down_button.clicked.connect(
            self.download_image_input)
        self.input_open_invoice_button.clicked.connect(
            self.open_file_invoice_input)
        # Kết nối sự kiện
        self.input_paste_button.clicked.connect(self.insert_clipboard_text)

    # Input Section
    def input_component_id_lineedit_load_auto(self):
        # B1: Lấy mã prefix (suffix) từ combobox, ví dụ "Vendor VE02" -> "VE02"
        full_text = self.input_storage_location_combobox.currentText()
        suffix = full_text.strip().split()[-1]

        # B2: Đọc tất cả component_id từ DB
        df = self.db_handler.read_data(TABLE_INPUT, ["component_id"])

        # B3: Lọc các component_id bắt đầu bằng suffix
        df_filtered = df[df['component_id'].str.startswith(suffix, na=False)]

        # B4: Lấy 3 ký tự cuối, chuyển sang số nguyên
        ids = (
            df_filtered['component_id']
            .str[-3:]                         # lấy 3 ký tự cuối
            .dropna()
            .str.extract(r'(\d{3})')[0]       # đảm bảo chỉ lấy đúng 3 chữ số
            .dropna()
            .astype(int)                     # chuyển sang số nguyên
        )

        # B5: Nếu không có mã nào -> bắt đầu từ 001
        if ids.empty:
            new_id = f"{suffix}001"
        else:
            new_id = f"{suffix}{str(ids.max() + 1).zfill(3)}"

        # B6: Gán vào lineedit
        self.input_component_id_lineedit.setText(new_id)

    def check_input_component_id(self):
        self.input_component_id_lineedit.setText(
            self.input_component_id_lineedit.text().strip().upper())
        component_id = self.input_component_id_lineedit.text()
        df = self.db_handler.read_data(TABLE_INPUT)
        df = df[df['component_id'] == component_id]
        if not df.empty:
            data = df.iloc[0]
            self.input_storage_location_combobox.setCurrentText(
                str(data['storage_location']))
            self.model_selector.set_selected_items(
                str(data['model']).split(", "))
            self.input_quantity_lineedit.setText(str(data['quantity']))
            self.input_component_name_lineedit.setText(
                str(data['component_name']))
            self.process_selector.set_selected_items(
                str(data['process']).split(", "))
            SizeHandler.to_fields(str(data['size']), self.input_length_lineedit,
                                  self.input_width_lineedit, self.input_height_lineedit)
            self.input_unit_combobox.setCurrentText(str(data['unit']))
            self.groups_selector.set_selected_items(
                str(data['groups']).split(", "))
            self.material_selector.set_selected_items(
                str(data['material']).split(", "))
            self.input_status_combobox.setCurrentText(str(data['status']))
            self.input_invoice_lineedit.setText(str(data['invoice']))
            self.input_desinvoice_lineedit.setText(str(data['desinvoice']))
            self.input_quantity_lineedit.setText(str(data['quantity']))
            self.display_image(os.path.join(
                IMAGES_FOLDER_PATH, f"{component_id}.jpg"), self.input_images_label)
            self.input_note_textedit.setText(str(data['note']))

    def message_yesno(self, title: str, str_info: str):
        return QMessageBox.question(self, title, str_info, QMessageBox.Yes | QMessageBox.No)

    def reset_buttons_input(self):
        self.input_new_button.setText("New")
        self.input_edit_button.setText("Edit")
        self.input_delete_button.setText("Delete")

        if self.user_levels > 1:
            self.input_new_button.setVisible(True)
            self.input_export_button.setVisible(True)
            self.input_down_button.setVisible(True)
            self.input_delete_button.setEnabled(True)
            self.input_new_button.setEnabled(True)
        else:
            # muốn ẩn các button input_new_button,input_export_button,input_down_button
            self.input_new_button.setVisible(False)
            self.input_export_button.setVisible(False)
            self.input_down_button.setVisible(False)

            if self.input_delete_button.text() == "Cancel":
                self.input_delete_button.setEnabled(True)
            else:
                self.input_delete_button.setEnabled(False)

        self.input_edit_button.setEnabled(False)
        self.is_new = False
        self.is_editing = False

    def reset_qlineedit_input(self):
        widgets = {
            self.input_component_id_lineedit: self.input_search_component_id_checkBox,
            self.input_component_name_lineedit: self.input_search_component_name_checkBox,
            self.input_quantity_lineedit: None,
            self.input_length_lineedit: self.input_search_size_checkBox,
            self.input_width_lineedit: self.input_search_size_checkBox,
            self.input_height_lineedit: self.input_search_size_checkBox,
            self.input_storage_location_combobox: self.input_search_storage_location_checkBox,
            self.input_unit_combobox: None,
            self.material_selector: self.input_search_material_checkBox,
            self.groups_selector: self.input_search_groups_checkBox,
            self.model_selector: self.input_search_model_checkBox,
            self.process_selector: self.input_search_process_checkBox,
            self.input_invoice_lineedit: self.input_search_invoice_checkBox,
            self.input_desinvoice_lineedit: self.input_search_desinvoice_checkBox,
            self.input_status_combobox: self.input_search_status_checkBox,
        }
        is_enabled = self.input_delete_button.text() == "Cancel"
        if self.user_levels > 1:
            for widget, checkbox in widgets.items():
                widget.setEnabled(is_enabled or (
                    checkbox.isChecked() if checkbox else False))
        else:
            if self.input_delete_button.text() != "Cancel":
                for widget, checkbox in widgets.items():
                    widget.setEnabled(checkbox.isChecked()
                                      if checkbox else False)

    def reset_buttons_output(self):
        self.output_new_button.setText("New")
        self.output_delete_button.setText("Delete")
        self.output_new_button.setEnabled(True)
        self.output_delete_button.setEnabled(False)
        self.is_new_output = False

    def load_combo_boxes(self):
        combo_data = self.db_handler.load_combo_box_data(TABLE_KEY_ALL)
        for combo, key in [(self.input_model_combobox, 'model'), (self.input_process_combobox, 'process'),
                           (self.input_groups_combobox,
                            'groups'), (self.input_material_combobox, 'material'),
                           (self.input_unit_combobox, 'unit'), (self.input_storage_location_combobox,
                                                                'storage_location'), (self.input_status_combobox, 'status'),
                           (self.inventory_model_combobox,
                            'model'), (self.inventory_process_combobox, 'process'),
                           (self.inventory_groups_combobox,
                            'groups'), (self.inventory_material_combobox, 'material'),
                           (self.inventory_unit_combobox, 'unit'), (
                               self.inventory_storage_location_combobox, 'storage_location'),
                           (self.layout_process_combobox, 'process')]:
            combo.addItems(combo_data[key])
        self.load_layout_combobox()

    def load_data_to_tablewidget(self, df, tablewidget):
        tablewidget.setColumnCount(len(df.columns))
        tablewidget.setHorizontalHeaderLabels(df.columns)
        tablewidget.setRowCount(len(df))
        for row_idx, row_data in df.iterrows():
            for col_idx, cell_data in enumerate(row_data):
                tablewidget.setItem(
                    row_idx, col_idx, QTableWidgetItem(str(cell_data)))
        tablewidget.selectRow(0)

    def on_row_selected(self):
        # print("[DEBUG] Row được chọn:",self.input_data_tablewidget.currentRow())
        self.reset_buttons_input()
        if not self.input_data_tablewidget.selectionModel().hasSelection() or self.is_editing:
            self.input_edit_button.setEnabled(False)
            return
        if not self.is_new:
            self.input_edit_button.setEnabled(True)
        row = self.input_data_tablewidget.currentRow()
        if row == -1:
            return
        self.input_component_id_lineedit.setText(
            self.input_data_tablewidget.item(row, 1).text() or "")
        self.input_component_name_lineedit.setText(
            self.input_data_tablewidget.item(row, 2).text() or "")
        self.process_selector.set_selected_items(
            self.input_data_tablewidget.item(row, 3).text().split(", ") if self.input_data_tablewidget.item(row, 3).text() else [])
        self.model_selector.set_selected_items(
            self.input_data_tablewidget.item(row, 4).text().split(", ") if self.input_data_tablewidget.item(row, 4).text() else [])
        size_str = self.input_data_tablewidget.item(row, 5).text() or ""
        SizeHandler.to_fields(size_str, self.input_length_lineedit,
                              self.input_width_lineedit, self.input_height_lineedit)
        self.input_quantity_lineedit.setText(
            self.input_data_tablewidget.item(row, 6).text() or "")
        self.input_unit_combobox.setCurrentText(
            self.input_data_tablewidget.item(row, 7).text() or "")
        self.groups_selector.set_selected_items(
            self.input_data_tablewidget.item(row, 8).text().split(", ") if self.input_data_tablewidget.item(row, 8).text() else [])
        self.material_selector.set_selected_items(
            self.input_data_tablewidget.item(row, 9).text().split(", ") if self.input_data_tablewidget.item(row, 9).text() else [])
        self.input_storage_location_combobox.setCurrentText(
            self.input_data_tablewidget.item(row, 10).text() or "")
        self.input_invoice_lineedit.setText(
            self.input_data_tablewidget.item(row, 11).text() or "")
        self.input_desinvoice_lineedit.setText(
            self.input_data_tablewidget.item(row, 12).text() or "")
        self.input_status_combobox.setCurrentText(
            self.input_data_tablewidget.item(row, 13).text() or "")
        self.display_image(os.path.join(
            IMAGES_FOLDER_PATH, f"{self.input_data_tablewidget.item(row, 1).text()}.jpg") or "", self.input_images_label)
        self.input_note_textedit.setText(
            self.input_data_tablewidget.item(row, 14).text() or "")
        self.is_editing = False

    def clear_image(self, images_label):
        path_attr = ('selected_image_path_input' if images_label.objectName() == 'input_images_label' else
                     'selected_image_path_output' if images_label.objectName() == 'output_images_label' else
                     'selected_image_path_inventory')
        setattr(self, path_attr, DEFAULT_IMAGE_PATH)
        images_label.setPixmap(QPixmap(DEFAULT_IMAGE_PATH).scaled(
            200, 200, Qt.KeepAspectRatio))

    def display_image(self, image_path: str, images_label):
        if not os.path.isfile(image_path):
            self.clear_image(images_label)
            return
        pixmap = QPixmap(image_path).scaled(*IMAGE_LABEL_SIZE,
                                            Qt.KeepAspectRatio, Qt.SmoothTransformation)
        images_label.setPixmap(pixmap)
        path_attr = ('selected_image_path_input' if images_label.objectName() == 'input_images_label' else
                     'selected_image_path_output' if images_label.objectName() == 'output_images_label' else
                     'selected_image_path_inventory')
        setattr(self, path_attr, image_path)
        self.update_zoom_image()

    def select_image(self, event):
        if self.input_delete_button.text() != "Cancel":
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Chọn Hình ảnh", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_path and any(file_path.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
            self.selected_image_path_input = file_path
            self.input_images_label.setPixmap(
                QPixmap(file_path).scaled(200, 200, Qt.KeepAspectRatio))
        else:
            QMessageBox.warning(
                self, "Lỗi", "Vui lòng chọn tệp hình ảnh hợp lệ!")

    def save_image(self, component_id):
        if not self.selected_image_path_input:
            return None

        target_path = os.path.join(IMAGES_FOLDER_PATH, f"{component_id}.jpg")
        _, ext = os.path.splitext(self.selected_image_path_input)
        ext = ext.lower()

        if os.path.exists(self.selected_image_path_input):
            try:
                if ext == '.jpg' or ext == '.jpeg':
                    # Nếu là file JPG, sao chép để tối ưu
                    if self.selected_image_path_input != target_path:
                        shutil.copy2(
                            self.selected_image_path_input, target_path)
                    return target_path
                else:
                    # Nếu không phải file JPG, mở bằng Pillow và lưu thành JPG
                    img = Image.open(self.selected_image_path_input)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img.save(target_path, "JPEG")
                    print(f"Đã chuyển đổi và lưu thành JPG tại: {target_path}")
                    return target_path

            except FileNotFoundError:
                print(
                    f"Lỗi: Không tìm thấy file ảnh nguồn tại: {self.selected_image_path_input}")
                return None
            except Exception as e:
                print(f"Lỗi trong quá trình xử lý và lưu ảnh: {e}")
                return None
        else:
            print(
                f"Lỗi: Không tìm thấy file ảnh nguồn tại: {self.selected_image_path_input}")
            return None

    def insert_clipboard_text(self):
        results = MyOther.extract_excel_clipboard()
        text = '\n'.join(results)  # nối list thành string, mỗi dòng 1 dòng
        cursor = self.input_note_textedit.textCursor()
        cursor.insertText(text)

    def add_new_item_input(self):
        if self.is_new:
            if not self.input_quantity_lineedit.text():
                QMessageBox.warning(self, "Lỗi", "Vui lòng nhập số lượng.")
                return
            self.reset_buttons_input()
            str_input_component_id_lineedit = self.input_component_id_lineedit.text().strip().upper()
            data = (
                None,
                str_input_component_id_lineedit,
                self.input_component_name_lineedit.text().strip(),
                ", ".join(self.process_selector.get_selected_items()),
                ", ".join(self.model_selector.get_selected_items()),
                SizeHandler.to_string(
                    self.input_length_lineedit, self.input_width_lineedit, self.input_height_lineedit),
                self.input_quantity_lineedit.text(),
                self.input_unit_combobox.currentText(),
                ", ".join(self.groups_selector.get_selected_items()),
                ", ".join(self.material_selector.get_selected_items()),
                self.input_storage_location_combobox.currentText(),
                self.input_invoice_lineedit.text().strip(),
                self.input_desinvoice_lineedit.text().strip(),
                self.input_status_combobox.currentText(),
                self.input_note_textedit.toPlainText(),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                self.name_user_label.text()
            )
            self.save_image(str_input_component_id_lineedit)
            self.input_manager.add_item(data)
            self.search_items()
        else:
            # Clear các trường
            self.input_component_id_lineedit.clear()
            self.input_component_name_lineedit.clear()
            self.input_quantity_lineedit.clear()
            self.input_length_lineedit.clear()
            self.input_width_lineedit.clear()
            self.input_height_lineedit.clear()
            self.input_unit_combobox.setCurrentIndex(-1)
            self.input_invoice_lineedit.clear()
            self.input_desinvoice_lineedit.clear()
            self.input_note_textedit.clear()
            self.input_storage_location_combobox.setCurrentIndex(-1)
            self.input_status_combobox.setCurrentIndex(-1)
            self.model_selector.set_selected_items([])
            self.material_selector.set_selected_items([])
            self.process_selector.set_selected_items([])
            self.groups_selector.set_selected_items([])
            self.display_image(DEFAULT_IMAGE_PATH, self.input_images_label)
            self.is_new = True
            self.input_new_button.setText("Save")
            self.input_delete_button.setText("Cancel")
            self.input_edit_button.setEnabled(False)
        self.reset_qlineedit_input()

    def edit_selected_item(self):
        # print("[DEBUG] Bắt đầu Edit - Row:",self.input_data_tablewidget.currentRow())
        row = self.input_data_tablewidget.currentRow()
        if row == -1:
            return
        unique_id = self.input_data_tablewidget.item(row, 0).text()

        old_component_id = self.input_data_tablewidget.item(row, 1).text()
        current_image_link = os.path.join(
            IMAGES_FOLDER_PATH, f"{old_component_id}.jpg") if old_component_id else ""
        new_component_id = self.input_component_id_lineedit.text()
        selected_image_path = self.selected_image_path_input

        updated_image_link = current_image_link

        if self.is_editing:
            self.reset_buttons_input()
            confirmation = self.message_yesno(
                "Xác nhận chỉnh sửa", f"Bạn có chắc chắn muốn chỉnh sửa dữ liệu với ID {unique_id} không?")
            if confirmation != QMessageBox.Yes:
                return

            # Store original data before updating
            original_data = (
                None,
                self.input_data_tablewidget.item(row, 1).text(),
                self.input_data_tablewidget.item(row, 2).text(),
                self.input_data_tablewidget.item(row, 3).text(),
                self.input_data_tablewidget.item(row, 4).text(),
                self.input_data_tablewidget.item(row, 5).text(),
                self.input_data_tablewidget.item(row, 6).text(),
                self.input_data_tablewidget.item(row, 7).text(),
                self.input_data_tablewidget.item(row, 8).text(),
                self.input_data_tablewidget.item(row, 9).text(),
                self.input_data_tablewidget.item(row, 10).text(),
                self.input_data_tablewidget.item(row, 11).text(),
                self.input_data_tablewidget.item(row, 12).text(),
                self.input_data_tablewidget.item(row, 13).text(),
                self.input_data_tablewidget.item(row, 14).text(),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                self.name_user_label.text(),
                'input edit'
            )
            self.db_handler.insert_data(TABLE_HISTORY_DELETE, original_data)

            # Trường hợp thay đổi ID
            if new_component_id and new_component_id != old_component_id and current_image_link and os.path.exists(current_image_link):
                new_image_name = f"{new_component_id}{os.path.splitext(current_image_link)[1]}"
                new_image_link_after_rename = os.path.join(
                    os.path.dirname(current_image_link), new_image_name)
                try:
                    os.rename(current_image_link, new_image_link_after_rename)
                    print(
                        f"Đã đổi tên hình ảnh từ '{os.path.basename(current_image_link)}' thành '{os.path.basename(new_image_link_after_rename)}'")
                    updated_image_link = new_image_link_after_rename
                except FileNotFoundError:
                    print(
                        f"Lỗi: Không tìm thấy file để đổi tên: {current_image_link}")
                except Exception as e:
                    print(f"Lỗi đổi tên file: {e}")

            # Trường hợp thay đổi hình ảnh
            if selected_image_path and selected_image_path != current_image_link and updated_image_link:
                try:
                    shutil.copy2(selected_image_path, updated_image_link)
                    print(
                        f"Đã ghi đè hình ảnh tại '{updated_image_link}' bằng '{os.path.basename(selected_image_path)}'")
                except FileNotFoundError:
                    print(
                        f"Lỗi: Không tìm thấy file đích để ghi đè: {updated_image_link}")
                except Exception as e:
                    print(f"Lỗi ghi đè hình ảnh: {e}")

            column_values = {
                "component_id": new_component_id,
                "component_name": self.input_component_name_lineedit.text(),
                "process": ", ".join(self.process_selector.get_selected_items()),
                "model": ", ".join(self.model_selector.get_selected_items()),
                "size": SizeHandler.to_string(self.input_length_lineedit, self.input_width_lineedit, self.input_height_lineedit),
                "quantity": self.input_quantity_lineedit.text(),
                "unit": self.input_unit_combobox.currentText(),
                "groups": ", ".join(self.groups_selector.get_selected_items()),
                "material": ", ".join(self.material_selector.get_selected_items()),
                "storage_location": self.input_storage_location_combobox.currentText(),
                "invoice": self.input_invoice_lineedit.text(),
                "desinvoice": self.input_desinvoice_lineedit.text(),
                "status": self.input_status_combobox.currentText(),
                "note": self.input_note_textedit.toPlainText(),
                "date_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "username": self.name_user_label.text()
            }
            self.db_handler.update_data(
                TABLE_INPUT, column_values, f"id = '{unique_id}'")
            self.search_items()
        else:
            # Store current data temporarily when entering edit mode
            self.selected_image_path_input = current_image_link
            self.input_edit_button.setText("Save")
            self.input_delete_button.setText("Cancel")
            self.input_new_button.setEnabled(False)
            self.input_delete_button.setEnabled(True)
            self.is_editing = True
            self.is_new = False

        self.reset_qlineedit_input()

    def delete_selected_item(self):
        # print("[DEBUG] Bắt đầu Delete - Row:",self.input_data_tablewidget.currentRow())
        """Delete selected item from Input tab and log to history."""
        try:
            row = self.input_data_tablewidget.currentRow()
            if row == -1:
                # print("[DEBUG] Không có row nào được chọn")
                return
            if self.input_delete_button.text() == "Cancel":
                if self.message_yesno("Thông báo hủy thao tác", "Bạn có muốn hủy nội dung đang thực hiện không?") != QMessageBox.Yes:
                    return
            else:
                unique_id = self.input_data_tablewidget.item(row, 0).text()
                # Bỏ image_path nếu không sử dụng, hoặc sửa cột nếu cần
                # image_path = self.input_data_tablewidget.item(row, 11).text() or None
                if self.message_yesno("Xác nhận xóa", f"Bạn có chắc chắn muốn xóa dữ liệu với ID {unique_id} không?") != QMessageBox.Yes:
                    self.reset_buttons_input()
                    return
                data = (
                    None,
                    self.input_component_id_lineedit.text(),
                    self.input_component_name_lineedit.text(),
                    ", ".join(self.process_selector.get_selected_items(
                    )) if self.process_selector.get_selected_items() else "",
                    ", ".join(self.model_selector.get_selected_items(
                    )) if self.model_selector.get_selected_items() else "",
                    SizeHandler.to_string(
                        self.input_length_lineedit, self.input_width_lineedit, self.input_height_lineedit),
                    self.input_quantity_lineedit.text(),
                    self.input_unit_combobox.currentText(),
                    ", ".join(self.groups_selector.get_selected_items(
                    )) if self.groups_selector.get_selected_items() else "",
                    ", ".join(self.material_selector.get_selected_items(
                    )) if self.material_selector.get_selected_items() else "",
                    self.input_storage_location_combobox.currentText(),
                    self.input_invoice_lineedit.text(),
                    self.input_desinvoice_lineedit.text(),
                    self.input_status_combobox.currentText(),
                    self.input_note_textedit.toPlainText(),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    self.name_user_label.text(),
                    'input'
                )
                self.db_handler.insert_data(TABLE_HISTORY_DELETE, data)
                self.db_handler.delete_data(TABLE_INPUT, f"id = '{unique_id}'")
                # Sử dụng search_items để giữ các bộ lọc hiện tại
                self.search_items()
            self.reset_buttons_input()
            self.reset_qlineedit_input()
        except Exception as e:
            print(f"Error in delete_selected_item: {str(e)}")

    def search_items(self):
        search_storage_locations = [self.input_storage_location_combobox.currentText(
        )] if self.input_storage_location_combobox.currentText() else []
        search_component_id = self.input_component_id_lineedit.text().strip().upper()
        search_component_name = self.input_component_name_lineedit.text()
        length_value = self.input_length_lineedit.text().strip()
        width_value = self.input_width_lineedit.text().strip()
        height_value = self.input_height_lineedit.text().strip()
        search_materials = self.material_selector.get_selected_items()
        search_groups = self.groups_selector.get_selected_items()
        search_models = self.model_selector.get_selected_items()
        search_processes = self.process_selector.get_selected_items()
        search_status = [self.input_status_combobox.currentText(
        )] if self.input_status_combobox.currentText() else []
        search_note = self.input_note_textedit.toPlainText()
        search_invoice = self.input_invoice_lineedit.text()
        search_desinvoice = self.input_desinvoice_lineedit.text()

        self.db_handler.cache.pop(TABLE_INPUT, None)
        df_search = self.db_handler.read_data(TABLE_INPUT)

        conditions = []
        if len(search_component_id) == 6 and self.input_search_component_id_checkBox.isChecked():
            conditions.append(df_search["component_id"].str.contains(
                search_component_id, case=False, na=False))
        else:
            if self.input_search_storage_location_checkBox.isChecked() and search_storage_locations:
                conditions.append(df_search["storage_location"].str.contains(
                    '|'.join(search_storage_locations), case=False, na=False))
            if self.input_search_component_id_checkBox.isChecked():
                conditions.append(df_search["component_id"].str.contains(
                    search_component_id, case=False, na=False))
            if self.input_search_component_name_checkBox.isChecked():
                conditions.append(df_search["component_name"].str.contains(
                    search_component_name, case=False, na=False))
            if self.input_search_size_checkBox.isChecked():
                length_val = length_value if length_value else '?'
                width_val = width_value if width_value else '?'
                height_val = height_value if height_value else '?'
                regex = SizeHandler.build_size_regex(
                    length_val, width_val, height_val)
                conditions.append(df_search['size'].str.match(regex, na=False))
            if self.input_search_material_checkBox.isChecked() and search_materials:
                conditions.append(df_search["material"].str.contains(
                    '|'.join(search_materials), case=False, na=False))
            if self.input_search_groups_checkBox.isChecked() and search_groups:
                conditions.append(df_search["groups"].str.contains(
                    '|'.join(search_groups), case=False, na=False))
            if self.input_search_model_checkBox.isChecked() and search_models:
                conditions.append(df_search["model"].str.contains(
                    '|'.join(search_models), case=False, na=False))
            if self.input_search_process_checkBox.isChecked() and search_processes:
                conditions.append(df_search["process"].str.contains(
                    '|'.join(search_processes), case=False, na=False))
            if self.input_search_status_checkBox.isChecked() and search_status:
                conditions.append(df_search["status"].isin(search_status))
            if self.input_search_note_checkBox.isChecked():
                mode = self.input_note_fillter_combobox.currentText()
                if mode == 'Does not contains':
                    conditions.append(
                        ~df_search['note'].str.contains(search_note, case=False, na=False))
                elif mode == 'Is empty':
                    conditions.append(df_search['note'].str.strip() == '')
                elif mode == 'Is not empty':
                    conditions.append(df_search['note'].str.strip() != '')
                else:
                    conditions.append(
                        df_search['note'].str.contains(search_note, case=False, na=False))
            if self.input_search_invoice_checkBox.isChecked():
                conditions.append(df_search["invoice"].str.contains(
                    search_invoice, case=False, na=False))
            if self.input_search_desinvoice_checkBox.isChecked():
                conditions.append(df_search["desinvoice"].str.contains(
                    search_desinvoice, case=False, na=False))

        if conditions:
            final_condition = conditions[0]
            for condition in conditions[1:]:
                final_condition &= condition
            df_filtered = df_search.loc[final_condition]
            df_filtered = df_filtered.reset_index(drop=True)
        else:
            df_filtered = df_search

        sort_column = "component_id" if self.input_filter_component_id_checkBox.isChecked(
        ) else "date_time"
        df_filtered.sort_values(by=sort_column, ascending=False, inplace=True)
        df_filtered = df_filtered.reset_index(drop=True)

        self.load_data_to_tablewidget(df_filtered, self.input_data_tablewidget)
        self.on_row_selected()

    def export_to_excel_input(self):
        self.export_tablewidget_to_excel(
            self.input_data_tablewidget, 'Du lieu nhap kho')

    def download_image_input(self):
        self.download_image_from_tablewidget(self.input_data_tablewidget)

    def open_file_invoice_input(self):
        # Bước 1: Lấy dữ liệu từ clipboard
        clipboard = QGuiApplication.clipboard()
        copied_text = clipboard.text().strip()

        if not copied_text:
            QMessageBox.warning(
                self, "Lỗi", "Không có dữ liệu trong clipboard!")
            return

        # Bước 2: Xử lý chuỗi bằng CAT_CHUOI_INVOICE
        invoice_name = cat_chuoi_invoice(copied_text)

        # Bước 3: Tạo đường dẫn file
        file_path = os.path.join(self.link_invoice, f"{invoice_name}.xlsx")
        print("Đường dẫn thử:", file_path)

        # Bước 4: Kiểm tra tồn tại
        if not os.path.exists(file_path):
            # Hiển thị hộp thoại nhập nếu file từ clipboard không tồn tại
            text, ok = QInputDialog.getText(self, "Nhập tên hóa đơn",
                                            f"Không tìm thấy file: {invoice_name}.xlsx\nVui lòng nhập tên khác:")
            if ok and text.strip():
                invoice_name = cat_chuoi_invoice(text.strip())
                file_path = os.path.join(
                    self.link_invoice, f"{invoice_name}.xlsx")
            else:
                return  # Người dùng hủy

        # Bước 5: Mở file nếu tồn tại
        if os.path.exists(file_path):
            # self.load_invoice_data(file_path)
            subprocess.Popen(['start', '', file_path], shell=True)
        else:
            QMessageBox.warning(self, "Không tìm thấy",
                                f"Không tìm thấy file invoice chi tiết: {invoice_name}")

    def update_zoom_image(self):
        try:
            """Cập nhật nội dung hình ảnh cho images_zoom_label."""
            image_path = (self.selected_image_path_input if self.tabWidget_main.currentIndex() == 1 else
                          self.selected_image_path_output if self.tabWidget_main.currentIndex() == 2 else
                          self.selected_image_path_inventory if self.tabWidget_main.currentIndex() == 5 else None)
            if image_path and os.path.isfile(image_path):
                self.images_zoom_label.setPixmap(QPixmap(image_path).scaled(
                    *self.IMAGE_LABEL_SIZE_ZOOM, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.images_zoom_label.clear()
        except Exception as e:
            print(f"[ERROR] {e}")

    def show_zoom_image(self, event):
        """Hiển thị hình ảnh zoom ở giữa màn hình."""
        self.update_zoom_image()
        self.center_zoom_label()  # Đặt ở giữa màn hình
        self.images_zoom_label.show()

    def hide_zoom_image(self, event):
        self.images_zoom_label.hide()

    def filter_component_id_input(self, state):
        self.db_handler.cache.pop(TABLE_INPUT, None)
        df = self.db_handler.read_data(TABLE_INPUT)
        if self.input_search_storage_location_checkBox.isChecked():
            df = df[df["storage_location"] ==
                    self.input_storage_location_combobox.currentText()]
        df.sort_values(
            by="component_id", ascending=not self.input_filter_component_id_checkBox.isChecked(), inplace=True)
        self.load_data_to_tablewidget(df, self.input_data_tablewidget)
        self.on_row_selected()

    # Output Section
    def calculate_inventory(self):
        component_id = self.output_component_id_lineedit.text().strip().upper()
        self.db_handler.cache.pop(TABLE_INPUT, None)
        df_in = self.db_handler.read_data(TABLE_INPUT)
        df_in = df_in[df_in['component_id'] == component_id]
        total_in = df_in.groupby('component_id')[
            'quantity'].sum().iloc[0] if not df_in.empty else 0
        df_out = self.db_handler.read_data(TABLE_OUTPUT)
        df_out = df_out[df_out['component_id'] == component_id]
        total_out = df_out['quantity'].sum() if not df_out.empty else 0
        inventory = total_in - total_out
        if not df_in.empty:
            data = df_in.iloc[0]
            self.output_inventory_label.setText(str(inventory))
            self.output_component_name_label.setText(
                str(data['component_name']))
            self.output_process_label.setText(str(data['process']))
            self.output_model_label.setText(str(data['model']))
            self.output_size_label.setText(str(data['size']))
            self.output_unit_label.setText(str(data['unit']))
            self.output_groups_label.setText(str(data['groups']))
            self.output_material_label.setText(str(data['material']))
            self.output_storage_location_label.setText(
                str(data['storage_location']))
            self.output_invoice_lineedit.setText(str(data['invoice']))
            self.output_desinvoice_lineedit.setText(str(data['desinvoice']))
            self.output_status_label.setText(str(data['status']))
            self.display_image(os.path.join(
                IMAGES_FOLDER_PATH, f"{component_id}.jpg"), self.output_images_label)
            self.output_note_textedit.setText(str(data['note']))

    def check_output_quantity(self):
        if self.output_new_button.text() != "Save":
            return
        try:
            entered_value = float(self.output_quantity_lineedit.text())
            inventory_value = float(self.output_inventory_label.text())
            self.output_quantity_lineedit.setStyleSheet(
                "background-color: #ff0000;" if entered_value > inventory_value else "background-color: #f0f0f0;")
        except ValueError:
            self.output_quantity_lineedit.setStyleSheet(
                "background-color: #f0f0f0;")

    def add_new_item_output(self):
        if self.is_new_output:
            if not self.output_quantity_lineedit.text():
                QMessageBox.warning(self, "Lỗi", "Vui lòng nhập số lượng.")
                return
            self.reset_buttons_output()
            data = (None, self.output_component_id_lineedit.text().strip().upper(),
                    self.output_component_name_label.text(),
                    self.output_process_label.text(),
                    self.output_model_label.text(),
                    self.output_size_label.text(),
                    self.output_quantity_lineedit.text(),
                    self.output_unit_label.text(),
                    self.output_groups_label.text(),
                    self.output_material_label.text(),
                    self.output_storage_location_label.text(),
                    self.output_invoice_lineedit.text(),
                    self.output_desinvoice_lineedit.text(),
                    self.output_status_label.text(),
                    self.output_note_textedit.toPlainText(),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    self.name_user_label.text()
                    )
            self.db_handler.insert_data(TABLE_OUTPUT, data)
            self.search_output_data()
        else:
            self.output_component_id_lineedit.setText('')
            self.output_storage_location_label.setText('')
            self.output_model_label.setText('')
            self.output_quantity_lineedit.setText('')
            self.output_unit_label.setText('')
            self.output_size_label.setText('')
            self.output_material_label.setText('')
            self.output_component_name_label.setText('')
            self.output_process_label.setText('')
            self.output_groups_label.setText('')
            self.output_invoice_lineedit.setText('')
            self.output_desinvoice_lineedit.setText('')
            self.output_status_label.setText('')
            self.clear_image(self.output_images_label)
            self.output_note_textedit.setText('')

            self.output_new_button.setText("Save")
            self.output_delete_button.setText("Cancel")
            self.output_delete_button.setEnabled(True)
            self.is_new_output = True

    def delete_selected_item_output(self):
        row = self.output_data_tablewidget.currentRow()
        if row == -1:
            return
        if self.output_delete_button.text() == "Cancel":
            if self.message_yesno("Thông báo hủy thao tác", "Bạn có muốn hủy nội dung đang thực hiện không?") != QMessageBox.Yes:
                return
        else:
            ids = self.output_data_tablewidget.item(row, 0).text()
            unique_id = self.output_data_tablewidget.item(row, 1).text()
            if self.message_yesno("Xác nhận xóa", f"Bạn có chắc chắn muốn xóa dữ liệu với ID {unique_id} không?") != QMessageBox.Yes:
                self.reset_buttons_output()
                return
            data = (None,
                    unique_id,
                    self.output_component_name_label.text(),
                    self.output_process_label.text(),
                    self.output_model_label.text(),
                    self.output_size_label.text(),
                    self.output_quantity_lineedit.text(),
                    self.output_unit_label.text(),
                    self.output_groups_label.text(),
                    self.output_material_label.text(),
                    self.output_storage_location_label.text(),
                    self.output_invoice_lineedit.text(),          # Thêm invoice
                    self.output_desinvoice_lineedit.text(),       # Thêm desinvoice
                    self.output_status_label.text(),
                    self.output_note_textedit.toPlainText(),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    self.name_user_label.text(),
                    'output')
            self.db_handler.insert_data(TABLE_HISTORY_DELETE, data)
            self.db_handler.delete_data(TABLE_OUTPUT, f"id = '{ids}'")
            self.load_data_to_tablewidget(self.db_handler.read_data(
                TABLE_OUTPUT), self.output_data_tablewidget)
        self.reset_buttons_output()

    def on_row_selected_output(self):
        if not self.output_data_tablewidget.selectionModel().hasSelection():
            self.output_delete_button.setEnabled(False)
            return
        self.output_delete_button.setEnabled(True)
        row = self.output_data_tablewidget.currentRow()
        if row == -1:
            return
        self.output_component_id_lineedit.setText(
            self.output_data_tablewidget.item(row, 1).text() or "")
        self.output_component_name_label.setText(
            self.output_data_tablewidget.item(row, 2).text() or "")
        self.output_process_label.setText(
            self.output_data_tablewidget.item(row, 3).text() or "")
        self.output_model_label.setText(
            self.output_data_tablewidget.item(row, 4).text() or "")
        self.output_size_label.setText(
            self.output_data_tablewidget.item(row, 5).text() or "")
        self.output_quantity_lineedit.setText(
            self.output_data_tablewidget.item(row, 6).text() or "")
        self.output_unit_label.setText(
            self.output_data_tablewidget.item(row, 7).text() or "")
        self.output_groups_label.setText(
            self.output_data_tablewidget.item(row, 8).text() or "")
        self.output_material_label.setText(
            self.output_data_tablewidget.item(row, 9).text() or "")
        self.output_storage_location_label.setText(
            self.output_data_tablewidget.item(row, 10).text() or "")
        self.output_invoice_lineedit.setText(
            self.output_data_tablewidget.item(row, 11).text() or "")
        self.output_desinvoice_lineedit.setText(
            self.output_data_tablewidget.item(row, 12).text() or "")
        self.output_status_label.setText(
            self.output_data_tablewidget.item(row, 13).text() or "")
        self.display_image(os.path.join(
            IMAGES_FOLDER_PATH, f"{self.output_data_tablewidget.item(row, 1).text()}.jpg") or "", self.output_images_label)
        self.output_note_textedit.setText(
            self.output_data_tablewidget.item(row, 14).text() or "")
        self.is_editing = False  # Thêm mới

    def export_to_excel_output(self):
        self.export_tablewidget_to_excel(
            self.output_data_tablewidget, 'Du lieu xuat kho')

    def search_items_inventory(self):
        """Search and display inventory data based on filters."""
        try:
            search_storage_location = self.inventory_storage_location_combobox.currentText()
            search_component_id = self.inventory_component_id_lineedit.text().strip().upper()
            search_component_name = self.inventory_component_name_lineedit.text()
            search_size = SizeHandler.to_string(
                self.inventory_length_lineedit, self.inventory_width_lineedit, self.inventory_height_lineedit)
            search_material = self.inventory_material_selector.get_selected_items()
            search_groups = self.inventory_groups_selector.get_selected_items()
            search_model = self.inventory_model_selector.get_selected_items()
            search_process = self.inventory_process_selector.get_selected_items()
            search_note = self.inventory_note_textedit.toPlainText()
            search_invoice = self.inventory_invoice_lineedit.text()
            search_desinvoice = self.inventory_desinvoice_lineedit.text()
            search_status = self.inventory_status_combobox.currentText()

            columns_needed = ['component_id', 'component_name', 'process', 'model', 'size', 'quantity',
                              'unit', 'groups', 'material', 'storage_location', 'invoice', 'desinvoice', 'status', 'note']

            self.db_handler.cache.pop(TABLE_INPUT, None)
            self.db_handler.cache.pop(TABLE_OUTPUT, None)

            df_input = self.db_handler.read_data(
                TABLE_INPUT, columns=columns_needed)
            if df_input.empty:
                print(f"[INFO] Bảng {TABLE_INPUT} không có dữ liệu.")
                self.load_data_to_tablewidget(pd.DataFrame(
                    columns=columns_needed), self.inventory_data_tablewidget)
                return

            # Aggregate input data
            df_input_agg = df_input.groupby('component_id').agg({
                'quantity': 'sum',
                'component_name': 'first',
                'process': 'first',
                'model': 'first',
                'size': 'first',
                'unit': 'first',
                'groups': 'first',
                'material': 'first',
                'storage_location': 'first',
                'invoice': 'first',
                'desinvoice': 'first',
                'status': 'first',
                'note': 'first'
            }).reset_index().rename(columns={'quantity': 'input_quantity'})

            # Aggregate output data
            df_output = self.db_handler.read_data(TABLE_OUTPUT)
            df_output = df_output[['component_id', 'quantity']]
            if df_output.empty:
                df_output_agg = pd.DataFrame(
                    columns=['component_id', 'output_quantity'])
            else:
                df_output_agg = df_output.groupby('component_id')['quantity'].sum(
                ).reset_index().rename(columns={'quantity': 'output_quantity'})

            df_inventory = pd.merge(df_input_agg, df_output_agg, on='component_id', how='left').fillna(
                {'output_quantity': 0})
            df_inventory['quantity'] = df_inventory['input_quantity'] - \
                df_inventory['output_quantity']
            df_inventory['quantity'] = df_inventory['quantity'].astype(int)

            conditions = []

            if len(search_component_id) == 6 and self.inventory_search_component_id_checkBox.isChecked():
                conditions.append(df_inventory["component_id"].str.contains(
                    search_component_id, case=False, na=False))
            else:
                if self.inventory_search_storage_location_checkBox.isChecked() and search_storage_location:
                    conditions.append(df_inventory["storage_location"].str.contains(
                        search_storage_location, case=False, na=False))
                if self.inventory_search_component_id_checkBox.isChecked() and search_component_id:
                    conditions.append(df_inventory["component_id"].str.contains(
                        search_component_id, case=False, na=False))
                if self.inventory_search_component_name_checkBox.isChecked() and search_component_name:
                    conditions.append(df_inventory["component_name"].str.contains(
                        search_component_name, case=False, na=False))
                if self.inventory_search_size_checkBox.isChecked() and search_size:
                    conditions.append(df_inventory["size"].str.contains(
                        search_size, case=False, na=False))
                if self.inventory_search_material_checkBox.isChecked() and search_material:
                    conditions.append(df_inventory["material"].str.contains(
                        '|'.join(search_material), case=False, na=False))
                if self.inventory_search_groups_checkBox.isChecked() and search_groups:
                    conditions.append(df_inventory["groups"].str.contains(
                        '|'.join(search_groups), case=False, na=False))
                if self.inventory_search_model_checkBox.isChecked() and search_model:
                    conditions.append(df_inventory["model"].str.contains(
                        '|'.join(search_model), case=False, na=False))
                if self.inventory_search_process_checkBox.isChecked() and search_process:
                    conditions.append(df_inventory["process"].str.contains(
                        '|'.join(search_process), case=False, na=False))
                if self.inventory_search_note_checkBox.isChecked() and search_note:
                    conditions.append(df_inventory["note"].str.contains(
                        search_note, case=False, na=False))
                if self.inventory_search_invoice_checkBox.isChecked() and search_invoice:
                    conditions.append(df_inventory["invoice"].str.contains(
                        search_invoice, case=False, na=False))
                if self.inventory_search_desinvoice_checkBox.isChecked() and search_desinvoice:
                    conditions.append(df_inventory["desinvoice"].str.contains(
                        search_desinvoice, case=False, na=False))
                if self.inventory_search_status_checkBox.isChecked() and search_status:
                    conditions.append(df_inventory["status"] == search_status)

            if conditions:
                final_condition = conditions[0]
                for condition in conditions[1:]:
                    final_condition &= condition
                df_inventory = df_inventory[final_condition]
                df_inventory = df_inventory.reset_index(drop=True)

            sort_column = "component_id" if self.inventory_filter_component_id_checkBox.isChecked(
            ) else "storage_location"
            df_inventory.sort_values(
                by=sort_column, ascending=False, inplace=True)
            df_inventory = df_inventory.reset_index(drop=True)

            display_columns = ['component_id', 'component_name', 'process', 'model', 'size', 'quantity',
                               'unit', 'groups', 'material', 'storage_location', 'invoice', 'desinvoice', 'status', 'note', 'input_quantity', 'output_quantity']
            df_inventory_display = df_inventory[display_columns]

            self.load_data_to_tablewidget(
                df_inventory_display, self.inventory_data_tablewidget)
            self.on_row_selected_inventory()
        except Exception as e:
            print(f"Error in search_items_inventory: {str(e)}")

    def on_row_selected_inventory(self):
        """Handle row selection in inventory table."""
        try:
            if not self.inventory_data_tablewidget.selectionModel().hasSelection():
                return
            row = self.inventory_data_tablewidget.currentRow()
            if row == -1:
                return
            self.inventory_component_id_lineedit.setText(
                self.inventory_data_tablewidget.item(row, 0).text() or "")
            self.inventory_component_name_lineedit.setText(
                self.inventory_data_tablewidget.item(row, 1).text() or "")
            self.inventory_process_selector.set_selected_items(
                self.inventory_data_tablewidget.item(row, 2).text().split(", ") if self.inventory_data_tablewidget.item(row, 2) and self.inventory_data_tablewidget.item(row, 2).text() else [])
            self.inventory_model_selector.set_selected_items(
                self.inventory_data_tablewidget.item(row, 3).text().split(", ") if self.inventory_data_tablewidget.item(row, 3) and self.inventory_data_tablewidget.item(row, 3).text() else [])
            size_str = self.inventory_data_tablewidget.item(
                row, 4).text() or ""
            SizeHandler.to_fields(size_str, self.inventory_length_lineedit,
                                  self.inventory_width_lineedit, self.inventory_height_lineedit)
            self.inventory_quantity_lineedit.setText(
                self.inventory_data_tablewidget.item(row, 5).text() or "")
            self.inventory_unit_combobox.setCurrentText(
                self.inventory_data_tablewidget.item(row, 6).text() or "")
            self.inventory_groups_selector.set_selected_items(
                self.inventory_data_tablewidget.item(row, 7).text().split(", ") if self.inventory_data_tablewidget.item(row, 7) and self.inventory_data_tablewidget.item(row, 7).text() else [])
            self.inventory_material_selector.set_selected_items(
                self.inventory_data_tablewidget.item(row, 8).text().split(", ") if self.inventory_data_tablewidget.item(row, 8) and self.inventory_data_tablewidget.item(row, 8).text() else [])
            self.inventory_storage_location_combobox.setCurrentText(
                self.inventory_data_tablewidget.item(row, 9).text() or "")
            self.inventory_invoice_lineedit.setText(
                self.inventory_data_tablewidget.item(row, 10).text() or "")
            self.inventory_desinvoice_lineedit.setText(
                self.inventory_data_tablewidget.item(row, 11).text() or "")
            self.inventory_status_combobox.setCurrentText(
                self.inventory_data_tablewidget.item(row, 12).text() or "")
            self.inventory_note_textedit.setText(
                self.inventory_data_tablewidget.item(row, 13).text() or "")
            self.display_image(os.path.join(
                IMAGES_FOLDER_PATH, f"{self.inventory_data_tablewidget.item(row, 0).text()}.jpg") or "", self.inventory_images_label)
        except Exception as e:
            print(f"Error in on_row_selected_inventory: {str(e)}")

    def export_to_excel_inventory(self):
        self.export_tablewidget_to_excel(
            self.inventory_data_tablewidget, 'Du lieu ton kho')

    # Layout Section
    def load_layout_combobox(self):
        storage_locations = sorted(self.db_handler.read_data(
            TABLE_INPUT, ['storage_location'])['storage_location'].drop_duplicates().tolist())
        self.layout_storage_location_combobox.addItems(storage_locations)

    def reset_label_layout(self):
        for row in range(1, 7):
            for shelf in range(1, 4):
                for box in range(1, 9):
                    label = self.label_cache.get(
                        f"row{row}_shelf{shelf}_box{box}")
                    if label:
                        label.setStyleSheet(
                            "border: 1px solid black; background-color: #f0f0f0;")

    def highlight_labels_layout(self, label, highlight=False):
        label.setStyleSheet(
            f"border: 1px solid black; background-color: {'yellow' if highlight else '#f0f0f0'};")

    def search_by_storage_locations_layout(self, search_value):
        for row in range(1, 7):
            for shelf in range(1, 4):
                for box in range(1, 9):
                    label = self.label_cache.get(
                        f"row{row}_shelf{shelf}_box{box}")
                    if label and search_value == label.text():
                        self.highlight_labels_layout(label, True)

    def search_by_process_layout(self, search_value):
        df = self.db_handler.read_data(
            TABLE_INPUT, ['process', 'storage_location'])
        storage_list = df[df['process'] ==
                          search_value]['storage_location'].drop_duplicates().tolist()
        for storage in storage_list:
            for row in range(1, 7):
                for shelf in range(1, 4):
                    for box in range(1, 9):
                        label = self.label_cache.get(
                            f"row{row}_shelf{shelf}_box{box}")
                        if label and storage == label.text() and 'yellow' not in label.styleSheet():
                            self.highlight_labels_layout(label, True)

    def on_search_layout(self):
        self.reset_label_layout()
        if self.layout_search_storage_location_radio.isChecked():
            search_value = self.layout_storage_location_combobox.currentText()
            if search_value:
                self.search_by_storage_locations_layout(search_value)
        elif self.layout_search_process_radio.isChecked():
            search_value = self.layout_process_combobox.currentText()
            if search_value:
                self.search_by_process_layout(search_value)

    # Login Section
    def hide_tabs_except_login(self):
        for i in range(1, 9):
            self.tabWidget_main.setTabVisible(i, False)
        self.login_info_label.setText('')

    def enable_tabs(self, level):
        self.user_levels = level
        tabs = {0: [0],
                1: [1, 6],
                2: [1, 2, 5, 6],
                3: [1, 2, 3, 5, 6],
                5: [1, 2, 3, 5, 6, 7, 8]}.get(level, [])
        for i in tabs:
            self.tabWidget_main.setTabVisible(i, True)

    def dang_nhap_login(self):
        user_manager = UserManager()
        username = self.login_msnv_lineedit.text()
        password = self.login_password_lineedit.text()
        self.login_password_lineedit.setText('')
        success, level, team = user_manager.login(username, password)
        if success:
            self.login_info_label.setText('')
            # Cập nhật đường dẫn dựa trên team
            self.user_levels = level  # user level
            self.update_paths_by_team(team)
            self.db_handler = DatabaseHandler()
            self.db_handler.cache.clear()
            self.input_manager = InputManager(self.db_handler)

            self.enable_tabs(int(level))
            self.name_user_label.setText(username)
            self.change_msnv_label.setText(username)
            self.team_user_label.setText(team)
            self.display_icon_user(username)
            self.tabWidget_main.setTabVisible(0, False)
            self.tabWidget_main.setCurrentIndex(1)
            window.setMinimumSize(800, 600)
            # Tải lại dữ liệu sau khi thay đổi đường dẫn
            self.setupUI_in()
            self.setupUI_out()
            self.setupUI_inventory()
            self.setupUI_layout()
            self.setupUI_adduser()
        else:
            self.login_info_label.setText('Thông tin đăng nhập không đúng!')
        user_manager.close()

    def dang_xuat_login(self, event):
        self.user_levels = 0
        self.enable_tabs(int(self.user_levels))
        self.tabWidget_main.setTabVisible(0, True)
        self.tabWidget_main.setCurrentIndex(0)
        # self.mark_user_offline()
        self.login_msnv_lineedit.setText('')
        self.login_password_lineedit.setText('')
        self.login_info_label.setText('')
        self.name_user_label.setText('Guest')
        self.hide_tabs_except_login()

    def change_password_login(self):
        user_manager = UserManager()
        username = self.change_msnv_label.text()
        user_manager.change_password(username, self.change_password_old_lineedit.text(),
                                     self.change_password_new_lineedit.text(), self.change_password_new2_lineedit.text())
        self.change_password_old_lineedit.setText('')
        self.change_password_new_lineedit.setText('')
        self.change_password_new2_lineedit.setText('')
        user_manager.close()

    def them_user_login(self):
        user_manager = UserManager()
        user_manager.add_user(self.adduser_msnv_lineedit.text(), self.adduser_password_lineedit.text(),
                              int(self.tabadduser_level_combobox.currentText()), self.tabadduser_team_combobox.currentText())
        user_manager.close()

    def display_icon_user(self, id_no):
        image_path = f"{IMAGES_ICON_EMPLOYEE_FOLDER_PATH}\\{id_no}.jpg"
        if not os.path.isfile(image_path):
            image_path = ':/icon/images/icon/User.png'
        self.image_user_label.setPixmap(QPixmap(image_path).scaled(
            QSize(50, 50), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def on_tab_changed(self, index):
        self.update_zoom_image()
        # tab_text = self.tabWidget_main.tabText(index)
        tab_titles = {"LOGIN": "LOGIN", "STOCK IN": "STOCK IN_"+self.team_user_label.text(),
                      "STOCK OUT": "STOCK OUT_"+self.team_user_label.text(), "LAYOUT": "WAREHOUSE LAYOUT_"+self.team_user_label.text(),
                      "OTHER": "OTHER", "STOCK SUMMARY": "STOCK SUMMARY_"+self.team_user_label.text(),
                      "CHANGE PASSWORD": "CHANGE PASSWORD", "ADD USER": "ADD USER", "CHAT": "TRAO ĐỔI THÔNG TIN"}
        self.title_label.setText(tab_titles.get(
            self.tabWidget_main.tabText(index), ""))

    def setup_autocomplete_on_input(self, table_name: str, column_name: str, line_edit: QLineEdit):
        timer = QTimer()
        timer.setSingleShot(True)

        # Đọc dữ liệu một lần
        df = self.db_handler.read_data(table_name, [column_name])
        # Làm sạch: bỏ NaN, strip 2 đầu, loại trùng, sắp xếp
        values = sorted(set(df[column_name].dropna().str.strip().unique()))

        completer = QCompleter(values, line_edit)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        line_edit.setCompleter(completer)

        def refresh_completer():
            text = line_edit.text().strip()
            if not text or not line_edit.isEnabled():
                return

            # Lọc dữ liệu dựa trên text người dùng gõ
            filtered_values = [v for v in values if text.lower() in v.lower()]
            completer.model().setStringList(filtered_values if filtered_values else values)

        line_edit.textChanged.connect(lambda: timer.start(300))
        timer.timeout.connect(refresh_completer)

    def update_image_label_size(self):
        self.images_zoom_label.setFixedSize(*self.IMAGE_LABEL_SIZE_ZOOM)
        # Tính toán vị trí để giữ ở giữa màn hình
        self.center_zoom_label()

    def center_zoom_label(self):
        """Đặt images_zoom_label ở giữa màn hình."""
        # Lấy kích thước của cửa sổ chính
        window_rect = self.geometry()
        window_width = window_rect.width()
        window_height = window_rect.height()

        # Lấy kích thước của images_zoom_label
        zoom_width = self.IMAGE_LABEL_SIZE_ZOOM[0]
        zoom_height = self.IMAGE_LABEL_SIZE_ZOOM[1]

        # Tính toán tọa độ x, y để đặt ở giữa
        x = (window_width - zoom_width) // 2
        y = (window_height - zoom_height) // 2

        # Đặt vị trí mới
        self.images_zoom_label.move(x, y)

    def increase_zoom(self):
        """Tăng kích thước và giữ ở giữa."""
        self.IMAGE_LABEL_SIZE_ZOOM[0] = min(
            self.IMAGE_LABEL_SIZE_ZOOM[0] + 50, MAX_ZOOM[0])
        self.IMAGE_LABEL_SIZE_ZOOM[1] = min(
            self.IMAGE_LABEL_SIZE_ZOOM[1] + 40, MAX_ZOOM[1])
        self.update_image_label_size()  # Cập nhật kích thước và vị trí

    def decrease_zoom(self):
        """Giảm kích thước và giữ ở giữa."""
        self.IMAGE_LABEL_SIZE_ZOOM[0] = max(
            self.IMAGE_LABEL_SIZE_ZOOM[0] - 50, 450)
        self.IMAGE_LABEL_SIZE_ZOOM[1] = max(
            self.IMAGE_LABEL_SIZE_ZOOM[1] - 40, 330)
        self.update_image_label_size()  # Cập nhật kích thước và vị trí

    def eventFilter(self, source, event):
        if event.type() != QEvent.KeyPress:
            return super().eventFilter(source, event)

        current_tab_name = self.tabWidget_main.tabText(
            self.tabWidget_main.currentIndex())
        key = event.key()
        modifiers = event.modifiers()

        # ===== TAB: LOGIN =====
        if current_tab_name == "LOGIN":

            if source in (self.login_msnv_lineedit, self.login_password_lineedit):
                if key in (Qt.Key_Return, Qt.Key_Enter) and modifiers == Qt.NoModifier:
                    # cho hiện message box với string keyboard

                    msnv = self.login_msnv_lineedit.text().strip()
                    pw = self.login_password_lineedit.text().strip()
                    if msnv and pw:
                        self.dang_nhap_login()
                        return True

        return super().eventFilter(source, event)

    def export_tablewidget_to_excel(self, table_widget, namestring='Data export', parent=None):
        namestring = f"{namestring}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        rows = table_widget.rowCount()
        cols = table_widget.columnCount()

        data = []
        headers = []

        # Lấy tiêu đề cột
        for col in range(cols):
            header = table_widget.horizontalHeaderItem(col)
            headers.append(header.text() if header else f"Cột {col+1}")

        # Lấy dữ liệu trong bảng
        for row in range(rows):
            row_data = []
            for col in range(cols):
                item = table_widget.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)

        df = pd.DataFrame(data, columns=headers)

        if df.empty:
            QMessageBox.warning(parent, "Cảnh báo",
                                "Dữ liệu đang trống, không thể xuất.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            parent,
            "Chọn nơi lưu file Excel",
            f"{namestring}.xlsx",
            "Excel Files (*.xlsx)"
        )

        if file_path:
            try:
                df.to_excel(file_path, index=False)
                QMessageBox.information(
                    parent, "Thành công", f"Đã lưu file Excel:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(parent, "Lỗi", f"Lỗi khi lưu file:\n{e}")

    # Hàm chính để copy hình ảnh từ table_widget
    def download_image_from_tablewidget(self, table_widget, parent=None):
        # Thay đổi văn bản nút và vô hiệu hóa nút trong khi copy
        self.input_down_button.setText("Downloading ...")
        self.input_down_button.setEnabled(False)

        # Kiểm tra ổ đĩa D, nếu không tồn tại thì dùng ổ C
        parent_folder = r"D:\lib_inventory"
        if not os.path.exists(r'D:'):
            parent_folder = r"C:\lib_inventory"
        os.makedirs(parent_folder, exist_ok=True)

        # Tạo thư mục con theo timestamp
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        destination_folder = os.path.join(
            parent_folder, f"lib_inventory_{timestamp}")
        os.makedirs(destination_folder, exist_ok=True)

        # Lấy danh sách tên file hình ảnh từ table_widget
        rows = table_widget.rowCount()
        list_image = []
        for row in range(rows):
            item = table_widget.item(row, 1)
            if item:
                name = item.text().strip()
                if name:
                    list_image.append(name)

        # Kiểm tra nếu không có file nào
        if not list_image:
            self.input_down_button.setText("Download Image")
            self.input_down_button.setEnabled(True)
            QMessageBox.warning(parent, "Cảnh báo",
                                "Không có dữ liệu hình ảnh để copy.")
            return

        # Kiểm tra file tồn tại với các đuôi hợp lệ
        extensions = [".jpg", ".jpeg", ".JPG", ".JPEG"]
        source_files = []
        for name in list_image:
            for ext in extensions:
                src = os.path.join(IMAGES_FOLDER_PATH, name + ext)
                if os.path.exists(src):
                    source_files.append(src)
                    break

        # Kiểm tra nếu không tìm thấy file nào
        if not source_files:
            self.input_down_button.setText("Download Image")
            self.input_down_button.setEnabled(True)
            QMessageBox.warning(parent, "Thông báo",
                                "Không tìm thấy file hình ảnh nào.")
            return

        # Tạo luồng để copy file trong nền
        self.copy_worker = CopyWorker(source_files, destination_folder)

        # Hiển thị % tiến độ lên nút
        def on_copy_progress(percent):
            self.input_down_button.setText(f"Copying... {percent}%")

        # Khi hoàn tất
        def on_copy_finished(message, copied):
            self.input_down_button.setText("Download Image")
            self.input_down_button.setEnabled(True)
            if copied > 0:
                QMessageBox.information(parent, "Kết quả", message)
            else:
                QMessageBox.warning(parent, "Kết quả", message)

        # Kết nối tín hiệu
        self.copy_worker.progress.connect(on_copy_progress)
        self.copy_worker.finished.connect(on_copy_finished)

        # Bắt đầu copy
        self.copy_worker.start()


def cat_chuoi_invoice(text: str) -> str:
    # Bước 1: Chuẩn hóa các dấu gạch
    text = text.replace("\u2010", "-").replace("\u2013",
                                               "-").replace("\u2014", "-").strip()

    # Bước 2: Nếu có dấu "_", xử lý theo phần sau
    if "_" in text:
        parts = text.split("_")
        # Ưu tiên tìm phần bắt đầu bằng "CBW"
        for part in parts:
            if part.upper().startswith("CBW"):
                return part.strip()
        # Nếu không có phần bắt đầu bằng CBW, trả về phần cuối cùng
        return parts[-1].strip()

    # Bước 3: Nếu không có dấu "_", lấy chuỗi trước dấu "-" cuối cùng
    dash_pos = text.rfind("-")
    if dash_pos > 0:
        return text[:dash_pos].strip()

    # Bước 4: Trường hợp không có "-" hoặc "_", trả về nguyên chuỗi đã được strip
    return text.strip()


def check_path_exists(path, description="đường dẫn"):
    if not os.path.exists(path):
        app = QApplication(sys.argv)  # Tạo ứng dụng để hiển thị thông báo
        QMessageBox.critical(
            None, "Lỗi", f"Máy chưa setup đầy đủ {description}, vui lòng kiểm tra lại!")
        sys.exit(1)  # Thoát chương trình với mã lỗi 1
    print(f"{description} tồn tại: {os.path.basename(path)}")


if __name__ == "__main__":
    # BƯỚC 1: KIỂM TRA FILE CẤU HÌNH
    check_path_exists(FILE_SETUP, "Dữ liệu cho phần mềm")

    # BƯỚC 2: TẠO QApplication TRƯỚC
    app = QApplication(sys.argv)

    # BƯỚC 3: BÂY GIỜ MỚI ĐƯỢC DÙNG QMessageBox, QWidget, v.v...
    # if not os.path.exists(DB_DATA_PATH):
    #     QMessageBox.critical(
    #         None, "Lỗi", f"Không tìm thấy file DB:\n{DB_DATA_PATH}"
    #     )
    #     sys.exit(1)  # Thoát ứng dụng

    # BƯỚC 4: TẠO CỬA SỔ CHÍNH
    window = InventoryManagerApp(DB_DATA_PATH)
    window.showMaximized()

    # BƯỚC 5: CHẠY ỨNG DỤNG
    sys.exit(app.exec())
