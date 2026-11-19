# PBAM00 原厂 Recovery 的 EDL 路径与故障对照

分析日期：2026-11-18，Asia/Singapore。原厂样本为本地已保存的 A.35
Recovery；本轮没有从手机回读镜像，也没有重新刷写 Recovery。

## 结论

原厂 Recovery 的已定位入口最终设置 `sys.powerctl=reboot,edl`，与当前
OrangeFox 的 EDL 目标一致。它先执行 Recovery 收尾，再由原厂 init 执行
关机收尾并调用带 `edl` 参数的 restart2。所分析入口没有另一个专用的
“OPPO 9008 命令”，也没有在 Recovery 菜单内上传 Firehose。

已找到用户这四次失败的具体原因：高通工具箱配置强制使用 **COM3**，
而本轮 PBAM00 的实际 9008 端口是 **COM5**。工具日志在串口打开阶段就
报错，尚未收到 Sahara HELLO，随后界面统一提示“发送引导失败”。
这是对保存的四次错误记录的定位；不能据此断言任何历史 EDL 异常都相同。

用同一个 QSaharaServer、同一份内置 OPPO 450 引导，选择实际 COM5：
正常 Android、Fox 直接请求属性、Fox 菜单同一后台路径，三组均完成了
Sahara 上传和 Firehose NOP ACK。没有进行实际刷机验证。

## 1. 原厂实际调用链

地址均为 ELF 虚拟地址，不是设备物理内存地址。

```text
root_detection_show(menuUnit*)                 0x0001fc64
  检查 usb / pc_port 连接；累计点击后显示确认框
  oppoIntent_send(3, 1, "reboot,edl")           0x0001fd40
    intent_reboot(int, char**)                 0x0001e59c
      finish_recovery(NULL)                   0x0001e5b8
      原厂恢复日志、BCB、临时修复目录等收尾
      property_set("sys.powerctl", argument)  0x0001e60c
        init: HandlePowerctlMessage           0x00422a90
          DoReboot                            0x00421378
            停服务 / 等待 / 同步 / 处理卸载
            syscall(reboot, ..., RESTART2, "edl")
                                               0x004224f4
```

关键证据见 `stock-recovery-reboot.disasm.txt` 和
`stock-init-reboot.disasm.txt`，通过 `.gnu_debugdata` 恢复函数符号后反汇编。
脚本 `disassemble-stock.py` 同时注释已解析的字符串和调用目标。
字符串追踪是局部辅助注释；结论核对了对应指令与调用参数，未将所有
邻近字符串引用自动视为真实的执行路径。

`finish_recovery()` 会保存日志，并调用 `write_bootloader_message()`
清理 BCB；它不是专门的 EDL 握手。随后两个 `__system()` 调用操作的是
`.recovery_repair` 临时目录，**不是卸载分区的命令**。
本轮没有把这些删除或 BCB 操作照搬进设备树。

## 2. 原厂与 Fox 的重启收尾差异

原厂 init 在 `0x42158c` 读取 `ro.build.shutdown_timeout`，
`0x4215a0` 提供默认值 6 秒。它保留了服务 Terminate 与轮询等待路径。
这是可提前结束的超时预算，**不是固定 sleep 六秒**，也不是 EDL 专用延时。

Fox 的实际编译命令先定义 `SHUTDOWN_ZERO_TIMEOUT=0`，随后 eng 变体通过
`-USHUTDOWN_ZERO_TIMEOUT -DSHUTDOWN_ZERO_TIMEOUT=1` 覆盖。
已核对实际打包 init：`DoReboot` 中没有原厂的优雅 Terminate 等待路径，
仍保留 Stop、sync、卸载处理及末尾短暂延时。仅在 prop 中增加
`ro.build.shutdown_timeout=6` 不能恢复被编译掉的分支。

**该差异不能认定为本次故障根因**：当前未改动的 Fox，在三组对照中的
两组 Recovery 路径已经成功加载同一引导。没有为了制造“已修好”的结果
而加入任意延时，也没有修改 init 或 Recovery 的运行代码。

相关证据：`fox-init-build-flags.txt`、`fox-timeout-source.txt`、
`fox-init-reboot.annotated.txt`、`stock-edl-verification.json`。

## 3. 内核层的 EDL

从本地保存的原厂镜像和已刷 Fox test-4 镜像提取 kernel payload 比较：

- 两者 kernel 大小均为 11619350 字节。
- SHA256 均为
  `73b91a174b9498badc3b0398c8bafd80ff7a13cd69176d8f2144d2dc7d5153fe`。
- kernel payload 完全相同，cmdline 有 eng、permissive、固件路径等区别。

因此不能把问题描述成 Fox 丢失了原厂内核中的 EDL 驱动。
原厂与 Fox 的用户空间及运行状态仍有区别，不能仅凭内核相同保证一切等价。

作为同平台源码参照，本地 AX5 8.1 源码的 `msm-poweroff.c` 在收到 `edl`
时选择 warm reset，设置 emergency download cookies、处理 PMIC watchdog，
并请求 secure EDLOAD。该源码不是 A.35 的精确构建源码，不能把其中每个
实现细节都当作已在 A.35 二进制中验证。参照文件为 `ax5-msm-poweroff.c`。

## 4. 本轮不刷分区的握手对照

共同工具：本机高通工具箱中的 `QSaharaServer.exe`。
共同 programmer：内置 `tool/qctool/oppo/firehose_450` 与项目
`tools/firehose_450.mbn` 的内容逐字节一致，SHA256：
`571351495ede00053cbb3669b31f65037e3440479190a621008999675c847ff9`。

programmer 文件本身为 1048576 字节；Sahara 按目标请求传输的有效数据
为 436452 字节。两者不同不是本轮传输截断。

| 入口 | 时间（UTC+8） | Sahara HELLO mode | 上传 | Firehose NOP |
|---|---|---:|---|---|
| Android `adb reboot edl` | 22:50 | 0 | 成功，436452 字节 | ACK |
| Fox `sys.powerctl=reboot,edl` | 22:52 | 0 | 成功，436452 字节 | ACK |
| Fox 菜单同一后台重启路径 | 22:55 | 0 | 成功，436452 字节 | ACK |

第三组通过 ORS 设置内存中的 `tw_reboot_arg=edl` 和 `tw_gui_done=1`，
使当前 GUI 退出后运行 `twrp.cpp` 中与菜单相同的收尾及
`TWFunc::tw_reboot(rb_edl)`；**不是用户物理点击屏幕的另一轮测试**。

各组在枚举后等待约 0.7 秒再连接。这些测试未覆盖各种工具的抢先连接、
端口占用、冷启动按键进入或其它引导文件，不把通过结果扩大到这些情形。

测试只主动向 RAM 上传 programmer，并发送 Firehose NOP / reset；
没有发送 read、program、erase、patch 或格式化命令，没有备份 userdata，
没有用设备块文件哈希替代回读。Recovery 自身正常退出涉及的日志收尾
不等同于测试脚本执行分区刷写。

reset 后 USB 可能立即消失，Windows 串口读取会报连接中断。
首组原始 result 保留了这条 reset 后的异常；Sahara 与 NOP 在此前已完成。
最后已独立通过 ADB 确认 `b658f72c` 回到正常 Android，
`ro.bootmode=normal`、`sys.boot_completed=1`。

原始记录：`edl-tests/`；汇总：`edl-tests-summary.json`。
`probe-edl-handshake.py` 是主动测试工具，会重启指定 PBAM00；
`compare-edl-tests.py` 只分析本地日志，不连接手机。

## 5. 高通工具箱错误证据与处理

本机配置 `E:/6/高通工具箱/bin/conf/user.bat`：

```bat
set qctool_port=specific
set qctool_port_specific_portnum=3
```

`chkdev.bat` 第 54～57 行在 specific 模式直接返回指定的端口号，
不会先确认该端口存在；`write.bat` 第 39 行使用这个号码调用 Sahara。

22:25、22:28（两次）、22:30 的四份日志均显示：

```text
设备已连接:qcedl.指定端口号:3
Failed to open com port handle
Could not connect to \\.\COM3
发送引导失败
```

这四次尚未建立串口，更没有进入 Sahara 协议中的程序认证或传输阶段。
完整日志与当时配置已复制到 `toolbox-port-evidence/`，同时保留原编码
版本、UTF-8 文本及哈希。未复制无关的历史分区数据。

处理方法：把高通工具箱的端口设置改成自动识别，或选当前实际 COM5，
然后退出并重新打开工具箱以清除已加载的旧环境。脚本中以
`qctool_port=specific` 判定固定模式；改成 `qctool_port=auto` 会使用
已有的端口检测分支。仅继续选择内置 OPPO 450 引导即可。

本轮只保存证据，**未擅自改动外部工具箱的配置文件**。所有新增分析、
脚本和记录均在本设备树 `analysis/` 下，没有为 COM 端口错误修改 Fox。
