"""Verify that required build tools are installed at the required versions."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
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

# Minimum versions for tools that have triggered build failures with older
# releases. Each constant carries a "Reason:" comment so future maintainers
# know why the floor was raised.

MIN_CMAKE_VERSION: tuple[int, int] = (3, 26)
# Reason: openal-soft's CMakeLists.txt uses the $<BUILD_LOCAL_INTERFACE:...>
# generator expression, introduced in CMake 3.26 (Ubuntu 22.04 ships 3.22).

MIN_GCC_VERSION: tuple[int, int] = (12, 0)
# Reason: openal-soft (core/hrtf.cpp) constructs std::string_view from a
# std::ranges::split_view inner iterator. GCC 11's libstdc++ doesn't model that
# iterator as contiguous, so the constructor's constraints aren't satisfied
# and compilation fails. GCC 12+ has the required ranges support.

MIN_CLANG_VERSION: tuple[int, int] = (15, 0)
# Reason: upstream Clang 15 matches the C++20 ranges/concepts maturity we need.

MIN_APPLE_CLANG_VERSION: tuple[int, int] = (14, 0)
# Reason: Xcode 14 (Apple Clang 14) is the first release with the C++20 ranges
# support these libraries rely on.


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


def _run_version(cmd: list[str]) -> str | None:
    """Invoke `cmd` and return its combined stdout/stderr, or None on failure."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout or result.stderr


def _parse_major_minor(text: str) -> tuple[int, int] | None:
    """Pull the first MAJOR.MINOR pair out of `text`."""
    match = re.search(r"(\d+)\.(\d+)", text)
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)))


def _format_version(version: tuple[int, int]) -> str:
    return f"{version[0]}.{version[1]}"


def _check_cmake_version() -> str | None:
    """Return an error string if CMake is too old; None if OK or undetectable."""
    output = _run_version(["cmake", "--version"])
    if not output:
        return None
    first_line = output.splitlines()[0]
    version = _parse_major_minor(first_line.replace("cmake version", ""))
    if version is None or version >= MIN_CMAKE_VERSION:
        return None
    return (
        f"CMake {_format_version(version)} is too old "
        f"(need {_format_version(MIN_CMAKE_VERSION)}+). "
        "Some libraries (e.g. openal-soft) use the "
        "$<BUILD_LOCAL_INTERFACE:...> generator expression introduced in "
        "CMake 3.26. Install a newer CMake via `pip install cmake` in the "
        "project venv, or via Kitware's APT repo (https://apt.kitware.com/)."
    )


def _resolve_cxx_compiler(platform_name: str) -> str | None:
    """Pick the C++ compiler the build will actually use.

    Honors $CXX (what CMake itself respects) before falling back to the
    platform default. Returns None on Windows — MSVC version checking happens
    via Visual Studio's own toolchain detection, not via this helper.
    """
    cxx = os.environ.get("CXX")
    if cxx:
        return cxx
    if platform_name == "linux":
        return "g++"
    if platform_name == "macos":
        return "clang++"
    return None


def _check_cxx_version(platform_name: str) -> str | None:
    """Return an error string if the C++ compiler is too old."""
    cxx = _resolve_cxx_compiler(platform_name)
    if cxx is None:
        return None
    if shutil.which(cxx) is None:
        return None
    output = _run_version([cxx, "--version"])
    if not output:
        return None
    first_line = output.splitlines()[0]

    if "Apple clang" in first_line or "Apple LLVM" in first_line:
        minimum = MIN_APPLE_CLANG_VERSION
        flavor = "Apple Clang"
    elif "clang" in first_line.lower():
        minimum = MIN_CLANG_VERSION
        flavor = "Clang"
    else:
        minimum = MIN_GCC_VERSION
        flavor = "GCC"

    version = _parse_major_minor(first_line)
    if version is None or version >= minimum:
        return None

    message = (
        f"{flavor} {_format_version(version)} (from {cxx!r}) is too old "
        f"(need {_format_version(minimum)}+). Some libraries (e.g. openal-soft) "
        "use C++20 ranges features that older releases don't fully support."
    )
    if platform_name == "linux" and flavor == "GCC":
        message += (
            "\n    On Ubuntu 22.04, install GCC 12 and select it for the build:\n"
            "      sudo apt install gcc-12 g++-12\n"
            "      export CC=gcc-12 CXX=g++-12"
        )
    return message


def check_tool_versions(platform_name: str) -> list[str]:
    """Return human-readable errors for tools whose version is too old.

    Only flags versions that are *detected and too low*. If a tool is missing
    or its version can't be parsed, it's silently skipped here — presence is
    handled by `check_required_tools`.
    """
    errors: list[str] = []
    cmake_error = _check_cmake_version()
    if cmake_error:
        errors.append(cmake_error)
    cxx_error = _check_cxx_version(platform_name)
    if cxx_error:
        errors.append(cxx_error)
    return errors


def report_tool_version_errors(errors: list[str]) -> None:
    """Print a clear error message listing tools with unsupported versions."""
    print("Error: the following build tools have unsupported versions:")
    for err in errors:
        print(f"  - {err}")