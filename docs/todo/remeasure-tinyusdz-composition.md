---
id: remeasure-tinyusdz-composition
title: 818 prims still missing from the reference USD stage after the v1.0.0-rc3 bump
status: open
priority: high
scope: libraries/tinyusdz.yaml, patches/tinyusdz.patch, repositories/tinyusdz/src/composition.cc
opened: 2026-08-31
tags: [tinyusdz, composition, usd, measurement]
---

# 818 prims still missing from the reference USD stage after the v1.0.0-rc3 bump

## Why

tinyusdz moved from v0.9.4 to **v1.0.0-rc3** and the seven composition/material fixes this
repository carried were dropped as no longer applying. The reference asset was **measured on
2026-09-14** (it was not, before that date) and the bump is only partly clean.

Measured with the engine loader's own `stage composed:` line —
`projet-alpha --load-demo world-lobby --demo-options 1`, the 1.6 GB Omniverse Kit export
`projet-alpha.data/data-stores/USD/WorldLobby.usdz`, which is **not on the build machine**:

| | patched v0.9.4 | rc3 as shipped | rc3 + the current patch |
|---|---|---|---|
| prims | 2806 | 1988 | **1988** |
| meshes | 942 | 741 | **741** |
| materials | 155 | 31 | **31** |
| textures | 348 | 0 | **85** |
| `SphereLight` | 4 | 0 | **0** |
| depth / cameras / `DiskLight` / `DomeLight` | 9 / 5 / 25 / 1 | unchanged | unchanged |

## Done — do not redo

1. **`allow_parent_relative_paths` is set by the engine** (`USDLoader::load()`, four flags: the
   resolver plus the sublayer, references and payload option structs). Without it the stage
   composed to ten prims while reporting success on demo option `0`, and errored on option `1`.
2. **The `is_connection()` predicate defect was back in a second file and is patched again.**
   `RemapPathsInPrimSpecTree()` (`composition.cc:4063`) gated its connection branch on
   `Property::is_attribute_connection()`, false as soon as the attribute also carries a value —
   so a `.connect` authored next to a fallback value kept its pre-splice path. Measured effect:
   **0 → 85 textures**. The hunk patches the live site only; `ReplaceRootPrimPathRec()`, where
   v0.9.4 patched the same thing, is now `[[maybe_unused]]` dead code and is left alone.
3. **Two classifications from 2026-08-31 were verified in the source and hold**: the
   `is_connection()` → `has_connections()` fix in `tydra/render-data-material.cc` (22 sites, the
   5 survivors are comments), and the arc prefix absorbed verbatim as `GetReferencedPrimPath()`
   (`composition.cc:351`).

## What remains

**818 prims, 201 meshes, 124 material prims and all four `SphereLight` are absent from the
composed stage, and nothing above moves them.** A dangling connection cannot delete a prim, so
this is a distinct mechanism, still unattributed. Start from the three defects classified as
"absorbed by the composition rewrite" — they were never verified, only reasoned about from the
new structure:

- subLayers of a referenced/payloaded layer never composed;
- arcs resolved in a single pass instead of to a fixed point;
- the arc prefix not re-rooted (this one IS verified present — see Done 3).

The old hunks, each with the measurement that justified it, are in
`git log -p -- patches/tinyusdz.patch` (before commit `1191c0e`). Port to the new architecture
rather than reverting the version bump.

## ⚠️ Traps

- **A fix verified file-by-file is not verified.** "The texture defect is fixed upstream" was
  true of `render-data-material.cc` and false of `composition.cc`, where the same predicate
  lived. Grep the PREDICATE across the whole tree, then re-run the asset. Measurement found this
  in one run; three passes of source reading had classified it as absorbed.
- **A patch that stops applying is not evidence the defect is gone.** Here the surrounding
  function was renamed (`ReplaceRootPrimPathRec` → `RemapPathsInPrimSpecTree`) and the defect
  travelled into the replacement.
- **Never trust this path on a "no error".** Four of the seven original defects failed silently
  or reported SUCCESS. Only a prim/mesh/texture COUNT is evidence.
- **The counts must come from the same instrument.** Every figure in the table above is the
  engine loader's `stage composed:` line on demo option **1**; option `0` legitimately composes
  ten prims and reports success, because the root layer's whole body is two `prepend payload`
  arcs — a broken option 1 reads exactly like a healthy option 0.

## References

- `libraries/tinyusdz.yaml` — the full account, per fix.
- `emeraude-engine/docs/scene-loaders-usd.md` § 11.5 item 3 and § 11.7 — the consumer side.

## Second, smaller thing to confirm

`TINYUSDZ_WITH_TEXTOOLS` (new in 1.0.0, ON upstream) is turned **off** in the YAML: it builds
a second static library and links it into the core for KTX2 / GPU-compressed texture decode
inside USDZ, which the engine already covers with libktx and bc7enc_rdo. If a USDZ asset ever
arrives with a KTX2 texture that tinyusdz is expected to decode *itself*, that decision is the
first thing to revisit.
