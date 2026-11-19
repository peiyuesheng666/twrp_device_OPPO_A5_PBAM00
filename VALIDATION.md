# 设备树与构建验证

截至 2026-11-19。设备树静态检查、TWRP Android 9 编译、recovery-only ADB 刷写及 PBAM00 启动验证均通过。TWRP 版本、root ADB 与 `/data` 挂载已检查；用户确认功能正常。未进行刷后分区回读。

本次修复：为 System 增加单独的 `system_image` 原始镜像刷写入口，映射到实机 `/dev/block/bootdevice/by-name/system`，使 TWRP 与 OrangeFox 的“安装镜像”列表能枚举 System。新的两份镜像完成编译和离线结构验证后，仍需在设备界面确认 System 选项；本次不执行 System 分区刷写。

2026-11-19 复编结果：OrangeFox R11.1 与 TWRP 3.7.0_9 均编译成功。最终命名的 OrangeFox `.img`/安装 ZIP 校验通过，ZIP 内 `recovery.img` 与独立镜像一致；TWRP 镜像通过 Android boot header、原厂内核哈希、64 MiB 大小、ramdisk 服务/原厂支持文件及 System/Boot/Recovery 镜像目标校验。此次仅构建和离线检查，没有刷入新 recovery 或写入 System 分区，因此 System 菜单显示和实际刷写仍待设备上确认。

- A.35 recovery 通过 Android header v0 的 kernel/ramdisk 大小与页对齐定位 ramdisk，解压 gzip 并解析 newc cpio；不从其他机型借用二进制。
- 从 A.35 vendor 的 ext4 镜像使用 debugfs 只读提取 `firmware/tp`，保留两个硬件项目目录，共 51 个文件。
- 逐一校验 `prebuilt/stock-support.json` 中 89 个导入文件的 SHA-256；三个服务的原始哈希与修改后哈希均记录。
- qseecomd / keymaster 3.0 service / hwservicemanager、动态加载的 keymaster HAL 以及 QSEE API 库递归展开 DT_NEEDED，共 35 个 ELF 节点。所有依赖均在独立运行库目录；`ld-android.so` 是 Android linker 提供的合成库，不需要磁盘文件。
- 三个服务 PT_INTERP 均指向存在的 `/sbin/a5-stock/linker64`；服务使用独立 LD_LIBRARY_PATH。未将原厂 libc、libdl、linker 覆盖到 TWRP 的 `/sbin` 同名文件。
- init 中的自定义 import 与 service 命令路径均存在，HAL 在原厂 libhardware 的 `/sbin/hw` 搜索目录。
- USB 参考原厂 recovery 与 vendor configfs 配置；ADB/MTP/UMS 的 function 先创建，再链接到配置，ADB 组合等 `sys.usb.ffs.ready=1` 后绑定。`none` 清理配置和停止 adbd，绑定后发布 sys.usb.state。TWRP 基础 init 负责 FunctionFS 挂载及 adbd service。
- 核对 TeamWin android-9.0 的 init.rc、Android.mk、crypto/fde/Android.mk、partitionmanager.cpp：自定义 USB 排除开关、加密入口、UMS LUN 路径变量和 USB 模式名均有源码对应。
- 为兼容精简的 TWRP manifest，将 Qualcomm `cryptfs_hw.c`、`cryptfs_hw.h` 和 `qseecom.h` 按上游提交复制到 `crypto/cryptfs_hw/`；用 Soong 模块定义生成 `libcryptfs_hw`，镜像中确认包含 `sbin/libcryptfs_hw.so` 和 `sbin/libcryptfsfde.so`。来源提交与 SHA-256 记录于 `crypto/cryptfs_hw/PROVENANCE.md`。
- TeamWin `twrp-9.0` / Omni Android 9 编译完成：`recovery.img` 为 34,549,760 字节，SHA-256 `6c859aaad89750581793af9b15669fe8276c87bf5e1121738bf4411eb01eb992`。`scripts/validate-image.py` 检查 Android header v0、原厂内核匹配、分区大小、ramdisk 中 104 个原厂支持文件、服务路径、EDL/Bootloader 菜单和 OEM 默认口令适配。
- TWRP 已在 PBAM00 上启动；root ADB 可用，`/data` 已解密并以 ext4 rw 挂载，约 51 GiB。用户确认功能正常。此次未执行分区回读；OrangeFox 的早期测试结果不用于替代 TWRP 实测。
- OTG enable 使用 R9s 的 OPPO 开关方式，并核对官方 AX5 源码 `drivers/power/oppo/charger_ic/oppo_battery_sdm450_O.c` 的 OTG_SWITCH 属性及可写实现。

这些检查、成功编译与本机启动验证确认镜像可在 PBAM00 上启动并解密挂载 `/data`。用户确认其余功能正常。未执行刷后分区回读；未单独记录 Sahara/EDL、OTG 或每一种 USB 模式的 TWRP 实测结果。
