---
id: stale-patch-applied-marker
title: A stale .patch_applied marker makes the builder skip a changed patch, silently
status: open
priority: high
scope: builder/cmake_builder.py (PatchManager), every patched library on every build machine
opened: 2026-10-20
tags: [builder, patches, release]
---

# A stale `.patch_applied` marker makes the builder skip a changed patch, silently

## Why

`PatchManager.apply_patch()` returns at once when `<source>/.patch_applied` exists, and the marker survives between
builds (nothing reverts the patch after a build). A patch CHANGED since the machine's last build is therefore never
applied: the library is built from the old patched state. The fallback is silent too: when `git apply --check` fails
("may already be applied") the function returns success without an error.

Met during the v019 build (2026-10-20, found by the glibc 2.43 builder): `bc7enc_rdo` (rgbcx added to its patch) and
`tinyusdz` (the fuzzing fixes) still carried their v018 patches under a marker — built as is, v019 would have lacked
rgbcx and the fixes, with no error. `clipper2` had a marker WITHOUT its patch applied (the patch only drops `-Werror`,
the output was unaffected). Each machine was corrected by hand (reverse the old patch exactly, remove the marker).

The second hole (macOS peer, same day): `cmake_builder.py` returns `True` on a failed forward `--check` ("may already be
applied"), so a tree holding an OLD version of a patch WITHOUT a marker is built silently unpatched as well. Only a
content-based check closes both: the CURRENT patch must reverse-check (already applied) or forward-check (then apply);
anything else is an error — the way `chromium_patches.py` already decides.

The v019 machines (2026-10-20): Linux glibc 2.41 — every marked patch current, clipper2 stale (left); glibc 2.43 —
bc7enc_rdo and tinyusdz reversed from v018 by hand, clipper2 stale marker removed; Windows and macOS — the changed
patches had no marker (applied fresh), clipper2 stale marker removed; glibc 2.35 VM — bc7enc_rdo and tinyusdz reversed
from v018, lib3mf carried an even OLDER patch (4997f18, 2026-07-07: v018's own GCC 15 version never reached that tree)
and was reversed from it, clipper2 stale marker removed. One machine can thus lag by several patch versions: reversing
"the previous release's patch" is not enough, the applied version must be FOUND (a recorded hash would say it).

## What remains

- A builder fix (owner's decision): decide by CONTENT, not by the marker — reverse-check the current patch (applied:
  skip), else forward-check (apply), else an ERROR naming the library; optionally the marker records the hash of the
  patch it applied, to reverse an older one automatically.
- Until then, before a release build: for every `patches/<lib>.patch` whose source has a marker, `git apply --reverse
  --check` of the CURRENT patch must pass (else reverse the old one and remove the marker).

## References

- `builder/cmake_builder.py` `PatchManager.apply_patch()` / `revert_patch()`.
