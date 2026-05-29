# 学习通自动签到

PySide6 桌面应用，自动完成学习通**普通签到**和**位置签到**（三角定位）。

## 功能

- 登录并获取课程列表
- 白名单选择需签到的课程
- 一键扫描所有课程的有效签到活动
- 普通签到：自动完成
- 位置签到：三角定位算法自动推算老师坐标
- 签到位置自动缓存，下次复用

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
├── app.py              # PySide6 GUI
├── chaoxing_sign.py    # 签到核心逻辑
├── triangulate.py      # 三角定位算法
├── ChaoxingSign.spec   # PyInstaller 打包配置
├── 启动签到.pyw         # 无黑框启动器
├── start.bat           # 一键启动（自动装依赖）
├── build.bat           # 一键打包构建
├── config.example.json # 配置模板
├── requirements.txt    # 依赖
└── config.json         # 配置文件（首次运行自动生成）
```

## 配置

首次运行后自动生成 `courses.json`、`whitelist.json`、`locations.json`，无需手动编辑。

`config.json` 中可修改默认签到坐标：

```json
{
    "username": "你的手机号",
    "password": "你的密码",
    "latitude": "36.1087",
    "longitude": "120.4682"
}
```

## 免责声明

本工具仅供学习交流，请勿用于违规用途。
