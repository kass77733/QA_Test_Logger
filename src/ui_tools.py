from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QMessageBox, QMenu
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QAction


class ToolsTab(QWidget):
    """其他工具标签页"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        """初始化UI"""
        self.layout = QVBoxLayout(self)
        
        # 创建工具分组
        tools_group = QGroupBox("常用工具")
        tools_layout = QVBoxLayout(tools_group)
        
        # 创建下拉菜单按钮
        self.tools_menu_button = QPushButton("其他工具 ▼")
        self.tools_menu_button.setMinimumHeight(40)
        
        # 创建下拉菜单
        self.tools_menu = QMenu(self)
        
        # 添加票据常用工具选项
        ticket_action = QAction("票据常用工具", self)
        ticket_action.triggered.connect(self.open_ticket_tools)
        self.tools_menu.addAction(ticket_action)
        
        # 可以添加更多工具选项
        # separator = self.tools_menu.addSeparator()
        # other_action = QAction("其他工具", self)
        # other_action.triggered.connect(self.open_other_tools)
        # self.tools_menu.addAction(other_action)
        
        # 将菜单关联到按钮
        self.tools_menu_button.setMenu(self.tools_menu)
        
        tools_layout.addWidget(self.tools_menu_button)
        
        # 添加一些间距
        tools_layout.addStretch()
        
        self.layout.addWidget(tools_group)
        self.layout.addStretch()
    
    def open_ticket_tools(self):
        """打开票据常用工具"""
        try:
            # 使用系统默认浏览器打开百度
            url = QUrl("http://baidu.com")
            QDesktopServices.openUrl(url)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开网页: {str(e)}")
    
    def open_other_tools(self):
        """打开其他工具（示例）"""
        QMessageBox.information(self, "提示", "这里可以添加其他工具功能")