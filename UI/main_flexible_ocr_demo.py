from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QImage, QPixmap, QIcon
from PyQt5.QtCore import QTimer, Qt
import cv2
import sys
import sqlite3
import os
import main_flexible_ocr_ui
import pytz
from datetime import datetime
import imutils
import easyocr
import numpy as np
import matplotlib.pyplot as plt
import utils.process_video as process_video
import re
from PyQt5.QtCore import QThread, pyqtSignal
from face_UI.ui import UI_main

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        win = UI_main()
        win.show()
        sys.exit(app.exec_())
    except Exception as e:
        QMessageBox.critical(None, "Critical Error", f"An unexpected error occurred: {e}")


"""
1. Lets make the form more flexible (maximizable and minimizable)
2. Lets make the start button add one more functionality (let embed OCR model to extract the students ID and automatically save the video using the ID_timestamp)
3. Lets put the messages using green label on top of the frame
"""


