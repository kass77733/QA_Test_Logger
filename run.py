import os
import sys
import subprocess

def check_requirements():
    """检查依赖是否已安装"""
    try:
        import PyQt6
        import pandas
        import PIL
        return True
    except ImportError:
        return False

def install_requirements():
    """安装依赖"""
    print("正在安装依赖...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("依赖安装完成")

def main():
    """主函数"""
    # 检查依赖
    if not check_requirements():
        print("检测到缺少必要依赖，将自动安装...")
        install_requirements()
    
    # 启动应用
    print("正在启动 Testar...")
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    subprocess.call([sys.executable, "src/main.py"])

if __name__ == "__main__":
    main()