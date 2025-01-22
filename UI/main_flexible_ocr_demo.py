from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QImage, QPixmap
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

class UI_main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = main_flexible_ocr_ui.Ui_StudentFaceRecorder()
        self.ui.setupUi(self)
        self.setWindowTitle("Student Face Recorder")

        # 设置默认学生ID
        self.default_student_id = "100066997"

        # 隐藏存储成功提示消息
        self.hide_label_2()

        # 初始化摄像头和视频流
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.recording = False
        self.recording_time = 0
        self.max_recording_time = 5000  # 5秒自动停止
        self.auto_stop_timer = None
        self.video_writer = None

        # 初始化进度条
        self.progress_bar = QtWidgets.QProgressBar(self.ui.centralwidget)
        self.progress_bar.setGeometry(QtCore.QRect(100, 400, 600, 20))
        self.progress_bar.setMaximum(self.max_recording_time)  # 设置最大值为录制时间
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)

        # 初始化按钮功能
        self.ui.pushButton_3.clicked.connect(self.start_recording)  # 开始
        self.ui.pushButton_2.clicked.connect(self.stop_recording)   # 停止
        self.ui.pushButton.clicked.connect(self.exit)              # 退出

        # 初始化视频显示区域
        self.video_label = QLabel(self.ui.centralwidget)
        self.video_label.setGeometry(QtCore.QRect(100, 100, 600, 300))
        self.video_label.setStyleSheet("background-color: rgb(0, 0, 0);")
        self.video_label.setAlignment(Qt.AlignCenter)

        # 初始化拖动标志
        self.m_flag = False


        self.show()

    # 开始录制
    def start_recording(self):
        # 使用默认学生ID
        student_id = self.default_student_id

        # 重新点击start按钮时，隐藏Label_2
        self.hide_label_2()

        if not student_id:
            QMessageBox.warning(self, "Warning", "Please enter a valid Student ID")
            return

        # 检查数据库中是否已存在该学生ID的记录
        conn = sqlite3.connect("students.db")
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS student_faces (
                student_id TEXT PRIMARY KEY,
                video_path TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute("SELECT * FROM student_faces WHERE student_id = ?", (student_id,))
        if cursor.fetchone():
            reply = QMessageBox.question(
                self,
                "Record Exists",
                "This student ID already exists. Do you want to overwrite the existing record?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.No:
                conn.close()
                return
        conn.close()

        # 初始化摄像头
        # self.cap = cv2.VideoCapture("rtsp://admin:Xray@12345;@10.10.176.19:554/h264Preview_01_main")
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            QMessageBox.critical(self, "Error", "Unable to access the camera")
            return

        # 获取摄像头的分辨率
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 配置视频写入器
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        video_file_path = os.path.join("video", f'{student_id}.avi')  # 保存到 video 文件夹
        os.makedirs("video", exist_ok=True)  # 确保 video 文件夹存在
        self.video_writer = cv2.VideoWriter(video_file_path, fourcc, 20.0, (width, height))

        if not self.video_writer.isOpened():
            QMessageBox.critical(self, "Error", "Failed to create video writer")
            return

        self.timer.start(30)  # 设置定时器，每30ms更新一帧
        self.recording = True
        self.recording_time = 0
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        print("Recording started")

        # 设置自动停止定时器
        self.auto_stop_timer = QTimer()
        self.auto_stop_timer.timeout.connect(self.stop_recording)
        self.auto_stop_timer.start(self.max_recording_time)

    # 停止录制
    def stop_recording(self):
        if self.recording:
            self.timer.stop()
            if self.auto_stop_timer:
                self.auto_stop_timer.stop()
            if self.cap:
                self.cap.release()
                self.cap = None
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            self.recording = False
            self.progress_bar.setVisible(False)

            # 确保进度条达到100%
            self.progress_bar.setValue(self.max_recording_time)

            # 保存记录到数据库
            student_id = self.default_student_id
            video_file_path = os.path.join("video", f'{student_id}.avi')
            self.save_to_db(student_id, video_file_path)

    # 更新视频帧
    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            # 写入视频文件
            self.video_writer.write(frame)

            # 将OpenCV图像转换为QImage
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.video_label.setPixmap(QPixmap.fromImage(qt_img))

            # 更新录制时间和进度条
            self.recording_time += 40  # 每次更新增加40ms
            self.progress_bar.setValue(self.recording_time)

            # 如果录制时间超过最大值，自动停止
            if self.recording_time >= self.max_recording_time:
                self.stop_recording()

    # 关闭程序
    def exit(self):
        if self.recording:
            self.stop_recording()
        self.close()



    def save_to_db(self, student_id, file_path):
        try:
            # 获取当前本地时间（以指定时区，例如 'Asia/Shanghai'）
            local_tz = pytz.timezone('Asia/Dubai')  # 根据所在地调整时区
            local_time = datetime.now(local_tz)

            conn = sqlite3.connect("students.db")
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS student_faces (
                    student_id TEXT PRIMARY KEY,
                    video_path TEXT,
                    timestamp DATETIME
                )
                """
            )
            cursor.execute(
                """
                INSERT OR REPLACE INTO student_faces (student_id, video_path, timestamp)
                VALUES (?, ?, ?)
                """,
                (student_id, file_path, local_time.strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()
            conn.close()

            print(f"Record saved: {student_id}, {file_path}, {local_time}")
            self.show_label_2("Video recording completed!")
            # QMessageBox.information(self, "Success", "Record saved successfully!")
        except sqlite3.Error as e:
            self.show_label_2(f"Failed to save to database: {e}", color='red')
        finally:
            conn.close()

    def show_label_2(self, message, color="green", visible=True):
        """
        控制 label_2 的显示和隐藏，并设置消息内容和颜色。
        :param message: 要显示的消息
        :param color: 文本颜色，默认为绿色
        :param visible: 是否显示 label_2，默认为 True
        """
        self.ui.label_2.setText(message)
        self.ui.label_2.setStyleSheet(f"font: 75 16pt 'Microsoft JhengHei UI'; color: {color};")  # 设置颜色
        self.ui.label_2.setVisible(visible)

    def hide_label_2(self):
        """
        隐藏 label_2。
        """
        self.ui.label_2.setVisible(False)

    # 拖动窗口
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and not self.isMaximized():
            self.m_flag = True
            self.m_Position = event.globalPos() - self.pos()
            event.accept()
            self.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))

    def mouseMoveEvent(self, mouse_event):
        if QtCore.Qt.LeftButton and self.m_flag:
            self.move(mouse_event.globalPos() - self.m_Position)
            mouse_event.accept()

    def mouseReleaseEvent(self, mouse_event):
        self.m_flag = False
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))

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