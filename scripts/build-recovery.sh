#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Run from an Android source root: bash device/oppo/PBAM00/scripts/build-recovery.sh
set -eo pipefail
test -f build/envsetup.sh
test -f build/soong/soong_ui.bash
device_path=device/oppo/PBAM00
test -f "$device_path/BoardConfig.mk"
export OUT_DIR=${OUT_DIR:-out-PBAM00}
mkdir -p "$OUT_DIR"
export OUT_DIR=$(cd "$OUT_DIR" && pwd)
export TMPDIR=${TMPDIR:-$OUT_DIR/pbam00-tmp}
mkdir -p "$TMPDIR" "$OUT_DIR/pbam00-host-bin"
# Pie's host tools require the complete Python 2 runtime, including zlib.
python2=$(command -v python2.7 || command -v python2)
"$python2" -c 'import zlib, zipfile'
ln -sfn "$python2" "$OUT_DIR/pbam00-host-bin/python"
export PATH="$OUT_DIR/pbam00-host-bin:$PATH"
export LC_ALL=C LANG=C
export ALLOW_MISSING_DEPENDENCIES=true

# OrangeFox's full source manifest already contains Qualcomm's cryptfs_hw and
# qseecom header Soong modules. The device-tree copies below fill the gap in
# the minimal TWRP manifest, so hide only those duplicate blueprints during a
# Fox build and always restore them before leaving this script.
disabled_bp_dir="$OUT_DIR/pbam00-disabled-blueprints"
disabled_hw_bp=false
disabled_qsee_bp=false
restore_device_blueprints() {
    if [[ "$disabled_hw_bp" == true ]]; then
        mv "$disabled_bp_dir/cryptfs_hw.Android.bp" "$device_path/crypto/cryptfs_hw/Android.bp"
    fi
    if [[ "$disabled_qsee_bp" == true ]]; then
        mv "$disabled_bp_dir/kernel-headers.Android.bp" "$device_path/crypto/cryptfs_hw/kernel-headers/Android.bp"
    fi
}
trap restore_device_blueprints EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
if [[ -f vendor/qcom/opensource/commonsys/cryptfs_hw/Android.bp ]] \
        && grep -q 'name: "libcryptfs_hw"' vendor/qcom/opensource/commonsys/cryptfs_hw/Android.bp \
        && grep -q 'name: "qseecom-kernel-headers"' vendor/qcom/opensource/commonsys/kernel-headers/Android.bp; then
    mkdir -p "$disabled_bp_dir"
    mv "$device_path/crypto/cryptfs_hw/Android.bp" "$disabled_bp_dir/cryptfs_hw.Android.bp"
    disabled_hw_bp=true
    mv "$device_path/crypto/cryptfs_hw/kernel-headers/Android.bp" "$disabled_bp_dir/kernel-headers.Android.bp"
    disabled_qsee_bp=true
    echo "Using source-manifest Qualcomm cryptfs_hw modules; device-tree files will be restored on exit."
fi

chmod 0755 "$device_path/vendorsetup.sh"
chmod 0755 "$device_path"/recovery/root/sbin/a5-stock/{linker64,qseecomd,hwservicemanager,android.hardware.keymaster@3.0-service-qti}
python3 "$device_path/recovery-patches/apply.py" "$PWD"
if [[ ! -f bootable/recovery/orangefox.mk ]]; then
    # Keep a TWRP build independent of a parent shell used for Fox earlier.
    for variable in ${!FOX_@} ${!OF_@}; do unset "$variable"; done
fi
source build/envsetup.sh
export TARGET_PRODUCT=omni_PBAM00
export TARGET_BUILD_VARIANT=eng
export TARGET_BUILD_TYPE=release
export ANDROID_PRODUCT_OUT=$OUT_DIR/target/product/PBAM00
export OUT=$ANDROID_PRODUCT_OUT
export TARGET_RECOVERY_ROOT_OUT=$ANDROID_PRODUCT_OUT/recovery/root
export TARGET_OUT=$ANDROID_PRODUCT_OUT/system
unset TARGET_BUILD_APPS TARGET_BUILD_DENSITY
jobs=${JOBS:-4}
if [[ ${1:-} == --resume ]]; then
    "$OUT_DIR/ninja-omni_PBAM00.sh" -j"$jobs" -d keepdepfile recoveryimage
else
    build/soong/soong_ui.bash --make-mode -j"$jobs" recoveryimage
fi
python3 "$device_path/scripts/validate-image.py" "$OUT/recovery.img"
if [[ -f bootable/recovery/orangefox.mk ]]; then
    python3 "$device_path/scripts/validate-package.py" "$OUT/OrangeFox-${FOX_VERSION:?}-${FOX_VARIANT:?}-${FOX_BUILD_TYPE:?}-PBAM00.zip" "$OUT/recovery.img"
fi
printf 'PBAM00_RECOVERY_BUILD_SUCCESS\n'
