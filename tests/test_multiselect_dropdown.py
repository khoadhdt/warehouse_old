from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from modules.ui.multiselect_dropdown import MultiSelectDropdown
import sys

app = QApplication(sys.argv)
win = QWidget()
layout = QVBoxLayout(win)

multi = MultiSelectDropdown(win, ["A", "B", "C", "D"], "process")
layout.addWidget(multi)

win.show()
sys.exit(app.exec())
