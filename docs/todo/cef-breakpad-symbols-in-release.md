---
id: cef-breakpad-symbols-in-release
title: Publish the Breakpad symbols of every CEF build beside its archives
status: open
priority: unranked
scope: build_cef.py (after the distribution), the GitHub release of each CEF build
opened: 2026-10-22
tags: [cef, symbols, crash-report, release]
---

# Publish the Breakpad symbols of every CEF build beside its archives

## Why

The applications built on CEF (Lychee Slicer: app_system) now collect the Crashpad minidumps of their native crashes
and read them with `minidump-stackwalk`. Every frame inside libcef (and libEGL, libGLESv2, swiftshader…) stays an
address without the symbols of the **exact** CEF build that shipped: a renderer crash then reads `libcef.so + 0x8ba3980`.
The symbols can only come from where CEF is built — here.

Owner decision (2026-10-22): they are published **in the release that ships the CEF archives**, beside them —
`cef_binary_<CEF version>_<platform>_breakpad_symbols.zip`. This repository is public; CEF's symbols are public by
nature (Spotify publishes its own).

Done by hand for **CEF 150.0.11+gb887805 in v014** (2026-10-22, from the build disk, Mozilla `dump_syms` 2.3.9):
`…_linux64_breakpad_symbols.zip` (35 MB: libcef, libEGL, libGLESv2, libvk_swiftshader) and
`…_windows64_breakpad_symbols.zip` (57 MB: libcef.dll, libEGL, libGLESv2, vk_swiftshader, vulkan-1, chrome_elf,
dxcompiler, bootstrap); `…_macosarm64_breakpad_symbols.zip` (63 MB) and `…_macosx64_breakpad_symbols.zip` (62 MB):
Chromium Embedded Framework, libEGL, libGLESv2, libvk_swiftshader, libcef_sandbox (each binary/dSYM pair checked by
UUID, and the arm64 framework of a Lychee package = the distribution's).

Done by hand for **CEF 156.0.31+ge603d97 linux64 in v019** (2026-11-19, `dump_syms` 2.3.9 on the unstripped
`output/…_linux64/Release/`): `…_linux64_breakpad_symbols.zip` (38.7 MB) holds `libcef.so` (id
`BC8E100537A78FDA3D5DA9FBE8832FC30`, = the stripped copy's; 9 s, 3.7 GB RAM, 694 MB `.sym`: 7 339 FUNC, 679 775 PUBLIC,
13.3 M STACK CFI) and `libvk_swiftshader.so`. No `libEGL`/`libGLESv2` any more: since 156 ANGLE is linked inside
libcef (`AGENTS.md` § Publishing a CEF archive).

Done for **CEF 156.0.31+ge603d97 windows64 in v019** (2026-11-20, on the Windows build machine, `dump_syms` 2.3.9):
`…_windows64_breakpad_symbols.zip` (64.7 MB) holds libcef.dll (id `30796557A1FB71BA4C4C44205044422E1`, code id
`6AF37C981346D000`, checked against the shipped DLL's CodeView record; 348.9 MB `.sym`: 644 094 FUNC, 21 585 PUBLIC,
556 227 STACK CFI INIT), chrome_elf.dll, dxcompiler.dll, vk_swiftshader.dll, vulkan-1.dll, bootstrap.exe,
bootstrapc.exe. Each **binary** was dumped with its PDB beside it (see Traps). The `*_release_symbols.zip` and
`*_debug_symbols.zip` made by automate-git are kept in `C:\cef156-symbols` on that machine (they live only in
`<download-dir>/chromium/src/cef/binary_distrib/`, not in `output/`). macosarm64, macosx64: to do when their builds land.

## What remains

- `build_cef.py`, after the distribution is made (or a separate step before publishing): run `dump_syms` on every
  library of the distribution and write `cef_binary_<version>_<platform>_breakpad_symbols.zip` next to the
  `.tar.bz2`, Breakpad store layout at the zip root (`<module>/<id>/<module>.sym`).
- Publish it with the CEF archive in the same release; consumers fetch every `*_breakpad_symbols.zip` of every release
  (app_system: `tools/crash-reports/crash_reports.py symbols`).
- **Keep the debug material of every published CEF build** until the next CEF bump at least: the unstripped Linux
  libraries, the Windows `*_release_symbols` PDBs, the macOS `*_release_symbols` dSYMs. Lost, the symbols of the CEF
  build already in users' hands can never be made again (a rebuild does not give the same module ids).

## ⚠️ Traps (measured 2026-10-22)

- **Linux**: the distribution's `Release/libcef.so` keeps its DWARF (`symbol_level=1`, 2 GB) — dump it, not the
  shipped stripped copy (277 MB, publics only). Its Breakpad module id equals the stripped one
  (`B59A74285D32579DD178F6D9A7B447BA0` for 150.0.11): **no GNU Build ID** in libcef, the id comes from the text
  section — check the ids match before publishing. 8 s, 3.2 GB RAM, a 592 MB `.sym` (6 068 FUNC, 647 196 PUBLIC,
  10 M STACK CFI).
- **Windows**: dump the **binary** of the distribution with its PDB (from
  `cef_binary_<version>_windows64_release_symbols/`) copied beside it: `dump_syms <dir>/libcef.dll`. The PDB alone
  gives the same FUNC/PUBLIC and the same module id but **no unwind table** (STACK CFI = 0: x64 unwind data is the
  PE's `.pdata`, not in the PDB) and no `INFO CODE_ID`; measured on 156 libcef: 0 vs 556 227 STACK CFI INIT, 278 vs
  349 MB `.sym`, ~40 s each. The 150 set (v014) was dumped from the PDBs alone (`libcef.dll.pdb` 2.4 GB: 24 s,
  5 GB RAM, a 263 MB `.sym`): its published libcef `.sym` has 607 780 FUNC, 0 STACK CFI and no `INFO CODE_ID`
  (re-read from the v014 asset 2026-11-20). Redoing it needs the 150 `libcef.dll` (any copy of the published
  archive) and its `libcef.dll.pdb` (`*_release_symbols`, if still kept). Module = `<name>.pdb`, id = PDB GUID + age (lld's
  deterministic link: every GUID ends in `4C4C44205044422E`, "LLD PDB."). `dump_syms --store <dir> <binary>` writes
  the store layout; zip it with Python `zipfile` (PowerShell 5.1's `Compress-Archive` writes `\` in entry names).
- **macOS**: `dump_syms <the .dSYM> <the binary>` in ONE call (`-a arm64|x86_64` for a fat binary). The dSYM alone
  names the module `<name>.dSYM` (a minidump looks for `<name>`: nothing found) and carries no unwind table (STACK CFI
  = 0); the binary alone has no FUNC/line. `release_symbols` holds 5 dSYMs per arch (Chromium Embedded Framework,
  libEGL, libGLESv2, libvk_swiftshader, libcef_sandbox); the distribution's binaries match them by UUID.
- `dump_syms` is a development tool (Mozilla, https://github.com/mozilla/dump_syms), never shipped.

## References

- app_system `docs/crash-report.md` § Symbols and § Minidumps; `tools/crash-reports/README.md` § Native stacks.
