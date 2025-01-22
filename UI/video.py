import cv2
import easyocr
import numpy as np

def process_frame(frame):
    """
    对单帧图像进行 OCR 识别，筛选白色背景上的黑色数字区域。
    :param frame: 图像帧
    :return: 识别的学生ID（字符串），以及带标注的图像帧
    """
    try:
        # 转换为灰度图像
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 自适应阈值处理，突出白色背景上的黑色数字
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

        # 形态学操作优化数字区域
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        binary = cv2.dilate(binary, kernel, iterations=2)
        binary = cv2.erode(binary, kernel, iterations=1)

        # 检测轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # 找到最大轮廓并获取边界框
        if not contours:
            raise ValueError("No contours detected")
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)

        # 裁剪感兴趣区域（ROI）
        cropped_roi = frame[y:y + h, x:x + w]

        # 使用 EasyOCR 对 ROI 进行文字识别
        reader = easyocr.Reader(['en'])
        result = reader.readtext(cropped_roi)

        if result:
            # 提取 OCR 结果
            student_id = result[0][-2]

            # 在图像上绘制矩形框和文字
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
            cv2.putText(frame, student_id, (x, y - 10), font, 1, (0, 255, 0), 2, cv2.LINE_AA)

            return student_id.strip(), frame
        else:
            return None, None

    except Exception as e:
        print("Error in OCR processing:", e)
        return None, None



if __name__ == '__main__':
    import cv2

    # 初始化摄像头（如果需要从摄像头获取帧）
    cap = cv2.VideoCapture(0)  # 如果从摄像头获取输入
    # cap = cv2.VideoCapture("./images/ppt123.mp4")  # 如果从视频文件获取输入

    if not cap.isOpened():
        print("Error: Unable to access the camera or video file.")
        exit()

    frame_number = 10  # 指定需要处理的帧编号
    frame_count = 0
    target_frame = None

    while frame_count < frame_number:
        ret, frame = cap.read()
        if not ret:
            print(f"Error: Unable to read frame {frame_count + 1}.")
            exit()
        frame_count += 1
        if frame_count == frame_number:
            target_frame = frame
            break

    # 释放摄像头资源
    cap.release()

    # 检查是否成功获取目标帧
    if target_frame is None:
        print("Error: Failed to capture the target frame.")
        exit()

    # 调用 OCR 函数处理目标帧
    student_id, annotated_frame = process_frame(target_frame)

    if student_id:
        # 显示带有标注的帧
        cv2.imshow("Annotated Frame", annotated_frame)
        print(f"Recognized Student ID: {student_id}")
        print("Press any key to close the window...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print("Failed to extract student ID or no valid image region detected.")
