"""
Configuration classes for the build system.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import platform
import yaml


@dataclass
class BuildConfig:
    """Global build configuration."""

    arch: str = "x86_64"
    build_type: str = "Release"
    macos_sdk: Optional[str] = None  # Required on macOS
    runtime_lib: str = "MD"  # Windows only: MD or MT
    root_dir: Path = field(default_factory=Path.cwd)

    def __post_init__(self):
        if isinstance(self.root_dir, str):
            self.root_dir = Path(self.root_dir)

    @property
    def platform_name(self) -> str:
        """Get the platform name (linux, macos, windows)."""
        system = platform.system().lower()
        if system == "darwin":
            return "macos"
        return system

    @property
    def platform_triplet(self) -> str:
        """Get the platform triplet (e.g., mac.arm64, linux.x86_64)."""
        prefix_map = {"macos": "mac", "linux": "linux", "windows": "windows"}
        prefix = prefix_map.get(self.platform_name, self.platform_name)
        return f"{prefix}.{self.arch}"

    @property
    def build_suffix(self) -> str:
        """Get the build suffix including runtime lib for Windows."""
        if self.platform_name == "windows":
            return f"{self.platform_triplet}-{self.build_type}-{self.runtime_lib}"
        return f"{self.platform_triplet}-{self.build_type}"

    @property
    def output_dir(self) -> Path:
        """Get the output/install directory."""
        return self.root_dir / "output" / self.build_suffix

    @property
    def builds_dir(self) -> Path:
        """Get the builds directory."""
        return self.root_dir / "builds" / self.build_suffix

    def validate(self) -> list[str]:
        """Validate the configuration. Returns list of errors."""
        errors = []

        if self.arch not in ("x86_64", "arm64"):
            errors.append(f"Invalid arch '{self.arch}'. Must be 'x86_64' or 'arm64'.")

        if self.build_type not in ("Release", "Debug"):
            errors.append(
                f"Invalid build_type '{self.build_type}'. Must be 'Release' or 'Debug'."
            )

        if self.platform_name == "macos" and not self.macos_sdk:
            errors.append("macos_sdk is required on macOS.")

        if self.runtime_lib not in ("MD", "MT"):
            errors.append(
                f"Invalid runtime_lib '{self.runtime_lib}'. Must be 'MD' or 'MT'."
            )

        return errors


@dataclass
class Library:
    """Configuration for a single library."""

    name: str
    source_dir: str
    build_system: str = "cmake"  # cmake or autotools
    cmake_options: dict = field(default_factory=dict)
    autotools_options: dict = field(default_factory=dict)
    platforms: dict = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=lambda: ["c"])
    use_install_prefix_as_find_root: bool = False
    disabled_platforms: list[str] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "Library":
        """Load a library configuration from a YAML file."""
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)

        return cls(
            name=data["name"],
            source_dir=data.get("source_dir", f"repositories/{data['name']}"),
            build_system=data.get("build_system", "cmake"),
            cmake_options=data.get("cmake_options", {}),
            autotools_options=data.get("autotools_options", {}),
            platforms=data.get("platforms", {}),
            depends_on=data.get("depends_on", []),
            languages=data.get("languages", ["c"]),
            use_install_prefix_as_find_root=data.get(
                "use_install_prefix_as_find_root", False
            ),
            disabled_platforms=data.get("disabled_platforms", []),
        )

    def get_cmake_options(self, platform_name: str, runtime_lib: str = "MD") -> dict:
        """Get merged CMake options for a specific platform and runtime.

        Args:
            platform_name: The target platform (linux, macos, windows)
            runtime_lib: Windows runtime library (MD or MT), ignored on other platforms
        """
        options = dict(self.cmake_options)

        # Merge platform-specific options
        if platform_name in self.platforms:
            platform_config = self.platforms[platform_name]
            platform_opts = platform_config.get("cmake_options", {})
            options.update(platform_opts)

            # Merge runtime-specific options (Windows only)
            if platform_name == "windows":
                runtime_key = f"runtime_{runtime_lib}"
                runtime_opts = platform_config.get(runtime_key, {})
                options.update(runtime_opts)

        return options

    def get_extra_c_flags(self, platform_name: str) -> str:
        """Get extra C flags to append for this library on a specific platform.

        These flags are appended to the platform's default C flags.
        """
        # Check platform-specific extra flags
        if platform_name in self.platforms:
            return self.platforms[platform_name].get("extra_c_flags", "")
        return ""

    def get_extra_cxx_flags(self, platform_name: str) -> str:
        """Get extra CXX flags to append for this library on a specific platform.

        These flags are appended to the platform's default CXX flags.
        """
        # Check platform-specific extra flags
        if platform_name in self.platforms:
            return self.platforms[platform_name].get("extra_cxx_flags", "")
        return ""

    def get_source_dir(self, platform_name: str) -> str:
        """Get the source directory for this library on a specific platform.

        Allows platform-specific source directories (e.g., for hwloc on Windows).
        """
        # Check platform-specific source_dir first
        if platform_name in self.platforms:
            platform_source = self.platforms[platform_name].get("source_dir")
            if platform_source:
                return platform_source
        return self.source_dir

    def get_build_system(self, platform_name: str) -> str:
        """Get the build system for this library on a specific platform.

        Allows platform-specific build systems (e.g., cmake on Windows, autotools on Linux).
        """
        # Check platform-specific build_system first
        if platform_name in self.platforms:
            platform_build = self.platforms[platform_name].get("build_system")
            if platform_build:
                return platform_build
        return self.build_system

    def is_enabled_for_platform(self, platform_name: str) -> bool:
        """Check if this library should be built for the given platform."""
        return platform_name not in self.disabled_platforms


class LibraryRegistry:
    """Registry of all available libraries."""

    def __init__(self, libraries_dir: Path):
        self.libraries_dir = libraries_dir
        self._libraries: dict[str, Library] = {}
        self._build_order: list[str] = []
        self._load_libraries()
        self._load_build_order()

    def _load_libraries(self):
        """Load all library configurations from YAML files."""
        if not self.libraries_dir.exists():
            return

        for yaml_file in self.libraries_dir.glob("*.yaml"):
            # Skip special files starting with _
            if yaml_file.name.startswith("_"):
                continue
            lib = Library.from_yaml(yaml_file)
            self._libraries[lib.name] = lib

    def _load_build_order(self):
        """Load build order configuration if available."""
        order_file = self.libraries_dir / "_build_order.yaml"
        if not order_file.exists():
            return

        with open(order_file, "r") as f:
            data = yaml.safe_load(f)

        if data and "order" in data:
            self._build_order = data["order"]

    def get(self, name: str) -> Optional[Library]:
        """Get a library by name."""
        return self._libraries.get(name)

    def get_all(self) -> list[Library]:
        """Get all libraries."""
        return list(self._libraries.values())

    def get_build_order(self, platform_name: str) -> list[Library]:
        """Get libraries in dependency order for a platform.

        Uses the configured build order as a base, then applies topological
        sort to ensure dependencies are built first.
        """
        enabled = {
            lib.name: lib
            for lib in self._libraries.values()
            if lib.is_enabled_for_platform(platform_name)
        }

        # Start with configured order, filter to enabled libs
        base_order = [
            name for name in self._build_order
            if name in enabled
        ]

        # Add any libraries not in the configured order
        remaining = [
            name for name in sorted(enabled.keys())
            if name not in base_order
        ]
        base_order.extend(remaining)

        # Topological sort based on dependencies, respecting base order
        ordered = []
        visited = set()
        temp_mark = set()

        def visit(lib_name: str):
            if lib_name in temp_mark:
                raise ValueError(f"Circular dependency detected: {lib_name}")
            if lib_name in visited:
                return
            if lib_name not in enabled:
                return

            lib = enabled[lib_name]
            temp_mark.add(lib_name)

            for dep_name in lib.depends_on:
                if dep_name in enabled:
                    visit(dep_name)

            temp_mark.remove(lib_name)
            visited.add(lib_name)
            ordered.append(lib)

        # Visit libraries in base order to maintain preferred ordering
        for lib_name in base_order:
            if lib_name not in visited:
                visit(lib_name)

        return ordered

    def get_with_dependencies(
        self, name: str, platform_name: str
    ) -> list[Library]:
        """Get a library and all its dependencies in build order."""
        lib = self._libraries.get(name)
        if not lib:
            return []

        deps = set()

        def collect_deps(library: Library):
            for dep_name in library.depends_on:
                dep = self._libraries.get(dep_name)
                if dep and dep.is_enabled_for_platform(platform_name):
                    deps.add(dep_name)
                    collect_deps(dep)

        collect_deps(lib)

        # Get ordered list
        all_ordered = self.get_build_order(platform_name)
        return [l for l in all_ordered if l.name in deps or l.name == name]
