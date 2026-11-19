#!/usr/bin/env python3
"""Check that all current Recovery source edits are reproduced by this tree."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

source = Path(sys.argv[1]).resolve()
tree = Path(__file__).resolve().parents[1]
repo = source / 'bootable/recovery'
expected = ['crypto/fde/Android.mk', 'crypto/fde/cryptfs.cpp']
changed = subprocess.check_output(['git', '-C', str(repo), 'diff', '--name-only'], text=True).splitlines()
assert sorted(changed) == sorted(expected), f'Unexpected Recovery edits: {changed}'
with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as directory:
    check = Path(directory)
    for name in expected:
        target = check / 'bootable/recovery' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(subprocess.check_output(['git', '-C', str(repo), 'show', 'HEAD:' + name]))
    subprocess.run([sys.executable, str(tree / 'recovery-patches/apply.py'), str(check)], check=True)
    for name in expected:
        assert (check / 'bootable/recovery' / name).read_bytes() == (repo / name).read_bytes(), name
print('PASS: all Recovery source edits reproduced from clean HEAD by the device tree')
