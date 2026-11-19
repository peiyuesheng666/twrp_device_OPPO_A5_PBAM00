from pathlib import Path
import hashlib
import json
import sys
import zipfile

package = Path(sys.argv[1])
image = Path(sys.argv[2])
with zipfile.ZipFile(package) as archive:
    assert archive.testzip() is None, 'ZIP CRC check failed'
    assert archive.namelist().count('recovery.img') == 1
    packed_image = archive.read('recovery.img')
    assert packed_image == image.read_bytes(), 'ZIP recovery differs from validated image'
    installer = archive.read('META-INF/com/google/android/update-binary').decode()
    assert 'TARGET_DEVICE="PBAM00"' in installer
    assert 'TARGET_DEVICE_ALT="PBAM00"' in installer
    assert 'RECOVERY_PARTITION="/dev/block/bootdevice/by-name/recovery"' in installer
    result = dict(package=str(package), bytes=package.stat().st_size,
                  sha256=hashlib.sha256(package.read_bytes()).hexdigest(),
                  recovery_sha256=hashlib.sha256(packed_image).hexdigest(),
                  crc_valid=True, recovery_matches=True,
                  target_devices=['PBAM00'],
                  recovery_partition='/dev/block/bootdevice/by-name/recovery')
package.with_suffix('.zip.validation.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
