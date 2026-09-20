# 接线与固件

本应用基于已验证的 Tang Mega138K Dock / AD9767 转接接线。**不要将模块40针接口未经核对直接对插。** 原转接跳过 Dock J13 的11/12电源排；模块J6-1外部5V与开发板隔离，模块J6-5接地脚与FPGA E14隔离，并单独共地。J13-33接地导致DAC B3固定0，绘图器已让低4位保持0。详细数字映射以 `firmware/board.cst` 和实际转接板为准。

```text
电脑 DEBUG USB → FPGA UART（Y14接收、U15发送，1 Mbaud）
FPGA 并行接口 → AD9767 CH1 → 示波器 CH1（X）
                       CH2 → 示波器 CH2（Y）
FPGA E14 → SDG1032X 后面板 AUX 输入
SDG1032X CH1 → 示波器 CH3（Z消隐）
各设备保持公共地；模块使用正确的外部5V供电。
```

示波器输入必须为1MΩ/DC，直连电缆按1X处理；不要将FPGA GPIO接50Ω负载。此应用的参数针对上述直连接法。

## 自动配置的参数

- 发生器先关闭CH1；高阻负载，±1V脉冲，周期100µs、延迟12µs、宽度76µs，外部上升沿单周期Burst。AUX必须作为输入。
- 示波器CH1/2为0.4V/div、20MHz带宽限制；CH3为0.5V/div、零偏置；三路DC/1MΩ；1ms/div、100k存储深度、最短余辉。
- 先启用XY，再设置X=CH1、Y=CH2、Z=CH3，避免部分固件重置Z来源。
- 通过1Mbaud CRC帧握手确认通用绘图器后，才开启发生器CH1输出。
- 关闭应用/断开连接时关闭由应用控制的发生器输出。停止游戏只停止帧流，FPGA的1秒超时会消隐。

## 固件准备（一次性）

用户原板已经完成Flash固化和冷启动验证，User Code为 `0x0000C48F`；对应历史构建SHA256为 `63be387ed00670d84a309af6685acd5620d5ffb43578e3ed69baf027151f0f79`。重新构建可能生成不同User Code/文件哈希；应用实际握手验证协议，不依赖固定COM编号。

其他板需自行安装Gowin工具并核对器件、板卡版本、GPIO及UART路由。在 `firmware` 目录用绝对工具路径运行 `build.tcl`：

```powershell
Set-Location firmware
& 'D:\tools\gowin\V1.9.12.03\IDE\bin\gw_sh.exe' build.tcl
```

仅需要运行游戏的电脑不必安装Gowin。应用不含位流和厂商工具，也不自动烧录。

原板持久化验证使用独立 Programmer1.9.12SP1 build2565、**USB Debugger A原生接口（cable-index4）**，GAO-Bridge Arora V擦除/写入/校验 operation69，随后独立校验67。FT2CH兼容路径曾在退出码0时报告校验失败，不能只看Finished。烧录会覆盖原配置，应按板卡实际情况单独执行。

Dock31002从Flash启动使用MSPI MODE[2:0]=001：SW2第1位ON、第2/3位OFF；其余位保持原用途。不要将其他板卡或版本的拨码直接套用。

## 换电脑

安装FTDI串口驱动和64位VISA运行库；接DEBUG USB后查看新增UART端口。两路FTDI端口中应选连接FPGA UART的接口，原电脑曾为COM11但新电脑不保证相同。扫描仪器会按实际IDN识别当前USB/VISA地址，不绑定原设备序列号。无法连接时先使用电脑预览检查应用，再处理驱动/连接，不需要反复烧写Flash。
