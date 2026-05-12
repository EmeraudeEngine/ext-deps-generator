#!/usr/bin/env python3
"""Read-only check: compare each submodule's pinned commit with upstream release tags.

For each submodule listed in .gitmodules, query the remote for tags, filter out
pre-release markers (alpha/beta/rc/pre/dev/snapshot/nightly), and report whether
a newer stable tag is available.

Nothing is modified. Use this to decide which libraries to update manually.
"""

from __future__ import annotations

import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


PRERELEASE_RE = re.compile(
    r"(?i)(alpha|beta|rc\d|[\-_]pre\b|[\-_]dev\b|snapshot|nightly|draft|fuzz|corpora|experimental|wip|test\b)"
)
# Last numeric component starting with 9 (e.g. ".90", ".91"). Several projects
# (libjpeg-turbo, mpg123, …) use this as a dev/odd-version convention meaning
# "in development toward the next stable minor", so treat them as pre-release.
DEV_MINOR_RE = re.compile(r"\.9\d+(?:\D|$)")
VERSION_PART_RE = re.compile(r"\d+")
# Anything before the first digit in a tag (e.g. "v", "VER-", "Clipper2_", "")
PREFIX_RE = re.compile(r"^([^\d]*)")


def parse_gitmodules(path: Path) -> dict[str, str]:
    """Return {submodule_path: url} from a .gitmodules file."""
    modules: dict[str, str] = {}
    cur_path: str | None = None
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if line.startswith("path"):
            cur_path = line.split("=", 1)[1].strip()
        elif line.startswith("url") and cur_path:
            modules[cur_path] = line.split("=", 1)[1].strip()
            cur_path = None
    return modules


def version_key(tag: str) -> tuple[int, ...]:
    """Sortable key for a version-like tag. Unparseable tags sort lowest."""
    stripped = tag.lstrip("vV")
    parts = VERSION_PART_RE.findall(stripped)
    return tuple(int(p) for p in parts) if parts else (-1,)


def remote_stable_tags(url: str) -> list[str]:
    """Return remote tag names with pre-release markers filtered out."""
    try:
        out = subprocess.check_output(
            ["git", "ls-remote", "--tags", "--refs", url],
            stderr=subprocess.DEVNULL,
            timeout=45,
            text=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return []
    tags: list[str] = []
    for line in out.splitlines():
        if "\t" not in line:
            continue
        _, ref = line.split("\t", 1)
        tag = ref.removeprefix("refs/tags/")
        if PRERELEASE_RE.search(tag) or DEV_MINOR_RE.search(tag):
            continue
        tags.append(tag)
    # Sort by version, then prefer the shorter/cleaner tag (no extra suffix)
    return sorted(tags, key=lambda t: (version_key(t), -len(t)))


SIMPLE_VERSION_RE = re.compile(r"^v?\d+(\.\d+)+")


def submodule_state(sub_dir: Path) -> tuple[str | None, str | None]:
    """Return (exact_tag_or_None, sha) for a submodule, or (None, None) if unavailable.

    When several tags point at the same commit, prefer a clean version tag
    (e.g. `v1.1.0`) over a sub-product variant (e.g. `go/cbrotli/v1.1.0`).
    """
    if not sub_dir.exists():
        return None, None
    try:
        sha = subprocess.check_output(
            ["git", "-C", str(sub_dir), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except subprocess.CalledProcessError:
        return None, None
    try:
        out = subprocess.check_output(
            ["git", "-C", str(sub_dir), "tag", "--points-at", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return None, sha
    tags_at_head = [t for t in out.splitlines() if t.strip()]
    if not tags_at_head:
        return None, sha
    # On ties, prefer the shorter/cleaner tag (no suffix like "_DLL" or "_bcr.1")
    sort_key = lambda t: (version_key(t), -len(t))
    simple = [t for t in tags_at_head if SIMPLE_VERSION_RE.match(t)]
    if simple:
        return sorted(simple, key=sort_key)[-1], sha
    return sorted(tags_at_head, key=sort_key)[-1], sha


def tag_prefix(tag: str) -> str:
    """Return the non-numeric prefix of a tag ('v1.3.6' -> 'v', '1.5.0' -> '')."""
    m = PREFIX_RE.match(tag)
    return m.group(1) if m else ""


def evaluate(name: str, sub_dir: Path, url: str) -> tuple[str, str, str, str]:
    """Return (name, current, latest, status) for a library row."""
    cur_tag, cur_sha = submodule_state(sub_dir)
    if cur_sha is None:
        return name, "?", "?", "submodule not initialized"

    all_tags = remote_stable_tags(url)
    if not all_tags:
        return name, cur_tag or cur_sha[:8], "-", "no release tags upstream"

    # If we have a current tag, only compare against tags sharing its prefix
    # (avoids picking unrelated tag families like "draft-N" or "jpeg-10").
    if cur_tag is not None:
        prefix = tag_prefix(cur_tag)
        same_family = [t for t in all_tags if tag_prefix(t) == prefix]
        candidates = same_family or all_tags
    else:
        candidates = all_tags

    latest = candidates[-1]
    current_label = cur_tag or f"{cur_sha[:8]} (branch)"

    if cur_tag is None:
        return name, current_label, latest, f"on branch — latest tag is {latest}"
    if cur_tag == latest or version_key(latest) == version_key(cur_tag):
        return name, current_label, latest, "up to date"
    if version_key(latest) > version_key(cur_tag):
        return name, current_label, latest, f"UPDATE available: {cur_tag} -> {latest}"
    return name, current_label, latest, f"ahead of latest tag ({cur_tag} > {latest})"


def main() -> int:
    root = Path(__file__).parent.resolve()
    gitmodules = root / ".gitmodules"
    if not gitmodules.exists():
        print("Error: .gitmodules not found", file=sys.stderr)
        return 1

    modules = parse_gitmodules(gitmodules)
    if not modules:
        print("No submodules found in .gitmodules", file=sys.stderr)
        return 1

    print(f"Checking {len(modules)} submodules against upstream tags...\n")

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [
            pool.submit(evaluate, Path(p).name, root / p, u)
            for p, u in modules.items()
        ]
        rows = [f.result() for f in futures]

    rows.sort(key=lambda r: r[0])
    nw = max(len(r[0]) for r in rows)
    cw = max(len(r[1]) for r in rows)
    lw = max(len(r[2]) for r in rows)

    print(f"{'lib':<{nw}}  {'current':<{cw}}  {'latest':<{lw}}  status")
    print(f"{'-' * nw}  {'-' * cw}  {'-' * lw}  {'-' * 40}")
    update_count = 0
    for name, current, latest, status in rows:
        print(f"{name:<{nw}}  {current:<{cw}}  {latest:<{lw}}  {status}")
        if status.startswith("UPDATE"):
            update_count += 1

    print(f"\n{update_count} update(s) available.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
