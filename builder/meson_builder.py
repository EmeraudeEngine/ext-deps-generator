"""
Meson build orchestration.
"""

import platform as platform_module
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, TYPE_CHECKING

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
        # On Windows, ensure MSVC is on PATH so Meson picks cl.exe and emits
        # foo.lib instead of MSYS2 gcc's libfoo.a.
        self._env: Optional[dict[str, str]] = None
        if hasattr(platform, "get_msvc_env"):
            self._env = platform.get_msvc_env(config)

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

        # Generate native file if needed (Windows: force MSVC)
        native_file = self._generate_native_file(build_dir)

        # Configure
        print(f"\n{'=' * 20} Configuring '{lib.name}' {'=' * 20}\n")
        if not self._run_meson_setup(
            lib, source_dir, build_dir, install_dir, cross_file, native_file
        ):
            return False

        # Build
        print(f"\n{'=' * 20} Building {'=' * 20}\n")
        if not self._run_meson_compile(build_dir):
            return False

        # Install
        print(f"\n{'=' * 20} Installing {'=' * 20}\n")
        if not self._run_meson_install(build_dir):
            return False

        # Meson intentionally names static libs `libfoo.a` even when built with
        # MSVC (see mesonbuild/build.py and the meson FAQ). The archives are
        # valid MSVC-produced .lib files internally — only the filename follows
        # GNU convention. Rename to `foo.lib` so they fit the rest of the
        # ecosystem (CRT validation, downstream linker expectations).
        if self.config.platform_name == "windows":
            self._rename_static_libs_to_lib(install_dir)

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

    def _generate_native_file(self, build_dir: Path) -> Path | None:
        """Generate a Meson native file forcing MSVC on Windows.

        Without this, Meson auto-detects the compiler from PATH/CC/CXX. If
        MSYS2's gcc is on PATH (required for libvpx), Meson silently picks
        it and produces UNIX-style libfoo.a archives instead of foo.lib.
        Pinning c='cl' / cpp='cl' here is bulletproof: native-file binaries
        override env vars and PATH auto-detection.
        """
        if self.config.platform_name != "windows":
            return None

        # Only pin c/cpp. Do NOT set `ar` — setting it forces Meson into GNU
        # ar mode, which names static archives `libfoo.a` regardless of the
        # compiler. With `c = 'cl'` alone, Meson picks the MSVC toolchain and
        # uses lib.exe to produce `foo.lib`.
        native_file = build_dir.parent / f"{build_dir.name}_meson_native.ini"
        native_file.write_text(
            "[binaries]\n"
            "c = 'cl'\n"
            "cpp = 'cl'\n"
        )
        print(f"  Generated native-file: {native_file}")
        return native_file

    def _run_meson_setup(
        self,
        lib: Library,
        source_dir: Path,
        build_dir: Path,
        install_dir: Path,
        cross_file: Path | None,
        native_file: Path | None,
    ) -> bool:
        """Run meson setup (configure)."""
        buildtype = "debug" if self.config.build_type == "Debug" else "release"

        # If a previous setup exists, nuke the build dir entirely. `meson setup
        # --wipe` reuses the previously-saved cmdline args, which means a new
        # --native-file (or any newly-added arg) would be silently ignored.
        # Deleting the dir forces a fresh setup that honors the current args.
        if (build_dir / "meson-private").is_dir():
            print(f"  Removing stale build dir: {build_dir}")
            shutil.rmtree(build_dir)
            build_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "meson", "setup",
            str(build_dir),
            str(source_dir),
            f"--prefix={install_dir}",
            f"--buildtype={buildtype}",
            "--default-library=static",
            # Force flat lib/ layout. Without this, Debian-flavored hosts make
            # meson install into lib/<host-triplet>/ (e.g. lib/x86_64-linux-gnu),
            # which diverges from the CMake builds and breaks downstream linking.
            "--libdir=lib",
        ]

        # Windows MSVC runtime selection. Meson defaults to /MD, ignoring any
        # /MT we'd pass via CFLAGS; the only honored knob is `b_vscrt`.
        if self.config.platform_name == "windows":
            is_debug = self.config.build_type == "Debug"
            if self.config.runtime_lib == "MT":
                vscrt = "mtd" if is_debug else "mt"
            else:
                vscrt = "mdd" if is_debug else "md"
            cmd.append(f"-Db_vscrt={vscrt}")

        # Cross-compilation file
        if cross_file:
            cmd.append(f"--cross-file={cross_file}")

        # Native file (Windows: force MSVC)
        if native_file:
            cmd.append(f"--native-file={native_file}")

        # Library-specific meson options
        meson_options = lib.get_meson_options(self.config.platform_name)
        for key, value in meson_options.items():
            cmd.append(f"-D{key}={value}")

        return self._run_command(cmd)

    def _run_meson_compile(self, build_dir: Path) -> bool:
        """Run meson compile."""
        cmd = ["meson", "compile", "-C", str(build_dir)]
        return self._run_command(cmd)

    def _run_meson_install(self, build_dir: Path) -> bool:
        """Run meson install."""
        cmd = ["meson", "install", "-C", str(build_dir)]
        return self._run_command(cmd)

    def _rename_static_libs_to_lib(self, install_dir: Path) -> None:
        """Rename `lib<name>.a` to `<name>.lib` in install_dir/lib."""
        lib_dir = install_dir / "lib"
        if not lib_dir.is_dir():
            return
        for archive in lib_dir.glob("lib*.a"):
            target = lib_dir / f"{archive.stem[3:]}.lib"
            if target.exists():
                target.unlink()
            archive.rename(target)
            print(f"  Renamed {archive.name} -> {target.name}")

    def _run_command(self, cmd: list[str]) -> bool:
        """Run a command and return success status."""
        print(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, check=True, env=self._env)
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            print(f"Command failed with return code {e.returncode}", file=sys.stderr)
            return False
        except FileNotFoundError:
            print(f"Command not found: {cmd[0]}", file=sys.stderr)
            return False
