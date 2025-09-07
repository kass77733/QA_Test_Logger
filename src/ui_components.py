import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QListWidget, QListWidgetItem, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QPixmap, QIcon

from utils import ImageUtils


class NotificationWidget(QFrame):
    """通知提示组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.hide)
    
    def initUI(self):
        """初始化UI"""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setStyleSheet("""
            background-color: #4CAF50;
            color: white;
            border-radius: 8px;
            padding: 15px;
            font-size: 18px;
            border: 3px solid #388E3C;
            margin: 10px;
        """)
        self.setMinimumHeight(80)
        self.setMaximumHeight(80)
        
        # 使用QMessageBox风格的布局
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(15, 10, 15, 10)
        self.layout.setSpacing(20)  # 增加间距
        
        # 添加大图标标签
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(40, 40)
        self.icon_label.setStyleSheet("font-size: 32px; font-weight: bold;")
        self.layout.addWidget(self.icon_label)
        
        # 添加消息标签
        self.label = QLabel()
        self.label.setStyleSheet("font-weight: bold; font-size: 18px; letter-spacing: 1px;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.layout.addWidget(self.label)
        
        # 添加关闭按钮
        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(30, 30)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                font-size: 20px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
                border-radius: 15px;
            }
        """)
        self.close_button.clicked.connect(self.hide)
        self.layout.addWidget(self.close_button)
        
        self.hide()
    
    def showMessage(self, message, duration=5000, type="success"):
        """显示通知消息"""
        # 确保消息不为空
        if not message:
            message = "操作完成"
            
        self.label.setText(message)
        
        # 根据消息类型设置不同的样式和图标
        if type == "success":
            self.setStyleSheet("""
                background-color: #4CAF50;
                color: white;
                border-radius: 8px;
                padding: 15px;
                font-size: 18px;
                border: 3px solid #388E3C;
                margin: 10px;
            """)
            self.icon_label.setText("✓")  # 成功图标
        elif type == "warning":
            self.setStyleSheet("""
                background-color: #FF9800;
                color: white;
                border-radius: 8px;
                padding: 15px;
                font-size: 18px;
                border: 3px solid #F57C00;
                margin: 10px;
            """)
            self.icon_label.setText("⚠")  # 警告图标
        elif type == "error":
            self.setStyleSheet("""
                background-color: #F44336;
                color: white;
                border-radius: 8px;
                padding: 15px;
                font-size: 18px;
                border: 3px solid #D32F2F;
                margin: 10px;
            """)
            self.icon_label.setText("✗")  # 错误图标
        
        # 显示通知
        self.show()
        self.raise_()  # 确保通知显示在最上层
        
        # 启动定时器
        self.timer.start(duration)


class ImageListWidget(QWidget):
    """图片列表组件，支持多张图片"""
    
    # 定义信号
    imagesChanged = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_paths = []
        self.initUI()
    
    def initUI(self):
        """初始化UI"""
        self.layout = QVBoxLayout(self)
        
        # 图片列表
        self.image_list = QListWidget()
        self.image_list.setIconSize(QSize(100, 100))
        self.image_list.setMaximumHeight(150)
        self.image_list.itemClicked.connect(self.onImageClicked)
        self.layout.addWidget(self.image_list)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 粘贴图片按钮
        self.paste_button = QPushButton("从剪贴板粘贴")
        button_layout.addWidget(self.paste_button)
        
        # 选择图片按钮
        self.select_button = QPushButton("选择图片文件")
        button_layout.addWidget(self.select_button)
        
        # 删除图片按钮
        self.delete_button = QPushButton("删除选中图片")
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self.deleteSelectedImage)
        button_layout.addWidget(self.delete_button)
        
        self.layout.addLayout(button_layout)
        
        # 图片预览
        self.preview_label = QLabel("选择图片查看预览")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(200)
        self.layout.addWidget(self.preview_label)
    
    def addImage(self, image_path):
        """添加图片到列表"""
        if not image_path or not os.path.exists(image_path):
            return
        
        # 添加到路径列表
        self.image_paths.append(image_path)
        
        # 创建列表项
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, image_path)
        
        # 加载缩略图
        pixmap = QPixmap(image_path)
        pixmap = pixmap.scaled(
            100, 100,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        item.setIcon(QIcon(pixmap))
        
        # 添加到列表
        self.image_list.addItem(item)
        
        # 发送信号
        self.imagesChanged.emit(self.image_paths)
    
    def setImages(self, image_paths):
        """设置图片列表"""
        # 清空当前列表
        self.image_list.clear()
        self.image_paths = []
        
        # 添加新图片
        for path in image_paths:
            if path and os.path.exists(path):
                self.addImage(path)
    
    def onImageClicked(self, item):
        """处理图片点击事件"""
        image_path = item.data(Qt.ItemDataRole.UserRole)
        
        if image_path and os.path.exists(image_path):
            # 加载图片
            pixmap = QPixmap(image_path)
            
            # 缩放图片以适应标签大小
            pixmap = pixmap.scaled(
                self.preview_label.width(), 
                self.preview_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.preview_label.setPixmap(pixmap)
            self.delete_button.setEnabled(True)
        else:
            self.preview_label.setText("图片不存在")
            self.delete_button.setEnabled(False)
    
    def deleteSelectedImage(self):
        """删除选中的图片"""
        current_item = self.image_list.currentItem()
        if not current_item:
            return
        
        # 获取图片路径
        image_path = current_item.data(Qt.ItemDataRole.UserRole)
        
        # 从列表中移除
        row = self.image_list.row(current_item)
        self.image_list.takeItem(row)
        
        # 从路径列表中移除
        if image_path in self.image_paths:
            self.image_paths.remove(image_path)
        
        # 清空预览
        self.preview_label.setText("选择图片查看预览")
        self.delete_button.setEnabled(False)
        
        # 发送信号
        self.imagesChanged.emit(self.image_paths)
    
    def getImagePaths(self):
        """获取所有图片路径"""
        return self.image_paths