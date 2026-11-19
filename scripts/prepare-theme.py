#!/usr/bin/env python3
"""Recreate the packed avatar using only files already inside this tree."""
from pathlib import Path
import hashlib
import json
from PIL import Image

tree = Path(__file__).resolve().parents[1]
report = json.loads((tree / 'assets/maintainer-provenance.json').read_text())
original = tree / 'assets/maintainer-original.png'
assert hashlib.sha256(original.read_bytes()).hexdigest() == report['original_sha256']
dest = tree / 'recovery/root' / report['packed_path']
dest.parent.mkdir(parents=True, exist_ok=True)
with Image.open(original) as picture:
    picture.convert('RGBA').resize(tuple(report['packed_size']),
        getattr(Image, 'Resampling', Image).LANCZOS).save(dest)
assert hashlib.sha256(dest.read_bytes()).hexdigest() == report['packed_sha256']
print('Maintainer avatar regenerated and verified')
