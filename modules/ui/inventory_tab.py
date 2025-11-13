# warehouse_app/modules/ui/inventory_tab.py
import os
import asyncio
import pandas as pd
from PySide6.QtWidgets import (
    QTableWidgetItem, QFileDialog, QMessageBox, QVBoxLayout
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import QObject, Qt, QEvent
from modules.inventory import get_current_stock, get_component_info_from_stock
from modules.options import get_all_categories
from modules.search import search_current_stock
from config.global_vars import get_folders
from modules.ui.multiselect_dropdown import MultiSelectDropdown
from modules.image_hover_preview import HoverPreviewLabel


class InventoryTabController(QObject):
    def __init__(self, ui, team_id, user_id, username, db_handler):
        super().__init__()
        self.ui = ui
        self.team_id = team_id
        self.user_id = user_id
        self.username = username
        self.db_handler = db_handler

        self.image_folder, _ = get_folders()

        # === TẢI OPTIONS ===
        self.options = asyncio.run(get_all_categories(self.team_id))

        # === MULTISELECT ===
        self.setup_multiselect_widgets()

        # === ẢNH HOVER ===
        self.replace_image_label_with_hover()

        # === KẾT NỐI ===
        self.setup_connections()

        # === TẢI TỒN KHO ===
        self.load_inventory_table()

    # =========================================================
    # MULTISELECT (GIỐNG INPUT_TAB)
    # =========================================================
    def setup_multiselect_widgets(self):
        self.inventory_groups_selector = MultiSelectDropdown(
            self.ui.tabInventory, self.options.get("groups", []), "inv_groups")
        self.inventory_process_selector = MultiSelectDropdown(
            self.ui.tabInventory, self.options.get("process", []), "inv_process")
        self.inventory_model_selector = MultiSelectDropdown(
            self.ui.tabInventory, self.options.get("model", []), "inv_model")
        self.inventory_material_selector = MultiSelectDropdown(
            self.ui.tabInventory, self.options.get("material", []), "inv_material")

        for widget, dropdown in [
            (self.ui.inventory_groups_widget, self.inventory_groups_selector),
            (self.ui.inventory_process_widget, self.inventory_process_selector),
            (self.ui.inventory_model_widget, self.inventory_model_selector),
            (self.ui.inventory_material_widget, self.inventory_material_selector),
        ]:
            if widget.layout() is None:
                widget.setLayout(QVBoxLayout())
            widget.layout().addWidget(dropdown)

        # Combobox
        self.ui.inventory_storage_location_combobox.clear()
        self.ui.inventory_unit_combobox.clear()
        self.ui.inventory_status_combobox.clear()
        self.ui.inventory_unit_combobox.addItems(
            self.options.get("unit", ["pcs"]))
        self.ui.inventory_status_combobox.addItems(
            self.options.get("status", ["Available"]))
        self.ui.inventory_storage_location_combobox.addItems(
            self.options.get("storage_location", ["Box 001"]))

    # =========================================================
    # HOVER ZOOM ẢNH (GIỐNG INPUT_TAB)
    # =========================================================

    def replace_image_label_with_hover(self):
        self.hover_preview = HoverPreviewLabel(self.ui.tabInventory)
        self.hover_preview.setFixedSize(200, 200)
        self.hover_preview.setStyleSheet("""
            QLabel { background: white; border: 2px solid #e0e0e0; border-radius: 10px; padding: 6px; }
            QLabel:hover { background: #f7faff; }
        """)
        self.hover_preview.setAttribute(Qt.WA_StyledBackground, True)

        old_label = self.ui.inventory_images_label
        parent_layout = old_label.parent().layout()
        if parent_layout:
            parent_layout.replaceWidget(old_label, self.hover_preview)
        old_label.deleteLater()
        self.ui.inventory_images_label = self.hover_preview

        self.hover_preview.setMouseTracking(True)
        self.hover_preview.installEventFilter(self)
        self.ui.inventory_images_label.hide_zoom()

    def eventFilter(self, watched, event):
        if watched == self.ui.inventory_images_label and event.type() == QEvent.MouseButtonDblClick:
            self.select_image()
            return True
        return super().eventFilter(watched, event)

    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            None, "Chọn ảnh", "", "Images (*.jpg *.jpeg *.png)")
        if file_path:
            self.ui.inventory_images_label.set_image(file_path)

    def display_image(self, component_id: str):
        image_path = os.path.join(self.image_folder, f"{component_id}.jpg")
        default = "images/default.jpg"
        path = image_path if os.path.exists(
            image_path) and os.path.getsize(image_path) > 0 else default
        self.ui.inventory_images_label.set_image(path)

    # =========================================================
    # KẾT NỐI NÚT (GIỐNG INPUT_TAB)
    # =========================================================
    def setup_connections(self):
        self.ui.inventory_search_button.clicked.connect(self.search_inventory)
        self.ui.inventory_export_button.clicked.connect(self.export_to_excel)
        self.ui.inventory_data_tablewidget.currentCellChanged.connect(
            self.on_row_selected)

    # =========================================================
    # TẢI TỒN KHO (GIỐNG INPUT_TAB)
    # =========================================================
    def load_inventory_table(self, data=None):
        try:
            data = data or asyncio.run(get_current_stock(team_id=self.team_id))

            table = self.ui.inventory_data_tablewidget
            if not data:
                table.setRowCount(0)
                return

            # === LẤY TẤT CẢ CỘT ===
            headers = list(data[0].keys())
            table.setColumnCount(len(headers))
            table.setHorizontalHeaderLabels(headers)
            table.setRowCount(len(data))

            # === ĐỔ DỮ LIỆU ===
            for r, row in enumerate(data):
                for c, key in enumerate(headers):
                    value = row.get(key, "")
                    if key == "current_quantity":
                        value = str(int(value)) if value is not None else "0"
                    elif isinstance(value, list):  # group_name, process, model, material
                        value = ", ".join(value) if value else ""
                    table.setItem(r, c, QTableWidgetItem(str(value)))

            # === HIỂN THỊ ĐẦY ĐỦ CỘT ===
            table.resizeColumnsToContents()
            table.horizontalHeader().setStretchLastSection(True)  # Kéo rộng cột cuối

            if table.rowCount() > 0:
                table.selectRow(0)
                self.on_row_selected(0, 0)

        except Exception as e:
            QMessageBox.critical(None, "Lỗi tải tồn kho", str(e))

    # =========================================================
    # TÌM KIẾM (GIỐNG INPUT_TAB)
    # =========================================================
    def search_inventory(self):
        filters = {}

        if self.ui.inventory_search_component_id_checkBox.isChecked():
            cid = self.ui.inventory_component_id_lineedit.text().strip().upper()
            if cid:
                filters["component_id"] = cid

        if self.ui.inventory_search_component_name_checkBox.isChecked():
            name = self.ui.inventory_component_name_lineedit.text().strip()
            if name:
                filters["component_name_contains"] = name

        if self.ui.inventory_search_size_checkBox.isChecked():
            size = self.ui.inventory_size_lineedit.text().strip()
            if size:
                filters["size"] = size

        if self.ui.inventory_search_status_checkBox.isChecked():
            status = self.ui.inventory_status_combobox.currentText()
            if status:
                filters["status"] = status

        if self.ui.inventory_search_invoice_checkBox.isChecked():
            inv = self.ui.inventory_invoice_lineedit.text().strip()
            if inv:
                filters["invoice"] = inv

        if self.ui.inventory_search_desinvoice_checkBox.isChecked():
            des = self.ui.inventory_desinvoice_lineedit.text().strip()
            if des:
                filters["modinvoice"] = des

        if self.ui.inventory_search_note_checkBox.isChecked():
            note = self.ui.inventory_note_textedit.toPlainText().strip()
            if note:
                filters["note_contains"] = note

        if self.ui.inventory_search_groups_checkBox.isChecked():
            groups = self.inventory_groups_selector.get_selected_items()
            if groups:
                filters["group_name"] = groups

        if self.ui.inventory_search_process_checkBox.isChecked():
            process = self.inventory_process_selector.get_selected_items()
            if process:
                filters["process"] = process

        if self.ui.inventory_search_model_checkBox.isChecked():
            model = self.inventory_model_selector.get_selected_items()
            if model:
                filters["model"] = model

        if self.ui.inventory_search_material_checkBox.isChecked():
            material = self.inventory_material_selector.get_selected_items()
            if material:
                filters["material"] = material

        if self.ui.inventory_search_storage_location_checkBox.isChecked():
            loc = self.ui.inventory_storage_location_combobox.currentText()
            if loc:
                filters["storage_location"] = [loc]

        try:
            if filters:
                data = asyncio.run(search_current_stock(self.team_id, filters))
            else:
                data = asyncio.run(get_current_stock(team_id=self.team_id))
            self.load_inventory_table(data)
        except Exception as e:
            QMessageBox.critical(None, "Lỗi tìm kiếm", str(e))

    # =========================================================
    # XEM CHI TIẾT (GIỐNG INPUT_TAB)
    # =========================================================
    def on_row_selected(self, row, col):
        if row < 0:
            self.clear_form()
            return

        try:
            table = self.ui.inventory_data_tablewidget
            component_id = ""

            # Tìm cột component_id
            for c in range(table.columnCount()):
                header = table.horizontalHeaderItem(c)
                if header and header.text() == "component_id":
                    item = table.item(row, c)
                    component_id = item.text() if item else ""
                    break

            if not component_id:
                return

            info = asyncio.run(get_component_info_from_stock(
                self.team_id, component_id))
            if not info:
                return

            # === ĐỔ ĐẦY ĐỦ THÔNG TIN ===
            self.ui.inventory_storage_location_combobox.setCurrentText(
                info.get("storage_location", ""))
            self.ui.inventory_component_id_lineedit.setText(component_id)
            self.ui.inventory_component_name_lineedit.setText(
                info.get("component_name", "-"))
            self.ui.inventory_size_lineedit.setText(info.get("size", "-"))
            self.ui.inventory_quantity_lineedit.setText(
                str(int(info.get("current_quantity", 0))))
            self.ui.inventory_unit_combobox.setCurrentText(
                info.get("unit", ""))
            self.ui.inventory_status_combobox.setCurrentText(
                info.get("status", ""))
            self.ui.inventory_invoice_lineedit.setText(info.get("invoice", ""))
            self.ui.inventory_desinvoice_lineedit.setText(
                info.get("modinvoice", ""))
            self.ui.inventory_note_textedit.setPlainText(info.get("note", ""))

            # MultiSelect
            self.inventory_groups_selector.set_selected_items(
                info.get("group_name", []))
            self.inventory_process_selector.set_selected_items(
                info.get("process", []))
            self.inventory_model_selector.set_selected_items(
                info.get("model", []))
            self.inventory_material_selector.set_selected_items(
                info.get("material", []))

            self.display_image(component_id)

        except Exception as e:
            print(f"[INVENTORY] on_row_selected lỗi: {e}")

    # =========================================================
    # XÓA FORM (GIỐNG INPUT_TAB)
    # =========================================================
    def clear_form(self):
        self.ui.inventory_component_id_lineedit.clear()
        self.ui.inventory_component_name_lineedit.clear()
        self.ui.inventory_size_lineedit.clear()
        self.ui.inventory_quantity_lineedit.clear()
        self.ui.inventory_invoice_lineedit.clear()
        self.ui.inventory_desinvoice_lineedit.clear()
        self.ui.inventory_note_textedit.clear()
        self.ui.inventory_unit_combobox.setCurrentIndex(-1)
        self.ui.inventory_status_combobox.setCurrentIndex(-1)
        self.ui.inventory_storage_location_combobox.setCurrentIndex(-1)
        self.inventory_groups_selector.set_selected_items([])
        self.inventory_process_selector.set_selected_items([])
        self.inventory_model_selector.set_selected_items([])
        self.inventory_material_selector.set_selected_items([])

        self.ui.inventory_images_label.set_image("images/default.jpg")
        self.ui.inventory_images_label.hide_zoom()

    # =========================================================
    # XUẤT EXCEL (GIỐNG INPUT_TAB)
    # =========================================================
    def export_to_excel(self):
        path, _ = QFileDialog.getSaveFileName(
            None, "Xuất Excel", "", "Excel Files (*.xlsx)")
        if not path:
            return
        try:
            table = self.ui.inventory_data_tablewidget
            headers = [table.horizontalHeaderItem(
                c).text() for c in range(table.columnCount())]
            data = []
            for r in range(table.rowCount()):
                row = []
                for c in range(table.columnCount()):
                    item = table.item(r, c)
                    row.append(item.text() if item else "")
                data.append(row)
            pd.DataFrame(data, columns=headers).to_excel(path, index=False)
            QMessageBox.information(None, "Xuất Excel", f"Đã lưu: {path}")
        except Exception as e:
            QMessageBox.critical(None, "Lỗi", str(e))
