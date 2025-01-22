def start_recording(self):
    # 初始化摄像头
    self.cap = cv2.VideoCapture(0)
    if not self.cap.isOpened():
        QMessageBox.critical(self, "Error", "Unable to access the camera")
        return

    # 获取摄像头分辨率
    width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # 提取第10帧进行OCR识别
    frame_count = 0
    student_id = None
    while frame_count < 10:
        ret, frame = self.cap.read()
        if not ret:
            QMessageBox.critical(self, "Error", "Unable to capture frame")
            return
        frame_count += 1

    # 调用OCR识别学生ID
    student_id, annotated_frame = process_frame(frame)
    if not student_id:
        QMessageBox.critical(self, "Error", "Failed to recognize Student ID")
        return

    # 保存识别结果到数据库（模拟保存逻辑）
    print(f"Recognized Student ID: {student_id}")
    self.save_to_database(student_id)

    # 配置视频写入器
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    video_file_path = os.path.join("video", f'{student_id}.avi')
    os.makedirs("video", exist_ok=True)
    self.video_writer = cv2.VideoWriter(video_file_path, fourcc, 20.0, (width, height))

    if not self.video_writer.isOpened():
        QMessageBox.critical(self, "Error", "Failed to create video writer")
        return

    # 开始录制
    self.timer.start(30)
    self.recording = True
    self.recording_time = 0
    self.progress_bar.setVisible(True)
    self.progress_bar.setValue(0)

    print("Recording started")

    # 设置自动停止定时器
    self.auto_stop_timer = QTimer()
    self.auto_stop_timer.timeout.connect(self.stop_recording)
    self.auto_stop_timer.start(self.max_recording_time)
