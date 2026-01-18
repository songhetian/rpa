import cv2
import numpy as np
from PIL import ImageGrab
import os

class ImageMatcher:
    @staticmethod
    def capture_screen(region=None):
        """截取屏幕，返回 OpenCV 格式图像 (BGR)"""
        screenshot = ImageGrab.grab(bbox=region)
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    @staticmethod
    def find_template(template_path, threshold=0.8, region=None):
        """
        在屏幕上查找模板图片
        :return: (x, y) 中心坐标，如果没找到则返回 None
        """
        if not os.path.exists(template_path):
            return None

        screen = ImageMatcher.capture_screen(region)
        template = cv2.imread(template_path)
        
        if template is None:
            return None

        res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        if max_val >= threshold:
            # 获取中心坐标
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return (center_x, center_y)
        
        return None

    @staticmethod
    def wait_for_image(template_path, timeout=10, threshold=0.8):
        """循环检测图片直到出现或超时"""
        import time
        start_time = time.time()
        while time.time() - start_time < timeout:
            pos = ImageMatcher.find_template(template_path, threshold)
            if pos:
                return pos
            time.sleep(0.5)
        return None
