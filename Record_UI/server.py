import cv2
import sqlite3
import os
import time
from datetime import datetime

import webbrowser
import threading

# 运行服务器
from flask import Flask, render_template, request, jsonify, Response
app = Flask(__name__, template_folder='./frontend/templates')

def start_recording(video_path, resolution="1080p"):
    resolutions = {"1080p": (1920, 1080), "2k": (2560, 1440)}
    width, height = resolutions.get(resolution, (1920, 1080))
    
    cap = cv2.VideoCapture("rtsp://admin:Xray@12345;@10.10.185.191:554/h264Preview_01_main")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    video_writer = cv2.VideoWriter(video_path, fourcc, 20.0, (width, height))
    
    start_time = time.time()
    print("Recording started...")
    while cap.isOpened():
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

# 视频流路由
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


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


def start_server():
    """启动 Flask 服务器，并自动打开网页"""
    print("Starting server on http://127.0.0.1:5000")
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:5000")
    #TODO
    app.run(debug=True, use_reloader=False)  # 禁止自动重启
    # app.run(debug=True)
    
if __name__ == "__main__":
    os.makedirs("videos", exist_ok=True)
    file_name = f"videos/recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"

    # 启动 Flask 服务器的线程
    server_thread = threading.Thread(target=start_server)
    server_thread.start()

    # 启动视频录制
    start_recording(file_name, resolution="2k")