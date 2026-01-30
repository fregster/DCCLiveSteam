# Ensure app.main is importable for tests and patching
from . import main
"""
ESP32 Live Steam Locomotive Controller
DCC-controlled automation system for live steam model locomotives.
"""

# Versioning: YY.MM.release_number (e.g., 26.01.1)
__version__ = "26.01.1"
__author__ = "ESP32 Live Steam Project"
__licence__ = "MIT"


# Parse version string for major, minor, patch
_version_parts = __version__.split('.')
_major = int(_version_parts[0]) if len(_version_parts) > 0 else 0
_minor = int(_version_parts[1]) if len(_version_parts) > 1 else 0
_patch = int(_version_parts[2]) if len(_version_parts) > 2 else 0
# Release type: always 'stable' for production, could be extended
_release = 'stable'

VERSION_INFO = {
    "version": __version__,
    "scheme": "YY.MM.release_number",
    "build_date": "2026-01-30",
    "major": _major,
    "minor": _minor,
    "patch": _patch,
    "release": _release
}


def get_version() -> str:
    """
    Returns the current software version in YY.MM.release_number format.

    Why: Provides a simple, date-based versioning scheme for CI, release tracking, and debugging.

    Returns:
        str: Version string (e.g., '26.01.1')

    Example:
        >>> from app import get_version
        >>> get_version()
        '26.01.1'
    """
    return __version__


def get_version_info() -> dict:
    """
    Returns detailed version information (date-based scheme).

    Returns:
        dict: Dictionary with version string, scheme, build date, major, minor, patch, release

    Example:
        >>> from app import get_version_info
        >>> info = get_version_info()
        >>> info['major']
        26
        >>> info['release']
        'stable'
    """
    return VERSION_INFO.copy()
