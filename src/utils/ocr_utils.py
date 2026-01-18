import ddddocr
import os

class CaptchaSolver:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CaptchaSolver, cls).__new__(cls)
            # 这里的 show_ad=False 是为了保持控制台整洁
            cls._instance.ocr = ddddocr.DdddOcr(show_ad=False)
        return cls._instance

    def solve(self, image_path):
        """识别本地图片的文字"""
        if not os.path.exists(image_path):
            return ""
        with open(image_path, 'rb') as f:
            img_bytes = f.read()
        return self.ocr.classification(img_bytes)

    def solve_bytes(self, img_bytes):
        """直接识别字节流图片"""
        return self.ocr.classification(img_bytes)
