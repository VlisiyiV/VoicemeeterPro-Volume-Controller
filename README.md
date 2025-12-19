# VoicemeeterPro 音量控制器 / VoicemeeterPro Volume Controller

> 通过 Python 直接修改 Voicemeeter Pro 内存中的增益值，实现 **A1/A2 独立音量控制**，并 **与 Windows 系统主音量实时同步**。
> 
- **⚠️ 重要提示**：程序 **仅支持 Windows 10 或更高版本**  

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Platform](https://img.shields.io/badge/Windows-10%2B-red?logo=windows)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## 🌟 功能特性

- ✅ **A1 / A2 输出通道独立增益控制**（0% ~ 100%，对应 -60dB ~ +12dB）  
- ✅ **系统主音量作为总增益**，自动与 Voicemeeter 增益叠加（dB 相加）  
- ✅ 后台自动注入 `voicemeeterpro.exe` 进程，断开后自动重连  
- ✅ 托盘图标支持：**左键打开 GUI**，右键退出  
- ✅ 自动保存/加载上次设置的音量值（使用 `platformdirs` 存储于用户数据目录）  
- ✅ 轻量级 GUI（基于 **[马良 maliang](https://github.com/Xiaokang2022/maliang/)**）  
- ✅ 系统音量监听（基于 `pycaw` + `comtypes`）

---

## 🛠️ 技术原理

- 使用 `pymem` 直接读写 Voicemeeter Pro 进程内存（偏移地址 `0x9CA68` / `0x9CAC8`）  
- 系统音量通过 Windows Core Audio API (`pycaw`) 实时获取  
- 增益值以 **dB → 线性浮点数** 转换后写入内存（符合 Voicemeeter 内部格式）  
- 主增益与通道增益按 **dB 相加**：`最终A1 = 主增益(dB) + A1增益(dB)`  
- 进程断开自动重连，确保长时间运行稳定性

---

## 📦 依赖安装

### 推荐方式（一键安装所有必需 + 可选依赖）
```bash
pip install maliang[opt] pymem pycaw psutil pystray platformdirs
```

> 💡 `maliang[opt]` 会自动安装：
> - `darkdetect`（深色/浅色主题自动适配）  
> - `Pillow`（图标加载与图像优化）  
> - `pywinstyles` / `hPyT` / `win32material`（Windows 窗口增强，可选但推荐）

### 仅基础依赖（无深色模式）
```bash
pip install pymem pycaw psutil Pillow pystray platformdirs maliang
```

> ⚠️ **Python 版本要求**：**≥ 3.10**（因 `maliang` 要求）

---

## ▶️ 运行程序

### 1. 从源码运行
- 推荐创建快捷方式运行
```bash
pythonw "VoicemeeterPro音量控制器.py"
```


### 2. 运行 EXE 程序
- 推荐使用pthon直接运行, 使用打包过的EXE程序可能出现问题
- Releases使用 PyInstaller 等工具打包为独立 `.exe` 文件  
- 可能触发 Windows 安全警告（内存写入操作）

### 3. 开机自启动
- 可以将创建的快捷方式放入 `C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup` 文件夹实现开机自启

### 前提条件
- ✅ **Voicemeeter Pro 已安装并正在运行**（进程名：`voicemeeterpro.exe`）  
- ✅ **Windows 10 / 11 系统**（低版本不兼容 Core Audio API 和部分 GUI 特性）  
- ✅ 无需管理员权限（但需允许 Python 访问其他进程内存）

---

## 🎨 GUI 框架说明

本项目的图形界面基于 **[马良（maliang）](https://github.com/Xiaokang2022/maliang/)** 构建 —— 一个轻量级、**基于 `tkinter.Canvas` 全手绘** 的 Python UI 框架

> 🌟 特性：纯 Canvas 渲染、响应式布局、主题自动适配（配合 `darkdetect`）、无原生控件依赖

🔗 项目地址：[https://github.com/Xiaokang2022/maliang/](https://github.com/Xiaokang2022/maliang/)

---

## 📁 配置文件

音量设置保存在用户数据目录：  
- **Windows**: `%LOCALAPPDATA%\VoicemeeterGainControl\vol.txt`  
- 文件格式：三行整数（主增益、A1、A2，单位 %）

---

