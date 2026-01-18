from pynput import mouse, keyboard
from PySide6.QtCore import QObject, Signal
import time

class GlobalRecorder(QObject):
    """全局动作录制器：捕捉鼠标点击和键盘输入"""
    action_captured = Signal(dict) # 发送捕捉到的动作数据

    def __init__(self):
        super().__init__()
        self.mouse_listener = None
        self.kb_listener = None
        self.is_recording = False
        self.last_time = 0

    def start(self):
        self.is_recording = True
        self.last_time = time.time()
        
        # 启动鼠标监听
        self.mouse_listener = mouse.Listener(on_click=self.on_click)
        self.mouse_listener.start()
        
        # 启动键盘监听
        self.kb_listener = keyboard.Listener(on_press=self.on_press)
        self.kb_listener.start()

    def stop(self):
        self.is_recording = False
        if self.mouse_listener: self.mouse_listener.stop()
        if self.kb_listener: self.kb_listener.stop()

    def on_click(self, x, y, button, pressed):
        if pressed and self.is_recording:
            # 记录点击动作
            action = {
                "type": "click",
                "mode": "图像识别", # 录制时默认为坐标/图像模式
                "target": f"{x},{y}",
                "note": f"点击坐标 ({x}, {y})"
            }
            self.action_captured.emit(action)

    def on_press(self, key):
        if not self.is_recording: return
        try:
            k = key.char # 普通字符
        except AttributeError:
            k = str(key) # 特殊按键
            
        action = {
            "type": "input",
            "mode": "键盘模拟",
            "text": k,
            "note": f"按键: {k}"
        }
        self.action_captured.emit(action)
