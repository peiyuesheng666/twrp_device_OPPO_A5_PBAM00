#!/usr/bin/env python3
"""Apply narrowly gated PBAM00 changes to the fox_9.0 FDE client."""
from pathlib import Path
import sys

source = Path(sys.argv[1])
fde = source / 'bootable/recovery/crypto/fde'

def replace_once(path, old, new, marker):
    text = path.read_text()
    if marker in text:
        return
    if text.count(old) != 1:
        raise SystemExit(f'Unsupported recovery revision, expected one anchor: {path}')
    path.write_text(text.replace(old, new))

mk = fde / 'Android.mk'
text = mk.read_text()
marker = '# PBAM00 stock default-password adapter'
block = '''# PBAM00 stock default-password adapter
ifneq ($(TW_CRYPTO_OPPO_DEFAULT_PASSWORD_PATH),)
    LOCAL_C_INCLUDES += $(TW_CRYPTO_OPPO_DEFAULT_PASSWORD_PATH)
    LOCAL_CFLAGS += -DTW_CRYPTO_OPPO_DEFAULT_PASSWORD
endif
'''
# Keep our include after the module's := assignment, which replaces prior paths.
if marker in text:
    text = text.replace(block, '')
if marker not in text:
    anchor = 'LOCAL_C_INCLUDES := '
    lines = text.splitlines(keepends=True)
    count = 0
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith(anchor):
            lines.insert(i + 1, block)
            count += 1
    if count != 2:
        raise SystemExit('Unexpected FDE module layout')
    updated = ''.join(lines)
    if updated != mk.read_text():
        mk.write_text(updated)

cpp = fde / 'cryptfs.cpp'
replace_once(cpp,
    '#define DEFAULT_PASSWORD "default_password"',
    '''#ifdef TW_CRYPTO_OPPO_DEFAULT_PASSWORD
#include "oppo_default_password.h"
#define DEFAULT_PASSWORD oppo_fde_default_password()
#else
#define DEFAULT_PASSWORD "default_password"
#endif''',
    '#include "oppo_default_password.h"')

replace_once(cpp,
    '    key_index = verify_hw_fde_passwd(passwd, crypt_ftr);\n    if (key_index < 0) {',
    '''    key_index = verify_hw_fde_passwd(passwd, crypt_ftr);
#ifdef TW_CRYPTO_OPPO_DEFAULT_PASSWORD
    // PBAM00 shipped with Oreo. Do not run the Lollipop password-migration
    // fallback or update a TEE key while opening existing user data.
    return key_index;
#endif
    if (key_index < 0) {''',
    '// PBAM00 shipped with Oreo.')

replace_once(cpp,
    '''#ifdef CONFIG_HW_DISK_ENCRYPTION
    if (is_hw_disk_encryption((char*)crypt_ftr.crypto_type_name))
        return cryptfs_check_passwd_hw(passwd);''',
    '''#ifdef TW_CRYPTO_OPPO_DEFAULT_PASSWORD
    // PartitionManager sends the AOSP marker for a password-free FDE volume.
    // Resolve it inside the crypto process; do not send an OEM secret via CLI.
    if (crypt_ftr.crypt_type == CRYPT_TYPE_DEFAULT &&
        (!passwd || !*passwd || !strcmp(passwd, "default_password"))) {
        passwd = DEFAULT_PASSWORD;
        if (!*passwd) {
            SLOGE("OPPO default-password generation needs the device serial\\n");
            return -1;
        }
        SLOGI("Using PBAM00 stock default-password algorithm\\n");
    }
#endif
#ifdef CONFIG_HW_DISK_ENCRYPTION
    if (is_hw_disk_encryption((char*)crypt_ftr.crypto_type_name))
        return cryptfs_check_passwd_hw(passwd);''',
    '// PartitionManager sends the AOSP marker')
print('PBAM00 FDE adapter applied (device flag gated)')
