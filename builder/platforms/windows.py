"""
Windows platform configuration.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from .base import Platform

if TYPE_CHECKING:
    from ..config import BuildConfig, Library


class WindowsPlatform(Platform):
    """Windows-specific build configuration."""

    _dumpbin_path: Optional[Path] = None
    _dumpbin_searched: bool = False
    _validated_libs: set[str] = set()  # Track already validated .lib files
    _msvc_env_cache: dict[str, Optional[dict[str, str]]] = {}

    @property
    def name(self) -> str:
        return "windows"

    def _find_dumpbin(self) -> Optional[Path]:
        """Find dumpbin.exe using vswhere or PATH.

        Searches in order:
        1. PATH (if running from Developer Command Prompt)
        2. Via vswhere to locate Visual Studio installation
        """
        if WindowsPlatform._dumpbin_searched:
            return WindowsPlatform._dumpbin_path

        WindowsPlatform._dumpbin_searched = True

        # First, check if dumpbin is in PATH
        dumpbin_in_path = shutil.which("dumpbin")
        if dumpbin_in_path:
            WindowsPlatform._dumpbin_path = Path(dumpbin_in_path)
            return WindowsPlatform._dumpbin_path

        # Use vswhere to find Visual Studio
        vswhere_paths = [
            Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"))
            / "Microsoft Visual Studio"
            / "Installer"
            / "vswhere.exe",
            Path("C:\\Program Files (x86)\\Microsoft Visual Studio\\Installer\\vswhere.exe"),
        ]

        vswhere = None
        for p in vswhere_paths:
            if p.exists():
                vswhere = p
                break

        if not vswhere:
            print("  Warning: vswhere.exe not found")
            return None

        try:
            result = subprocess.run(
                [
                    str(vswhere),
                    "-latest",
                    "-requires",
                    "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                    "-property",
                    "installationPath",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0 or not result.stdout.strip():
                print("  Warning: vswhere could not find Visual Studio with VC tools")
                return None

            vs_path = Path(result.stdout.strip())
            vc_tools_dir = vs_path / "VC" / "Tools" / "MSVC"

            if not vc_tools_dir.exists():
                print(f"  Warning: VC tools directory not found: {vc_tools_dir}")
                return None

            # Get the latest MSVC version
            msvc_versions = sorted(vc_tools_dir.iterdir(), reverse=True)
            if not msvc_versions:
                print("  Warning: No MSVC versions found")
                return None

            # Try x64 host first, then x86
            for host in ["Hostx64", "Hostx86"]:
                for target in ["x64", "x86"]:
                    dumpbin = msvc_versions[0] / "bin" / host / target / "dumpbin.exe"
                    if dumpbin.exists():
                        WindowsPlatform._dumpbin_path = dumpbin
                        print(f"  Found dumpbin: {dumpbin}")
                        return WindowsPlatform._dumpbin_path

            print("  Warning: dumpbin.exe not found in MSVC installation")
            return None

        except (subprocess.TimeoutExpired, OSError) as e:
            print(f"  Warning: Error running vswhere: {e}")
            return None

    def _find_vcvarsall(self) -> Optional[Path]:
        """Locate vcvarsall.bat via vswhere."""
        vswhere_paths = [
            Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"))
            / "Microsoft Visual Studio"
            / "Installer"
            / "vswhere.exe",
            Path("C:\\Program Files (x86)\\Microsoft Visual Studio\\Installer\\vswhere.exe"),
        ]

        vswhere = next((p for p in vswhere_paths if p.exists()), None)
        if not vswhere:
            return None

        try:
            result = subprocess.run(
                [
                    str(vswhere),
                    "-latest",
                    "-requires",
                    "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                    "-property",
                    "installationPath",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0 or not result.stdout.strip():
                return None

            vcvarsall = (
                Path(result.stdout.strip()) / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
            )
            return vcvarsall if vcvarsall.exists() else None
        except (subprocess.TimeoutExpired, OSError):
            return None

    def get_msvc_env(self, config: "BuildConfig") -> Optional[dict[str, str]]:
        """Return an environment dict with MSVC tools activated.

        Build systems like Meson auto-detect the C compiler from PATH. If
        MSYS2's gcc is in PATH (required for libvpx) and MSVC is not, Meson
        will produce UNIX-style libfoo.a archives instead of foo.lib. To
        avoid forcing users to launch from a Developer Command Prompt, we
        locate vcvarsall.bat via vswhere, execute it, and capture the
        resulting environment.

        Returns None if cl.exe is already in PATH (caller's env is fine),
        or if vcvarsall.bat could not be located.
        """
        cache_key = config.arch
        if cache_key in WindowsPlatform._msvc_env_cache:
            return WindowsPlatform._msvc_env_cache[cache_key]

        if shutil.which("cl"):
            WindowsPlatform._msvc_env_cache[cache_key] = None
            return None

        vcvarsall = self._find_vcvarsall()
        if not vcvarsall:
            print("  Warning: vcvarsall.bat not found; build systems that auto-detect "
                  "the compiler may pick the wrong toolchain.")
            WindowsPlatform._msvc_env_cache[cache_key] = None
            return None

        vcvars_arch = "arm64" if config.arch == "arm64" else "x64"
        print(f"  Activating MSVC environment ({vcvars_arch}) via {vcvarsall}")

        try:
            # Pass the command as one string with `/s /c "<cmd>"`, not an argv
            # list: with a list, cmd's /c de-quoting mangles a vcvarsall path
            # containing spaces and exits rc=1. `/s` strips only the outer quote
            # pair, preserving the inner quoting around the path.
            result = subprocess.run(
                f'cmd.exe /s /c " "{vcvarsall}" {vcvars_arch} >nul && set "',
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                print(f"  Warning: vcvarsall.bat failed (rc={result.returncode})")
                WindowsPlatform._msvc_env_cache[cache_key] = None
                return None

            env: dict[str, str] = {}
            for line in result.stdout.splitlines():
                key, sep, value = line.partition("=")
                if sep:
                    env[key] = value

            # Sanity check: confirm cl.exe is actually reachable through the
            # captured PATH. If not, vcvarsall ran but didn't update PATH the
            # way we expected — better to know now than to fail in meson.
            # `set` emits PATH under its stored casing, "Path" on most machines
            # but "PATH" on some, so accept either.
            captured_path = env.get("PATH") or env.get("Path", "")
            cl_path = shutil.which("cl", path=captured_path)
            if cl_path:
                print(f"  MSVC activated: cl -> {cl_path}")
            else:
                print("  Warning: vcvarsall.bat ran but cl.exe is NOT in the "
                      "resulting PATH. Meson will likely fail.")

            WindowsPlatform._msvc_env_cache[cache_key] = env
            return env
        except (subprocess.TimeoutExpired, OSError) as e:
            print(f"  Warning: failed to run vcvarsall.bat: {e}")
            WindowsPlatform._msvc_env_cache[cache_key] = None
            return None

    def get_generator(self) -> str:
        return "Visual Studio 17 2022"

    def get_architecture_arg(self, config: "BuildConfig") -> Optional[str]:
        """Visual Studio uses -A for architecture selection."""
        return "ARM64" if config.arch == "arm64" else "x64"

    def get_platform_cmake_options(self, config: "BuildConfig") -> dict:
        """Windows requires MSVC runtime library settings."""
        runtime = self._get_runtime_library(config)

        options = {
            "CMAKE_MSVC_RUNTIME_LIBRARY": runtime,
            # CMAKE_MSVC_RUNTIME_LIBRARY is only honored when CMake policy
            # CMP0091 is NEW, which requires cmake_minimum_required(VERSION
            # 3.15+) at the consumed library's top level. Several upstreams
            # we vendor still declare older minimums (e.g. pthread-win32:
            # 2.8...3.14) and silently fall back to the legacy /MD-by-default
            # flags, producing .lib files that link MSVCRT regardless of the
            # runtime requested here. Forcing CMP0091=NEW project-wide makes
            # the runtime knob authoritative and keeps CRT validation honest.
            "CMAKE_POLICY_DEFAULT_CMP0091": "NEW",
        }

        return options

    def get_c_flags(self, config: "BuildConfig") -> str:
        """MSVC-specific C flags."""
        if config.build_type == "Debug":
            return f"/{config.runtime_lib}d /Od /Zi /D_DEBUG"
        return f"/{config.runtime_lib} /O2 /DNDEBUG"

    def get_cxx_flags(self, config: "BuildConfig") -> str:
        """MSVC-specific C++ flags (includes /EHsc for exception handling)."""
        if config.build_type == "Debug":
            return f"/{config.runtime_lib}d /Od /Zi /D_DEBUG /EHsc"
        return f"/{config.runtime_lib} /O2 /DNDEBUG /EHsc"

    def get_config_specific_c_flags(self, config: "BuildConfig") -> dict[str, str]:
        """Get config-specific C flags for multi-config generators like Visual Studio.

        Returns a dict mapping CMAKE_C_FLAGS_<CONFIG> to flag values.
        """
        debug_flags = f"/{config.runtime_lib}d /Od /Zi /D_DEBUG"
        release_flags = f"/{config.runtime_lib} /O2 /DNDEBUG"

        return {
            "CMAKE_C_FLAGS_DEBUG": debug_flags,
            "CMAKE_C_FLAGS_RELEASE": release_flags,
            "CMAKE_C_FLAGS_MINSIZEREL": release_flags,
            "CMAKE_C_FLAGS_RELWITHDEBINFO": f"/{config.runtime_lib} /O2 /Zi /DNDEBUG",
        }

    def get_config_specific_cxx_flags(self, config: "BuildConfig") -> dict[str, str]:
        """Get config-specific CXX flags for multi-config generators like Visual Studio.

        Returns a dict mapping CMAKE_CXX_FLAGS_<CONFIG> to flag values.
        """
        debug_flags = f"/{config.runtime_lib}d /Od /Zi /D_DEBUG /EHsc"
        release_flags = f"/{config.runtime_lib} /O2 /DNDEBUG /EHsc"

        return {
            "CMAKE_CXX_FLAGS_DEBUG": debug_flags,
            "CMAKE_CXX_FLAGS_RELEASE": release_flags,
            "CMAKE_CXX_FLAGS_MINSIZEREL": release_flags,
            "CMAKE_CXX_FLAGS_RELWITHDEBINFO": f"/{config.runtime_lib} /O2 /Zi /DNDEBUG /EHsc",
        }

    def _get_runtime_library(self, config: "BuildConfig") -> str:
        """Get the MSVC runtime library name."""
        runtime = "MultiThreaded"
        if config.build_type == "Debug":
            runtime += "Debug"
        if config.runtime_lib == "MD":
            runtime += "DLL"
        return runtime

    def post_install(
        self,
        config: "BuildConfig",
        lib: "Library",
        build_dir: Path,
        install_dir: Path,
    ) -> None:
        """Copy PDB files in Debug mode."""
        if config.build_type != "Debug":
            return

        pdb_dest_dir = install_dir / "lib"

        if not build_dir.exists():
            print(f"Build directory not found: {build_dir}. Skipping PDB copy.")
            return

        # Different libraries emit their .pdb in different locations under the
        # build dir (e.g. <build_dir>/Debug for most, <build_dir>/lib/Debug for
        # libzip). Search recursively for any per-target PDB matching the build
        # type, skipping compiler intermediate PDBs (vcNNN.pdb).
        pdb_files = [
            pdb
            for pdb in build_dir.rglob(f"{config.build_type}/*.pdb")
            if not re.fullmatch(r"vc\d+\.pdb", pdb.name, re.IGNORECASE)
        ]

        if not pdb_files:
            print(f"No PDB files found under {build_dir}. Skipping PDB copy.")
            return

        pdb_dest_dir.mkdir(parents=True, exist_ok=True)

        for pdb_file in pdb_files:
            dest_file = pdb_dest_dir / pdb_file.name
            print(f"Copying {pdb_file.name} to {pdb_dest_dir}")
            shutil.copy2(pdb_file, dest_file)

    def _get_expected_crt(self, config: "BuildConfig") -> str:
        """Get the expected CRT directive based on configuration.

        Expected results:
        - MT builds: LIBCMT
        - MTd builds: LIBCMTD
        - MD builds: MSVCRT
        - MDd builds: MSVCRTD
        """
        if config.runtime_lib == "MT":
            return "LIBCMTD" if config.build_type == "Debug" else "LIBCMT"
        else:  # MD
            return "MSVCRTD" if config.build_type == "Debug" else "MSVCRT"

    def _get_forbidden_crts(self, config: "BuildConfig") -> set[str]:
        """Get CRT directives that should NOT appear for this configuration."""
        expected = self._get_expected_crt(config)
        all_crts = {"LIBCMT", "LIBCMTD", "MSVCRT", "MSVCRTD"}
        return all_crts - {expected}

    def validate_crt_linkage(
        self, config: "BuildConfig", install_dir: Path
    ) -> tuple[bool, list[str]]:
        """Validate that all .lib files use the correct CRT.

        Only validates new files that haven't been checked yet.
        Returns (success, error_messages).
        """
        lib_dir = install_dir / "lib"
        if not lib_dir.exists():
            return True, []

        all_lib_files = list(lib_dir.glob("*.lib"))
        if not all_lib_files:
            return True, []

        # Filter to only new files not yet validated
        new_lib_files = [
            f for f in all_lib_files
            if str(f) not in WindowsPlatform._validated_libs
        ]

        if not new_lib_files:
            return True, []

        # Find dumpbin
        dumpbin = self._find_dumpbin()
        if not dumpbin:
            return False, ["dumpbin.exe not found. Install Visual Studio with C++ tools."]

        expected_crt = self._get_expected_crt(config)
        forbidden_crts = self._get_forbidden_crts(config)
        errors: list[str] = []

        # Regex to match CRT directives in dumpbin output
        crt_pattern = re.compile(r"\b(LIBCMTD?|MSVCRTD?)\b", re.IGNORECASE)

        print(f"\n{'=' * 20} Validating CRT linkage (expected: {expected_crt}) {'=' * 20}\n")

        for lib_file in new_lib_files:
            try:
                result = subprocess.run(
                    [str(dumpbin), "/directives", str(lib_file)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    print(f"  Warning: dumpbin failed for {lib_file.name}")
                    continue

                # Find all CRT references in output
                found_crts = set()
                for match in crt_pattern.finditer(result.stdout):
                    found_crts.add(match.group(1).upper())

                # Check for forbidden CRTs
                bad_crts = found_crts & forbidden_crts
                if bad_crts:
                    error = f"{lib_file.name}: found {', '.join(sorted(bad_crts))} (expected only {expected_crt})"
                    errors.append(error)
                    print(f"  FAIL: {error}")
                else:
                    # Mark as validated only if successful
                    WindowsPlatform._validated_libs.add(str(lib_file))
                    if found_crts:
                        print(f"  OK: {lib_file.name} -> {', '.join(sorted(found_crts))}")
                    else:
                        print(f"  SKIP: {lib_file.name} (no CRT directives found)")

            except subprocess.TimeoutExpired:
                print(f"  Warning: dumpbin timeout for {lib_file.name}")
                continue

        return len(errors) == 0, errors
