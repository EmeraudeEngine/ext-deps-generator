---
id: cef-gclient-sync-memory-macos
title: Bound the gclient sync of a CEF bump on the 16 GB Mac
status: open
priority: high
scope: build_cef.py (update phase), macOS
opened: 2026-11-20
tags: [cef, macos, memory]
---

# Bound the gclient sync of a CEF bump on the 16 GB Mac

## Why
The CEF 156 update phase on the Mac mini (12 cores, 16 GB), 2026-11-20 night: three
JetsamEvent reports (02:36, 03:17, 03:55), each dominated by `git` — 6, 29 then 51
processes at once, several of 4 to 6 GiB resident (fetch / index-pack on Chromium-size
repositories). Jetsam killed processes; no kernel panic, unlike the compile phase
(`AGENTS.md` § CEF, "Memory-bound machines", which `apply_memory_limits()` now covers).
The next branch bump will hit it again.

## What remains
- Find what sets the gclient sync parallelism under automate-git.py (gclient's
  `--jobs`, default from the core count; automate-git exposes no option today) and how
  to pass a lower value — environment, or the `.gclient` / a wrapper.
- Size it like the compile limit (RAM-based, inert on the Linux and Windows machines)
  and wire it into `apply_memory_limits()`.
- Measure on the next bump: the jetsam reports in `/Library/Logs/DiagnosticReports/`.

## References
- `build_cef.py` `apply_memory_limits()`
- `/Library/Logs/DiagnosticReports/JetsamEvent-2026-11-20-*.ips` on the Mac mini
