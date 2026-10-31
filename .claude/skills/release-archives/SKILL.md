---
name: release-archives
description: How to build, verify and publish a set of ext-deps archives (a vNNN release) on Linux, macOS and Windows — the per-OS build traps, the checks every archive passes before upload, and the publish order. Load it before building a full configuration, before uploading anything to a GitHub release, and when a consumer reports a missing or broken library.
---

# Release archives — build, verify, publish

> Authoritative: `AGENTS.md` (build policy, Windows generator, CRT validation, post-build assertions, CEF).
> This skill is the ordered checklist plus the traps paid for on each OS.

## 1. Build
- One configuration at a time per machine; `--jobs` per `.claude/rules/working-here.md`.
- **Windows** (Git Bash + MSVC 14.44, French-only install: `VSLANG=1033` does nothing, cl/cmd print cp850): the builder
  handles the encoding; Python 3.15 runs in strict UTF-8 mode. Git Bash lacks `strings` and `zip` (use Python); set
  `MSYS_NO_PATHCONV=1` before passing `/p:` MSBuild arguments; MSYS2 lives in `C:\msys64`. On this box the
  downstream `dependencies/windows.*` trees link to `output/`: after a test build, restore them from the zips.
- **macOS**: activate the venv (`source .venv/bin/activate`) so `meson`/`ninja`/`cmake` are on PATH; never put
  Homebrew's GNU `libtool` first in PATH. Build arm64 and x86_64 for EACH deployment target (12.0 and 13.0).
- **Linux**: the build box depends on the release (rule `working-here.md`).

## 2. Verify every archive before upload
- `DependenciesTest` on every configuration (a `--no-deps` run skipped it). macOS x86_64 runs under Rosetta 2.
- Compare the produced file list with the previous archive of the same configuration: a missing library or header
  directory is a broken release even when everything links.
- Windows: the type-server scan of every shipped `.lib` (`/Z7` objects, no external PDB reference) — the check that
  counts (`AGENTS.md` § Windows generator).
- macOS: `vtool -show-build` on every library against the archive's sdk tag — a native Meson build once shipped
  harfbuzz at minos 27.0 instead of the target. NASM objects carry no version command: normal.
- Linux: the glibc floor of the configuration (`objdump -T … | grep GLIBC_`).

## 3. Publish
- Uploads to a GitHub release (`gh release …`) are outward-facing: the owner's explicit OK first, with the exact list
  of assets and the tag.
- A CEF archive rides as an annex asset on the current deps release; consumers then bump `CEF_DOWNLOAD_BASE_URL`.
- After publishing, the consumer's version stamp moves (base `cmake/InstallDependencies.cmake`): say so; never edit a
  consumer repository without the owner's request.
