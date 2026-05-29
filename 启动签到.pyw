import os, sys

def _show_error(title, message):
    """用系统原生弹窗显示错误，无需任何第三方库"""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, str(message), str(title), 0x10)
    except Exception:
        pass

try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app import MainWindow
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFont

    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

except ImportError as e:
    name = str(e).rsplit("'", 2)[1] if "'" in str(e) else str(e)
    _show_error("启动失败 - 缺少依赖", (
        f"未找到必要组件：{name}\n\n"
        "请按以下步骤操作：\n"
        "1. 运行 start.bat 自动安装\n"
        "2. 或执行：pip install -r requirements.txt\n\n"
        "安装完成后重新运行本程序。"
    ))

except Exception as e:
    _show_error("启动失败", f"发生错误：\n\n{e}\n\n请检查网络连接后重试。")
