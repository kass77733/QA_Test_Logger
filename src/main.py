import sys
import os
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt, QTimer

from ui import MainWindow


def main():
    """程序入口函数"""
    # 确保必要的目录存在
    os.makedirs('data', exist_ok=True)
    os.makedirs('images', exist_ok=True)
    
    # 创建应用
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用Fusion风格，在不同平台上保持一致的外观
    
    # 设置应用图标（使用绝对路径，避免工作目录变化导致找不到）
    base_dir = os.path.dirname(__file__)
    icon_path_ico = os.path.join(base_dir, 'icon.ico')
    icon_path_png = os.path.join(base_dir, 'icon.png')
    if os.path.exists(icon_path_ico):
        app.setWindowIcon(QIcon(icon_path_ico))
    elif os.path.exists(icon_path_png):
        app.setWindowIcon(QIcon(icon_path_png))
    
    # 显示启动画面
    splash_pix = QPixmap(400, 200)
    splash_pix.fill(Qt.GlobalColor.white)
    splash = QSplashScreen(splash_pix)
    splash.showMessage("正在加载应用...", Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.black)
    splash.show()
    app.processEvents()
    
    # 创建主窗口
    window = MainWindow()
    
    # 延迟关闭启动画面并显示主窗口
    def show_main_window():
        splash.finish(window)
        window.show()
    
    QTimer.singleShot(1000, show_main_window)
    
    # 运行应用
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
