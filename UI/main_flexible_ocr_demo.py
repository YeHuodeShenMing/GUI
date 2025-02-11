from PyQt5.QtWidgets import *
import sys
from face_UI.ui import UI_main

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        win = UI_main()
        win.show()
        sys.exit(app.exec_())
    except Exception as e:
        QMessageBox.critical(None, "Critical Error", f"An unexpected error occurred: {e}")

