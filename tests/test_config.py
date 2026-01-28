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


def test_cv_defaults_match_documentation():
    """
    Tests that CV_DEFAULTS includes all CVs documented in docs/CV.md.
    
    Why: CV_DEFAULTS must be kept in sync with documentation. Missing defaults
    cause incomplete config.json on first boot, leading to runtime errors when
    code tries to access undocumented CVs.
    
    Safety: Undocumented CVs prevent safe defaults from being provisioned.
    All CVs in CV.md must have defaults in CV_DEFAULTS.
    
    Example:
        >>> test_cv_defaults_match_documentation()
        # Asserts all CVs from documentation are in CV_DEFAULTS
    """
    # All CVs documented in docs/CV.md with their default values
    # Source: docs/CV.md - must match exactly
    documented_cvs = {
        "1": "Primary Address",
        "29": "Configuration",
        "30": "Failsafe Mode",
        "31": "Servo Offset",
        "32": "Target Pressure",      # CRITICAL: Was missing!
        "33": "Stiction Breakout",
        "34": "Slip Sensitivity",     # CRITICAL: Was missing!
        "37": "Wheel Radius",
        "38": "Encoder Count",
        "39": "Prototype Speed",
        "40": "Scale Ratio",
        "41": "Watchdog: Logic",
        "42": "Watchdog: Boiler",
        "43": "Watchdog: Super",
        "44": "Watchdog: DCC",
        "45": "Watchdog: Power",
        "46": "Servo Neutral",
        "47": "Servo Max",
        "48": "Whistle Offset",
        "49": "Travel Time"
    }
    
    # Verify each documented CV has a default
    missing_defaults = []
    for cv_num in documented_cvs:
        if cv_num not in CV_DEFAULTS:
            missing_defaults.append(f"CV{cv_num} ({documented_cvs[cv_num]})")
    
    assert missing_defaults == [], \
        f"CV_DEFAULTS missing: {', '.join(missing_defaults)}. " \
        f"When adding new CVs to docs/CV.md, add defaults to CV_DEFAULTS first."
    
    # Also verify no extra undocumented CVs (might be accidentally added)
    extra_cvs = []
    for cv_num in CV_DEFAULTS:
        if cv_num not in documented_cvs:
            extra_cvs.append(f"CV{cv_num}")
    
    assert extra_cvs == [], \
        f"CV_DEFAULTS has undocumented CVs: {', '.join(extra_cvs)}. " \
        f"Add these to docs/CV.md with parameter name and description."


def test_cv_defaults_values_are_valid():
    """
    Tests that all CV default values are valid types and reasonable.
    
    Why: Invalid defaults cause type errors or unsafe operation (e.g., negative
    temperature limits, servo PWM values outside 0-255 range).
    
    Safety: Type validation prevents runtime crashes from bad defaults.
    """
    # CV type validation: integer CVs should be int, float CVs should be float
    int_cvs = {"1", "29", "30", "31", "38", "40", "44", "45", "46", "47", "48", "49"}
    float_cvs = {"32", "33", "34", "37", "39", "42", "43", "41"}  # Pressure/temps can be float
    
    for cv_num in int_cvs:
        if cv_num in CV_DEFAULTS:
            assert isinstance(CV_DEFAULTS[cv_num], int), \
                f"CV{cv_num} should be int, got {type(CV_DEFAULTS[cv_num])}"
    
    for cv_num in float_cvs:
        if cv_num in CV_DEFAULTS:
            assert isinstance(CV_DEFAULTS[cv_num], (int, float)), \
                f"CV{cv_num} should be numeric, got {type(CV_DEFAULTS[cv_num])}"
    
    # Range validation for safety limits
    assert 0 <= CV_DEFAULTS["41"] <= 100, "CV41 (Logic temp) unreasonable"
    assert 0 <= CV_DEFAULTS["42"] <= 200, "CV42 (Boiler temp) unreasonable"
    assert 0 <= CV_DEFAULTS["43"] <= 300, "CV43 (Superheater temp) unreasonable"
    assert CV_DEFAULTS["42"] < CV_DEFAULTS["43"], "Boiler temp should be below superheater"
    
    # Range validation for servo PWM duty cycles (0-255)
    assert 0 <= CV_DEFAULTS["46"] <= 255, "CV46 (Servo neutral) out of PWM range"
    assert 0 <= CV_DEFAULTS["47"] <= 255, "CV47 (Servo max) out of PWM range"
    assert CV_DEFAULTS["46"] < CV_DEFAULTS["47"], "Servo neutral should be less than max"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-W', 'error'])
