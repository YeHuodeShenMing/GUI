from PyQt5.QtWidgets import *
import numpy as np
import utils.process_video as process_video

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
        student_id, annotated_frame = process_video.process_frame(frame)
        self.recognition_done.emit(student_id, annotated_frame)

