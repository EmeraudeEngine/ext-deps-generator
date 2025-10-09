"""
macOS platform configuration.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from .base import Platform

if TYPE_CHECKING:
    from ..config import BuildConfig, Library


class MacOSPlatform(Platform):
    """macOS-specific build configuration."""

    @property
    def name(self) -> str:
        return "macos"

    def get_generator(self) -> str:
        return "Ninja"

    def get_platform_cmake_options(self, config: "BuildConfig") -> dict:
        """macOS requires architecture and deployment target settings."""
        return {
            "CMAKE_OSX_ARCHITECTURES": config.arch,
            "CMAKE_OSX_DEPLOYMENT_TARGET": config.macos_sdk,
        }

    def get_c_flags(self, config: "BuildConfig") -> str:
        """macOS version min and position-independent code."""
        return f"-mmacosx-version-min={config.macos_sdk} -fPIC"

    def get_cxx_flags(self, config: "BuildConfig") -> str:
        """macOS version min and position-independent code."""
        return f"-mmacosx-version-min={config.macos_sdk} -fPIC"

    def post_install(
        self,
        config: "BuildConfig",
        lib: "Library",
        build_dir: Path,
        install_dir: Path,
    ) -> None:
        """No special post-install actions needed on macOS."""
        pass
