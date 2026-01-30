"""
StatusReporter: Formats and enqueues periodic status messages.

Why:
    Encapsulates status message formatting and queueing logic, keeping main.py clean.
    Ensures status messages are sent at the correct interval.

Usage:
    status_reporter = StatusReporter(serial_queue)
    status_reporter.process(velocity, pressure, temps, servo_current, loop_count)
"""
class StatusReporter:
    """
    Handles periodic status message formatting and queueing.

    Why:
        Encapsulates status message formatting and queueing logic, keeping main.py clean.
        Ensures status messages are sent at the correct interval for telemetry and debugging.

    Args:
        serial_queue: SerialPrintQueue instance (required)
        interval: int, send interval (every N loops, default 50)

    Returns:
        None

    Raises:
        None

    Safety:
        Ensures status messages are sent at a controlled rate to avoid serial buffer overflows.
        Does not block main control loop.

    Example:
        >>> sr = StatusReporter(serial_queue)
        >>> sr.process(12.3, 45.6, [70, 110, 220], 120, 100)
    """
    def __init__(self, serial_queue, interval=50):
        """
        Initialises the StatusReporter.

        Why:
            Sets up the serial queue and reporting interval for status messages.

        Args:
            serial_queue: SerialPrintQueue instance (required)
            interval: int, send interval (every N loops, default 50)

        Returns:
            None

        Raises:
            None

        Safety:
            No direct hardware access; safe for use in main control loop.

        Example:
            >>> sr = StatusReporter(serial_queue)
        """
        self.serial_queue = serial_queue
        self.interval = interval

    def process(self, velocity_cms, pressure, temps, servo_current, loop_count):
        """
        Formats and enqueues a status message if the interval is met.

        Why:
            Ensures status messages are sent at a regular interval for monitoring and debugging.

        Args:
            velocity_cms: float, current speed in cm/s
            pressure: float, current boiler pressure in PSI
            temps: list of float, [logic_temp, boiler_temp, superheater_temp] in Celsius
            servo_current: float, current draw of servo in mA
            loop_count: int, current main loop iteration

        Returns:
            None

        Raises:
            None

        Safety:
            Does not block; only enqueues if interval is met. No direct hardware access.

        Example:
            >>> sr = StatusReporter(serial_queue)
            >>> sr.process(12.3, 45.6, [70, 110, 220], 120, 100)
        """
        if loop_count % self.interval == 0:
            status_msg = (
                f"SPD:{velocity_cms:.1f} PSI:{pressure:.1f} "
                f"T:{temps[0]:.0f}/{temps[1]:.0f}/{temps[2]:.0f} "
                f"SRV:{int(servo_current)}"
            )
            self.serial_queue.enqueue(status_msg)
