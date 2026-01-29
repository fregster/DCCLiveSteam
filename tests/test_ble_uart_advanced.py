"""
BLE/telemetry disconnect and malformed packet tests.
Covers BLE disconnects, malformed packets, and buffer overflow edge cases.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.ble_uart import BLE_UART

def test_ble_disconnect_during_send():
    """
    Tests BLE send() handles disconnect during transmission.
    """
    with patch('app.ble_uart.bluetooth.BLE') as mock_ble, \
         patch('app.ble_advertising._ADV_TYPE_FLAGS', 0x01), \
         patch('app.ble_advertising._ADV_TYPE_NAME', 0x09), \
         patch('app.ble_advertising._ADV_TYPE_UUID16_COMPLETE', 0x03), \
         patch('app.ble_advertising._ADV_TYPE_UUID32_COMPLETE', 0x05), \
         patch('app.ble_advertising._ADV_TYPE_UUID128_COMPLETE', 0x07), \
         patch('app.ble_advertising._ADV_TYPE_APPEARANCE', 0x19):
        ble_instance = MagicMock()
        # Mock .gatts_register_services to return two handles
        ble_instance.gatts_register_services.return_value = [(1, 2)]
        mock_ble.return_value = ble_instance
        ble = BLE_UART()
        ble._connected = True
        ble_instance.gatts_notify.side_effect = OSError("disconnect")
        # Should not raise
        ble.send(b"data")

def test_ble_malformed_packet():
    """
    Tests BLE RX handler with malformed (non-UTF8) packet.
    """
    with patch('app.ble_uart.bluetooth.BLE') as mock_ble, \
         patch('app.ble_advertising._ADV_TYPE_FLAGS', 0x01), \
         patch('app.ble_advertising._ADV_TYPE_NAME', 0x09), \
         patch('app.ble_advertising._ADV_TYPE_UUID16_COMPLETE', 0x03), \
         patch('app.ble_advertising._ADV_TYPE_UUID32_COMPLETE', 0x05), \
         patch('app.ble_advertising._ADV_TYPE_UUID128_COMPLETE', 0x07), \
         patch('app.ble_advertising._ADV_TYPE_APPEARANCE', 0x19):
        ble_instance = MagicMock()
        ble_instance.gatts_register_services.return_value = [(1, 2)]
        mock_ble.return_value = ble_instance
        ble = BLE_UART()
        ble._ble.gatts_read.return_value = b'\xff\xfe\xfd\n'  # Invalid UTF-8
        ble._on_rx()
        assert len(ble.rx_queue) == 0

def test_ble_rx_buffer_overflow():
    """
    Tests BLE RX buffer overflow protection (over 128 bytes).
    """
    with patch('app.ble_uart.bluetooth.BLE') as mock_ble, \
         patch('app.ble_advertising._ADV_TYPE_FLAGS', 0x01), \
         patch('app.ble_advertising._ADV_TYPE_NAME', 0x09), \
         patch('app.ble_advertising._ADV_TYPE_UUID16_COMPLETE', 0x03), \
         patch('app.ble_advertising._ADV_TYPE_UUID32_COMPLETE', 0x05), \
         patch('app.ble_advertising._ADV_TYPE_UUID128_COMPLETE', 0x07), \
         patch('app.ble_advertising._ADV_TYPE_APPEARANCE', 0x19):
        ble_instance = MagicMock()
        ble_instance.gatts_register_services.return_value = [(1, 2)]
        mock_ble.return_value = ble_instance
        ble = BLE_UART()
        large_data = b'X' * 150
        ble._ble.gatts_read.return_value = large_data
        ble._on_rx()
        assert len(ble._rx_buffer) == 128
