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
    def login(self, username=None, password=None, address=None):
        if username is None:
            username, password = self._cfg.get_account()
        if not username or not password:
            raise ValueError("账号密码未配置")
        if address is None:
            address = self._cfg.get_address()
        self._signer = ChaoXingSign(username, password, address=address)
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

        dl, dln, address = self._cfg.get_signing_location()
        self._signer.address = address
        loc_db = self._cfg.get_locations()
        cache_changed = False

        for c in targets:
            if stop_check and stop_check():
                break
            lk = f"{c['courseId']}_{c['clazzId']}"
            lat, lng = dl, dln
            cached_location = loc_db.get(lk, {})
            if self._is_location_cache_current(cached_location, dl, dln, address):
                lat = float(cached_location["lat"])
                lng = float(cached_location["lng"])
                result.add_log(
                    f"[{c['name']}] 使用缓存坐标({lat:.4f},{lng:.4f})", "info")
            else:
                if cached_location:
                    loc_db.pop(lk, None)
                    cache_changed = True
                result.add_log(
                    f"[{c['name']}] 使用配置起点({float(lat):.4f},{float(lng):.4f})", "info")

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
                                "source_latitude": dl,
                                "source_longitude": dln,
                                "source_address": address,
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

        if result.locations_updated or cache_changed:
            self._cfg.save_locations(loc_db)
        return result

    @staticmethod
    def _is_location_cache_current(location, latitude, longitude, address):
        """仅复用由当前配置起点和地址生成的定位缓存。"""
        try:
            float(location["lat"])
            float(location["lng"])
        except (KeyError, TypeError, ValueError):
            return False
        return (
            isinstance(location, dict)
            and location.get("source_latitude") == latitude
            and location.get("source_longitude") == longitude
            and location.get("source_address") == address
        )

    # ---- 监控间隔计算 ----
    def calc_wait(self):
        base, jitter = self._cfg.get_monitor_settings()
        if jitter > 0:
            factor = 1 + random.uniform(-jitter / 100, jitter / 100)
            return max(1, int(base * factor))
        return base
