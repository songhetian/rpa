import time
import json
import os
import threading
from datetime import datetime
from pynput import keyboard
from PySide6.QtCore import QObject, Signal

class TriggerManager(QObject):
    """触发器后台引擎：处理定时任务和全局快捷键"""
    trigger_fired = Signal(str) # 发送需要运行的脚本路径

    def __init__(self):
        super().__init__()
        self.triggers = []
        self.path = "data/triggers.json"
        self.is_running = True
        self.load_triggers()
        
        # 启动定时检查线程
        self.timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self.timer_thread.start()
        
        # 快捷键监听
        self.hk_listener = None
        self._update_hotkeys()

    def load_triggers(self):
        if os.path.exists(self.path):
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                from core.models import Trigger
                self.triggers = [Trigger(**d) for d in data]

    def save_triggers(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump([t.to_dict() for t in self.triggers], f, indent=4, ensure_ascii=False)
        self._update_hotkeys()

    def _timer_loop(self):
        """每分钟检查一次定时任务"""
        while self.is_running:
            now = datetime.now().strftime("%H:%M")
            for t in self.triggers:
                if t.enabled and t.type == "time":
                    if t.config.get("time") == now:
                        # 简单的一天一次逻辑
                        self.trigger_fired.emit(t.script_path)
            time.sleep(60)

    def _update_hotkeys(self):
        """更新全局快捷键监听"""
        if self.hk_listener: self.hk_listener.stop()
        
        mapping = {}
        for t in self.triggers:
            if t.enabled and t.type == "hotkey" and t.config.get("key"):
                # 示例: '<ctrl>+<alt>+r'
                mapping[t.config["key"]] = lambda p=t.script_path: self.trigger_fired.emit(p)
        
        if mapping:
            self.hk_listener = keyboard.GlobalHotKeys(mapping)
            self.hk_listener.start()
