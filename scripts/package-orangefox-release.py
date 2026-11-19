#!/usr/bin/env python3
"""Package already-built PBAM00 OrangeFox outputs; no phone I/O."""
import hashlib
import json
import shutil
import sys
import subprocess
import zipfile
from datetime import date
from pathlib import Path

source = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2]).resolve()
tree = Path(__file__).resolve().parents[1]
if output.exists():
    raise SystemExit(f'Refusing to overwrite existing release directory: {output}')
img = next(source.glob('OrangeFox-*-Unofficial-PBAM00.img'))
package = next(source.glob('OrangeFox-*-Unofficial-PBAM00.zip'))
# The build validates recovery.img before OrangeFox renames it. Revalidate the
# final published filenames so each artifact has its own adjacent report.
subprocess.run([sys.executable, str(tree / 'scripts/validate-image.py'), str(img)], check=True)
subprocess.run([sys.executable, str(tree / 'scripts/validate-package.py'), str(package), str(img)], check=True)
flash = tree.parent / 'recovery-build/results/orangefox/pbam00-test-4-edl/flash-result.json'
tests = tree / 'analysis/edl-tests-summary.json'
assert flash.is_file() and tests.is_file()
flash_record = json.loads(flash.read_text())
edl_record = json.loads(tests.read_text())
assert flash_record['device'] == 'PBAM00' and flash_record['partition'] == '/dev/block/mmcblk0p28'
assert flash_record['flash_exit_code'] == 0 and not flash_record['partition_readback_performed']
assert not flash_record['userdata_formatted_or_backed_up']
assert edl_record['all_handshakes_passed'] and not edl_record['partition_io_performed']
image_validation = json.loads(img.with_suffix('.validation.json').read_text())
package_validation = json.loads(package.with_name(package.name + '.validation.json').read_text())
assert image_validation['sha256'] == hashlib.sha256(img.read_bytes()).hexdigest()
assert package_validation['recovery_sha256'] == image_validation['sha256']
assert package_validation['crc_valid'] and package_validation['recovery_matches']

output.mkdir(parents=True)
files = [img, package, source / 'SHA256SUMS']
files.extend(source / (f.name + '.md5') for f in (img, package))
files.extend([img.with_suffix('.validation.json'), package.with_name(package.name + '.validation.json')])
files.append(tree / 'FEATURES.md')
for f in files:
    if f.is_file():
        shutil.copy2(f, output / f.name)
shutil.copy2(flash, output / 'flash-result.json')
shutil.copy2(tests, output / 'edl-tests-summary.json')

hashes = {img.name: hashlib.sha256(img.read_bytes()).hexdigest(),
          package.name: hashlib.sha256(package.read_bytes()).hexdigest()}
manifest = dict(product='OrangeFox R11.1', device='PBAM00', build_type='Unofficial',
                maintainer='peiyuesheng', source_build_date=date.today().isoformat(),
                artifacts=hashes, image_validation_passed=True,
                zip_validation_passed=True, recovery_only_flash_succeeded=True,
                partition_readback_performed=False,
                edl_sahara_and_nop_tests_passed=True,
                actual_firehose_flash_test=False)
(output / 'release-info.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
readme = '''# OrangeFox R11.1 for OPPO PBAM00

Unofficial recovery for 2018 OPPO A5 model PBAM00, maintained by peiyuesheng.

- `.img`: standalone recovery image.
- `.zip`: OrangeFox recovery installer package.
- `SHA256SUMS`, `.md5`: artifact integrity checks.
- `*.validation.json`: offline Android image and installer package checks.
- `flash-result.json`: previously completed recovery-only flash record; no partition readback.
- `edl-tests-summary.json`: Android and OrangeFox Sahara upload plus Firehose NOP tests. These were handshake tests, not a Firehose partition-flash test.

The target device has booted this release. The user confirmed automatic decryption of the A.35 FDE data partition without a lock-screen password, usable internal storage, correct display/brightness, avatar, and R11.1 version. The EDL and Bootloader menu entries are both present.

The prior flash wrote only recovery. No partition readback was performed; userdata was not formatted or backed up.

SHA-256:

```text
''' + ''.join(f'{digest}  {name}\n' for name, digest in hashes.items()) + '''```
'''
(output / 'README.md').write_text(readme, encoding='utf-8')
bundle = output / 'OrangeFox-R11.1-PBAM00-artifacts.zip'
with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
    for f in sorted(output.iterdir()):
        if f != bundle and f.is_file():
            archive.write(f, f.name)
with zipfile.ZipFile(bundle) as archive:
    assert archive.testzip() is None
print(json.dumps(dict(output=str(output), artifacts=hashes,
                      bundle=bundle.name, bundle_bytes=bundle.stat().st_size,
                      bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest()), indent=2))
