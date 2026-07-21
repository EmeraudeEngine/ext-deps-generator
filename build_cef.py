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

Staying current: bump DEFAULT_CEF_BRANCH + DEFAULT_CEF_CHECKOUT (below) every
2-3 months to the current Spotify-CDN stable, re-run this script per platform,
publish the archive. The GN_DEFINES do not change across versions — only the
version pins do.

    Find the current stable branch:
      https://bitbucket.org/chromiumembedded/cef/wiki/BranchesAndBuilding.md
      https://cef-builds.spotifycdn.com/index.html   (branch = milestone)

Usage:
    python build_cef.py                                  # host platform, Release, x86_64
    python build_cef.py --branch 6478                    # target a specific CEF branch
    python build_cef.py --arch arm64 --macos-sdk 12.0    # macOS arm64
    python build_cef.py --arch both --macos-sdk 12.0     # macOS: arm64 THEN x86_64 (two distributions)
    python build_cef.py --build-type Debug               # debug distribution
    python build_cef.py --build-type Both                # Release + Debug in one run
    python build_cef.py --sync-only                      # update the checkout, build nothing
    python build_cef.py --distrib minimal                # smaller, ship-ready distribution
    python build_cef.py --download-dir /data/chromium    # where the ~100 GB checkout lives
    python build_cef.py --dry-run                         # print the plan, build nothing
    python build_cef.py --clean                           # remove the CEF output archives

CANNOT cross-compile Chromium: run this on the target OS (the one exception is
macOS x86_64/arm64 on an Apple-Silicon host). depot_tools is bootstrapped into
the download dir automatically if absent.

Download dir (the ~100 GB Chromium checkout + depot_tools + automate-git.py):
    --download-dir  >  $CEF_DOWNLOAD_DIR  >  <repo>/../cef-chromium
The default is a SIBLING of the repo (outside it), so it stays invisible to git and
to IDEs that would otherwise index the giant tree (CLion), and a `build.py --clean`
never reaches it.
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
# Pinned CEF version — the ONLY knobs to bump when staying current.
# ---------------------------------------------------------------------------
# Bump BOTH to the current Spotify-CDN stable on each refresh cycle (see the
# URLs in the module docstring). From a CDN version string such as
# `150.0.11+gb887805+chromium-150.0.7871.115`:
#   branch   = 3rd component of the Chromium version -> 7871
#   checkout = the CEF commit after '+g'             -> b887805
# Override per-run with --branch / --checkout.
#   7871 @ b887805 == CEF 150.0.11 / Chromium 150.0.7871.115 (CDN stable, 2026-07)
#   7827           == CEF 149 / Chromium 149 (previous anchor)
#   6478           == CEF 126 / Chromium 126 (mid-2024 anchor, kept for reference)
DEFAULT_CEF_BRANCH = "7871"
# Exact CEF commit within DEFAULT_CEF_BRANCH: pins the produced version string
# to the Spotify CDN artifact (the branch HEAD may have moved past it, which
# would yield a different cef_binary_<version> name). Only applied while
# --branch is left at its default; `--checkout head` unpins.
DEFAULT_CEF_CHECKOUT = "b887805"

# automate-git.py is fetched from the CEF repo (kept out of the checkout so a
# --force-clean of the Chromium tree never deletes our tooling).
AUTOMATE_GIT_URL = (
    "https://bitbucket.org/chromiumembedded/cef/raw/master/tools/automate/automate-git.py"
)
DEPOT_TOOLS_URL = "https://chromium.googlesource.com/chromium/tools/depot_tools.git"

# Default location for the ~100 GB Chromium checkout + depot_tools + automate-git.py:
# a sibling of the repo root (<repo>/../<CEF_CHECKOUT_DIRNAME>/). Living OUTSIDE the
# repo keeps it invisible to git (no .gitignore entry needed) and to IDEs that would
# otherwise try to index the giant tree (CLion), and puts it out of reach of
# `build.py --clean` (which only touches paths inside the repo) without special-casing.
# build.py still imports this name to preserve any legacy in-repo checkout under
# builds/. Overridable via --download-dir / $CEF_DOWNLOAD_DIR.
CEF_CHECKOUT_DIRNAME = "cef-chromium"


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
    "use_thin_lto": "false",     # custom-build friendly + faster (skips the slow, RAM-hungry LTO link)
    "is_cfi": "false",           # MUST accompany use_thin_lto=false: is_official_build enables CFI
                                 # by default on Linux x64/arm64, and compiler.gni asserts
                                 # `!is_cfi || use_thin_lto` (CFI requires ThinLTO). No-op on
                                 # Windows/macOS where CFI is already off.
    "chrome_pgo_phase": "0",     # no profile-guided optimization data for a custom build

    # --- Symbols: match the official/Spotify builds ---
    # Without it, is_official_build keeps full debug info (symbol_level=2):
    # multi-GB libcef.so, slow links — and gdb still struggled to symbolize it.
    # Level 1 = function-level symbols: small binary, fast link, backtraces
    # with function names. NOTE: GN_DEFINES apply to BOTH configs
    # (cef/tools/gn_args.py merges them before the per-config split), so the
    # Debug distribution also gets level 1 — identical to the official CDN
    # builds (DCHECKs + function names, not full debug info). Bump to 2 here
    # (one-off) if a full-symbol Debug build is ever needed.
    "symbol_level": "1",

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
        "--checkout",
        metavar="COMMIT",
        default=None,
        help=(
            "Exact CEF commit/tag to build (passed to automate-git.py --checkout). "
            f"Defaults to the pinned {DEFAULT_CEF_CHECKOUT} while --branch is left "
            "at its default, otherwise to the branch head. Pass 'head' to force "
            "the branch head explicitly."
        ),
    )
    parser.add_argument(
        "--arch",
        choices=["x86_64", "arm64", "both"],
        default="x86_64",
        help=(
            "Target architecture (default: x86_64). 'both' builds arm64 then "
            "x86_64 in sequence from the same checkout — macOS only (the sole "
            "supported Chromium cross-compile), yielding the two Spotify "
            "distributions (macosarm64 + macosx64)."
        ),
    )
    parser.add_argument(
        "--build-type",
        choices=["Release", "Debug", "Both"],
        default="Release",
        help=(
            "Build type (default: Release). 'Both' compiles Release AND Debug in a "
            "single automate-git.py run, yielding one distribution folder that "
            "already contains both subdirs (the complete Spotify layout)."
        ),
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
            "Defaults to $CEF_DOWNLOAD_DIR, then <repo>/../cef-chromium "
            "(a sibling of the repo: outside git, unseen by IDEs, untouched by `build.py --clean`)."
        ),
    )
    parser.add_argument(
        "--force-clean",
        action="store_true",
        help="Pass --force-clean to automate-git.py (wipe & re-fetch the Chromium tree).",
    )
    parser.add_argument(
        "--force-build",
        action="store_true",
        help=(
            "Pass --force-build to automate-git.py. Needed to build when the checkout "
            "already exists and is unchanged: automate-git.py otherwise no-ops the build "
            "AND the distribution (returning success with no binary_distrib) unless the "
            "source hashes changed. Use this to compile/re-compile an already-synced tree; "
            "building implies --force-distrib upstream."
        ),
    )
    parser.add_argument(
        "--build-target",
        metavar="NAME",
        default=None,
        help=(
            "Ninja target passed to automate-git.py's --build-target. Defaults to "
            "'cefsimple' on Linux (cefclient needs GTK, unavailable in the sysroot "
            "we build against) and to automate-git.py's own default ('cefclient') "
            "elsewhere. Either way libcef + the wrapper are built, which is all the "
            "binary distribution needs."
        ),
    )
    parser.add_argument(
        "--sync-only",
        action="store_true",
        help=(
            "Update the CEF/Chromium checkout to the pinned version and exit "
            "(passes --no-build --no-distrib to automate-git.py). Useful to "
            "refresh the tree or regenerate the seed tar without compiling."
        ),
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


def resolve_download_dir(arg: str | None, root_dir: Path) -> Path:
    """--download-dir > $CEF_DOWNLOAD_DIR > <repo>/../cef-chromium.

    The default lives *beside* the repo (a sibling directory), not inside it. An
    earlier iteration kept it under <repo>/builds/ (git-ignored), but IDEs such as
    CLion still try to index the ~100 GB Chromium tree when it sits inside the
    project. Placing it outside the repo keeps it invisible to git and to the IDE,
    and puts it out of reach of `build.py --clean` (which only ever touches paths
    inside the repo) with no special-casing. Use `--download-dir` / $CEF_DOWNLOAD_DIR
    to place it elsewhere (e.g. a bigger disk).
    """
    if arg:
        return Path(arg).expanduser().resolve()
    env = os.environ.get("CEF_DOWNLOAD_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return (root_dir.parent / CEF_CHECKOUT_DIRNAME).resolve()


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


def check_download_dir(arg: str | None, download_dir: Path) -> list[str]:
    """Refuse to bootstrap a checkout at a dead explicit path.

    When --download-dir/$CEF_DOWNLOAD_DIR points somewhere that does not exist
    AND whose parent does not exist either, the most likely cause is an
    unmounted removable disk (the mount point only exists while mounted).
    Blindly mkdir-ing would silently start a fresh ~100 GB checkout on the
    wrong disk, so explicit locations require an existing parent. The default
    sibling-of-repo location keeps its bootstrap behavior.
    """
    explicit = bool(arg or os.environ.get("CEF_DOWNLOAD_DIR"))
    if not explicit or download_dir.exists() or download_dir.parent.exists():
        return []
    return [
        f"Download dir '{download_dir}' does not exist, nor does its parent. "
        "If the checkout lives on a removable disk, mount it first (e.g. "
        "`udisksctl mount -b /dev/disk/by-label/CEF-LINUX`); otherwise create "
        "the parent directory. Refusing to start a fresh checkout at a dead path."
    ]


def confirm_bootstrap(download_dir: Path, dry_run: bool) -> bool:
    """Warn — and prompt on a TTY — before starting a brand-new checkout.

    Forgetting CEF_DOWNLOAD_DIR (checkout on an unmounted/unexported external
    disk) silently falls back to the default path and kicks off a fresh
    ~100 GB Chromium download. An existing checkout passes straight through;
    automation (no TTY) proceeds too, with the warning in the log.
    """
    if (download_dir / "automate-git.py").exists() or (download_dir / "chromium").exists():
        return True
    print(f"\nWARNING: no existing checkout under {download_dir}")
    print("A FRESH Chromium checkout (~100 GB download, hours of sync) will be bootstrapped there.")
    print("If your checkout lives elsewhere (external disk?), set CEF_DOWNLOAD_DIR or --download-dir.")
    if dry_run or not sys.stdin.isatty():
        return True
    return input("Continue? [y/N] ").strip().lower() in ("y", "yes")


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
        # Only GN-gen the configs we build. Without this, CEF's gclient_hook
        # also generates the x86 configs, whose `gn gen` fails unless the SDK's
        # x86 "Debugging Tools for Windows" (dbghelp.dll) are installed.
        cpu = "arm64" if config.arch == "arm64" else "x64"
        env.setdefault("GN_OUT_CONFIGS", f"Debug_GN_{cpu},Release_GN_{cpu}")
    elif config.platform_name == "macos":
        if config.macos_sdk:
            env["MACOSX_DEPLOYMENT_TARGET"] = config.macos_sdk
        # CEF's gn_args.py generates GN configs only for the HOST cpu by default
        # (machine == 'arm64' on Apple Silicon), so cross-compiling the other
        # arch needs CEF_ENABLE_{AMD64,ARM64}=1 to make it a "supported_cpu" —
        # otherwise gclient_hook never writes out/Debug_GN_x64/args.gn and
        # automate-git.py dies reading it. GN_OUT_CONFIGS then restricts gn gen
        # to just the target configs (skips a wasteful gen of the host arch).
        cpu = "arm64" if config.arch == "arm64" else "x64"
        env.setdefault("GN_OUT_CONFIGS", f"Debug_GN_{cpu},Release_GN_{cpu}")
        env.setdefault("CEF_ENABLE_ARM64" if cpu == "arm64" else "CEF_ENABLE_AMD64", "1")

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
    automate: Path,
    config: BuildConfig,
    args: argparse.Namespace,
    download_dir: Path,
    subsequent: bool = False,
) -> list[str]:
    """Assemble the automate-git.py invocation.

    `subsequent` marks the 2nd+ run over the same checkout in one invocation
    (--arch both): the sync already happened, so the update phase is skipped
    and the build forced (unchanged hashes would otherwise no-op it).
    """
    cmd = [
        sys.executable,
        str(automate),
        f"--download-dir={download_dir}",
        f"--branch={args.branch}",
    ]

    # Exact CEF commit pin — keeps the produced cef_binary_<version> name
    # identical to the Spotify CDN artifact. The default pin belongs to the
    # default branch, so it is dropped when --branch is overridden without a
    # matching --checkout (the Chromium version follows the CEF commit via
    # CHROMIUM_BUILD_COMPATIBILITY.txt either way).
    checkout = args.checkout
    if checkout is None and args.branch == DEFAULT_CEF_BRANCH:
        checkout = DEFAULT_CEF_CHECKOUT
    if checkout and checkout.lower() != "head":
        cmd.append(f"--checkout={checkout}")

    # Build type: automate-git.py builds BOTH Release and Debug by default;
    # restrict unless 'Both' was requested (then neither flag is passed).
    if args.build_type == "Release":
        cmd.append("--no-debug-build")
    elif args.build_type == "Debug":
        cmd.append("--no-release-build")

    # Architecture flag.
    cmd.append("--arm64-build" if config.arch == "arm64" else "--x64-build")

    # Distribution flavor.
    if args.distrib == "minimal":
        cmd.append("--minimal-distrib")
    elif args.distrib == "client":
        cmd.append("--client-distrib")
    # 'standard' -> automate produces the standard distribution by default.

    # Build target. automate-git.py defaults to 'cefclient', but on Linux that
    # sample #includes <gtk/gtk.h> unconditionally (cef_paths2.gypi bundles the
    # *_gtk.cc files into cefclient_sources_linux) while CEF sets
    # `cef_use_gtk = !use_sysroot` — so with our mandatory use_sysroot=true the
    # GTK include/link config is never added and cefclient fails to compile.
    # 'cefsimple' (X11-only, no GTK) still pulls in libcef + the wrapper, which
    # is all the binary distribution needs. Let the caller override either way.
    target = args.build_target
    if target is None and config.platform_name == "linux":
        target = "cefsimple"
    if target is not None:
        cmd.append(f"--build-target={target}")

    if args.force_clean:
        cmd.append("--force-clean")

    if args.force_build or subsequent:
        cmd.append("--force-build")

    if subsequent:
        # The previous arch's run just synced this checkout; skip the whole
        # update phase (git fetch / gclient revert+sync / hooks) outright.
        cmd.append("--no-update")

    if args.sync_only:
        # Update the checkout only: no compile, no distribution.
        cmd += ["--no-build", "--no-distrib"]

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

    # 'both' = arm64 then x86_64 from the same checkout (two automate-git runs,
    # two Spotify distributions). Native arch first on Apple Silicon.
    archs = ["arm64", "x86_64"] if args.arch == "both" else [args.arch]

    # BuildConfig only knows Release/Debug and a single arch (the static-lib
    # grammar); stand-ins pass validation — the real build-type/arch selection
    # happens in automate_git_command(), which reads args directly.
    configs = [
        BuildConfig(
            arch=arch,
            build_type="Release" if args.build_type == "Both" else args.build_type,
            macos_sdk=args.macos_sdk,
            root_dir=root_dir,
        )
        for arch in archs
    ]

    download_dir = resolve_download_dir(args.download_dir, root_dir)

    errors: list[str] = []
    for cfg in configs:
        errors += cfg.validate()
        errors += check_cross_compile(cfg)
    errors += check_download_dir(args.download_dir, download_dir)
    if args.arch == "both" and configs[0].platform_name != "macos":
        errors.append(
            "--arch both is only supported on macOS (Apple Silicon), the sole "
            "platform where Chromium can cross-compile the second arch."
        )
    if args.sync_only and (args.force_build or args.archive):
        errors.append("--sync-only builds nothing: it cannot be combined with --force-build or --archive.")
    if args.sync_only and args.arch == "both":
        errors.append("--sync-only syncs the shared checkout once: use it with a single --arch.")
    if errors:
        # Both configs can yield the same error: dedupe, preserving order.
        for e in dict.fromkeys(errors):
            print(f"Error: {e}", file=sys.stderr)
        return 1

    gn_defines = build_gn_defines(configs[0].platform_name)
    env = build_environment(configs[0], gn_defines)

    build_type_display = (
        "Release + Debug" if args.build_type == "Both" else args.build_type
    )
    arch_display = " + ".join(archs)
    print(f"\n{'=' * 60}")
    print(f"Building CEF {args.branch} for {configs[0].platform_name}.{arch_display} ({build_type_display})")
    print(f"{'=' * 60}\n")
    print(f"  CEF branch    : {args.branch}")
    print(f"  Platform      : {configs[0].platform_name} ({arch_display})")
    print(f"  Build type    : {build_type_display}")
    print(f"  Distribution  : {args.distrib}")
    print(f"  Download dir  : {download_dir}")
    for cfg in configs:
        print(f"  Output        : {cef_output_root(root_dir)}/cef_binary_<version>_{spotify_platform_token(cfg)}/  (Spotify layout)")
    print(f"\n  GN_DEFINES:\n    {gn_defines}\n")

    if not confirm_bootstrap(download_dir, args.dry_run):
        print("Aborted — nothing downloaded.")
        return 1

    depot_tools = ensure_depot_tools(download_dir, env, args.dry_run)
    automate = ensure_automate_git(download_dir, args.dry_run)
    print("depot_tools :", depot_tools)

    results: list[tuple[Path, Path | None]] = []
    for i, cfg in enumerate(configs):
        cmd = automate_git_command(automate, cfg, args, download_dir, subsequent=(i > 0))
        print("Command     :", " ".join(cmd))

        if args.dry_run:
            continue

        step = "sync only" if args.sync_only else "this takes hours"
        print(f"\n{'=' * 60}\nRunning automate-git.py for {cfg.arch} ({step})\n{'=' * 60}\n")
        if subprocess.run(cmd, env=env).returncode != 0:
            print("\nError: automate-git.py failed.", file=sys.stderr)
            return 1

        if args.sync_only:
            print(f"\n{'=' * 60}")
            print("Checkout synced — nothing built (--sync-only).")
            print(f"  Checkout : {download_dir}")
            print(f"{'=' * 60}\n")
            return 0

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
        results.append((dist_dir, archive_path))

    if args.dry_run:
        print("\nDry run — nothing built.")
        return 0

    print(f"\n{'=' * 60}")
    print("CEF build completed successfully!")
    for dist_dir, archive_path in results:
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
