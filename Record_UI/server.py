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

def get_video_capture(resolution="1080p"):
    resolutions = {"1080p": (1920, 1080), "2k": (2560, 1440)}
    width, height = resolutions.get(resolution, (1920, 1080))
    cap = cv2.VideoCapture("rtsp://admin:Xray@12345;@10.10.185.191:554/h264Preview_01_main")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    return cap

def play_video_stream(resolution="1080p"):
    """
    单独实现视频流播放，不进行录制，
    在未点击 start 之前可调用此函数进行预览。
    """
    cap = get_video_capture(resolution)
    if not cap.isOpened():
        print("无法打开视频流！")
        return
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        cv2.imshow("Video Preview", frame)
        # 按 'q' 键退出预览
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()

def start_recording(video_path, resolution="1080p"):
    recording_control["recording"] = True
    recording_control["paused"] = False
    recording_control["stop_event"].clear()
    
    resolutions = {"1080p": (1920, 1080), "2k": (2560, 1440)}
    width, height = resolutions.get(resolution, (1920, 1080))
    
    cap = cv2.VideoCapture("rtsp://admin:Xray@12345;@10.10.185.191:554/h264Preview_01_main")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    video_writer = cv2.VideoWriter(video_path, fourcc, 20.0, (width, height))
    
    start_time = time.time()
    print("Recording started...")
    while cap.isOpened() and not recording_control["stop_event"].is_set():
        # 当处于暂停状态时等待
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
def generate_frames():
    cap = cv2.VideoCapture("rtsp://admin:Xray@12345;@10.10.185.191:554/h264Preview_01_main")
    if not cap.isOpened():
        raise ValueError("无法打开视频流！")

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
    return render_template('long_recording.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')


# 前端请求响应API
@app.route('/start', methods=['POST'])
def start():
    data = request.json
    resolution = data.get('resolution', "1080p")

    # 生成唯一的视频文件路径
    video_path = f"videos/recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    os.makedirs("videos", exist_ok=True)

    # 启动录制任务线程
    Thread(target=start_recording, args=(video_path, resolution)).start()

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

# 视频流路由
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')



@app.route('/save_camera_config', methods=['POST'])
def save_camera_config():
    data = request.json
    conn = sqlite3.connect("settings.db")
    cursor = conn.cursor()
    
    # 清空现有配置
    cursor.execute("DELETE FROM cameras")
    
    # 插入新的配置
    for config in data:
        cursor.execute("""
            INSERT INTO cameras (rtsp_address, channel) VALUES (?, ?)
        """, (config['networkPath'], config['channel']))
    
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Camera configurations saved."})


def start_server():
    """启动 Flask 服务器，并自动打开网页"""
    print("Starting server on http://127.0.0.1:5000")
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:5000")
    #TODO
    app.run(debug=True, use_reloader=False)  # 禁止自动重启
    
if __name__ == "__main__":
    os.makedirs("videos", exist_ok=True)
    file_name = f"videos/recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"

    # 启动 Flask 服务器的线程
    server_thread = threading.Thread(target=start_server)
    server_thread.start()

    # 启动视频显示
    #TODO 这里可以写一个显示视频函数，而不是录制函数
    # start_recording(file_name, resolution="2k")
    generate_frames()