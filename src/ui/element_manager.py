import os
import json
import uuid
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
    QListWidgetItem, QPushButton, QLineEdit, QLabel,
    QFileDialog, QMessageBox, QWidget
)
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt, QSize
from utils.capture_tool import CaptureTool
from core.models import Element

class ElementManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("元素库管理")
        self.resize(600, 500)
        self.elements_dir = "data/elements"
        self.elements_file = os.path.join(self.elements_dir, "elements.json")
        self.elements = []
        
        self.setup_ui()
        self.load_elements()

    def setup_ui(self):
        layout = QHBoxLayout(self)

        # 左侧列表
        left_layout = QVBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(60, 60))
        self.list_widget.itemSelectionChanged.connect(self.on_selection_changed)
        left_layout.addWidget(QLabel("已保存元素:"))
        left_layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        self.btn_capture = QPushButton("截取新图")
        self.btn_capture.clicked.connect(self.start_capture)
        self.btn_delete = QPushButton("删除")
        self.btn_delete.clicked.connect(self.delete_element)
        btn_layout.addWidget(self.btn_capture)
        btn_layout.addWidget(self.btn_delete)
        left_layout.addLayout(btn_layout)

        # 右侧详情
        self.detail_panel = QWidget()
        right_layout = QVBoxLayout(self.detail_panel)
        self.img_preview = QLabel("预览图")
        self.img_preview.setFixedSize(200, 200)
        self.img_preview.setAlignment(Qt.AlignCenter)
        self.img_preview.setStyleSheet("border: 1px solid #ccc;")
        
        self.name_edit = QLineEdit()
        self.value_edit = QLineEdit()
        self.value_edit.setReadOnly(True)
        
        right_layout.addWidget(QLabel("预览:"))
        right_layout.addWidget(self.img_preview)
        right_layout.addWidget(QLabel("元素名称:"))
        right_layout.addWidget(self.name_edit)
        right_layout.addWidget(QLabel("数值/路径:"))
        right_layout.addWidget(self.value_edit)
        
        self.btn_save = QPushButton("保存修改")
        self.btn_save.clicked.connect(self.save_element_changes)
        right_layout.addWidget(self.btn_save)
        right_layout.addStretch()

        layout.addLayout(left_layout, 1)
        layout.addWidget(self.detail_panel)

    def load_elements(self):
        self.list_widget.clear()
        if os.path.exists(self.elements_file):
            with open(self.elements_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.elements = [Element(**d) for d in data]
        
        for el in self.elements:
            item = QListWidgetItem(el.name)
            item.setData(Qt.UserRole, el)
            if el.type == "image" and os.path.exists(el.value):
                item.setIcon(QIcon(el.value))
            self.list_widget.addItem(item)

    def start_capture(self):
        self.hide() # 隐藏管理器以便截图
        self.capture_tool = CaptureTool()
        self.capture_tool.finished.connect(self.on_capture_finished)
        self.capture_tool.start_capture()

    def on_capture_finished(self, pixmap):
        self.show()
        # 保存图片到 data/elements/
        el_id = str(uuid.uuid4())
        img_path = os.path.join(self.elements_dir, f"{el_id}.png")
        pixmap.save(img_path)
        
        # 创建新元素对象
        new_el = Element(
            id=el_id,
            name=f"新元素_{len(self.elements)+1}",
            type="image",
            value=img_path
        )
        self.elements.append(new_el)
        self.save_to_disk()
        self.load_elements()

    def save_to_disk(self):
        os.makedirs(self.elements_dir, exist_ok=True)
        with open(self.elements_file, 'w', encoding='utf-8') as f:
            json.dump([el.to_dict() for el in self.elements], f, indent=4, ensure_ascii=False)

    def on_selection_changed(self):
        items = self.list_widget.selectedItems()
        if not items: return
        el = items[0].data(Qt.UserRole)
        self.name_edit.setText(el.name)
        self.value_edit.setText(el.value)
        if el.type == "image" and os.path.exists(el.value):
            pix = QPixmap(el.value)
            self.img_preview.setPixmap(pix.scaled(200, 200, Qt.KeepAspectRatio))

    def save_element_changes(self):
        items = self.list_widget.selectedItems()
        if not items: return
        el = items[0].data(Qt.UserRole)
        el.name = self.name_edit.text()
        self.save_to_disk()
        self.load_elements()
        QMessageBox.information(self, "提示", "保存成功")

    def delete_element(self):
        items = self.list_widget.selectedItems()
        if not items: return
        el = items[0].data(Qt.UserRole)
        # 删除物理图片
        if el.type == "image" and os.path.exists(el.value):
            os.remove(el.value)
        self.elements.remove(el)
        self.save_to_disk()
        self.load_elements()
