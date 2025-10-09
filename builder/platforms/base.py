"""
Base platform class defining the interface for platform-specific behavior.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import BuildConfig, Library


class Platform(ABC):
    """Abstract base class for platform-specific build configuration."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Platform name (linux, macos, windows)."""
        ...

    @abstractmethod
    def get_generator(self) -> str:
        """Get the CMake generator to use."""
        ...

    def get_architecture_arg(self, config: "BuildConfig") -> Optional[str]:
        """Get the architecture argument for CMake (e.g., -A for Visual Studio).

        Returns None if the generator doesn't use -A.
        """
        return None

    @abstractmethod
    def get_platform_cmake_options(self, config: "BuildConfig") -> dict:
        """Get platform-specific CMake options.

        These are applied to all libraries built on this platform.
        """
        ...

    @abstractmethod
    def get_c_flags(self, config: "BuildConfig") -> str:
        """Get C compiler flags for this platform."""
        ...

    @abstractmethod
    def get_cxx_flags(self, config: "BuildConfig") -> str:
        """Get C++ compiler flags for this platform."""
        ...

    def post_install(
        self,
        config: "BuildConfig",
        lib: "Library",
        build_dir: Path,
        install_dir: Path,
    ) -> None:
        """Hook called after installation completes.

        Override for platform-specific post-install actions.
        """
        pass
