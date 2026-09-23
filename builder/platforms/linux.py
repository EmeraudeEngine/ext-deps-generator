"""
Linux platform configuration.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from .base import Platform

if TYPE_CHECKING:
    from ..config import BuildConfig, Library


class LinuxPlatform(Platform):
    """Linux-specific build configuration."""

    @property
    def name(self) -> str:
        return "linux"

    def get_generator(self) -> str:
        return "Ninja"

    def get_platform_cmake_options(self, config: "BuildConfig") -> dict:
        """Linux doesn't need special platform options."""
        return {}

    def get_c_flags(self, config: "BuildConfig") -> str:
        """Position-independent code for static libraries, build-machine paths remapped."""
        return " ".join(["-fPIC", *config.path_remap_flags])

    def get_cxx_flags(self, config: "BuildConfig") -> str:
        """Position-independent code for static libraries, build-machine paths remapped."""
        return " ".join(["-fPIC", *config.path_remap_flags])

    def post_install(
        self,
        config: "BuildConfig",
        lib: "Library",
        build_dir: Path,
        install_dir: Path,
    ) -> None:
        """Drop the absolute source paths left in the symbol tables of the installed archives."""
        self._strip_build_machine_file_symbols(config, install_dir)

    @staticmethod
    def _strip_build_machine_file_symbols(config: "BuildConfig", install_dir: Path) -> None:
        """Remove the STT_FILE symbols naming a file under the root directory.

        An assembler names each object's STT_FILE symbol after the source path it was
        given, and CMake gives absolute paths: NASM (libjpeg-turbo SIMD) put 27
        "<root>/repositories/libjpeg-turbo/simd/..." strings per archive into every binary
        linking it, out of reach of -fmacro-prefix-map. The symbol is informational only
        (it plays no part in linking or at runtime), so it is removed rather than renamed.
        The whole lib/ directory is swept on every install; archives already clean are
        left untouched.
        """
        lib_dir = install_dir / "lib"
        if not lib_dir.is_dir():
            return

        roots = tuple(f"{root}/" for root in config.build_machine_roots)
        env = {**os.environ, "LC_ALL": "C"}

        for archive in sorted(lib_dir.glob("*.a")):
            result = subprocess.run(
                ["readelf", "-sW", str(archive)], capture_output=True, text=True, env=env
            )
            if result.returncode != 0:
                raise RuntimeError(f"readelf failed on {archive}:\n{result.stderr}")

            names = set()
            for line in result.stdout.splitlines():
                fields = line.split()
                if len(fields) >= 8 and fields[3] == "FILE" and fields[7].startswith(roots):
                    names.add(fields[7])
            if not names:
                continue

            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
                handle.write("\n".join(sorted(names)) + "\n")
                symbols_file = handle.name
            try:
                result = subprocess.run(
                    ["objcopy", f"--strip-symbols={symbols_file}", str(archive)],
                    capture_output=True, text=True, env=env,
                )
            finally:
                os.unlink(symbols_file)
            if result.returncode != 0:
                raise RuntimeError(f"objcopy failed on {archive}:\n{result.stderr}")

            print(f"  {archive.name}: removed {len(names)} build-machine FILE symbol(s)")
