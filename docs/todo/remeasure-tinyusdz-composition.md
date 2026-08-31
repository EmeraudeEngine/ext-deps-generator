---
id: remeasure-tinyusdz-composition
title: Re-measure tinyusdz composition on the reference asset after the v1.0.0-rc3 bump
status: open
priority: high
scope: libraries/tinyusdz.yaml, patches/tinyusdz.patch, engine-side composition options
opened: 2026-08-31
tags: [tinyusdz, composition, usd, measurement]
---

tinyusdz moved from v0.9.4 to **v1.0.0-rc3**, and with it the seven composition/material fixes
this repository carried in `patches/tinyusdz.patch` were dropped: three are fixed verbatim
upstream, one became an API option, and three were absorbed by a rewrite of the composition
engine (`src/composition-graph.cc`, a task-queue prim-index builder). The full account is in
the `libraries/tinyusdz.yaml` header.

**Nothing here re-measures composition**, and that is the whole risk. The reference asset that
found the seven defects — `projet-alpha.data/data-stores/USD/WorldLobby.usdz`, 1.6 GB, an
Omniverse Kit export — is not on the build machine, and four of the seven defects failed
*silently* or reported SUCCESS. A "no error" from the loader proves nothing.

## To do

1. Load `WorldLobby.usdz` with the v1.0.0-rc3 build and compare against the numbers the
   patched 0.9.4 produced: **2806 prims, 942 meshes, 141 materials, 348 textures,
   10 000 199 triangles**. Anything close to the pre-patch figure (10 prims — five cameras, a
   DomeLight, empty Xforms) means a defect came back under a new shape.
2. **Set `allow_parent_relative_paths = true`** in the engine's composition options before
   concluding anything. It is a new upstream field and it defaults to **false**
   (`composition.hh:81,104,157`); a Kit export writes its subLayers as `../Source/…`, so with
   the default those layers are rejected and the stage composes to almost nothing — the exact
   symptom the old patch fixed in `security-policy.hh`.
3. If a defect survives, port the corresponding fix to the new architecture rather than
   reverting the version bump: the old hunks are in this repository's git history
   (`git log -p -- patches/tinyusdz.patch`), each with the measurement that justified it.
4. Record the resulting counts in `libraries/tinyusdz.yaml`, then delete this file.

## Second, smaller thing to confirm

`TINYUSDZ_WITH_TEXTOOLS` (new in 1.0.0, ON upstream) is turned **off** in the YAML: it builds
a second static library and links it into the core for KTX2 / GPU-compressed texture decode
inside USDZ, which the engine already covers with libktx and bc7enc_rdo. If a USDZ asset ever
arrives with a KTX2 texture that tinyusdz is expected to decode *itself*, that decision is the
first thing to revisit.
