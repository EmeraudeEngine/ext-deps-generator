---
id: nasm-objects-without-macos-platform-load-command
title: libjpeg-turbo's NASM objects carry no macOS platform load command (27 ld warnings per x86_64 link)
status: open
priority: unranked
scope: builder/platforms/macos.py (the assembler flags), libraries/libjpeg-turbo.yaml, the macos.x86_64 archives
opened: 2026-11-24
tags: [macos, x86_64, nasm, libjpeg-turbo, warnings, v020]
---

# libjpeg-turbo's NASM objects carry no macOS platform load command (27 ld warnings per x86_64 link)

Owner, 2026-11-24: to be fixed for **v020**.

## Why

Every x86_64 macOS link against the v019 archive prints 27 warnings from the linker, one per SIMD object of
`libjpeg.a` (from `[2] jsimdcpu.asm.o` to `[28] jquanti-avx2.asm.o`):

```
ld: warning: no platform load command found in '…/macos.x86_64-Release-sdk13.0/lib/libjpeg.a[N](<x>-sse2|avx2|sse.asm.o)', assuming: macOS
```

Measured on a Mac mini M6 (macOS 27.2, Apple clang 21.0.0, ld 27106.1), linking emeraude-base's test binary for
x86_64 with `macos.x86_64-Release-sdk13.0.v019.zip`. arm64 is not affected: its SIMD code is not assembled by NASM.

The C and C++ objects get their `LC_BUILD_VERSION` from `-mmacosx-version-min` (`MacOSPlatform.get_c_flags()` /
`get_cxx_flags()`), but nothing gives the assembler a deployment target, so NASM writes Mach-O objects without any
platform load command. The linker assumes macOS, so the binary is right today. Still, every consumer's build log
carries 27 warnings that are not theirs, and the "0 warning" gate of the cascade cannot pass on x86_64 macOS.

## What remains

- Give NASM the platform and the deployment target on macOS. NASM 2.16 and later have a Mach-O option for this
  (`--macho-min-os`). ⚠️ Verify its exact syntax and the NASM version on the macOS build machine before you rely on it.
  Pass it through `CMAKE_ASM_NASM_FLAGS` (from `MacOSPlatform`, or the libjpeg-turbo recipe if NASM is used nowhere
  else), built from `config.macos_sdk`, so that the `sdk12.0` and `sdk13.0` archives each carry their own floor.
- Rebuild `macos.x86_64-{Debug,Release}-sdk{12.0,13.0}` and check every `*.asm.o` of `libjpeg.a`: `otool -l` must
  show an `LC_BUILD_VERSION` (platform MACOS, minos = the archive's SDK). Then check that an x86_64 link of a consumer
  prints 0 `no platform load command` warnings.
- Look for other NASM or yasm users among the libraries (libvpx and others). The same fix applies to them.

## ⚠️ Traps

- A minos ABOVE the archive's deployment target would make the consumer's binary claim a newer macOS. A consumer's
  packager checks it (minos ≤ `LSMinimumSystemVersion`), and the warning would become a refused package. Use exactly
  `config.macos_sdk`.
- The STT_FILE stripping of NASM objects (`linux.py`, `_strip_build_machine_file_symbols`) is Linux-only. Check that
  the macOS objects do not name build-machine paths either (`verify_no_build_machine_paths` of the consumer).

## References

- `builder/platforms/macos.py` (`get_platform_cmake_options()`, `get_c_flags()`), `libraries/libjpeg-turbo.yaml`
  (`REQUIRE_SIMD`, `WITH_SIMD`).
