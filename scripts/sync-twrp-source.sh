#!/usr/bin/env bash
# Run from the E-backed A5-Recovery WSL instance.
set -euo pipefail
source /mnt/e/OPPOA5UnlockBootLoader/recovery-build/env-native.sh
tree=/mnt/e/OPPOA5UnlockBootLoader/twrp_device_oppo_PBAM00
exec > >(tee -a "$A5_BUILD_ROOT/logs/twrp-sync.log") 2>&1
cd "$A5_BUILD_ROOT/twrp"

repo init -u https://github.com/minimal-manifest-twrp/platform_manifest_twrp_omni.git \
    -b twrp-9.0 --depth=1 --no-clone-bundle </dev/null
repo sync -c --no-clone-bundle --no-tags --optimized-fetch -j3 \
    --retry-fetches=3 --force-checkout --force-sync
repo manifest -r -o "$tree/manifests/twrp-pinned.xml"
mkdir -p device/oppo
rsync -a --delete --chmod=Du=rwx,Dgo=rx,Fu=rw,Fgo=r "$tree/" device/oppo/PBAM00/
printf 'TWRP_SOURCE_READY\n'
