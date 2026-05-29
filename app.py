#!/usr/bin/env python3
"""学习通签到 - PySide6 GUI"""
import json, os, sys, time

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
        QTextEdit, QLineEdit, QDialog)
    from PySide6.QtCore import Qt, QTimer, Signal, QThread
    from PySide6.QtGui import QFont, QTextCursor
except ImportError as e:
    name = str(e).rsplit("'", 2)[1] if "'" in str(e) else "PySide6"
    _fail(f"未找到 {name}\n\n请先安装依赖：\n  pip install -r requirements.txt\n\n或运行 start.bat 自动安装")

sys.path.insert(0, os.path.dirname(__file__))
from chaoxing_sign import ChaoXingSign

BASE = os.path.dirname(__file__)
CFG = lambda f: os.path.join(BASE, f)

def load(f, d=None):
    if d is None: d = {}
    if os.path.exists(f):
        with open(f, "r", encoding="utf-8") as fh: return json.load(fh)
    return d

def save(f, data):
    with open(f, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

# 共享样式
STYLE_INPUT = "QLineEdit{border:2px solid #d0d0d0;border-radius:5px;padding:10px 14px;font-size:14px;background:#fff;color:#222;} QLineEdit:focus{border-color:#4a6cf7;}"
STYLE_OUTLINE = "QPushButton{background:transparent;color:#4a6cf7;border:1px solid #4a6cf7;border-radius:4px;font-size:11px;} QPushButton:hover{background:#4a6cf7;color:#fff;}"

# ---------- 登录弹窗 ----------
class LoginDialog(QDialog):
    def __init__(self, parent=None, prefill=""):
        super().__init__(parent)
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
            signer = ChaoXingSign(u, p); signer.login()
            courses = signer.get_courses()
            cl = [{"courseId":c["courseId"],"clazzId":c["clazzId"],
                   "name":c["name"],"teacher":c["teacher"]} for c in courses]
            save(CFG("courses.json"), cl)
            save(CFG("whitelist.json"), [f"{c['courseId']}_{c['clazzId']}" for c in cl])
            cfg = load(CFG("config.json")); cfg["username"]=u; cfg["password"]=p
            save(CFG("config.json"), cfg)
            self.result_user = u; self.accept()
        except Exception as e:
            self.err.setText(str(e)); self.btn.setText("登录并获取课程"); self.btn.setEnabled(True)

# ---------- 工作线程 ----------
class RefreshThread(QThread):
    log = Signal(str, str); done = Signal()
    def run(self):
        cfg = load(CFG("config.json"))
        try:
            s = ChaoXingSign(cfg["username"],cfg["password"]); s.login()
            cl = [{"courseId":c["courseId"],"clazzId":c["clazzId"],
                   "name":c["name"],"teacher":c["teacher"]} for c in s.get_courses()]
            old = load(CFG("whitelist.json"),[]); nk = {f"{c['courseId']}_{c['clazzId']}" for c in cl}
            wl = [k for k in old if k in nk] + [f"{c['courseId']}_{c['clazzId']}" for c in cl if f"{c['courseId']}_{c['clazzId']}" not in old]
            save(CFG("courses.json"), cl); save(CFG("whitelist.json"), wl)
            self.log.emit(f"课程已更新，共{len(cl)}门","success")
        except Exception as e: self.log.emit(f"更新失败:{e}","error")
        self.done.emit()

class SignThread(QThread):
    log = Signal(str, str); done = Signal()
    def __init__(self, targets):
        super().__init__(); self.targets = targets
    def run(self):
        cfg = load(CFG("config.json"))
        dl, dln = cfg.get("latitude","36.1087"), cfg.get("longitude","120.4682")
        loc_db = load(CFG("locations.json")); updated = False
        try:
            signer = ChaoXingSign(cfg["username"],cfg["password"])
            self.log.emit("登录成功","success"); signer.login(); total = 0
            for c in self.targets:
                lk = f"{c['courseId']}_{c['clazzId']}"
                sv = loc_db.get(lk,{})
                lat = sv.get("lat",dl) if sv else dl
                lng = sv.get("lng",dln) if sv else dln
                if sv: self.log.emit(f"[{c['name']}] 坐标({lat:.4f},{lng:.4f})","info")
                try:
                    signs = signer.get_active_signs(c)
                    if signs: self.log.emit(f"[{c['name']}] {len(signs)}个活动","info")
                    for s in signs:
                        self.log.emit(f"  -> {s['name']}","info")
                        r = signer.sign(s, lat=lat, lng=lng)
                        st = r.get("status")
                        if st == "success":
                            nl, ng = r.get("lat"), r.get("lng")
                            if nl is not None and ng is not None:
                                loc_db[lk]={"lat":nl,"lng":ng,"updated_at":time.strftime("%Y-%m-%d %H:%M:%S")}
                                updated=True
                                self.log.emit(f"  坐标缓存({nl:.4f},{ng:.4f})","success")
                            self.log.emit(f"  -> 签到成功!","success")
                        else:
                            self.log.emit(f"  -> {st}","warn")
                        total += 1
                except Exception as e: self.log.emit(f"[{c['name']}] 出错:{e}","error")
            if updated: save(CFG("locations.json"), loc_db)
            self.log.emit(f"完成,共{total}个活动" if total else "无有效活动","success" if total else "info")
        except Exception as e: self.log.emit(f"异常:{e}","error")
        self.done.emit()

# ---------- 主窗口 ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("学习通自动签到"); self.setMinimumSize(700,560); self.resize(760,600)
        self.sign_running = False; self.course_checks = {}
        self._build(); self._style()
        QTimer.singleShot(80, self._check_login)

    def _build(self):
        c = QWidget(); self.setCentralWidget(c)
        root = QVBoxLayout(c); root.setContentsMargins(16,12,16,8); root.setSpacing(10)

        # 顶栏
        top = QHBoxLayout(); top.setSpacing(10)
        self.dot = QLabel(); self.dot.setFixedSize(10,10); self._dot_idle(); top.addWidget(self.dot)
        self.sts = QLabel("就绪"); self.sts.setStyleSheet("font-size:12px;color:#666;"); top.addWidget(self.sts)
        top.addStretch()
        self.acct = QLabel(""); self.acct.setStyleSheet("font-size:11px;color:#999;"); top.addWidget(self.acct)
        self.btn = QPushButton("  开始签到"); self.btn.setObjectName("btn_sign")
        self.btn.setFixedSize(120,34); self.btn.clicked.connect(self._start); top.addWidget(self.btn)
        root.addLayout(top)

        # 课程卡片
        cc = QFrame(); cc.setObjectName("card")
        cl = QVBoxLayout(cc); cl.setContentsMargins(14,10,14,8); cl.setSpacing(6)
        ch = QHBoxLayout()
        t = QLabel("  签到白名单"); t.setStyleSheet("font-size:13px;font-weight:bold;color:#333;"); ch.addWidget(t)
        self.cnt = QLabel(""); self.cnt.setStyleSheet("font-size:11px;color:#999;"); ch.addWidget(self.cnt); ch.addStretch()
        for txt, slot in [("全选",self._all),("清空",self._none),("保存",self._save_wl),("刷新",self._refresh)]:
            b = QPushButton(txt); b.setFixedSize(54,24); b.setStyleSheet(STYLE_OUTLINE); b.clicked.connect(slot); ch.addWidget(b)
        cl.addLayout(ch)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        self.cw = QWidget()
        self.cly = QVBoxLayout(self.cw); self.cly.setContentsMargins(0,0,0,0); self.cly.setSpacing(1); self.cly.addStretch()
        sc.setWidget(self.cw); cl.addWidget(sc)
        root.addWidget(cc, 2)

        # 日志卡片
        lc = QFrame(); lc.setObjectName("card")
        ll = QVBoxLayout(lc); ll.setContentsMargins(14,8,14,8); ll.setSpacing(4)
        lh = QHBoxLayout()
        lh.addWidget(QLabel("  签到日志")); lh.itemAt(0).widget().setStyleSheet("font-size:13px;font-weight:bold;color:#333;"); lh.addStretch()
        cb = QPushButton("清空"); cb.setFixedSize(54,24); cb.setStyleSheet(STYLE_OUTLINE); cb.clicked.connect(self._clr_log); lh.addWidget(cb)
        ll.addLayout(lh)
        self.log = QTextEdit(); self.log.setReadOnly(True)
        self.log.setStyleSheet("QTextEdit{background:#1e1e2e;color:#cdd6f4;border:none;border-radius:6px;padding:10px;font-family:'Consolas','Microsoft YaHei';font-size:12px;}")
        ll.addWidget(self.log, 1); root.addWidget(lc, 1)

    def _style(self):
        self.setStyleSheet("QMainWindow{background:#f0f2f5;} QFrame#card{background:#fff;border-radius:8px;border:1px solid #eee;} QPushButton#btn_sign{background:#38A169;color:#fff;border:none;border-radius:6px;font-size:13px;font-weight:bold;} QPushButton#btn_sign:hover{background:#2F855A;} QPushButton#btn_sign:disabled{background:#ccc;}")

    def _dot_running(self): self.dot.setStyleSheet("background:#38A169;border-radius:5px;")
    def _dot_idle(self): self.dot.setStyleSheet("background:#ccc;border-radius:5px;")
    def _log(self, msg, level="info"):
        c = {"success":"#a6e3a1","warn":"#f9e2af","error":"#f38ba8","info":"#cdd6f4"}.get(level,"#cdd6f4")
        self.log.moveCursor(QTextCursor.End)
        self.log.insertHtml(f'<span style="color:#6c7086">{time.strftime("%H:%M:%S")}</span>  <span style="color:{c}">{msg}</span><br>')
        self.log.moveCursor(QTextCursor.End)
    def _clr_log(self): self.log.clear()

    # ---------- 登录 ----------
    def _check_login(self):
        cfg = load(CFG("config.json")); u = cfg.get("username","")
        courses = load(CFG("courses.json"),[])
        if u and courses: self._load(u); return
        dlg = LoginDialog(self, prefill=u)
        if dlg.exec() == QDialog.Accepted: self._load(dlg.result_user)
        else:
            # 弹窗被关但可能已经登录成功（LoginDialog 内写了文件），再试一次
            cfg2 = load(CFG("config.json")); u2 = cfg2.get("username","")
            if u2 and load(CFG("courses.json"),[]): self._load(u2)
            else: self.close()

    def _load(self, u):
        self.acct.setText(f" {u}"); self._pop_courses()

    def _pop_courses(self):
        while self.cly.count()>1:
            w=self.cly.takeAt(0);
            if w.widget(): w.widget().deleteLater()
        self.course_checks.clear()
        courses = load(CFG("courses.json"),[]); wl = load(CFG("whitelist.json"),[])
        loc_db = load(CFG("locations.json"),{})
        if not courses:
            e = QLabel("暂无课程数据"); e.setStyleSheet("color:#999;padding:16px;"); e.setAlignment(Qt.AlignCenter)
            self.cly.insertWidget(0,e); self.cnt.setText(""); return
        for c in courses:
            k = f"{c['courseId']}_{c['clazzId']}"
            cb = QCheckBox(c["name"]); cb.setChecked(k in wl)
            cb.setStyleSheet("QCheckBox{spacing:6px;font-size:12px;padding:2px 0;} QCheckBox:hover{color:#4a6cf7;}")
            self.course_checks[k] = cb
            row = QWidget(); rl = QHBoxLayout(row); rl.setContentsMargins(6,1,10,1); rl.setSpacing(6)
            rl.addWidget(cb); rl.addStretch()
            if k in loc_db:
                lo = loc_db[k]
                tag = QLabel(f" {lo['lat']:.4f},{lo['lng']:.4f}"); tag.setStyleSheet("color:#38A169;font-size:9px;"); rl.addWidget(tag)
            if c.get("teacher"):
                t = QLabel(c["teacher"]); t.setStyleSheet("color:#bbb;font-size:10px;"); rl.addWidget(t)
            self.cly.insertWidget(self.cly.count()-1, row)
        checked = sum(1 for v in self.course_checks.values() if v.isChecked())
        self.cnt.setText(f"共{len(courses)}门 选{checked}")

    # ---------- 白名单 ----------
    def _all(self):
        for v in self.course_checks.values(): v.setChecked(True)
        self._upd_cnt()
    def _none(self):
        for v in self.course_checks.values(): v.setChecked(False)
        self._upd_cnt()
    def _save_wl(self):
        save(CFG("whitelist.json"), [k for k,v in self.course_checks.items() if v.isChecked()])
        self._upd_cnt(); self._log("白名单已保存","success")
    def _refresh(self):
        self._rt = RefreshThread(); self._rt.log.connect(self._log)
        self._rt.done.connect(self._pop_courses); self._rt.start()
    def _upd_cnt(self):
        cs = load(CFG("courses.json"),[]); chk = sum(1 for v in self.course_checks.values() if v.isChecked())
        self.cnt.setText(f"共{len(cs)}门 选{chk}")

    # ---------- 签到 ----------
    def _start(self):
        if self.sign_running: return
        wl = [k for k,v in self.course_checks.items() if v.isChecked()]
        if not wl: self._log("请先选择课程","warn"); return
        cs = load(CFG("courses.json"),[])
        targets = [c for c in cs if f"{c['courseId']}_{c['clazzId']}" in wl]
        self.sign_running = True; self.btn.setText("签到中..."); self.btn.setEnabled(False)
        self._dot_running(); self.sts.setText("签到中...")
        self._clr_log(); self._log(f"开始签到,{len(targets)}门","info")
        self._st = SignThread(targets)
        self._st.log.connect(self._log); self._st.done.connect(self._done)
        self._st.start()

    def _done(self):
        self.sign_running = False; self.btn.setText("  开始签到"); self.btn.setEnabled(True)
        self._dot_idle(); self.sts.setText("就绪"); self._pop_courses()

if __name__ == "__main__":
    app = QApplication(sys.argv); app.setFont(QFont("Microsoft YaHei",10))
    MainWindow().show(); sys.exit(app.exec())
