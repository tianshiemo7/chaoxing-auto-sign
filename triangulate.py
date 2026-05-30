#!/usr/bin/env python3
"""三角定位模块：自适应步长迭代收缩 —— 三点定位逐次逼近"""
import re, time, math

METERS_PER_DEG_LAT = 111320.0
SIGN_RANGE = 20             # 距离小于此值认为签到成功
MAX_ROUNDS = 20             # 安全上限
MIN_STEP = 0.00001          # 最小步长（度）≈ 1.1m
MAX_STEP = 0.5              # 最大步长（度）≈ 55km
STEP_RATIO = 0.4            # 步长 / 当前距离 比例
MAX_OFFSET_RATIO = 3.0      # 解算偏移 clamp 上限（相对步长的倍数）
MEASURE_RETRIES = 1         # measure 失败重试次数


def parse_distance(text):
    """从 API 返回文本提取距离（米）"""
    m = re.search(r'([\d.]+)\s*米', text)
    return float(m.group(1)) if m else None


def _cos_lat(lat):
    """纬度余弦：修正不同纬度下经度对应的实际距离"""
    return math.cos(math.radians(lat))


class Triangulator:
    """do_sign(lat_str, lng_str) -> 返回签到API原始文本, is_success(text) -> bool"""

    def __init__(self, do_sign, is_success):
        self._do_sign = do_sign
        self._is_success = is_success

    def measure(self, lat, lng):
        """单点测量：返回 0=成功, float=距离(米), None=解析失败（含重试）"""
        for attempt in range(MEASURE_RETRIES + 1):
            r = self._do_sign(str(lat), str(lng))
            if self._is_success(r):
                return 0
            d = parse_distance(r)
            if d is not None:
                return d
            if attempt < MEASURE_RETRIES:
                time.sleep(0.3)
        return None

    def locate(self, start_lat, start_lng):
        """自适应三角定位：步长随距离动态缩放，收敛即止"""
        cl, cn = start_lat, start_lng
        df = None  # 上一轮验证距离，首轮为 None 表示需要实测 d0

        for _ in range(MAX_ROUNDS):
            # ── 测量 / 复用 P0 ──
            if df is not None:
                d0 = df       # 复用上一轮验证结果，省一次请求
            else:
                d0 = self.measure(cl, cn)
                if d0 == 0:
                    return True, cl, cn
                if d0 is None:
                    return False, cl, cn
                time.sleep(0.2)

            # 已进入签到范围 → 成功
            if d0 is not None and d0 < SIGN_RANGE:
                return True, cl, cn

            # ── 自适应步长 ──
            step = (d0 / METERS_PER_DEG_LAT) * STEP_RATIO if d0 else MIN_STEP
            step = max(MIN_STEP, min(MAX_STEP, step))
            cs = _cos_lat(cl)

            # ── 测量 P1（北偏）──
            d1 = self.measure(cl + step, cn)
            if d1 == 0:
                return True, cl + step, cn
            if d1 is None:
                return False, cl, cn
            time.sleep(0.2)

            # ── 测量 P2（东偏）──
            d2 = self.measure(cl, cn + step)
            if d2 == 0:
                return True, cl, cn + step
            if d2 is None:
                return False, cl, cn
            time.sleep(0.2)

            # ── 三角解算 ──
            dy = step * METERS_PER_DEG_LAT
            dx = step * METERS_PER_DEG_LAT * cs
            y_t = (d0 * d0 - d1 * d1 + dy * dy) / (2 * dy)
            x_t = (d0 * d0 - d2 * d2 + dx * dx) / (2 * dx)

            # ── 范围校验：clamp 异常跳变 ──
            max_offset = step * METERS_PER_DEG_LAT * MAX_OFFSET_RATIO
            y_t = max(-max_offset, min(max_offset, y_t))
            x_t = max(-max_offset, min(max_offset, x_t))

            cl = cl + y_t / METERS_PER_DEG_LAT
            cn = cn + x_t / (METERS_PER_DEG_LAT * cs)

            # ── 验证解算结果 ──
            time.sleep(0.2)
            df = self.measure(cl, cn)
            if df == 0 or (df is not None and df < SIGN_RANGE):
                return True, cl, cn
            if df is None:
                return False, cl, cn

        # 安全上限
        return False, cl, cn
