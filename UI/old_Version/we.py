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
import utils.process_video as process_video
import re

class UI_main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = main_flexible_ocr_ui.Ui_StudentFaceRecorder()
        self.ui.setupUi(self)
        self.setWindowTitle("Student Face Recorder")

        # 设置默认学生ID
        self.current_id = None

        # 在类初始化中添加一个布尔标志变量
        self.warning_printed = False  # 用于标记是否已打印警告

        self.ui.label_2.setAlignment(Qt.AlignCenter)  # 设置内容居中

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
        self.progress_bar = self.ui.progressBar
        self.progress_bar.setMaximum(self.max_recording_time)  # 设置最大值为录制时间
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)

        # 初始化按钮功能
        self.ui.pushButton_3.clicked.connect(self.start_recording)  # 开始
        self.ui.pushButton_2.clicked.connect(self.stop_recording)   # 停止
        self.ui.pushButton.clicked.connect(self.exit)              # 退出

        # 初始化视频显示区域
        self.ui.video_label.setAlignment(Qt.AlignCenter)

        # 初始化拖动标志
        self.m_flag = False

        # 连接信号和槽
        self.ui.checkBox.stateChanged.connect(self.on_checkbox_state_changed)

        self.show()

    def start_recording(self):
        self.hide_label_2()

        if self.recording:
            self.stop_recording()

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            QMessageBox.critical(self, "Error", "Unable to access the camera")
            return

        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self.timer.start(30)
        self.recording = True
        self.recording_time = 0
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # 每次开始录制时，重置 current_id
        self.current_id = None

        # 检查复选框是否被选中
        if self.ui.checkBox.isChecked():
            # 如果复选框被选中，从 QLineEdit 获取学生ID
            self.current_id = self.ui.lineEdit.text().strip()
            if not self.current_id:
                self.show_label_2("No valid Student ID found in the input field.", color="red")
                self.cap.release()
                return
        else:
            # 如果复选框未被选中，执行 OCR 逻辑
            frame_count = 0
            frame = None
            while frame_count < 10:
                ret, frame = self.cap.read()
                if not ret:
                    print(f"Skipping invalid frame at position {frame_count + 1}")
                    frame_count += 1
                    continue
                frame_count += 1

            if frame is None:
                self.cap.release()
                self.show_label_2("Unable to capture frames", color="red")
                return

            student_id, annotated_frame = process_video.process_frame(frame)  # 假设 video.process_frame 是一个外部函数
            if not student_id:
                self.show_label_2("Failed to recognize Student ID.\n Please try again.", color="red")
                self.cap.release()
                return

            self.current_id = self.extract_student_id(student_id)
            if not self.current_id:
                self.show_label_2("No valid Student ID found. Please check the input.", color="red")
                self.cap.release()
                return

            if not self.exam_student_ID(self.current_id):  # 用户选择“不覆盖”，直接返回
                self.cap.release()
                return

        # 配置视频写入器
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        video_file_path = os.path.join("video", f'{self.current_id}.avi')
        os.makedirs("video", exist_ok=True)
        self.video_writer = cv2.VideoWriter(video_file_path, fourcc, 20.0, (width, height))

        if not self.video_writer.isOpened():
            QMessageBox.critical(self, "Error", "Failed to create video writer")
            return

        self.auto_stop_timer = QTimer()
        self.auto_stop_timer.timeout.connect(self.stop_recording)
        self.auto_stop_timer.start(self.max_recording_time)

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

            # 确保进度条达到100%
            self.progress_bar.setValue(self.max_recording_time)

            # 保存记录到数据库
            student_id = self.current_id
            if student_id:
                video_file_path = os.path.join("video", f'{student_id}.avi')
                self.save_to_db(student_id, video_file_path)

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret and self.video_writer:
            # 写入视频文件
            self.video_writer.write(frame)

            # 将OpenCV图像转换为QImage
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.ui.video_label.setPixmap(QPixmap.fromImage(qt_img))

            # 更新录制时间和进度条
            self.recording_time += 40  # 每次更新增加40ms
            self.progress_bar.setValue(self.recording_time)

            # 如果录制时间超过最大值，自动停止
            if self.recording_time >= self.max_recording_time:
                self.stop_recording()

            # 重置标志变量，因为读取和写入正常
            self.warning_printed = False
        else:
            # 仅打印一次警告信息
            if not self.warning_printed:
                print("Warning: Video writer is not initialized or frame capture failed.")
                self.warning_printed = True

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
        except sqlite3.Error as e:
            self.show_label_2(f"Failed to save to database: {e}", color='red')
        finally:
            conn.close()

    def show_label_2(self, message, color="green", visible=True):
        self.ui.label_2.setText(message)
        self.ui.label_2.setStyleSheet(f"font: 75 16pt 'Microsoft JhengHei UI'; color: {color};")
        self.ui.label_2.setVisible(visible)

    def hide_label_2(self):
        self.ui.label_2.setVisible(False)

    def extract_student_id(self, text):
        text = text.strip()
        matches = re.findall