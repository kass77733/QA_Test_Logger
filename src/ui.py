from PyQt6.QtWidgets import QMainWindow, QTabWidget

from database import Database
from ui_cases import TestCasesTab
from ui_history import HistoryTab


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
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 测试用例标签页
        self.cases_tab = TestCasesTab(self.db)
        self.tabs.addTab(self.cases_tab, "测试执行")
        
        # 历史记录标签页
        self.history_tab = HistoryTab(self.db)
        self.tabs.addTab(self.history_tab, "历史记录")
        
        self.setCentralWidget(self.tabs)
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 关闭数据库连接
        self.db.close()
        event.accept()