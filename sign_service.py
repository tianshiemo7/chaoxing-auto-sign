#!/usr/bin/env python3
"""业务服务层 —— 封装 ChaoXingSign 实例、签到扫描、坐标管理"""
import time, random, traceback
from dataclasses import dataclass, field
from chaoxing_sign import ChaoXingSign
from config_manager import ConfigManager


@dataclass
class SignResult:
    """一轮扫描的完整结果"""
    total: int = 0
    locations_updated: bool = False
    logs: list = field(default_factory=list)  # list of (msg, level)

    def add_log(self, msg, level):
        self.logs.append((msg, level))


class SignService:
    def __init__(self, config: ConfigManager):
        self._cfg = config
        self._signer = None

    # ---- 登录 / 会话 ----
    def login(self, username=None, password=None):
        if username is None:
            username, password = self._cfg.get_account()
        if not username or not password:
            raise ValueError("账号密码未配置")
        self._signer = ChaoXingSign(username, password)
        self._signer.login()
        return True

    @property
    def is_logged_in(self):
        return self._signer is not None

    # ---- 课程 ----
    def fetch_courses(self):
        if not self.is_logged_in:
            raise RuntimeError("未登录")
        raw = self._signer.get_courses()
        return [{"courseId": c["courseId"], "clazzId": c["clazzId"],
                 "name": c["name"], "teacher": c["teacher"]} for c in raw]

    # ---- 扫描签到 ----
    def scan_and_sign(self, targets, stop_check=None):
        """执行一轮扫描签到。stop_check 返回 True 时中断。
        返回 SignResult。"""
        result = SignResult()
        if not self.is_logged_in:
            result.add_log("未登录，无法签到", "error")
            return result

        dl, dln = self._cfg.get_coords_default()
        loc_db = self._cfg.get_locations()

        for c in targets:
            if stop_check and stop_check():
                break
            lk = f"{c['courseId']}_{c['clazzId']}"
            sv = loc_db.get(lk, {})
            lat = sv.get("lat", dl) if sv else dl
            lng = sv.get("lng", dln) if sv else dln
            if sv:
                result.add_log(
                    f"[{c['name']}] 坐标({lat:.4f},{lng:.4f})", "info")

            try:
                signs = self._signer.get_active_signs(c) or []
                if signs:
                    result.add_log(
                        f"[{c['name']}] {len(signs)}个活动", "info")
                for s in signs:
                    if stop_check and stop_check():
                        break
                    result.add_log(f"  -> {s['name']}", "info")
                    r = self._signer.sign(s, lat=lat, lng=lng)
                    st = r.get("status")
                    if st == "success":
                        nl, ng = r.get("lat"), r.get("lng")
                        if nl is not None and ng is not None:
                            loc_db[lk] = {
                                "lat": nl, "lng": ng,
                                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
                            result.locations_updated = True
                            result.add_log(
                                f"  坐标缓存({nl:.4f},{ng:.4f})", "success")
                        result.add_log(f"  -> 签到成功!", "success")
                    else:
                        result.add_log(f"  -> {st}", "warn")
                    result.total += 1
            except Exception as e:
                result.add_log(f"[{c['name']}] 出错:{e}", "error")
                result.add_log(traceback.format_exc(), "error")

        if result.locations_updated:
            self._cfg.save_locations(loc_db)
        return result

    # ---- 监控间隔计算 ----
    def calc_wait(self):
        base, jitter = self._cfg.get_monitor_settings()
        if jitter > 0:
            factor = 1 + random.uniform(-jitter / 100, jitter / 100)
            return max(1, int(base * factor))
        return base
