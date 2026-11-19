"""Inspect compiled recovery offline; never communicates with a phone."""
from pathlib import Path
import gzip
import hashlib
import json
import stat
import struct
import sys

image = Path(sys.argv[1])
tree = Path(__file__).resolve().parents[1]
b = image.read_bytes()
assert b[:8] == b'ANDROID!'
k, ka, r, ra, second, sa, ta, page, version, osver = struct.unpack_from('<10I', b, 8)
assert version == 0 and page == 2048 and second == 0
provenance = json.loads((tree/'prebuilt/provenance.json').read_text())
assert osver == int(provenance['stock_os_version_raw'], 16), 'OS compatibility fields differ from stock'
assert (ka, ra, sa, ta) == (0x80008000, 0x81000000, 0x80f00000, 0x80000100)
assert len(b) <= 67108864
kernel = b[page:page+k]
assert kernel == (tree/'prebuilt/Image.gz-dtb').read_bytes()
start = page + ((k+page-1)//page)*page
ramdisk = b[start:start+r]
image_id = hashlib.sha1()
for payload in (kernel, ramdisk, b''):
    image_id.update(payload)
    image_id.update(struct.pack('<I', len(payload)))
standard_id = image_id.digest()
# The Omni Pie Qualcomm mkbootimg also hashes a zero-length DT slot for v0.
image_id.update(struct.pack('<I', 0))
legacy_dt_id = image_id.digest()
assert b[576:596] in (standard_id, legacy_dt_id), 'Boot image ID does not match payloads'
d = gzip.decompress(ramdisk)
entries = {}
offset = 0
while d[offset:offset+6] in (b'070701', b'070702'):
    h = [int(d[offset+6+j*8:offset+14+j*8], 16) for j in range(13)]
    name = d[offset+110:offset+110+h[11]-1].decode().removeprefix('./')
    start = (offset+110+h[11]+3)&~3
    payload = d[start:start+h[6]]
    offset = (start+h[6]+3)&~3
    if name == 'TRAILER!!!':
        break
    entries[name] = (h[1], payload)
required = ['init', 'init.rc', 'sbin/recovery', 'sbin/adbd', 'sbin/libcryptfs_hw.so',
            'sbin/libcryptfsfde.so', 'etc/recovery.fstab',
            'init.recovery.qcom.rc', 'init.recovery.a5.usb.rc',
            'init.recovery.a5.services.rc', 'ueventd.qcom.rc',
            'sbin/a5-stock/linker64', 'sbin/a5-stock/qseecomd',
            'sbin/a5-stock/android.hardware.keymaster@3.0-service-qti',
            'sbin/a5-stock/hwservicemanager',
            'vendor/lib64/hw/android.hardware.keymaster@3.0-impl-qti.so']
for name in required:
    assert name in entries, name
    if name.startswith('sbin/') and not name.endswith('.so'):
        assert entries[name][0]&0o111, f'Executable permission missing: {name}'
manifest = json.loads((tree/'prebuilt/stock-support.json').read_text())
for row in manifest['imported']:
    assert row['path'] in entries, row['path']
    assert hashlib.sha256(entries[row['path']][1]).hexdigest() == row['sha256'], row['path']
for name, (mode, _) in entries.items():
    if name.endswith('.rc') and stat.S_ISREG(mode):
        assert not mode&0o022, f'Init configuration is group/world writable: {name}'
services = {}
for name, (_, contents) in entries.items():
    if name.endswith('.rc') and name.startswith('init'):
        for line in contents.decode(errors='replace').splitlines():
            if line.startswith('service '):
                service = line.split()[1]
                services.setdefault(service, []).append(name)
assert not any(len(v)>1 for v in services.values()), services
device_init = entries['init.recovery.qcom.rc'][1].decode()
fstab = entries['etc/recovery.fstab'][1].decode(errors='replace')
system_image = next((line.split() for line in fstab.splitlines()
                     if line.startswith('/system_image ')), None)
assert system_image is not None and 'flashimg=1' in system_image[-1], \
    'System image flash target missing'
assert system_image[1] == 'emmc' and \
    system_image[2] == '/dev/block/bootdevice/by-name/system', \
    'System image target does not map to the PBAM00 system partition'
for partition in ('boot', 'recovery'):
    assert any(line.startswith(f'/{partition} ') and 'flashimg=1' in line
               for line in fstab.splitlines()), \
        f'{partition} image flash target missing'
assert 'setprop sys.usb.ffs.aio_compat 1' in device_init
assert 'chmod 0755 /sbin\n' in device_init
assert 'symlink /dev/block/platform/soc/7824900.sdhci /dev/block/bootdevice' in device_init
assert 'symlink /vendor_hwservice_contexts /nonplat_hwservice_contexts' in device_init
assert 'write /sys/class/leds/lcd-backlight/brightness 1400' in device_init
assert 'ro.product.device=PBAM00' in entries['prop.default'][1].decode()
assert b'peiyuesheng_PBAM00' in entries['sbin/recovery'][1]
assert b'TW_HAS_EDL_MODE := true' in entries['sbin/recovery'][1]
assert b'TW_NO_REBOOT_BOOTLOADER := true' not in entries['sbin/recovery'][1]
assert b'Using PBAM00 stock default-password algorithm' in entries['sbin/libcryptfsfde.so'][1]
assert 'sbin/logcat' in entries and 'sbin/logd' in entries
avatar = json.loads((tree/'assets/maintainer-provenance.json').read_text())
assert hashlib.sha256(entries[avatar['packed_path']][1]).hexdigest() == avatar['packed_sha256']
for item in manifest['imported']:
    if item['path'].startswith('sbin/a5-stock/') and item['path'].endswith('.so'):
        assert f"chmod 0644 /{item['path']}" in device_init, item['path']
result = dict(image=str(image), bytes=len(b), sha256=hashlib.sha256(b).hexdigest(),
              header_version=version, page_size=page, stock_kernel_matches=True,
              ramdisk_entries=len(entries), stock_support_files_checked=len(manifest['imported']),
              duplicate_services=False, os_version_raw=hex(osver), flashed=False,
              edl_menu_enabled=True, bootloader_menu_preserved=True,
              oppo_default_password_adapter=True, maintainer_avatar_matches=True,
              cmdline=b[64:576].split(b'\0')[0].decode())
image.with_suffix('.validation.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
