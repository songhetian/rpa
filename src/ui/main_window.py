import sys
import os
import json
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QListWidget, QListWidgetItem, QPushButton, 
    QLabel, QFrame, QSplitter, QStatusBar,
    QToolBar, QAbstractItemView, QLineEdit, QFormLayout,
    QSpinBox, QComboBox, QMessageBox, QFileDialog, QMenu, QInputDialog,
    QTreeWidget, QTreeWidgetItem, QStyle, QTabWidget, QTextEdit, QSystemTrayIcon, QDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QAction

from core.models import ActionStep, AutomationScript, Trigger
from ui.element_manager import ElementManagerDialog
from core.executor import ScriptExecutor
from core.trigger_manager import TriggerManager

class TriggerPanel(QWidget):
    """触发任务面板：管理定时和快捷键"""
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        layout = QVBoxLayout(self)
        
        self.list = QListWidget()
        self.refresh()
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("添加触发器")
        add_btn.clicked.connect(self.add_trigger)
        del_btn = QPushButton("删除选中")
        del_btn.clicked.connect(self.delete_trigger)
        
        btn_layout.addWidget(add_btn); btn_layout.addWidget(del_btn)
        layout.addWidget(QLabel("<b>已配置的自动触发规则:</b>"))
        layout.addWidget(self.list)
        layout.addLayout(btn_layout)

    def refresh(self):
        self.list.clear()
        for t in self.manager.triggers:
            status = "已开启" if t.enabled else "已禁用"
            desc = f"[{t.type.upper()}] {t.name} -> {status}"
            item = QListWidgetItem(desc)
            item.setData(Qt.UserRole, t)
            self.list.addItem(item)

    def add_trigger(self):
        dlg = TriggerEditDialog(self)
        if dlg.exec():
            new_t = dlg.get_trigger()
            self.manager.triggers.append(new_t)
            self.manager.save_triggers()
            self.refresh()

    def delete_trigger(self):
        idx = self.list.currentRow()
        if idx >= 0:
            self.manager.triggers.pop(idx)
            self.manager.save_triggers()
            self.refresh()

class TriggerEditDialog(QDialog):
    """触发器编辑弹窗"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置自动触发规则")
        self.resize(400, 300)
        l = QFormLayout(self)
        
        self.name = QLineEdit("每日日报任务")
        self.type = QComboBox(); self.type.addItems(["time", "hotkey"])
        self.script = QLineEdit(); self.script.setPlaceholderText("选择要运行的脚本...")
        self.val = QLineEdit("09:00"); self.val.setPlaceholderText("时间(09:00) 或 快捷键(<ctrl>+r)")
        
        btn_file = QPushButton("...")
        btn_file.clicked.connect(self.pick_script)
        
        l.addRow("任务名称:", self.name)
        l.addRow("触发类型:", self.type)
        script_l = QHBoxLayout(); script_l.addWidget(self.script); script_l.addWidget(btn_file)
        l.addRow("执行脚本:", script_l)
        l.addRow("触发配置:", self.val)
        
        ok = QPushButton("保存"); ok.clicked.connect(self.accept)
        l.addRow(ok)

    def pick_script(self):
        p, _ = QFileDialog.getOpenFileName(self, "选择脚本", "data/scripts", "*.json")
        if p: self.script.setText(p)

    def get_trigger(self):
        t_type = self.type.currentText()
        config = {"time": self.val.text()} if t_type == "time" else {"key": self.val.text()}
        return Trigger(name=self.name.text(), type=t_type, script_path=self.script.text(), config=config)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gemini RPA Pro - 影刀增强版")
        self.resize(1400, 900)
        
        # 初始化管理器
        self.trigger_manager = TriggerManager()
        self.trigger_manager.trigger_fired.connect(self.auto_run_script)
        
        self.setup_ui()
        self.setup_tray()

    def setup_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        main_l = QVBoxLayout(central)
        h_split = QSplitter(Qt.Horizontal)

        # 1. 左侧 Tab (组件库 + 变量 + 触发器)
        self.left_tabs = QTabWidget()
        self.left_tabs.addTab(self.create_action_lib(), "指令库")
        self.left_tabs.addTab(TriggerPanel(self.trigger_manager), "任务触发")
        h_split.addWidget(self.left_tabs)

        # 2. 中间 编辑器 (省略，同之前)
        mid_w = QWidget(); mid_v = QVBoxLayout(mid_w)
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["指令步骤", "参数"])
        mid_v.addWidget(QLabel("<b>工作流编排</b>")); mid_v.addWidget(self.tree)
        h_split.addWidget(mid_w)

        # 3. 右侧 属性 (省略，同之前)
        right_w = QWidget(); right_w.setMinimumWidth(350); self.right_v = QVBoxLayout(right_w)
        self.prop_form = QFormLayout(); self.prop_container = QWidget(); self.prop_container.setLayout(self.prop_form)
        self.right_v.addWidget(QLabel("<b>参数配置</b>")); self.right_v.addWidget(self.prop_container); self.right_v.addStretch()
        h_split.addWidget(right_w)

        main_l.addWidget(h_split)
        
        # 4. 日志
        self.log_box = QTextEdit(); self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        main_l.addWidget(self.log_box)
        
        self.setup_toolbar()

    def setup_tray(self):
        self.tray = QSystemTrayIcon(self.style().standardIcon(QStyle.SP_ComputerIcon), self)
        self.tray.setToolTip("Gemini RPA 后台运行中")
        menu = QMenu()
        show_act = menu.addAction("显示主界面"); show_act.triggered.connect(self.show)
        quit_act = menu.addAction("退出程序"); quit_act.triggered.connect(sys.exit)
        self.tray.setContextMenu(menu)
        self.tray.show()

    def create_action_lib(self):
        lib = QListWidget(); s = self.style()
        actions = [("打开网页", "open_url"), ("点击", "click"), ("输入", "input"), ("设置日期", "set_datetime"), ("获取文本", "get_text")]
        for n, tid in actions:
            item = QListWidgetItem(s.standardIcon(QStyle.SP_FileIcon), n)
            item.setData(Qt.UserRole, tid); lib.addItem(item)
        lib.setDragEnabled(True); return lib

    def auto_run_script(self, path):
        """由触发器自动调用的运行接口"""
        self.log(f"⏰ 触发器激活: 正在自动运行脚本 {os.path.basename(path)}")
        try:
            script = AutomationScript.load(path)
            self.executor = ScriptExecutor(script)
            self.executor.log_signal.connect(lambda m, _: self.log(m))
            self.executor.start()
        except Exception as e: self.log(f"自动运行失败: {str(e)}")

    def log(self, msg):
        self.log_box.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def setup_toolbar(self):
        tb = self.addToolBar("Main")
        tb.addAction(QAction("💾 保存", self, triggered=lambda: None)) # 省略具体逻辑
        tb.addAction(QAction("▶️ 运行", self, triggered=lambda: None))

    # 当点击关闭按钮时，隐藏到托盘而不是退出
    def closeEvent(self, event):
        if self.tray.isVisible():
            self.hide()
            self.tray.showMessage("RPA 运行中", "程序已最小化到托盘，定时任务持续有效。", QSystemTrayIcon.Information, 2000)
            event.ignore()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow(); window.show()
    sys.exit(app.exec())