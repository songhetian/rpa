from PySide6.QtWidgets import QWidget, QApplication, QRubberBand
from PySide6.QtCore import Qt, QRect, QPoint, Signal, QSize
from PySide6.QtGui import QPainter, QColor, QScreen, QPixmap
import sys

class CaptureTool(QWidget):
    """全屏截图工具：允许用户拖拽选择区域 (适配 DPI)"""
    finished = Signal(QPixmap)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setCursor(Qt.CrossCursor)
        self.start_pos = None
        self.end_pos = None
        self.full_screen_pixmap = None

    def start_capture(self):
        # 捕捉物理屏幕内容
        screen = QApplication.primaryScreen()
        self.full_screen_pixmap = screen.grabWindow(0)
        
        # 适配 DPI：将窗口大小设置为逻辑大小，但背景使用原始物理像素图
        rect = screen.geometry()
        self.setGeometry(rect)
        self.showFullScreen()
        self.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        # 绘制背景底图
        painter.drawPixmap(0, 0, self.full_screen_pixmap)
        # 绘制半透明黑色遮罩
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        
        if self.start_pos and self.end_pos:
            rect = QRect(self.start_pos, self.end_pos).normalized()
            # 挖空选中区域（恢复原图亮度和清晰度）
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(rect, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            # 绘制选中区域边框
            painter.setPen(QPen(QColor(0, 174, 255), 2))
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
            self.end_pos = event.pos()
            self.update()

    def mouseMoveEvent(self, event):
        if self.start_pos:
            self.end_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.start_pos:
            rect = QRect(self.start_pos, self.end_pos).normalized()
            self.close()
            
            if rect.width() > 2 and rect.height() > 2:
                # 注意：rect 是逻辑坐标，需要转换为物理坐标进行裁剪
                device_ratio = self.screen().devicePixelRatio()
                physical_rect = QRect(
                    rect.x() * device_ratio,
                    rect.y() * device_ratio,
                    rect.width() * device_ratio,
                    rect.height() * device_ratio
                )
                cropped = self.full_screen_pixmap.copy(physical_rect)
                self.finished.emit(cropped)
            self.start_pos = None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

from PySide6.QtGui import QPen # 确保导入了 QPen

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    tool = CaptureTool()
    tool.finished.connect(lambda p: p.save("captured.png"))
    tool.start_capture()
    sys.exit(app.exec())
