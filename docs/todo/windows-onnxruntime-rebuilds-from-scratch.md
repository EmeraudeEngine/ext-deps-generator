---
id: windows-onnxruntime-rebuilds-from-scratch
title: Windows builds compile each target's files serially (Visual Studio generator, no /MP) — move to Ninja
status: in-progress
priority: unranked
scope: builder/cmake_builder.py, builder/platforms/windows.py, libraries/*.yaml (Windows), the Windows build machine
opened: 2026-10-20
tags: [windows, build-time, ninja]
---

# Windows builds compile each target's files serially — move to Ninja

## Why

The v019 build (2026-10-20, 28 cores, 90 GB): each Windows configuration took 27–34 min against 6–7 min per
configuration on the Mac. Measured by the Windows peer: the CPU stayed at 13–31 %, and `--jobs 28` took the same time
as `--jobs 20` (Debug-MT 1619 s vs Debug-MD 1607 s). The Windows CMake path uses the "Visual Studio 17 2022"
generator: `--parallel N` is MSBuild `/m` (projects in parallel) and no `/MP` is passed (0 of 568 `cl` lines), so the
files of ONE target compile serially; the big single targets bound the wall clock (onnxruntime ~12 min per
configuration, recompiling ~2500 sources; tinyusdz ~4 min; libvpx's msys2 configure ~2 min).

Owner decision (2026-10-20): move the Windows CMake path to Ninja as far as possible.

## What remains

- The Ninja path (Windows peer, in progress): the MSVC environment for Ninja, every library rebuilt, the CRT validation
  and `DependenciesTest` green in the four configurations.
- A Ninja build replaces a Visual Studio one only if it ships the same content — the Debug PDBs included (220 in the
  v019 Debug archives).
- What cannot move (a library whose build only works with MSBuild) keeps the VS generator with `/MP`.

## References

- Windows peer reports of the v019 build (2026-10-20).
