# SPDX-License-Identifier: Apache-2.0
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)
$(call inherit-product-if-exists, $(SRC_TARGET_DIR)/product/embedded.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base_telephony.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/languages_full.mk)
$(call inherit-product, device/oppo/PBAM00/device.mk)
$(call inherit-product, vendor/omni/config/common.mk)
$(call inherit-product, vendor/omni/config/gsm.mk)
PRODUCT_DEVICE := PBAM00
PRODUCT_NAME := omni_PBAM00
PRODUCT_BRAND := OPPO
PRODUCT_MODEL := PBAM00
PRODUCT_MANUFACTURER := OPPO
PRODUCT_RELEASE_NAME := OPPO A5
PRODUCT_LOCALES := zh_CN en_US
