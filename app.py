#!/usr/bin/env python3
"""学习通签到 - PySide6 GUI（纯界面层）"""
import sys, time, traceback

def _fail(msg):
    """双重报错：控制台 + Windows弹窗"""
    print(f"\n[启动失败] {msg}\n")
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, msg,
            "学习通签到 - 启动失败", 0x10)
    except Exception:
        pass
    sys.exit(1)

try:
    from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
        QHBoxLayout, QLabel, QPushButton, QCheckBox, QScrollArea, QFrame,
        QTextEdit, QLineEdit, QDialog, QStackedWidget, QRadioButton,
        QSlider, QSpinBox, QButtonGroup)
    from PySide6.QtCore import Qt, QTimer, Signal, QThread
    from PySide6.QtGui import QFont, QTextCursor
except ImportError as e:
    name = str(e).rsplit("'", 2)[1] if "'" in str(e) else "PySide6"
    _fail(f"未找到 {name}\n\n请先安装依赖：\n  pip install -r requirements.txt\n\n或运行 start.bat 自动安装")

import os
sys.path.insert(0, os.path.dirname(__file__))

from config_manager import ConfigManager
from sign_service import SignService
from workers import RefreshWorker, SignWorker, MonitorWorker

# 共享样式
STYLE_INPUT = "QLineEdit{border:2px solid #d0d0d0;border-radius:5px;padding:10px 14px;font-size:14px;background:#fff;color:#222;} QLineEdit:focus{border-color:#4a6cf7;}"
STYLE_OUTLINE = "QPushButton{background:transparent;color:#4a6cf7;border:1px solid #4a6cf7;border-radius:4px;font-size:11px;} QPushButton:hover{background:#4a6cf7;color:#fff;}"

# ---------- 登录弹窗 ----------
class LoginDialog(QDialog):
    def __init__(self, config, service, parent=None, prefill=""):
        super().__init__(parent)
        self._cfg = config
        self._svc = service
        self.setWindowTitle("登录学习通"); self.setFixedSize(380, 270)
        self.setStyleSheet("QDialog{background:#fff}")
        self.result_user = None
        ly = QVBoxLayout(self); ly.setSpacing(10); ly.setContentsMargins(28,20,28,20)

        t = QLabel("学习通登录"); t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet("font-size:17px;font-weight:bold;color:#1a1a2e;"); ly.addWidget(t)
        s = QLabel("首次使用需登录获取课程，数据缓存本地"); s.setAlignment(Qt.AlignCenter)
        s.setStyleSheet("font-size:11px;color:#999;"); ly.addWidget(s); ly.addSpacing(6)

        self.user = QLineEdit(); self.user.setPlaceholderText("手机号")
        self.user.setStyleSheet(STYLE_INPUT); self.user.setText(prefill); ly.addWidget(self.user)

        self.pwd = QLineEdit(); self.pwd.setPlaceholderText("密码")
        self.pwd.setEchoMode(QLineEdit.Password); self.pwd.setStyleSheet(STYLE_INPUT)
        self.pwd.returnPressed.connect(self._go); ly.addWidget(self.pwd)

        self.err = QLabel(""); self.err.setStyleSheet("color:#e74c3c;font-size:11px;")
        self.err.setAlignment(Qt.AlignCenter); ly.addWidget(self.err)

        self.btn = QPushButton("登录并获取课程"); self.btn.clicked.connect(self._go)
        self.btn.setStyleSheet("QPushButton{background:#4a6cf7;color:#fff;border:none;border-radius:5px;padding:10px;font-size:13px;font-weight:bold;} QPushButton:hover{background:#3b5de7;} QPushButton:disabled{background:#bbb;}")
        ly.addWidget(self.btn)

    def _go(self):
        u = self.user.text().strip(); p = self.pwd.text().strip()
        if not u or not p: self.err.setText("账号密码不能为空"); return
        self.btn.setText("登录中..."); self.btn.setEnabled(False); self.err.setText("")
        QApplication.processEvents()
        try:
            self._svc.login(u, p)
            courses = self._svc.fetch_courses()
            cl = [{"courseId":c["courseId"],"clazzId":c["clazzId"],
                   "name":c["name"],"teacher":c["teacher"]} for c in courses]
            self._cfg.save_courses(cl)
            self._cfg.save_whitelist(
                [f"{c['courseId']}_{c['clazzId']}" for c in cl])
            self._cfg.save_credentials(u, p)
            self.result_user = u; self.accept()
        except Exception as e:
            self.err.setText(str(e)); self.btn.setText("登录并获取课程"); self.btn.setEnabled(True)


# ---------- 主题样式 ----------
LIGHT_STYLE = """
QMainWindow{background:#f0f2f5;}
QFrame#card{background:#fff;border-radius:8px;border:1px solid #eee;}
QFrame#sidebar{background:#1e1e2e;border:none;}
QLabel#sidebar_title{color:#fff;font-size:15px;font-weight:bold;}
QPushButton#nav_btn{background:transparent;color:#a0a0b8;border:none;border-left:3px solid transparent;
    border-radius:0;padding:10px 16px;font-size:13px;text-align:left;}
QPushButton#nav_btn:hover{background:#2a2a3c;color:#cdd6f4;}
QPushButton#nav_btn[active="true"]{background:#2a2a3c;color:#fff;border-left:3px solid #4a6cf7;}
QLabel#sidebar_status{color:#888;font-size:11px;}
QPushButton#btn_mon{background:#4a6cf7;color:#fff;border:none;border-radius:6px;font-size:12px;font-weight:bold;}
QPushButton#btn_mon:hover{background:#3b5de7;}
QPushButton#btn_mon:disabled{background:#ccc;}
QPushButton#btn_mon[running="true"]{background:#e74c3c;}
QPushButton#btn_mon[running="true"]:hover{background:#c0392b;}
QPushButton#btn_sign{background:#38A169;color:#fff;border:none;border-radius:6px;font-size:13px;font-weight:bold;}
QPushButton#btn_sign:hover{background:#2F855A;}
QPushButton#btn_sign:disabled{background:#ccc;}
QPushButton#btn_save{background:#4a6cf7;color:#fff;border:none;border-radius:6px;padding:10px 24px;font-size:13px;font-weight:bold;}
QPushButton#btn_save:hover{background:#3b5de7;}
QRadioButton{font-size:13px;color:#333;spacing:6px;}
QSpinBox{border:2px solid #d0d0d0;border-radius:5px;padding:6px 10px;font-size:13px;background:#fff;color:#222;}
QSpinBox:focus{border-color:#4a6cf7;}
QSlider::groove:horizontal{border:none;height:6px;background:#e0e0e0;border-radius:3px;}
QSlider::handle:horizontal{background:#4a6cf7;border:none;width:16px;height:16px;margin:-5px 0;border-radius:8px;}
QSlider::handle:horizontal:hover{background:#3b5de7;}
QSlider::sub-page:horizontal{background:#4a6cf7;border-radius:3px;}
QLabel#setting_title{font-size:14px;font-weight:bold;color:#333;}
QLabel#setting_hint{font-size:11px;color:#999;}
QCheckBox{font-size:13px;color:#333;spacing:6px;}
QLabel{color:#333;}
"""

DARK_STYLE = """
QMainWindow{background:#181825;}
QFrame#card{background:#1e1e2e;border-radius:8px;border:1px solid #313244;}
QFrame#sidebar{background:#11111b;border:none;}
QLabel#sidebar_title{color:#cdd6f4;font-size:15px;font-weight:bold;}
QPushButton#nav_btn{background:transparent;color:#6c7086;border:none;border-left:3px solid transparent;
    border-radius:0;padding:10px 16px;font-size:13px;text-align:left;}
QPushButton#nav_btn:hover{background:#181825;color:#cdd6f4;}
QPushButton#nav_btn[active="true"]{background:#181825;color:#cdd6f4;border-left:3px solid #4a6cf7;}
QLabel#sidebar_status{color:#6c7086;font-size:11px;}
QPushButton#btn_mon{background:#4a6cf7;color:#fff;border:none;border-radius:6px;font-size:12px;font-weight:bold;}
QPushButton#btn_mon:hover{background:#3b5de7;}
QPushButton#btn_mon:disabled{background:#585b70;}
QPushButton#btn_mon[running="true"]{background:#e74c3c;}
QPushButton#btn_mon[running="true"]:hover{background:#c0392b;}
QPushButton#btn_sign{background:#38A169;color:#fff;border:none;border-radius:6px;font-size:13px;font-weight:bold;}
QPushButton#btn_sign:hover{background:#2F855A;}
QPushButton#btn_sign:disabled{background:#585b70;}
QPushButton#btn_save{background:#4a6cf7;color:#fff;border:none;border-radius:6px;padding:10px 24px;font-size:13px;font-weight:bold;}
QPushButton#btn_save:hover{background:#3b5de7;}
QRadioButton{font-size:13px;color:#cdd6f4;spacing:6px;}
QSpinBox{border:2px solid #45475a;border-radius:5px;padding:6px 10px;font-size:13px;background:#313244;color:#cdd6f4;}
QSpinBox:focus{border-color:#4a6cf7;}
QSlider::groove:horizontal{border:none;height:6px;background:#45475a;border-radius:3px;}
QSlider::handle:horizontal{background:#4a6cf7;border:none;width:16px;height:16px;margin:-5px 0;border-radius:8px;}
QSlider::handle:horizontal:hover{background:#3b5de7;}
QSlider::sub-page:horizontal{background:#4a6cf7;border-radius:3px;}
QLabel#setting_title{font-size:14px;font-weight:bold;color:#cdd6f4;}
QLabel#setting_hint{font-size:11px;color:#6c7086;}
QTextEdit{font-family:'Consolas','Microsoft YaHei';font-size:12px;}
QCheckBox{font-size:13px;color:#cdd6f4;spacing:6px;}
QLabel{color:#cdd6f4;}
"""


# ---------- 主窗口 ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 依赖注入：配置 → 服务
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(__file__)
        self._cfg = ConfigManager(base)
        self._svc = SignService(self._cfg)

        self.setWindowTitle("学习通自动签到")
        self.setMinimumSize(860, 600); self.resize(920, 640)
        self.sign_running = False; self.monitoring = False
        self.night_mode = self._cfg.is_night_mode(); self.course_checks = {}
        self._build()
        self._apply_theme()
        QTimer.singleShot(80, self._check_login)

    # ===== 主题 =====
    def _apply_theme(self):
        if self.night_mode:
            self.setStyleSheet(DARK_STYLE)
            self.log.setStyleSheet(
                "QTextEdit{background:#11111b;color:#cdd6f4;border:none;"
                "border-radius:6px;padding:10px;font-family:'Consolas','Microsoft YaHei';font-size:12px;}")
        else:
            self.setStyleSheet(LIGHT_STYLE)
            self.log.setStyleSheet(
                "QTextEdit{background:#1e1e2e;color:#cdd6f4;border:none;"
                "border-radius:6px;padding:10px;font-family:'Consolas','Microsoft YaHei';font-size:12px;}")
        self._update_nav_btns()

    # ===== 构建 =====
    def _build(self):
        c = QWidget(); self.setCentralWidget(c)
        root = QHBoxLayout(c); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_sign_page())
        self.pages.addWidget(self._build_settings_page())
        root.addWidget(self.pages, 1)

    def _build_sidebar(self):
        sb = QFrame(); sb.setObjectName("sidebar"); sb.setFixedWidth(150)
        sl = QVBoxLayout(sb); sl.setContentsMargins(0, 16, 0, 10); sl.setSpacing(2)

        t = QLabel("  学习通签到"); t.setObjectName("sidebar_title")
        sl.addWidget(t); sl.addSpacing(16)

        self.nav_sign_btn = QPushButton("  签到"); self.nav_sign_btn.setObjectName("nav_btn")
        self.nav_sign_btn.setCursor(Qt.PointingHandCursor)
        self.nav_sign_btn.clicked.connect(lambda: self._switch_page(0))
        sl.addWidget(self.nav_sign_btn)

        self.nav_set_btn = QPushButton("  设置"); self.nav_set_btn.setObjectName("nav_btn")
        self.nav_set_btn.setCursor(Qt.PointingHandCursor)
        self.nav_set_btn.clicked.connect(lambda: self._switch_page(1))
        sl.addWidget(self.nav_set_btn)

        sl.addStretch()

        sr = QHBoxLayout(); sr.setContentsMargins(12, 0, 12, 0); sr.setSpacing(6)
        self.dot = QLabel(); self.dot.setFixedSize(8, 8); self._dot_idle(); sr.addWidget(self.dot)
        self.sts = QLabel("就绪"); self.sts.setObjectName("sidebar_status"); sr.addWidget(self.sts)
        sl.addLayout(sr)
        return sb

    def _switch_page(self, idx):
        self.pages.setCurrentIndex(idx)
        self._update_nav_btns()
        if idx == 1:
            self._load_settings()

    def _update_nav_btns(self):
        cur = self.pages.currentIndex()
        for i, btn in enumerate([self.nav_sign_btn, self.nav_set_btn]):
            btn.setProperty("active", i == cur)
            btn.style().unpolish(btn); btn.style().polish(btn)

    # ===== 签到页面 =====
    def _build_sign_page(self):
        page = QWidget()
        root = QVBoxLayout(page); root.setContentsMargins(16, 12, 16, 8); root.setSpacing(10)

        top = QHBoxLayout(); top.setSpacing(10)
        self.acct = QLabel(""); self.acct.setStyleSheet("font-size:11px;color:#999;")
        top.addWidget(self.acct); top.addStretch()
        self.btn_mon = QPushButton("  持续监听"); self.btn_mon.setObjectName("btn_mon")
        self.btn_mon.setFixedSize(100, 34); self.btn_mon.clicked.connect(self._toggle_monitor)
        top.addWidget(self.btn_mon)
        self.btn = QPushButton("  开始签到"); self.btn.setObjectName("btn_sign")
        self.btn.setFixedSize(120, 34); self.btn.clicked.connect(self._start)
        top.addWidget(self.btn)
        root.addLayout(top)

        cc = QFrame(); cc.setObjectName("card")
        cl = QVBoxLayout(cc); cl.setContentsMargins(14, 10, 14, 8); cl.setSpacing(6)
        ch = QHBoxLayout()
        t = QLabel("  签到白名单")
        t.setStyleSheet("font-size:13px;font-weight:bold;color:#333;"); ch.addWidget(t)
        self.cnt = QLabel(""); self.cnt.setStyleSheet("font-size:11px;color:#999;")
        ch.addWidget(self.cnt); ch.addStretch()
        for txt, slot in [("全选", self._all), ("清空", self._none),
                          ("保存", self._save_wl), ("刷新", self._refresh)]:
            b = QPushButton(txt); b.setFixedSize(54, 24)
            b.setStyleSheet(STYLE_OUTLINE); b.clicked.connect(slot); ch.addWidget(b)
        cl.addLayout(ch)
        sc = QScrollArea(); sc.setWidgetResizable(True)
        sc.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        self.cw = QWidget()
        self.cly = QVBoxLayout(self.cw); self.cly.setContentsMargins(0, 0, 0, 0)
        self.cly.setSpacing(1); self.cly.addStretch()
        sc.setWidget(self.cw); cl.addWidget(sc)
        root.addWidget(cc, 2)

        lc = QFrame(); lc.setObjectName("card")
        ll = QVBoxLayout(lc); ll.setContentsMargins(14, 8, 14, 8); ll.setSpacing(4)
        lh = QHBoxLayout()
        lh.addWidget(QLabel("  签到日志"))
        lh.itemAt(0).widget().setStyleSheet("font-size:13px;font-weight:bold;color:#333;")
        lh.addStretch()
        cb = QPushButton("清空"); cb.setFixedSize(54, 24)
        cb.setStyleSheet(STYLE_OUTLINE); cb.clicked.connect(self._clr_log); lh.addWidget(cb)
        ll.addLayout(lh)
        self.log = QTextEdit(); self.log.setReadOnly(True)
        self.log.setStyleSheet(
            "QTextEdit{background:#1e1e2e;color:#cdd6f4;border:none;border-radius:6px;"
            "padding:10px;font-family:'Consolas','Microsoft YaHei';font-size:12px;}")
        ll.addWidget(self.log, 1); root.addWidget(lc, 1)
        return page

    # ===== 设置页面 =====
    def _build_settings_page(self):
        page = QWidget()
        ly = QVBoxLayout(page); ly.setContentsMargins(24, 20, 24, 16); ly.setSpacing(14)

        hdr = QLabel("设置"); hdr.setStyleSheet("font-size:18px;font-weight:bold;color:#333;")
        ly.addWidget(hdr)

        c1 = QFrame(); c1.setObjectName("card")
        c1l = QVBoxLayout(c1); c1l.setContentsMargins(16, 12, 16, 14); c1l.setSpacing(8)
        t1 = QLabel("监听间隔"); t1.setObjectName("setting_title"); c1l.addWidget(t1)

        self.bg_interval = QButtonGroup(self)
        self.radio_active = QRadioButton("积极（10 秒）")
        self.radio_normal = QRadioButton("常规（30 秒）")
        self.radio_custom = QRadioButton("自定义")
        for r in [self.radio_active, self.radio_normal, self.radio_custom]:
            self.bg_interval.addButton(r); c1l.addWidget(r)

        cust_row = QHBoxLayout(); cust_row.setContentsMargins(24, 0, 0, 0); cust_row.setSpacing(8)
        self.spin_interval = QSpinBox(); self.spin_interval.setRange(5, 3600)
        self.spin_interval.setValue(30); self.spin_interval.setSuffix(" 秒")
        self.spin_interval.setFixedWidth(120); self.spin_interval.setEnabled(False)
        cust_row.addWidget(self.spin_interval); cust_row.addStretch(); c1l.addLayout(cust_row)

        self.radio_custom.toggled.connect(lambda v: self.spin_interval.setEnabled(v))
        ly.addWidget(c1)

        c2 = QFrame(); c2.setObjectName("card")
        c2l = QVBoxLayout(c2); c2l.setContentsMargins(16, 12, 16, 14); c2l.setSpacing(6)
        t2 = QLabel("随机浮动"); t2.setObjectName("setting_title"); c2l.addWidget(t2)
        h2 = QLabel("每次监听间隔上下随机浮动，0 表示关闭浮动")
        h2.setObjectName("setting_hint"); c2l.addWidget(h2)

        sr = QHBoxLayout(); sr.setSpacing(10)
        self.jitter_slider = QSlider(Qt.Horizontal); self.jitter_slider.setRange(0, 100)
        self.jitter_slider.setValue(40)
        self.jitter_label = QLabel("40%")
        self.jitter_label.setStyleSheet("font-size:13px;font-weight:bold;color:#4a6cf7;min-width:40px;")
        self.jitter_slider.valueChanged.connect(
            lambda v: self.jitter_label.setText(f"{v}%"))
        sr.addWidget(self.jitter_slider, 1); sr.addWidget(self.jitter_label)
        c2l.addLayout(sr)
        ly.addWidget(c2)

        c3 = QFrame(); c3.setObjectName("card")
        c3l = QVBoxLayout(c3); c3l.setContentsMargins(16, 12, 16, 14); c3l.setSpacing(6)
        t3 = QLabel("外观"); t3.setObjectName("setting_title"); c3l.addWidget(t3)
        self.night_check = QCheckBox("夜间模式")
        self.night_check.toggled.connect(self._on_night_toggle)
        c3l.addWidget(self.night_check)
        ly.addWidget(c3)

        ly.addStretch()

        bl = QHBoxLayout()
        bl.addStretch()
        save_btn = QPushButton("保存设置"); save_btn.setObjectName("btn_save")
        save_btn.setFixedSize(140, 38); save_btn.clicked.connect(self._save_settings)
        bl.addWidget(save_btn); ly.addLayout(bl)
        return page

    def _load_settings(self):
        cfg = self._cfg.get_config()
        interval = cfg.get("monitor_interval", 30)
        if interval == 10:
            self.radio_active.setChecked(True)
        elif interval != 30:
            self.radio_custom.setChecked(True)
            self.spin_interval.setValue(interval)
        else:
            self.radio_normal.setChecked(True)
        jitter = cfg.get("monitor_jitter", 40)
        self.jitter_slider.setValue(jitter)
        self.jitter_label.setText(f"{jitter}%")
        self.night_check.setChecked(cfg.get("night_mode", False))

    def _save_settings(self):
        updates = {}
        if self.radio_active.isChecked():
            updates["monitor_interval"] = 10
        elif self.radio_custom.isChecked():
            updates["monitor_interval"] = self.spin_interval.value()
        else:
            updates["monitor_interval"] = 30
        updates["monitor_jitter"] = self.jitter_slider.value()
        updates["night_mode"] = self.night_mode
        self._cfg.save_config(updates)
        self._log("设置已保存", "success")

    def _on_night_toggle(self, checked):
        self.night_mode = checked
        self._apply_theme()

    # ===== 状态指示 =====
    def _dot_running(self):
        self.dot.setStyleSheet(
            "background:#38A169;border-radius:4px;min-width:8px;min-height:8px;")
    def _dot_idle(self):
        self.dot.setStyleSheet(
            "background:#ccc;border-radius:4px;min-width:8px;min-height:8px;")

    def _log(self, msg, level="info"):
        c = {"success": "#a6e3a1", "warn": "#f9e2af",
             "error": "#f38ba8", "info": "#cdd6f4"}.get(level, "#cdd6f4")
        self.log.moveCursor(QTextCursor.End)
        self.log.insertHtml(
            f'<span style="color:#6c7086">{time.strftime("%H:%M:%S")}</span>'
            f'  <span style="color:{c}">{msg}</span><br>')
        self.log.moveCursor(QTextCursor.End)

    def _clr_log(self):
        self.log.clear()

    # ===== 登录 =====
    def _check_login(self):
        u, _ = self._cfg.get_account()
        courses = self._cfg.get_courses()
        if u and courses: self._load(u); return
        dlg = LoginDialog(self._cfg, self._svc, self, prefill=u)
        if dlg.exec() == QDialog.Accepted:
            self._load(dlg.result_user)
        else:
            u2, _ = self._cfg.get_account()
            if u2 and self._cfg.get_courses(): self._load(u2)
            else: self.close()

    def _load(self, u):
        self.acct.setText(f" {u}"); self._pop_courses()

    # ===== 课程列表 =====
    def _pop_courses(self):
        while self.cly.count() > 1:
            w = self.cly.takeAt(0)
            if w.widget(): w.widget().deleteLater()
        self.course_checks.clear()
        courses = self._cfg.get_courses()
        wl = self._cfg.get_whitelist()
        loc_db = self._cfg.get_locations()
        if not courses:
            e = QLabel("暂无课程数据"); e.setStyleSheet("color:#999;padding:16px;")
            e.setAlignment(Qt.AlignCenter)
            self.cly.insertWidget(0, e); self.cnt.setText(""); return
        for c in courses:
            k = f"{c['courseId']}_{c['clazzId']}"
            cb = QCheckBox(c["name"]); cb.setChecked(k in wl)
            cb.setStyleSheet(
                "QCheckBox{spacing:6px;font-size:12px;padding:2px 0;color:#cdd6f4;}"
                "QCheckBox:hover{color:#4a6cf7;}")
            self.course_checks[k] = cb
            row = QWidget()
            rl = QHBoxLayout(row); rl.setContentsMargins(6, 1, 10, 1); rl.setSpacing(6)
            rl.addWidget(cb); rl.addStretch()
            if k in loc_db:
                lo = loc_db[k]
                tag = QLabel(f" {lo['lat']:.4f},{lo['lng']:.4f}")
                tag.setStyleSheet("color:#38A169;font-size:9px;"); rl.addWidget(tag)
            if c.get("teacher"):
                t = QLabel(c["teacher"])
                t.setStyleSheet("color:#bbb;font-size:10px;"); rl.addWidget(t)
            self.cly.insertWidget(self.cly.count() - 1, row)
        checked = sum(1 for v in self.course_checks.values() if v.isChecked())
        self.cnt.setText(f"共{len(courses)}门 选{checked}")

    # ===== 白名单 =====
    def _all(self):
        for v in self.course_checks.values(): v.setChecked(True)
        self._upd_cnt()

    def _none(self):
        for v in self.course_checks.values(): v.setChecked(False)
        self._upd_cnt()

    def _save_wl(self):
        self._cfg.save_whitelist(
            [k for k, v in self.course_checks.items() if v.isChecked()])
        self._upd_cnt(); self._log("白名单已保存", "success")

    def _refresh(self):
        self._rt = RefreshWorker(self._svc, self._cfg)
        self._rt.log.connect(self._log)
        self._rt.done.connect(self._pop_courses); self._rt.start()

    def _upd_cnt(self):
        cs = self._cfg.get_courses()
        chk = sum(1 for v in self.course_checks.values() if v.isChecked())
        self.cnt.setText(f"共{len(cs)}门 选{chk}")

    # ===== 持续监听 =====
    def _toggle_monitor(self):
        if self.monitoring: self._stop_monitor()
        else: self._start_monitor()

    def _start_monitor(self):
        wl = [k for k, v in self.course_checks.items() if v.isChecked()]
        if not wl: self._log("请先在白名单中选择课程", "warn"); return
        self.monitoring = True
        self.btn_mon.setText("  停止监听")
        self.btn_mon.setProperty("running", True)
        self.btn_mon.style().unpolish(self.btn_mon)
        self.btn_mon.style().polish(self.btn_mon)
        self._dot_running(); self.sts.setText("监听中...")
        self._clr_log(); self._log("启动持续监听模式", "info")
        self._mt = MonitorWorker(self._svc, self._cfg)
        self._mt.log.connect(self._log)
        self._mt.tick.connect(self._monitor_tick)
        self._mt.state.connect(self._monitor_state)
        self._mt.start()

    def _stop_monitor(self):
        self.monitoring = False
        if hasattr(self, '_mt') and self._mt.isRunning():
            self._mt.stop(); self._mt.wait(3000)
        self.btn_mon.setText("  持续监听")
        self.btn_mon.setProperty("running", False)
        self.btn_mon.style().unpolish(self.btn_mon)
        self.btn_mon.style().polish(self.btn_mon)
        self._dot_idle(); self.sts.setText("就绪")
        self._log("监听已停止", "info")

    def _monitor_tick(self, sec):
        if sec > 0: self.sts.setText(f"监听中... {sec}秒后扫描")
        else: self.sts.setText("监听中... 扫描中")

    def _monitor_state(self, running):
        if not running:
            self.monitoring = False
            self.btn_mon.setText("  持续监听")
            self.btn_mon.setProperty("running", False)
            self.btn_mon.style().unpolish(self.btn_mon)
            self.btn_mon.style().polish(self.btn_mon)
            self._dot_idle(); self.sts.setText("就绪")

    # ===== 手动签到 =====
    def _start(self):
        if self.sign_running: return
        if self.monitoring: self._log("监听运行中，请先停止监听", "warn"); return
        wl = [k for k, v in self.course_checks.items() if v.isChecked()]
        if not wl: self._log("请先选择课程", "warn"); return
        cs = self._cfg.get_courses()
        targets = [c for c in cs if f"{c['courseId']}_{c['clazzId']}" in wl]
        self.sign_running = True
        self.btn.setText("签到中..."); self.btn.setEnabled(False)
        self._dot_running(); self.sts.setText("签到中...")
        self._clr_log(); self._log(f"开始签到,{len(targets)}门", "info")
        self._st = SignWorker(self._svc, self._cfg, targets)
        self._st.log.connect(self._log); self._st.done.connect(self._done)
        self._st.start()

    def _done(self):
        self.sign_running = False
        self.btn.setText("  开始签到"); self.btn.setEnabled(True)
        self._dot_idle(); self.sts.setText("就绪"); self._pop_courses()


if __name__ == "__main__":
    app = QApplication(sys.argv); app.setFont(QFont("Microsoft YaHei",10))
    MainWindow().show(); sys.exit(app.exec())
