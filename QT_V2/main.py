import sys
import cv2
import time
import os
import sqlite3
from datetime import datetime
from threading import Event

from PyQt5 import QtCore, QtGui, QtWidgets, uic

# 定义全局摄像头配置（可修改为实际地址）
CAMERA_CONFIGS = [
    {"channel": 1, "rtspAddress": "rtsp://admin:Xray@12345;@10.10.176.19:554/h264Preview_01_main"},
    {"channel": 1, "rtspAddress": "rtsp://admin:Xray@12345;@10.10.185.191:554/h264Preview_01_main"},
    {"channel": 1, "rtspAddress": "rtsp://admin:Xray@12345;@10.10.176.17:554/h264Preview_01_main"}  # 0 表示本地摄像头
]

# 用于录制控制
class RecorderControl:
    def __init__(self):
        self.recording = False
        self.paused = False
        self.stop_event = Event()

# 视频捕获与录制线程
class VideoThread(QtCore.QThread):
    change_pixmap_signal = QtCore.pyqtSignal(QtGui.QImage)
    update_device_signal = QtCore.pyqtSignal(bool)       # True 表示已连接
    update_recording_signal = QtCore.pyqtSignal(str)       # 状态：idle, recording, paused

    def __init__(self, cam_config, resolution="1080p", parent=None):
        super().__init__(parent)
        self.cam_config = cam_config
        self.resolution = resolution
        self.cap = None
        self.record_writer = None
        self.recorder_control = RecorderControl()
        self.video_path = ""
        self.fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.fps = 20.0
        # 分辨率设置
        self.resolutions = {"1080p": (1920, 1080), "2k": (2560, 1440)}
        self.width, self.height = self.resolutions.get(resolution, (1920, 1080))
        
    def run(self):
        # 尝试打开摄像头
        self.cap = cv2.VideoCapture(self.cam_config["rtspAddress"])
        connected = self.cap.isOpened()
        self.update_device_signal.emit(connected)
        if not connected:
            return
        
        # 若录制，创建保存文件
        if self.recorder_control.recording:
            folder = "videos"
            os.makedirs(folder, exist_ok=True)
            self.video_path = os.path.join(folder, f"Camera_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
            self.record_writer = cv2.VideoWriter(self.video_path, self.fourcc, self.fps, (self.width, self.height))
        
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break

            # 若分辨率需要设置
            frame = cv2.resize(frame, (self.width, self.height))

            # 录制逻辑：检查是否暂停或停止
            if self.recorder_control.recording and not self.recorder_control.paused:
                if self.record_writer is not None:
                    self.record_writer.write(frame)
                self.update_recording_signal.emit("recording")
            elif self.recorder_control.paused:
                self.update_recording_signal.emit("paused")
            else:
                self.update_recording_signal.emit("idle")

            # 将 frame 转换为 QImage 并发射信号用于界面显示
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
            p = convert_to_Qt_format.scaled(600, 400, QtCore.Qt.KeepAspectRatio)
            self.change_pixmap_signal.emit(p)

            # 检查停止事件
            if self.recorder_control.stop_event.is_set():
                break

            self.msleep(30)
        # 释放资源
        if self.cap:
            self.cap.release()
        if self.record_writer:
            self.record_writer.release()
        # 保存录制记录到数据库
        if self.video_path:
            self.save_to_db(self.video_path)
        self.update_recording_signal.emit("idle")
        
    def start_recording(self, resolution):
        # 更新分辨率设置
        self.resolution = resolution
        self.width, self.height = self.resolutions.get(resolution, (1920, 1080))
        self.recorder_control.recording = True
        self.recorder_control.paused = False
        self.recorder_control.stop_event.clear()
        # 若摄像头已打开，则在 run 中自动创建 record_writer
        if self.cap is None:
            self.start()
    
    def pause_recording(self):
        self.recorder_control.paused = True

    def resume_recording(self):
        self.recorder_control.paused = False

    def finish_recording(self):
        self.recorder_control.stop_event.set()
        self.recorder_control.recording = False

    def save_to_db(self, file_path):
        conn = sqlite3.connect("videos.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recordings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("INSERT INTO recordings (file_path) VALUES (?)", (file_path,))
        conn.commit()
        conn.close()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main.ui", self)

        # 定时器用于更新录制计时
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.seconds = 0

        # 创建三个视频线程
        self.threads = []
        self.init_video_threads()

        # 绑定按钮事件
        self.pushButton_start.clicked.connect(self.start_recording)
        self.pushButton_stop.clicked.connect(self.toggle_pause)
        self.pushButton_finish.clicked.connect(self.finish_recording)
        self.pushButton_exit.clicked.connect(self.close)

        # 初始按钮状态
        self.recording = False

    def init_video_threads(self):
        # 初始化三个线程，每个线程连接对应的信号槽更新界面显示和指示灯
        self.thread1 = VideoThread(CAMERA_CONFIGS[0], self.comboBox_resolution.currentText())
        self.thread1.change_pixmap_signal.connect(self.update_image1)
        self.thread1.update_device_signal.connect(lambda status: self.update_indicator(self.label_device1, status))
        self.thread1.update_recording_signal.connect(lambda status: self.update_indicator(self.label_recording1, status))
        
        self.thread2 = VideoThread(CAMERA_CONFIGS[1], self.comboBox_resolution.currentText())
        self.thread2.change_pixmap_signal.connect(self.update_image2)
        self.thread2.update_device_signal.connect(lambda status: self.update_indicator(self.label_device2, status))
        self.thread2.update_recording_signal.connect(lambda status: self.update_indicator(self.label_recording2, status))
        
        self.thread3 = VideoThread(CAMERA_CONFIGS[2], self.comboBox_resolution.currentText())
        self.thread3.change_pixmap_signal.connect(self.update_image3)
        self.thread3.update_device_signal.connect(lambda status: self.update_indicator(self.label_device3, status))
        self.thread3.update_recording_signal.connect(lambda status: self.update_indicator(self.label_recording3, status))
        
        self.threads = [self.thread1, self.thread2, self.thread3]

    def update_indicator(self, label, status):
        # 根据状态更新指示灯颜色：设备连接状态或录制状态
        if label.objectName().startswith("label_device"):
            # 设备连接：连接成功为绿色，否则红色
            if status:
                label.setStyleSheet("background-color: #4ade80; border-radius:7px;")
            else:
                label.setStyleSheet("background-color: red; border-radius:7px;")
        else:
            # 录制状态：idle 红色，recording 绿色闪烁，paused 黄色
            if status == "idle":
                label.setStyleSheet("background-color: red; border-radius:7px;")
            elif status == "recording":
                label.setStyleSheet("background-color: #4ade80; border-radius:7px;")
            elif status == "paused":
                label.setStyleSheet("background-color: #fbc02d; border-radius:7px;")

    def update_image1(self, qt_img):
        self.label_camera1.setPixmap(QtGui.QPixmap.fromImage(qt_img))

    def update_image2(self, qt_img):
        self.label_camera2.setPixmap(QtGui.QPixmap.fromImage(qt_img))

    def update_image3(self, qt_img):
        self.label_camera3.setPixmap(QtGui.QPixmap.fromImage(qt_img))

    def start_recording(self):
        if self.recording:
            return
        self.recording = True
        self.seconds = 0
        self.label_timer.setText("00:00")
        resolution = self.comboBox_resolution.currentText()
        # 启动所有线程的录制逻辑
        for thread in self.threads:
            thread.start_recording(resolution)
        self.timer.start(1000)

    def toggle_pause(self):
        if not self.recording:
            return
        # 按钮文本在 Stop 和 Continue 之间切换
        if self.pushButton_stop.text().strip().lower() == "stop":
            # 暂停录制
            for thread in self.threads:
                thread.pause_recording()
            self.pushButton_stop.setText("Continue")
            self.timer.stop()
        else:
            # 恢复录制
            for thread in self.threads:
                thread.resume_recording()
            self.pushButton_stop.setText("Stop")
            self.timer.start(1000)

    def finish_recording(self):
        if not self.recording:
            return
        # 通知所有线程结束录制
        for thread in self.threads:
            thread.finish_recording()
        self.timer.stop()
        self.recording = False
        self.pushButton_stop.setText("Stop")
        self.label_timer.setText("00:00")
        self.seconds = 0
        QtWidgets.QMessageBox.information(self, "提示", "Recording finished!")

    def update_timer(self):
        self.seconds += 1
        m, s = divmod(self.seconds, 60)
        self.label_timer.setText(f"{m:02d}:{s:02d}")

    def closeEvent(self, event):
        # 结束线程
        for thread in self.threads:
            thread.finish_recording()
            thread.wait()
        event.accept()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
