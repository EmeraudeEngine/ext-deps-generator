"""Verify that required build tools are installed on the current platform."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


COMMON_TOOLS: list[tuple[str, str]] = [
    ("CMake", "cmake"),
    ("Ninja", "ninja"),
    ("Meson", "meson"),
    ("NASM", "nasm"),
]

# Autotools bootstrap differs per OS: Linux uses libtoolize (from the `libtool`
# apt package, which doesn't ship the libtool binary itself), while macOS ships
# Apple's libtool natively (used as a static archiver, e.g. in patches/libvpx.patch).
AUTOTOOLS_LINUX: list[tuple[str, str]] = [
    ("Autoconf", "autoconf"),
    ("Automake", "automake"),
    ("Libtoolize", "libtoolize"),
]

AUTOTOOLS_MACOS: list[tuple[str, str]] = [
    ("Autoconf", "autoconf"),
    ("Automake", "automake"),
    ("Libtool", "libtool"),
]

PLATFORM_TOOLS: dict[str, list[tuple[str, str]]] = {
    "linux": COMMON_TOOLS + AUTOTOOLS_LINUX + [("GCC", "gcc")],
    "macos": COMMON_TOOLS + AUTOTOOLS_MACOS + [("Clang (Xcode CLT)", "clang")],
    "windows": COMMON_TOOLS,
}


def _msys2_present() -> bool:
    """Return True if MSYS2 bash.exe is reachable (env var or standard path)."""
    msys2_path = os.environ.get("MSYS2_PATH")
    if msys2_path and (Path(msys2_path) / "usr" / "bin" / "bash.exe").exists():
        return True
    return any(
        (Path(root) / "usr" / "bin" / "bash.exe").exists()
        for root in ("C:/msys64", "C:/msys32")
    )


def check_required_tools(platform_name: str) -> list[str]:
    """Return a list of human-readable names of tools that are missing.

    Empty list means everything required for `platform_name` is present.
    """
    missing: list[str] = []

    for display_name, executable in PLATFORM_TOOLS.get(platform_name, []):
        if shutil.which(executable) is None:
            missing.append(f"{display_name} ({executable})")

    if platform_name == "windows" and not _msys2_present():
        missing.append("MSYS2 (required for libvpx)")

    return missing


def report_missing_tools(missing: list[str]) -> None:
    """Print a clear error message listing missing tools."""
    print("Error: the following required build tools are missing:")
    for tool in missing:
        print(f"  - {tool}")
    print(
        "\nSee the 'Prerequisites' section of README.md for installation "
        "instructions for your platform."
    )