#!/usr/bin/env python3
"""
Unified build script for external dependencies.

Usage:
    python build.py                              # Build all for current platform
    python build.py --arch arm64                 # Specify architecture
    python build.py --build-type Debug           # Debug build
    python build.py --macos-sdk 12.0             # macOS deployment target
    python build.py --runtime-lib MT             # Windows runtime library
    python build.py --library zlib               # Build single library with deps
    python build.py --library zlib --no-deps     # Build single library only
    python build.py --list                       # List available libraries
    python build.py --clean                      # Clean build and output directories
"""

import argparse
import shutil
import sys
from pathlib import Path

from builder.config import BuildConfig, Library, LibraryRegistry
from builder.cmake_builder import CMakeBuilder
from builder.autotools_builder import AutotoolsBuilder
from builder.meson_builder import MesonBuilder
from builder.msys2_builder import Msys2Builder
from builder.platforms import get_platform


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Build external dependencies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--arch",
        choices=["x86_64", "arm64"],
        default="x86_64",
        help="Target architecture (default: x86_64)",
    )

    parser.add_argument(
        "--build-type",
        choices=["Release", "Debug"],
        default="Release",
        help="Build type (default: Release)",
    )

    parser.add_argument(
        "--macos-sdk",
        metavar="VERSION",
        help="macOS deployment target (required on macOS)",
    )

    parser.add_argument(
        "--runtime-lib",
        choices=["MD", "MT"],
        default="MD",
        help="Windows runtime library (default: MD)",
    )

    parser.add_argument(
        "--library",
        metavar="NAME",
        help="Build only this library (with dependencies unless --no-deps)",
    )

    parser.add_argument(
        "--no-deps",
        action="store_true",
        help="Don't build dependencies when using --library",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List available libraries and exit",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be built without building",
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build and output directories for current configuration",
    )

    return parser.parse_args()


def list_libraries(registry: LibraryRegistry, platform_name: str) -> None:
    """List all available libraries."""
    print("\nAvailable libraries:\n")

    libraries = registry.get_build_order(platform_name)

    for lib in libraries:
        details = []
        if lib.depends_on:
            details.append(f"depends on: {', '.join(lib.depends_on)}")
        if lib.build_system != "cmake":
            details.append(f"build: {lib.build_system}")

        suffix = f" ({', '.join(details)})" if details else ""
        print(f"  - {lib.name}{suffix}")

    print(f"\nTotal: {len(libraries)} libraries for {platform_name}")


def clean_directories(root_dir: Path) -> None:
    """Clean build and output directories.

    - Removes all contents from builds/
    - Empties each subdirectory in output/ but keeps the directories themselves
      (symlinks may be attached to them)
    """
    print(f"\n{'=' * 60}")
    print("Cleaning build directories")
    print(f"{'=' * 60}\n")

    # Clean builds directory
    builds_dir = root_dir / "builds"
    if builds_dir.exists():
        print(f"Cleaning: {builds_dir}")
        shutil.rmtree(builds_dir)
        print("  Done")
    else:
        print(f"Not found: {builds_dir}")

    # Empty each subdirectory in output/ but keep them
    output_dir = root_dir / "output"
    if output_dir.exists():
        print(f"\nCleaning: {output_dir}")
        for subdir in output_dir.iterdir():
            if subdir.is_dir():
                for item in subdir.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                print(f"  Emptied: {subdir.name}/")
    else:
        print(f"\nNot found: {output_dir}")

    # Reset validated libs cache (Windows)
    try:
        from builder.platforms.windows import WindowsPlatform
        WindowsPlatform._validated_libs.clear()
    except ImportError:
        pass

    print(f"\n{'=' * 60}")
    print("Clean completed!")
    print(f"{'=' * 60}\n")


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Determine root directory
    root_dir = Path(__file__).parent.resolve()

    # Clean mode (no config validation needed)
    if args.clean:
        clean_directories(root_dir)
        return 0

    # Create build configuration
    config = BuildConfig(
        arch=args.arch,
        build_type=args.build_type,
        macos_sdk=args.macos_sdk,
        runtime_lib=args.runtime_lib,
        root_dir=root_dir,
    )

    # Get platform handler
    try:
        platform = get_platform(config.platform_name)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Validate configuration
    errors = config.validate()
    if errors:
        for error in errors:
            print(f"Error: {error}", file=sys.stderr)
        return 1

    # Load library registry
    libraries_dir = root_dir / "libraries"
    registry = LibraryRegistry(libraries_dir)

    # List mode
    if args.list:
        list_libraries(registry, config.platform_name)
        return 0

    # Determine which libraries to build
    if args.library:
        if args.no_deps:
            lib = registry.get(args.library)
            if not lib:
                print(f"Error: Unknown library '{args.library}'", file=sys.stderr)
                return 1
            if not lib.is_enabled_for_platform(config.platform_name):
                print(
                    f"Error: Library '{args.library}' is not available on {config.platform_name}",
                    file=sys.stderr,
                )
                return 1
            libraries = [lib]
        else:
            libraries = registry.get_with_dependencies(
                args.library, config.platform_name
            )
            if not libraries:
                print(f"Error: Unknown library '{args.library}'", file=sys.stderr)
                return 1
    else:
        libraries = registry.get_build_order(config.platform_name)

    if not libraries:
        print("No libraries to build.", file=sys.stderr)
        return 1

    # Show build plan
    print(f"\n{'=' * 60}")
    print(f"Building dependencies for '{config.build_suffix}'")
    print(f"{'=' * 60}\n")
    print("Libraries to build:")
    for lib in libraries:
        print(f"  - {lib.name}")
    print()

    if args.dry_run:
        print("Dry run - no builds performed.")
        return 0

    # Build libraries
    cmake_builder = CMakeBuilder(config, platform)
    autotools_builder = AutotoolsBuilder(config, platform)
    meson_builder = MesonBuilder(config, platform)
    msys2_builder = Msys2Builder(config, platform)
    failed = []

    for lib in libraries:
        # Select the appropriate builder (can be platform-specific)
        build_system = lib.get_build_system(config.platform_name)
        if build_system == "autotools":
            builder = autotools_builder
        elif build_system == "meson":
            builder = meson_builder
        elif build_system == "msys2":
            builder = msys2_builder
        else:
            builder = cmake_builder

        if not builder.build(lib):
            failed.append(lib.name)
            print(f"\nError: Failed to build '{lib.name}'", file=sys.stderr)
            break  # Stop on first failure

    if failed:
        print(f"\nBuild failed for: {', '.join(failed)}", file=sys.stderr)
        return 1

    print(f"\n{'=' * 60}")
    print("All builds completed successfully!")
    print(f"{'=' * 60}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
