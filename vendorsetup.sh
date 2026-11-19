#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
if [[ -d bootable/recovery/crypto/fde ]]; then
    # Keep the OEM crypto adapter with the device tree, including clean builds.
    python3 "$(dirname "${BASH_SOURCE[0]}")/recovery-patches/apply.py" "$PWD" || return 1
fi
if type add_lunch_combo >/dev/null 2>&1; then
    add_lunch_combo omni_PBAM00-userdebug
    add_lunch_combo omni_PBAM00-eng
fi
if [[ -f bootable/recovery/orangefox.mk ]]; then
    export FOX_BUILD_DEVICE=PBAM00
    export FOX_BUILD_TYPE=Unofficial
    export FOX_VERSION=R11.1
    export FOX_VARIANT=peiyuesheng_PBAM00
    export FOX_RECOVERY_INSTALL_PARTITION=/dev/block/bootdevice/by-name/recovery
    export TARGET_DEVICE_ALT=PBAM00
    export FOX_USE_TWRP_RECOVERY_IMAGE_BUILDER=1
    export OF_MAINTAINER=peiyuesheng
    export OF_DONT_PATCH_ENCRYPTED_DEVICE=1
    export OF_DONT_PATCH_ON_FRESH_INSTALLATION=1
    export OF_USE_LZ4_COMPRESSION=0
fi
