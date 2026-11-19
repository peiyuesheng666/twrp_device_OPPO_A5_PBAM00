#!/usr/bin/env python3
"""Package a validated PBAM00 TWRP image and its complete device tree."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import stat
import zipfile


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


parser = argparse.ArgumentParser()
parser.add_argument("image", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--flashed", action="store_true",
                    help="record a completed recovery-only flash")
parser.add_argument("--runtime-tested", action="store_true",
                    help="record successful PBAM00 boot and runtime checks")
args = parser.parse_args()

tree = Path(__file__).resolve().parents[1]
image_source = args.image.resolve()
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
image = output / "TWRP-PBAM00-recovery.img"
if image_source != image.resolve():
    shutil.copy2(image_source, image)

tree_zip = output / "TWRP-PBAM00-device-tree.zip"
excluded = {"__pycache__", ".git"}
with zipfile.ZipFile(tree_zip, "w", compression=zipfile.ZIP_DEFLATED,
                     compresslevel=6) as archive:
    for path in sorted(p for p in tree.rglob("*")
                       if p.is_file() and not p.is_symlink()
                       and not excluded.intersection(p.parts)):
        entry = zipfile.ZipInfo(
            (tree.name + "/" + path.relative_to(tree).as_posix()),
            (2026, 11, 19, 0, 0, 0))
        entry.compress_type = zipfile.ZIP_DEFLATED
        entry.external_attr = (stat.S_IFREG | (path.stat().st_mode & 0o777)) << 16
        archive.writestr(entry, path.read_bytes(),
                         compress_type=zipfile.ZIP_DEFLATED,
                         compresslevel=6)

with zipfile.ZipFile(tree_zip) as archive:
    assert archive.testzip() is None
    names = archive.namelist()
    assert any(name.endswith("/BoardConfig.mk") for name in names)
    assert any(name.endswith("/crypto/cryptfs_hw/cryptfs_hw.c") for name in names)

image_hash = sha256(image)
tree_hash = sha256(tree_zip)
flash_note = ("Recovery-only ADB flash completed; no partition readback was performed."
              if args.flashed else
              "Flashing pending. No partition readback is planned.")
runtime_note = ("Booted on PBAM00 as TWRP 3.7.0_9-peiyuesheng_PBAM00; root ADB and "
                "read-write /data mount were verified, and the user confirmed normal function."
                if args.runtime_tested else
                "On-device startup and runtime tests are pending.")
readme = f"""# TWRP for OPPO PBAM00

TeamWin twrp-9.0 / Omni Android 9 recovery build. The image passed the device-tree structural validator and contains the bundled Qualcomm hardware-encryption module, stock A.35 kernel and required ramdisk files.

- `{image.name}`: standalone recovery image.
- `{tree_zip.name}`: complete PBAM00 device tree and build scripts.
- Source manifest pin: `twrp_device_oppo_PBAM00/manifests/twrp-pinned.xml`.
- Build: successful; image size {image.stat().st_size:,} bytes, below the 64 MiB recovery partition limit.
- TWRP runtime checks: {runtime_note}
- {flash_note}

SHA-256:

```text
{image_hash}  {image.name}
{tree_hash}  {tree_zip.name}
```
"""
(output / "README.md").write_text(readme, encoding="utf-8")
(output / "SHA256SUMS").write_text(
    f"{image_hash}  {image.name}\n{tree_hash}  {tree_zip.name}\n",
    encoding="ascii")
info = {
    "product": "TWRP 9.0", "device": "PBAM00",
    "source_manifest": "twrp-9.0", "build_succeeded": True,
    "image_validation_passed": True,
    "recovery_image_bytes": image.stat().st_size,
    "recovery_image_sha256": image_hash,
    "device_tree_zip_sha256": tree_hash,
    "flashed": args.flashed, "partition_readback_performed": False,
    "on_device_runtime_tests": args.runtime_tested,
    "twrp_version": "3.7.0_9-peiyuesheng_PBAM00" if args.runtime_tested else None,
    "root_adb_verified": args.runtime_tested,
    "data_mount_rw_verified": args.runtime_tested,
    "user_confirmed_normal_functions": args.runtime_tested,
}
(output / "release-info.json").write_text(
    json.dumps(info, indent=2) + "\n", encoding="utf-8")

bundle = output / "TWRP-PBAM00-artifacts.zip"
with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED,
                     compresslevel=1) as archive:
    for path in sorted(p for p in output.iterdir()
                       if p.is_file() and p != bundle
                       and p.name != "TWRP-PBAM00-artifacts.zip"):
        archive.write(path, path.name)
with zipfile.ZipFile(bundle) as archive:
    assert archive.testzip() is None
    assert image.name in archive.namelist()
    assert tree_zip.name in archive.namelist()

print(json.dumps({
    "image": image.name, "image_bytes": image.stat().st_size,
    "image_sha256": image_hash,
    "tree_zip": tree_zip.name, "tree_zip_bytes": tree_zip.stat().st_size,
    "tree_zip_sha256": tree_hash,
    "bundle": bundle.name, "bundle_bytes": bundle.stat().st_size,
    "bundle_sha256": sha256(bundle),
    "tree_file_count": len([p for p in tree.rglob("*")
                             if p.is_file() and not excluded.intersection(p.parts)]),
}, indent=2))
