# LAN Radar (ipScanner) 🛰️

[![Windows Executable](https://img.shields.io/badge/Windows-Standalone_.exe-0078D4?logo=windows&logoColor=white)](file:///g:/我的雲端硬碟/Google%20Antigravity/Coding/ipScanner/ipScanner.exe)
[![Frontend](https://img.shields.io/badge/Frontend-Vanilla_HTML5_Canvas-F16529?logo=html5&logoColor=white)](file:///g:/我的雲端硬碟/Google%20Antigravity/Coding/ipScanner/index.html)
[![Backend](https://img.shields.io/badge/Backend-Python_3-3776AB?logo=python&logoColor=white)](file:///g:/我的雲端硬碟/Google%20Antigravity/Coding/ipScanner/server.py)
[![Offline Ready](https://img.shields.io/badge/Dependencies-Zero_External_CDNs-10B981)](#)
[![Localization](https://img.shields.io/badge/Language-繁體中文_%7C_English-8B5CF6)](#)

A high-speed local network IP scanner and interactive real-time network topology visualizer. Built as a zero-dependency, portable single executable for Windows with a multi-threaded discovery backend and a responsive HTML5 Canvas radar interface.

---

## 📸 Overview

LAN Radar provides instant visibility into your local area network (LAN):
- **Fast Multi-Threaded Engine**: Rapid 60-worker parallel ICMP Echo sweep and kernel ARP table cache harvesting.
- **Radial Latency Radar**: Live Canvas topology with concentric latency rings (`< 5ms`, `5–20ms`, `> 20ms`), orbital gravitation, and a rotating sweep beam.
- **Subnet Matrix (254 Hosts)**: Interactive 254-node status grid showing real-time scanning progress and host responsiveness.
- **Portable & Self-Contained**: Packaged into a standalone single `.exe` file (~9.6 MB) that runs without requiring Python, Node.js, or external runtime installation.

---

## ✨ Features

| Category | Feature | Description |
| :--- | :--- | :--- |
| **Discovery** | Multi-Threaded Ping Sweep | 60 parallel threads scan `/24` subnets (1–254) in seconds. |
| | Kernel ARP Harvesting | Discovers network devices even if firewalls block TCP/HTTP ports; retrieves MAC addresses. |
| | Browser-Native Timing Fallback | Differential timing detection via `Promise.race()` and `fetch()` if running purely in-browser. |
| **Topology View** | Concentric Radar Rings | Visual concentric tiers based on node round-trip time (`< 5ms`, `5–20ms`, `> 20ms`). |
| | Orbital Gravitation | Faster nodes cluster closely around Gateway (`.1`); higher-latency endpoints orbit outer rim. |
| | Rotating Radar Sweep | Continuous 360-degree radar beam animation with link packet pulse indicators. |
| **Probing & Controls** | Port Presets | Quick selection for HTTP (`80`), HTTPS (`443`), SSH (`22`), SMB (`445`), RDP (`3389`), RTSP (`554`), Alt Web (`8080`), or Custom. |
| | Target Host Range | Target specific host slices (e.g., `.10` to `.50`) with automatic subnet matrix dimming. |
| | Continuous Auto Scan | Automated background sweeps at 15s, 30s, 1m, 2m, or 5m intervals with live countdown. |
| **Customization** | Visual Themes | 4 color palettes: **Cyberpunk Neon**, **Matrix Terminal**, **Deep Space Navy**, and **Clean Obsidian**. |
| | Bilingual i18n | Instant one-click toggle between **Traditional Chinese (繁體中文)** and **English**. |
| | View Modes | Dedicated tabs for **Network Topology Diagram**, **Host Table**, and **Split View**. |

---

## 🚀 Quick Start

### Option 1: Standalone Single Executable (Recommended)
1. Download or copy [`ipScanner.exe`](file:///g:/我的雲端硬碟/Google%20Antigravity/Coding/ipScanner/ipScanner.exe) to any Windows machine.
2. Double-click `ipScanner.exe`.
3. The application will:
   - Free any stale process holding port `63210`.
   - Start the local HTTP discovery service.
   - Automatically launch your default web browser at `http://localhost:63210/`.
4. Press `Ctrl+C` or close the console window to stop the server.

### Option 2: Run via Python Source
Requirements: Python 3.7+ (Standard Library only, no `pip install` required).
```bash
python server.py
```
Open your browser to `http://localhost:63210/`.

### Option 3: Run via Windows Batch Launcher
```cmd
Autorun.bat
```

---

## 📁 Project Architecture

```
ipScanner/
├── ipScanner.exe       # Portable single executable (PyInstaller onefile bundle)
├── index.html          # Frontend UI (Single-file HTML5 Canvas, CSS & JS, 0 dependencies)
├── server.py           # Backend discovery server & REST API (Python standard library)
├── build.bat           # One-click PyInstaller build script to compile ipScanner.exe
├── Autorun.bat         # Windows launcher script with port conflict resolution
├── icon.ico            # Multi-resolution application icon (16x16 to 256x256)
├── ipScanner.spec      # PyInstaller build specification
└── README.md           # Project documentation
```

---

## 🔌 Backend REST APIs

The internal server operates on `http://localhost:63210` and exposes the following endpoints:

### 1. `GET /api/my-ip`
Returns the active local network interface and `/24` subnet base.
```json
{
  "ip": "192.168.1.105",
  "subnet": "192.168.1",
  "host": 105,
  "hostname": "MY-PC"
}
```

### 2. `GET /api/arp-devices?subnet=192.168.1`
Returns active hosts recorded in the OS kernel dynamic ARP cache.
```json
{
  "devices": {
    "192.168.1.1": "A4-91-B1-23-45-67",
    "192.168.1.120": "E8-9F-80-AB-CD-EF"
  }
}
```

### 3. `GET /api/scan-subnet?subnet=192.168.1`
Executes a rapid 60-worker multi-threaded ICMP sweep across all 254 hosts and returns responsive devices.
```json
{
  "subnet": "192.168.1",
  "count": 4,
  "devices": [
    { "ip": "192.168.1.1", "host": 1, "mac": "A4-91-B1-23-45-67", "rtt": 1, "reason": "ICMP Echo Reply" },
    { "ip": "192.168.1.105", "host": 105, "mac": "", "rtt": 1, "reason": "Local Interface" }
  ]
}
```

---

## 🛠️ Rebuilding the Executable

To rebuild [`ipScanner.exe`](file:///g:/我的雲端硬碟/Google%20Antigravity/Coding/ipScanner/ipScanner.exe) after editing [`index.html`](file:///g:/我的雲端硬碟/Google%20Antigravity/Coding/ipScanner/index.html) or [`server.py`](file:///g:/我的雲端硬碟/Google%20Antigravity/Coding/ipScanner/server.py):

Run the automated build script:
```cmd
build.bat
```

Or manually invoke PyInstaller:
```bash
pip install pyinstaller
python -m PyInstaller --clean --noconfirm --onefile --name "ipScanner" --icon "icon.ico" --add-data "index.html;." server.py
copy dist\ipScanner.exe .\ipScanner.exe
```

---

## 📜 License

MIT License. Designed for network administration, diagnostic inspection, and educational security research.
