@echo off
chcp 65001 >nul
title QA测试日志工具 - 一键打包脚本
color 0A

echo.
echo ========================================
echo    QA测试日志工具 - 一键打包脚本
echo ========================================
echo.
echo 🚀 正在检查环境并开始打包...
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未检测到Python环境
    echo 请先安装Python 3.7或更高版本
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python环境检查通过

REM 检查PyInstaller是否安装
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo 📦 正在安装PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo ❌ PyInstaller安装失败
        pause
        exit /b 1
    )
)

echo ✅ PyInstaller检查通过

REM 检查依赖包
echo 📋 正在检查项目依赖...
if exist "requirements.txt" (
    echo 📦 正在安装项目依赖...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ⚠️  依赖安装可能有问题，但继续尝试打包...
    )
) else (
    echo ⚠️  未找到requirements.txt，尝试安装基础依赖...
    pip install PyQt6 pandas openpyxl Pillow reportlab
)

echo ✅ 依赖检查完成

REM 清理旧的打包文件
echo 🧹 正在清理旧的打包文件...
if exist "dist" rmdir /s /q "dist" >nul 2>&1
if exist "build" rmdir /s /q "build" >nul 2>&1
for %%f in (*.spec) do del "%%f" >nul 2>&1

echo ✅ 清理完成

REM 检查源码文件
if not exist "src\main.py" (
    echo ❌ 错误：未找到src\main.py文件
    echo 请确保在项目根目录运行此脚本
    pause
    exit /b 1
)

echo ✅ 源码文件检查通过

REM 开始打包
echo.
echo 🔨 开始打包QA测试日志工具...
echo ⏳ 这可能需要几分钟时间，请耐心等待...
echo.

pyinstaller ^
    --onefile ^
    --windowed ^
    --name="QA测试日志工具_最终版" ^
    --add-data="src;src" ^
    --hidden-import=sqlite3 ^
    --hidden-import=PyQt6.QtWidgets ^
    --hidden-import=PyQt6.QtGui ^
    --hidden-import=PyQt6.QtCore ^
    --hidden-import=pandas ^
    --hidden-import=openpyxl ^
    --hidden-import=PIL.Image ^
    --icon="src/icon.png" ^
    --distpath="dist" ^
    --workpath="build" ^
    --clean ^
    --noconfirm ^
    src/main.py

REM 检查打包结果
if exist "dist\QA测试日志工具_最终版.exe" (
    echo.
    echo ========================================
    echo           🎉 打包成功！
    echo ========================================
    echo.
    echo 📁 输出文件：dist\QA测试日志工具_最终版.exe
    
    REM 获取文件大小
    for %%A in ("dist\QA测试日志工具_最终版.exe") do (
        set /a size=%%~zA/1024/1024
        echo 📊 文件大小：!size! MB
    )
    
    echo.
    echo 📋 使用说明：
    echo   1. 可以直接运行 dist\QA测试日志工具_最终版.exe
    echo   2. 将exe文件发给其他人即可使用
    echo   3. 无需安装Python或其他依赖
    echo.
    
    REM 创建使用说明文件
    echo 🎯 QA测试日志工具 - 使用指南 > "dist\使用说明.txt"
    echo =============================== >> "dist\使用说明.txt"
    echo. >> "dist\使用说明.txt"
    echo ✅ 使用方法： >> "dist\使用说明.txt"
    echo 1. 双击 "QA测试日志工具_最终版.exe" 启动程序 >> "dist\使用说明.txt"
    echo 2. 等待3-5秒程序完全加载 >> "dist\使用说明.txt"
    echo 3. 看到界面后即可开始使用 >> "dist\使用说明.txt"
    echo. >> "dist\使用说明.txt"
    echo 💡 程序功能： >> "dist\使用说明.txt"
    echo - 测试用例管理 >> "dist\使用说明.txt"
    echo - 测试执行记录 >> "dist\使用说明.txt"
    echo - 历史数据查询 >> "dist\使用说明.txt"
    echo - Excel报告导出 >> "dist\使用说明.txt"
    echo - 截图功能支持 >> "dist\使用说明.txt"
    echo. >> "dist\使用说明.txt"
    echo ⚠️ 注意事项： >> "dist\使用说明.txt"
    echo - 首次启动可能较慢，请耐心等待 >> "dist\使用说明.txt"
    echo - 程序会自动创建data文件夹存储数据 >> "dist\使用说明.txt"
    echo - 支持Windows 7/8/10/11 (64位) >> "dist\使用说明.txt"
    echo - 无需安装Python或其他依赖 >> "dist\使用说明.txt"
    
    echo ✅ 已创建使用说明文件
    echo.
    
    REM 询问是否测试运行
    set /p test="🔍 是否要测试运行打包的程序？(y/n): "
    if /i "%test%"=="y" (
        echo 🚀 正在启动程序进行测试...
        start "" "dist\QA测试日志工具_最终版.exe"
    )
    
    echo.
    echo 🎊 打包完成！可以在dist文件夹中找到可执行文件。
    
) else (
    echo.
    echo ========================================
    echo           ❌ 打包失败
    echo ========================================
    echo.
    echo 可能的原因：
    echo 1. 缺少必要的依赖包
    echo 2. 源码文件有错误
    echo 3. 磁盘空间不足
    echo.
    echo 请检查上面的错误信息并重试
)

echo.
echo 按任意键退出...
pause >nul