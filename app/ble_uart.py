"""
BLE UART telemetry interface using Nordic UART Service (NUS).
Provides wireless monitoring of locomotive status via Bluetooth Low Energy.

Why: Real-time telemetry enables remote monitoring of boiler pressure, temperatures,
and speed without physical connection. Nordic UART Service is widely supported by
mobile apps (nRF Connect, Serial Bluetooth Terminal). Non-blocking telemetry buffer
prevents BLE operations from blocking the 50Hz main control loop.
"""
from typing import Tuple, Optional
import bluetooth
from .ble_advertising import advertising_payload

class BLE_UART:
    """BLE UART interface for wireless telemetry streaming.

    Why: Nordic UART Service (NUS) provides serial-like communication over BLE.
    Standardized UUIDs (6E400001-...) ensure compatibility with mobile apps.
    TX characteristic (notify) sends data to phone, RX (write) receives commands.

    Safety: BLE operates independently of locomotive control. Connection loss does
    not affect operation. Telemetry send failures are silently ignored to prevent
    blocking main control loop.

    Example:
        >>> ble = BLE_UART(name="LiveSteam")
        >>> ble.send_telemetry(35.2, 55.3, (95.0, 210.0, 45.0), 450)
    """
    def __init__(self, name: str = "LiveSteam") -> None:
        """Initialise BLE stack and Nordic UART Service.

        Why: NUS requires three components: Service UUID (6E400001), TX characteristic
        (6E400003, notify), RX characteristic (6E400002, write). GATT registration
        must complete before advertising starts.

        Args:
            name: BLE device name visible in scan results (default "LiveSteam")

        Safety: BLE active() must be called before irq() to prevent nil pointer.
        GATT handles (_handle_tx, _handle_rx) stored for gatts_notify() calls.

        Example:
            >>> ble = BLE_UART(name="MyLoco")
            >>> ble._name
            'MyLoco'
        """
        self._ble = bluetooth.BLE()
        self._ble.active(True)
        self._ble.irq(self._irq)
        self._connected = False
        self._name = name

        # Telemetry buffer for non-blocking send (prevents main loop blocking)
        self._telemetry_buffer: Optional[bytes] = None  # Queued telemetry packet
        self._telemetry_pending = False  # True if packet queued but not yet sent

        # RX buffer for receiving commands (NEW: BLE CV updates)
        self.rx_queue: list[str] = []  # Parsed commands ready for processing
        self._rx_buffer = bytearray()  # Accumulation buffer for partial commands
        self._max_rx_buffer = 128  # Maximum buffer size (safety limit)
        self._max_rx_queue = 16  # Maximum queued commands (safety limit)

        # Standard Nordic UART Service (NUS) UUIDs
        self._uart_uuid = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
        TX_UUID = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")
        RX_UUID = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")

        UART_SERVICE = (self._uart_uuid, ((TX_UUID, bluetooth.FLAG_NOTIFY), (RX_UUID, bluetooth.FLAG_WRITE),),)
        self._services = self._ble.gatts_register_services((UART_SERVICE,))
        self._handle_tx, self._handle_rx = self._services[0]
        self._advertise()

    def _advertise(self) -> None:
        """Start BLE advertising with device name and service UUID.

        Why: 100ms advertising interval balances discovery speed with power consumption.
        Advertising payload includes device name and service UUID to enable filtering
        in mobile apps.

        Safety: Called after disconnect to enable reconnection without reboot.

        Example:
            >>> ble._advertise()  # Start advertising
        """
        self._ble.gap_advertise(100, advertising_payload(name=self._name, services=[self._uart_uuid]))

    def send(self, data: bytes) -> None:
        """Send raw bytes over BLE UART TX characteristic.

        Why: Low-level send method for arbitrary binary data. Wrapped in try-except
        to prevent BLE errors from crashing main loop.

        Args:
            data: Raw bytes to transmit (max ~20 bytes per packet for BLE 4.2)

        Safety: Silently ignores send failures (disconnected client, buffer full).
        Does not block or raise exceptions. Connection handle 0 targets first client.

        Example:
            >>> ble.send(b"Hello\n")
        """
        if self._connected:
            try:
                self._ble.gatts_notify(0, self._handle_tx, data)
            except Exception:
                pass

    def send_telemetry(self, speed: float, psi: float, temps: Tuple[float, float, float],
                      servo_duty: int) -> None:
        """Queue telemetry packet for non-blocking background transmission.

        Why: BLE operations can block main loop. Instead of sending immediately,
        telemetry is formatted and queued. Call process_telemetry() from main loop
        to send queued packets. Prevents 1-5ms BLE blocking on 50Hz (20ms) cycle.

        Args:
            speed: Locomotive speed in cm/s from PhysicsEngine.calc_velocity()
            psi: Boiler pressure in PSI from SensorSuite.read_pressure()
            temps: (boiler_c, super_c, logic_c) tuple from SensorSuite.read_temps()
            servo_duty: Current servo PWM duty from MechanicalMapper.current

        Safety: Non-blocking. Format errors are caught and packet discarded. Does not
        affect main loop timing (returns immediately after queueing). Queued packet
        overwrites previous if not yet sent (latest data always available).

        Example:
            >>> ble.send_telemetry(35.2, 55.3, (95.0, 210.0, 45.0), 450)
            >>> # Returns immediately (queued, not sent)
            >>> ble.process_telemetry()  # Sends when called from main loop
        """
        if not self._connected:
            self._telemetry_buffer = None
            self._telemetry_pending = False
            return
        
        try:
            # Format telemetry packet (non-blocking, <1ms)
            data = (f"SPD:{speed:.1f}|PSI:{psi:.1f}|TB:{temps[0]:.1f}|"
                    f"TS:{temps[1]:.1f}|TL:{temps[2]:.1f}|SRV:{servo_duty}\n")
            # Queue for background transmission
            self._telemetry_buffer = data.encode('utf-8')
            self._telemetry_pending = True
        except Exception:
            self._telemetry_buffer = None
            self._telemetry_pending = False

    def process_telemetry(self) -> None:
        """Send queued telemetry packet to connected client (background task).

        Why: Called from main loop to transmit queued telemetry without blocking
        main control cycle. BLE operations (1-5ms) happen here instead of in
        send_telemetry(), keeping main loop predictable for real-time control.

        Safety: Non-blocking. If send fails, packet is discarded and next one queued.
        Multiple queued packets result in latest overwriting previous (acceptable
        because telemetry updates every 1 second).

        Example:
            >>> ble.send_telemetry(35.2, 55.3, (95.0, 210.0, 45.0), 450)
            >>> # Later in main loop:
            >>> ble.process_telemetry()  # Actually sends the packet
        """
        if not self._telemetry_pending or not self._telemetry_buffer:
            return
        
        try:
            self.send(self._telemetry_buffer)
            self._telemetry_pending = False
        except Exception:
            self._telemetry_pending = False
        finally:
            self._telemetry_buffer = None

    def is_connected(self) -> bool:
        """Returns True if a BLE client is connected.

        Why: Allows main loop to skip telemetry formatting when no client connected,
        saving ~2ms per 50Hz iteration.

        Returns:
            bool: True if client connected, False otherwise

        Example:
            >>> if ble.is_connected():
            ...     ble.send_telemetry(...)
        """
        return self._connected

    def _irq(self, event: int, data: Tuple) -> None:
        """Handle BLE connection events (connect/disconnect) and RX data.

        Why: BLE stack calls this IRQ handler on connection state changes and data RX.
        Event codes: 1=connect, 2=disconnect, 3=RX data available. Commands arrive
        as ASCII strings terminated with newline, possibly split across multiple events.

        Args:
            event: BLE event code (1=connect, 2=disconnect, 3=RX gatts_write)
            data: Event-specific data tuple (unused for connection events)

        Safety: Restart advertising on disconnect enables automatic reconnection.
        Connection state tracked in _connected flag for is_connected() queries.
        RX buffer limited to 128 bytes to prevent memory exhaustion.

        Example:
            >>> # Called automatically by BLE stack
            >>> ble._irq(1, ())  # Connection event
            >>> ble._connected
            True
        """
        if event == 1:  # _IRQ_CENTRAL_CONNECT
            self._connected = True
        elif event == 2:  # _IRQ_CENTRAL_DISCONNECT
            self._connected = False
            self._advertise()  # Restart advertising
        elif event == 3:  # _IRQ_GATTS_WRITE (RX data received)
            self._on_rx()

    def _on_rx(self) -> None:
        """Process incoming BLE RX data and extract complete commands.

        Why: Commands arrive as ASCII strings with \n terminator. Single RX events
        may contain partial commands, so data is accumulated in buffer until newline
        is found. Complete commands are extracted and queued for main loop processing.

        Safety: Buffer limited to 128 bytes max. If exceeded, oldest data is discarded
        to prevent memory exhaustion. Queue limited to 16 commands to prevent overflow.

        Example:
            >>> # Receives "CV32=20.0\n"
            >>> ble._on_rx()  # Extracts command, adds to rx_queue
            >>> ble.rx_queue
            ['CV32=20.0']
        """
        try:
            # Read all available data from RX characteristic
            data = self._ble.gatts_read(self._handle_rx)
            if not data:
                return

            # Append to buffer, enforce max size
            self._rx_buffer.extend(data)
            if len(self._rx_buffer) > self._max_rx_buffer:
                # Discard oldest data to stay under limit
                self._rx_buffer = self._rx_buffer[-self._max_rx_buffer:]

            # Extract complete commands (terminated by \n)
            while b'\n' in self._rx_buffer:
                newline_index = self._rx_buffer.index(b'\n')
                command_bytes = self._rx_buffer[:newline_index]
                self._rx_buffer = self._rx_buffer[newline_index + 1:]  # Remove processed

                # Decode and queue command
                try:
                    command_str = command_bytes.decode('utf-8').strip()
                    if command_str and len(self.rx_queue) < self._max_rx_queue:
                        self.rx_queue.append(command_str)
                except (UnicodeDecodeError, AttributeError):
                    pass  # Invalid UTF-8, discard

        except Exception:
            pass  # Silently ignore RX errors (don't crash main loop)
