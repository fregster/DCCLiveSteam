#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/pfrye/git/DCCLiveSteam')

# Set up mocks
from tests.conftest import MockPin, MockPWM, MockADC, MockMachine, MockTime, mock_const, mock_time_module

sys.modules['machine'] = MockMachine
sys.modules['time'] = mock_time_module
sys.modules['micropython'] = type('module', (), {'const': mock_const})()
sys.modules['ubluetooth'] = type('module', (), {'BLE': lambda: None})()
sys.modules['bluetooth'] = type('module', (), {'BLE': lambda: None, 'UUID': type('MockUUID', (), {'__init__': lambda s, x: None}), 'FLAG_NOTIFY': 1, 'FLAG_WRITE': 2})()
sys.modules['gc'] = type('module', (), {'collect': lambda: None, 'mem_free': lambda: 100000})()

# Now import the app
from app.dcc_decoder import DCCDecoder

cv = {1: 3, 17: 0, 18: 0, 29: 0}
decoder = DCCDecoder(cv)

# Function Group 1 with F0=1: 0b10010001 = 0x91
decoder.bits = [0,0,0,0,0,0,1,1, 1,  # Address 3
                1,0,0,1,0,0,0,1, 1]  # Function 0x91 (F0 on)

print(f"Before decode: whistle = {decoder.whistle}")
print(f"Bits: {decoder.bits}")

# Extract bytes manually to debug
packet = []
for i in range(0, len(decoder.bits) - 1, 9):
    if i + 8 >= len(decoder.bits):
        break
    byte = 0
    for j in range(8):
        byte = (byte << 1) | decoder.bits[i + j]
    packet.append(byte)
    print(f"Byte {len(packet)-1}: {byte:08b} = 0x{byte:02X}")

if len(packet) >= 2:
    cmd_byte = packet[1]
    print(f"\nCommand byte analysis:")
    print(f"  cmd_byte = 0x{cmd_byte:02X} = {cmd_byte:08b}")
    print(f"  (cmd_byte & 0xC0) = 0x{cmd_byte & 0xC0:02X} (should be 0x80 for function, not 0x40 for speed)")
    print(f"  (cmd_byte & 0xC0) == 0x40? {(cmd_byte & 0xC0) == 0x40}")
    print(f"  (cmd_byte & 0xE0) == 0x80? {(cmd_byte & 0xE0) == 0x80}")
    print(f"  (cmd_byte & 0x10) != 0? {(cmd_byte & 0x10) != 0}")

decoder._decode_packet()
print(f"\nAfter decode: whistle = {decoder.whistle}")
