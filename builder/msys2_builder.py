"""
MSYS2 build orchestration for libraries using configure/make on Windows.

Used for libraries like libvpx that use their own configure/make system
(not autotools) but need a bash shell to run. The configure script targets
MSVC (--target=x86_64-win64-vs17) and the resulting Makefile invokes
msbuild.exe internally.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .cmake_builder import PatchManager
from .config import BuildConfig, Library

if TYPE_CHECKING:
    from .platforms.base import Platform


class Msys2Builder:
    """Handles builds that require MSYS2 bash on Windows (configure/make targeting MSVC)."""

    def __init__(self, config: BuildConfig, platform: "Platform"):
        self.config = config
        self.platform = platform
        self.patch_manager = PatchManager(config.root_dir)
        self._msbuild_dir: str | None = None

    def build(self, lib: Library) -> bool:
        """Build a single library via MSYS2. Returns True on success."""
        print(f"\n{'=' * 20} Building '{lib.name}' (msys2) for '{self.config.build_suffix}' {'=' * 20}\n")

        source_dir = self.config.root_dir / lib.get_source_dir(self.config.platform_name)
        build_dir = self.config.builds_dir / lib.name
        install_dir = self.config.output_dir

        # Ensure directories exist
        build_dir.mkdir(parents=True, exist_ok=True)
        install_dir.mkdir(parents=True, exist_ok=True)

        # Apply patches if any
        if not self.patch_manager.apply_patch(lib.name, source_dir):
            return False

        # Find MSYS2 bash
        bash = self._find_msys2_bash()
        if not bash:
            return False

        # Get autotools/configure options
        autotools_opts = dict(lib.autotools_options)
        platform_opts = lib.platforms.get(self.config.platform_name, {}).get(
            "autotools_options", {}
        )
        autotools_opts.update(platform_opts)

        # Configure
        print(f"\n{'=' * 20} Configuring '{lib.name}' {'=' * 20}\n")
        if not self._run_configure(bash, source_dir, build_dir, install_dir, autotools_opts, lib):
            return False

        # Build
        print(f"\n{'=' * 20} Building {'=' * 20}\n")
        if not self._run_make(bash, build_dir):
            return False

        # Install
        print(f"\n{'=' * 20} Installing {'=' * 20}\n")
        if not self._run_make_install(bash, build_dir):
            return False

        # Post-install: flatten lib subdirectories (libvpx puts .lib in lib/x64/)
        self._flatten_lib_dir(install_dir)

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

    def _find_msys2_bash(self) -> Path | None:
        """Find MSYS2 bash.exe.

        Search order:
        1. MSYS2_PATH environment variable
        2. Standard install locations (C:\\msys64, C:\\msys32)
        """
        # Check environment variable
        msys2_path = os.environ.get("MSYS2_PATH")
        if msys2_path:
            bash = Path(msys2_path) / "usr" / "bin" / "bash.exe"
            if bash.exists():
                print(f"  Found MSYS2 bash (from MSYS2_PATH): {bash}")
                return bash

        # Check standard locations
        for root in [Path("C:/msys64"), Path("C:/msys32")]:
            bash = root / "usr" / "bin" / "bash.exe"
            if bash.exists():
                print(f"  Found MSYS2 bash: {bash}")
                return bash

        print(
            "Error: MSYS2 bash.exe not found.\n"
            "  Install MSYS2 from https://www.msys2.org/\n"
            "  Or set MSYS2_PATH environment variable to your MSYS2 installation.",
            file=sys.stderr,
        )
        return None

    def _to_msys_path(self, path: Path) -> str:
        """Convert a Windows path to MSYS2 format (C:\\foo\\bar -> /c/foo/bar)."""
        # Resolve to absolute, then convert
        p = str(path.resolve()).replace("\\", "/")
        # C:/foo -> /c/foo
        if len(p) >= 2 and p[1] == ":":
            p = f"/{p[0].lower()}{p[2:]}"
        return p

    def _find_msbuild_dir(self) -> str | None:
        """Find the directory containing MSBuild.exe via vswhere.

        Returns the MSYS2-formatted path to the directory, or None.
        """
        if self._msbuild_dir is not None:
            return self._msbuild_dir

        # Check if msbuild is already in PATH
        msbuild = shutil.which("msbuild") or shutil.which("MSBuild")
        if msbuild:
            self._msbuild_dir = str(Path(msbuild).parent)
            print(f"  Found MSBuild (in PATH): {msbuild}")
            return self._msbuild_dir

        # Use vswhere to find Visual Studio
        vswhere_paths = [
            Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"))
            / "Microsoft Visual Studio" / "Installer" / "vswhere.exe",
        ]

        vswhere = None
        for p in vswhere_paths:
            if p.exists():
                vswhere = p
                break

        if not vswhere:
            print("  Warning: vswhere.exe not found, cannot locate MSBuild", file=sys.stderr)
            return None

        try:
            result = subprocess.run(
                [str(vswhere), "-latest", "-requires",
                 "Microsoft.Component.MSBuild",
                 "-find", "MSBuild\\**\\Bin\\MSBuild.exe"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                msbuild_path = Path(result.stdout.strip().splitlines()[0])
                self._msbuild_dir = str(msbuild_path.parent)
                print(f"  Found MSBuild (via vswhere): {msbuild_path}")
                return self._msbuild_dir
        except (subprocess.TimeoutExpired, OSError) as e:
            print(f"  Warning: Error running vswhere: {e}", file=sys.stderr)

        print(
            "Error: MSBuild.exe not found.\n"
            "  Install Visual Studio 2022 with C++ workload.",
            file=sys.stderr,
        )
        return None

    def _get_configure_target(self) -> str:
        """Get the libvpx configure target string for the current architecture."""
        if self.config.arch == "arm64":
            return "arm64-win64-vs17"
        return "x86_64-win64-vs17"

    def _run_bash(self, script: str, cwd: Path, bash: Path) -> bool:
        """Execute a script via MSYS2 bash.

        Uses bash --login to set up the MSYS2 environment, then prepends
        extra directories (MSBuild, Windows system) to PATH so that
        msbuild.exe and cl.exe are accessible.
        """
        env = os.environ.copy()
        # MSYSTEM=MSYS ensures we get the base MSYS2 environment
        env["MSYSTEM"] = "MSYS"

        # Build a list of extra directories to inject into MSYS2 PATH
        extra_paths = []
        msbuild_dir = self._find_msbuild_dir()
        if msbuild_dir:
            extra_paths.append(self._to_msys_path(Path(msbuild_dir)))

        # Prepend extra paths to PATH in the bash script
        if extra_paths:
            path_prefix = ":".join(extra_paths)
            path_export = f'export PATH="{path_prefix}:$PATH"; '
        else:
            path_export = ""

        full_script = f"{path_export}{script}"

        cmd = [str(bash), "-lc", full_script]
        print(f"Running (via MSYS2): {script}")

        try:
            result = subprocess.run(cmd, cwd=cwd, env=env, check=True)
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            print(f"Command failed with return code {e.returncode}", file=sys.stderr)
            return False
        except FileNotFoundError:
            print(f"Command not found: {cmd[0]}", file=sys.stderr)
            return False

    def _run_configure(
        self,
        bash: Path,
        source_dir: Path,
        build_dir: Path,
        install_dir: Path,
        options: dict,
        lib: Library,
    ) -> bool:
        """Run the configure script via MSYS2 bash."""
        configure_path = self._to_msys_path(source_dir / "configure")
        prefix_path = self._to_msys_path(install_dir)
        target = self._get_configure_target()

        args = [
            configure_path,
            f"--target={target}",
            f"--prefix={prefix_path}",
        ]

        # MT runtime: enable static MSVCRT linking
        if self.config.runtime_lib == "MT":
            args.append("--enable-static-msvcrt")

        # Add options from YAML
        for key, value in options.items():
            if isinstance(value, bool):
                if value:
                    args.append(f"--{key.replace('_', '-')}")
            else:
                args.append(f"--{key.replace('_', '-')}={value}")

        script = " ".join(args)
        return self._run_bash(script, build_dir, bash)

    def _run_make(self, bash: Path, build_dir: Path) -> bool:
        """Run make (which invokes msbuild internally for vs17 targets)."""
        return self._run_bash("make -j", build_dir, bash)

    def _run_make_install(self, bash: Path, build_dir: Path) -> bool:
        """Run make install."""
        return self._run_bash("make install", build_dir, bash)

    def _flatten_lib_dir(self, install_dir: Path) -> None:
        """Flatten platform subdirectories inside lib/.

        libvpx installs .lib files into lib/x64/ (or lib/arm64/).
        Move them up to lib/ for consistency with other libraries.
        Only targets known libvpx platform subdirectories.
        """
        lib_dir = install_dir / "lib"
        if not lib_dir.exists():
            return

        # Only flatten the specific subdirectories libvpx creates
        vpx_subdirs = ["x64", "x86", "arm64", "Win32"]
        for name in vpx_subdirs:
            subdir = lib_dir / name
            if not subdir.is_dir():
                continue
            for item in subdir.iterdir():
                dest = lib_dir / item.name
                if dest.exists():
                    dest.unlink()
                print(f"  Flattening: {name}/{item.name} -> lib/{item.name}")
                shutil.move(str(item), str(dest))
            try:
                subdir.rmdir()
            except OSError:
                pass
