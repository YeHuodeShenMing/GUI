import cv2
import sqlite3
import os
import time
from datetime import datetime
from threading import Thread
import threading
import queue
import webbrowser
from flask import Flask, render_template, Response, request, jsonify

app = Flask(__name__, template_folder='./frontend/templates')

# 全局录制控制变量，用于标识录制、暂停和停止状态
recording_control = {
    "recording": False,
    "paused": False,
    "stop_event": threading.Event()
}

# 全局摄像头配置，示例中配置了三个摄像头
global_config = {
    "cameras": [
        {
            "channel": 1,
            "rtspAddress": "rtsp://admin:Xray@12345;@10.10.176.19:554/h264Preview_01_main"
        },
        {
            "channel": 1,
            "rtspAddress": "rtsp://admin:Xray@12345;@10.10.185.191:554/h264Preview_01_main"
        },
        {
            "channel": 1,
            "rtspAddress": "rtsp://admin:Xray@12345;@10.10.176.17:554/h264Preview_01_main"
        }
    ]
}

# 全局变量，用于保存每个摄像头最新一帧图像（用于网页视频流）
latest_frames = {}  # key: 摄像头索引（0,1,2），value: frame (numpy array)
# 全局字典，用于每个摄像头录制时存放帧的队列
recording_queues = {}  # key: 摄像头索引，value: queue.Queue

def save_to_db(file_path):
    """保存录像文件记录到数据库"""
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
    print("Video saved to database.")

def camera_capture_thread(camera_config, camera_index):
    """
    为每个摄像头启动采集线程，不断读取帧：
    1. 更新全局最新帧（用于网页显示）
    2. 如果正在录制，则将帧放入对应队列（用于录制保存）
    """
    cap = cv2.VideoCapture(camera_config["rtspAddress"])
    # 为了保证流畅显示，设置一个较低的分辨率（也可根据需要调整）
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue
        # 更新最新帧（网页端读取该帧进行显示）
        latest_frames[camera_index] = frame

        # 若正在录制，则将帧放入录制队列
        if recording_control["recording"]:
            if camera_index in recording_queues:
                try:
                    recording_queues[camera_index].put(frame, timeout=0.01)
                except queue.Full:
                    # 队列满了就跳过该帧
                    pass
        time.sleep(0.03)  # 控制帧率，可根据实际情况调整

def record_camera(camera_index, video_path, resolution="1080p"):
    """
    录制线程：从对应的队列中取出帧，写入视频文件。
    支持暂停（暂停时不写入）和停止控制
    """
    resolutions = {"1080p": (1920, 1080), "2k": (2560, 1440)}
    width, height = resolutions.get(resolution, (1920, 1080))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(video_path, fourcc, 20.0, (width, height))
    
    start_time = time.time()
    print(f"Recording started for Camera {camera_index+1}")
    while recording_control["recording"] and not recording_control["stop_event"].is_set():
        # 暂停时不写入帧
        if recording_control["paused"]:
            time.sleep(0.1)
            continue
        try:
            frame = recording_queues[camera_index].get(timeout=0.1)
        except queue.Empty:
            continue
        # 若摄像头采集分辨率与录制分辨率不同，则需要调整帧大小
        frame = cv2.resize(frame, (width, height))
        video_writer.write(frame)
        elapsed_time = time.time() - start_time
        print(f"Camera {camera_index+1} recording... {elapsed_time:.2f} seconds", end="\r")
    video_writer.release()
    print(f"\nRecording finished for Camera {camera_index+1}.")
    save_to_db(video_path)

def generate_frames(camera_index):
    """
    网页视频流生成器：不断从全局最新帧中读取数据，将其编码为 JPEG 并通过 multipart 格式传输
    """
    while True:
        frame = latest_frames.get(camera_index)
        if frame is None:
            time.sleep(0.1)
            continue
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.05)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/single_capture')
def single_capture():
    return render_template('single_capture.html')

@app.route('/long_recording')
def long_recording():
    return render_template('long_recording.html', cameras=global_config["cameras"])

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/start', methods=['POST'])
def start():
    """
    接收开始录制请求：
    1. 将录制状态置为 True 并清除停止标记
    2. 为每个摄像头初始化录制队列，并启动录制线程
    """
    data = request.json
    resolution = data.get('resolution', "1080p")
    
    recording_control["recording"] = True
    recording_control["paused"] = False
    recording_control["stop_event"].clear()
    
    for i, camera in enumerate(global_config["cameras"]):
        # 生成唯一的视频文件路径
        video_path = f"videos/Camera{i+1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        # 为当前摄像头创建一个录制队列
        recording_queues[i] = queue.Queue(maxsize=200)
        t = Thread(target=record_camera, args=(i, video_path, resolution))
        t.start()
    
    return jsonify({"status": "Recording started"})

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    """
    根据前端传入的 action 控制录制状态：暂停、恢复或结束
    """
    data = request.json
    action = data.get("action")
    if action == "pause":
        recording_control["paused"] = True
        return jsonify({"status": "Recording paused"})
    elif action == "resume":
        recording_control["paused"] = False
        return jsonify({"status": "Recording resumed"})
    elif action == "finish":
        recording_control["stop_event"].set()
        recording_control["recording"] = False
        return jsonify({"status": "Recording stopped"})
    else:
        return jsonify({"status": "Invalid action"})

@app.route('/check_camera_status')
def check_camera_status():
    status_list = []
    for camera in global_config["cameras"]:
        cap = cv2.VideoCapture(camera["rtspAddress"])
        status = cap.isOpened()
        cap.release()
        status_list.append(status)
    print("Camera status:", status_list)
    return jsonify({"status": status_list})

@app.route('/video_feed/<int:camera>')
def video_feed(camera):
    if 0 < camera <= len(global_config["cameras"]):
        # 注意：这里 camera 的传入值为 1,2,3，因此内部索引为 camera-1
        return Response(generate_frames(camera-1), mimetype='multipart/x-mixed-replace; boundary=frame')
    return "Invalid camera number", 404

@app.route('/save_camera_config', methods=['POST'])
def save_camera_config():
    data = request.json
    print("Received camera config data:", data)
    
    if len(global_config["cameras"]) < 3:
        global_config["cameras"].extend([{} for _ in range(3 - len(global_config["cameras"]))])
    
    for i, config in enumerate(data):
        if i < 3:
            global_config["cameras"][i] = config

    print("Updated global camera configuration:", global_config["cameras"])
    return jsonify({
        "status": "success",
        "message": "Camera configurations updated in global dictionary.",
        "data": global_config
    })

@app.route('/get_camera_config', methods=['GET'])
def get_camera_config():
    return jsonify({
        "status": "success",
        "data": global_config
    })

def start_server():
    print("Starting server on http://127.0.0.1:5000")
    app.run(debug=True, use_reloader=False)

if __name__ == "__main__":
    os.makedirs("videos", exist_ok=True)
    
    # 启动每个摄像头的采集线程（负责不断从摄像头读取数据）
    for i, cam in enumerate(global_config["cameras"]):
        t = Thread(target=camera_capture_thread, args=(cam, i))
        t.daemon = True
        t.start()
    
    print("Camera capture threads started.")
    
    # 检查摄像头连接情况
    print("Checking camera connections...")
    for i, cam in enumerate(global_config["cameras"]):
        cap = cv2.VideoCapture(cam["rtspAddress"])
        if cap.isOpened():
            print(f"Camera {i+1} ✅ Connected")
            cap.release()
        else:
            print(f"Camera {i+1} ❌ Connection failed")
    
    # 启动 Flask 服务器线程，并自动打开网页
    server_thread = threading.Thread(target=start_server)
    server_thread.start()
    
    webbrowser.open("http://127.0.0.1:5000")
