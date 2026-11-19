"""Check that every gclient dependency of the Chromium checkout sits on the commit DEPS asks for.

Why this exists: automate-git.py runs `gclient sync` only when the Chromium `src` commit
changes. A sync that dies part-way (an HTTP 429 from chromium.googlesource.com, a half-cloned
dependency) leaves `src` on the new tag while dozens of dependencies stay on the old version,
and every later run skips the sync because `src` already looks right. Seen on the CEF 156 bump
(2026-11-19): 45 dependencies (v8, skia, webrtc, vulkan-*, ...) on wrong commits and one
missing; CEF's own v8 patch was what stopped the build, by luck. Building such a tree mixes two
Chromium versions. The cure is `build_cef.py --force-update`; this check is what notices.

The comparison is `gclient revinfo` (path: url@sha, conditions already evaluated for this
host) against `git rev-parse HEAD` in each dependency. Entries whose revision is not a plain
40-hex commit (CIPD packages, GCS objects, the unmanaged `src` solution) are not git
checkouts pinned by DEPS and are skipped. Local modifications are NOT checked: CEF's own
patches legitimately modify some dependencies after the hooks run.

The same interrupted sync also leaves CIPD packages with files of their PREVIOUS version: the
new one is installed over the old directory and nothing removes what it no longer ships. On the
156 bump, Dawn's Go toolchain kept 834 Go 1.24-era files and the build died 25 s in
(`internal/abi/map_swiss.go: ctrlEmpty redeclared`, old and new sources compiled together);
mold, the JDK and typescript had leftovers too. So every CIPD package of the gclient root
(`chromium/.cipd/pkgs/<n>/`: `description.json` gives its directory, `_current` its installed
instance — a symlink on Linux/macOS, a `_current.txt` holding the instance id on Windows —
and `.cipdpkg/manifest.json` its file list) is checked for files that no manifest declares.
Ignored: `.git` directories, `__pycache__` directories (regenerated Python bytecode),
`.DS_Store` (written by the macOS Finder), and files git tracks (on Windows `third_party/wtl`,
`third_party/webview2` and `lzma_sdk/bin/*` are both CIPD directories and `chromium/src`
sources). Measured on a clean Linux 156 checkout: 31 packages, 0 such file. The Windows 156
run (2026-11-19) found the Go toolchain leftovers again (231 files per arch) once the
`_current.txt` layout was read: before that fix every Windows package was skipped silently,
so a package that cannot be read now fails the check.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

_REVINFO_LINE = re.compile(r"^(src[^:]*): (\S+)@([0-9a-f]{40})$")
_IGNORED_DIRS = {".git", "__pycache__"}
_IGNORED_FILES = {".DS_Store"}


def _norm(path: str) -> str:
    """Comparable form of a relative path (separators, and case on Windows)."""
    return os.path.normcase(os.path.normpath(path))


def _installed_manifest(pkg: Path) -> Path | None:
    """The manifest of the instance a CIPD package directory has installed.

    `_current` is a symlink to the instance directory on Linux and macOS; on Windows CIPD
    writes `_current.txt` instead, holding the instance id (the directory's name).
    """
    current = pkg / "_current"
    if not current.is_dir():
        pointer = pkg / "_current.txt"
        if not pointer.is_file():
            return None
        current = pkg / pointer.read_text().strip()
    manifest = current / ".cipdpkg" / "manifest.json"
    return manifest if manifest.is_file() else None


def _git_tracked(directory: Path) -> set[str] | None:
    """Files git tracks under `directory`, relative to it; None when it is in no repository."""
    result = subprocess.run(
        ["git", "-C", str(directory), "ls-files", "-z"], capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    return {_norm(name) for name in result.stdout.split("\0") if name}


def _stale_cipd_files(chromium_dir: Path) -> tuple[dict[str, list[str]], int, list[str]]:
    """Files under a CIPD package directory that no installed manifest declares, per directory.

    Also returns how many packages were read and the package directories that could not be
    (a silent skip once hid every package on Windows). Files git tracks are not leftovers:
    on Windows some package directories are shared with sources of `chromium/src`
    (`third_party/wtl`, `third_party/webview2`).
    """
    packages: list[tuple[str, set[str]]] = []
    unreadable: list[str] = []
    for pkg in sorted((chromium_dir / ".cipd" / "pkgs").glob("*")):
        if not pkg.is_dir():
            continue
        description = pkg / "description.json"
        manifest = _installed_manifest(pkg)
        if not description.is_file() or manifest is None:
            unreadable.append(pkg.name)
            continue
        subdir = _norm(json.loads(description.read_text())["subdir"])
        names = {f["name"] for f in json.loads(manifest.read_text())["files"]}
        packages.append((subdir, names))

    # Several packages may share a directory, and one may sit inside another's.
    declared = {_norm(os.path.join(sub, name)) for sub, names in packages for name in names}
    subdirs = {sub for sub, _ in packages}

    stale: dict[str, list[str]] = {}
    for subdir in sorted(subdirs):
        candidates: list[str] = []
        for dirpath, dirnames, filenames in os.walk(chromium_dir / subdir):
            rel_dir = os.path.relpath(dirpath, chromium_dir)
            # A nested package directory is walked on its own turn.
            dirnames[:] = [
                d for d in dirnames
                if d not in _IGNORED_DIRS and _norm(os.path.join(rel_dir, d)) not in subdirs
            ]
            for name in filenames:
                rel = _norm(os.path.join(rel_dir, name))
                if name not in _IGNORED_FILES and rel not in declared:
                    candidates.append(rel)
        if candidates:
            tracked = _git_tracked(chromium_dir / subdir) or set()
            left = [rel for rel in candidates if _norm(os.path.relpath(rel, subdir)) not in tracked]
            if left:
                stale[subdir] = left
    return stale, len(packages), unreadable


def verify_gclient_deps(download_dir: Path, env: dict[str, str], dry_run: bool = False) -> bool:
    """Print the dependencies off their DEPS commit or missing, and the CIPD leftovers.

    True when there is none of either.
    """
    chromium_dir = download_dir / "chromium"
    print(f"\n{'=' * 60}\nChecking gclient dependencies against DEPS\n{'=' * 60}\n")
    if dry_run:
        print("  [dry-run] gclient revinfo vs git rev-parse HEAD in each dependency;")
        print("  [dry-run] every CIPD package directory vs its installed manifest")
        return True

    gclient = shutil.which("gclient", path=env.get("PATH"))
    if gclient is None:
        print("  Error: gclient not found on PATH (depot_tools missing?).")
        return False

    result = subprocess.run(
        [gclient, "revinfo"], cwd=chromium_dir, env=env, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  Error: `gclient revinfo` failed:\n{result.stdout}{result.stderr}")
        return False

    checked = 0
    wrong: list[tuple[str, str, str]] = []
    missing: list[str] = []
    for line in result.stdout.splitlines():
        match = _REVINFO_LINE.match(line.strip())
        if not match:
            continue
        path, _url, expected = match.groups()
        head = subprocess.run(
            ["git", "-C", str(chromium_dir / path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        )
        checked += 1
        if head.returncode != 0:
            missing.append(path)
        elif head.stdout.strip() != expected:
            wrong.append((path, head.stdout.strip()[:12], expected[:12]))

    ok = True
    if not wrong and not missing:
        print(f"  {checked} dependencies, all on their DEPS commit.")
    else:
        ok = False
        for path, head, expected in wrong:
            print(f"  WRONG   {path}: at {head}, DEPS wants {expected}")
        for path in missing:
            print(f"  MISSING {path}")
        print(
            f"\n  {len(wrong)} of {checked} dependencies off their DEPS commit, {len(missing)} missing:\n"
            "  an earlier `gclient sync` did not finish, and automate-git.py never re-syncs once\n"
            "  `src` is on the right commit. Re-run with --force-update."
        )

    stale, read, unreadable = _stale_cipd_files(chromium_dir)
    if unreadable:
        ok = False
        print(
            f"  CIPD packages: {len(unreadable)} under .cipd/pkgs without a readable description.json or\n"
            f"  installed manifest ({', '.join(unreadable)}): unknown CIPD layout, the check cannot\n"
            "  vouch for them."
        )
    if not stale:
        print(f"  CIPD packages: {read} read, no file outside their manifests.")
    else:
        ok = False
        for subdir, files in stale.items():
            print(f"  STALE   {subdir}: {len(files)} file(s) in no CIPD manifest, e.g.")
            for rel in files[:3]:
                print(f"            {rel}")
        print(
            f"\n  {sum(len(f) for f in stale.values())} file(s) left by a previous version of these CIPD\n"
            "  packages (an interrupted sync installed the new version over the old one). Move\n"
            "  them out of the checkout, keeping their paths, then re-run: see AGENTS.md\n"
            "  § CEF, `--force-update`."
        )
    return ok
