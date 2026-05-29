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

### 方式一：Python 源码

```bash
pip install -r requirements.txt
python app.py
```

### 方式二：打包版（无需 Python）

下载 [Releases](../../releases) 中的 `ChaoxingSign_vX.X.zip`，解压双击 `启动签到.exe`。

## 文件结构

```
├── app.py              # PySide6 GUI
├── chaoxing_sign.py    # 签到核心逻辑
├── triangulate.py      # 三角定位算法
├── 启动签到.pyw         # 无黑框启动器
├── config.json         # 配置文件（首次运行自动生成）
├── requirements.txt    # 依赖
└── start.bat           # 一键启动
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
