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
import video
import re

class UI_main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = main_flexible_ocr_ui.Ui_StudentFaceRecorder()
        self.ui.setupUi(self)
        self.setWindowTitle("Student Face Recorder")
        # 设置窗口图标
        self.setWindowIcon(QIcon("./cropped-logo.png"))  

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

        # self.cap = cv2.VideoCapture(0)
        # self.cap = cv2.VideoCapture("rtsp://admin:Xray@12345;@10.10.185.79:554/h264Preview_01_main")
        
        # self.cap = cv2.VideoCapture("rtsp://admin:Xray@12345;@10.10.186.178:554/h264Preview_02_main")
        
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
            
            
            # 检查 Student ID 是否重复
            if not self.exam_student_ID(self.current_id):
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

            student_id, annotated_frame = video.process_frame(frame)  # 假设 video.process_frame 是一个外部函数
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

    # 检查Student ID 是否在库中
    def exam_student_ID(self, student_id):
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
                self.current_id = None  # 清除当前ID
                return False
        conn.close()
        return True


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

            # 确保进度条达到100%
            self.progress_bar.setValue(self.max_recording_time)

            # 保存记录到数据库
            student_id = self.current_id
            if student_id:
                video_file_path = os.path.join("video", f'{student_id}.avi')
                self.save_to_db(student_id, video_file_path)



    # 更新视频帧的逻辑
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
            
            # 清空 QLineEdit 输入框
            self.ui.lineEdit.clear()

            # 将 QCheckBox 恢复为未选中状态
            self.ui.checkBox.setChecked(False)
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
    
    def extract_student_id(self, text):
        """
        提取可能的学生ID。允许格式为纯数字或包含字母和数字的组合。
        :param text: 输入OCR提取的文本
        :return: 提取的学生ID或None
        """
        text = text.strip()
        # 修改正则匹配：允许字母和数字组合，长度为9-12
        matches = re.findall(r'\b[A-Za-z0-9]{9,12}\b', text)
        return matches[0] if matches else None
    
    def on_checkbox_state_changed(self, state): 
        """
        当 QCheckBox 的状态发生变化时，调用此函数
        """
        if state == 2:  # Qt.Checked 的值为 2
            student_id_input = self.ui.lineEdit
            self.current_id = student_id_input.text().strip()

            self.start_recording()

        else:
            # 当 QCheckBox 未被选中时，清空 QLineEdit 的内容
            self.ui.lineEdit.clear()


from PyQt5.QtCore import QThread, pyqtSignal

class RecognitionThread(QThread):
    recognition_done = pyqtSignal(str, np.ndarray)  # 信号：传递学生ID和标注帧

    def __init__(self, cap):
        super().__init__()
        self.cap = cap

    def run(self):
        frame_count = 0
        while frame_count < 10:
            ret, frame = self.cap.read()
            if not ret:
                self.recognition_done.emit(None, None)
                return
            frame_count += 1

        # 调用OCR识别学生ID
        student_id, annotated_frame = video.process_frame(frame)
        self.recognition_done.emit(student_id, annotated_frame)



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