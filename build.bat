@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 学习通签到 - 打包构建

echo.
echo    ╔══════════════════════════════════════╗
echo    ║       学习通签到 - 打包构建           ║
echo    ╚══════════════════════════════════════╝
echo.

:: ── 检查 Python ──
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo    [X] 未检测到 Python
    pause & exit /b 1
)

:: ── 检查 / 安装 PyInstaller ──
echo    [*] 检查 PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo    [!] 正在安装 PyInstaller...
    pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple
    if %errorlevel% neq 0 (
        echo    [X] 安装失败
        pause & exit /b 1
    )
    echo    [√] PyInstaller 安装完成
    echo.
)

:: ── 清理旧文件 ──
echo    [*] 清理旧构建...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist
echo    [√] 清理完成
echo.

:: ── 编译 Release 版（无控制台） ──
echo    [*] 正在编译 Release 版...
echo.
pyinstaller ChaoxingSign.spec --distpath dist/release --workpath build/release --clean --noconfirm
if %errorlevel% neq 0 (
    echo.
    echo    [X] Release 版编译失败
    pause & exit /b 1
)
echo.
echo    [√] Release 版编译完成
echo.

:: ── 编译 Debug 版（带控制台） ──
echo    [*] 正在编译 Debug 版...
echo.
python -c "
with open('ChaoxingSign.spec', 'r', encoding='utf-8') as f:
    spec = f.read()
spec = spec.replace(\"name='ChaoxingSign'\", \"name='ChaoxingSign_debug'\")
spec = spec.replace('console=False', 'console=True')
with open('_debug.spec', 'w', encoding='utf-8') as f:
    f.write(spec)
"
pyinstaller _debug.spec --distpath dist/debug --workpath build/debug --clean --noconfirm
del _debug.spec
if %errorlevel% neq 0 (
    echo.
    echo    [X] Debug 版编译失败
    pause & exit /b 1
)
echo.
echo    [√] Debug 版编译完成
echo.

:: ── 打包 ZIP ──
echo    [*] 正在打包 ZIP...
powershell -Command "Compress-Archive -Path 'dist/release/ChaoxingSign.exe' -DestinationPath 'dist/ChaoxingSign_Release.zip' -Force" 2>nul
powershell -Command "Compress-Archive -Path 'dist/debug/ChaoxingSign_debug.exe' -DestinationPath 'dist/ChaoxingSign_Debug.zip' -Force" 2>nul
echo    [√] ZIP 打包完成
echo.

:: ── 完成 ──
echo    ═══════════════════════════════════════
echo    构建完成！
echo.
echo    Release 版:  dist\release\ChaoxingSign.exe
echo    Debug 版:    dist\debug\ChaoxingSign_debug.exe
echo    ZIP 包:      dist\ChaoxingSign_Release.zip
echo                 dist\ChaoxingSign_Debug.zip
echo.
echo    上传 Release 请执行:
echo      gh release create v1.1 --title "v1.1" --notes "更新说明" ^
echo        dist/ChaoxingSign_Release.zip dist/ChaoxingSign_Debug.zip
echo    ═══════════════════════════════════════
echo.
pause
