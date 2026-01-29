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

    Args:
        serial_queue: SerialPrintQueue instance
        interval: Send interval (every N loops, default 50)
    """
    def __init__(self, serial_queue, interval=50):
        self.serial_queue = serial_queue
        self.interval = interval

    def process(self, velocity_cms, pressure, temps, servo_current, loop_count):
        """
        Formats and enqueues a status message if interval is met.
        """
        if loop_count % self.interval == 0:
            status_msg = (
                f"SPD:{velocity_cms:.1f} PSI:{pressure:.1f} "
                f"T:{temps[0]:.0f}/{temps[1]:.0f}/{temps[2]:.0f} "
                f"SRV:{int(servo_current)}"
            )
            self.serial_queue.enqueue(status_msg)
