from flask import Flask, request, jsonify
import cv2
import sqlite3
import os
import datetime
import pytz

app = Flask(__name__)

# 数据库初始化
def init_db():
    conn = sqlite3.connect("videos.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            video_path TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# 视频录制逻辑
def record_video(student_id, resolution, duration):
    # 设置视频分辨率
    resolutions = {
        "1080p": (1920, 1080),
        "2k": (2560, 1440)
    }
    width, height = resolutions.get(resolution, (640, 480))

    # 初始化摄像头
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise Exception("无法打开摄像头")

    # 设置视频编码器和输出路径
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    video_path = f"videos/{student_id}.avi"
    os.makedirs("videos", exist_ok=True)
    video_writer = cv2.VideoWriter(video_path, fourcc, 20.0, (width, height))

    # 开始录制
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    start_time = datetime.datetime.now()
    while (datetime.datetime.now() - start_time).seconds < duration:
        ret, frame = cap.read()
        if ret:
            video_writer.write(frame)
        else:
            break

    # 释放资源
    cap.release()
    video_writer.release()

    # 保存到数据库
    save_to_db(student_id, video_path)

# 保存到数据库
def save_to_db(student_id, video_path):
    conn = sqlite3.connect("videos.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO video_records (student_id, video_path) VALUES (?, ?)
    """, (student_id, video_path))
    conn.commit()
    conn.close()

# 后端接口
@app.route('/start_recording', methods=['POST'])
def start_recording():
    data = request.json
    student_id = data.get("student_id")
    resolution = data.get("resolution", "1080p")
    duration = data.get("duration", 5) * 60  # 转换为秒

    try:
        record_video(student_id, resolution, duration)
        return jsonify({"status": "success", "message": "Recording completed"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    app.run(debug=True)