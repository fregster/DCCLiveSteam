# Ensure app.main is importable for tests and patching
from . import main
"""
ESP32 Live Steam Locomotive Controller
DCC-controlled automation system for live steam model locomotives.
"""
__version__ = "1.0.0"
__author__ = "ESP32 Live Steam Project"
__licence__ = "MIT"

# Version history
VERSION_INFO = {
    "major": 1,
    "minor": 0,
    "patch": 0,
    "release": "stable",
    "build_date": "2026-01-28"
}

def get_version() -> str:
    """Returns version string in semantic versioning format.
    
    Returns:
        Version string (e.g., "1.0.0")
        
    Example:
        >>> from app import get_version
        >>> get_version()
        '1.0.0'
    """
    return __version__

def get_version_info() -> dict:
    """Returns detailed version information.
    
    Returns:
        Dictionary with version components and metadata
        
    Example:
        >>> from app import get_version_info
        >>> info = get_version_info()
        >>> info['release']
        'stable'
    """
    return VERSION_INFO.copy()
