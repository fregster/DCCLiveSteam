"""
Tests for version management functionality.

These tests verify that version information is correctly exposed
and follows semantic versioning conventions.
"""

def test_version_string_format():
    """Verify __version__ follows semantic versioning format."""
    from app import __version__
    
    # Should be in format "major.minor.patch"
    parts = __version__.split('.')
    assert len(parts) == 3, f"Version {__version__} should have 3 parts"
    
    # All parts should be integers
    for part in parts:
        assert part.isdigit(), f"Version part '{part}' should be numeric"

def test_get_version_function():
    """Verify get_version() returns correct string."""
    from app import get_version, __version__
    
    version = get_version()
    assert version == __version__
    assert isinstance(version, str)

def test_get_version_info_structure():
    """Verify VERSION_INFO dictionary has required fields."""
    from app import get_version_info
    
    info = get_version_info()
    
    # Required fields
    assert "major" in info
    assert "minor" in info
    assert "patch" in info
    assert "release" in info
    assert "build_date" in info
    
    # Type validation
    assert isinstance(info["major"], int)
    assert isinstance(info["minor"], int)
    assert isinstance(info["patch"], int)
    assert isinstance(info["release"], str)
    assert isinstance(info["build_date"], str)

def test_version_info_matches_version_string():
    """Verify VERSION_INFO components match __version__ string."""
    from app import get_version_info, __version__
    
    info = get_version_info()
    major, minor, patch = __version__.split('.')
    
    assert info["major"] == int(major)
    assert info["minor"] == int(minor)
    assert info["patch"] == int(patch)

def test_version_info_returns_copy():
    """Verify get_version_info() returns a copy, not reference."""
    from app import get_version_info
    
    info1 = get_version_info()
    info2 = get_version_info()
    
    # Should be equal but not same object
    assert info1 == info2
    assert info1 is not info2
    
    # Modifying one should not affect the other
    info1["test_key"] = "test_value"
    assert "test_key" not in info2

def test_release_type_is_valid():
    """Verify release type is one of expected values."""
    from app import get_version_info
    
    info = get_version_info()
    valid_releases = ["stable", "beta", "alpha", "rc", "dev"]
    
    assert info["release"] in valid_releases, \
        f"Release '{info['release']}' should be one of {valid_releases}"

def test_build_date_format():
    """Verify build_date follows YYYY-MM-DD format."""
    from app import get_version_info
    import re
    
    info = get_version_info()
    date_pattern = r'^\d{4}-\d{2}-\d{2}$'
    
    assert re.match(date_pattern, info["build_date"]), \
        f"Build date '{info['build_date']}' should match YYYY-MM-DD format"

def test_version_is_v1_or_higher():
    """Verify we're at least at v1.0.0 (stable release)."""
    from app import get_version_info
    
    info = get_version_info()
    assert info["major"] >= 1, "Should be at least v1.x.x for production"
