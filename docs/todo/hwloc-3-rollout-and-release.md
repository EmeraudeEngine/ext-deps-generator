---
id: hwloc-3-rollout-and-release
title: Rebuild hwloc 3.0.0a1 (upstream master + patches/hwloc.patch) on every configuration and publish the next archive
status: in-progress
priority: high
scope: libraries/hwloc.yaml, patches/hwloc.patch, repositories/hwloc, every output/<config>, the next GitHub release
opened: 2026-10-10
tags: [hwloc, apple-silicon, release, api-break]
---

# Rebuild hwloc 3.0.0a1 on every configuration and publish the next archive

## Why

hwloc <= 2.15 hangs forever in `hwloc_topology_load()` on Apple silicon with three core types
(measured on a Mac18,5: `hw.nperflevels = 3`, IOKit cluster types E ×6, P ×2, M ×4). The engine
calls it from `SystemInfo::fetchCPUInformation()` at start-up, so every application linking the
archive freezes at 100 % CPU right after `SettingsService` comes up. Story and pin rationale: the
header of `libraries/hwloc.yaml`. The owner chose upstream master (2026-10-10): the Apple fix is
on master only, not on v2.x.

hwloc 3.0 breaks the 2.x API (`hwloc_cpukinds_get_info()` takes a `struct hwloc_infos_s **`
instead of `unsigned *nr_infos, struct hwloc_info_s **infos`). The engine is adapted in the
same move, so **an engine built from that commit no longer compiles against v017**: the archive
version consumed by emeraude-base (`cmake/InstallDependencies.cmake`, `EXTERNAL_DEPENDENCIES_VERSION`)
must move to the new release in the same push.

## Done

- macOS arm64, Release and Debug (2026-10-10): `HWLOC_VERSION "3.0.0a1-git"`, the patch applied
  before `autogen.sh`, Release archive 0 build-path strings (Debug: 70 DWARF paths, same count as
  v017's — kept on purpose, see § Build-machine paths). A standalone probe linked on the archive
  loads in < 10 ms (`time`, 5 runs: 0.00 s real): 12 PUs, 3 cpukinds (Efficiency cpus 0-5, Performance 8-11,
  Super 6-7 — matches IOKit), 3 L2 caches. The v017 archive hangs on the same probe.

## To do

- Linux x86_64 (Release, Debug): autotools; `autogen.sh` now runs on a git checkout of master
  (autoconf, automake, libtool needed).
- macOS x86_64 (Release, Debug).
- Windows MD and MT (Release, Debug): `contrib/windows-cmake` exists on master but changed
  (15 commits since 2.14.0-33) — check the YAML's `cmake_options` are still honoured
  (`HWLOC_SKIP_TOOLS`, `HWLOC_SKIP_LSTOPO`, `HWLOC_ENABLE_TESTING`) and the CRT validation.
- `DependenciesTest` on the three OS (it links hwloc).
- Every downstream consumer of the archive that calls the hwloc API directly: adapt it to 3.0
  before it moves to the new release.
- Cut the release, then move emeraude-base's `EXTERNAL_DEPENDENCIES_VERSION`.
- When 3.0.0 is tagged: move the pin to the tag and re-check whether `patches/hwloc.patch` is
  still needed (report the wrap-around upstream only on the owner's decision).
