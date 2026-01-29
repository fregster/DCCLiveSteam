"""
Tests for corrupted/missing config.json and unknown CVs.
Covers file corruption, missing keys, and unknown CV access.
"""
import pytest
import os
import json
from app.config import load_cvs, ensure_environment, CV_DEFAULTS

def test_missing_config_json(tmp_path, monkeypatch):
    """
    Tests system behaviour when config.json is missing.
    """
    monkeypatch.chdir(tmp_path)
    # Ensure file does not exist
    config_file = tmp_path / 'config.json'
    if config_file.exists():
        os.remove(config_file)
    # Should auto-create
    ensure_environment()
    assert config_file.exists()

def test_corrupted_config_json(tmp_path, monkeypatch):
    """
    Tests system behaviour when config.json is corrupted (invalid JSON).
    """
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / 'config.json'
    with open(config_file, 'w') as f:
        f.write('{corrupt json')
    with pytest.raises(json.JSONDecodeError):
        load_cvs()

def test_unknown_cv_access():
    """
    Tests that accessing unknown CV raises KeyError.
    """
    cvs = CV_DEFAULTS.copy()
    with pytest.raises(KeyError):
        _ = cvs['999']
