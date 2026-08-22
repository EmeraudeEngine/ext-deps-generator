# Local patches to the Chromium/CEF source tree

Every patch in this directory is applied to the Chromium checkout by
[`builder/chromium_patches.py`](../../builder/chromium_patches.py) during
`build_cef.py`, between automate-git's *update* and *build* phases.

They are **not** the same thing as the flat `patches/*.patch` files one level up:
those are looked up by library name and applied to vendored submodules by
`PatchManager` (`builder/cmake_builder.py`). These target the ~100 GB external
Chromium checkout instead, and are discovered by globbing this directory.

## Why they are files and not working-tree edits

Before this directory existed, these fixes were bare edits in the checkout.
Nothing recorded them, nothing verified them, and a `gclient revert` dropped
them silently — the build still succeeded, the archive still shipped, and the
regression resurfaced in the field weeks later. That is the failure mode this
mechanism removes:

| | bare edit | patch file here |
|---|---|---|
| Survives a fresh checkout | no, silently | yes |
| Survives `gclient revert` | no, silently | yes (re-applied every build) |
| Source drift detected | no | **hard build error** |
| Rationale recorded | in nobody's memory | in the patch preamble |
| Reviewable / diffable | no | yes, in git |

## File format

A `# key: value` preamble, then a `-p0` diff (no `a/` / `b/` prefixes — the same
convention CEF's own patcher uses):

```
# target-dir: third_party/angle     optional, relative to chromium/src (default '.')
# target-commit: 8d3c5a8caebd       REQUIRED — HEAD of the target repo when authored
# description: one-line summary     optional, shown while applying
#
# Free-form rationale: why it is needed, what breaks without it, how to
# re-verify it on the shipped binary, links to the consumer-side docs.
diff --git base/foo.cc base/foo.cc
...
```

Produce the diff with `--no-prefix`, never by hand:

```bash
cd <checkout>/chromium/src
git diff --no-prefix -- path/to/file.cc >> ../../../patches/chromium/my-fix.patch
```

Filenames drive the apply order (sorted), so prefix them (`10-`, `20-`) if two
patches ever touch the same file.

## The `# target-commit:` guard

This is the whole point. On every build the applier compares the header against
the target repo's actual `HEAD`:

- **Match** → apply (or report "already applied" — the check is content-based,
  via `git apply --reverse --check`, never a marker file).
- **Mismatch** → **the build fails** with the two SHAs and what to do.
- **Header absent** → the build fails too. An unguarded patch is precisely what
  we are getting rid of.

When the guard fires after a CEF version bump, the correct move is never to
delete the patch. It is to re-verify that the fix is *still needed* and *still
correct* against the new source, regenerate the diff, and update the SHA.

## Current patches

| File | Target | Platform | Summary |
|---|---|---|---|
| `mallinfo-overflow.patch` | `.` (Chromium) | Linux only | Legacy glibc `struct mallinfo` has `int` fields; past 2 GiB of renderer heap they wrap negative and `checked_cast<size_t>` CHECK-fails on a bare `ud2` — a silent SIGILL with no log line in an official build. Saturate instead. |
| `angle-max-texture-bytes.patch` | `third_party/angle` | all | ANGLE refuses any *single* texture/renderbuffer allocation over `Limitations::maxTextureBytes` (1 GiB) with `GL_INVALID_OPERATION` while every declared capability still reports support. The slicer's HD AA path crosses it (1.19 GiB, 1.76 GiB on a 16K plate), every layer renders black and an empty print file is written. Raised to 2 GiB. |

## Regenerating the ANGLE patch

Two hunks, and the second one is easy to drop by mistake:

- `src/libANGLE/Caps.h` — `Limitations::maxTextureBytes`. Covers D3D11 (Windows)
  and Metal (macOS), which declare no native override.
- `src/libANGLE/renderer/vulkan/vk_renderer.cpp` — `kMemoryAllocationSizeLimit`.
  **Required for Linux to move at all**: the Vulkan backend overwrites the
  `Caps.h` default unconditionally in `vk_caps_utils.cpp` with
  `min(maintenance3.maxMemoryAllocationSize, kMemoryAllocationSizeLimit)`. Note
  the effective ceiling stays driver-dependent there — the Vulkan spec only
  requires drivers to report 1 GiB, though desktop drivers report far more.

```bash
cd <checkout>/chromium/src/third_party/angle
# edit both files, then:
git diff --no-prefix -- src/libANGLE/Caps.h \
    src/libANGLE/renderer/vulkan/vk_renderer.cpp \
    >> ../../../../patches/chromium/angle-max-texture-bytes.patch
```

Upstream is moving on this, so expect the guard to fire on a CEF bump: the
1 -> 1.25 GiB bump (ANGLE `8e69854ca6`) first appears in `chromium/7926`, missing
the M151 branch point by four revisions, and it raises **only** `Caps.h`. On M152
(`chromium/7977`) the effective ceiling is therefore 1.25 GiB on Windows/macOS
and an unchanged 1 GiB on Linux — which clears neither a 16K plate nor, with any
real margin, the case that surfaced this. Re-verify, do not assume the bump fixed
it. The patch preamble carries the full reasoning, including why 2 GiB and not
more.
