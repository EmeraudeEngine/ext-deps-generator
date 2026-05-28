"""
CMake build orchestration.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .config import BuildConfig, Library

if TYPE_CHECKING:
    from .platforms.base import Platform


class PatchManager:
    """Handles applying and reverting patches to library sources."""

    _TARGET_COMMIT_RE = re.compile(r"^#\s*target-commit:\s*([0-9a-fA-F]{7,40})\s*$")

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.patches_dir = root_dir / "patches"
        self._applied_patches: dict[str, Path] = {}

    @classmethod
    def _read_target_commit(cls, patch_file: Path) -> str | None:
        """Pull a `# target-commit: <sha>` annotation from the patch preamble.

        Returns None if no header is present (patch is unguarded). Reading
        stops at the first `diff ` line — anything past that is patch content.
        """
        with patch_file.open() as f:
            for line in f:
                if line.startswith("diff "):
                    return None
                match = cls._TARGET_COMMIT_RE.match(line.rstrip("\n"))
                if match:
                    return match.group(1)
        return None

    @staticmethod
    def _current_source_commit(source_dir: Path) -> str | None:
        """Return the HEAD SHA of the git repo containing `source_dir`, or None."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=source_dir,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return None
        if result.returncode != 0:
            return None
        return result.stdout.strip()

    @staticmethod
    def _commits_match(target: str, actual: str) -> bool:
        # Either SHA may be abbreviated; accept if one is a prefix of the other.
        return actual.startswith(target) or target.startswith(actual)

    @staticmethod
    def _apply_path_args(source_dir: Path) -> list[str]:
        # `git apply` resolves patch paths against the work tree root, not cwd.
        # When source_dir is a subdirectory of the submodule (e.g. clipper2's
        # CPP/), we must add --directory=<rel> so paths land in the right
        # place; otherwise git silently no-ops and reports success.
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=source_dir, capture_output=True, text=True,
            )
        except FileNotFoundError:
            return []
        if result.returncode != 0:
            return []
        toplevel = Path(result.stdout.strip())
        try:
            rel = source_dir.resolve().relative_to(toplevel.resolve())
        except ValueError:
            return []
        if rel == Path(".") or str(rel) == "":
            return []
        return [f"--directory={rel.as_posix()}"]

    def apply_patch(self, lib_name: str, source_dir: Path) -> bool:
        """Apply patch for a library if it exists. Returns True on success."""
        patch_file = self.patches_dir / f"{lib_name}.patch"
        if not patch_file.exists():
            return True  # No patch to apply

        # Check if already applied by looking for our marker
        marker_file = source_dir / ".patch_applied"
        if marker_file.exists():
            print(f"  Patch already applied for '{lib_name}'")
            return True

        # Guard against silent drift: if the patch declares a target commit,
        # bail out when the source has moved underneath it. A patch authored
        # against an older revision may apply with subtly wrong semantics or
        # fail later in compilation; better to surface the mismatch up front.
        target_commit = self._read_target_commit(patch_file)
        if target_commit is not None:
            current_commit = self._current_source_commit(source_dir)
            if current_commit is None:
                print(
                    f"  Warning: could not determine HEAD of {source_dir}; "
                    f"skipping target-commit check for '{lib_name}'",
                    file=sys.stderr,
                )
            elif not self._commits_match(target_commit, current_commit):
                print(
                    f"  Error: patch '{lib_name}' targets commit "
                    f"{target_commit[:12]} but source is at "
                    f"{current_commit[:12]}.\n"
                    f"    The submodule has moved since the patch was "
                    f"authored. Review patches/{lib_name}.patch against the "
                    f"current source, regenerate if needed, then update the "
                    f"`# target-commit:` line at the top of the patch.",
                    file=sys.stderr,
                )
                return False

        print(f"  Applying patch for '{lib_name}'...")
        path_args = self._apply_path_args(source_dir)
        try:
            # Use git apply with --check first to verify
            check_cmd = ["git", "apply", "--check", *path_args, str(patch_file)]
            result = subprocess.run(
                check_cmd, cwd=source_dir, capture_output=True, text=True
            )
            if result.returncode != 0:
                # Patch may already be applied or conflicts
                print(f"  Patch check failed (may already be applied): {result.stderr}")
                return True

            # Apply the patch
            apply_cmd = ["git", "apply", *path_args, str(patch_file)]
            result = subprocess.run(
                apply_cmd, cwd=source_dir, capture_output=True, text=True
            )
            if result.returncode == 0:
                # Create marker file
                marker_file.write_text(f"Patch applied: {patch_file.name}\n")
                self._applied_patches[lib_name] = source_dir
                print(f"  Patch applied successfully")
                return True
            else:
                print(f"  Failed to apply patch: {result.stderr}", file=sys.stderr)
                return False
        except FileNotFoundError:
            print("  Warning: git not found, skipping patch", file=sys.stderr)
            return True

    def revert_patch(self, lib_name: str, source_dir: Path) -> bool:
        """Revert patch for a library. Returns True on success."""
        patch_file = self.patches_dir / f"{lib_name}.patch"
        marker_file = source_dir / ".patch_applied"

        if not marker_file.exists():
            return True  # No patch was applied

        print(f"  Reverting patch for '{lib_name}'...")
        path_args = self._apply_path_args(source_dir)
        try:
            cmd = ["git", "apply", "--reverse", *path_args, str(patch_file)]
            result = subprocess.run(cmd, cwd=source_dir, capture_output=True, text=True)
            if result.returncode == 0:
                marker_file.unlink()
                print(f"  Patch reverted successfully")
                return True
            else:
                print(f"  Failed to revert patch: {result.stderr}", file=sys.stderr)
                return False
        except FileNotFoundError:
            return True


class CMakeBuilder:
    """Handles CMake configuration, build, and installation."""

    def __init__(self, config: BuildConfig, platform: "Platform"):
        self.config = config
        self.platform = platform
        self.patch_manager = PatchManager(config.root_dir)

    def build(self, lib: Library) -> bool:
        """Build a single library. Returns True on success."""
        print(f"\n{'=' * 20} Building '{lib.name}' for '{self.config.build_suffix}' {'=' * 20}\n")

        source_dir = self.config.root_dir / lib.get_source_dir(self.config.platform_name)
        build_dir = self.config.builds_dir / lib.name
        install_dir = self.config.output_dir

        # Ensure directories exist
        build_dir.mkdir(parents=True, exist_ok=True)
        install_dir.mkdir(parents=True, exist_ok=True)

        # Apply patches if any
        if not self.patch_manager.apply_patch(lib.name, source_dir):
            return False

        # Build CMake arguments
        cmake_args = self._build_cmake_args(lib, source_dir, build_dir, install_dir)

        # Configure
        print(f"\n{'=' * 20} Configuring '{lib.name}' {'=' * 20}\n")
        if not self._run_cmake_configure(source_dir, build_dir, cmake_args):
            return False

        # Build
        print(f"\n{'=' * 20} Building {'=' * 20}\n")
        if not self._run_cmake_build(build_dir):
            return False

        # Install
        print(f"\n{'=' * 20} Installing {'=' * 20}\n")
        if not self._run_cmake_install(build_dir):
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

        # Post-build assertions declared by the library YAML.
        success, errors = lib.verify_post_build(self.config.platform_name, build_dir)
        if not success:
            print(f"\nPost-build assertions failed for '{lib.name}':", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return False

        print(f"\n{'=' * 20} Success! {'=' * 20}\n")
        return True

    def _build_cmake_args(
        self,
        lib: Library,
        source_dir: Path,
        build_dir: Path,
        install_dir: Path,
    ) -> list[str]:
        """Build the CMake configuration arguments."""
        args = []

        # Generator
        generator = self.platform.get_generator()
        args.extend(["-G", generator])

        # Architecture for Visual Studio
        arch_arg = self.platform.get_architecture_arg(self.config)
        if arch_arg:
            args.extend(["-A", arch_arg])

        # Basic options
        args.append(f"-DCMAKE_BUILD_TYPE={self.config.build_type}")
        args.append(f"-DCMAKE_INSTALL_PREFIX={install_dir}")

        # Platform-specific options
        platform_options = self.platform.get_platform_cmake_options(self.config)
        for key, value in platform_options.items():
            args.append(f"-D{key}={value}")

        # Language flags
        extra_c_flags = lib.get_extra_c_flags(self.config.platform_name)
        extra_cxx_flags = lib.get_extra_cxx_flags(self.config.platform_name)

        if "c" in lib.languages:
            c_flags = self.platform.get_c_flags(self.config)
            if extra_c_flags:
                c_flags = f"{c_flags} {extra_c_flags}" if c_flags else extra_c_flags
            if c_flags:
                args.append(f"-DCMAKE_C_FLAGS={c_flags}")

            # Config-specific flags for multi-config generators (Visual Studio)
            if hasattr(self.platform, "get_config_specific_c_flags"):
                for key, value in self.platform.get_config_specific_c_flags(self.config).items():
                    if extra_c_flags:
                        value = f"{value} {extra_c_flags}"
                    args.append(f"-D{key}={value}")

        if "cxx" in lib.languages:
            cxx_flags = self.platform.get_cxx_flags(self.config)
            if extra_cxx_flags:
                cxx_flags = f"{cxx_flags} {extra_cxx_flags}" if cxx_flags else extra_cxx_flags
            if cxx_flags:
                args.append(f"-DCMAKE_CXX_FLAGS={cxx_flags}")

            # Config-specific flags for multi-config generators (Visual Studio)
            if hasattr(self.platform, "get_config_specific_cxx_flags"):
                for key, value in self.platform.get_config_specific_cxx_flags(self.config).items():
                    if extra_cxx_flags:
                        value = f"{value} {extra_cxx_flags}"
                    args.append(f"-D{key}={value}")

        # Find root path for dependencies
        if lib.use_install_prefix_as_find_root:
            args.append(f"-DCMAKE_FIND_ROOT_PATH={install_dir}")

        # Prefix path for finding dependencies
        if lib.depends_on:
            args.append(f"-DCMAKE_PREFIX_PATH={install_dir}")

        # Library-specific options
        lib_options = lib.get_cmake_options(
            self.config.platform_name, self.config.runtime_lib
        )
        for key, value in lib_options.items():
            # Handle boolean values
            if isinstance(value, bool):
                value = "On" if value else "Off"
            # Path substitution: allow YAML to reference build-time paths.
            # Supported tokens: ${INSTALL_PREFIX}, ${ROOT_DIR}, ${SOURCE_DIR}, ${BUILD_DIR}
            # Use forward slashes (CMake convention) so backslash sequences like
            # \U in C:\Users aren't reinterpreted as escape codes when CMake
            # re-evaluates the value inside string contexts (add_custom_command, etc.).
            if isinstance(value, str):
                value = (
                    value.replace("${INSTALL_PREFIX}", install_dir.as_posix())
                    .replace("${ROOT_DIR}", self.config.root_dir.as_posix())
                    .replace("${SOURCE_DIR}", source_dir.as_posix())
                    .replace("${BUILD_DIR}", build_dir.as_posix())
                )
            args.append(f"-D{key}={value}")

        return args

    def _run_cmake_configure(
        self, source_dir: Path, build_dir: Path, args: list[str]
    ) -> bool:
        """Run CMake configuration."""
        cmd = ["cmake", "-S", str(source_dir), "-B", str(build_dir)] + args
        return self._run_command(cmd)

    def _run_cmake_build(self, build_dir: Path) -> bool:
        """Run CMake build."""
        cmd = [
            "cmake",
            "--build",
            str(build_dir),
            "--config",
            self.config.build_type,
        ]
        return self._run_command(cmd)

    def _run_cmake_install(self, build_dir: Path) -> bool:
        """Run CMake install."""
        cmd = [
            "cmake",
            "--install",
            str(build_dir),
            "--config",
            self.config.build_type,
        ]
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
