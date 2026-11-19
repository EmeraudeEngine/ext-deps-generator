---
id: cef-v8-shared-cage-trial
title: Try the V8 shared pointer-compression cage in the CEF build instead of multi-cage
status: open
priority: unranked
scope: build_cef.py (BASE_GN_DEFINES), every CEF archive, the downstream application's renderer memory
opened: 2026-11-19
tags: [cef, v8, memory]
---

# Try the V8 shared pointer-compression cage in the CEF build instead of multi-cage

## Why

Since CEF 156 the build compresses V8 pointers in **multi-cage** mode
(`v8_enable_pointer_compression_shared_cage=false`, owner decision 2026-11-19, rationale in
`BASE_GN_DEFINES`). The shared cage is the mode Chrome itself ships, hence the most exercised
inside Chromium; the owner wants it tested later.

What changes with `v8_enable_pointer_compression_shared_cage=true` (sandbox still OFF):
- NOT the heap limit. In multi-cage the cage belongs to an `IsolateGroup`, every isolate created
  without one lands in the default group (`v8/include/v8-isolate.h`), and neither Chromium nor
  CEF 156 creates a group: both modes give ONE 4 GB cage of ordinary JS objects per renderer
  process, shared by the main thread and its workers (verified on CEF 156 / V8 15.6.75.57).
  ArrayBuffer contents stay outside the cage either way.
- The cage base becomes a process-wide constant (slightly cheaper decompression).
- NOT V8's partition_alloc: multi-cage forbids it, but `v8/BUILD.gn` also forbids it in every
  Chromium build (`build_with_v8_embedder = build_with_chromium`), so it stays off either way.
- The zero-copy bridge is unaffected: external backing stores depend on the sandbox alone.

## What remains

1. Build with `v8_enable_pointer_compression_shared_cage=true` (one platform is enough for the
   trial), read the effective `args.gn` back.
2. The downstream application runs its zero-copy bridge and its heaviest scene, with workers,
   and compares performance and memory against the multi-cage build (the 4 GB per-process
   limit is the same in both modes).
3. Owner decision: keep multi-cage or switch; update `BASE_GN_DEFINES`, its comment and
   `AGENTS.md` § CEF ("Why build CEF ourselves", point 2).

## ⚠️ Traps

- Switching the cage mode without a CEF version bump republishes the same archive name with
  different content: a consumer that cached the previous archive keeps it silently
  (`AGENTS.md` § Publishing a CEF archive). Land it with a version bump, or name the trial
  build differently.

## References

- `build_cef.py`, `BASE_GN_DEFINES` (Goal 2 comment).
- `v8/BUILD.gn`: the `v8_enable_pointer_compression_shared_cage` default and the
  partition_alloc assert.
