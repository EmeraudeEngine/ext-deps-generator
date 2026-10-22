---
id: build-independent-libraries-concurrently
title: Build the libraries whose dependencies are ready concurrently, not one after the other
status: open
priority: unranked
scope: build.py (library scheduling), builder/* (shared install prefix, patch markers, CRT validation)
opened: 2026-10-20
tags: [build-time, windows, cross-platform]
---

# Build the libraries whose dependencies are ready concurrently, not one after the other

## Why

`build.py` builds the ~50 libraries strictly in sequence. Inside one library the compilation
uses every core (Ninja on every platform since 2026-10-20, AGENTS.md § Windows generator: Ninja),
but each library's **configure** step (CMake's feature probes, one `cl.exe` per check on Windows,
where process creation is slow) runs on a single core, and so do the short builds of the small
libraries. On the 28-thread Windows build box a from-scratch Ninja build took 951-1347 s per
configuration (AGENTS.md table), of which onnxruntime (~280 s), libvpx (~77 s) and tinyusdz (~67 s)
are the only long builds: most of the rest is serial configure time while the CPU is mostly idle.

## What remains

- Schedule a library as soon as everything in its `depends_on` is installed, a bounded number at a
  time, with the `--jobs` budget shared between the running builds.
- Every library installs into the SAME prefix (`output/<config>`): check that no two concurrently
  built libraries install the same file, or serialise the install steps.
- `WindowsPlatform.validate_crt_linkage()` validates "the .lib files not validated yet" in the
  shared `lib/` folder: with concurrent installs it must validate the files of its own library.
- Measure it per platform (Windows, Linux, macOS) before adopting it: the gain is the serial part
  only.

## ⚠️ Traps

- The patch markers (`.patch_applied`) live in the shared `repositories/` checkouts: two
  configurations of the same library must never be built concurrently.
- The console output of concurrent builds interleaves: one log per library.
