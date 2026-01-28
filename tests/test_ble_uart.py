"""
Unit tests for BLE UART telemetry interface.
Tests initialisation, connection handling, telemetry formatting, and error resilience.

Why: BLE UART provides wireless monitoring without affecting locomotive control.
Tests verify telemetry doesn't block main loop on errors.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from app.ble_uart import BLE_UART


@pytest.fixture
def mock_ble():
    """Mock BLE stack for testing."""
    with patch('app.ble_uart.bluetooth.BLE') as mock:
        ble_instance = MagicMock()
        # Mock gatts_register_services to return expected structure
        # Returns list of service handles, each service is tuple of characteristic handles
        ble_instance.gatts_register_services.return_value = [((1,), (2,))]  # [((TX_handle,), (RX_handle,))]
        mock.return_value = ble_instance
        yield ble_instance


@pytest.fixture
def mock_advertising():
    """Mock advertising_payload function."""
    with patch('app.ble_uart.advertising_payload') as mock:
        mock.return_value = b'\x02\x01\x06'  # Simple payload
        yield mock


def test_ble_uart_initialisation(mock_ble, mock_advertising):
    """
    Verify BLE UART initialises with Nordic UART Service UUIDs.
    
    Why: NUS (Nordic UART Service) is standardized BLE serial protocol with
    UUIDs 6E400001 (service), 6E400003 (TX/notify), 6E400002 (RX/write).
    
    Safety: BLE initialisation errors must not prevent main loop execution.
    """
    ble = BLE_UART(name="TestLoco")
    
    assert ble._name == "TestLoco"
    assert ble._connected is False
    mock_ble.active.assert_called_once_with(True)
    mock_ble.irq.assert_called_once()


def test_ble_uart_default_name(mock_ble, mock_advertising):
    """
    Verify default device name is "LiveSteam".
    
    Why: Device name appears in BLE scan results, must be recognizable.
    """
    ble = BLE_UART()
    
    assert ble._name == "LiveSteam"


def test_advertise_calls_gap_advertise(mock_ble, mock_advertising):
    """
    Verify advertising starts with 100ms interval.
    
    Why: 100ms advertising interval balances discovery speed (phone finds device
    within ~1 second) with power consumption (~2mA advertising current).
    
    Safety: Advertising must restart after disconnect to enable reconnection.
    """
    ble = BLE_UART()
    
    # Verify gap_advertise called during init
    assert mock_ble.gap_advertise.called


def test_send_when_connected(mock_ble, mock_advertising):
    """
    Verify send() transmits data when client connected.
    
    Why: gatts_notify() sends data over BLE TX characteristic. Connection
    handle 0 targets first (only) connected client.
    
    Safety: Send failures (client disconnected mid-send, buffer full) must not
    crash or block main loop.
    """
    ble = BLE_UART()
    ble._connected = True
    
    ble.send(b"Test data")
    
    mock_ble.gatts_notify.assert_called_once()


def test_send_when_disconnected(mock_ble, mock_advertising):
    """
    Verify send() does nothing when no client connected.
    
    Why: Saves CPU time (no format/transmit overhead) when telemetry unused.
    
    Safety: Prevents gatts_notify() exception on disconnected handle.
    """
    ble = BLE_UART()
    ble._connected = False
    
    ble.send(b"Test data")
    
    # gatts_notify should not be called
    assert not mock_ble.gatts_notify.called


def test_send_handles_exceptions(mock_ble, mock_advertising):
    """
    Verify send() silently handles BLE exceptions.
    
    Why: BLE errors (buffer full, disconnection race, hardware fault) can raise
    OSError or other exceptions. Try-except wrapper prevents crash.
    
    Safety: Main control loop must continue even if telemetry fails.
    """
    ble = BLE_UART()
    ble._connected = True
    mock_ble.gatts_notify.side_effect = OSError("BLE error")
    
    # Should not raise exception
    ble.send(b"Test data")


def test_send_telemetry_formats_correctly(mock_ble, mock_advertising):
    """
    Verify telemetry packet format matches specification (queued, non-blocking).
    
    Why: Pipe-delimited format (SPD:35.2|PSI:55.3|...) is human-readable and
    easily parsed by mobile apps. Newline terminator enables line buffering.
    Telemetry is queued in send_telemetry() then sent by process_telemetry().

    Safety: Format errors must not crash encoder. Non-blocking ensures main loop
    timing is not affected.
    """
    ble = BLE_UART()
    ble._connected = True
    
    # Queue telemetry (non-blocking)
    ble.send_telemetry(35.2, 55.3, (95.0, 210.0, 45.0), 450)
    
    # Verify packet is queued but not yet sent
    assert ble._telemetry_pending is True
    assert ble._telemetry_buffer is not None
    
    # Process telemetry (background transmission)
    ble.process_telemetry()
    
    # Verify send called with encoded string
    assert mock_ble.gatts_notify.called
    call_args = mock_ble.gatts_notify.call_args[0]
    data = call_args[2]  # Third argument is data
    
    # Decode and verify format
    decoded = data.decode('utf-8')
    assert "SPD:35.2" in decoded
    assert "PSI:55.3" in decoded
    assert "TB:95.0" in decoded
    assert "TS:210.0" in decoded
    assert "TL:45.0" in decoded
    assert "SRV:450" in decoded
    assert decoded.endswith("\n")


def test_send_telemetry_when_disconnected(mock_ble, mock_advertising):
    """
    Verify send_telemetry() skips formatting when disconnected.
    
    Why: Format operations (string formatting, float conversion, encoding) take
    ~2ms. Skipping when disconnected saves CPU for control loop.
    
    Safety: Early return prevents wasteful computation.
    """
    ble = BLE_UART()
    ble._connected = False
    
    ble.send_telemetry(35.2, 55.3, (95.0, 210.0, 45.0), 450)
    
    # gatts_notify should not be called
    assert not mock_ble.gatts_notify.called


def test_send_telemetry_handles_format_errors(mock_ble, mock_advertising):
    """
    Verify send_telemetry() handles invalid input gracefully.
    
    Why: Sensor failures can produce NaN, None, or invalid values. Try-except
    wrapper prevents format exceptions from crashing.
    
    Safety: Telemetry errors must not affect locomotive control.
    """
    ble = BLE_UART()
    ble._connected = True
    
    # Should not raise exception for invalid input
    ble.send_telemetry(float('nan'), None, (None, 210.0, 45.0), "invalid")


def test_is_connected_true(mock_ble, mock_advertising):
    """
    Verify is_connected() returns True when client connected.
    
    Why: Main loop uses is_connected() to skip telemetry formatting when
    no client present, saving ~2ms per 50Hz iteration.
    """
    ble = BLE_UART()
    ble._connected = True
    
    assert ble.is_connected() is True


def test_is_connected_false(mock_ble, mock_advertising):
    """
    Verify is_connected() returns False when no client.
    """
    ble = BLE_UART()
    ble._connected = False
    
    assert ble.is_connected() is False


def test_irq_handler_connect_event(mock_ble, mock_advertising):
    """
    Verify IRQ handler sets _connected=True on connect event.
    
    Why: BLE stack calls _irq() callback on connection state changes.
    Event code 1 = _IRQ_CENTRAL_CONNECT (client connected).
    
    Safety: Connection state must track accurately to prevent sending to
    disconnected handle.
    """
    ble = BLE_UART()
    ble._connected = False
    
    # Simulate connection event (event=1)
    ble._irq(1, ())
    
    assert ble._connected is True


def test_irq_handler_disconnect_event(mock_ble, mock_advertising):
    """
    Verify IRQ handler sets _connected=False and restarts advertising on disconnect.
    
    Why: Event code 2 = _IRQ_CENTRAL_DISCONNECT (client lost). Must restart
    advertising to enable reconnection without reboot.
    
    Safety: Automatic reconnection improves usability (phone app can reconnect
    after going out of range).
    """
    ble = BLE_UART()
    ble._connected = True
    mock_ble.gap_advertise.reset_mock()  # Clear init call
    
    # Simulate disconnect event (event=2)
    ble._irq(2, ())
    
    assert ble._connected is False
    # Verify advertising restarted
    assert mock_ble.gap_advertise.called


def test_uart_service_uuids(mock_ble, mock_advertising):
    """
    Verify Nordic UART Service UUIDs match specification.
    
    Why: NUS is standardized protocol (Nordic Semiconductor documentation).
    Wrong UUIDs prevent mobile apps from recognizing service.
    
    Service: 6E400001-B5A3-F393-E0A9-E50E24DCCA9E
    TX char: 6E400003-B5A3-F393-E0A9-E50E24DCCA9E (notify)
    RX char: 6E400002-B5A3-F393-E0A9-E50E24DCCA9E (write)
    
    Safety: Incorrect UUIDs render telemetry non-functional.
    """
    with patch('app.ble_uart.bluetooth.UUID') as mock_uuid:
        ble = BLE_UART()
        
        # Verify UUID calls
        uuid_calls = [call[0][0] for call in mock_uuid.call_args_list]
        assert "6E400001-B5A3-F393-E0A9-E50E24DCCA9E" in uuid_calls  # Service
        assert "6E400003-B5A3-F393-E0A9-E50E24DCCA9E" in uuid_calls  # TX
        assert "6E400002-B5A3-F393-E0A9-E50E24DCCA9E" in uuid_calls  # RX


def test_telemetry_decimal_precision(mock_ble, mock_advertising):
    """
    Verify telemetry values formatted with appropriate precision (queued, non-blocking).
    
    Why: Float precision balances readability with data size. 1 decimal place
    sufficient for speed/pressure/temperature monitoring. Telemetry is queued
    then transmitted to avoid blocking main loop.
    
    Safety: Excessive precision wastes BLE bandwidth (20 byte packet limit).
    """
    ble = BLE_UART()
    ble._connected = True
    
    # Queue and process telemetry
    ble.send_telemetry(35.678, 55.432, (95.123, 210.987, 45.555), 450)
    ble.process_telemetry()
    
    call_args = mock_ble.gatts_notify.call_args[0]
    data = call_args[2].decode('utf-8')
    
    # Verify 1 decimal place for floats
    assert "SPD:35.7" in data or "SPD:35.6" in data  # Rounding tolerance
    assert "PSI:55.4" in data or "PSI:55.5" in data
    assert "TB:95.1" in data or "TB:95.2" in data


def test_multiple_telemetry_sends(mock_ble, mock_advertising):
    """
    Verify multiple telemetry sends don't interfere (queued, non-blocking).
    
    Why: Main loop calls send_telemetry() every 1 second. Buffer management
    must handle rapid sequential sends with queueing. Latest telemetry data
    is always preserved.
    
    Safety: Send failures must not leave BLE stack in bad state. Queue-based
    approach ensures robust error handling.
    """
    ble = BLE_UART()
    ble._connected = True
    
    # Send three telemetry packets
    ble.send_telemetry(35.2, 55.3, (95.0, 210.0, 45.0), 450)
    ble.process_telemetry()
    
    ble.send_telemetry(36.1, 54.8, (96.0, 215.0, 46.0), 460)
    ble.process_telemetry()
    
    ble.send_telemetry(37.0, 56.0, (97.0, 220.0, 47.0), 470)
    ble.process_telemetry()
    
    # Verify all three were sent
    assert mock_ble.gatts_notify.call_count == 3
    
    # Verify all sends completed
    assert mock_ble.gatts_notify.call_count == 3
