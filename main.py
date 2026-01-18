import sys
import os

# 将 src 目录添加到 Python 路径，确保导入正常
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # 设置全局样式 (可选)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
