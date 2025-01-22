import cv2
import easyocr
import numpy as np

def process_video_nth_frame(video_path, frame_number=10):
    """
    从视频中提取指定帧（默认第10帧），筛选白色背景上的黑色数字区域，并进行OCR识别。
    :param video_path: 视频文件路径
    :param frame_number: 要提取的帧编号，默认为第10帧
    :return: 识别的学生ID（字符串），以及带标注的指定帧图像
    """
    try:
        # 打开视频文件
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("Unable to open video file: {}".format(video_path))  # 无法打开视频文件

        # 跳过前 frame_number-1 帧
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number - 1)

        # 读取指定帧
        ret, frame = cap.read()
        if not ret:
            raise ValueError("Unable to read frame {} from the video".format(frame_number))  # 无法读取指定帧

        # 释放视频对象
        cap.release()

        # 转换为灰度图像
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 使用自适应阈值化处理，突出白色背景上的黑色数字[^11^]
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)  # 筛选白色背景上的黑色区域

        # 形态学操作：膨胀和腐蚀，优化数字区域[^8^]
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        binary = cv2.dilate(binary, kernel, iterations=2)
        binary = cv2.erode(binary, kernel, iterations=1)

        # 检测轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # 找到最大轮廓并获取其边界框
        if not contours:
            raise ValueError("No contours detected")  # 未检测到任何轮廓
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)

        # 裁剪感兴趣区域（ROI）
        cropped_roi = frame[y:y+h, x:x+w]

        # 使用EasyOCR对ROI进行文字识别
        reader = easyocr.Reader(['en'])
        result = reader.readtext(cropped_roi)

        if result:
            # 提取OCR结果
            student_id = result[0][-2]

            # 在原图上绘制绿色矩形框和文字
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
            cv2.putText(frame, student_id, (x, y-10), font, 1, (0, 255, 0), 2, cv2.LINE_AA)

            print("Recognized Student ID: {}".format(student_id))  # 打印识别的学生ID
            return student_id.strip(), frame
        else:
            print("OCR failed to recognize any text")  # OCR识别失败
            return None, None

    except Exception as e:
        print("Error: {}".format(e))  # 打印错误信息
        return None, None


if __name__ == '__main__':
    # 输入视频路径
    # video_path = r"./video/100066997.avi"
    video_path = r"./images/ppt123.mp4"

    # 调用函数处理视频
    student_id, annotated_frame = process_video_nth_frame(video_path)

    # 检查结果
    if student_id:
        # 显示标注的指定帧图像
        cv2.imshow("Annotated Frame", annotated_frame)
        print("Press any key to close the window...")  # 提示按任意键关闭窗口
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print("Failed to extract student ID or no valid image region detected")  # 未能成功提取学生ID或未检测到有效图像区域