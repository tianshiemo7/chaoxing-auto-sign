#!/usr/bin/env python3
"""三角定位模块：三点测距 -> 解算目标经纬度 -> 梯度精调"""
import re, time, math

METERS_PER_DEG_LAT = 111320.0
SIGN_RANGE = 20  # 距离小于此值认为签到成功


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

    def locate(self, start_lat, start_lng, step_deg=0.003):
        bl = start_lat
        cs = _cos_lat(bl)

        d0 = self.measure(start_lat, start_lng)
        if d0 == 0: return True, start_lat, start_lng
        if d0 is None: return False, start_lat, start_lng
        time.sleep(0.2)

        d1 = self.measure(start_lat + step_deg, start_lng)
        if d1 == 0: return True, start_lat + step_deg, start_lng
        if d1 is None: return False, start_lat, start_lng
        time.sleep(0.2)

        d2 = self.measure(start_lat, start_lng + step_deg)
        if d2 == 0: return True, start_lat, start_lng + step_deg
        if d2 is None: return False, start_lat, start_lng

        # 三角解算
        dy = step_deg * METERS_PER_DEG_LAT
        dx = step_deg * METERS_PER_DEG_LAT * cs
        y_t = (d0 * d0 - d1 * d1 + dy * dy) / (2 * dy)
        x_t = (d0 * d0 - d2 * d2 + dx * dx) / (2 * dx)

        t_lat = start_lat + y_t / METERS_PER_DEG_LAT
        t_lng = start_lng + x_t / (METERS_PER_DEG_LAT * cs)

        time.sleep(0.2)
        df = self.measure(t_lat, t_lng)
        if df == 0 or (df is not None and df < SIGN_RANGE):
            return True, t_lat, t_lng
        if df is None:
            return False, start_lat, start_lng

        return self._fine_tune(t_lat, t_lng, df)

    def _fine_tune(self, lat, lng, dist, max_iter=5):
        if dist < SIGN_RANGE:
            return True, lat, lng
        delta = 0.0003
        for _ in range(max_iter):
            best_lat, best_lng, best_d = lat, lng, dist
            improved = False
            for cl, cln in [(lat + delta, lng), (lat - delta, lng),
                             (lat, lng + delta), (lat, lng - delta)]:
                d = self.measure(cl, cln)
                if d == 0 or (d is not None and d < SIGN_RANGE):
                    return True, cl, cln
                if d is not None and d < best_d:
                    best_lat, best_lng, best_d = cl, cln, d
                    improved = True
            if improved:
                lat, lng, dist = best_lat, best_lng, best_d
                if dist < SIGN_RANGE: return True, lat, lng
                time.sleep(0.2)
            else:
                delta /= 2
                if delta < 1e-6: break
        return dist < SIGN_RANGE, lat, lng
