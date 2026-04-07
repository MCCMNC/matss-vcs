import os
import sys
import django
from PyQt6.QtWidgets import QApplication

# -------------------- Django Setup --------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
# -------------------- Main Window --------------------
from GUI_MainWindow import *
# -------------------- Run App --------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())