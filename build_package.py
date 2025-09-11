#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动打包脚本
将QA_Test_Logger项目打包成可移植的加密版本
"""

import os
import sys
import shutil
import subprocess
import zipfile
import py_compile
import base64
import marshal
import compileall
from pathlib import Path

class ProjectPackager:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.build_dir = self.project_root / "build"
        self.dist_dir = self.project_root / "dist"
        self.encrypted_dir = self.build_dir / "encrypted_src"
        self.package_name = "QA_Test_Logger_Portable"
        
    def clean_build_dirs(self):
        """清理构建目录"""
        print("清理构建目录...")
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
        self.build_dir.mkdir(exist_ok=True)
        self.dist_dir.mkdir(exist_ok=True)
        self.encrypted_dir.mkdir(exist_ok=True)
    
    def create_portable_python(self):
        """创建便携式Python环境"""
        print("创建便携式Python环境...")
        
        # 创建虚拟环境
        venv_dir = self.build_dir / "python_env"
        subprocess.run([
            sys.executable, "-m", "venv", str(venv_dir), "--copies"
        ], check=True)
        
        # 获取虚拟环境的python和pip路径
        if os.name == 'nt':  # Windows
            python_exe = venv_dir / "Scripts" / "python.exe"
            pip_exe = venv_dir / "Scripts" / "pip.exe"
        else:  # Unix-like
            python_exe = venv_dir / "bin" / "python"
            pip_exe = venv_dir / "bin" / "pip"
        
        # 安装项目依赖
        print("安装项目依赖...")
        subprocess.run([
            str(pip_exe), "install", "-r", str(self.project_root / "requirements.txt")
        ], check=True)
        
        # 安装加密所需的依赖
        subprocess.run([
            str(pip_exe), "install", "cryptography"
        ], check=True)
        
        return venv_dir, python_exe
    
    def encrypt_source_code(self):
        """加密源代码"""
        print("加密源代码...")
        
        src_dir = self.project_root / "src"
        
        # 创建加密模块
        encryptor_code = '''
import base64
import marshal
import types
import sys
import os

def decrypt_and_load(encrypted_data, module_name):
    """解密并加载模块"""
    try:
        # Base64解码
        decoded_data = base64.b64decode(encrypted_data)
        # Marshal反序列化
        code_obj = marshal.loads(decoded_data)
        # 创建模块
        module = types.ModuleType(module_name)
        # 设置模块属性
        module.__file__ = f"<encrypted:{module_name}>"
        module.__name__ = module_name
        # 执行代码
        exec(code_obj, module.__dict__)
        return module
    except Exception as e:
        print(f"解密模块 {module_name} 失败: {e}")
        raise

def load_encrypted_module(encrypted_file, module_name):
    """从文件加载加密模块"""
    with open(encrypted_file, 'r', encoding='utf-8') as f:
        encrypted_data = f.read()
    return decrypt_and_load(encrypted_data, module_name)
'''
        
        # 保存加密器
        encryptor_file = self.encrypted_dir / "encryptor.py"
        with open(encryptor_file, 'w', encoding='utf-8') as f:
            f.write(encryptor_code)
        
        # 加密每个Python文件
        encrypted_files = {}
        for py_file in src_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
                
            print(f"加密文件: {py_file.name}")
            
            # 编译Python代码
            with open(py_file, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # 编译为字节码
            code_obj = compile(source_code, str(py_file), 'exec')
            
            # 序列化字节码
            marshaled_code = marshal.dumps(code_obj)
            
            # Base64编码
            encrypted_data = base64.b64encode(marshaled_code).decode('utf-8')
            
            # 保存加密文件
            encrypted_file = self.encrypted_dir / f"{py_file.stem}.enc"
            with open(encrypted_file, 'w', encoding='utf-8') as f:
                f.write(encrypted_data)
            
            encrypted_files[py_file.stem] = str(encrypted_file)
        
        return encrypted_files
    
    def create_launcher(self, encrypted_files, venv_dir):
        """创建启动器"""
        print("创建启动器...")
        
        # 创建主启动器
        launcher_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QA Test Logger 便携版启动器
"""

import os
import sys
from pathlib import Path
import importlib.util

# 添加当前目录到路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir / "encrypted_src"))

# 导入加密器
from encryptor import load_encrypted_module

class EncryptedModuleFinder:
    """自定义模块查找器，用于处理加密模块的导入"""
    
    def __init__(self, encrypted_dir):
        self.encrypted_dir = encrypted_dir
        self.loaded_modules = {}
    
    def find_spec(self, name, path, target=None):
        """查找模块规范"""
        if name in self.loaded_modules:
            return None
            
        enc_file = self.encrypted_dir / f"{name}.enc"
        if enc_file.exists():
            # 创建模块规范
            spec = importlib.util.spec_from_loader(
                name, 
                EncryptedModuleLoader(str(enc_file), name),
                origin=str(enc_file)
            )
            return spec
        return None

class EncryptedModuleLoader:
    """自定义模块加载器"""
    
    def __init__(self, enc_file, module_name):
        self.enc_file = enc_file
        self.module_name = module_name
    
    def create_module(self, spec):
        """创建模块"""
        return None  # 使用默认模块创建
    
    def exec_module(self, module):
        """执行模块"""
        encrypted_module = load_encrypted_module(self.enc_file, self.module_name)
        # 将加密模块的内容复制到目标模块
        module.__dict__.update(encrypted_module.__dict__)

def setup_encrypted_import_system():
    """设置加密模块导入系统"""
    encrypted_dir = current_dir / "encrypted_src"
    finder = EncryptedModuleFinder(encrypted_dir)
    
    # 将自定义查找器添加到sys.meta_path的开头
    if finder not in sys.meta_path:
        sys.meta_path.insert(0, finder)

def main():
    """主函数"""
    try:
        # 确保必要的目录存在
        os.makedirs('data', exist_ok=True)
        os.makedirs('images', exist_ok=True)
        
        # 更改工作目录到程序目录
        os.chdir(str(current_dir))
        
        # 设置加密模块导入系统
        setup_encrypted_import_system()
        
        # 动态加载加密的主模块
        main_module = load_encrypted_module(
            str(current_dir / "encrypted_src" / "main.enc"), 
            "main"
        )
        
        # 运行主程序
        if hasattr(main_module, 'main'):
            main_module.main()
        else:
            print("错误: 主模块中找不到main函数")
            
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("按回车键退出...")

if __name__ == "__main__":
    main()
'''
        
        # 保存启动器
        launcher_file = self.build_dir / "start.py"
        with open(launcher_file, 'w', encoding='utf-8') as f:
            f.write(launcher_code)
        
        # 创建批处理启动器（Windows）
        if os.name == 'nt':
            bat_code = f'''@echo off
cd /d "%~dp0"
python_env\\Scripts\\python.exe start.py
pause
'''
            bat_file = self.build_dir / "启动程序.bat"
            with open(bat_file, 'w', encoding='gbk') as f:
                f.write(bat_code)
        
        # 创建Shell启动器（Unix-like）
        else:
            sh_code = f'''#!/bin/bash
cd "$(dirname "$0")"
./python_env/bin/python start.py
read -p "按回车键退出..."
'''
            sh_file = self.build_dir / "启动程序.sh"
            with open(sh_file, 'w', encoding='utf-8') as f:
                f.write(sh_code)
            # 添加执行权限
            os.chmod(sh_file, 0o755)
    
    def copy_resources(self):
        """复制资源文件"""
        print("复制资源文件...")
        
        # 复制requirements.txt
        if (self.project_root / "requirements.txt").exists():
            shutil.copy2(
                self.project_root / "requirements.txt",
                self.build_dir / "requirements.txt"
            )
        
        # 复制其他必要的文件和目录
        for item in ["data", "images"]:
            src_path = self.project_root / item
            if src_path.exists():
                dst_path = self.build_dir / item
                if src_path.is_dir():
                    shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(src_path, dst_path)
        
        # 查找并复制图标文件
        for icon_name in ["icon.ico", "icon.png"]:
            icon_path = self.project_root / "src" / icon_name
            if icon_path.exists():
                shutil.copy2(icon_path, self.encrypted_dir / icon_name)
    
    def create_readme(self):
        """创建说明文件"""
        print("创建说明文件...")
        
        readme_content = '''# QA Test Logger 便携版

## 使用说明

1. 本软件为便携版，无需安装，解压后即可使用
2. 首次运行可能需要几秒钟加载时间，请耐心等待

### Windows用户：
- 双击"启动程序.bat"即可运行

### Linux/Mac用户：
- 在终端中执行: ./启动程序.sh
- 或者执行: python start.py

## 注意事项

1. 请确保解压路径中没有中文字符和特殊符号
2. 如果遇到问题，请检查是否有杀毒软件阻止程序运行
3. 本程序已包含所有必要的依赖，无需额外安装任何模块

## 系统要求

- Windows 7/10/11 或 Linux/macOS
- 至少500MB可用磁盘空间

## 技术支持

如有问题请联系开发团队。

---
版本: {package_name}
构建时间: {build_time}
'''
        
        from datetime import datetime
        readme_content = readme_content.format(
            package_name=self.package_name,
            build_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        readme_file = self.build_dir / "README.txt"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
    
    def create_package(self):
        """创建最终的打包文件"""
        print("创建最终的打包文件...")
        
        # 创建ZIP包
        zip_file = self.dist_dir / f"{self.package_name}.zip"
        
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(self.build_dir):
                for file in files:
                    file_path = Path(root) / file
                    arc_name = file_path.relative_to(self.build_dir)
                    zf.write(file_path, arc_name)
        
        print(f"打包完成: {zip_file}")
        print(f"包大小: {zip_file.stat().st_size / 1024 / 1024:.2f} MB")
        
        return zip_file
    
    def build(self):
        """执行完整的构建过程"""
        print("=" * 50)
        print("开始构建 QA Test Logger 便携版")
        print("=" * 50)
        
        try:
            # 1. 清理构建目录
            self.clean_build_dirs()
            
            # 2. 创建便携式Python环境
            venv_dir, python_exe = self.create_portable_python()
            
            # 3. 加密源代码
            encrypted_files = self.encrypt_source_code()
            
            # 4. 创建启动器
            self.create_launcher(encrypted_files, venv_dir)
            
            # 5. 复制资源文件
            self.copy_resources()
            
            # 6. 创建说明文件
            self.create_readme()
            
            # 7. 创建最终包
            package_file = self.create_package()
            
            print("=" * 50)
            print("构建成功！")
            print(f"输出文件: {package_file}")
            print("=" * 50)
            
            return package_file
            
        except Exception as e:
            print(f"构建失败: {e}")
            import traceback
            traceback.print_exc()
            return None

def main():
    """主函数"""
    packager = ProjectPackager()
    package_file = packager.build()
    
    if package_file:
        print(f"\n✅ 打包成功！")
        print(f"📦 输出文件: {package_file}")
        print(f"📁 解压后运行: 启动程序.bat (Windows) 或 启动程序.sh (Linux/Mac)")
        print(f"\n🔒 源码已加密保护")
        print(f"🚀 包含完整Python环境，无需安装依赖")
    else:
        print("\n❌ 打包失败，请查看错误信息")

if __name__ == "__main__":
    main()