from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import cv2
from PyQt5.QtCore import QTimer
import sys


# 主界面1
class UI_main_1(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = main_ui.Ui_MainWidget()
        self.ui.setupUi(self)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.ui.pushButton.clicked.connect(lambda: self.go_to_main_2())
        self.ui.pushButton_2.clicked.connect(lambda: self.exit())
        self.show()

    # 跳转到主界面2
    def go_to_main_2(self):
        self.win = UI_main_2()
        self.close()

    # 关闭程序
    def exit(self):
        self.close()

    # 拖动
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.isMaximized() == False:
            self.m_flag = True
            self.m_Position = event.globalPos() - self.pos()  # 获取鼠标相对窗口的位置
            event.accept()
            self.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))  # 更改鼠标图标

    def mouseMoveEvent(self, mouse_event):
        if QtCore.Qt.LeftButton and self.m_flag:
            self.move(mouse_event.globalPos() - self.m_Position)  # 更改窗口位置
            mouse_event.accept()

    def mouseReleaseEvent(self, mouse_event):
        self.m_flag = False
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))


# 主界面2
class UI_main_2(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = dialog_ui.Ui_Dialog()
        self.ui.setupUi(self)
        self.img_path = None
        self.videoName = ''
        self.cap = None
        # 初始化 QTimer
        self.timer = QTimer()
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.ui.pushButton.clicked.connect(lambda: self.open_video())
        self.ui.pushButton_2.clicked.connect(lambda: self.video_show())
        self.show()

    # 读取图片,将路径存入txt文件中
    def openimage(self):
        imgName, imgType = QFileDialog.getOpenFileName(self, "打开图片", "", "*.jpg;;*.png;*.mp4;All Files(*)")
        jpg = QtGui.QPixmap(imgName).scaled(self.ui.label_2.width(), self.ui.label_2.height())
        self.ui.label_2.setPixmap(jpg)
        self.img_path = imgName

    def img_show(self):
        print(self.img_path)
        # detect_main.process_image_simple(img)
        # img_path=(r'D:\my_homework\yolov5_infer\0001.jpg')
        # jpg = QtGui.QPixmap(img_path).scaled(self.ui.show_output.width(), self.ui.show_output.height())
        # self.ui.show_output.setPixmap(jpg)

    def update_frame(self):
        ret, image = self.cap.read()
        print(ret)
        if ret:
            # 图像转换及显示逻辑
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            vedio_img = QImage(image.data, image.shape[1], image.shape[0], QImage.Format_RGB888)
            self.ui.label_2.setPixmap(QPixmap(vedio_img))
            self.ui.label_2.setScaledContents(True)  # 自适应窗口
            self.ui.label_2.update()
        else:
            self.timer.stop()
            self.cap.release()

    def open_video(self):
        videoName, videoType = QFileDialog.getOpenFileName(self, "打开视频", "", "*.mp4;All Files(*)")
        self.videoName = videoName
        self.cap = cv2.VideoCapture(self.videoName)

    def video_show(self):
        self.timer.start()  # 假设每30毫秒更新一次，根据需要调整
        self.timer.timeout.connect(self.update_frame)

    def exit(self):
        self.win = UI_main_2()
        self.close()

    # 拖动
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.isMaximized() == False:
            self.m_flag = True
            self.m_Position = event.globalPos() - self.pos()  # 获取鼠标相对窗口的位置
            event.accept()
            self.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))  # 更改鼠标图标

    def mouseMoveEvent(self, mouse_event):
        if QtCore.Qt.LeftButton and self.m_flag:
            self.move(mouse_event.globalPos() - self.m_Position)  # 更改窗口位置
            mouse_event.accept()

    def mouseReleaseEvent(self, mouse_event):
        self.m_flag = False
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = UI_main_1()
    sys.exit(app.exec_())