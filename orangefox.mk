# SPDX-License-Identifier: Apache-2.0
FOX_BUILD_DEVICE := PBAM00
FOX_BUILD_TYPE := Unofficial
FOX_VERSION := R11.1
FOX_VARIANT := peiyuesheng_PBAM00
FOX_RECOVERY_INSTALL_PARTITION := /dev/block/bootdevice/by-name/recovery
FOX_USE_TWRP_RECOVERY_IMAGE_BUILDER := 1
OF_MAINTAINER := peiyuesheng
# Theme coordinates have a 1080 px design width; the LCD is 720 x 1520.
# 2280 * (720 / 1080) = 1520, keeping X and Y scaling identical.
OF_SCREEN_H := 2280
OF_STATUS_H := 120
OF_STATUS_INDENT_LEFT := 60
OF_STATUS_INDENT_RIGHT := 60
OF_CLOCK_POS := 1
OF_DONT_PATCH_ENCRYPTED_DEVICE := 1
OF_DONT_PATCH_ON_FRESH_INSTALLATION := 1
# Non-A/B, static partitions, FDE. No virtual-A/B or FBE flags.
