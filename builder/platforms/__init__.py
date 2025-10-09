"""
Platform-specific build configurations.
"""

from .base import Platform
from .linux import LinuxPlatform
from .macos import MacOSPlatform
from .windows import WindowsPlatform


def get_platform(platform_name: str) -> Platform:
    """Get the appropriate platform handler."""
    platforms = {
        "linux": LinuxPlatform,
        "macos": MacOSPlatform,
        "windows": WindowsPlatform,
    }

    platform_class = platforms.get(platform_name)
    if not platform_class:
        raise ValueError(f"Unsupported platform: {platform_name}")

    return platform_class()


__all__ = [
    "Platform",
    "LinuxPlatform",
    "MacOSPlatform",
    "WindowsPlatform",
    "get_platform",
]
