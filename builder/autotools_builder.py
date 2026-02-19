"""
Autotools build orchestration for libraries like hwloc.
"""

import os
import platform as platform_module
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .cmake_builder import PatchManager
from .config import BuildConfig, Library

if TYPE_CHECKING:
    from .platforms.base import Platform


def _get_host_arch() -> str:
    """Get the current host architecture."""
    machine = platform_module.machine()
    if machine in ("arm64", "aarch64"):
        return "arm64"
    return "x86_64"


class AutotoolsBuilder:
    """Handles autotools-based builds (configure/make/make install)."""

    def __init__(self, config: BuildConfig, platform: "Platform"):
        self.config = config
        self.platform = platform
        self.patch_manager = PatchManager(config.root_dir)
        self._lib_handles_cross = False
        self._current_lib: Library | None = None

    def _has_custom_cross_targets(self, lib: Library) -> bool:
        """Check if the library handles cross-compilation itself via cross_compile_targets."""
        platform_config = lib.platforms.get(self.config.platform_name, {})
        cross_targets = platform_config.get("cross_compile_targets", {})
        return bool(cross_targets.get(self.config.arch))

    def build(self, lib: Library) -> bool:
        """Build a single autotools library. Returns True on success."""
        print(f"\n{'=' * 20} Building '{lib.name}' (autotools) for '{self.config.build_suffix}' {'=' * 20}\n")

        self._current_lib = lib
        source_dir = self.config.root_dir / lib.get_source_dir(self.config.platform_name)
        install_dir = self.config.output_dir

        # Ensure install directory exists
        install_dir.mkdir(parents=True, exist_ok=True)

        # Check if library handles cross-compilation itself (e.g. libvpx).
        # When true, we must not inject -arch flags since the library's own
        # build system manages architecture and our flags would conflict.
        self._lib_handles_cross = self._has_custom_cross_targets(lib)

        # Get autotools options
        autotools_opts = lib.platforms.get(self.config.platform_name, {}).get(
            "autotools_options", {}
        )
        base_opts = getattr(lib, "autotools_options", {}) if hasattr(lib, "autotools_options") else {}
        autotools_opts = {**base_opts, **autotools_opts}

        # Apply patches if any
        if not self.patch_manager.apply_patch(lib.name, source_dir):
            return False

        # Run autogen if needed
        if not self._run_autogen(source_dir):
            return False

        # Create build directory (arch-specific to prevent cross-architecture contamination)
        build_dir = source_dir / f"build-{self.config.arch}-{self.config.build_type}"
        build_dir.mkdir(parents=True, exist_ok=True)

        # Configure
        print(f"\n{'=' * 20} Configuring '{lib.name}' {'=' * 20}\n")
        if not self._run_configure(source_dir, build_dir, install_dir, autotools_opts, lib):
            return False

        # Build
        print(f"\n{'=' * 20} Building {'=' * 20}\n")
        if not self._run_make(build_dir):
            return False

        # Install
        print(f"\n{'=' * 20} Installing {'=' * 20}\n")
        if not self._run_make_install(build_dir):
            return False

        # Architecture validation (macOS only)
        if hasattr(self.platform, "validate_architecture"):
            success, errors = self.platform.validate_architecture(self.config, install_dir)
            if not success:
                print(f"\nArchitecture validation failed for '{lib.name}':", file=sys.stderr)
                for error in errors:
                    print(f"  - {error}", file=sys.stderr)
                return False

        print(f"\n{'=' * 20} Success! {'=' * 20}\n")
        return True

    def _run_autogen(self, source_dir: Path) -> bool:
        """Run autogen.sh if it exists."""
        autogen_script = source_dir / "autogen.sh"
        if not autogen_script.exists():
            return True

        print("Running autogen.sh...")
        return self._run_command(["bash", "autogen.sh"], cwd=source_dir)

    def _run_configure(
        self,
        source_dir: Path,
        build_dir: Path,
        install_dir: Path,
        options: dict,
        lib: Library = None,
    ) -> bool:
        """Run configure script."""
        configure_script = source_dir / "configure"

        args = [str(configure_script), f"--prefix={install_dir}"]

        # Add cross-compilation flags on macOS
        if self.config.platform_name == "macos":
            host_arch = _get_host_arch()
            target_arch = self.config.arch
            if host_arch != target_arch:
                # Check for library-specific cross-compile target (e.g. libvpx
                # uses --target instead of standard --build/--host)
                cross_target = None
                if lib:
                    platform_config = lib.platforms.get(self.config.platform_name, {})
                    cross_targets = platform_config.get("cross_compile_targets", {})
                    cross_target = cross_targets.get(target_arch)

                if cross_target:
                    args.append(f"--target={cross_target}")
                    print(f"  Cross-compiling: {host_arch} -> {target_arch} (target: {cross_target})")
                else:
                    # Standard autotools --build/--host triplets
                    args.append(f"--build={host_arch}-apple-darwin")
                    args.append(f"--host={target_arch}-apple-darwin")
                    print(f"  Cross-compiling: {host_arch} -> {target_arch}")

        # Add options
        for key, value in options.items():
            if isinstance(value, bool):
                if value:
                    args.append(f"--{key.replace('_', '-')}")
            else:
                args.append(f"--{key.replace('_', '-')}={value}")

        # Set environment for cross-compilation
        env = self._get_build_env()
        return self._run_command(args, cwd=build_dir, env=env)

    def _run_make(self, build_dir: Path) -> bool:
        """Run make with appropriate flags."""
        env = self._get_build_env()
        cmd = ["make", "-j"]
        return self._run_command(cmd, cwd=build_dir, env=env)

    def _run_make_install(self, build_dir: Path) -> bool:
        """Run make install."""
        return self._run_command(["make", "install"], cwd=build_dir)

    def _get_base_compile_flags(self) -> list[str]:
        """Get base compile flags shared between CFLAGS and CXXFLAGS."""
        flags = ["-fPIC"]

        if self.config.platform_name == "macos":
            # Skip -arch when the library handles cross-compilation itself
            # (e.g. libvpx uses --target and manages its own arch flags)
            if not self._lib_handles_cross:
                flags.append(f"-arch {self.config.arch}")
            if self.config.macos_sdk:
                flags.append(f"-mmacosx-version-min={self.config.macos_sdk}")

        if self.config.build_type == "Release":
            flags.append("-O2")
        else:
            flags.extend(["-g3", "-O0"])

        return flags

    def _get_cflags(self) -> str:
        """Get CFLAGS based on platform, build type, and library extra flags."""
        flags = self._get_base_compile_flags()

        if self._current_lib:
            extra = self._current_lib.get_extra_c_flags(self.config.platform_name)
            if extra:
                flags.append(extra)

        return " ".join(flags)

    def _get_cxxflags(self) -> str:
        """Get CXXFLAGS based on platform, build type, and library extra flags."""
        flags = self._get_base_compile_flags()

        if self._current_lib:
            extra = self._current_lib.get_extra_cxx_flags(self.config.platform_name)
            if extra:
                flags.append(extra)

        return " ".join(flags)

    def _get_ldflags(self) -> str:
        """Get LDFLAGS based on platform."""
        flags = []

        if self.config.platform_name == "macos":
            # Skip -arch when the library handles cross-compilation itself
            if not self._lib_handles_cross:
                flags.append(f"-arch {self.config.arch}")

        return " ".join(flags)

    def _get_build_env(self) -> dict:
        """Get environment variables for the build."""
        env = os.environ.copy()

        cflags = self._get_cflags()
        cxxflags = self._get_cxxflags()
        ldflags = self._get_ldflags()

        if cflags:
            env["CFLAGS"] = cflags
        if cxxflags:
            env["CXXFLAGS"] = cxxflags
        if ldflags:
            env["LDFLAGS"] = ldflags

        return env

    def _run_command(
        self,
        cmd: list[str],
        cwd: Path = None,
        env: dict = None,
    ) -> bool:
        """Run a command and return success status."""
        print(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, cwd=cwd, env=env, check=True)
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            print(f"Command failed with return code {e.returncode}", file=sys.stderr)
            return False
        except FileNotFoundError:
            print(f"Command not found: {cmd[0]}", file=sys.stderr)
            return False
