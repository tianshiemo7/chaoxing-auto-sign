# 学习通自动签到

PySide6 桌面应用，自动完成学习通**普通签到**和**位置签到**（三角定位），支持持续监听。

## 功能

- 登录并获取课程列表
- 白名单选择需签到的课程
- **手动签到**：一键扫描所有课程的有效签到活动
- **持续监听**：后台循环扫描，自动签到，间隔和浮动可配置
- 普通签到：自动完成
- 位置签到：以配置的经纬度为起点，三角定位算法自动逼近签到点
- 签到位置按课程自动缓存；修改经纬度或地址后自动重新定位
- 夜间模式 / 侧边栏导航 / 设置页面

## 运行

### 方式一：一键启动（推荐，无需 Python）

下载 [Releases](../../releases) 中最新的 `ChaoxingSign_vX.X_Release.zip`，解压后双击 `ChaoxingSign.exe`。

### 方式二：Python 源码

```bash
pip install -r requirements.txt
python app.py
# 或直接双击  start.bat  （会自动检查环境、安装依赖）
```

## 文件结构

```
├── app.py              # PySide6 GUI（纯界面层）
├── chaoxing_sign.py    # 签到核心：登录、课程、活动、签到
├── triangulate.py      # 三角定位算法（自适应迭代收缩）
├── sign_service.py     # 业务服务层：签到扫描、坐标管理
├── config_manager.py   # 配置管理层：所有 JSON 读写唯一入口
├── workers.py          # 工作线程：刷新课程、手动签到、持续监听
├── ChaoxingSign.spec   # PyInstaller 打包配置
├── 启动签到.pyw         # 无黑框启动器
├── start.bat           # 一键启动（自动装依赖）
├── build.bat           # 一键打包构建
├── config.example.json # 配置模板
├── requirements.txt    # 依赖
├── test_triangulate.py # 三角定位测试程序
├── config.json         # 配置文件（首次登录后自动生成，请勿提交）
├── courses.json        # 课程缓存（运行时生成，请勿提交）
├── whitelist.json      # 课程白名单（运行时生成，请勿提交）
└── locations.json      # 课程定位缓存（运行时生成，请勿提交）
```

## 三角定位算法

位置签到时，学习通 API 不直接给出正确坐标，而是返回"距离签到点还有 X 米"。利用这一特性，通过**自适应迭代三点定位**反推真实位置：

- 在当前位置及北偏、东偏各测一次距离
- 三组距离做三角解算，估算目标方位
- 步长随距离动态缩放：远距离大步快跑，近距离精细逼近
- 收敛至 20m 以内即视为成功

相较于固定步长的 5 轮 20 次请求，优化后典型场景仅需 **4~7 次** API 请求。

```bash
# 运行测试
python test_triangulate.py
```

## 配置

首次登录弹窗会收集账号、密码、经纬度和地址，并统一写入 `config.json`。课程、白名单和定位缓存会在运行时自动生成。

`latitude`、`longitude` 和 `address` 是位置签到的初始定位参数。程序定位成功后会按课程缓存结果；修改其中任一参数会自动使旧缓存失效，并从新的经纬度重新定位。

`config.json` 完整配置项：

```json
{
    "username": "你的手机号",
    "password": "你的密码",
    "latitude": "",
    "longitude": "",
    "address": "",
    "monitor_interval": 30,
    "monitor_jitter": 40,
    "night_mode": false
}
```

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `username` / `password` | 学习通账号密码 | 空 |
| `latitude` / `longitude` | 位置签到的初始经纬度 | 必填 |
| `address` | 位置签到提交的地址文字 | 必填 |
| `monitor_interval` | 持续监听扫描间隔（秒） | 30 |
| `monitor_jitter` | 间隔随机浮动百分比（0~100） | 40 |
| `night_mode` | 夜间模式 | false |

请仅填写学校规则允许且与实际签到地点一致的信息。`config.json` 含有账号和密码，请勿发送或提交到 GitHub。

## 打包

先安装打包工具：

```bash
python -m pip install pyinstaller
```

然后运行 `build.bat`。构建脚本应使用 `python -m PyInstaller`，避免依赖 `pyinstaller` 是否已加入 PATH。最终发布文件在 `dist/`；`build/`、`__pycache__/` 和自动生成的 `app.spec` 都是临时文件，不应提交或发送。

## 免责声明

本工具仅供学习交流，请勿用于违规用途。
