# test_ui_inventory.py
import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from ui.screen_InventoryManager import Ui_MainWindow

app = QApplication(sys.argv)
win = QMainWindow()
ui = Ui_MainWindow()
ui.setupUi(win)
win.show()
sys.exit(app.exec())
