from app.actuators import servo
"""
Advanced slew-rate limiting and emergency bypass tests for actuators.
Covers edge cases, rapid command changes, and repeated emergency triggers.
"""
from app.actuators.servo import MechanicalMapper

def test_slew_rate_limit_multiple_steps():
    """
    Tests that servo never exceeds max allowed step per update.
    """
    cv = {46: 77, 47: 128, 49: 1000}
    mapper = MechanicalMapper(cv)
    mapper.current = 77.0
    mapper.target = 128.0
    max_step = (cv[47] - cv[46]) / (cv[49] / 50)  # 50Hz update
    # The first step may be a stiction breakout (kick), so skip it
    # prev = mapper.current  # Removed unused variable
    mapper.update(cv)  # First update may be a stiction kick
    for _ in range(9):
        prev = mapper.current
        mapper.update(cv)
        # Now, all steps should be within slew rate
        assert abs(mapper.current - prev) <= max_step + 1e-3
        if mapper.current == mapper.target:
            break

def test_emergency_bypass_repeated():
    """
    Tests repeated toggling of emergency mode always results in instant movement.
    """
    cv = {46: 77, 47: 128, 49: 1000}
    mapper = MechanicalMapper(cv)
    for _ in range(5):
        mapper.current = 128.0
        mapper.target = 77.0
        mapper.emergency_mode = True
        mapper.update(cv)
        assert abs(mapper.current - 77.0) < 1e-6
        mapper.emergency_mode = False
        mapper.target = 128.0
        mapper.update(cv)
        assert mapper.current < 128.0
