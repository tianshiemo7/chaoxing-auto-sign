#!/usr/bin/env python3
"""学习通签到核心：登录、课程、签到、三角定位"""
import time, base64
from urllib.parse import urlencode
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from triangulate import Triangulator, parse_distance

BASE_ADDRESS = "青岛科技大学"
USER_AGENT = ("Mozilla/5.0 (Linux; Android 12; Pixel 6) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")
AES_KEY = "u2oh6Vu^HWe4_AES"

class ChaoXingSign:
    def __init__(self, username, password):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        self.username = username
        self.password = password
        self.uid = ""
        self.name = "同学"

    @staticmethod
    def _encrypt_aes(message):
        key = AES_KEY.encode("utf-8")
        cipher = AES.new(key, AES.MODE_CBC, iv=key)
        return base64.b64encode(cipher.encrypt(pad(message.encode(), AES.block_size))).decode()

    @staticmethod
    def _is_success(text):
        return "success" in text.lower() or "已签到" in text or "簽到" in text

    def login(self):
        self.session.get(
            "https://passport2.chaoxing.com/mlogin?fid=&newversion=true&refer=http://i.chaoxing.com")
        resp = self.session.post("https://passport2.chaoxing.com/fanyalogin", data={
            "fid": "-1", "t": "true", "forbidotherlogin": "0",
            "doubleFactorLogin": "0", "independentId": "0",
            "uname": self._encrypt_aes(self.username),
            "password": self._encrypt_aes(self.password),
        }, allow_redirects=True)
        try:
            result = resp.json()
        except ValueError:
            raise Exception(f"登录返回异常: {resp.text[:200]}")
        if not result.get("status"):
            raise Exception(f"登录失败: {result.get('msg2', '账号或密码错误')}")
        self.session.get(result.get("url", "http://i.chaoxing.com"), allow_redirects=True)
        for c in self.session.cookies:
            if c.name == "_uid": self.uid = c.value; break
        return True

    def get_courses(self):
        resp = self.session.get(
            "https://mooc1-api.chaoxing.com/mycourse/backclazzdata?"
            + urlencode({"courseType":"1","courseFolderId":"0","query":"","superstarClass":"0"}))
        channels = []
        for ch in resp.json().get("channelList", []):
            cd = ch.get("content", {}).get("course", {}).get("data", [{}])[0]
            channels.append({
                "courseId": cd.get("id",""), "clazzId": ch["content"].get("id",""),
                "name": cd.get("name","未知课程"), "teacher": cd.get("teacherfactor",""),
            })
        return channels

    def get_active_signs(self, course):
        resp = self.session.get(
            f"https://mobilelearn.chaoxing.com/v2/apis/active/student/activelist?"
            f"fid=0&courseId={course['courseId']}&classId={course['clazzId']}"
            f"&showNotStartedActive=0")
        now_ms = int(time.time() * 1000)
        signs = []
        for a in resp.json().get("data",{}).get("activeList",[]):
            try: et = int(a.get("endTime",0) or 0)
            except (ValueError, TypeError): et = 0
            if 0 < et < now_ms: continue
            signs.append({"activeId":a["id"], "name":a.get("nameOne","签到"),
                          "type":a.get("activeType"), "status":a.get("status"),
                          "userStatus":a.get("userStatus",0),
                          "courseId":course["courseId"], "clazzId":course["clazzId"],
                          "endTime":et})
        return signs

    def _do_sign(self, si, lat="-1", lng="-1"):
        self.session.get(
            f"https://mobilelearn.chaoxing.com/pptSign/analysis?"
            f"activeId={si['activeId']}&code=&uid={self.uid}")
        params = {"activeId":si["activeId"], "uid":self.uid, "clientip":"",
                  "latitude":lat, "longitude":lng, "appType":"15", "ifTiJiao":"1",
                  "address": BASE_ADDRESS}
        return self.session.get("https://mobilelearn.chaoxing.com/pptSign/stuSignajax",
                                params=params).text

    DEFAULT_LAT, DEFAULT_LNG = 36.1087, 120.4682

    def _triangulate(self, si, start_lat, start_lng):
        tri = Triangulator(
            lambda lt, ln: self._do_sign(si, lat=lt, lng=ln),
            self._is_success)
        return tri.locate(start_lat, start_lng)

    def sign(self, si, lat="-1", lng="-1"):
        r = self._do_sign(si, lat=lat, lng=lng)
        if self._is_success(r):
            return {"status": "success"}

        dist = parse_distance(r)
        if dist is None:
            return {"status": "unknown", "raw": r}

        use_lat = float(lat) if lat != "-1" else self.DEFAULT_LAT
        use_lng = float(lng) if lng != "-1" else self.DEFAULT_LNG

        # 第一次：从给定坐标（缓存/上次）出发三角定位
        ok, nl, ng = self._triangulate(si, use_lat, use_lng)
        if ok:
            return {"status": "success", "lat": nl, "lng": ng}

        # 缓存坐标太远定位失败 → 回退到默认坐标重试
        if abs(use_lat - self.DEFAULT_LAT) > 0.001 or abs(use_lng - self.DEFAULT_LNG) > 0.001:
            ok2, nl2, ng2 = self._triangulate(si, self.DEFAULT_LAT, self.DEFAULT_LNG)
            if ok2:
                return {"status": "success", "lat": nl2, "lng": ng2}

        return {"status": "fail", "raw": r}
