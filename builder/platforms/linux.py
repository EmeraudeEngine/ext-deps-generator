"""
Linux platform configuration.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from .base import Platform

if TYPE_CHECKING:
    from ..config import BuildConfig, Library


class LinuxPlatform(Platform):
    """Linux-specific build configuration."""

    @property
    def name(self) -> str:
        return "linux"

    def get_generator(self) -> str:
        return "Ninja"

    def get_platform_cmake_options(self, config: "BuildConfig") -> dict:
        """Linux doesn't need special platform options."""
        return {}

    def get_c_flags(self, config: "BuildConfig") -> str:
        """Position-independent code for static libraries, build-machine paths remapped."""
        return " ".join(["-fPIC", *config.path_remap_flags])

    def get_cxx_flags(self, config: "BuildConfig") -> str:
        """Position-independent code for static libraries, build-machine paths remapped."""
        return " ".join(["-fPIC", *config.path_remap_flags])

    def post_install(
        self,
        config: "BuildConfig",
        lib: "Library",
        build_dir: Path,
        install_dir: Path,
    ) -> None:
        """No special post-install actions needed on Linux."""
        pass
