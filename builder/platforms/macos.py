"""
macOS platform configuration.
"""

import platform as platform_module
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from .base import Platform

if TYPE_CHECKING:
    from ..config import BuildConfig, Library


def _get_host_arch() -> str:
    """Get the current host architecture."""
    machine = platform_module.machine()
    if machine in ("arm64", "aarch64"):
        return "arm64"
    return "x86_64"


class MacOSPlatform(Platform):
    """macOS-specific build configuration."""

    _validated_libs: set[str] = set()  # Track already validated .a files

    @property
    def name(self) -> str:
        return "macos"

    def get_generator(self) -> str:
        return "Ninja"

    def get_platform_cmake_options(self, config: "BuildConfig") -> dict:
        """macOS requires architecture and deployment target settings.

        CMAKE_SYSTEM_PROCESSOR is critical for cross-compilation: without it,
        CMake auto-detects the host architecture. Libraries like cpu_features
        use this variable to decide which CPU detection logic to compile.
        Without it, cross-compiling from ARM to x86_64 produces x86_64 binaries
        with ARM internal logic.

        CMAKE_SYSTEM_NAME is set when cross-compiling to put CMake in official
        cross-compilation mode (CMAKE_CROSSCOMPILING=TRUE).
        """
        options = {
            "CMAKE_OSX_ARCHITECTURES": config.arch,
            "CMAKE_OSX_DEPLOYMENT_TARGET": config.macos_sdk,
            "CMAKE_SYSTEM_PROCESSOR": config.arch,
        }

        host_arch = _get_host_arch()
        if host_arch != config.arch:
            options["CMAKE_SYSTEM_NAME"] = "Darwin"

        return options

    def get_c_flags(self, config: "BuildConfig") -> str:
        """macOS architecture, version min, and position-independent code."""
        return f"-arch {config.arch} -mmacosx-version-min={config.macos_sdk} -fPIC"

    def get_cxx_flags(self, config: "BuildConfig") -> str:
        """macOS architecture, version min, and position-independent code."""
        return f"-arch {config.arch} -mmacosx-version-min={config.macos_sdk} -fPIC"

    def get_linker_flags(self, config: "BuildConfig") -> str:
        """macOS linker flags for cross-compilation."""
        return f"-arch {config.arch}"

    def post_install(
        self,
        config: "BuildConfig",
        lib: "Library",
        build_dir: Path,
        install_dir: Path,
    ) -> None:
        """No special post-install actions needed on macOS."""
        pass

    def validate_architecture(
        self, config: "BuildConfig", install_dir: Path
    ) -> tuple[bool, list[str]]:
        """Validate that all .a files have the correct architecture.

        Uses 'lipo -archs' to check each static library.
        Only validates new files that haven't been checked yet.
        Returns (success, error_messages).
        """
        lib_dir = install_dir / "lib"
        if not lib_dir.exists():
            return True, []

        all_lib_files = list(lib_dir.glob("*.a"))
        if not all_lib_files:
            return True, []

        # Filter to only new files not yet validated
        new_lib_files = [
            f for f in all_lib_files
            if str(f) not in MacOSPlatform._validated_libs
        ]

        if not new_lib_files:
            return True, []

        expected_arch = config.arch
        errors: list[str] = []

        print(f"\n{'=' * 20} Validating architecture (expected: {expected_arch}) {'=' * 20}\n")

        for lib_file in new_lib_files:
            try:
                result = subprocess.run(
                    ["lipo", "-archs", str(lib_file)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode != 0:
                    print(f"  Warning: lipo failed for {lib_file.name}: {result.stderr.strip()}")
                    continue

                archs = result.stdout.strip().split()

                if expected_arch not in archs:
                    error = f"{lib_file.name}: found {', '.join(archs)} (expected {expected_arch})"
                    errors.append(error)
                    print(f"  FAIL: {error}")
                else:
                    # Mark as validated only if successful
                    MacOSPlatform._validated_libs.add(str(lib_file))
                    print(f"  OK: {lib_file.name} -> {', '.join(archs)}")

            except subprocess.TimeoutExpired:
                print(f"  Warning: lipo timeout for {lib_file.name}")
                continue
            except FileNotFoundError:
                return False, ["lipo command not found. This should not happen on macOS."]

        return len(errors) == 0, errors
