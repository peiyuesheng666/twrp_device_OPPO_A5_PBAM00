# SPDX-License-Identifier: Apache-2.0
# R9s-style standalone recovery; all layout values below come from A5 A.35.
DEVICE_PATH := device/oppo/PBAM00
# Minimal recovery manifests omit full-ROM modules (same setting as R9s).
ALLOW_MISSING_DEPENDENCIES := true
TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv8-a
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_ABI2 :=
TARGET_CPU_VARIANT := generic
TARGET_2ND_ARCH := arm
TARGET_2ND_ARCH_VARIANT := armv7-a-neon
TARGET_2ND_CPU_ABI := armeabi-v7a
TARGET_2ND_CPU_ABI2 := armeabi
TARGET_2ND_CPU_VARIANT := generic
TARGET_BOARD_SUFFIX := _64
TARGET_USES_64_BIT_BINDER := true
TARGET_BOARD_PLATFORM := msm8953
TARGET_NO_BOOTLOADER := true
# Keep the Bootloader menu entry and also expose the direct EDL route.
TW_HAS_EDL_MODE := true
TARGET_NO_RADIOIMAGE := true
TARGET_OTA_ASSERT_DEVICE := PBAM00

TARGET_PREBUILT_KERNEL := $(DEVICE_PATH)/prebuilt/Image.gz-dtb
TARGET_KERNEL_ARCH := arm64
TARGET_KERNEL_HEADER_ARCH := arm64
BOARD_KERNEL_IMAGE_NAME := Image.gz-dtb
BOARD_BOOT_HEADER_VERSION := 0
BOARD_KERNEL_BASE := 0x80000000
BOARD_KERNEL_OFFSET := 0x00008000
BOARD_RAMDISK_OFFSET := 0x01000000
BOARD_KERNEL_SECOND_OFFSET := 0x00f00000
BOARD_KERNEL_TAGS_OFFSET := 0x00000100
BOARD_KERNEL_PAGESIZE := 2048
BOARD_KERNEL_CMDLINE := console=ttyMSM0,115200,n8 androidboot.console=ttyMSM0 androidboot.hardware=qcom msm_rtb.filter=0x237 ehci-hcd.park=3 lpm_levels.sleep_disabled=1 androidboot.bootdevice=7824900.sdhci earlycon=msm_serial_dm,0x78af000 ramoops.mem_address=0x91400000 ramoops.mem_size=0x100000 ramoops.record_size=0x20000 ramoops.dump_oops=0 buildvariant=eng androidboot.selinux=permissive firmware_class.path=/vendor/firmware
BOARD_MKBOOTIMG_ARGS += --header_version 0
BOARD_MKBOOTIMG_ARGS += --kernel_offset $(BOARD_KERNEL_OFFSET)
BOARD_MKBOOTIMG_ARGS += --ramdisk_offset $(BOARD_RAMDISK_OFFSET)
BOARD_MKBOOTIMG_ARGS += --second_offset $(BOARD_KERNEL_SECOND_OFFSET)
BOARD_MKBOOTIMG_ARGS += --tags_offset $(BOARD_KERNEL_TAGS_OFFSET)
BOARD_FLASH_BLOCK_SIZE := 131072
BOARD_BOOTIMAGE_PARTITION_SIZE := 67108864
BOARD_RECOVERYIMAGE_PARTITION_SIZE := 67108864
BOARD_USES_RECOVERY_AS_BOOT := false
BOARD_RAMDISK_USE_LZ4 := false
# Stock has an AVB footer. Signing/unsigned-footer policy requires a later
# boot-chain review; no sheng test signing key or rollback values are copied.
BOARD_AVB_ENABLE := false
# Recovery compatibility fields match the installed PBAM00 A.35 firmware.
# Keep the Pie build SDK, but do not announce a newer OS to the boot chain.
PLATFORM_VERSION := 8.1.0
PLATFORM_SECURITY_PATCH := 2021-03-05
VENDOR_SECURITY_PATCH := $(PLATFORM_SECURITY_PATCH)

BOARD_HAS_LARGE_FILESYSTEM := true
BOARD_SYSTEMIMAGE_PARTITION_TYPE := ext4
BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_USERDATAIMAGE_FILE_SYSTEM_TYPE := ext4
TARGET_COPY_OUT_VENDOR := vendor
TARGET_USERIMAGES_USE_EXT4 := true
TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/recovery.fstab
TARGET_RECOVERY_PIXEL_FORMAT := RGBX_8888
RECOVERY_SDCARD_ON_DATA := true
TARGET_RECOVERY_DEVICE_DIRS += $(DEVICE_PATH)

TW_THEME := portrait_hdpi
TW_EXTRA_LANGUAGES := true
TW_DEFAULT_LANGUAGE := zh_CN
TW_INPUT_BLACKLIST := "hbtp_vm"
TW_BRIGHTNESS_PATH := /sys/class/leds/lcd-backlight/brightness
TW_MAX_BRIGHTNESS := 2047
TW_DEFAULT_BRIGHTNESS := 1400
TW_USE_TOOLBOX := true
TW_INCLUDE_CRYPTO := true
TWRP_INCLUDE_LOGCAT := true
TARGET_USES_LOGD := true
# Stock A.35 uses Qualcomm req-crypt (aes-xts), not software dm-crypt.
TARGET_HW_DISK_ENCRYPTION := true
TARGET_CRYPTFS_HW_PATH := device/oppo/PBAM00/crypto/cryptfs_hw
TW_CRYPTO_OPPO_DEFAULT_PASSWORD_PATH := $(DEVICE_PATH)/crypto
# FDE via stock QSEE + keymaster 3.0 services and the source-tree cryptfs client.
TW_DEVICE_VERSION := peiyuesheng_PBAM00

ifneq ($(wildcard bootable/recovery/orangefox.mk),)
include $(DEVICE_PATH)/orangefox.mk
endif

# Device USB RC owns configfs; do not install a second USB state machine.
TW_EXCLUDE_DEFAULT_USB_INIT := true
TARGET_USE_CUSTOM_LUN_FILE_PATH := /config/usb_gadget/g1/functions/mass_storage.0/lun.%d/file
