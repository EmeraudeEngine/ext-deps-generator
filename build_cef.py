#!/usr/bin/env python3
"""
Standalone CEF (Chromium Embedded Framework) build script.

CEF is deliberately NOT integrated into build.py / the libraries/*.yaml registry:
the other dependencies are small static libs built from git submodules via
cmake/autotools/meson, ordered by a dependency graph and linked together by the
DependenciesTest. CEF is a completely different beast — a full Chromium checkout
(~100 GB, several hours) driven by depot_tools + automate-git.py + GN, producing
a *binary distribution* (a shared libcef + a libcef_dll_wrapper static lib +
resources + headers), not a static lib. It has its own versioning (a CEF branch
number tied to a Chromium milestone). Shoehorning it into the registry would
pollute the dependency graph and the link test. So it lives here, on its own.

Why we build CEF ourselves (both reasons require a from-source build):

  1. H.264 / proprietary codecs — the official/Spotify builds ship with
     proprietary_codecs=false, ffmpeg_branding="Chromium". Enabling H.264 needs
     proprietary_codecs=true + ffmpeg_branding=Chrome, hence a source build.

  2. No V8 sandbox — app_system's zero-copy ArrayBuffer bridge (ASArrayBuffer /
     ASArrayBufferView, external C++ memory exposed to V8) is fundamentally
     incompatible with the V8 sandbox: when the sandbox is on, every ArrayBuffer
     backing store MUST live inside the sandbox's address space, so an external
     pointer crashes at ArrayBuffer::NewBackingStore. The sandbox is default-ON
     upstream but still disable-able at build time — which is why we can stay
     current AND keep zero-copy, as long as the flag survives upstream.

     IMPORTANT: disabling the sandbox REQUIRES also disabling pointer
     compression (three flags below, kept together). Cost: uncompressed 64-bit
     pointers = a bit more RAM per renderer. Negligible for us.

Staying current: bump DEFAULT_CEF_BRANCH (below) every 2-3 months to the current
stable CEF branch, re-run this script per platform, publish the archive. The
GN_DEFINES do not change across versions — only the branch number does.

    Find the current stable branch:
      https://bitbucket.org/chromiumembedded/cef/wiki/BranchesAndBuilding.md
      https://cef-builds.spotifycdn.com/index.html   (branch = milestone)

Usage:
    python build_cef.py                                  # host platform, Release, x86_64
    python build_cef.py --branch 6478                    # target a specific CEF branch
    python build_cef.py --arch arm64 --macos-sdk 12.0    # macOS arm64
    python build_cef.py --build-type Debug               # debug distribution
    python build_cef.py --distrib minimal                # smaller, ship-ready distribution
    python build_cef.py --download-dir /data/chromium    # where the ~100 GB checkout lives
    python build_cef.py --dry-run                         # print the plan, build nothing
    python build_cef.py --clean                           # remove the CEF output archives

CANNOT cross-compile Chromium: run this on the target OS (the one exception is
macOS x86_64/arm64 on an Apple-Silicon host). depot_tools is bootstrapped into
the download dir automatically if absent.
"""

import argparse
import os
import platform as _platform
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

from builder.config import BuildConfig


# ---------------------------------------------------------------------------
# Pinned CEF version — the ONLY knob to bump when staying current.
# ---------------------------------------------------------------------------
# Bump this to the current stable branch on each refresh cycle (see the URLs in
# the module docstring; branch = the 3rd component of the Chromium version, e.g.
# 149.0.7827.201 -> 7827). Override per-run with --branch.
#   7827 == CEF 149 / Chromium 149 (stable as of 2026-07)
#   6478 == CEF 126 / Chromium 126 (mid-2024 anchor, kept for reference)
DEFAULT_CEF_BRANCH = "7827"

# automate-git.py is fetched from the CEF repo (kept out of the checkout so a
# --force-clean of the Chromium tree never deletes our tooling).
AUTOMATE_GIT_URL = (
    "https://bitbucket.org/chromiumembedded/cef/raw/master/tools/automate/automate-git.py"
)
DEPOT_TOOLS_URL = "https://chromium.googlesource.com/chromium/tools/depot_tools.git"


# ---------------------------------------------------------------------------
# GN build arguments — the heart of this script. Same across every platform and
# every CEF version. These two goals (H.264 + no V8 sandbox) are the entire
# reason we build CEF ourselves; see the module docstring for the rationale.
# ---------------------------------------------------------------------------
# Values are written verbatim into the GN_DEFINES env var as `key=value`,
# space-separated. Booleans are the strings "true"/"false"; string-enum values
# (ffmpeg_branding) are bare per CEF's GN_DEFINES convention (no surrounding
# quotes — gn/automate handle them).
BASE_GN_DEFINES: dict[str, str] = {
    # --- Official, optimized build ---
    "is_official_build": "true",
    "use_thin_lto": "false",     # custom-build friendly + faster; official builds tolerate off
    "chrome_pgo_phase": "0",     # no profile-guided optimization data for a custom build

    # --- Goal 1: H.264 / AAC proprietary codecs ---
    "proprietary_codecs": "true",
    "ffmpeg_branding": "Chrome",

    # --- Goal 2: disable the V8 sandbox (mandatory for zero-copy ArrayBuffers) ---
    # These THREE must stay together: disabling the sandbox without also
    # disabling pointer compression is an unsupported combination that fails to
    # build / run.
    "v8_enable_sandbox": "false",
    "v8_enable_pointer_compression": "false",
    "v8_enable_pointer_compression_shared_cage": "false",
}

# Platform-specific additions merged on top of BASE_GN_DEFINES.
PLATFORM_GN_DEFINES: dict[str, dict[str, str]] = {
    "linux": {
        # Build against the bundled sysroot for a portable glibc floor
        # (mirrors the "build on the oldest target" discipline used elsewhere).
        "use_sysroot": "true",
    },
    "windows": {},
    "macos": {},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build CEF from source with H.264 enabled and the V8 sandbox disabled.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--branch",
        default=DEFAULT_CEF_BRANCH,
        metavar="N",
        help=f"CEF branch number (default: {DEFAULT_CEF_BRANCH}). Bump to stay current.",
    )
    parser.add_argument(
        "--arch",
        choices=["x86_64", "arm64"],
        default="x86_64",
        help="Target architecture (default: x86_64).",
    )
    parser.add_argument(
        "--build-type",
        choices=["Release", "Debug"],
        default="Release",
        help="Build type (default: Release).",
    )
    parser.add_argument(
        "--distrib",
        choices=["standard", "minimal", "client"],
        default="standard",
        help=(
            "Distribution flavor (default: standard). 'minimal' strips debug "
            "symbols/tools (ship-ready, much smaller); 'client' also builds the "
            "cefclient/cefsimple samples (useful to validate a build)."
        ),
    )
    parser.add_argument(
        "--macos-sdk",
        metavar="VERSION",
        help="macOS deployment target (required on macOS, e.g. 12.0).",
    )
    parser.add_argument(
        "--download-dir",
        metavar="PATH",
        help=(
            "Where the Chromium checkout + depot_tools live (~100 GB). "
            "Defaults to $CEF_DOWNLOAD_DIR, then ~/chromium_git. MUST be outside "
            "this repo."
        ),
    )
    parser.add_argument(
        "--force-clean",
        action="store_true",
        help="Pass --force-clean to automate-git.py (wipe & re-fetch the Chromium tree).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved plan (env, command, paths) and exit without building.",
    )
    parser.add_argument(
        "--archive",
        action="store_true",
        help="Also zip the distribution folder for publishing (output/<folder>-<cefversion>.zip).",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove this repo's CEF distribution folders (output/*.cef.*) and exit. Does NOT touch the Chromium checkout.",
    )
    return parser.parse_args()


def resolve_download_dir(arg: str | None) -> Path:
    """--download-dir > $CEF_DOWNLOAD_DIR > ~/chromium_git."""
    if arg:
        return Path(arg).expanduser().resolve()
    env = os.environ.get("CEF_DOWNLOAD_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / "chromium_git").resolve()


# Map (platform, arch) to the Spotify CDN platform token — the exact tokens the
# official CEF binary distributions use. Naming our output like Spotify's means
# the app_system consumer keeps working unchanged: only the download base URL
# changes (Spotify CDN -> our GitHub release), the cef_binary_<ver>_<token> name
# stays identical.
SPOTIFY_PLATFORM_TOKEN = {
    ("linux", "x86_64"): "linux64",
    ("linux", "arm64"): "linuxarm64",
    ("windows", "x86_64"): "windows64",
    ("windows", "arm64"): "windowsarm64",
    ("macos", "x86_64"): "macosx64",
    ("macos", "arm64"): "macosarm64",
}


def spotify_platform_token(config: BuildConfig) -> str:
    return SPOTIFY_PLATFORM_TOKEN[(config.platform_name, config.arch)]


def cef_output_root(root_dir: Path) -> Path:
    """Parent dir under which the Spotify-named distribution folders/archives land."""
    return root_dir / "output"


def clean_output(root_dir: Path) -> int:
    """Remove every CEF distribution (output/cef_binary_*, folders and archives).

    The Chromium checkout under the download dir is left untouched.
    """
    out_root = cef_output_root(root_dir)
    targets = sorted(out_root.glob("cef_binary_*")) if out_root.exists() else []
    print(f"\n{'=' * 60}\nCleaning CEF output\n{'=' * 60}\n")
    if targets:
        for t in targets:
            print(f"Removing: {t}")
            if t.is_dir():
                shutil.rmtree(t)
            else:
                t.unlink()
        print("  Done")
    else:
        print(f"Nothing to remove under {out_root} (no cef_binary_* entries).")
    print("\nNote: the Chromium checkout under the download dir is left untouched.")
    return 0


def check_cross_compile(config: BuildConfig) -> list[str]:
    """Chromium can't be cross-compiled, except macOS x86_64/arm64 on Apple Silicon."""
    errors: list[str] = []
    host_machine = _platform.machine().lower()
    host_arch = "arm64" if host_machine in ("arm64", "aarch64") else "x86_64"

    if config.arch != host_arch:
        if config.platform_name == "macos":
            # arm64 host can target x86_64 (and vice-versa) on macOS only.
            pass
        else:
            errors.append(
                f"Cannot cross-compile Chromium: host is {host_arch}, target is "
                f"{config.arch}. Run this script on a native {config.arch} "
                f"{config.platform_name} machine."
            )
    return errors


def build_gn_defines(platform_name: str) -> str:
    """Merge base + platform GN args into the space-separated GN_DEFINES string."""
    merged = dict(BASE_GN_DEFINES)
    merged.update(PLATFORM_GN_DEFINES.get(platform_name, {}))
    return " ".join(f"{k}={v}" for k, v in merged.items())


def build_environment(config: BuildConfig, gn_defines: str) -> dict[str, str]:
    """Environment for automate-git.py, including depot_tools on PATH."""
    env = dict(os.environ)
    env["CEF_USE_GN"] = "1"
    env["GN_DEFINES"] = gn_defines

    if config.platform_name == "windows":
        # Use the locally installed Visual Studio, not Google's internal toolchain.
        env["DEPOT_TOOLS_WIN_TOOLCHAIN"] = "0"
        env.setdefault("GYP_MSVS_VERSION", "2022")
    elif config.platform_name == "macos":
        if config.macos_sdk:
            env["MACOSX_DEPLOYMENT_TARGET"] = config.macos_sdk

    return env


def ensure_depot_tools(download_dir: Path, env: dict[str, str], dry_run: bool) -> Path:
    """Clone depot_tools into the download dir if absent; prepend it to PATH."""
    depot_tools = download_dir / "depot_tools"
    if not depot_tools.exists():
        print(f"depot_tools not found — cloning into {depot_tools} ...")
        if not dry_run:
            download_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", DEPOT_TOOLS_URL, str(depot_tools)], check=True
            )
    else:
        print(f"depot_tools present: {depot_tools}")

    # Prepend to PATH (both the caller's PATH copy and the child env).
    env["PATH"] = f"{depot_tools}{os.pathsep}{env.get('PATH', '')}"
    return depot_tools


def ensure_automate_git(download_dir: Path, dry_run: bool) -> Path:
    """Fetch automate-git.py into the download dir (kept out of the Chromium tree)."""
    automate = download_dir / "automate-git.py"
    if not automate.exists():
        print(f"Fetching automate-git.py -> {automate} ...")
        if not dry_run:
            download_dir.mkdir(parents=True, exist_ok=True)
            # depot_tools ships no downloader we can rely on cross-platform here;
            # urllib keeps this dependency-free.
            import urllib.request

            urllib.request.urlretrieve(AUTOMATE_GIT_URL, automate)
    else:
        print(f"automate-git.py present: {automate}")
    return automate


def automate_git_command(
    automate: Path, config: BuildConfig, args: argparse.Namespace, download_dir: Path
) -> list[str]:
    """Assemble the automate-git.py invocation."""
    cmd = [
        sys.executable,
        str(automate),
        f"--download-dir={download_dir}",
        f"--branch={args.branch}",
    ]

    # Build type: automate builds both by default; restrict to the one we want.
    if config.build_type == "Release":
        cmd.append("--no-debug-build")
    else:
        cmd.append("--no-release-build")

    # Architecture flag.
    cmd.append("--arm64-build" if config.arch == "arm64" else "--x64-build")

    # Distribution flavor.
    if args.distrib == "minimal":
        cmd.append("--minimal-distrib")
    elif args.distrib == "client":
        cmd.append("--client-distrib")
    # 'standard' -> automate produces the standard distribution by default.

    if args.force_clean:
        cmd.append("--force-clean")

    return cmd


def locate_distribution(download_dir: Path) -> Path | None:
    """Find the freshly produced CEF binary distribution folder.

    automate-git.py drops it under
    <download-dir>/chromium/src/cef/binary_distrib/cef_binary_<version>_<platform>[_minimal|_client].
    """
    distrib_root = download_dir / "chromium" / "src" / "cef" / "binary_distrib"
    if not distrib_root.exists():
        return None
    candidates = sorted(
        (p for p in distrib_root.iterdir() if p.is_dir() and p.name.startswith("cef_binary_")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def install_distribution(distrib: Path, output_root: Path, dry_run: bool) -> Path:
    """Copy the produced cef_binary_* distribution into output/, keeping its
    EXACT Spotify CDN name (cef_binary_<version>_<platform>[_<flavor>]).

    Because the name is identical to Spotify's, the app_system consumer keeps
    working unchanged — only its download base URL flips to our GitHub release.

    Merge semantics: building Release then Debug of the SAME branch yields the
    same folder name, so the second run adds its build subdir (Release/Debug)
    and refreshes the shared dirs (include, Resources, libcef_dll, cmake, *.txt)
    WITHOUT wiping the build subdir it didn't rebuild — only dirs present in the
    new distrib are replaced. A different version or flavor is a different folder
    (Spotify logic). Build both from the same branch for a Spotify-complete
    distribution (Release + Debug in one folder).
    """
    target = output_root / distrib.name
    print(f"\nInstalling distribution:\n  from: {distrib}\n  into: {target}")
    if dry_run:
        return target

    target.mkdir(parents=True, exist_ok=True)
    for entry in distrib.iterdir():
        dest = target / entry.name
        if entry.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(entry, dest)
        else:
            shutil.copy2(entry, dest)
    return target


def archive_dist(target: Path, dry_run: bool) -> Path:
    """Re-pack the distribution as <name>.tar.bz2 — the Spotify archive format.

    Extracts to a single top-level cef_binary_<version>_<platform>/ directory,
    exactly like the official CEF archives.
    """
    archive_path = target.parent / f"{target.name}.tar.bz2"
    print(f"\nArchiving:\n  from: {target}\n  into: {archive_path}")
    if dry_run:
        return archive_path
    if archive_path.exists():
        archive_path.unlink()
    with tarfile.open(archive_path, "w:bz2") as tar:
        tar.add(target, arcname=target.name)
    return archive_path


def main() -> int:
    args = parse_args()
    root_dir = Path(__file__).parent.resolve()

    if args.clean:
        return clean_output(root_dir)

    config = BuildConfig(
        arch=args.arch,
        build_type=args.build_type,
        macos_sdk=args.macos_sdk,
        root_dir=root_dir,
    )

    errors = config.validate()
    errors += check_cross_compile(config)
    if errors:
        for e in errors:
            print(f"Error: {e}", file=sys.stderr)
        return 1

    download_dir = resolve_download_dir(args.download_dir)
    gn_defines = build_gn_defines(config.platform_name)
    env = build_environment(config, gn_defines)

    print(f"\n{'=' * 60}")
    print(f"Building CEF for '{config.build_suffix}'")
    print(f"{'=' * 60}\n")
    print(f"  CEF branch    : {args.branch}")
    print(f"  Platform      : {config.platform_name} ({config.arch})")
    print(f"  Build type    : {config.build_type}")
    print(f"  Distribution  : {args.distrib}")
    print(f"  Download dir  : {download_dir}")
    print(f"  Output        : {cef_output_root(root_dir)}/cef_binary_<version>_{spotify_platform_token(config)}/  (Spotify layout)")
    print(f"\n  GN_DEFINES:\n    {gn_defines}\n")

    depot_tools = ensure_depot_tools(download_dir, env, args.dry_run)
    automate = ensure_automate_git(download_dir, args.dry_run)
    cmd = automate_git_command(automate, config, args, download_dir)

    print("depot_tools :", depot_tools)
    print("Command     :", " ".join(cmd))

    if args.dry_run:
        print("\nDry run — nothing built.")
        return 0

    print(f"\n{'=' * 60}\nRunning automate-git.py (this takes hours)\n{'=' * 60}\n")
    if subprocess.run(cmd, env=env).returncode != 0:
        print("\nError: automate-git.py failed.", file=sys.stderr)
        return 1

    distrib = locate_distribution(download_dir)
    if distrib is None:
        print(
            "\nError: no CEF binary distribution found under "
            f"{download_dir / 'chromium' / 'src' / 'cef' / 'binary_distrib'}.",
            file=sys.stderr,
        )
        return 1

    # CEF version = the distribution folder name with the 'cef_binary_' prefix and
    # the trailing platform tokens stripped (e.g. cef_binary_126.2.7+g...+chromium-126.0...._linux64).
    dist_dir = install_distribution(distrib, cef_output_root(root_dir), args.dry_run)
    archive_path = archive_dist(dist_dir, args.dry_run) if args.archive else None

    print(f"\n{'=' * 60}")
    print("CEF build completed successfully!")
    print(f"  Source      : {distrib}")
    print(f"  Dist folder : {dist_dir}  (Spotify-named: Release/Debug + shared dirs)")
    if archive_path:
        print(f"  Archive     : {archive_path}")
    print(f"{'=' * 60}\n")
    print(
        "The folder/archive name matches the Spotify CDN exactly "
        "(cef_binary_<version>_<platform>), so the app_system consumer only needs "
        "its CEF download base URL pointed at our GitHub release. For local dev, "
        "symlink the consumer's CEF path at the dist folder. Add --archive to "
        "produce the .tar.bz2 for publishing."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
