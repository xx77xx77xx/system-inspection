@echo off
setlocal
title 医院系统巡检控制台

:: 强制切换到脚本所在目录
cd /d "%~dp0"

echo ----------------------------------------------
echo        系统巡检及看板启动脚本
echo ----------------------------------------------


:: --- 环境检测 ---
set PY=python
if exist "python_env\python.exe" (
    set PY="%~dp0python_env\python.exe"
    echo [+] 使用便携版 Python 环境...
) else (
    echo [!] 使用全局系统 Python 环境。
)

:: 验证 Python 是否可用
%PY% --version >nul 2>&1
if errorlevel 1 (
    echo [❌] 错误：无法启动 Python！
    echo [!] 请检查是否安装了 Python，或者是否运行过 setup_env.ps1 构建本地环境。
    echo [!] 当前路径：%cd%
    echo [!] 尝试调用的命令：%PY%
    pause
    exit /b
)

if not exist logs mkdir logs

echo [1] 正在检查依赖库...
%PY% -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo [!] 警告：依赖安装或检查过程中出现问题，请确认网络连接。
    pause
)

echo [2] 正在启动后台 Web 服务...
:: 使用 start /b 启动，注意必须加 "" 作为标题占位符
start /b "InspectionWeb" %PY% -m uvicorn web:app --host 0.0.0.0 --port 8000
if errorlevel 1 (
    echo [❌] 无法启动 Web 服务，请检查端口 8000 是否被占用。
    pause
    exit /b
)

echo [3] Web 服务已在后台运行 (http://localhost:8000)
echo ==============================================
echo [4] 准备进行当前轮次系统巡检...
pause

echo ----------------------------------------------
%PY% main.py
echo ----------------------------------------------


echo 本次巡检脚本执行完毕！
echo 如果您以后要添加定时巡检，建议将 "python main.py" 加入到 Windows 任务计划程序中。
echo 注意：此控制台未关闭时，Web 服务将继续在后台运行，关闭此控制台可能会结束该进程。
pause
endlocal
