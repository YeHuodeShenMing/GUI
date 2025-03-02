import cv2
import sqlite3
import os
import time
from datetime import datetime
from threading import Thread
import webbrowser
import threading

# 运行服务器
from flask import Flask, render_template, Response, request, jsonify
app = Flask(__name__, template_folder='./frontend/templates')

# 全局录制控制变量，使用 Event 控制停止，用布尔变量控制暂停状态
recording_control = {
    "recording": False,
    "paused": False,
    "stop_event": threading.Event()
}

# 全局字典用于存储摄像头配置以及录制信息
global_config = {
    "cameras": [{
                "channel": 1,
                "rtspAddress": "rtsp://admin:Xray@12345;@10.10.176.19:554/h264Preview_01_main"
                }, 
                {
                "channel": 1,
                "rtspAddress": "rtsp://admin:Xray@12345;@10.10.185.191:554/h264Preview_01_main"
                }, 
                {
                "channel": 1,
                "rtspAddress": "0"
                    
                 }],  
        # 用于存储最多三个摄像头的配置
        # "recordings": []          # 用于存储录像记录
}


def start_recording(video_path, camera_config, resolution="1080p"):
    recording_control["recording"] = True
    recording_control["paused"] = False
    recording_control["stop_event"].clear()
    
    resolutions = {"1080p": (1920, 1080), "2k": (2560, 1440)}
    width, height = resolutions.get(resolution, (1920, 1080))
    
    cap = cv2.VideoCapture(camera_config["rtspAddress"])
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(video_path, fourcc, 20.0, (width, height))
    
    start_time = time.time()
    print(f"Recording started for {camera_config['rtspAddress']}")
    while cap.isOpened() and not recording_control["stop_event"].is_set():
        if recording_control["paused"]:
            time.sleep(0.1)
            continue
        
        ret, frame = cap.read()
        if not ret:
            break
        video_writer.write(frame)
        elapsed_time = time.time() - start_time
        print(f"Recording... {elapsed_time:.2f} seconds", end="\r")
    
    cap.release()
    video_writer.release()
    print("\nRecording finished.")
    save_to_db(video_path)
    recording_control["recording"] = False

def save_to_db(file_path):
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


# 视频流生成器函数
def generate_frames(camera_config):
    cap = cv2.VideoCapture(camera_config["rtspAddress"])
    if not cap.isOpened():
        raise ValueError("无法打开视频: {camera_config['rtspAddress']}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 将帧转换为 JPEG 格式
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        # 生成视频流
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n') 

    cap.release()

# 网页跳转API
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


# 前端请求响应API
@app.route('/start', methods=['POST'])
def start():
    data = request.json
    resolution = data.get('resolution', "1080p")

    # 遍历所有摄像头，启动录制任务
    for i, camera in enumerate(global_config["cameras"]):
        # 生成唯一的视频文件路径
        video_path = f"videos/Camera{i+1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        Thread(target=start_recording, args=(video_path, camera, resolution)).start()

    return jsonify({"status": "Recording started"})

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
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
        return jsonify({"status": "Recording stopped"})
    else:
        return jsonify({"status": "Invalid action"})

# 检查摄像头连接情况
@app.route('/check_camera_status')
def check_camera_status():
    status_list = []
    for camera in global_config["cameras"]:
        if camera.get("rtspAddress"):
            cap = cv2.VideoCapture(camera["rtspAddress"])
            status = cap.isOpened()
            cap.release()
            status_list.append(status)
        else:
            status_list.append(False)
    print("Camera status:", status_list)
    return jsonify({"status": status_list})

# 视频流路由 多个摄像头视频流
@app.route('/video_feed/<int:camera>')
def video_feed(camera):
    if 0 < camera <= len(global_config["cameras"]):
        config = global_config["cameras"][camera-1]
        if not config.get("rtspAddress"):
            return "Camera not configured", 404
        try:
            def generate():
                cap = cv2.VideoCapture(config["rtspAddress"])
                while True:
                    ret, frame = cap.read()
                    if not ret: break
                    ret, buffer = cv2.imencode('.jpg', frame)
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')
        except Exception as e:
            return f"Error: {str(e)}", 500
    return "Invalid camera number", 404

# 将摄像头配置写入全局字典
@app.route('/save_camera_config', methods=['POST'])
def save_camera_config():
    data = request.json  # 期望 data 为一个列表，顺序依次对应 Camera1, Camera2, Camera3
    print("Received camera config data:", data)
    
    # 确保 global_config["cameras"] 至少有 3 个槽位，若不足则补充空字典
    if len(global_config["cameras"]) < 3:
        global_config["cameras"].extend([{} for _ in range(3 - len(global_config["cameras"]))])
    
    # 根据传入数据更新对应槽位，不清空其他槽位
    for i, config in enumerate(data):
        if i < 3:
            global_config["cameras"][i] = config

    print("Updated global camera configuration:", global_config["cameras"])
    return jsonify({
        "status": "success",
        "message": "Camera configurations updated in global dictionary.",
        "data": global_config
    })
    
# 常态化显示config
@app.route('/get_camera_config', methods=['GET'])
def get_camera_config():
    return jsonify({
        "status": "success",
        "data": global_config
    })



def start_server():
    """启动 Flask 服务器，并自动打开网页"""
    print("Starting server on http://127.0.0.1:5000")
    app.run(debug=True, use_reloader=False)  # 禁止自动重启
    
if __name__ == "__main__":
    os.makedirs("videos", exist_ok=True)

    # 启动时检测摄像头
    print("Checking camera connections...")
    for i, cam in enumerate(global_config["cameras"]):
        if cam.get("rtspAddress"):
            cap = cv2.VideoCapture(cam["rtspAddress"])
            if cap.isOpened():
                print(f"Camera {i+1} ✅ Connected")
                cap.release()
            else:
                print(f"Camera {i+1} ❌ Connection failed")

    # 启动 Flask 服务器的线程
    server_thread = threading.Thread(target=start_server)
    server_thread.start()
    
    webbrowser.open("http://127.0.0.1:5000")

    # 启动视频显示
    #TODO 这里可以写一个显示视频函数，而不是录制函数
    # start_recording(file_name, resolution="2k")
    # for i in global_config.get("carema"):
    #     generate_frames()