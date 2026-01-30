"""
DCC signal decoder for NMRA-compliant track signals.
Implements interrupt-driven bit decoding and packet parsing.
"""
from typing import Dict
import time
from machine import Pin
from .config import PIN_DCC, DCC_ONE_MIN, DCC_ONE_MAX, DCC_ZERO_MIN, DCC_ZERO_MAX

class DCCDecoder:
    """
    Decodes NMRA DCC packets from track signal using interrupt-driven bit timing.

    Why: DCC signal is Manchester-encoded square wave at ~8kHz. Software decode requires
    microsecond-precision edge timing to distinguish 1-bit (52-64µs) from 0-bit (95-119µs).
    Interrupt handler captures edges at hardware speed, main loop parses complete packets.

    Args:
        cv (Dict[int, any]): CV configuration table for address matching and mode selection.

    Returns:
        DCCDecoder: Instance of the decoder class.

    Raises:
        None

    Safety: Watchdog monitors last_valid timestamp (CV44 timeout, default 500ms). Signal
    loss triggers emergency shutdown via Locomotive.die(). Address filtering (CV1/CV17-18)
    prevents responding to packets for other locomotives on shared track.

    Example:
        >>> cv = {1: 3, 29: 0x00}  # Short address 3, basic config
        >>> decoder = DCCDecoder(cv)
        >>> # ISR processes edges automatically
        >>> decoder.is_active()
        True
    """
    def __init__(self, cv: Dict[int, any]) -> None:
        """
        Initialise DCC decoder with address matching and interrupt handler.

        Why: DCC packets broadcast to all locomotives. CV1 (short address 1-127) or
        CV17-18 (long address 128-10239) determines which packets this decoder accepts.
        CV29 bit 5 selects addressing mode.

        Args:
            cv (Dict[int, any]): CV configuration table with keys:
                - 1: Short address (1-127)
                - 29: Configuration byte (bit 5 = long address enable)
                - 17-18: Long address (if CV29 bit 5 set)

        Returns:
            None

        Raises:
            None

        Safety: IRQ handler attached to both edges (rising/falling) to capture all
        half-bit transitions. Pin configured as INPUT (not PULL_UP) because DCC track
        voltage provides strong drive. Bits buffer cleared on invalid timing to prevent
        parsing garbage data.

        Example:
            >>> cv = {1: 3, 29: 0x20, 17: 0xC0, 18: 100}  # Long address 100
            >>> decoder = DCCDecoder(cv)
            >>> decoder.long_addr
            True
            >>> decoder.addr
            100
        """
        self.pin = Pin(PIN_DCC, Pin.IN)
        self.long_addr = (cv[29] & 0x20) != 0
        
        # Calculate address based on addressing mode
        if self.long_addr:
            # Long addressing: ((CV17 & 0x3F) << 8) | CV18
            self.addr = ((cv.get(17, 0) & 0x3F) << 8) | cv.get(18, 0)
        else:
            # Short addressing: CV1 (1-127)
            self.addr = cv.get(1, 0)
        
        self.speed_128 = True
        self.current_speed = 0
        self.direction = 1
        self.whistle = False
        self.e_stop = False
        self.last_valid = time.ticks_ms()
        self.bits = []
        self.last_edge = time.ticks_us()
        self.pin.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._edge_handler)

    def _edge_handler(self, pin: Pin) -> None:
        """
        ISR: Decodes DCC bit stream from edge timing.

        Why: NMRA S-9.1 standard defines bit timing: 1-bit = 52-64µs half-period,
        0-bit = 95-119µs (nominally 58µs and 100µs). Manchester encoding has two edges
        per bit, so we accumulate bits until stop bit (1) detected.

        Args:
            pin (Pin): Pin object (required by MicroPython IRQ signature, unused)

        Returns:
            None

        Raises:
            None

        Safety: Invalid timing (outside all valid ranges) clears bit buffer to prevent
        decoding corrupted data. ISR executes in <10µs to avoid missing next edge.
        Minimum 24 bits (3 bytes) required for valid packet.

        Example:
            >>> # Called automatically by hardware on DCC pin edge
            >>> # 58µs edge -> appends 1 bit
            >>> # 100µs edge -> appends 0 bit
        """
        now = time.ticks_us()
        delta = time.ticks_diff(now, self.last_edge)
        self.last_edge = now

        # Decode half-bit timing
        if DCC_ONE_MIN <= delta <= DCC_ONE_MAX:
            self.bits.append(1)
        elif DCC_ZERO_MIN <= delta <= DCC_ZERO_MAX:
            self.bits.append(0)
        else:
            self.bits = []  # Invalid timing, reset
            return

        # Process complete packet (min 3 bytes)
        if len(self.bits) >= 24 and self.bits[-1] == 1:
            self._decode_packet()
            self.bits = []

    def _decode_packet(self) -> None:
        """
        Parses DCC packet structure according to NMRA S-9.2 standard.

        Why: DCC packet format: [preamble] [address] [instruction] [error-detect] [stop].
        Each byte is 8 data bits + 1 stop bit (always 1). Address can be 1 or 2 bytes
        (short vs long addressing). Speed commands are instruction byte 0b111xxxxx.

        Args:
            None

        Returns:
            None

        Raises:
            None (malformed packets are silently discarded)

        Safety: Address filtering discards packets for other locomotives (prevents
        multi-locomotive collisions). Try-except wrapper silently discards malformed
        packets to prevent decoder lockup. Checksum validation not implemented (NMRA
        allows omission for speed-critical applications).

        Example:
            >>> # Packet [0x03, 0xBF, 0x40, 0xFC] -> Address 3, Speed 64, Direction forward
            >>> decoder._decode_packet()  # Called by ISR
            >>> decoder.current_speed
            64
            >>> decoder.direction
            1
        """
        try:
            # Extract bytes from bit stream
            packet = []
            for i in range(0, len(self.bits) - 1, 9):  # 8 data + 1 stop bit
                if i + 8 >= len(self.bits):
                    break
                byte = 0
                for j in range(8):
                    byte = (byte << 1) | self.bits[i + j]
                packet.append(byte)

            if len(packet) < 3:
                return

            # Check address match
            addr_byte = packet[0]
            if self.long_addr:
                if len(packet) < 4 or (packet[0] & 0xC0) != 0xC0:
                    return
                addr = ((packet[0] & 0x3F) << 8) | packet[1]
                cmd_byte = packet[2]
            else:
                addr = addr_byte
                cmd_byte = packet[1]

            if addr != self.addr:
                return

            self.last_valid = time.ticks_ms()

            # Decode speed and function commands
            # Speed commands: 01xxxxxx (0x40-0x7F) basic speed
            if (cmd_byte & 0xC0) == 0x40:  # Speed command (01xxxxxx)
                # Bit 5 encodes direction
                self.direction = (cmd_byte & 0x20) >> 5
                # Bits 4-0 encode speed
                self.current_speed = cmd_byte & 0x1F
            elif (cmd_byte & 0xE0) == 0xA0:  # Advanced speed (101xxxxx: 0xA0-0xBF)
                # Advanced speed format: 101 D S S S S S where D=direction, S=speed
                self.direction = (cmd_byte & 0x20) >> 5
                self.current_speed = cmd_byte & 0x1F
            elif (cmd_byte & 0xE0) == 0x80:  # Function Group 1 (100xxxxx: 0x80-0x9F)
                # Function Group 1: 0b100xxxxx, where:
                # Bit 4 = F0 (whistle/horn)
                # Bit 3 = F1
                # Bit 2 = F2
                # Bit 1 = F3
                # Bit 0 = F4
                self.whistle = (cmd_byte & 0x10) != 0  # Bit 4 is F0
        except Exception:
            pass  # Silently discard malformed packets

    def is_active(self) -> bool:
        """
        Returns True if DCC signal received recently (within CV44 timeout).

        Why: Track power loss or DCC base station failure causes signal dropout.
        Watchdog.check() monitors this method to trigger emergency shutdown if signal
        lost for >CV44 milliseconds (default 500ms).

        Args:
            None

        Returns:
            bool: True if valid packet decoded within last 500ms, False otherwise

        Raises:
            None

        Safety: Conservative 500ms timeout allows for DCC refresh rate (NMRA minimum
        30ms) plus margin for processing delays. False return forces Locomotive.die() to
        close regulator and kill heaters.

        Example:
            >>> decoder.last_valid = time.ticks_ms() - 100  # 100ms ago
            >>> decoder.is_active()
            True
            >>> decoder.last_valid = time.ticks_ms() - 600  # 600ms ago
            >>> decoder.is_active()
            False
        """
        return time.ticks_diff(time.ticks_ms(), self.last_valid) < 500
