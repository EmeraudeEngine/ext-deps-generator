"""
Local source patches applied to the Chromium/CEF tree before building.

Why this module exists
---------------------
The CEF distribution we ship is a source build (see `build_cef.py`'s module
docstring for the GN-args rationale). On top of those GN args, a handful of
*source* fixes are required -- in Chromium itself, or in one of its vendored
dependencies such as ANGLE.

Historically those fixes were bare working-tree edits: nothing recorded them,
nothing verified them, and a `gclient revert` dropped them silently. The build
still succeeded, the archive still shipped, and the regression only surfaced in
the field weeks later. That failure mode is the entire reason this module
exists.

Every such fix now lives as a patch file under `patches/chromium/`, versioned in
this repository, applied here, and guarded by a `# target-commit:` annotation so
that a source-revision drift is a **hard build error** instead of a silent
no-op.

Patch file format
-----------------
A `# key: value` preamble, then a `-p0` diff (no `a/` / `b/` path prefixes --
the convention CEF's own patcher uses; produce one with
`git diff --no-prefix -- <path>`):

    # target-dir: third_party/angle     optional, relative to chromium/src (default '.')
    # target-commit: 25f5b661e5b08      REQUIRED: HEAD of the target repo when authored
    # description: one-line summary     optional, shown while applying
    #
    # Free-form rationale, re-verification recipe, links...
    diff --git base/foo.cc base/foo.cc
    ...

Where this runs in the build
----------------------------
`automate-git.py` performs an *update* phase (git fetch, `gclient revert` +
sync, CEF's own patch step, hooks) and then a *build* phase within the same
invocation. `gclient revert` wipes local modifications, so the only correct
seam is *between* the two. That is why `build_cef.py` splits the run in two
whenever patches are present: update, patch, then build with `--no-update`.

Relationship to `PatchManager` (cmake_builder.py)
-------------------------------------------------
Same `# target-commit:` discipline, deliberately stricter on two points, because
the target here is a 100 GB external checkout rather than a vendored submodule:

* **Idempotence is content-based** (`git apply --reverse --check`), never a
  `.patch_applied` marker file. A marker survives the `gclient revert` that
  removes the edit, so a marker-based check would skip a patch that is no longer
  applied -- reintroducing the exact silent-loss bug.
* **A patch that fails to apply is fatal.** `PatchManager` treats an apply
  failure as "may already be applied" and continues; here, building on an
  unpatched tree means shipping the bugs these patches fix.
"""

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Sub-directory of <repo>/patches/ holding the Chromium-tree patches. Kept
# separate from the flat library patches: those are looked up by library name
# (`patches/<lib>.patch`), these are discovered by globbing, and the two must
# never collide.
PATCH_SUBDIR = "chromium"

_HEADER_RE = re.compile(r"^#\s*(target-dir|target-commit|description)\s*:\s*(.+?)\s*$")

# Reading the preamble stops at the first line that belongs to the diff itself.
_DIFF_MARKERS = ("diff ", "--- ", "+++ ", "@@ ", "index ")


@dataclass(frozen=True)
class ChromiumPatch:
    """One patch file plus its parsed preamble."""

    path: Path
    target_dir: str
    target_commit: str | None
    description: str

    @property
    def name(self) -> str:
        return self.path.stem

    @property
    def label(self) -> str:
        return self.description or self.name


def _parse_headers(patch_file: Path) -> dict[str, str]:
    """Pull the `# key: value` preamble out of a patch file."""
    headers: dict[str, str] = {}
    with patch_file.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith(_DIFF_MARKERS):
                break
            match = _HEADER_RE.match(line.rstrip("\n"))
            if match and match.group(1) not in headers:
                headers[match.group(1)] = match.group(2)
    return headers


def discover_patches(root_dir: Path) -> list[ChromiumPatch]:
    """Return every patch under `patches/chromium/`, sorted by filename.

    Filenames drive the apply order, so a prefix (`10-`, `20-`) can be used if
    two patches ever have to touch the same file.
    """
    patches_dir = root_dir / "patches" / PATCH_SUBDIR
    if not patches_dir.is_dir():
        return []

    patches = []
    for path in sorted(patches_dir.glob("*.patch")):
        headers = _parse_headers(path)
        patches.append(
            ChromiumPatch(
                path=path,
                target_dir=headers.get("target-dir", "."),
                target_commit=headers.get("target-commit"),
                description=headers.get("description", ""),
            )
        )
    return patches


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def _head_commit(repo: Path) -> str | None:
    """HEAD SHA of the git repo at `repo`, or None if it is not one."""
    try:
        result = _git(["rev-parse", "HEAD"], repo)
    except FileNotFoundError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _commits_match(target: str, actual: str) -> bool:
    # Either SHA may be abbreviated; accept when one is a prefix of the other.
    return actual.startswith(target) or target.startswith(actual)


def apply_patch(patch: ChromiumPatch, chromium_src: Path) -> bool:
    """Apply one patch. Returns False on any anomaly -- the caller must abort."""
    target = (chromium_src / patch.target_dir).resolve()

    if not target.is_dir():
        print(
            f"  Error: patch '{patch.name}' declares target-dir "
            f"'{patch.target_dir}', which does not exist under {chromium_src}.",
            file=sys.stderr,
        )
        return False

    if patch.target_commit is None:
        print(
            f"  Error: patch '{patch.name}' has no '# target-commit:' header.\n"
            f"    Every Chromium-tree patch must declare the revision it was\n"
            f"    authored against, so that a source drift fails the build instead\n"
            f"    of applying with subtly wrong semantics. See\n"
            f"    patches/{PATCH_SUBDIR}/README.md.",
            file=sys.stderr,
        )
        return False

    head = _head_commit(target)
    if head is None:
        print(
            f"  Error: '{target}' is not a git repository -- cannot verify the\n"
            f"    target commit of patch '{patch.name}'.",
            file=sys.stderr,
        )
        return False

    if not _commits_match(patch.target_commit, head):
        print(
            f"  Error: patch '{patch.name}' targets commit "
            f"{patch.target_commit[:12]} but '{patch.target_dir}' is at "
            f"{head[:12]}.\n"
            f"    The source moved since the patch was authored. Re-verify that\n"
            f"    the fix is still needed AND still correct against the current\n"
            f"    source, regenerate the diff with `git diff --no-prefix`, then\n"
            f"    update the '# target-commit:' line.\n"
            f"    Do not bypass this check by deleting the patch: shipping without\n"
            f"    it, silently, is the exact failure this guard exists to prevent.",
            file=sys.stderr,
        )
        return False

    # Content-based idempotence: if the reverse patch would apply, the change is
    # already in the tree. Deliberately not a marker file -- see the module
    # docstring.
    if _git(["apply", "-p0", "--reverse", "--check", str(patch.path)], target).returncode == 0:
        print(f"  Already applied : {patch.label}")
        return True

    check = _git(["apply", "-p0", "--check", str(patch.path)], target)
    if check.returncode != 0:
        print(
            f"  Error: patch '{patch.name}' does not apply to "
            f"'{patch.target_dir}', and is not already applied.\n"
            f"{check.stderr.rstrip()}",
            file=sys.stderr,
        )
        return False

    result = _git(["apply", "-p0", str(patch.path)], target)
    if result.returncode != 0:
        print(
            f"  Error: applying patch '{patch.name}' failed.\n{result.stderr.rstrip()}",
            file=sys.stderr,
        )
        return False

    print(f"  Applied         : {patch.label}")
    return True


def apply_all(root_dir: Path, download_dir: Path, dry_run: bool = False) -> bool:
    """Apply every `patches/chromium/*.patch` to the checkout under `download_dir`.

    Returns False if any patch could not be applied. Every patch is attempted
    even after a failure, so one run surfaces every problem at once.
    """
    patches = discover_patches(root_dir)
    if not patches:
        return True

    print(f"\n{'=' * 60}")
    print(f"Local Chromium patches ({len(patches)})")
    print(f"{'=' * 60}\n")

    if dry_run:
        for patch in patches:
            commit = (patch.target_commit or "<unguarded>")[:12]
            print(f"  [dry-run] {patch.name} -> {patch.target_dir} @ {commit}")
        return True

    chromium_src = download_dir / "chromium" / "src"
    if not chromium_src.is_dir():
        print(
            f"  Error: no Chromium checkout at {chromium_src}.", file=sys.stderr
        )
        return False

    # Do not short-circuit: report every failing patch in a single run.
    return all([apply_patch(patch, chromium_src) for patch in patches])
