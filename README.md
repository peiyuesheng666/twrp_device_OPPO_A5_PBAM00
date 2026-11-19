# OPPO A5 / PBAM00 — TWRP & OrangeFox device tree

### 已工作功能 / Working

- ADB 侧载 / ADB Sideload
- 电池与充电状态 / Battery and Charger status
- 屏幕亮度调节 / Brightness control
- 屏幕显示 / Display
- 存储解密 / Storage decryption
- 触摸屏 / Touchscreen
- ADB / ADB connection

上述功能已由用户在 PBAM00 上确认。当前修复为安装镜像列表加入 System image 原始分区目标；重新构建后仍需设备上确认该入口显示并完成镜像刷写验证，因此暂不列为已验证功能。

TWRP / OrangeFox 共用硬件树，仅面向 2018 OPPO A5 **PBAM00**，不表示兼容所有年份的 A5。正式产品为 `omni_PBAM00`、设备代号为 `PBAM00`；`OPPO A5` 只是展示名称。维护者沿用作者 sheng 树的 `peiyuesheng`，Fox variant / TW_DEVICE_VERSION 为 `peiyuesheng_PBAM00`。

2026-11-18 OrangeFox R11.1 PBAM00 已交付目录并在目标机验证。用户确认无锁屏密码的 A.35 FDE 自动解密成功、`/data` 和内置存储可用，且显示、亮度、维护者头像和版本正确。EDL 菜单与 Bootloader 菜单均保留；正常 Android 和 Fox EDL 路径均已完成 Sahara 上传及 Firehose NOP ACK。test-4 刷写仅写 recovery，没有刷后回读。OrangeFox 完成交付后继续同步和编译 TWRP。

2026-11-19 已用锁定的 TeamWin `twrp-9.0` / Omni Android 9 源码成功编译并经 ADB 刷入 PBAM00 的 recovery 分区。TWRP `3.7.0_9-peiyuesheng_PBAM00` 已实机启动，root ADB 正常；设备 `/data` 已解密并以 ext4 rw 挂载，约 51 GiB 可用。用户确认功能正常。镜像大小 34,549,760 字节，小于 recovery 分区限制；SHA-256 为 `6c859aaad89750581793af9b15669fe8276c87bf5e1121738bf4411eb01eb992`。刷写仅覆盖 recovery，没有进行分区回读，也未格式化或备份 userdata。

## 结构与参考

主要参考 [R9s / R9sk 树](https://github.com/mominqimiang/twrp_device_oppo_r9s_r9sk)，快照 `419c03d`：保留 `Android.mk`、`AndroidProducts.mk`、`BoardConfig.mk`、`device.mk`、`omni_PBAM00.mk`、`vendorsetup.sh`、`prebuilt/Image.gz-dtb`、`recovery/root/` 布局。

[sheng 树](https://github.com/peiyuesheng666/twrp_device_xiaomi_sheng)，快照 `2a05a06`，参考共用树、OrangeFox 配置分离及维护版本命名。PBAM00 不采用其动态分区、virtual A/B、header v2、独立 DTB、FBE、屏幕旋转、AVB 测试密钥或虚构系统版本号。

## 硬件与打包

- 目标：2018 OPPO A5 PBAM00，SDM450 / msm8953 平台族，arm64 + arm，720 × 1520。
- 原厂 A.35 recovery 提取的 Linux 4.9.82-perf+ 内核，保留追加 DTB；不是此前循环重启的自编译内核。
- 独立 recovery 分区，非 A/B；无 vendor_boot、super 或 recovery-as-boot。
- Android boot image header v0，gzip ramdisk，2048 字节页面。
- base `0x80000000`；kernel offset `0x00008000`；ramdisk offset `0x01000000`；second offset `0x00f00000`；tags offset `0x00000100`。
- recovery 分区大小 `67108864` 字节；boot 同样为 64 MiB。
- 原厂 recovery 的 cmdline 是基础，只将 buildvariant 改成 eng 并追加 permissive 参数。

后期打包沿用 R9s 的 `Image.gz-dtb + recovery ramdisk → recovery.img` 形式。TWRP 输出独立 `recovery.img`；OrangeFox 还可由自身构建系统生成安装 ZIP。设备树不自带刷写 ZIP 脚本，不手工拼装未知安装器。

**原厂 recovery 存在 AVB footer。** 当前配置只描述普通 v0 recovery 镜像，未配置自定义签名或 footer。独立 recovery.img 的结构正确不代表引导链会接受；后续编译时需核对原厂 AVB 描述和解锁状态，再决定是否补充与原厂对应的 unsigned hash footer。不要照搬 sheng 的签名和 rollback 配置。

## 构建入口

OrangeFox 使用 fox_9.0 / Omni Pie；TWRP 使用 TeamWin `twrp-9.0` / Omni Android 9。当前产品继承 `vendor/omni`；若以后换成仅含 `vendor/twrp` 的分支，需要调整产品继承及 lunch 名称。TWRP 所需 Qualcomm `libcryptfs_hw` 与 QSEE ioctl 头文件已随本设备树提供，不依赖源码树外的 Qualcomm vendor 仓库。

将本目录放到源码的 `device/oppo/PBAM00`：

```bash
bash device/oppo/PBAM00/scripts/build-recovery.sh
```

OrangeFox 使用相应源码树，保留同样设备目录和 lunch 产品；`vendorsetup.sh` 设置 Fox 环境变量，`BoardConfig.mk` 检测 `bootable/recovery/orangefox.mk` 后加载 `orangefox.mk`。Fox 安装 ZIP 的最终目标和文件名依所选分支确认。

构建入口、原厂支持、资源和必须修改 Recovery 源码的补丁均位于本设备树。`scripts/build-recovery.sh` 和 `vendorsetup.sh` 自动运行 `recovery-patches/apply.py`，安装仅由 `TW_CRYPTO_OPPO_DEFAULT_PASSWORD_PATH` 开启的 FDE 适配；不依赖工作区绝对路径。可在配置好的 Pie 编译主机上指定 `OUT_DIR`、`TMPDIR` 和 `JOBS`。外部 WSL 包装脚本只负责存储、主机兼容环境与复制本树。

`scripts/verify-patches.py <源码根目录>` 从 Recovery 仓库干净 HEAD 的原文件重放补丁，再逐字节核对当前改动。原厂文件与内核哈希、头像源图与缩图均随树保存；`scripts/prepare-theme.py` 可仅用树内文件重建头像。编译后自动运行树内 `scripts/validate-image.py`，Fox 还会运行 `scripts/validate-package.py`。PBAM00 的默认口令适配已在 OrangeFox 和 TWRP 9.0 两个源码布局上编译通过，TWRP 已实机确认 `/data` 自动解密并挂载。

Fox 核心版本显示 `R11.1`，构建类型保留 `Unofficial`，设备变体为 `peiyuesheng_PBAM00`。维护者头像沿用 sheng 树的原图，原图及来源哈希记录在 `assets/`；打包资源为同图缩小到原主题所需的 192 × 192，避免把 4096 像素头像直接套进旧版主题。

## 实机测试约定

用户于 2026-11-18 明确要求：**本次及以后刷写均不回读分区**，包括刷后对块设备计算哈希这种等效回读。保留电脑端产物校验、目标身份/分区路径检查、刷写命令结果及启动功能测试。首版历史记录中的回读发生在此要求之前，不应据此继续回读。当前测试授权范围仅 recovery，不格式化或备份 userdata。

## 适配配置与验证边界

- USB 已按原厂 configfs 适配：g1、ffs.adb、mtp.gs0、mass_storage.0、OS 描述符、模式清理与 UDC 绑定完整接入。支持 adb、mtp、mtp+adb、mass_storage+adb；使用 A.35 原厂 VID/PID。ADB 的 FunctionFS 挂载与 adbd service 沿用 TWRP 基础 init，禁用它默认的 USB 状态机以避免重复绑定。UMS 指向真实 configfs LUN，只由 TWRP 用户操作选择外置存储，不自动暴露原厂 DRIVER 分区。
- 触控已接入原厂 `/proc/touchpanel/tp_fw_update` 启动触发；从同版本 vendor 导入 18031 / 18171 共 51 个触控固件和参数文件，放在 ramdisk `/vendor/firmware/tp/`。cmdline 和 init 均指定 firmware 搜索路径，无须先挂载系统 vendor 才能加载触控固件。
- 设备权限已导入 A.35 原厂 `ueventd.rc` 和 `ueventd.qcom.rc`，包含输入、显示、MTP、USB、QSEE 等节点权限；没有复制原厂 init 中的 fsck 或系统修复服务。
- 分区别名：Pie ueventd 未生成旧式 `/dev/block/bootdevice`；init 建立指向 `/dev/block/platform/soc/7824900.sdhci` 的链接，供 fstab、固件服务和安装器共同使用。临时补链接后，本机已能识别加密分区，原先 0 MB 并非容量参数错误。
- 解密使用 footer FDE；启用 `TW_INCLUDE_CRYPTO`、`TARGET_HW_DISK_ENCRYPTION`，并将 Qualcomm `libcryptfs_hw` 与 QSEE ioctl 头文件放在 `crypto/cryptfs_hw/` 随设备树交付。原厂 `aes-xts` 对应 Qualcomm `req-crypt`，不可直接交给软件 dm-crypt，后者会报 `IV mechanism required`。
- A.35 原厂 qseecomd、keymaster 3.0 HAL、hwservicemanager 及依赖使用独立 `/sbin/a5-stock/linker64` 与原厂库。补齐 qseecomd 通过 dlopen 加载的监听库；HAL 放在 **libhidltransport** 搜索的 `/vendor/lib64/hw`。加入 Oreo `nonplat_*` 到 Pie `vendor_*` 上下文文件的兼容链接，modem 固件分区只读挂载到 `/firmware`。这些临时修复已使本机三个服务正常运行，但还须用重新构建的硬件解密路径验证最终解密结果。
- 背光实测路径为 `/sys/class/leds/lcd-backlight/brightness`，上限 `2047`，默认改为 `1400`（约 68%）。旧版路径不存在，回退后的亮度 200 仅约 10%。
- Fox portrait_hdpi 使用 1080 宽设计坐标，720 × 1520 屏幕对应 `OF_SCREEN_H=2280`，使 X/Y 都缩放为 2/3。状态栏设计高度 120，左右留白各 60，避免贴边；第二版实机中，用户已确认显示和默认亮度正常，ADB 也能在重启后自动连接。
- 历史第二版 OrangeFox 曾无法解密。用户确认正常系统未设置锁屏密码；A.35 原厂 Recovery 的 `decrypt_default` 调用 `getDefString`，根据序列号使用 OEM 算法生成默认口令，并非 AOSP 的 `default_password`。本树的 `crypto/oppo_default_password.h` 对应此流程，不记录生成值；开启此适配时禁用旧 Lollipop 密码迁移写入。后续 OrangeFox 版本及本次 TWRP 均已在本机确认自动解密和挂载成功。
- 原厂 qseecomd 会降权运行，其子进程需要穿过 `/sbin` 读取隔离库。仅调整 `/sbin/a5-stock` 和库文件权限还不够；init 同时将 `/sbin` 设为 0755。该项已在第二版运行环境验证：libdrmtime、libqisl、libGPreqcancel 均成功加载并注册监听；原厂本就缺少的可选 libspl 不从其他设备混入。
- 直接打开并读取 `/dev/graphics/fb0` 后用户反馈屏幕只剩背光，Fox 进程及 ADB 仍正常；重启 recovery 界面后用户确认恢复。停止此种截图方式，改用 Fox 内置 `screenshotinternal`（电源+音量减）。未将疑似驱动交互写成已证明的根因。
- fstab 为 System 增加独立 `system_image` 镜像目标，指向设备实际的 `/dev/block/bootdevice/by-name/system`，供 TWRP 与 OrangeFox 的“安装镜像”列表使用；编译镜像会静态检查该项。NV、设备身份、bootloader 等分区不提供格式化入口。
- PBAT00、海外 AX5 等其他变体未验证，OTA assert 仅包含 PBAM00。
- 启用 `TW_HAS_EDL_MODE`，在原生重启菜单显示 EDL，调用内核/init 的 `reboot,edl` 路径，不依赖 Fastboot；按用户要求同时保留 Bootloader 菜单入口。2026-11-18 的 OrangeFox test-4 从 Recovery 路径进入 9008 后，同一 Sahara programmer 成功传输，Firehose NOP 返回 ACK；只做握手，不写或读取设备分区。物理按键关机进入 9008 尚未单独验证。

`prebuilt/provenance.json` 记录原厂 recovery / 内核 SHA-256、原始 header、cmdline 和本地分区大小证据。预编译内核来自本机原厂备份，其再分发许可需随固件来源核实；新增配置采用 Apache-2.0，原厂内核适用其原有许可。

`prebuilt/stock-support.json` 逐文件记录原厂固件与运行库来源、SHA-256、大小和 ELF 依赖。三个服务只有 ELF 解释器路径经 patchelf 调整，记录修改前后哈希；原始库和触控固件保留原字节。原厂文件保留各自许可。

`tools/create_a5_recovery_tree.py` / `tools/install_a5_stock_support.py` 是工作区中最初的导入工具，不是发布树的构建依赖，也不应覆盖当前维护树。构建所需的已提取文件、补丁、配置、头像及检查脚本已经随树提供。
