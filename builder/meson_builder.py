"""
Meson build orchestration.
"""

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


# Map our arch names to Meson cpu_family values
_MESON_CPU_FAMILY = {
    "x86_64": "x86_64",
    "arm64": "aarch64",
}


class MesonBuilder:
    """Handles Meson configuration, build, and installation."""

    def __init__(self, config: BuildConfig, platform: "Platform"):
        self.config = config
        self.platform = platform
        self.patch_manager = PatchManager(config.root_dir)

    def build(self, lib: Library) -> bool:
        """Build a single library. Returns True on success."""
        print(f"\n{'=' * 20} Building '{lib.name}' (meson) for '{self.config.build_suffix}' {'=' * 20}\n")

        source_dir = self.config.root_dir / lib.get_source_dir(self.config.platform_name)
        build_dir = self.config.builds_dir / lib.name
        install_dir = self.config.output_dir

        # Ensure directories exist
        build_dir.mkdir(parents=True, exist_ok=True)
        install_dir.mkdir(parents=True, exist_ok=True)

        # Apply patches if any
        if not self.patch_manager.apply_patch(lib.name, source_dir):
            return False

        # Generate cross-file if needed (macOS cross-compilation)
        cross_file = self._generate_cross_file(build_dir)

        # Configure
        print(f"\n{'=' * 20} Configuring '{lib.name}' {'=' * 20}\n")
        if not self._run_meson_setup(lib, source_dir, build_dir, install_dir, cross_file):
            return False

        # Build
        print(f"\n{'=' * 20} Building {'=' * 20}\n")
        if not self._run_meson_compile(build_dir):
            return False

        # Install
        print(f"\n{'=' * 20} Installing {'=' * 20}\n")
        if not self._run_meson_install(build_dir):
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

    def _generate_cross_file(self, build_dir: Path) -> Path | None:
        """Generate a Meson cross-file for macOS cross-compilation.

        Returns the path to the cross-file, or None if not cross-compiling.
        """
        if self.config.platform_name != "macos":
            return None

        host_arch = _get_host_arch()
        target_arch = self.config.arch
        if host_arch == target_arch:
            return None

        cpu_family = _MESON_CPU_FAMILY.get(target_arch, target_arch)
        min_version = self.config.macos_sdk or "12.0"

        cross_file = build_dir.parent / f"{build_dir.name}_meson_cross.ini"
        cross_file.write_text(
            f"[binaries]\n"
            f"c = 'cc'\n"
            f"cpp = 'c++'\n"
            f"ar = 'ar'\n"
            f"strip = 'strip'\n"
            f"\n"
            f"[host_machine]\n"
            f"system = 'darwin'\n"
            f"cpu_family = '{cpu_family}'\n"
            f"cpu = '{target_arch}'\n"
            f"endian = 'little'\n"
            f"\n"
            f"[built-in options]\n"
            f"c_args = ['-arch', '{target_arch}', '-mmacosx-version-min={min_version}', '-fPIC']\n"
            f"cpp_args = ['-arch', '{target_arch}', '-mmacosx-version-min={min_version}', '-fPIC']\n"
            f"c_link_args = ['-arch', '{target_arch}']\n"
            f"cpp_link_args = ['-arch', '{target_arch}']\n"
        )

        print(f"  Generated cross-file: {cross_file}")
        return cross_file

    def _run_meson_setup(
        self,
        lib: Library,
        source_dir: Path,
        build_dir: Path,
        install_dir: Path,
        cross_file: Path | None,
    ) -> bool:
        """Run meson setup (configure)."""
        buildtype = "debug" if self.config.build_type == "Debug" else "release"

        cmd = [
            "meson", "setup",
            str(build_dir),
            str(source_dir),
            f"--prefix={install_dir}",
            f"--buildtype={buildtype}",
            "--default-library=static",
        ]

        # Cross-compilation file
        if cross_file:
            cmd.append(f"--cross-file={cross_file}")

        # Library-specific meson options
        meson_options = lib.get_meson_options(self.config.platform_name)
        for key, value in meson_options.items():
            cmd.append(f"-D{key}={value}")

        # Wipe existing build if reconfiguring (only valid when a previous build exists)
        if (build_dir / "meson-private").is_dir():
            cmd.append("--wipe")

        return self._run_command(cmd)

    def _run_meson_compile(self, build_dir: Path) -> bool:
        """Run meson compile."""
        cmd = ["meson", "compile", "-C", str(build_dir)]
        return self._run_command(cmd)

    def _run_meson_install(self, build_dir: Path) -> bool:
        """Run meson install."""
        cmd = ["meson", "install", "-C", str(build_dir)]
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
