@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 学习通自动签到

echo.
echo    ╔══════════════════════════════════════╗
echo    ║       学习通自动签到 v1.0            ║
echo    ╚══════════════════════════════════════╝
echo.

:: 检查 Python 是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo    [X] 未检测到 Python，请先安装 Python 3.9 或更高版本
    echo.
    echo    下载地址：https://www.python.org/downloads/
    echo    安装时务必勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

:: 检查并安装依赖
echo    [*] 正在检查依赖...
python -c "from PySide6.QtWidgets import QApplication; from Crypto.Cipher import AES; import requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo    [!] 检测到缺少依赖，正在自动安装...
    echo.
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if %errorlevel% neq 0 (
        echo.
        echo    [X] 依赖安装失败，请手动执行：pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo    [√] 依赖安装完成
    echo.
)

echo    [√] 环境就绪，正在启动...
echo.
start "" pythonw app.py
