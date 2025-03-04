import sys
import cv2
import time
import os
import sqlite3
import threading
import pytz
from datetime import datetime
from threading import Event

from PyQt5 import QtCore, QtGui, QtWidgets, uic
from onvif import ONVIFCamera

# ----------------- 全局参数 -----------------
DELAY_BEFORE_MOTION = 15         # 10分钟后触发机动动作（测试时设为30秒）
RECORD_DURATION = 5              # 每段动作期间录制5分钟（测试时设为5秒）
COMPENSATION_DURATION = 1        # 补偿动作1秒

# ----------------- 摄像头配置 -----------------
CAMERA_CONFIGS = [
    {
        "name": "Camera1",
        "channel": 1,
        "rtspAddress": "rtsp://admin:Xray@12345;@10.10.185.191:554/h264Preview_01_main",
        "onvif_ip": "10.10.185.191",
        "onvif_port": 8000
    },
    {
        "name": "Camera2",
        "channel": 1,
        "rtspAddress": "rtsp://admin:Xray@12345;@10.10.176.19:554/h264Preview_01_main",
        "onvif_ip": "10.10.176.19",
        "onvif_port": 8000
    },
    {
        "name": "Camera3",
        "channel": 1,
        "rtspAddress": "rtsp://admin:Xray@12345;@10.10.176.17:554/h264Preview_01_main",
        "onvif_ip": "10.10.176.17",
        "onvif_port": 8000
    }
]
ONVIF_USERNAME = "admin"
ONVIF_PASSWORD = "Xray@12345;"

# ----------------- PTZ 控制函数 -----------------
def move(ptz, profile_token, pan=0.0, tilt=0.0, zoom=0.0, duration=1):
    """
    利用 onvif 发送连续移动指令，然后停止
    """
    try:
        move_req = ptz.create_type('ContinuousMove')
        move_req.ProfileToken = profile_token
        move_req.Velocity = {
            'PanTilt': {
                'space': 'http://www.onvif.org/ver10/tptz/PanTiltSpaces/VelocityGenericSpace',
                'x': pan,
                'y': tilt
            },
            'Zoom': {
                'space': 'http://www.onvif.org/ver10/tptz/ZoomSpaces/VelocityGenericSpace',
                'x': zoom
            }
        }
        ptz.ContinuousMove(move_req)
        time.sleep(duration)
        ptz.Stop({'ProfileToken': profile_token})
    except Exception as e:
        print(f"PTZ move error: {e}")

def ptz_sequence(cam_name, ptz_info):
    """
    针对单个摄像头执行机动动作（各摄像头动作可单独设置）
    """
    ptz = ptz_info["ptz"]
    profile_token = ptz_info["profile_token"]
    print(f"开始对 {cam_name} 执行机动动作")
    
    if cam_name == "Camera1":
        # Camera1：左右和上下各一次
        move(ptz, profile_token, pan=0.1, duration=COMPENSATION_DURATION)
        time.sleep(RECORD_DURATION)
        move(ptz, profile_token, pan=-0.1, duration=COMPENSATION_DURATION)
        
        move(ptz, profile_token, pan=-0.1, duration=COMPENSATION_DURATION)
        time.sleep(RECORD_DURATION)
        move(ptz, profile_token, pan=0.1, duration=COMPENSATION_DURATION)
        
        move(ptz, profile_token, tilt=0.1, duration=COMPENSATION_DURATION)
        time.sleep(RECORD_DURATION)
        move(ptz, profile_token, tilt=-0.1, duration=COMPENSATION_DURATION)
        
        move(ptz, profile_token, tilt=-0.1, duration=COMPENSATION_DURATION)
        time.sleep(RECORD_DURATION)
        move(ptz, profile_token, tilt=0.1, duration=COMPENSATION_DURATION)
        
        move(ptz, profile_token, zoom=0.1, duration=RECORD_DURATION)
        move(ptz, profile_token, zoom=-0.1, duration=COMPENSATION_DURATION)
        move(ptz, profile_token, zoom=-0.1, duration=COMPENSATION_DURATION)
        move(ptz, profile_token, zoom=0.1, duration=RECORD_DURATION)
    
    elif cam_name == "Camera2":
        # Camera2：左右、上下、放大后回正
        move(ptz, profile_token, pan=0.1, duration=COMPENSATION_DURATION)
        time.sleep(RECORD_DURATION)
        move(ptz, profile_token, pan=-0.1, duration=COMPENSATION_DURATION)
        
        # move(ptz, profile_token, pan=-0.1, duration=COMPENSATION_DURATION)
        # time.sleep(RECORD_DURATION)
        # move(ptz, profile_token, pan=0.1, duration=COMPENSATION_DURATION)
        
        # move(ptz, profile_token, tilt=0.1, duration=COMPENSATION_DURATION)
        # time.sleep(RECORD_DURATION)
        # move(ptz, profile_token, tilt=-0.1, duration=COMPENSATION_DURATION)
        
        # move(ptz, profile_token, tilt=-0.1, duration=COMPENSATION_DURATION)
        # time.sleep(RECORD_DURATION)
        # move(ptz, profile_token, tilt=0.1, duration=COMPENSATION_DURATION)
        
        # move(ptz, profile_token, zoom=0.1, duration=RECORD_DURATION)
        # move(ptz, profile_token, zoom=-0.1, duration=COMPENSATION_DURATION)
        # move(ptz, profile_token, zoom=-0.1, duration=COMPENSATION_DURATION)
        # move(ptz, profile_token, zoom=0.1, duration=RECORD_DURATION)
    
    elif cam_name == "Camera3":
        # Camera3：左右、上下、放大缩小
        move(ptz, profile_token, pan=0.1, duration=COMPENSATION_DURATION)
        time.sleep(RECORD_DURATION)
        move(ptz, profile_token, pan=-0.1, duration=COMPENSATION_DURATION)
        
        # move(ptz, profile_token, pan=-0.1, duration=COMPENSATION_DURATION)
        # time.sleep(RECORD_DURATION)
        # move(ptz, profile_token, pan=0.1, duration=COMPENSATION_DURATION)
        
        # move(ptz, profile_token, tilt=0.1, duration=COMPENSATION_DURATION)
        # time.sleep(RECORD_DURATION)
        # move(ptz, profile_token, tilt=-0.1, duration=COMPENSATION_DURATION)
        
        # move(ptz, profile_token, tilt=-0.1, duration=COMPENSATION_DURATION)
        # time.sleep(RECORD_DURATION)
        # move(ptz, profile_token, tilt=0.1, duration=COMPENSATION_DURATION)
        
        # move(ptz, profile_token, zoom=0.1, duration=RECORD_DURATION)
        # move(ptz, profile_token, zoom=-0.1, duration=COMPENSATION_DURATION)
        # move(ptz, profile_token, zoom=-0.1, duration=COMPENSATION_DURATION)
        # move(ptz, profile_token, zoom=0.1, duration=RECORD_DURATION)
    
    else:
        # 默认动作
        move(ptz, profile_token, pan=0.1, duration=COMPENSATION_DURATION)
        time.sleep(RECORD_DURATION)
        move(ptz, profile_token, pan=-0.1, duration=COMPENSATION_DURATION)
        move(ptz, profile_token, tilt=0.1, duration=COMPENSATION_DURATION)
        time.sleep(RECORD_DURATION)
        move(ptz, profile_token, tilt=-0.1, duration=COMPENSATION_DURATION)
        move(ptz, profile_token, zoom=0.1, duration=RECORD_DURATION)
        move(ptz, profile_token, zoom=-0.1, duration=COMPENSATION_DURATION)
    
    print(f"{cam_name} 的机动动作执行完毕")

def perform_motion_sequence(ptz_services):
    """
    为每个摄像头启动独立线程执行 PTZ 动作
    """
    threads = []
    for cam_name, ptz_info in ptz_services.items():
        t = threading.Thread(target=ptz_sequence, args=(cam_name, ptz_info), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    print("所有摄像头的机动动作执行完毕")

def initialize_ptz_services():
    """
    初始化所有摄像头的 onvif ptz 服务，返回字典 {CameraName: {ptz, profile_token}}
    """
    ptz_services = {}
    for cam in CAMERA_CONFIGS:
        try:
            cam_obj = ONVIFCamera(cam["onvif_ip"], cam["onvif_port"], ONVIF_USERNAME, ONVIF_PASSWORD)
            media_service = cam_obj.create_media_service()
            profiles = media_service.GetProfiles()
            profile = profiles[0]
            ptz = cam_obj.create_ptz_service()
            ptz_services[cam["name"]] = {"ptz": ptz, "profile_token": profile.token}
            print(f"{cam['name']} onvif 初始化成功")
        except Exception as e:
            print(f"{cam['name']} onvif 初始化失败: {e}")
    return ptz_services

# ----------------- 视频录制相关类 -----------------
class RecorderControl:
    def __init__(self):
        self.recording = False
        self.paused = False
        self.stop_event = Event()

class VideoThread(QtCore.QThread):
    change_pixmap_signal = QtCore.pyqtSignal(QtGui.QImage)
    update_device_signal = QtCore.pyqtSignal(bool)       # True 表示已连接
    update_recording_signal = QtCore.pyqtSignal(str)       # 状态：idle, recording, paused

    def __init__(self, cam_config, resolution="2k", parent=None):
        super().__init__(parent)
        self.cam_config = cam_config
        self.resolution = resolution
        self.cap = None
        self.record_writer = None
        self.recorder_control = RecorderControl()
        self.video_path = ""
        self.fourcc = cv2.VideoWriter_fourcc(*'H264')
        self.fps = 20.0
        self.resolutions = {"1080p": (1920, 1080), "2k": (2560, 1440)}
        self.width, self.height = self.resolutions.get(resolution, (1920, 1080))

    def run(self):
        self.cap = cv2.VideoCapture(self.cam_config["rtspAddress"])
        connected = self.cap.isOpened()
        self.update_device_signal.emit(connected)
        if not connected:
            print(f"{self.cam_config.get('name')} 设备连接失败")
            return

        if self.recorder_control.recording:
            # 固定存储路径：videos/Camera1, videos/Camera2, videos/Camera3
            camera_name = self.cam_config.get("name", "Camera")
            camera_folder = os.path.join("videos", camera_name)
            os.makedirs(camera_folder, exist_ok=True)
            dubai_tz = pytz.timezone('Asia/Dubai')
            timestamp = datetime.now(dubai_tz).strftime('%Y%m%d_%H%M%S')
            file_ext = ".mp4"
            self.video_path = os.path.join(camera_folder, f"{camera_name}_{timestamp}{file_ext}")
            self.record_writer = cv2.VideoWriter(self.video_path, self.fourcc, self.fps, (self.width, self.height))

        failure_count = 0  # 连续失败计数器
        max_failures = 50  # 达到一定次数后重连

        while self.cap.isOpened() and not self.recorder_control.stop_event.is_set():
            ret, frame = self.cap.read()
            if not ret:
                failure_count += 1
                print(f"{self.cam_config.get('name')} 获取帧失败，失败次数：{failure_count}")
                if failure_count > max_failures:
                    print(f"{self.cam_config.get('name')} 连续失败次数过多，尝试重新初始化视频流")
                    self.cap.release()
                    time.sleep(2)  # 给摄像头恢复时间
                    self.cap = cv2.VideoCapture(self.cam_config["rtspAddress"])
                    if self.cap.isOpened():
                        print(f"{self.cam_config.get('name')} 重新初始化视频流成功")
                        failure_count = 0
                        continue
                    else:
                        print(f"{self.cam_config.get('name')} 重新初始化视频流失败")
                        time.sleep(1)
                        continue
                time.sleep(0.1)
                continue
            else:
                failure_count = 0

            frame = cv2.resize(frame, (self.width, self.height))
            if self.recorder_control.recording and not self.recorder_control.paused:
                if self.record_writer is not None:
                    self.record_writer.write(frame)
                self.update_recording_signal.emit("recording")
            elif self.recorder_control.paused:
                self.update_recording_signal.emit("paused")
            else:
                self.update_recording_signal.emit("idle")

            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
            p = convert_to_Qt_format.scaled(720, 600, QtCore.Qt.KeepAspectRatio)
            self.change_pixmap_signal.emit(p)
            self.msleep(30)
        if self.cap:
            self.cap.release()
        if self.record_writer:
            self.record_writer.release()
        if self.video_path:
            self.save_to_db(self.video_path)
        self.update_recording_signal.emit("idle")

    def start_recording(self, resolution):
        self.resolution = resolution
        self.width, self.height = self.resolutions.get(resolution, (1920, 1080))
        self.recorder_control.recording = True
        self.recorder_control.paused = False
        self.recorder_control.stop_event.clear()
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

# ----------------- 主窗口 -----------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main.ui", self)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.seconds = 0

        self.threads = []
        self.init_video_threads()

        self.ptz_services = initialize_ptz_services()

        # 按钮事件绑定（录制、暂停、结束、退出）
        self.pushButton_start.clicked.connect(self.start_recording)
        self.pushButton_stop.clicked.connect(self.toggle_pause)
        self.pushButton_finish.clicked.connect(self.finish_recording)
        self.pushButton_exit.clicked.connect(self.close)

        # 绑定 PTZ 控制事件——为每个摄像头分别绑定对应按钮和滑块
        # Camera1
        self.pushButton_up1.clicked.connect(lambda: self.ptz_move("Camera1", "up"))
        self.pushButton_down1.clicked.connect(lambda: self.ptz_move("Camera1", "down"))
        self.pushButton_left1.clicked.connect(lambda: self.ptz_move("Camera1", "left"))
        self.pushButton_right1.clicked.connect(lambda: self.ptz_move("Camera1", "right"))
        self.slider_zoom1.valueChanged.connect(lambda value: self.ptz_zoom("Camera1", value))
        # Camera2
        self.pushButton_up2.clicked.connect(lambda: self.ptz_move("Camera2", "up"))
        self.pushButton_down2.clicked.connect(lambda: self.ptz_move("Camera2", "down"))
        self.pushButton_left2.clicked.connect(lambda: self.ptz_move("Camera2", "left"))
        self.pushButton_right2.clicked.connect(lambda: self.ptz_move("Camera2", "right"))
        self.slider_zoom2.valueChanged.connect(lambda value: self.ptz_zoom("Camera2", value))
        # Camera3
        self.pushButton_up3.clicked.connect(lambda: self.ptz_move("Camera3", "up"))
        self.pushButton_down3.clicked.connect(lambda: self.ptz_move("Camera3", "down"))
        self.pushButton_left3.clicked.connect(lambda: self.ptz_move("Camera3", "left"))
        self.pushButton_right3.clicked.connect(lambda: self.ptz_move("Camera3", "right"))
        self.slider_zoom3.valueChanged.connect(lambda value: self.ptz_zoom("Camera3", value))

        self.recording = False

    def init_video_threads(self):
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
        if label.objectName().startswith("label_device"):
            if status:
                label.setStyleSheet("background-color: #4ade80; border-radius:7px;")
            else:
                label.setStyleSheet("background-color: red; border-radius:7px;")
        else:
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
        for thread in self.threads:
            thread.start_recording(resolution)
        self.timer.start(1000)

    def toggle_pause(self):
        if not self.recording:
            return
        if self.pushButton_stop.text().strip().lower() == "stop":
            for thread in self.threads:
                thread.pause_recording()
            self.pushButton_stop.setText("Continue")
            self.timer.stop()
        else:
            for thread in self.threads:
                thread.resume_recording()
            self.pushButton_stop.setText("Stop")
            self.timer.start(1000)

    def finish_recording(self):
        if not self.recording:
            return
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
        if self.seconds == DELAY_BEFORE_MOTION:
            # 启动独立线程执行PTZ机动动作，避免阻塞视频采集
            threading.Thread(target=self.start_motion_sequence, daemon=True).start()

    def start_motion_sequence(self):
        print("开始执行摄像头机动动作序列")
        perform_motion_sequence(self.ptz_services)

    def ptz_move(self, cam_name, direction):
        if cam_name not in self.ptz_services:
            print(f"{cam_name} PTZ 服务未初始化")
            return
        ptz_info = self.ptz_services[cam_name]
        pan = 0.0
        tilt = 0.0
        if direction == "up":
            tilt = 0.1
        elif direction == "down":
            tilt = -0.1
        elif direction == "left":
            pan = 0.1
        elif direction == "right":
            pan = -0.1
        move(ptz_info["ptz"], ptz_info["profile_token"], pan=pan, tilt=tilt, zoom=0.0, duration=1)

    def ptz_zoom(self, cam_name, slider_value):
        if cam_name not in self.ptz_services:
            print(f"{cam_name} PTZ 服务未初始化")
            return
        ptz_info = self.ptz_services[cam_name]
        zoom = (slider_value - 50) / 50 * 0.1
        move(ptz_info["ptz"], ptz_info["profile_token"], pan=0.0, tilt=0.0, zoom=zoom, duration=0.5)

    def closeEvent(self, event):
        for thread in self.threads:
            thread.finish_recording()
            thread.wait()
        event.accept()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
