#!/usr/bin/env python3
"""工作线程 —— 通过注入的 SignService + ConfigManager 操作，不直接读写文件"""
import time, traceback
from PySide6.QtCore import QThread, Signal


class RefreshWorker(QThread):
    log = Signal(str, str)
    done = Signal()

    def __init__(self, service, config):
        super().__init__()
        self._svc = service
        self._cfg = config

    def run(self):
        try:
            self._svc.login()
            cl = self._svc.fetch_courses()
            old = self._cfg.get_whitelist()
            nk = {f"{c['courseId']}_{c['clazzId']}" for c in cl}
            wl = [k for k in old if k in nk] + [
                f"{c['courseId']}_{c['clazzId']}" for c in cl
                if f"{c['courseId']}_{c['clazzId']}" not in old]
            self._cfg.save_courses(cl)
            self._cfg.save_whitelist(wl)
            self.log.emit(f"课程已更新，共{len(cl)}门", "success")
        except Exception as e:
            self.log.emit(f"更新失败:{e}", "error")
        self.done.emit()


class SignWorker(QThread):
    """手动签到：调用 SignService.scan_and_sign 一次"""
    log = Signal(str, str)
    done = Signal()

    def __init__(self, service, config, targets):
        super().__init__()
        self._svc = service
        self._cfg = config
        self._targets = targets

    def run(self):
        try:
            self._svc.login()
            self.log.emit("登录成功", "success")
            result = self._svc.scan_and_sign(self._targets)
            for msg, lvl in result.logs:
                self.log.emit(msg, lvl)
            msg = f"完成,共{result.total}个活动" if result.total else "无有效活动"
            self.log.emit(msg, "success" if result.total else "info")
        except Exception as e:
            self.log.emit(f"异常:{e}", "error")
            self.log.emit(traceback.format_exc(), "error")
        self.done.emit()


class MonitorWorker(QThread):
    """持续监听：循环调用 scan_and_sign，间隔/浮动由 ConfigManager 控制"""
    log = Signal(str, str)
    tick = Signal(int)
    state = Signal(bool)

    def __init__(self, service, config):
        super().__init__()
        self._svc = service
        self._cfg = config
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        try:
            self._svc.login()
            self.log.emit("登录成功", "success")

            base, jitter = self._cfg.get_monitor_settings()
            if jitter:
                self.log.emit(
                    f"持续监听已启动 · 基准{base}秒 ±{jitter}%浮动", "success")
            else:
                self.log.emit(
                    f"持续监听已启动 · 每{base}秒扫描白名单", "success")

            while self._running:
                courses = self._cfg.get_courses()
                wl = self._cfg.get_whitelist()
                targets = [c for c in courses
                           if f"{c['courseId']}_{c['clazzId']}" in wl]

                result = self._svc.scan_and_sign(
                    targets, stop_check=lambda: not self._running)
                for msg, lvl in result.logs:
                    self.log.emit(msg, lvl)
                if result.total:
                    self.log.emit(
                        f"本轮完成 · 共签到{result.total}个活动", "success")

                wait = self._svc.calc_wait()
                for i in range(wait, 0, -1):
                    if not self._running:
                        break
                    self.tick.emit(i)
                    time.sleep(1)
        except Exception as e:
            self.log.emit(f"监听异常:{e}", "error")
            self.log.emit(traceback.format_exc(), "error")

        self.tick.emit(0)
        self.state.emit(False)
