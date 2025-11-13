# warehouse_app/modules/ui/input_tab.py
import os
import shutil
import asyncio
import pandas as pd
from datetime import datetime
from PySide6.QtWidgets import (
    QFileDialog, QMessageBox, QTableWidgetItem, QVBoxLayout, QCompleter, QLabel
)
from PySide6.QtGui import QPixmap, QDesktopServices, QImage
from PySide6.QtCore import QStringListModel, Qt, QThread, QTimer, QUrl, QObject, QEvent


from modules.inventory import add_entry, delete_entry, refresh_current_stock, update_entry, generate_next_cid
from modules.options import get_all_categories
from modules.search import search_entries, get_name_suggestions
from modules.ui.multiselect_dropdown import MultiSelectDropdown
from modules.autocomplete_worker import AutocompleteWorker
from typing import List, Optional
import re
import json
from config.global_vars import get_folders
from modules.image_hover_preview import HoverPreviewLabel

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logging.disable(logging.CRITICAL)  # ← TẮT TẤT CẢ LOG TRONG TOÀN BỘ APP

DEFAULT_IMAGE_PATH = "images/default.jpg"


class InputTabController(QObject):
    def __init__(self, ui, team_id, user_id, username, db_handler):  # ← THÊM db_handler
        super().__init__()
        self.ui = ui
        self.team_id = team_id
        self.user_id = user_id
        self.username = username
        self.db_handler = db_handler  # ← GÁN ĐÚNG

        self.is_new = False
        self.is_editing = False
        self.editing_entry_id = None

        self.image_folder, self.invoice_folder = get_folders()  # ← LẤY MỚI NHẤT
        self.selected_image_path_input = DEFAULT_IMAGE_PATH
        self.options = {}
        self.current_data = []

        # GỢI Ý
        self.is_user_typing = False
        self.name_suggestions_cache = []
        self.current_search_text = ""

        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.refresh_name_suggestions)

        # Completer
        self.name_completer = QCompleter()
        self.name_model = QStringListModel()
        self.name_completer.setModel(self.name_model)
        self.name_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.name_completer.setFilterMode(Qt.MatchContains)
        self.ui.input_component_name_lineedit.setCompleter(self.name_completer)

        self.ui.input_component_name_lineedit.textChanged.connect(
            self.on_name_text_changed)

        # === THAY THẾ NGAY ĐẦU TIÊN ===
        self.replace_image_label_with_hover()
        logger.debug("[InputTab] HoverPreviewLabel replaced and initialized")

        self.setup_dropdowns()
        self.setup_connections()
        self.load_table_data()
        self.load_name_suggestions_cache()  # BÂY GIỜ DÙNG ĐƯỢC db_handler

    # =========================================================
    # HIỂN THỊ ẢNH TỪ image_folder
    # =========================================================
    def display_image(self, image_filename: str):
        try:
            if not image_filename:
                self.ui.input_images_label.set_image(DEFAULT_IMAGE_PATH)
                # self.ui.input_images_label.hide_zoom()  # ← ẨN ZOOM KHI KHÔNG CÓ ẢNH
                return

            folder = self.image_folder
            base_name = os.path.splitext(image_filename)[0].lower()

            found_path = None
            for file in os.listdir(folder):
                if os.path.splitext(file)[0].lower() == base_name:
                    found_path = os.path.join(folder, file)
                    break

            path_to_show = found_path if found_path and os.path.exists(
                found_path) else DEFAULT_IMAGE_PATH
            self.ui.input_images_label.set_image(path_to_show)
            # self.ui.input_images_label.hide_zoom()  # ← ẨN ZOOM SAU KHI LOAD

        except Exception as e:
            print(f"[IMAGE][LỖI hiển thị]: {e}")
            self.ui.input_images_label.set_image(DEFAULT_IMAGE_PATH)
            # self.ui.input_images_label.hide_zoom()
    # =========================================================
    # cấp mới mã số sản phẩm CID
    # =========================================================

    def on_auto_cid_changed(self, state):
        if state == 2:  # Qt.Checked
            self.generate_and_set_cid()
        else:
            # Không làm gì khi bỏ check
            pass

    # === HÀM MỚI: generate_and_set_cid ===
    def generate_and_set_cid(self):
        storage_text = self.ui.input_storage_location_combobox.currentText()
        if not storage_text:
            QMessageBox.warning(None, "Lỗi", "Vui lòng chọn Storage Location.")
            self.ui.input_check_id_auto_checkBox.setChecked(False)
            return

        # Gọi hàm sinh CID
        new_cid = asyncio.run(generate_next_cid(storage_text))
        if new_cid:
            self.ui.input_component_id_lineedit.setText(new_cid)
            # QMessageBox.information(None, "Auto CID", f"Đã sinh: {new_cid}")
        else:
            QMessageBox.critical(None, "Lỗi", "Không thể sinh CID.")
            self.ui.input_check_id_auto_checkBox.setChecked(False)

    # =========================================================
    # Thiết lập dropdowns
    # =========================================================
    def setup_dropdowns(self):
        try:
            self.options = asyncio.run(get_all_categories(self.team_id))

            self.groups_selector = MultiSelectDropdown(
                self.ui.tabInput, self.options.get("groups", []), "groupsSelector")
            self.process_selector = MultiSelectDropdown(
                self.ui.tabInput, self.options.get("process", []), "processSelector")
            self.model_selector = MultiSelectDropdown(
                self.ui.tabInput, self.options.get("model", []), "modelSelector")
            self.material_selector = MultiSelectDropdown(
                self.ui.tabInput, self.options.get("material", []), "materialSelector")

            for widget, dropdown in [
                (self.ui.input_groups_widget, self.groups_selector),
                (self.ui.input_process_widget, self.process_selector),
                (self.ui.input_model_widget, self.model_selector),
                (self.ui.input_material_widget, self.material_selector),
            ]:
                if widget.layout() is None:
                    widget.setLayout(QVBoxLayout())
                widget.layout().addWidget(dropdown)

            self.ui.input_unit_combobox.addItems(self.options.get("unit", []))
            self.ui.input_storage_location_combobox.addItems(
                self.options.get("storage_location", []))
            self.ui.input_status_combobox.addItems(
                self.options.get("status", []))

        except Exception as e:
            QMessageBox.critical(None, "Lỗi khởi tạo dropdown", str(e))

    # =========================================================
    # Kết nối nút
    # =========================================================
    def setup_connections(self):
        self.ui.input_check_id_auto_checkBox.stateChanged.connect(
            self.on_auto_cid_changed)
        self.ui.input_new_button.clicked.connect(self.add_new_item)
        self.ui.input_edit_button.clicked.connect(self.edit_selected_item)
        self.ui.input_delete_button.clicked.connect(self.delete_selected_item)
        self.ui.input_search_button.clicked.connect(self.search_items)
        self.ui.input_export_button.clicked.connect(self.export_to_excel)

        self.ui.input_data_tablewidget.currentCellChanged.connect(
            self.on_row_selected)

    # =========================================================
    # TẢI DỮ LIỆU (TỐI ƯU)
    # =========================================================
    def load_table_data(self, data=None):
        try:
            self.current_data = data or asyncio.run(
                search_entries(team_id=self.team_id)
            )

            if not self.current_data:
                self.ui.input_data_tablewidget.setRowCount(0)
                return

            headers = list(self.current_data[0].keys())
            table = self.ui.input_data_tablewidget
            table.setColumnCount(len(headers))
            table.setHorizontalHeaderLabels(headers)
            table.setRowCount(len(self.current_data))

            for r, row in enumerate(self.current_data):
                for c, key in enumerate(headers):
                    table.setItem(r, c, QTableWidgetItem(
                        str(row.get(key, ""))))

            table.resizeColumnsToContents()
            # === THÊM 2 DÒNG NÀY ===
            if table.rowCount() > 0:
                table.selectRow(0)                    # TỰ ĐỘNG CHỌN DÒNG ĐẦU
                # HIỂN THỊ ẢNH NGAY LẬP TỨC
                self.on_row_selected(0, 0)
        except Exception as e:
            QMessageBox.critical(None, "Lỗi tải dữ liệu", str(e))

    # =========================================================
    # TÌM KIẾM (SIÊU NHANH)
    # =========================================================
    def search_items(self):
        """Tìm kiếm có điều kiện theo checkbox"""
        filters = {}
        # === 0. thêm điều kiện movement_type='in'
        filters['movement_type'] = 'in'
        # === 1. Component ID (chỉ khi check) ===
        if self.ui.input_search_component_id_checkBox.isChecked():
            cid = self.ui.input_component_id_lineedit.text().strip().upper()
            if cid:
                filters["component_id"] = cid

        # === 2. Component Name ===
        if self.ui.input_search_component_name_checkBox.isChecked():
            name = self.ui.input_component_name_lineedit.text().strip()
            if name:
                filters["component_name"] = name

        # === 3. Groups ===
        if self.ui.input_search_groups_checkBox.isChecked():
            groups = self.groups_selector.get_selected_items()
            if groups:
                filters["groups"] = groups

        # === 4. Process ===
        if self.ui.input_search_process_checkBox.isChecked():
            process = self.process_selector.get_selected_items()
            if process:
                filters["process"] = process

        # === 5. Model ===
        if self.ui.input_search_model_checkBox.isChecked():
            model = self.model_selector.get_selected_items()
            if model:
                filters["model"] = model

        # === 6. Material ===
        if self.ui.input_search_material_checkBox.isChecked():
            material = self.material_selector.get_selected_items()
            if material:
                filters["material"] = material

        # === 7. Storage Location ===
        if self.ui.input_search_storage_location_checkBox.isChecked():
            loc = self.ui.input_storage_location_combobox.currentText()
            if loc:
                filters["storage_location"] = [loc]

        # === 8. Status ===
        if self.ui.input_search_status_checkBox.isChecked():
            status = self.ui.input_status_combobox.currentText()
            if status:
                filters["status"] = [status]

        # === 9. Invoice ===
        if self.ui.input_search_invoice_checkBox.isChecked():
            inv = self.ui.input_invoice_lineedit.text().strip()
            if inv:
                filters["invoice"] = inv

        # === 10. Desinvoice (modinvoice) ===
        if self.ui.input_search_desinvoice_checkBox.isChecked():
            des = self.ui.input_desinvoice_lineedit.text().strip()
            if des:
                filters["modinvoice"] = des

        # === 11. Note (có mode: contains, not contains, empty, not empty) ===
        if self.ui.input_search_note_checkBox.isChecked():
            note_text = self.ui.input_note_textedit.toPlainText().strip()
            mode = self.ui.input_note_fillter_combobox.currentText()

            if mode == "Contains":
                if note_text:
                    filters["note_contains"] = note_text
            elif mode == "Does not contains":
                if note_text:
                    filters["note_not_contains"] = note_text
            elif mode == "Is empty":
                filters["note_is_empty"] = True
            elif mode == "Is not empty":
                filters["note_is_not_empty"] = True

        # === GỌI SEARCH SIÊU NHANH ===
        data = asyncio.run(search_entries(self.team_id, filters=filters))
        self.load_table_data(data)

    # =========================================================
    # THÊM MỚI
    # =========================================================
    def add_new_item(self):
        if self.is_new:
            self.save_new_item()
            return
        if self.is_editing:
            self.save_edit_item()
            return

        # ... chế độ thêm mới
        self.clear_form()
        self.is_new = True
        self.ui.input_new_button.setText("💾 Save")
        self.ui.input_delete_button.setText("❌ Cancel")
        self.ui.input_edit_button.setEnabled(False)

    def save_new_item(self):
        try:
            component_id = self.ui.input_component_id_lineedit.text().strip().upper()
            if not component_id:
                QMessageBox.warning(None, "Lỗi", "Vui lòng nhập mã linh kiện.")
                return

            # === LƯU ẢNH TRƯỚC ===
            image_path = self.save_image(component_id)

            data = {
                "component_id": component_id,
                "component_name": self.ui.input_component_name_lineedit.text().strip(),
                "group_name": self.groups_selector.get_selected_items(),
                "process": self.process_selector.get_selected_items(),
                "model": self.model_selector.get_selected_items(),
                "size": self.ui.input_size_lineedit.text().strip(),
                "unit": self.ui.input_unit_combobox.currentText(),
                "team_id": self.team_id,
                "material": self.material_selector.get_selected_items(),
                "storage_location": self.ui.input_storage_location_combobox.currentText(),
                "invoice": self.ui.input_invoice_lineedit.text().strip(),
                "modinvoice": self.ui.input_desinvoice_lineedit.text().strip(),
                "status": self.ui.input_status_combobox.currentText(),
                "note": self.ui.input_note_textedit.toPlainText(),
                "quantity": float(self.ui.input_quantity_lineedit.text() or 0),
                "movement_type": "in",
                "created_by": self.user_id,
            }

            entry_id = asyncio.run(add_entry(**data))
            asyncio.run(refresh_current_stock())

            # === Sau khi lưu DB xong, in log ảnh nếu có ===
            if image_path:
                print(f"[SAVE] Ảnh đã lưu tại: {image_path}")

            self.is_new = False
            self.ui.input_new_button.setText("New")
            self.ui.input_delete_button.setText("Delete")
            self.ui.input_edit_button.setEnabled(True)

            self.load_table_data()
            QMessageBox.information(
                None, "Thành công", f"Đã lưu ID={entry_id}")

        except Exception as e:
            QMessageBox.critical(None, "Lỗi lưu", str(e))

    # =========================================================
    # EDIT
    # =========================================================

    def edit_selected_item(self):
        row = self.ui.input_data_tablewidget.currentRow()
        if row < 0:
            QMessageBox.warning(None, "Lỗi", "Vui lòng chọn dòng để sửa.")
            return

        if self.is_new:
            QMessageBox.warning(None, "Lỗi", "Đang tạo mới, không thể sửa.")
            return

        # Lấy ID
        entry_id = int(self.ui.input_data_tablewidget.item(row, 0).text())
        self.editing_entry_id = entry_id
        self.is_editing = True

        self.ui.input_new_button.setText("💾 Save Edit")
        self.ui.input_delete_button.setText("❌ Cancel")
        self.ui.input_edit_button.setEnabled(False)

        QMessageBox.information(
            None, "Chế độ sửa", f"Đang sửa phiếu ID={entry_id}")

    def save_edit_item(self):
        try:
            # LẤY ID CỦA DÒNG ĐANG EDIT
            if not self.editing_entry_id:
                QMessageBox.warning(None, "Lỗi", "Không có ID để sửa.")
                return

            component_id = self.ui.input_component_id_lineedit.text().strip().upper()
            if not component_id:
                QMessageBox.warning(None, "Lỗi", "Vui lòng nhập mã linh kiện.")
                return

            # === LƯU ẢNH NẾU CÓ ===
            image_path = None
            if self.selected_image_path_input and self.selected_image_path_input != DEFAULT_IMAGE_PATH:
                image_path = self.save_image(component_id)

            # LẤY DỮ LIỆU HIỆN TẠI TỪ FORM
            data = {
                "id": self.editing_entry_id,
                "component_id": component_id,
                "component_name": self.ui.input_component_name_lineedit.text().strip(),
                "group_name": self.groups_selector.get_selected_items(),
                "process": self.process_selector.get_selected_items(),
                "model": self.model_selector.get_selected_items(),
                "size": self.ui.input_size_lineedit.text().strip(),
                "unit": self.ui.input_unit_combobox.currentText(),
                "team_id": self.team_id,
                "material": self.material_selector.get_selected_items(),
                "storage_location": self.ui.input_storage_location_combobox.currentText(),
                "invoice": self.ui.input_invoice_lineedit.text().strip(),
                "modinvoice": self.ui.input_desinvoice_lineedit.text().strip(),
                "status": self.ui.input_status_combobox.currentText(),
                "note": self.ui.input_note_textedit.toPlainText(),
                "quantity": float(self.ui.input_quantity_lineedit.text() or 0),
                # KHÔNG GỬI movement_type → giữ nguyên
                "created_by": self.user_id,
            }

            # GỌI update_entry() → chỉ cập nhật dòng cũ
            updated_id = asyncio.run(update_entry(**data))

            # CẬP NHẬT TỒN KHO
            asyncio.run(refresh_current_stock())

            # THOÁT CHẾ ĐỘ EDIT
            self.is_editing = False
            self.editing_entry_id = None
            self.ui.input_new_button.setText("➕ New")
            self.ui.input_delete_button.setText("🗑 Delete")
            self.ui.input_edit_button.setEnabled(True)

            # Làm mới bảng & thông báo
            self.load_table_data()

            msg = f"Đã cập nhật ID={updated_id}"
            if image_path:
                msg += f"\nẢnh đã lưu tại: {image_path}"
            QMessageBox.information(None, "Thành công", msg)

        except Exception as e:
            QMessageBox.critical(None, "Lỗi", str(e))

    # =========================================================
    # XÓA / HỦY
    # =========================================================

    def delete_selected_item(self):
        if self.ui.input_delete_button.text() == "❌ Cancel":
            self.is_new = False
            self.is_editing = False
            self.editing_entry_id = None
            self.ui.input_new_button.setText("➕ New")
            self.ui.input_delete_button.setText("🗑 Delete")
            self.ui.input_edit_button.setEnabled(True)
            self.clear_form()
            return

        row = self.ui.input_data_tablewidget.currentRow()
        if row < 0:
            QMessageBox.warning(None, "Lỗi", "Vui lòng chọn dòng để xóa.")
            return

        entry_id = int(self.ui.input_data_tablewidget.item(row, 0).text())
        if QMessageBox.question(None, "Xác nhận", f"Xóa ID={entry_id}?") == QMessageBox.Yes:
            asyncio.run(delete_entry(entry_id, self.user_id))
            asyncio.run(refresh_current_stock())
            self.load_table_data()
            QMessageBox.information(None, "Xóa", f"Đã xóa ID={entry_id}")

    # =========================================================
    # XUẤT EXCEL (CÓ HEADER)
    # =========================================================
    def export_to_excel(self):
        path, _ = QFileDialog.getSaveFileName(
            None, "Xuất Excel", "", "Excel Files (*.xlsx)")
        if not path:
            return
        try:
            table = self.ui.input_data_tablewidget
            headers = [table.horizontalHeaderItem(
                c).text() for c in range(table.columnCount())]
            data = []
            for r in range(table.rowCount()):
                row = [table.item(r, c).text() if table.item(
                    r, c) else "" for c in range(table.columnCount())]
                data.append(row)
            df = pd.DataFrame(data, columns=headers)
            df.to_excel(path, index=False)
            QMessageBox.information(None, "Xuất Excel", f"Đã lưu: {path}")
        except Exception as e:
            QMessageBox.critical(None, "Lỗi", str(e))

    # =========================================================
    # CHỌN HÌNH ẢNH
    # =========================================================
    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            None, "Chọn ảnh", "", "Images (*.jpg *.jpeg *.png)")
        if file_path:
            self.selected_image_path_input = file_path
            self.ui.input_images_label.set_image(file_path)  # ← Dùng set_image

    # =========================================================
    # XÓA FORM
    # =========================================================
    def clear_form(self):
        self.is_user_typing = False
        self.ui.input_component_id_lineedit.clear()
        self.ui.input_component_name_lineedit.clear()
        self.ui.input_size_lineedit.clear()
        self.ui.input_invoice_lineedit.clear()
        self.ui.input_desinvoice_lineedit.clear()
        self.ui.input_note_textedit.clear()
        self.ui.input_quantity_lineedit.clear()
        self.ui.input_unit_combobox.setCurrentIndex(-1)
        self.ui.input_storage_location_combobox.setCurrentIndex(-1)
        self.ui.input_status_combobox.setCurrentIndex(-1)
        self.groups_selector.set_selected_items([])
        self.model_selector.set_selected_items([])
        self.process_selector.set_selected_items([])
        self.material_selector.set_selected_items([])
        self.ui.input_images_label.set_image(
            DEFAULT_IMAGE_PATH)  # ← Dùng set_image
        self.is_user_typing = True
        self.ui.input_images_label.clear_and_hide()  # ← ẨN ZOOM + XÓA ẢNH
    # =========================================================
    # KHI CHỌN DÒNG TRONG BẢNG
    # =========================================================

    def on_row_selected(self, row, col, prev_row=None, prev_col=None):
        if row < 0:
            # self.ui.input_images_label.clear_and_hide()  # ← ẨN KHI KHÔNG CÓ DÒNG
            return  # Tránh lỗi khi bảng rỗng

        try:
            self.is_user_typing = False

            table = self.ui.input_data_tablewidget

            def get_col(name):
                for c in range(table.columnCount()):
                    header = table.horizontalHeaderItem(c)
                    if header and header.text() == name:
                        item = table.item(row, c)
                        return item.text() if item else ""
                return ""

            def parse_array(text):
                if not text or text in ("[]", "null"):
                    return []
                text = text.strip()
                if text.startswith('[') and text.endswith(']'):
                    try:
                        return json.loads(text)
                    except:
                        pass
                text = text.strip("[]").replace("'", "").replace('"', '')
                return [x.strip() for x in re.split(r',\s*', text) if x.strip()]

            # === LẤY DỮ LIỆU ===
            component_id = get_col("component_id")

            # === GÁN CÁC TRƯỜNG ===
            self.ui.input_component_id_lineedit.setText(
                get_col("component_id"))
            self.ui.input_component_name_lineedit.setText(
                get_col("component_name"))
            self.ui.input_size_lineedit.setText(get_col("size"))
            self.ui.input_invoice_lineedit.setText(get_col("invoice"))
            self.ui.input_desinvoice_lineedit.setText(get_col("modinvoice"))
            self.ui.input_quantity_lineedit.setText(get_col("quantity"))
            self.ui.input_unit_combobox.setCurrentText(get_col("unit"))
            self.ui.input_status_combobox.setCurrentText(get_col("status"))
            self.ui.input_note_textedit.setPlainText(get_col("note"))
            self.ui.input_storage_location_combobox.setCurrentText(
                get_col("storage_location"))

            # === MULTISELECT ===
            self.groups_selector.set_selected_items(
                parse_array(get_col("group_name")))
            self.process_selector.set_selected_items(
                parse_array(get_col("process")))
            self.model_selector.set_selected_items(
                parse_array(get_col("model")))
            self.material_selector.set_selected_items(
                parse_array(get_col("material")))

            # === HIỂN THỊ ẢNH (QUAN TRỌNG NHẤT) ===
            self.display_image(component_id)  # ← GỌI ĐÚNG

            self.is_user_typing = True

        except Exception as e:
            print(f"[on_row_selected] Lỗi: {e}")

    def load_name_suggestions_cache(self):
        try:
            df = self.db_handler.read_data(
                "inventory_entries", ["component_name", "team_id"])
            df = df[df["team_id"] == self.team_id]
            self.name_suggestions_cache = sorted(
                set(df["component_name"].dropna().astype(
                    str).str.strip().unique())
            )
            # print(
            #     f"[CACHE] Đã tải {len(self.name_suggestions_cache)} tên linh kiện")
        except Exception as e:
            print(f"[CACHE] Lỗi: {e}")
            self.name_suggestions_cache = []

    def on_name_text_changed(self, text: str):
        if not self.is_user_typing:
            return
        if len(text) < 2:
            self.name_model.setStringList([])
            return
        self.current_search_text = text
        self.debounce_timer.start(300)

    def refresh_name_suggestions(self):
        text = self.current_search_text.lower()
        filtered = [
            v for v in self.name_suggestions_cache if text in v.lower()][:20]
        # print(f"[SUGGEST] '{text}' → {len(filtered)} gợi ý")
        self.name_model.setStringList(filtered)
        if filtered:
            self.name_completer.complete()

    def on_suggestions_ready(self, suggestions: List[str]):
        # print(f"[DEBUG] Gợi ý nhận được: {suggestions}")
        self.name_model.setStringList(suggestions)
        if suggestions:
            QTimer.singleShot(0, self.name_completer.complete)

    def save_image(self, component_id: str):
        if not self.selected_image_path_input or self.selected_image_path_input == DEFAULT_IMAGE_PATH:
            return None

        target_path = os.path.join(self.image_folder, f"{component_id}.jpg")
        os.makedirs(self.image_folder, exist_ok=True)

        try:
            if self.selected_image_path_input.lower().endswith(('.jpg', '.jpeg')):
                if self.selected_image_path_input != target_path:
                    shutil.copy2(self.selected_image_path_input, target_path)
            else:
                from PIL import Image
                img = Image.open(self.selected_image_path_input).convert('RGB')
                img.save(target_path, "JPEG", quality=90)

            # Cập nhật lại ảnh hiển thị sau khi lưu
            self.ui.input_images_label.set_image(target_path)
            return target_path
        except Exception as e:
            print(f"[IMAGE][LỖI lưu]: {e}")
            return None

    def replace_image_label_with_hover(self):
        logger.debug("[InputTab] replace_image_label_with_hover START")
        # Tạo HoverPreviewLabel
        self.hover_preview = HoverPreviewLabel(self.ui.tabInput)
        self.hover_preview.setFixedSize(200, 200)

        # Áp dụng style từ .ui (QLabel) → giữ nguyên thiết kế
        self.hover_preview.setStyleSheet("""
            QLabel {
                background-color: #ffffff;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                padding: 6px;
                color: #444444;
            }
            QLabel:hover {
                background-color: #f7faff;
            }
        """)
        self.hover_preview.setAttribute(
            Qt.WA_StyledBackground, True)  # ← BẬT ĐỂ border-radius HOẠT ĐỘNG

        # Thay thế widget cũ
        old_label = self.ui.input_images_label
        parent_layout = old_label.parent().layout()
        if parent_layout:
            parent_layout.replaceWidget(old_label, self.hover_preview)
        old_label.deleteLater()
        self.ui.input_images_label = self.hover_preview

        self.hover_preview.setMouseTracking(True)
        logger.debug(
            f"[InputTab] Mouse tracking enabled: {self.hover_preview.hasMouseTracking()}")

        self.hover_preview.installEventFilter(self)
        logger.debug("[InputTab] eventFilter installed")

        # TEST: Ẩn zoom ngay từ đầu
        self.ui.input_images_label.hide_zoom()
        logger.debug("[InputTab] hide_zoom() called at init")

    def eventFilter(self, watched, event):
        if watched == self.ui.input_images_label and event.type() == QEvent.MouseButtonDblClick:
            self.select_image()
            return True
        return super().eventFilter(watched, event)
