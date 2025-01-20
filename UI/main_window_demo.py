from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt
import cv2
import sys
import main_window_ui
import sqlite3
import os

class UI_main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = main_window_ui.Ui_StudentFaceRecorder()
        self.ui.setupUi(self)
        self.setWindowTitle("Student Face Recorder")
        # self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        # self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

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

        # 获取学生 ID 输入框
        self.student_id_input = self.ui.lineEdit

        self.show()

    # 开始录制
    def start_recording(self):
        student_id = self.student_id_input.text().strip()
        if not student_id:
            QMessageBox.warning(self, "Warning", "Please enter a valid Student ID")
            return

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
            QMessageBox.information(self, "Success", "Video recording completed!")

            # 保存记录到数据库
            student_id = self.student_id_input.text().strip()
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
            self.recording_time += 30  # 每次更新增加30ms
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
        conn = sqlite3.connect("students.db")
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT, video_path TEXT)"
        )
        cursor.execute("INSERT INTO students (student_id, video_path) VALUES (?, ?)", (student_id, file_path))
        conn.commit()
        conn.close()

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
    app = QApplication(sys.argv)
    win = UI_main()
    win.show()
    sys.exit(app.exec_())