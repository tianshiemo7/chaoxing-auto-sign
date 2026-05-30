#!/usr/bin/env python3
"""配置管理层 —— 所有 JSON 文件读写的唯一入口，带内存缓存"""
import json, os


class ConfigManager:
    def __init__(self, base_dir):
        self._base = base_dir
        self._cache = {}

    def _path(self, filename):
        return os.path.join(self._base, filename)

    def _load(self, filename, default=None):
        if default is None:
            default = {}
        if filename not in self._cache:
            p = self._path(filename)
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as fh:
                    self._cache[filename] = json.load(fh)
            else:
                self._cache[filename] = default
        return self._cache[filename]

    def _save(self, filename, data):
        self._cache[filename] = data
        p = self._path(filename)
        try:
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
        except Exception as e:
            self._notify_error(f"保存文件失败：{p}\n\n{type(e).__name__}: {e}")
            raise

    @staticmethod
    def _notify_error(msg):
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, str(msg),
                "学习通签到 - 写入错误", 0x10)
        except Exception:
            pass

    # ---- 读 ----
    def get_config(self):
        return self._load("config.json", {
            "latitude": "36.1087", "longitude": "120.4682",
            "monitor_interval": 30, "monitor_jitter": 40,
            "night_mode": False})

    def get_courses(self):
        return self._load("courses.json", [])

    def get_whitelist(self):
        return self._load("whitelist.json", [])

    def get_locations(self):
        return self._load("locations.json", {})

    def get_account(self):
        cfg = self.get_config()
        return cfg.get("username", ""), cfg.get("password", "")

    def get_coords_default(self):
        cfg = self.get_config()
        return cfg.get("latitude", "36.1087"), cfg.get("longitude", "120.4682")

    def get_monitor_settings(self):
        cfg = self.get_config()
        interval = max(5, min(3600, int(cfg.get("monitor_interval", 30))))
        jitter = max(0, min(100, int(cfg.get("monitor_jitter", 40))))
        return interval, jitter

    def is_night_mode(self):
        return self.get_config().get("night_mode", False)

    # ---- 写 ----
    def save_config(self, updates: dict):
        cfg = self.get_config()
        cfg.update(updates)
        self._save("config.json", cfg)

    def save_courses(self, courses: list):
        self._save("courses.json", courses)

    def save_whitelist(self, keys: list):
        self._save("whitelist.json", keys)

    def save_locations(self, loc_db: dict):
        self._save("locations.json", loc_db)

    def save_credentials(self, username, password):
        self.save_config({"username": username, "password": password})

    # ---- 缓存控制 ----
    def invalidate(self, filename=None):
        if filename:
            self._cache.pop(filename, None)
        else:
            self._cache.clear()
