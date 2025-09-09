from PyQt6.QtWidgets import QMainWindow, QTabWidget, QMenu, QWidget, QTabBar, QMessageBox
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QAction

from database import Database
from ui_cases import TestCasesTab
from ui_history import HistoryTab
from PyQt6.QtGui import QIcon
import os


class CustomTabBar(QTabBar):
    """自定义标签栏，处理特殊标签的点击事件"""
    
    # 自定义信号，用于通知标签点击
    tab_clicked_signal = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tools_tab_index = -1
    
    def mousePressEvent(self, event):
        """重写鼠标点击事件"""
        index = self.tabAt(event.pos())
        if index >= 0:
            # 发送自定义信号
            self.tab_clicked_signal.emit(index)
            
            # 如果点击的是工具标签，不调用父类方法（阻止标签切换）
            if index == self.tools_tab_index:
                return
        
        # 对于其他标签，正常处理
        super().mousePressEvent(event)


class CustomTabWidget(QTabWidget):
    """自定义标签页组件，支持下拉菜单"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 使用自定义标签栏
        self.custom_tab_bar = CustomTabBar()
        self.setTabBar(self.custom_tab_bar)
        
        self.tools_menu = None
        self.tools_tab_index = -1
        self.setup_tools_menu()
        
        # 连接自定义标签点击信号
        self.custom_tab_bar.tab_clicked_signal.connect(self.on_tab_clicked)
    
    def setup_tools_menu(self):
        """设置工具下拉菜单"""
        self.tools_menu = QMenu(self)
        
        # 添加票据常用工具选项
        ticket_action = QAction("票据常用工具", self)
        ticket_action.triggered.connect(self.open_ticket_tools)
        self.tools_menu.addAction(ticket_action)
        
        # 添加分隔线
        self.tools_menu.addSeparator()
        
        # 添加关于选项
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        self.tools_menu.addAction(about_action)
    
    def add_tools_tab(self):
        """添加工具标签页"""
        placeholder_widget = QWidget()
        self.tools_tab_index = self.addTab(placeholder_widget, "其他工具")
        self.custom_tab_bar.tools_tab_index = self.tools_tab_index
        return self.tools_tab_index
    
    def on_tab_clicked(self, index):
        """处理标签页点击事件"""
        if index == self.tools_tab_index:
            # 如果点击的是"其他工具"标签，显示下拉菜单
            tab_rect = self.tabBar().tabRect(index)
            # 计算菜单显示位置（标签页下方）
            menu_pos = self.tabBar().mapToGlobal(tab_rect.bottomLeft())
            
            # 显示菜单
            self.tools_menu.exec(menu_pos)
            # 注意：这里不会切换标签页，因为在CustomTabBar中已经阻止了
    
    def open_ticket_tools(self):
        """打开票据常用工具"""
        try:
            url = QUrl("http://baidu.com")
            QDesktopServices.openUrl(url)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开网页: {str(e)}")
    
    def show_about(self):
        """显示关于对话框"""
        about_text = """
<h2>Testar - 测试用例管理工具</h2>
<p><b>版本：</b> 1.0.0</p>
<p><b>描述：</b> 一款专业的测试用例管理和执行工具</p>

<h3>主要功能：</h3>
<ul>
<li>📋 Excel测试用例导入</li>
<li>🔍 测试用例执行与记录</li>
<li>📊 测试结果统计分析</li>
<li>📈 历史记录查询与导出</li>
<li>🖼️ 测试截图管理</li>
<li>📄 PDF/Excel报告导出</li>
</ul>

<h3>使用说明：</h3>
<p>• <b>测试执行：</b> 导入Excel用例，执行测试并记录结果</p>
<p>• <b>历史记录：</b> 查看历史测试记录，支持筛选和导出</p>
<p>• <b>其他工具：</b> 提供常用工具快捷访问</p>

<p><b>开发者：</b> CodeBuddy</p>
<p><b>技术栈：</b> Python + PyQt6 + SQLite</p>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("关于 Testar")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(about_text)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        # 设置对话框大小
        msg.resize(500, 400)
        
        msg.exec()


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.initUI()
    
    def initUI(self):
        """初始化UI"""
        self.setWindowTitle("Testar")
        self.setGeometry(100, 100, 1200, 800)
        # 同步设置主窗口图标（部分平台只读取窗口图标）
        base_dir = os.path.dirname(__file__)
        icon_path_ico = os.path.join(base_dir, 'icon.ico')
        icon_path_png = os.path.join(base_dir, 'icon.png')
        if os.path.exists(icon_path_ico):
            self.setWindowIcon(QIcon(icon_path_ico))
        elif os.path.exists(icon_path_png):
            self.setWindowIcon(QIcon(icon_path_png))
        
        # 创建自定义标签页
        self.tabs = CustomTabWidget()
        
        # 测试用例标签页
        self.cases_tab = TestCasesTab(self.db)
        self.tabs.addTab(self.cases_tab, "测试执行")
        
        # 历史记录标签页
        self.history_tab = HistoryTab(self.db)
        self.tabs.addTab(self.history_tab, "历史记录")
        
        # 添加"其他工具"标签（这是一个特殊的标签，点击时显示菜单）
        self.tabs.add_tools_tab()
        
        # 默认显示第一个标签页（测试执行）
        self.tabs.setCurrentIndex(0)
        
        # 建立标签页之间的通信：当导入新案例集时，通知历史记录界面刷新下拉框
        self.cases_tab.collection_imported = self.on_collection_imported
        
        self.setCentralWidget(self.tabs)
    
    def on_collection_imported(self):
        """处理案例集导入事件"""
        # 刷新历史记录界面的案例集下拉框
        self.history_tab.refresh_collection_combo()
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 关闭数据库连接
        self.db.close()
        event.accept()