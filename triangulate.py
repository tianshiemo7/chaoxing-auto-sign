#!/usr/bin/env python3
"""三角定位模块：大范围迭代收缩 —— 5轮三点定位逐次逼近"""
import re, time, math

METERS_PER_DEG_LAT = 111320.0
SIGN_RANGE = 20     # 距离小于此值认为签到成功
MAX_ROUNDS = 5      # 最多 5 轮迭代
INIT_STEP = 5.0     # 首轮步长（度），从"边境级"大范围开始


def parse_distance(text):
    m = re.search(r'([\d.]+)米', text)
    return float(m.group(1)) if m else None


def _cos_lat(lat):
    return math.cos(math.radians(lat))


class Triangulator:
    """do_sign(lat_str, lng_str) -> 返回签到API原始文本, is_success(text) -> bool"""

    def __init__(self, do_sign, is_success):
        self._do_sign = do_sign
        self._is_success = is_success

    def measure(self, lat, lng):
        r = self._do_sign(str(lat), str(lng))
        return 0 if self._is_success(r) else parse_distance(r)

    def locate(self, start_lat, start_lng):
        """5 轮迭代三角定位：步长从 5° → 0.5° → 0.05° → 0.005° → 0.0005°"""
        cl, cn = start_lat, start_lng

        for rnd in range(MAX_ROUNDS):
            step = INIT_STEP / (10 ** rnd)
            cs = _cos_lat(cl)

            # 本轮 3 个测量点：中心 / 中心北偏 / 中心东偏
            d0 = self.measure(cl, cn)
            if d0 == 0:
                return True, cl, cn
            if d0 is None:
                return False, cl, cn
            time.sleep(0.2)

            d1 = self.measure(cl + step, cn)
            if d1 == 0:
                return True, cl + step, cn
            if d1 is None:
                return False, cl, cn
            time.sleep(0.2)

            d2 = self.measure(cl, cn + step)
            if d2 == 0:
                return True, cl, cn + step
            if d2 is None:
                return False, cl, cn
            time.sleep(0.2)

            # 三角解算
            dy = step * METERS_PER_DEG_LAT
            dx = step * METERS_PER_DEG_LAT * cs
            y_t = (d0 * d0 - d1 * d1 + dy * dy) / (2 * dy)
            x_t = (d0 * d0 - d2 * d2 + dx * dx) / (2 * dx)

            cl = cl + y_t / METERS_PER_DEG_LAT
            cn = cn + x_t / (METERS_PER_DEG_LAT * cs)

            # 检查新估算点是否已足够近
            time.sleep(0.2)
            df = self.measure(cl, cn)
            if df == 0 or (df is not None and df < SIGN_RANGE):
                return True, cl, cn

        # 5 轮迭代后仍未进入 20 米范围 → 失败
        return False, cl, cn
