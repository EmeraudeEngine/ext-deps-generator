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

        pdb_source_dir = build_dir / config.build_type
        pdb_dest_dir = install_dir / "lib"

        if not pdb_source_dir.exists():
            print(f"PDB source directory not found: {pdb_source_dir}. Skipping PDB copy.")
            return

        pdb_dest_dir.mkdir(parents=True, exist_ok=True)

        for pdb_file in pdb_source_dir.glob("*.pdb"):
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
