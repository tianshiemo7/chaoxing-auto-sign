import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from app import MainWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

app = QApplication(sys.argv)
app.setFont(QFont("Microsoft YaHei", 10))
win = MainWindow()
win.show()
sys.exit(app.exec())
