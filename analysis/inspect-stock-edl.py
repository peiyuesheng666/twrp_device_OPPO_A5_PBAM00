#!/usr/bin/env python3
"""Find ARM64 references to reboot-related strings in an original stock ELF.

Usage: python3 inspect-stock-edl.py original-elf report.json
Requires Capstone. Reads an existing firmware file only; never contacts a phone.
"""
from pathlib import Path
import bisect
import hashlib
import json
import lzma
import re
import struct
import sys
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from capstone.arm64 import ARM64_OP_IMM, ARM64_OP_REG

def sections(data):
    assert data[:5] == b'\x7fELF\x02' and data[5] == 1
    off = struct.unpack_from('<Q', data, 40)[0]
    entsize, count, names_index = struct.unpack_from('<HHH', data, 58)
    headers = [struct.unpack_from('<IIQQQQIIQQ', data, off + i * entsize) for i in range(count)]
    name_header = headers[names_index]
    names = data[name_header[4]:name_header[4] + name_header[5]]
    result = []
    for header in headers:
        name = names[header[0]:].split(b'\0', 1)[0].decode()
        result.append(dict(name=name, type=header[1], flags=header[2], addr=header[3],
                           offset=header[4], size=header[5], link=header[6], entsize=header[9]))
    return result

def functions(data):
    ss = sections(data)
    mini = next((s for s in ss if s['name'] == '.gnu_debugdata'), None)
    if mini:
        data = lzma.decompress(data[mini['offset']:mini['offset'] + mini['size']])
        ss = sections(data)
    result = {}
    for section in ss:
        if section['type'] not in (2, 11):
            continue
        names_header = ss[section['link']]
        names = data[names_header['offset']:names_header['offset'] + names_header['size']]
        for offset in range(section['offset'], section['offset'] + section['size'], section['entsize'] or 24):
            name, info, other, index, value, size = struct.unpack_from('<IBBHQQ', data, offset)
            if info & 15 == 2 and value:
                result[value] = names[name:].split(b'\0', 1)[0].decode(errors='replace')
    return result

path = Path(sys.argv[1])
data = path.read_bytes()
ss = sections(data)
funcs = functions(data)
starts = sorted(funcs)
strings = {}
pattern = re.compile(r'edl|dload|powerctl|reboot|warm.?reset|download.mode', re.I)
for section in ss:
    if not section['flags'] & 2 or section['flags'] & 4 or section['type'] == 8:
        continue
    blob = data[section['offset']:section['offset'] + section['size']]
    for match in re.finditer(rb'[\x20-\x7e]{3,}\x00', blob):
        value = match.group()[:-1].decode()
        if pattern.search(value):
            strings[section['addr'] + match.start()] = value

md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
md.detail = True
refs = []
for section in ss:
    if not section['flags'] & 4:
        continue
    registers = {}
    blob = data[section['offset']:section['offset'] + section['size']]
    for insn in md.disasm(blob, section['addr']):
        ops = insn.operands
        target = None
        if insn.mnemonic in ('adrp', 'adr') and len(ops) == 2 and ops[0].type == ARM64_OP_REG and ops[1].type == ARM64_OP_IMM:
            registers[ops[0].reg] = (ops[1].imm, insn.address)
            if insn.mnemonic == 'adr':
                target = ops[1].imm
        elif insn.mnemonic == 'add' and len(ops) == 3 and ops[0].type == ARM64_OP_REG and ops[1].type == ARM64_OP_REG and ops[2].type == ARM64_OP_IMM:
            base = registers.get(ops[1].reg)
            if base and insn.address - base[1] <= 48:
                target = base[0] + ops[2].imm
                registers[ops[0].reg] = (target, insn.address)
        elif insn.mnemonic == 'ret':
            registers.clear()
        if target in strings:
            i = bisect.bisect_right(starts, insn.address) - 1
            start = starts[i] if i >= 0 else 0
            refs.append(dict(address=hex(insn.address), instruction=f'{insn.mnemonic} {insn.op_str}',
                             string_address=hex(target), string=strings[target],
                             function_address=hex(start), function=funcs.get(start, '?')))

report = dict(file=path.name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
              strings={hex(k): v for k, v in strings.items()}, references=refs,
              debug_function_count=len(funcs))
Path(sys.argv[2]).write_text(json.dumps(report, indent=2) + '\n')
for ref in refs:
    if 'edl' in ref['string'].lower() or 'powerctl' in ref['string'].lower() or 'dload' in ref['string'].lower():
        print(json.dumps(ref))
print(f'Saved {len(refs)} reboot-related references, {len(funcs)} function symbols')
