"""
Unit tests for config.py module.
Tests configuration management and CV persistence.
"""
import pytest
import json
import os
from pathlib import Path
from app.config import ensure_environment, load_cvs, save_cvs, CV_DEFAULTS


@pytest.fixture
def temp_config_dir(tmp_path, monkeypatch):
    """
    Creates temporary directory for config files.
    
    Why: Tests should not modify real config files.
    """
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_ensure_environment_creates_config(temp_config_dir):
    """
    Tests that ensure_environment creates config.json if missing.
    
    Why: First boot should auto-provision factory defaults.
    
    Safety: System must have valid configuration to operate.
    """
    ensure_environment()
    
    config_file = temp_config_dir / 'config.json'
    assert config_file.exists()
    
    with open(config_file, 'r') as f:
        data = json.load(f)
    
    # Check critical CVs exist
    assert "1" in data  # DCC address
    assert "42" in data  # Boiler temp limit
    assert "43" in data  # Superheater limit


def test_ensure_environment_creates_error_log(temp_config_dir):
    """
    Tests that ensure_environment creates error_log.json if missing.
    
    Why: Error logging infrastructure must exist before first failure.
    """
    ensure_environment()
    
    log_file = temp_config_dir / 'error_log.json'
    assert log_file.exists()
    
    with open(log_file, 'r') as f:
        data = json.load(f)
    
    assert isinstance(data, list)
    assert len(data) == 0  # Should be empty initially


def test_load_cvs_returns_integer_keys(temp_config_dir):
    """
    Tests that load_cvs converts string keys to integers.
    
    Why: CV lookups use integer indices, not strings.
    """
    ensure_environment()
    cv_table = load_cvs()
    
    # Check keys are integers
    assert isinstance(list(cv_table.keys())[0], int)
    
    # Check critical values
    assert cv_table[1] == 3  # Default address
    assert cv_table[42] == 110  # Boiler limit


def test_save_cvs_persists_changes(temp_config_dir):
    """
    Tests that save_cvs writes changes to flash.
    
    Why: CV changes must survive power cycles.
    
    Safety: Modified safety limits must be preserved.
    """
    ensure_environment()
    cv_table = load_cvs()
    
    # Modify a CV
    cv_table[1] = 99  # Change address
    cv_table[42] = 105  # Lower boiler limit
    
    save_cvs(cv_table)
    
    # Reload and verify
    cv_reloaded = load_cvs()
    assert cv_reloaded[1] == 99
    assert cv_reloaded[42] == 105


def test_cv_defaults_have_safety_limits():
    """
    Tests that CV_DEFAULTS includes all critical safety thresholds.
    
    Why: Factory defaults must include thermal and signal limits.
    
    Safety: Missing defaults could result in unprotected operation.
    """
    # Check thermal limits
    assert "41" in CV_DEFAULTS  # Logic temp
    assert "42" in CV_DEFAULTS  # Boiler temp
    assert "43" in CV_DEFAULTS  # Superheater temp
    
    # Check timeout limits
    assert "44" in CV_DEFAULTS  # DCC timeout
    assert "45" in CV_DEFAULTS  # Power timeout
    
    # Validate reasonable defaults
    assert CV_DEFAULTS["41"] <= 85  # Logic temp not too high
    assert CV_DEFAULTS["42"] <= 120  # Boiler limit reasonable
    assert CV_DEFAULTS["43"] <= 300  # Superheater limit safe


def test_cv_defaults_have_servo_calibration():
    """
    Tests that CV_DEFAULTS includes servo endpoints.
    
    Why: Servo must have valid neutral and max positions.
    
    Safety: Invalid servo positions could jam regulator.
    """
    assert "46" in CV_DEFAULTS  # Neutral position
    assert "47" in CV_DEFAULTS  # Max position
    assert "49" in CV_DEFAULTS  # Travel time
    
    # Max should be greater than neutral
    assert CV_DEFAULTS["47"] > CV_DEFAULTS["46"]


def test_load_cvs_missing_file_raises_error(temp_config_dir):
    """
    Tests that load_cvs fails gracefully if config missing.
    
    Why: Should call ensure_environment first, but test error handling.
    """
    with pytest.raises(FileNotFoundError):
        load_cvs()


def test_save_cvs_with_float_values(temp_config_dir):
    """
    Tests that save_cvs handles float CV values.
    
    Why: Some CVs like CV33 (pressure) use decimal values.
    """
    ensure_environment()
    cv_table = load_cvs()
    
    cv_table[33] = 37.5  # Set target pressure to 37.5 PSI
    save_cvs(cv_table)
    
    cv_reloaded = load_cvs()
    assert abs(cv_reloaded[33] - 37.5) < 0.1


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-W', 'error'])
