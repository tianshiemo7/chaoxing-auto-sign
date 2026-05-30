#!/usr/bin/env python3
"""三角定位算法测试 —— 模拟学习通签到 API，验证定位精度和效率"""
import math, time, random, sys
sys.path.insert(0, '.')
from triangulate import Triangulator, METERS_PER_DEG_LAT, _cos_lat

# ============================================================
# 模拟器
# ============================================================

def haversine(lat1, lng1, lat2, lng2):
    """计算两点间真实距离（米），作为模拟API的距离基准"""
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def create_mock_api(target_lat, target_lng, noise_meters=1.0):
    """
    创建模拟的 do_sign / is_success 回调对。

    参数:
      target_lat, target_lng: 真实签到点
      noise_meters: API 返回距离的高斯噪声标准差（米），模拟真实 API 精度

    返回 (do_sign, is_success)
    """
    call_count = [0]  # 用列表包装以支持闭包内修改

    def do_sign(lat_str, lng_str):
        call_count[0] += 1
        lat, lng = float(lat_str), float(lng_str)
        d = haversine(lat, lng, target_lat, target_lng)
        # 叠加高斯噪声（模拟真实 API 精度，但不会 < 0）
        noise = random.gauss(0, noise_meters)
        d_noisy = max(0.0, d + noise)
        time.sleep(0.01)  # 模拟网络延迟（测试中加速）
        if d < 0.5:  # 距离 < 0.5m 视为签到成功
            return '{"status":"success"}'
        return f'{{"status":"fail","msg":"距离签到点还有{d_noisy:.1f}米"}}'

    def is_success(text):
        return 'success' in text.lower()

    return do_sign, is_success, call_count


# ============================================================
# 测试用例
# ============================================================

def run_test(label, target_lat, target_lng, start_lat, start_lng,
             noise=1.0, expected_ok=True):
    """执行单次测试并返回结果"""
    do_sign, is_success, calls = create_mock_api(target_lat, target_lng, noise)
    tri = Triangulator(do_sign, is_success)
    ok, found_lat, found_lng = tri.locate(start_lat, start_lng)
    error = haversine(found_lat, found_lng, target_lat, target_lng) if ok else None
    direct_dist = haversine(start_lat, start_lng, target_lat, target_lng)

    status = "OK" if ok else "FAIL"
    if error is not None:
        detail = f"error={error:.1f}m"
    else:
        detail = "expected OK" if expected_ok else "expected fail"
    print(f"\n{'─'*60}")
    print(f"  {label}")
    print(f"  start dist={direct_dist:.0f}m  noise=±{noise:.1f}m")
    print(f"  result={status}  {detail}  calls={calls[0]}  pos=({found_lat:.6f},{found_lng:.6f})")
    return {"ok": ok, "error": error, "calls": calls[0],
            "found": (found_lat, found_lng), "direct_dist": direct_dist}


def run_batch(name, target, starts, noise=1.0, expected_ok=True):
    """批量跑一组测试并统计"""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"  目标: ({target[0]:.6f}, {target[1]:.6f})")
    errors, calls = [], []
    for label, slat, slng in starts:
        r = run_test(label, target[0], target[1], slat, slng, noise, expected_ok)
        if r["ok"]:
            errors.append(r["error"])
        calls.append(r["calls"])

    if errors:
        print(f"\n  ── 统计 ──")
        print(f"  成功率: {len(errors)}/{len(starts)}")
        print(f"  误差: avg={sum(errors)/len(errors):.1f}m  max={max(errors):.1f}m  min={min(errors):.1f}m")
        print(f"  API请求: avg={sum(calls)/len(calls):.1f}次  max={max(calls)}次  min={min(calls)}次")
    else:
        print(f"\n  全部失败")


# ============================================================
# 主测试
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    QUST_DEFAULT = (36.1087, 120.4682)  # 青岛科技大学崂山校区

    # ── 测试1：近距离（缓存命中场景）──
    # 上次签到成功后缓存了坐标，这次签同一位置，起点就是目标附近
    run_batch("【测试1】近距离 —— 模拟缓存命中",
              target=QUST_DEFAULT,
              starts=[
                  ("同位置",     36.1087, 120.4682),
                  ("偏移 10m",   36.1088, 120.4683),
                  ("偏移 50m",   36.1091, 120.4685),
                  ("偏移 100m",  36.1095, 120.4688),
              ], noise=1.0)

    # ── 测试2：中距离（不同教学楼）──
    # 同一校园内不同位置，几百米级别
    run_batch("【测试2】中距离 —— 不同教学楼",
              target=QUST_DEFAULT,
              starts=[
                  ("约 300m",   36.1058, 120.4660),
                  ("约 500m",   36.1043, 120.4651),
                  ("约 1km",    36.1000, 120.4620),
                  ("约 2km",    36.0910, 120.4600),
              ], noise=1.0)

    # ── 测试3：远距离（默认坐标兜底）──
    # 缓存坐标失效，从很远的地方出发
    run_batch("【测试3】远距离 —— 默认坐标兜底",
              target=QUST_DEFAULT,
              starts=[
                  ("约 5km",   36.0640, 120.4500),
                  ("约 10km",  36.0200, 120.4400),
                  ("约 50km",  35.6600, 120.3800),
                  ("约 100km", 35.2200, 120.3000),
              ], noise=1.0)

    # ── 测试4：极端距离（青岛市外）──
    run_batch("【测试4】极端距离 —— 其他城市",
              target=QUST_DEFAULT,
              starts=[
                  ("济南 ~300km",  36.6512, 116.9972),
                  ("北京 ~550km",  39.9042, 116.4074),
                  ("上海 ~550km",  31.2304, 121.4737),
              ], noise=1.0)

    # ── 测试5：高噪声环境 ──
    run_batch("【测试5】高噪声 —— 模拟 API 精度差",
              target=QUST_DEFAULT,
              starts=[
                  ("50m 噪声5m",   36.1090, 120.4690),
                  ("200m 噪声5m",  36.1100, 120.4700),
                  ("500m 噪声10m", 36.1130, 120.4720),
                  ("1km 噪声20m",  36.1180, 120.4750),
              ], noise=5.0)

    # ── 测试6：成功率压力测试 ──
    print(f"\n{'='*60}")
    print(f"  【测试6】压力测试 —— 100 个随机起点")
    target = QUST_DEFAULT
    successes, total_errors, total_calls = 0, [], []
    for i in range(100):
        # 随机偏移 10m ~ 100km
        angle = random.uniform(0, 2 * math.pi)
        dist = 10 ** random.uniform(1, 5)  # 10m ~ 100km 对数均匀
        dlat = dist / METERS_PER_DEG_LAT * math.cos(angle)
        dlng = dist / (METERS_PER_DEG_LAT * _cos_lat(target[0])) * math.sin(angle)
        slat, slng = target[0] + dlat, target[1] + dlng
        r = run_test(f"#{i+1}", target[0], target[1], slat, slng,
                     noise=random.uniform(0, 3),
                     expected_ok=True)
        if r["ok"]:
            successes += 1
            total_errors.append(r["error"])
        total_calls.append(r["calls"])

    print(f"\n  ── 压力测试统计 ──")
    print(f"  成功率: {successes}/100")
    if total_errors:
        print(f"  误差: avg={sum(total_errors)/len(total_errors):.1f}m"
              f"  max={max(total_errors):.1f}m  min={min(total_errors):.1f}m")
    print(f"  API请求: avg={sum(total_calls)/len(total_calls):.1f}次"
          f"  max={max(total_calls)}次  min={min(total_calls)}次")

    print(f"\n{'='*60}")
    print("  测试完毕。")
