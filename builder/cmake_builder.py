"""
CMake build orchestration.
"""

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .config import BuildConfig, Library

if TYPE_CHECKING:
    from .platforms.base import Platform


class CMakeBuilder:
    """Handles CMake configuration, build, and installation."""

    def __init__(self, config: BuildConfig, platform: "Platform"):
        self.config = config
        self.platform = platform

    def build(self, lib: Library) -> bool:
        """Build a single library. Returns True on success."""
        print(f"\n{'=' * 20} Building '{lib.name}' for '{self.config.build_suffix}' {'=' * 20}\n")

        source_dir = self.config.root_dir / lib.get_source_dir(self.config.platform_name)
        build_dir = self.config.builds_dir / lib.name
        install_dir = self.config.output_dir

        # Ensure directories exist
        build_dir.mkdir(parents=True, exist_ok=True)
        install_dir.mkdir(parents=True, exist_ok=True)

        # Build CMake arguments
        cmake_args = self._build_cmake_args(lib, source_dir, build_dir, install_dir)

        # Configure
        print(f"\n{'=' * 20} Configuring '{lib.name}' {'=' * 20}\n")
        if not self._run_cmake_configure(source_dir, build_dir, cmake_args):
            return False

        # Build
        print(f"\n{'=' * 20} Building {'=' * 20}\n")
        if not self._run_cmake_build(build_dir):
            return False

        # Install
        print(f"\n{'=' * 20} Installing {'=' * 20}\n")
        if not self._run_cmake_install(build_dir):
            return False

        # Post-install hook (platform-specific)
        self.platform.post_install(self.config, lib, build_dir, install_dir)

        # CRT validation (Windows only)
        if hasattr(self.platform, "validate_crt_linkage"):
            success, errors = self.platform.validate_crt_linkage(self.config, install_dir)
            if not success:
                print(f"\nCRT linkage validation failed for '{lib.name}':", file=sys.stderr)
                for error in errors:
                    print(f"  - {error}", file=sys.stderr)
                return False

        print(f"\n{'=' * 20} Success! {'=' * 20}\n")
        return True

    def _build_cmake_args(
        self,
        lib: Library,
        source_dir: Path,
        build_dir: Path,
        install_dir: Path,
    ) -> list[str]:
        """Build the CMake configuration arguments."""
        args = []

        # Generator
        generator = self.platform.get_generator()
        args.extend(["-G", generator])

        # Architecture for Visual Studio
        arch_arg = self.platform.get_architecture_arg(self.config)
        if arch_arg:
            args.extend(["-A", arch_arg])

        # Basic options
        args.append(f"-DCMAKE_BUILD_TYPE={self.config.build_type}")
        args.append(f"-DCMAKE_INSTALL_PREFIX={install_dir}")

        # Platform-specific options
        platform_options = self.platform.get_platform_cmake_options(self.config)
        for key, value in platform_options.items():
            args.append(f"-D{key}={value}")

        # Language flags
        extra_c_flags = lib.get_extra_c_flags(self.config.platform_name)
        extra_cxx_flags = lib.get_extra_cxx_flags(self.config.platform_name)

        if "c" in lib.languages:
            c_flags = self.platform.get_c_flags(self.config)
            if extra_c_flags:
                c_flags = f"{c_flags} {extra_c_flags}" if c_flags else extra_c_flags
            if c_flags:
                args.append(f"-DCMAKE_C_FLAGS={c_flags}")

            # Config-specific flags for multi-config generators (Visual Studio)
            if hasattr(self.platform, "get_config_specific_c_flags"):
                for key, value in self.platform.get_config_specific_c_flags(self.config).items():
                    if extra_c_flags:
                        value = f"{value} {extra_c_flags}"
                    args.append(f"-D{key}={value}")

        if "cxx" in lib.languages:
            cxx_flags = self.platform.get_cxx_flags(self.config)
            if extra_cxx_flags:
                cxx_flags = f"{cxx_flags} {extra_cxx_flags}" if cxx_flags else extra_cxx_flags
            if cxx_flags:
                args.append(f"-DCMAKE_CXX_FLAGS={cxx_flags}")

            # Config-specific flags for multi-config generators (Visual Studio)
            if hasattr(self.platform, "get_config_specific_cxx_flags"):
                for key, value in self.platform.get_config_specific_cxx_flags(self.config).items():
                    if extra_cxx_flags:
                        value = f"{value} {extra_cxx_flags}"
                    args.append(f"-D{key}={value}")

        # Find root path for dependencies
        if lib.use_install_prefix_as_find_root:
            args.append(f"-DCMAKE_FIND_ROOT_PATH={install_dir}")

        # Prefix path for finding dependencies
        if lib.depends_on:
            args.append(f"-DCMAKE_PREFIX_PATH={install_dir}")

        # Library-specific options
        lib_options = lib.get_cmake_options(
            self.config.platform_name, self.config.runtime_lib
        )
        for key, value in lib_options.items():
            # Handle boolean values
            if isinstance(value, bool):
                value = "On" if value else "Off"
            args.append(f"-D{key}={value}")

        return args

    def _run_cmake_configure(
        self, source_dir: Path, build_dir: Path, args: list[str]
    ) -> bool:
        """Run CMake configuration."""
        cmd = ["cmake", "-S", str(source_dir), "-B", str(build_dir)] + args
        return self._run_command(cmd)

    def _run_cmake_build(self, build_dir: Path) -> bool:
        """Run CMake build."""
        cmd = [
            "cmake",
            "--build",
            str(build_dir),
            "--config",
            self.config.build_type,
        ]
        return self._run_command(cmd)

    def _run_cmake_install(self, build_dir: Path) -> bool:
        """Run CMake install."""
        cmd = [
            "cmake",
            "--install",
            str(build_dir),
            "--config",
            self.config.build_type,
        ]
        return self._run_command(cmd)

    def _run_command(self, cmd: list[str]) -> bool:
        """Run a command and return success status."""
        print(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, check=True)
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            print(f"Command failed with return code {e.returncode}", file=sys.stderr)
            return False
        except FileNotFoundError:
            print(f"Command not found: {cmd[0]}", file=sys.stderr)
            return False
