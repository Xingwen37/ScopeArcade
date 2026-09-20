# ScopeArcade · 示波器游戏中心

把 XY 示波器变成可切换游戏的街机。Windows 桌面应用统一管理串口、示波器、信号发生器和游戏包。

## 下载和运行

将 `ScopeArcade-v0.2.0-Windows-x64.zip` **解压整个文件夹**后运行 `ScopeArcade.exe`。不需要安装 Python。当前 v0.2.0 为本地打包版本，尚未上传 GitHub；线上 v0.1.0 不包含动画。

1. 没接硬件：选择游戏，点击 **仅电脑预览**。
2. 接硬件：连接 DEBUG USB、示波器和发生器，点击 **扫描设备**。
3. 选择 FPGA 的 UART 串口、DHO4404、SDG1032X，点击 **配置仪器并连接**。应用会先关闭输出，验证设备、配置参数和固件响应，最后开启消隐输出。
4. 在游戏列表中切换游戏，或点击 **启动 / 重开**。切换游戏不改写 FPGA。
5. 点击 **断开并关闭输出** 或关闭应用，释放串口并关闭应用控制的发生器输出。

Windows 10/11 x64 为交付目标；实际验证环境见 [测试记录](docs/validation.md)。USB 连接仍需系统安装 **FTDI 串口驱动**和 **NI-VISA 或兼容的 64 位 VISA 运行库**。这些厂商驱动不随应用分发。只有电脑预览时不需要驱动。

## 内置游戏

| 游戏 | 操作 |
|---|---|
| 赛车 | 空格开始，←/→ 或 A/D转向，P暂停，R重开；60秒挑战、音效和本机排行榜 |
| Pong | W/S 或 ↑/↓移动，空格发球/暂停，A自动演示，R重开 |
| 小恐龙 | 空格或 ↑跳跃，A自动演示，R重开 |
| Bad Apple · 轮廓动画 | 空格播放/暂停，←/→前后5秒，Home/R重播，L切换循环 |

点击预览区域后使用键盘。应用中的“静音”开关控制音效。Esc 停止当前游戏。

选择 **Bad Apple · 轮廓动画** 并点击 **启动 / 重开** 即可播放。约3分39秒、30帧/秒，默认循环；动画数据已随应用携带，换电脑不需要原MP4、原文件路径或视频解码库。可先用“仅电脑预览”查看。每帧最多72条轮廓线，细节会简化，白色区域不填充；纯黑帧可能在画面边角留下一个停车点。此版本无音乐音轨。素材来源说明见 `games/bad_apple/ASSET_NOTICE.md`（EXE包内位于 `_internal/games/bad_apple/`）。

## 硬件和固件

当前驱动精确匹配 **RIGOL DHO4404 + SIGLENT SDG1032X**。其他型号不会自动套用配置。

- FPGA：Tang Mega 138K Dock，GW5AST-LV138PG484AC1/I0，revision B。
- DAC：双通道 AD9767 模块，经已核对的转接板连接。
- FPGA 内需运行 `firmware/renderer.sv` 的通用绘图器。已固化的用户板无需每次下载。
- **旧版 Pong/小恐龙专用位流与本应用不兼容**；内置游戏和动画均使用通用线段协议。
- 接线、固件准备和重启说明：[硬件指南](docs/hardware.md)。本应用不执行 FPGA 或 Flash 烧录。

## 添加自己的游戏

复制 `game-template` 文件夹，修改 `game.json` 的唯一 id/name 和 `game.py`，在应用中点击 **添加游戏…**，选择它的 `game.json`。

游戏包会复制到当前用户的数据目录，不修改安装目录。每幅画面最多72条线段，坐标0～255。示例无需额外第三方库。

**游戏包是可执行 Python 代码，仅导入可信来源。** API 与扩展示例见 [游戏开发指南](docs/game-api.md)。插件不能改变仪器配置或占用串口；这些由宿主应用统一管理。

## 数据位置

默认 `%LOCALAPPDATA%\ScopeArcade`：设备地址、昵称、排行榜、自定义游戏、状态和错误日志。复制应用到另一台电脑后，应重新扫描端口；不要照抄 COM11 或设备序列号。可用 `--data-dir 路径` 指定独立的数据目录。

## 从源码运行

建议 Python 3.11～3.13，包含 Tk。源码测试环境 Python3.13.5 / 3.13.7，发布包使用标准 CPython3.13.7。

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

打包脚本见 `build_windows.py`；它使用当前 Python 环境中的 PyInstaller，产物写到忽略的 `dist/`、`release/`。不包含厂商工具、许可证、位流或本机运行状态。

动画播放器仅使用Python标准库。可选的开发工具 `tools/convert_video.py` 将本地视频预转换成轮廓数据；安装 `requirements-video.txt` 后运行 `python tools/convert_video.py "你的视频.mp4" games/bad_apple/animation.xyframes --fps 30`。这些转换依赖和原视频不会进入EXE包；普通用户无需运行转换工具。

## 来源与许可

从 [Gowin-FPGA-AI-Workflow](https://github.com/Xingwen37/Gowin-FPGA-AI-Workflow) 中已实机验证的游戏提取并整合。2026-09-20 新增统一应用、仪器驱动、串口管理、插件 API、通用绘图器游戏适配和便携打包。

沿用 [GWFlow Personal Non-Commercial License 1.0](LICENSE)，不是商业使用授权。第三方组件保留各自许可，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
