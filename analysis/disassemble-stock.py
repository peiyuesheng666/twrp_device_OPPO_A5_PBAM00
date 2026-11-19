#!/usr/bin/env python3
"""Annotate selected original ARM64 ELF functions; never connects to a device."""
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
    assert data[:6] == b'\x7fELF\x02\x01', 'Expected little-endian ELF64'
    off = struct.unpack_from('<Q', data, 40)[0]
    size, count, names_index = struct.unpack_from('<HHH', data, 58)
    headers = [struct.unpack_from('<IIQQQQIIQQ', data, off + i * size) for i in range(count)]
    h = headers[names_index]
    names = data[h[4]:h[4] + h[5]]
    return [dict(name=names[h[0]:].split(b'\0', 1)[0].decode(), type=h[1], flags=h[2],
                 addr=h[3], offset=h[4], size=h[5], link=h[6], entsize=h[9]) for h in headers]


def symbols(data, ss):
    result = []
    for s in ss:
        if s['type'] not in (2, 11):
            continue
        h = ss[s['link']]
        names = data[h['offset']:h['offset'] + h['size']]
        table = []
        for pos in range(s['offset'], s['offset'] + s['size'], s['entsize'] or 24):
            name, info, other, index, value, size = struct.unpack_from('<IBBHQQ', data, pos)
            table.append(dict(name=names[name:].split(b'\0', 1)[0].decode(errors='replace'),
                              value=value, size=size, type=info & 15))
        result.append((s['name'], table))
    return dict(result)


path, output, *patterns = sys.argv[1:]
data = Path(path).read_bytes()
ss = sections(data)
tables = symbols(data, ss)
mini = next((s for s in ss if s['name'] == '.gnu_debugdata'), None)
if mini:
    debug = lzma.decompress(data[mini['offset']:mini['offset'] + mini['size']])
    tables.update(symbols(debug, sections(debug)))
funcs = {s['value']: s for table in tables.values() for s in table if s['type'] == 2 and s['value']}
plt = next((s for s in ss if s['name'] == '.plt'), None)
rel = next((s for s in ss if s['name'] == '.rela.plt'), None)
if plt and rel:
    dyn = tables['.dynsym']
    for i, pos in enumerate(range(rel['offset'], rel['offset'] + rel['size'], rel['entsize'] or 24)):
        _, info, _ = struct.unpack_from('<QQq', data, pos)
        address = plt['addr'] + 32 + i * 16
        funcs[address] = dict(value=address, size=16, name=dyn[info >> 32]['name'] + '@plt')
starts = sorted(funcs)


def string_at(address):
    for s in ss:
        if s['type'] != 8 and s['flags'] & 2 and not s['flags'] & 4 and s['addr'] <= address < s['addr'] + s['size']:
            off = s['offset'] + address - s['addr']
            b = data[off:off + 240].split(b'\0', 1)[0]
            if len(b) >= 3 and all(x in (9, 10, 13) or 32 <= x < 127 for x in b):
                return b.decode()


md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
md.detail = True
lines = [f'Input: {path}', f'SHA256: {hashlib.sha256(data).hexdigest()}',
         'Addresses are ELF virtual addresses. String tracking is local and heuristic.', '']
selected = [f for f in funcs.values() if any(p in f['name'] for p in patterns)]
for f in sorted(selected, key=lambda f: f['value']):
    address = f['value']
    i = bisect.bisect_right(starts, address)
    size = f['size'] or ((starts[i] - address) if i < len(starts) else 512)
    section = next((s for s in ss if s['flags'] & 4 and s['addr'] <= address < s['addr'] + s['size']), None)
    if section is None:
        continue
    off = section['offset'] + address - section['addr']
    lines.append(f"\nFUNCTION 0x{address:x} size={size} {f['name']}")
    registers = {}
    for insn in md.disasm(data[off:off + size], address):
        ops = insn.operands
        comments = []
        target = None
        if insn.mnemonic in ('adrp', 'adr') and len(ops) == 2 and ops[1].type == ARM64_OP_IMM:
            registers[ops[0].reg] = (ops[1].imm, insn.address)
            if insn.mnemonic == 'adr':
                target = ops[1].imm
        elif insn.mnemonic == 'add' and len(ops) == 3 and ops[1].type == ARM64_OP_REG and ops[2].type == ARM64_OP_IMM:
            base = registers.get(ops[1].reg)
            if base and insn.address - base[1] <= 64:
                target = base[0] + ops[2].imm
                registers[ops[0].reg] = (target, insn.address)
        if target is not None:
            value = string_at(target)
            if value:
                comments.append(f'0x{target:x} ' + json.dumps(value))
        if insn.mnemonic in ('b', 'bl') and ops and ops[0].type == ARM64_OP_IMM:
            if ops[0].imm in funcs:
                comments.append(funcs[ops[0].imm]['name'])
        line = f'  {insn.address:08x}: {insn.bytes.hex():8s}  {insn.mnemonic:8s} {insn.op_str}'
        if comments:
            line += '  ; ' + ' | '.join(comments)
        lines.append(line)
        if insn.mnemonic == 'bl':
            for r in list(registers):
                name = insn.reg_name(r)
                if name.startswith('x') and name[1:].isdigit() and int(name[1:]) <= 18:
                    del registers[r]
Path(output).write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(json.dumps(dict(output=output, functions=len(selected), lines=len(lines))))
