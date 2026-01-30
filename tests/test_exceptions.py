"""
Exception handling and input validation tests for safety-critical system.
Ensures all except clauses specify exception types and all functions validate input.
"""
import pytest
from app.sensors import SensorSuite
from app.config import validate_and_update_cv

def test_no_bare_except_in_app():
    """
    Tests that no bare except clauses exist in app/ modules.
    
    Why: Bare excepts can mask critical errors and are forbidden.
    """
    import ast, os
    app_dir = os.path.join(os.path.dirname(__file__), '../app')
    def file_has_bare_except(fname):
        with open(os.path.join(app_dir, fname), 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                return node.lineno
        return None
    for fname in os.listdir(app_dir):
        if fname.endswith('.py') and fname != '__init__.py':
            lineno = file_has_bare_except(fname)
            if lineno:
                pytest.fail(f"Bare except in {fname} at line {lineno}")

def test_sensor_input_validation():
    """
    Tests that sensor input validation raises ValueError for out-of-range ADC.
    """
    from unittest.mock import Mock
    def mock_pin_factory(pin):
        return Mock()
    def mock_adc_factory(pin):
        adc = Mock()
        adc.read = Mock(return_value=2048)
        return adc
    sensors = SensorSuite(adc_factory=mock_adc_factory, pin_factory=mock_pin_factory, encoder_hw=Mock())
    with pytest.raises(ValueError):
        sensors._adc_to_temp(-1)
    with pytest.raises(ValueError):
        sensors._adc_to_temp(4096)

def test_cv_input_validation():
    """
    Tests that CV validation rejects invalid types and values.
    """
    cv_table = {32: 18.0}
    # Non-numeric
    success, msg = validate_and_update_cv(32, "abc", cv_table)
    assert not success and "not a number" in msg
    # Out of range
    success, msg = validate_and_update_cv(32, "999.0", cv_table)
    assert not success and "out of range" in msg
