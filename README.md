# 天文望远镜自动化系统 / Telescope Automation System

> 基于 Raspberry Pi 的天文望远镜自动化控制系统，支持星体定位、步进电机驱动、视频流传输与 Web 远程控制。
>
> A Raspberry Pi-based telescope automation system with star locating, stepper motor control, video streaming, and web remote control.

---

## 目录 / Table of Contents

- [功能概览 / Features](#功能概览--features)
- [硬件需求 / Hardware Requirements](#硬件需求--hardware-requirements)
- [系统架构 / System Architecture](#系统架构--system-architecture)
- [依赖安装 / Install Dependencies](#依赖安装--install-dependencies)
- [配置 / Configuration](#配置--configuration)
- [运行 / Run](#运行--run)
- [Web 控制界面 / Web Control Interface](#web-控制界面--web-control-interface)
- [模块说明 / Module Guide](#模块说明--module-guide)
- [目录结构 / Project Layout](#目录结构--project-layout)

---

## 功能概览 / Features

- 🌟 **星体定位**：输入天体赤经 (RA) / 赤纬 (DEC)，自动转换为地平坐标 (ALT/AZ)，驱动电机指向目标
- 🔭 **自动追踪**：基于图像质心检测，实时校正望远镜指向偏差，支持 ALT-AZ 与赤道仪两种安装方式
- 📷 **摄像头控制**：亮度 / 对比度 / 快门 / ISO 调节，拍照、录像、延时摄影
- 📡 **视频流传输**：通过 WebSocket 实时推送 MJPEG 视频流到浏览器
- 🌐 **Web 远程控制**：浏览器访问，支持中英文界面，移动端友好
- ⚙️ **YAML 配置**：所有硬件参数集中管理，无需修改源码

---

## 硬件需求 / Hardware Requirements

| 组件 | 规格 |
|------|------|
| 主控板 | Raspberry Pi（3B+ / 4 / Zero 2W 均可） |
| 摄像头 | Raspberry Pi Camera Module（PiCamera2） |
| 步进电机驱动 | EasyDriver 或兼容模块 × 3（垂直 / 水平 / 调焦） |
| 步进电机 | 标准 200 步/圈电机 × 3 |
| 限位开关 | 4 路（垂直上下、水平左右） |
| 磁力计（可选） | LSM303 （方位角辅助标定） |
| 串口模块（可选） | `/dev/ttyAMA0` 兼容模块 |
| 网络 | Wi-Fi 或有线以太网 |

**GPIO 引脚分配（BCM 编号）/ GPIO Pin Assignment (BCM):**

| 电机 | 引脚 (Step/Dir/En/—) |
|------|----------------------|
| 垂直 Vertical | 12, 16, 20, 21 |
| 水平 Horizontal | 6, 13, 19, 26 |
| 调焦 Focus | 4, 17, 27, 22 |

| 限位开关 | 引脚 |
|----------|------|
| 垂直下限 | 24 |
| 垂直上限 | 23 |
| 水平左限 | 25 |
| 水平右限 | 8 |

---

## 系统架构 / System Architecture

```
浏览器 / Browser
    │  HTTP (port 8080)
    ▼
Web/server/app.py          # Python HTTP 服务器
    ├── routes.py           # API 路由分发
    └── handlers.py         # 请求处理逻辑
            │
            ├── StarLocator/StarLocator_v2.py   # RA/DEC → ALT/AZ 坐标转换
            ├── StarLocator/StarTracking_v2.py  # 自动追踪控制器
            ├── EasyDriver/stepper.py           # 步进电机驱动
            └── cv2/detect_bright_spots.py      # 图像质心检测
            
nodejs/websocket-relay.js  # WebSocket 视频中继 (port 8081)
    │  WebSocket
    ▼
浏览器 jsmpg.js             # MJPEG 解码与渲染
```

---

## 依赖安装 / Install Dependencies

### Python 依赖

```bash
# 创建虚拟环境（推荐）/ Create virtual environment (recommended)
python3 -m venv ~/env
source ~/env/bin/activate

# 安装依赖 / Install dependencies
cd ~/projects
pip install -r requirements.txt

# Raspberry Pi 专用依赖 / Pi-specific
pip install RPi.GPIO picamera2
```

`requirements.txt` 包含 / includes:
- `PyYAML>=6.0` — 配置文件解析
- `python-dateutil>=2.8` — 时间/时区处理

### Node.js 依赖（视频流）

```bash
# 确认 Node.js 已安装 / Verify Node.js
node --version

# 无需额外 npm 包，websocket-relay.js 为纯 Node.js 实现
# No extra npm packages needed; websocket-relay.js uses Node built-ins
```

---

## 配置 / Configuration

所有硬件参数集中在 `config/telescope_config.yaml`，修改此文件即可适配不同硬件，无需改动源码。

All hardware parameters are centralized in `config/telescope_config.yaml` — edit this file to adapt to different hardware without touching source code.

### 关键配置项 / Key Settings

```yaml
location:
  latitude: 42.27          # 观测地纬度 / Observer latitude
  longitude: -83.04        # 观测地经度 / Observer longitude
  timezone: "America/Detroit"

motors:
  vertical:
    pins: [12, 16, 20, 21] # GPIO 引脚 / GPIO pins (BCM)
    speed: 120              # 转速 RPM / Speed RPM
  horizontal:
    pins: [6, 13, 19, 26]
  focus:
    pins: [4, 17, 27, 22]

camera:
  resolution:
    width: 700
    height: 524
  defaults:
    shutter_speed: 4000     # 微秒 / microseconds
    iso: 400

tracking:
  threshold_limit: 5        # 触发校正的最小偏移像素 / Min offset to trigger correction
  blur_limit: 13            # 图像模糊阈值 / Image blur threshold
  thresh_limit: 45          # 质心检测阈值 / Centroid detection threshold
```

---

## 运行 / Run

### 完整模式（电机 + 摄像头 + Web）

```bash
cd ~/projects/Web
./start.sh
```

### 仅摄像头模式（不需要电机）

```bash
cd ~/projects/Web
./start.sh -c
```

### 停止所有服务

```bash
cd ~/projects/Web
./stopall.sh
```

启动后在局域网浏览器访问（IP 会在终端打印）：

```
http://<Pi-IP>:8080
```

---

## Web 控制界面 / Web Control Interface

| 页面 | URL | 说明 |
|------|-----|------|
| 主控制台（英文） | `http://<Pi-IP>:8080/` | 星体定位、电机控制、摄像头 |
| 主控制台（中文） | `http://<Pi-IP>:8080/index_zh.html` | 同上，中文界面 |
| 实时追踪 | `http://<Pi-IP>:8080/tracking.html` | 追踪状态监控 |
| 视频流测试 | `http://<Pi-IP>:8080/stream-example.html` | 原始视频流 |
| 资源页 | `http://<Pi-IP>:8080/resources.html` | 参考资料链接 |

### 主要操作 / Main Controls

**星体定位 / Star Locate:**
1. 在 RA（赤经）栏输入 时:分:秒，在 DEC（赤纬）栏输入 度:分:秒
2. 点击 **Locate** — 系统计算 ALT/AZ 并驱动电机指向目标
3. 点击 **Track** — 启动自动追踪

**电机控制 / Motor Control:**
- 上下左右按钮手动微调指向
- 调焦 +/- 调整焦距
- 步数 (Steps) 和速度 (Speed) 可在侧栏调节

**摄像头 / Camera:**
- 实时预览视频流
- 拍照 (Snap) / 录像 (Video) / 延时摄影 (Timelapse)
- 亮度 / 对比度 / 饱和度 / 快门 / ISO 实时调节

---

## 模块说明 / Module Guide

### StarLocator (`StarLocator/StarLocator_v2.py`)

将天体赤道坐标转换为地平坐标。  
Converts equatorial coordinates (RA/DEC) to horizontal coordinates (ALT/AZ).

**核心算法 / Core Algorithm:**
1. 根据观测时间和地点计算本地恒星时 (LST)
2. 由 LST 和 RA 计算时角 (Hour Angle)
3. 通过球面三角公式转换为 ALT/AZ

```python
# 示例 / Example
from StarLocator.StarLocator_v2 import StarLocator, CelestialCoords
locator = StarLocator()
coords = CelestialCoords(ra_hours=5, ra_minutes=34, ra_seconds=32,    # 猎户座 / Orion
                          dec_degrees=22, dec_minutes=0, dec_seconds=52)
alt, az = locator.locate(coords)
```

### StarTracking (`StarLocator/StarTracking_v2.py`)

自动追踪控制器，两种安装模式：  
Auto-tracking controller supporting two mount types:

| 模式 | 说明 |
|------|------|
| **ALT-AZ** | 地平式安装，分别校正高度角和方位角 |
| **EQ** | 赤道仪安装，通过 RA 轴跟踪周日运动 |

**工作流程 / Workflow:**
1. 拍摄当前帧，检测最亮点质心位置
2. 计算质心与画面中心的偏差（像素）
3. 将偏差转换为电机步数，驱动步进电机校正
4. 循环执行（间隔 `tracking_interval` 秒）

### EasyDriver (`EasyDriver/stepper.py` + `easydriver.py`)

步进电机驱动封装，支持：  
Stepper motor driver wrapper supporting:

- 单步 / 双相 / 微步驱动模式
- 正反转方向控制
- 速度与步数配置
- 限位开关保护

### 图像处理 (`cv2/detect_bright_spots.py`)

基于 OpenCV 的亮斑检测，用于追踪时确定星点质心位置。  
OpenCV-based bright spot detection for determining star centroid during tracking.

### Web 服务器 (`Web/server/`)

| 文件 | 职责 |
|------|------|
| `app.py` | HTTP 服务器主入口，多线程处理请求 |
| `routes.py` | API 路由注册与匹配（REST-like） |
| `handlers.py` | 业务逻辑：电机控制、摄像头、追踪启停 |

**主要 API 端点 / Key API Endpoints:**

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/locate` | POST | 星体定位，RA/DEC → 电机驱动 |
| `/api/track/start` | POST | 启动自动追踪 |
| `/api/track/stop` | POST | 停止追踪 |
| `/api/motor/move` | POST | 手动移动电机 |
| `/api/camera/snap` | GET | 拍照 |
| `/api/camera/settings` | POST | 调整摄像头参数 |
| `/api/status` | GET | 获取系统状态 |

### 视频流 (`nodejs/websocket-relay.js`)

Node.js WebSocket 中继服务器，将 PiCamera2 的 MJPEG 流通过 WebSocket 推送到浏览器，由 `jsmpg.js` 解码渲染。  
Node.js WebSocket relay: forwards PiCamera2 MJPEG stream over WebSocket to the browser, decoded by `jsmpg.js`.

---

## 目录结构 / Project Layout

```
projects/
├── requirements.txt              # Python 依赖 / Python dependencies
├── config/
│   ├── telescope_config.yaml     # 主配置文件 / Main config file
│   ├── __init__.py               # 配置加载器 / Config loader
│   └── errors.py                 # 错误类型定义 / Error types
│
├── StarLocator/
│   ├── StarLocator_v2.py         # RA/DEC → ALT/AZ 坐标转换
│   └── StarTracking_v2.py        # 自动追踪控制器
│
├── EasyDriver/
│   ├── easydriver.py             # EasyDriver GPIO 封装
│   └── stepper.py                # 步进电机抽象层
│
├── cv2/
│   └── detect_bright_spots.py    # 图像质心检测
│
├── nodejs/
│   ├── websocket-relay.js        # WebSocket 视频中继服务器
│   └── jsmpg.js                  # 浏览器端 MJPEG 解码器
│
└── Web/
    ├── start.sh                  # 启动脚本 / Start script
    ├── stopall.sh                # 停止脚本 / Stop script
    ├── getip.py                  # 获取本机 IP / Get local IP
    ├── content/                  # 前端静态文件 / Frontend static files
    │   ├── index.html            # 主界面（英文）
    │   ├── index_zh.html         # 主界面（中文）
    │   ├── tracking.html         # 追踪状态页
    │   ├── control.js            # 前端控制逻辑
    │   └── draw.js               # 图形绘制
    └── server/
        ├── app.py                # HTTP 服务器主入口
        ├── routes.py             # API 路由
        └── handlers.py           # 请求处理逻辑
```

---

## 地理位置 / Observer Location

本系统默认配置为加拿大安大略省温莎市（Windsor, ON）：  
Default location configured for Windsor, Ontario, Canada:

- 纬度 / Latitude: **42.27° N**
- 经度 / Longitude: **83.04° W**
- 时区 / Timezone: `America/Detroit` (EST/EDT)

修改 `config/telescope_config.yaml` 中的 `location` 字段适配您的观测地点。  
Edit the `location` section in `config/telescope_config.yaml` to adapt to your observing site.

---

## 许可 / License

个人学习与研究用途。  
For personal learning and research use.
