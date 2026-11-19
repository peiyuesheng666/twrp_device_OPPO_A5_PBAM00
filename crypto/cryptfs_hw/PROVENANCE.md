# Qualcomm hardware encryption support

`cryptfs_hw.c`, `cryptfs_hw.h`, and `kernel-headers/linux/qseecom.h` are copied
from the OrangeFox `vendor/qcom/opensource/commonsys` source at commit
`8650a9f80edab99a2f5081fde3222aa4184f4413` (2019-05-24). The original source
licenses and notices are retained in each source file where supplied. The
module makefile is specific to this device tree and exports the bundled QSEE
ioctl header to the Android 9 recovery build.

SHA-256:

```text
4dea2dd0c815f0f703bf59b589323ce1fa18c0a1b3f9ae0fe4ab5d50f5b7df52  cryptfs_hw.c
c11451d14aa406ebc7adcc5af881722a94363f54d9a59b1a6e2605a7e71076dc  cryptfs_hw.h
f92594cc2c97d484a3f8c0307272b3be5e24d631135080f06a3b02a903344d81  kernel-headers/linux/qseecom.h
```
