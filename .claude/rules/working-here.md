# Working in ext-deps-generator (ALWAYS ACTIVE)

> Digest of what a session must know before building or publishing here. `AGENTS.md` is authoritative; the release
> procedure is the `release-archives` skill. This repository is PUBLIC: never name a private downstream application,
> its company, tools, paths or hosts — write "a downstream application".

- **Which machine builds varies.** Look before building: a populated `output/<config>/` and `builds/<config>/` for the
  local platform, or the owner describing a failure on "this machine", means build here. Linux archives for a
  downstream application's releases (glibc 2.35 floor) are built on a separate Ubuntu 22.04 box (gcc-14,
  `source config_ubuntu22.sh`); when the box is not local, make the fix committable and reason about it instead.
- **macOS deployment targets: both 12.0 and 13.0 are published.** A downstream application still requires 12.0;
  the 12.0 archives stay available until the owner retires them. Never drop a target on your own.
- **Two CEF consumers pin differently, on purpose — never "align" them.** projet-alpha uses the vanilla Spotify CDN
  build (free to track a newer branch); a downstream application uses this repository's patched build (H.264, V8
  sandbox off, `patches/chromium/`) pinned to the branch in `build_cef.py`. A CEF archive is an annex asset on the
  current deps release, not a release of its own (`AGENTS.md` § Publishing a CEF archive).
- **A single-library run (`--library X --no-deps`) skips `DependenciesTest`**: run the test project by hand before
  any publish. On Apple Silicon the x86_64 `DependenciesTest` runs under Rosetta 2 (installed).
- `--jobs N`: Windows box (28 threads, 80 GB) → `--jobs 20`; elsewhere the machine's full parallelism.
- `python build.py --clean` is GLOBAL (wipes every configuration and extracted CEF): to rebuild one configuration,
  delete `builds/<suffix>` and empty `output/<suffix>` (keep the directory: links point to it).
- Commits and pushes only on the owner's explicit request; the work branch is `develop`.
