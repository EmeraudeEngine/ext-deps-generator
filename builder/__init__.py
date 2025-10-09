"""
Unified build system for external dependencies.
"""

from .config import BuildConfig, Library, LibraryRegistry
from .cmake_builder import CMakeBuilder
from .autotools_builder import AutotoolsBuilder

__all__ = [
    "BuildConfig",
    "Library",
    "LibraryRegistry",
    "CMakeBuilder",
    "AutotoolsBuilder",
]
