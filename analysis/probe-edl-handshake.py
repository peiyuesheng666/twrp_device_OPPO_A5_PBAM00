#!/usr/bin/env python3
"""PBAM00 EDL comparison: RAM programmer upload and Firehose NOP only.

Never reads or writes a device partition. Reboots only serial b658f72c after
checking PBAM00 and the expected Android/Recovery environment. An optional
Firehose reset restarts the phone after a successful NOP.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
import time
import serial
from serial.tools import list_ports

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--adb', required=True)
p.add_argument('--sahara-tool', required=True)
p.add_argument('--programmer', required=True)
p.add_argument('--entry', required=True, choices=['android', 'fox', 'fox-menu'])
p.add_argument('--out', required=True)
p.add_argument('--reset-after-nop', action='store_true')
a = p.parse_args()
out = Path(a.out).resolve()
out.mkdir(parents=True, exist_ok=False)
programmer = Path(a.programmer).resolve()
result = dict(date=datetime.datetime.now().astimezone().isoformat(), entry=a.entry,
              target_serial='b658f72c', programmer=str(programmer),
              programmer_sha256=hashlib.sha256(programmer.read_bytes()).hexdigest(),
              programmer_bytes=programmer.stat().st_size,
              partition_reads=False, partition_writes=False,
              sahara_success=False, firehose_nop_ack=False)


def adb(*args):
    return subprocess.check_output([a.adb, '-s', 'b658f72c', *args], timeout=12).decode(errors='replace').strip()


def exchange(port, command, seconds=5):
    received = bytearray()
    port.write(command)
    port.flush()
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        chunk = port.read(4096)
        received.extend(chunk)
        if b'</data>' in received and b'<response ' in received:
            break
    return bytes(received)


try:
    device = adb('shell', 'getprop', 'ro.product.device')
    version = adb('shell', 'getprop', 'ro.twrp.version')
    state = adb('get-state')
    result['before'] = dict(device=device, twrp_version=version, adb_state=state,
                            bootmode=adb('shell', 'getprop', 'ro.bootmode'))
    if device != 'PBAM00' or state != ('device' if a.entry == 'android' else 'recovery'):
        raise RuntimeError('Device or expected Android/Fox environment does not match')
    if any(p.vid == 0x05c6 and p.pid == 0x9008 for p in list_ports.comports()):
        raise RuntimeError('A pre-existing 9008 port would make attribution ambiguous')
    print('Target verified; rebooting the selected PBAM00 into EDL.', flush=True)
    start = time.monotonic()
    # Both paths request the same sys.powerctl target. Android adbd performs
    # the property write itself; the root Recovery shell can request it directly.
    if a.entry == 'android':
        adb('reboot', 'edl')
    elif a.entry == 'fox-menu':
        # GUIAction::reboot sets these two in-memory DataManager variables.
        # Set the argument first, then let the same main GUI exit/reboot path run.
        # No XML, settings file, partition, or source file is modified here.
        adb('shell', 'twrp', 'set', 'tw_reboot_arg', 'edl')
        adb('shell', 'twrp', 'set', 'tw_gui_done', '1')
    else:
        adb('shell', 'setprop', 'sys.powerctl', 'reboot,edl')
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        ports = [p for p in list_ports.comports() if p.vid == 0x05c6 and p.pid == 0x9008]
        if len(ports) > 1:
            raise RuntimeError('More than one Qualcomm 9008 port appeared')
        if ports:
            break
        time.sleep(.2)
    else:
        raise RuntimeError('9008 did not enumerate within 35 seconds')
    port = ports[0]
    result['port'] = port.device
    result['usb_hwid'] = port.hwid
    result['seconds_to_enumeration'] = round(time.monotonic() - start, 3)
    time.sleep(.7)
    command = [a.sahara_tool, '-p', '\\\\.\\' + port.device, '-s', '13:' + str(programmer), '-t', '5', '-v', '3']
    result['sahara_command'] = command
    print('9008 enumerated; checking Sahara programmer transfer.', flush=True)
    with (out / 'sahara.log').open('wb') as log:
        try:
            completed = subprocess.run(command, cwd=out, stdout=log, stderr=subprocess.STDOUT, timeout=25)
            result['sahara_returncode'] = completed.returncode
        except subprocess.TimeoutExpired:
            result['sahara_timeout'] = True
    log = (out / 'sahara.log').read_bytes()
    result['sahara_success'] = result.get('sahara_returncode') == 0 and b'Sahara protocol completed' in log
    if not result['sahara_success']:
        print('Sahara failed. Preserved detailed log; no Firehose command sent.', flush=True)
    else:
        print('Sahara completed; sending only a Firehose NOP.', flush=True)
        with serial.Serial(port.device, 115200, timeout=.15, write_timeout=3) as link:
            pending = link.read(link.in_waiting)
            (out / 'firehose-initial.bin').write_bytes(pending)
            response = exchange(link, b'<?xml version="1.0"?><data><nop /></data>')
            (out / 'firehose-nop.bin').write_bytes(response)
            result['firehose_nop_ack'] = bool(re.search(rb'<response\b[^>]*\bvalue="ACK"', response))
            if result['firehose_nop_ack'] and a.reset_after_nop:
                result['reset_requested'] = True
                try:
                    response = exchange(link, b'<?xml version="1.0"?><data><power value="reset" /></data>')
                    (out / 'firehose-reset.bin').write_bytes(response)
                    result['reset_exchange_completed'] = True
                except serial.SerialException as e:
                    # USB can vanish immediately after the reset request.
                    # Confirm the subsequent boot independently, never call a
                    # transport disconnect a successful Android/Recovery boot.
                    result['reset_transport_disconnected'] = str(e)
except Exception as e:
    result['error'] = str(e)
finally:
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2), flush=True)
sys.exit(0 if result['sahara_success'] and result['firehose_nop_ack'] else 1)
