# Standard MicroPython BLE advertising helper
from micropython import const
import struct

# Advertising constants
_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID16_COMPLETE = const(0x03)
_ADV_TYPE_UUID32_COMPLETE = const(0x05)
_ADV_TYPE_UUID128_COMPLETE = const(0x07)
_ADV_TYPE_APPEARANCE = const(0x19)

def advertising_payload(limited_disc=False, br_edr=False, name=None, services=None, appearance=0):
    """Generates the byte payload for BLE advertising."""
    payload = bytearray()

    def _append(adv_type, value):
        nonlocal payload
        payload.append(len(value) + 1)
        payload.append(adv_type)
        payload.extend(value)

    def _append_service_uuid(uuid):
        """Appends a service UUID based on its length."""
        b = bytes(uuid)
        if len(b) == 2:
            _append(_ADV_TYPE_UUID16_COMPLETE, b)
        elif len(b) == 4:
            _append(_ADV_TYPE_UUID32_COMPLETE, b)
        elif len(b) == 16:
            _append(_ADV_TYPE_UUID128_COMPLETE, b)

    # Flags: General discovery mode + No BR/EDR (BLE only)
    _append(_ADV_TYPE_FLAGS, struct.pack("B", (0x01 if limited_disc else 0x02) + (0x10 if br_edr else 0x04)))

    # Device Name
    if name:
        _append(_ADV_TYPE_NAME, name)

    # Services (UUIDs)
    if services:
        for uuid in services:
            _append_service_uuid(uuid)

    # Appearance (e.g., Generic Sensor)
    if appearance:
        _append(_ADV_TYPE_APPEARANCE, struct.pack("<H", appearance))

    return payload
