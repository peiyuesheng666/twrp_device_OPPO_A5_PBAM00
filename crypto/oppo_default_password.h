/* SPDX-License-Identifier: Apache-2.0 */
#pragma once

#include <openssl/aes.h>
#include <openssl/mem.h>

// PBAM00 A.35 stock recovery: getDefString(), virtual address 0x13c1b4.
// The constant below belongs to the OEM algorithm, not to a user's data key.
// Never print the generated device-specific default password.
static const char* oppo_fde_default_password() {
    static char password[513] = {};
    if (password[0]) return password;

    char serial[256] = {};
    property_get("ro.serialno", serial, "");
    if (!serial[0]) property_get("ro.vold.serialno", serial, "");
    if (!serial[0]) return password;
    strlcat(serial, "aessecurity", sizeof(serial));
    size_t size = strlen(serial);
    const size_t padded = (size + AES_BLOCK_SIZE - 1) & ~(AES_BLOCK_SIZE - 1);
    memset(serial + size, '0', padded - size);

    static const unsigned char key[16] = {
        0x16, 0x14, 0x27, 0x63, 0x15, 0x7c, 0x11, 0xc2,
        0x49, 0xce, 0x53, 0x34, 0xb7, 0x5a, 0x18, 0x22
    };
    AES_KEY schedule;
    unsigned char encrypted[256] = {};
    if (AES_set_encrypt_key(key, 128, &schedule) != 0) {
        OPENSSL_cleanse(serial, sizeof(serial));
        return password;
    }
    for (size_t offset = 0; offset < padded; offset += AES_BLOCK_SIZE) {
        AES_ecb_encrypt(reinterpret_cast<const unsigned char*>(serial) + offset,
                        encrypted + offset, &schedule, AES_ENCRYPT);
    }
    static const char digits[] = "0123456789abcdef";
    for (size_t i = 0; i < padded; ++i) {
        password[2 * i] = digits[encrypted[i] >> 4];
        password[2 * i + 1] = digits[encrypted[i] & 15];
    }
    password[2 * padded] = '\0';
    OPENSSL_cleanse(serial, sizeof(serial));
    OPENSSL_cleanse(encrypted, sizeof(encrypted));
    OPENSSL_cleanse(&schedule, sizeof(schedule));
    return password;
}
