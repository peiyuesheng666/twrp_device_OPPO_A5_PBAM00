#!/usr/bin/env python3
"""Summarize saved Sahara/Firehose tests without contacting a phone."""
from pathlib import Path
import json
import re

root = Path(__file__).resolve().parent
results = []
for directory in sorted((root / 'edl-tests').iterdir()):
    if not (directory / 'result.json').is_file():
        continue
    saved = json.loads((directory / 'result.json').read_text())
    log = (directory / 'sahara.log').read_text(errors='replace')
    nop = (directory / 'firehose-nop.bin').read_bytes() if (directory / 'firehose-nop.bin').exists() else b''
    modes = re.findall(r'sahara_hello->mode\s*=\s*(\d+)', log)
    sent = re.findall(r'(\d+) bytes transferred in ([0-9.]+) seconds', log)
    results.append(dict(directory=directory.name, entry=saved['entry'],
                        date=saved['date'], programmer_sha256=saved['programmer_sha256'],
                        programmer_file_bytes=saved['programmer_bytes'],
                        sahara_hello_mode=int(modes[0]) if modes else None,
                        sahara_transferred_bytes=int(sent[-1][0]) if sent else None,
                        sahara_success=saved['sahara_success'],
                        firehose_nop_ack=bool(re.search(rb'<response\b[^>]*value="ACK"', nop)),
                        seconds_to_enumeration=saved['seconds_to_enumeration'],
                        partition_reads=saved['partition_reads'],
                        partition_writes=saved['partition_writes']))
report = dict(tests=results,
              same_programmer=len({r['programmer_sha256'] for r in results}) == 1,
              all_handshakes_passed=all(r['sahara_success'] and r['firehose_nop_ack'] for r in results),
              partition_io_performed=any(r['partition_reads'] or r['partition_writes'] for r in results),
              user_reported_failure_reproduced=False,
              actual_flashing_test=False,
              warning='The fox-menu test invoked the same GUI exit/reboot backend through in-memory variables; it was not a physical screen tap.')
(root / 'edl-tests-summary.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
