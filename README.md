# Introduction

This repository aims to create a cross-platform archive of static libraries to use with a project easily.
This must be run on a clean machine to create the archive for a specific platform.
Currently, Linux (x86_64), macOS (arm64, x86_64) and Windows (x86_64) are handled.


# Updating dependencies

If you update a dependency that requires other dependencies like freetype, update them as well.

When a dependency is updated, remember to report in 'Available libraries' the changes (branch, commit, version, ...).

## Updating LibreSSL (vendored)

LibreSSL is the **one exception** to the "every dependency is a git submodule" rule: its
sources are a committed release tarball under `repositories/libressl/` (see the "Vendored
Sources" section in `AGENTS.md` for why). `check_releases.py` cannot see it, so releases must
be checked manually. To move to a new version:

```sh
# 1. Check for a newer stable at https://www.libressl.org/releases.html
#    (x.y.2 is the first STABLE of a branch; x.y.0/x.y.1 are dev snapshots).

# 2. Download the tarball and the mirror's signed checksum list, then VERIFY.
VER=4.3.2   # <-- set the target version
cd /tmp
curl -sSLO "https://ftp.openbsd.org/pub/OpenBSD/LibreSSL/libressl-${VER}.tar.gz"
curl -sSLO "https://ftp.openbsd.org/pub/OpenBSD/LibreSSL/SHA256"
grep "libressl-${VER}.tar.gz" SHA256
sha256sum "libressl-${VER}.tar.gz"     # <-- the two hashes MUST match

# 3. Replace the vendored sources (from the ext-deps-generator repo root).
rm -rf repositories/libressl
mkdir  repositories/libressl
tar -xzf "/tmp/libressl-${VER}.tar.gz" -C repositories/libressl --strip-components=1

# 4. Update the version + SHA256 in libraries/libressl.yaml AND the "## libressl"
#    entry in this README, then rebuild + run the link-test to confirm.
```


# Available libraries

## bc7enc_rdo
[master, b9438627eef73a1157e84201b6fa6eb2ffd6d9f0]

- URL: https://github.com/richgel999/bc7enc_rdo.git
- Version: master (no upstream releases)
- Dependencies: None
- Usage: BC7 texture block encoder/decoder. Required by engines doing GPU-side compressed texture upload.
- Notes: Upstream targets a standalone `bc7enc` executable with RDO tooling. The patch replaces the CMakeLists with a minimal static-library build exposing only the core encoder/decoder (`bc7enc.cpp` + `bc7decomp.cpp`); the RDO optimizer and lodepng/utils helpers are not needed downstream and are excluded.
- Warning: **compiled as C++17, not C++20**, in deviation from the build policy: upstream sets
  the `CXX_STANDARD 17` *target property* (CMakeLists.txt:18), which beats the
  `CMAKE_CXX_STANDARD` cache variable, so passing the standard from the YAML would be inert.
  Lifting it needs a patch; the codec's API is C-style structs and free functions, identical
  under both standards.

## brotli 
[v1.2.0, 028fb5a23661f123017c060daa546b55cf4bde29]

- URL: https://github.com/google/brotli.git
- Version: 1.2.0
- Dependencies: None
- Usage: Lossless compression library (Huffman LZ77). Requested by Freetype.

## bzip2 
[master, 1ea1ac188ad4b9cb662e3f8314673c63df95a589]

- URL: https://github.com/libarchive/bzip2.git
- Version: 1.1.0
- Dependencies: None
- Usage: Compression library.

## clipper2 
[Clipper2_2.0.1, 21ebba05db8894f0c7217ad35ea518080f324946]

- URL: https://github.com/AngusJohnson/clipper2
- Version: 2.0.1
- Dependencies: None
- Usage: A polygon clipping and offsetting library.

## cppzmq
[master, 7f0530688804c2b5b6b0d985773405593fd25ca8]

- URL: https://github.com/zeromq/cppzmq.git
- Version: 4.11.0~
- Dependencies: libzmq
- Usage: C++ wrapper for libzmq.
- Notes: There is no compilation here, this is just some headers for libzmq.

## cpu_features 
[main, 81d13c49649f0714dd41fb56bb246398b6584085]

- URL: https://github.com/google/cpu_features.git
- Version: 0.11.0
- Dependencies: None
- Usage: Fetch CPU extensions and capabilities.

## cryptopp-cmake 
[master, 866aceb8b13b6427a3c4541288ff412ad54f11ea]

- URL: https://github.com/abdes/cryptopp-cmake
- Version: 0.8.9~
- Dependencies: None
- Usage: Common cryptographic library for C++.

## draco
[1.5.7, 8786740086a9f4d83f44aa83badfbea4dce7a1b5]

- URL: https://github.com/google/draco.git
- Version: 1.5.7 (release tag; upstream has cut no release since 2024-01)
- Dependencies: None
- Usage: geometry compression codec behind `KHR_draco_mesh_compression`. Same situation as
  meshoptimizer for `EXT_meshopt_compression`: fastgltf parses the extension but decodes
  nothing, so the accessors of a compressed primitive point at a Draco bitstream instead of
  vertex data. Only the decoder is needed at runtime
  (`draco::Decoder::DecodeBufferToGeometry`, then `GetAttributeByUniqueId()` keyed by the
  attribute ids the glTF extension carries); the encoder ships in the same archive and the
  linker prunes it.
- Notes: built consumer-only (no tests, no Unity/Maya plugins, no JS glue, no transcoder —
  the transcoder would drag in the vendored tinygltf and eigen and force C++17 on the whole
  build) and compiled as C++20 per the build policy, since Draco declares no standard of its
  own and would otherwise take the host compiler's default.
  `DRACO_BACKWARDS_COMPATIBILITY` stays ON so pre-1.0 bitstreams still decode.
- Warning: `DRACO_GLTF_BITSTREAM` is **not** a "build glTF support" switch — it *restricts*
  the build to the feature subset the glTF extension standardises, narrowing what the
  decoder accepts. It is left OFF on purpose.
- Warning: `make install` also drops two CLI executables into `bin/` (`draco_encoder`,
  `draco_decoder`). `draco_setup_install_target()` installs them unconditionally with no
  option to opt out; removing them would take a patch.

## fastgltf
[v0.9.x, 0d1b67a28c4950ea2deb796702006dcbe31e02b3]

- URL: https://github.com/spnda/fastgltf.git
- Version: 0.9.0
- Dependencies: None
- Usage: GLTF 2.0 file parser.

## flac
[1.5.0, 1507800de4b70e21be71f38caa0d9079d0bc6e45]

- URL: https://github.com/xiph/flac.git
- Version: 1.5.0
- Dependencies: libogg
- Usage: Free Lossless Audio Codec. Required by libsndfile.

## freetype 
[VER-2-14-3, 0a0221a1347e2f1e07c395263540026e9a0aa7c7]

- URL: https://gitlab.freedesktop.org/freetype/freetype.git
- Version: 2.14.3
- Dependencies: brotli, bzip2, harbuzz, png, zlib
- Usage: Fonts files (.ttf, .tti, ...) library.

## glslang
[16.5.0, a8d28bd082bff18ffbe80996e922b012f915cf07]

- URL: https://github.com/KhronosGroup/glslang.git
- Version: 16.5.0
- Dependencies: spirv-tools (which itself depends on spirv-headers)
- Usage: GLSL/HLSL front-end and SPIR-V code generator. Required to compile GLSL shaders to SPIR-V at runtime in Vulkan engines.
- Notes: Built with `ALLOW_EXTERNAL_SPIRV_TOOLS=ON` and `BUILD_EXTERNAL=OFF` so the SPIR-V optimizer is consumed from the standalone spirv-tools package via `find_package` instead of glslang's bundled `update_glslang_sources.py` fetch. Commits of spirv-tools and spirv-headers are aligned with glslang's `known_good.json` to stay ABI-compatible.
- Notes: exceptions and RTTI are off (`ENABLE_EXCEPTIONS`, `ENABLE_RTTI`), which is both
  upstream's default and the build policy; they are pinned in the YAML so a change of default
  cannot flip them silently.
- Warning: **compiled as C++17, not C++20**, in deviation from the build policy: glslang does
  `set(CMAKE_CXX_STANDARD 17)` unconditionally (CMakeLists.txt:229), so the builder's
  `-DCMAKE_CXX_STANDARD=20` is silently overridden. Lifting it would take a patch making that
  `set()` conditional; the two standards present the same API here, so it was left alone.

## harfbuzz 
[14.4.0, 36cb489cb02ce4b92099669ba9f9bea348eff93f]

- URL: https://github.com/harfbuzz/harfbuzz.git
- Version: 14.4.0
- Dependencies: None
- Usage: Vector font library. Requested by Freetype
 
## hwloc 
[v2.14, 51896fab7ce4244bd49334558e01c0c2bd8dc2af]

- URL: https://github.com/open-mpi/hwloc
- Version: 2.14
- Dependencies: None
- Usage: Fetch system capabilities.
- Notes: Linux and macOS versions are using autotools instead of cmake.

## jsoncpp
[1.9.8, 8519b8381f3c741ad1421f88237b1deda0b11412]

- URL: https://github.com/open-source-parsers/jsoncpp.git
- Version: 1.9.8
- Dependencies: None
- Usage: JSON parser.

## ktx (KTX-Software / libktx)
[v4.4.2, 4d6fc70eaf62ad0558e63e8d97eb9766118327a6]

- URL: https://github.com/KhronosGroup/KTX-Software.git
- Version: 4.4.2
- Dependencies: None (vendors its own basisu, astc-encoder and zstd)
- Usage: KTX2 container reader + Basis Universal transcoder, i.e. the `KHR_texture_basisu`
  path. fastgltf only reports `MimeType::KTX2` and hands over the bytes; libktx transcodes
  the UASTC/ETC1S payload to BC7 (`ktxTexture2_TranscodeBasis` + `KTX_TTF_BC7_RGBA`), or to
  `KTX_TTF_RGBA32` when the device reports no `textureCompressionBC`. Does **not** replace
  bc7enc_rdo, which stays the runtime encoder for PNG/JPEG assets.
- Notes: built consumer-only (no tools, tests, docs, JNI, Python, GL/VK upload).
  `KTX_FEATURE_KTX1` MUST stay ON even though the format is unused: turning it off in 4.4.2
  yields a broken archive (`lib/texture.c` still calls `ktxTexture1_constructFromStreamAndHeader`,
  whose translation unit gets excluded — verified by link test).
- Warning: zstd is **vendored and unprefixed** (`external/basisu/zstd/zstd.c` is hardcoded in
  the target sources), so `libktx.a` defines its own `ZSTD_*` symbols next to the cascade's
  zstd. Harmless while the linker resolves them from a single archive; if a link ever dies on
  duplicate definitions, patch out that source file rather than changing the builder. A static
  build also installs the astc-encoder archive, so expect a second `.a` in the output dir.

## lame
[master, 1f5cc9487284d5950343aa5d4f70de433468070a]

- URL: https://github.com/lameproject/lame.git
- Version: 3.100
- Dependencies: None
- Usage: MP3 encoder. Required by libsndfile for MP3 write support.
- Notes: No official git upstream (lame is on SourceForge in SVN). This mirror has no release tags, so we pin to a master SHA. libsndfile needs LAME 3.100+ (uses `lame_encode_buffer_interleaved_int`). Disabled on Windows: only old VS 2008 project files are provided.

## lib3mf 
[release/2.5.0, bbbbffb79e197903b874470e5f83609b1d6272ae]

- URL: https://github.com/3MFConsortium/lib3mf.git
- Version: 2.5.0
- Dependencies: zlib, libzip
- Usage: 3D model format library.
- Notes: This library fails to compile as static.

## libjpeg-turbo 
[3.2.0, c85e6b905bf237038faa936dab160ebfc5da0344]

- URL: https://github.com/libjpeg-turbo/libjpeg-turbo.git
- Version: 3.2.0
- Dependencies: NASM compiler (optional, but slower lib)
- Usage: Image format library.

## libogg
[v1.3.6, be05b13e98b048f0b5a0f5fa8ce514d56db5f822]

- URL: https://github.com/xiph/ogg.git
- Version: 1.3.6
- Dependencies: None
- Usage: Ogg container format. Required by libvorbis, flac, and libsndfile.

## libpng 
[v1.6.58, 3061454d980de7d53608f594194cfac722721d2a]

- URL: https://github.com/glennrp/libpng.git
- Version: 1.6.58
- Dependencies: zlib
- Usage: Image format library.

## libsamplerate 
[master, 0844c208f683527c08ea8a80acc13b398aa9c8bf]

- URL: https://github.com/libsndfile/libsamplerate.git
- Version: 0.2.2~
- Dependencies: FFTW3 library (optional, but slower lib)
- Usage: Audio resampler library.

## libsndfile
[1.2.2, 72f6af15e8f85157bd622ed45b979025828b7001]

- URL: https://github.com/libsndfile/libsndfile.git
- Version: 1.2.2
- Dependencies: libogg, libvorbis, flac, opus, mpg123, lame (lame disabled on Windows)
- Usage: Audio file I/O library (WAV, FLAC, Ogg/Vorbis, Opus, MP3, etc.).
- Notes: MP3 write support requires lame, so it is disabled on Windows.

## libtiff
[v4.7.2, d01a94be176f5f6a87f7ee1c0b32e65416aa2b4d]

- URL: https://gitlab.com/libtiff/libtiff.git
- Version: 4.7.2
- Dependencies: zlib, libjpeg-turbo, xz, zstd
- Usage: TIFF reader/writer. Needed because reference assets store whole vegetation
  albedo/translucency sets as 4096x4096 16-bit TIFF; without a TIFF codec those materials
  render pure white.
- Notes: library only (tools, tests, contrib, docs and deprecated APIs are off). WebP, JBIG,
  LERC and libdeflate codecs are disabled — they are not in the cascade and enabling them
  breaks the engine link on `WebPGetFeaturesInternal` / `jbg_dec_in`.
- Warning: 12-bit JPEG must be off **and** its detection short-circuited
  (`HAVE_JPEGTURBO_DUAL_MODE_12=false`). libjpeg-turbo 3.x *declares* `jpeg12_read_scanlines`
  in `jpeglib.h` while our archive does not export it, so libtiff's `check_symbol_exists`
  probe believes in dual 8/12-bit mode, compiles `tif_jpeg_12.c`, and the link dies on
  `jpeg12_*`. `jpeg12: false` alone does NOT help (it guards the other branch).

## libvorbis
[v1.3.7, 0657aee69dec8508a0011f47f3b69d7538e9d262]

- URL: https://github.com/xiph/vorbis.git
- Version: 1.3.7
- Dependencies: libogg
- Usage: Vorbis audio codec. Required by libsndfile.

## libvpx
[v1.17.0, 6df3ec34557879fff673706f4a1d9fbd0f3a6f0e]

- URL: https://github.com/webmproject/libvpx.git
- Version: 1.17.0
- Dependencies: None
- Usage: VP8/VP9 video codec library.
- Notes: Linux and macOS only (configure script requires Cygwin/MSYS2 on Windows).

## libwebp
[1.6.0, 991170bbab3e6afc74666d124f3f1dc7be942cd0]

- URL: https://github.com/webmproject/libwebp.git
- Version: 1.6.0
- Dependencies: None
- Usage: Image format library.

## libzip 
[main, 6f8a0cdd24a0dc6cce9dac4a7679da784ab124ea]

- URL: https://github.com/nih-at/libzip.git
- Version: 1.11.14
- Dependencies: zlib bzip2 xz zstd
- Usage: Compressed archive management library.
- Notes: On Windows, you need to add "PATHS LIBS_ROOT" inside find_package() functions in the CMakeLists.txt before compiling.
- Warning: On Windows, zstd support has been disabled.

## libzmq (ZeroMQ) 
[master, 46493370217ac135246617fa2f6ac819d8b61bfc]

- URL: https://github.com/zeromq/libzmq.git
- Version: 4.3.6~
- Dependencies: None
- Usage: Common IPC library.

## lunasvg
[master, 2a6a43a54de815dc8b7ab96a29ecac1555f610bd]

- URL: https://github.com/sammycage/lunasvg
- Version: 3.5.0~
- Dependencies: None
- Usage: Image format library.
- Warning: **compiled as C++17, not C++20**, in deviation from the build policy: upstream sets
  the `CXX_STANDARD 17` *target property* (CMakeLists.txt:57), which beats the
  `CMAKE_CXX_STANDARD` cache variable. Lifting it needs a patch; the API (Document, Bitmap)
  is the same under both standards.

## meshoptimizer
[v1.2, 9d9890c73011d75920af614485296d1e03e95448]

- URL: https://github.com/zeux/meshoptimizer.git
- Version: 1.2
- Dependencies: None
- Usage: Vertex/index buffer codec behind `EXT_meshopt_compression`. fastgltf *parses* the
  extension (it fills a `fastgltf::CompressedBufferView` per buffer view) but never decodes
  it — there is no `meshopt_decode*` call anywhere in it — so a GLB using the extension feeds
  `iterateAccessor()` raw compressed bytes, silently. Every meshopt buffer view must be
  decoded before any accessor is read.
- Notes: only the decoder is used at runtime (`meshopt_decodeVertexBuffer`,
  `meshopt_decodeIndexBuffer`, plus the inverse filters `meshopt_decodeFilterOct/Quat/Exp`);
  the encoder ships in the same archive and the linker prunes it. Demo and gltfpack are off.

## mpg123
[master, b41e9d9b4f223f8173ea8c9811dd4290a434d6fb]

- URL: https://github.com/madebr/mpg123.git
- Version: 1.34.0
- Dependencies: None
- Usage: MP3 decoder. Required by libsndfile for MP3 read support.
- Notes: Upstream is SourceForge SVN, this is a community git mirror with no release tags, so we pin to a master SHA. Built via the CMake port in `ports/cmake/`.

## onnxruntime (ONNX Runtime)
[v1.29.0, 2e2543fbe9fae542f921d47a72d21d5a4ef0b710]

- URL: https://github.com/microsoft/onnxruntime.git
- Version: 1.29.0 (release tag)
- Dependencies: None *in the cascade* — it vendors its own (abseil, onnx, protobuf, re2,
  flatbuffers, cpuinfo, eigen, GSL, mp11, json, date), all fetched at configure time.
- Usage: cross-platform machine-learning inference engine (ONNX and ORT model formats),
  CPU execution provider only.
- Notes: the CMake project root is `cmake/`, not the repository root. Built consumer-only:
  no unit tests (ON by default upstream), no benchmarks, no python/C#/Objective-C bindings,
  no LTO, RTTI off (upstream's own default here, and what the build policy asks; harmless
  either way since the boundary is the ORT C API and nothing polymorphic crosses it).
  No execution provider beyond CPU — CUDA, TensorRT, DirectML, CoreML, QNN, XNNPACK and
  WebGPU each need a vendor SDK at build time and would make the artifact machine-specific.
- Warning: **shipped as a shared library — the only one in the archive**, so it must be
  deployed next to the executable, unlike every static lib here. This follows a measurement,
  not a preference: with `onnxruntime_BUILD_SHARED_LIB=Off` the install step lays down the
  ten `libonnxruntime_*.a` and nothing else — abseil (50 archives), onnx, protobuf-lite,
  flatbuffers, cpuinfo and friends are `EXCLUDE_FROM_ALL` FetchContent dependencies that no
  install rule reaches, and re2 is never even built (a static library does not link its
  dependencies, so nothing in `all` pulls it in) although `onnxruntime_providers` references
  `re2::RE2`. A consumer link against the installed static set fails on thousands of
  undefined symbols — verified by link test. The shared build links all of it inside
  `libonnxruntime.so` (30.5 MiB; `ldd` shows only libstdc++/libm/libgcc_s/libc) and exports
  just the ORT C API; the C++ API is a header-only wrapper over it, so no C++ ABI crosses
  the boundary either.
- Warning: sizes to plan for — `libonnxruntime.so` is 30.5 MiB in Release but **782 MiB in
  Debug**, and a clean build leaves ~580 MiB of intermediates (Linux, gcc 14.2).
- Warning: **~1 GiB is downloaded at configure time**. `cmake/deps.txt` lists every
  dependency as a URL + SHA1 fetched by FetchContent. Pinned by hash, hence reproducible,
  but the build needs network access — by far the largest such fetch in the cascade.
  `deps.txt` also accepts local file paths, which is the way out if an offline build is
  ever required.
- Warning: the engine cascade compiles with `-fno-exceptions` while the ORT C++ header
  throws `Ort::Exception`. Such translation units must define **`ORT_NO_EXCEPTIONS`** before
  including it (it then abort()s on error instead of throwing). The C API returns
  `OrtStatus*` and never throws.

## openal-soft
[master, b2c48f7718ef3fcf67921a8b6534c4914e328970]

- URL: https://github.com/kcat/openal-soft.git
- Version: 1.25.2
- Notes: This version is stable on all platforms. Beware when updating.
- Dependencies: None
- Usage: Audio API.

## opus
[v1.6.1, 22244de5a79bd1d6d623c32e72bf1954b56235be]

- URL: https://github.com/xiph/opus.git
- Version: 1.6.1
- Dependencies: None
- Usage: Opus audio codec. Required by libsndfile.

## pthread-win32
[master, 334dd243487013a7faa3a9b96afa5264fcfb09ba]

- URL: https://github.com/GerHobbelt/pthread-win32.git
- Version: 4.1.0.9
- Dependencies: None
- Usage: Thread library.
- Notes: Only for Windows.

## reproc
[v14.2.8, 904a0dc087674729c334eccb8bafc142aa0d1c92]

- URL: https://github.com/DaanDeMeyer/reproc.git
- Version: 14.2.8
- Dependencies: None
- Usage: Cross-platform process control library (C `reproc` + C++ `reproc++`). Both static libraries are built and installed.
- Warning: **compiled as C++11 (and C99), not C++20**, in deviation from the build policy:
  reproc sets `CXX_STANDARD 11` as a target property on every target it creates
  (cmake/reproc.cmake:111), which beats the cache variable. reproc++ is a thin RAII layer over
  the C API and presents the same surface either way.

## simdjson
[v4.6.9, 0a2e33f345f49cb6e24401d5b16dbdbc9650921a]

- URL: https://github.com/simdjson/simdjson.git
- Version: 4.6.9 (release tag — the tagged commit is titled "Release candidate 4.6.9"
  because that is upstream's wording for its release-prep commit; `simdjson_version.h` on
  that commit says a bare `4.6.9`)
- Dependencies: None
- Usage: SIMD-accelerated JSON parser (DOM and On-Demand APIs), for the JSON the engine
  reads outside glTF — configuration, manifests, descriptors. 4.x also ships a serialisation
  side (`simdjson::builder`, `include/simdjson/builder.h`), so it overlaps jsoncpp more than
  the name suggests; which of the two owns which use is an engine-side decision, not a build
  one.
- Notes: built with runtime dispatch, which is the whole point of the library — every x86
  kernel it can compile (fallback, westmere, haswell, icelake) is in the archive and the CPU
  is probed on first use, so **never** narrow it with `SIMDJSON_IMPLEMENTATION` or
  `-march=native`. Compiled as C++20 to match the engine, developer mode off (that is what
  pulls tests, benchmarks, fuzzers and cxxopts).
- Warning: **consumers must define `SIMDJSON_THREADS_ENABLED=1`** — and this one is an ABI
  matter, not a preference. It adds four data members to `document_stream` (the worker
  thread, its parser, its error and the `use_thread` flag), so a consumer that omits it sees
  a smaller class than the code it links against: a silent layout mismatch, not a link
  error. Upstream ships the macro as a PUBLIC definition on its CMake target, which anything
  linking the raw archive never sees. `DependenciesTest` sets it in `CMakeLists.txt`, and so
  must the engine. The fix is the define and never `SIMDJSON_ENABLE_THREADS=OFF`: this
  library is in the archive because it is the fast parser, and building the threads out
  would remove the one path where it uses a core beyond the caller's — `document_stream`'s
  background stage-1 thread over NDJSON and multi-document batches.
- Warning: **the only installed header is the amalgamated `singleheader/simdjson.h`**
  (7.7 MiB, 187k lines) copied to `include/simdjson.h`; upstream has no
  `install(DIRECTORY include/)` at all. So `SIMDJSON_SINGLEHEADER` must stay ON — turning it
  off (its help text reads "Disable singleheader generation", which invites the mistake)
  installs the library with **no header whatsoever**. The file is checked into the
  repository at release time, so nothing is generated and Python is not needed.
- Warning: `CMAKE_CXX_STANDARD` is ignored here, so do not reach for it —
  `cmake/developer-options.cmake` does a plain
  `set(CMAKE_CXX_STANDARD ${SIMDJSON_CXX_STANDARD})`, and a normal variable shadows the
  cache entry a `-D` sets: the command line is silently dropped. The knob is
  `SIMDJSON_CXX_STANDARD` (cache variable, default 17), set to 20 in the YAML.
- Warning: **the archive is built without the exception-throwing interface**
  (`SIMDJSON_EXCEPTIONS=OFF`), because the engine that consumes it compiles without
  exceptions — so **consumers must define `SIMDJSON_EXCEPTIONS=0`** as well. This selects an
  API, not a detail: `simdjson_result<T>` no longer converts implicitly to `T`, and every
  access takes the error-code form, `if (doc["k"].get_string().get(view) != simdjson::SUCCESS)`.
  See `test_simdjson()` in `src/main.cpp` for the shape. Unlike `SIMDJSON_THREADS_ENABLED`,
  forgetting this one fails at compile time rather than silently. Verified: a consumer built
  with `-fno-exceptions` links and runs against the archive.
- Warning: on MSVC, turning exceptions off also rewrites `/EHsc` into `/EHs-c-` and adds a
  global `-D_HAS_EXCEPTIONS=0` (`cmake/exception-flags.cmake`). That is intended here — it
  is what makes simdjson match an exception-free engine — but it makes this the only library
  of the cascade built with a different STL configuration, so the Windows package is the
  first place to look if a mixed-mode link ever misbehaves.

## spirv-headers
[vulkan-sdk-1.4.357.0, 29981f65241605e08b0ede4cfeb999fe3b723c6a]

- URL: https://github.com/KhronosGroup/SPIRV-Headers.git
- Version: vulkan-sdk-1.4.357.0
- Dependencies: None
- Usage: SPIR-V header files (enums, opcodes). Consumed by spirv-tools.
- Notes: Commit pinned to glslang 16.5.0's `known_good.json` to keep the SPIR-V toolchain
  coherent. This trio (spirv-headers, spirv-tools, glslang) is bumped **together**, always
  from that file — never library by library.

## spirv-tools
[v2026.3, b707790a898e44038547df54580022fc1cf89c3d]

- URL: https://github.com/KhronosGroup/SPIRV-Tools.git
- Version: 2026.3 (the commit glslang 16.5.0 asks for happens to be the v2026.3 release tag,
  where the previous pin sat on a release candidate)
- Dependencies: spirv-headers
- Usage: SPIR-V parsing, validation, optimization and linking. Consumed by glslang's SPIR-V optimizer (`SPIRV-Tools-opt`).
- Notes: Built with `SPIRV_TOOLS_BUILD_STATIC=ON` and `SPIRV-Headers_SOURCE_DIR=${INSTALL_PREFIX}` so the headers from the previously installed `spirv-headers` package are reused (no `add_subdirectory` of headers). Commit pinned to glslang 16.5.0's `known_good.json`.
- Notes: `patches/spirv-tools.patch` adds the `SPIRV_TOOLS_BUILD_SHARED` gate upstream lacks
  (it always builds `libSPIRV-Tools-shared`) and fixes an upstream typo that links mimalloc
  into the *shared* target from inside the *static* branch. Re-verified against v2026.3: the
  patch still applies unchanged and the typo is still there. Its `# target-commit:` guard is
  updated with every bump.

## taglib 
[v2.3.1, 54ae7d8ac45755e286a5c574280f48d5bef93aef]

- URL: https://github.com/taglib/taglib.git
- Version: 2.3.1
- Dependencies: zlib
- Usage: Audio meta-data library.
- Warning: **compiled as C++17, not C++20**, in deviation from the build policy: taglib does
  `set(CMAKE_CXX_STANDARD 17)` unconditionally at the top of its CMakeLists, so the builder's
  `-DCMAKE_CXX_STANDARD=20` is silently overridden. Lifting it needs a patch; the API
  (TagLib::String, FileRef) is the same under both standards.

## tinyusdz
[v1.0.0-rc3, 7f5b62c3d32064ae0d10eaebd40d0bdf720b485a]

- URL: https://github.com/lighttransport/tinyusdz.git
- Version: 1.0.0-rc3
- Dependencies: None (C++ STL only)
- Usage: OpenUSD reader (USDA / USDC crate / USDZ) for the engine's SceneLoaders. Built with
  `TINYUSDZ_CXX_EXCEPTIONS=Off` (the cascade is `-fno-exceptions`); MaterialX, audio, the C API,
  the pxr-compat shim and the side importers (obj/vox/fbx/gltf) are all disabled. Tydra is kept
  for material-binding and GeomSubset resolution.
- Patch: upstream installs ONLY its optional C API shared library, so a stock build exports
  nothing at all while reporting success. `patches/tinyusdz.patch` adds the install rules for
  the static library, the header tree (layout preserved — headers include one another by
  relative path) and a CMake package config. It also fixes two build-level details: the
  `../../src/` include paths in `tydra/shape-to-mesh.hh`, and a `NOMINMAX` / `WIN32_LEAN_AND_MEAN`
  guard before the `<windows.h>` that `nonstd/expected.hpp` pulls in on MSVC as soon as
  exceptions are off (its min/max macros otherwise shred every `std::numeric_limits<T>::max()`).
- Warning: **the pin is a release candidate**, a deliberate exception to the rule that had kept
  this library on v0.9.4. Upstream has cut no final release since 0.9.4 — as of 2026-08-31 the
  tag line runs `v0.9.9-rc1..rc7` then `v1.0.0-rc1..rc3` — so the choice was between an RC and a
  reader two major versions behind. Revisit when 1.0.0 final lands.
- Warning: **the seven composition and material fixes this repository used to carry are gone**,
  re-verified against v1.0.0-rc3 rather than assumed. Three are fixed verbatim upstream (the
  `material:binding`-with-no-target abort, `st` authored as `float2[]`, and the
  `is_connection()` → `has_connections()` texture defect that made every material come back
  flat grey). One became an API option the **engine** must now set: `allow_parent_relative_paths`
  defaults to **false** (`composition.hh:81,104,157`), and a Kit-exported stage writes its
  subLayers as `../Source/…`, so with the default those layers are silently rejected. The last
  three were absorbed by a rewrite of the composition engine (`src/composition-graph.cc`, a
  task-queue prim-index builder). **Composition is therefore unmeasured on this version**: four
  of the seven defects used to fail silently or report SUCCESS, so it is only ever trusted on a
  prim/mesh/texture count — see `docs/todo/remeasure-tinyusdz-composition.md`.
- Note: `TINYUSDZ_WITH_TEXTOOLS` (new in 1.0.0, ON upstream) is turned off. It builds a second
  static library and links it into the core for KTX2 / GPU-compressed decode inside USDZ, which
  the engine already covers with libktx and bc7enc_rdo; leaving it on would also add a second
  archive to the package and to every consumer's link line.
- Warning: **compiled as C++17, not C++20**, in deviation from the build policy: tinyusdz sets
  `CMAKE_CXX_STANDARD` unconditionally inside its own branches, and the only branch yielding
  C++20 is gated on `TINYUSDZ_WITH_COROUTINE` — a feature switch, not a standard switch, so it
  must not be turned on just to move the standard.

## ufbx
[v0.23.0, fcc5d6ba444cfd3eb80677dba5e37e493941abe5]

- URL: https://github.com/ufbx/ufbx.git
- Version: 0.23.0
- Dependencies: None (links libm on Unix)
- Usage: Single-translation-unit FBX 7.x parser. Used for skeletal mesh/animation import.
- Notes: Upstream is header + single `.c`, no CMakeLists.txt. The patch adds a minimal one that builds a static library and installs `ufbx.h` under `include/ufbx/`.

## xz (LZMA) 
[v5.8, 4b73f2ec19a99ef465282fbce633e8deb33691b3]

- URL: https://github.com/tukaani-project/xz.git
- Version: 5.8.3
- Dependencies: None
- Usage: Compression library.

## zlib 
[v1.3.2, da607da739fa6047df13e66a2af6b8bec7c2a498]

- URL: https://github.com/madler/zlib.git
- Version: 1.3.2
- Dependencies: None
- Usage: Compression library.
- Notes: This version builds the static and the shared libraries, beware when linking. An upcoming release will fix this with cmake options.

## zstd (Zstandard)
[release, f8745da6ff1ad1e7bab384bd1f9d742439278e99]

- URL: https://github.com/facebook/zstd.git
- Version: 1.5.7
- Dependencies: pthread-win32 on Windows
- Usage: Compression library.
- Notes: This version builds the static and the shared libraries, beware when linking.

## libressl
[VENDORED — release tarball, NOT a git submodule]

- Source: https://ftp.openbsd.org/pub/OpenBSD/LibreSSL/libressl-4.3.2.tar.gz
- Version: 4.3.2 (first stable of the 4.3 branch; LibreSSL convention: x.y.0/x.y.1 are
  development snapshots, x.y.2 is the first stable of a branch)
- SHA256: edf01aee24c65d69e6a9efcb9d44bcda682ff9d4f3bbbd95e794e1dfa90847b5
- Dependencies: None
- Usage: TLS/crypto provider (libtls + libssl + libcrypto). Consumed by emeraude-base's
  HTTPS client through `asio::ssl` (OpenSSL-compatible API). Chosen over OpenSSL because
  LibreSSL-portable builds with CMake, whereas OpenSSL's perl `Configure` would require a
  bespoke builder plus perl/nasm build deps in this CMake-centric generator.
- **Notes — THE ONE VENDORED DEPENDENCY.** Unlike every other library here, LibreSSL is
  NOT a git submodule: its full release sources are committed under `repositories/libressl/`.
  The `libressl/portable` git repo is not self-contained (crypto/ssl/tls hold only build
  files; the real sources are pulled from OpenBSD by `update.sh` at build time), so the
  reproducible form is the release tarball. See "Updating LibreSSL (vendored)" above and the
  "Vendored Sources" section in `AGENTS.md`. `check_releases.py` does NOT track it (it only
  sees `.gitmodules`) — check for new releases manually at https://www.libressl.org/releases.html

# Upcoming libraries

- OCCT (Open Cascade) (https://github.com/Open-Cascade-SAS/OCCT.git)

# Requirements and build process

The repository uses a unified Python build system (`build.py`) that works on all platforms.
The `builds/` directory will contain the compilation files.
The `output/` directory will contain the final library files to ship.

## Prerequisites

Every platform needs the same core toolchain: **Python 3.10+**, **CMake 3.25.1+**,
**Ninja**, **Meson**, **Autotools** (autoconf, automake, libtool), and **NASM**
(for libjpeg-turbo / libvpx assembly optimizations). What differs is the
compiler and how you install everything.

### Linux (Debian/Ubuntu)

GCC 12+ is required. For other distributions, install the equivalent packages.

```bash
sudo apt install build-essential python3 python3-pip python3-venv cmake meson ninja-build autoconf automake libtool nasm
```

A few libraries probe for system development headers and silently disable
optional features if they are missing. The most consequential case is
**openal-soft**: with no audio backend `-dev` packages installed, CMake drops
ALSA / PulseAudio / PipeWire / JACK detection and produces a `libopenal.a`
that links but cannot open any device at runtime. The build now refuses to
finish in that state (see [Post-build assertions](#post-build-assertions)),
so install the audio dev headers before running `build.py`:

```bash
sudo apt install libasound2-dev libpulse-dev libpipewire-0.3-dev libjack-jackd2-dev
```

### macOS

Xcode Command Line Tools with macOS SDK 12.0+ is required.

```bash
# Install Homebrew if not already installed (see https://brew.sh)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install python3 cmake meson ninja autoconf automake libtool nasm
```

### Windows

Install each tool separately (no single package manager):

- **Visual Studio 2022** with the MSVC v143 toolchain
- **Python 3.10+** — https://www.python.org/downloads/ (check *Add Python to PATH*)
- **CMake 3.25.1+** — https://cmake.org/download/
- **Ninja** and **Meson** — via `pip install ninja meson` (after Python is installed)
- **NASM** — https://www.nasm.us/pub/nasm/releasebuilds/?C=M;O=D
- **MSYS2** (required to build libvpx) — https://www.msys2.org/
  - After install, run `pacman -S make diffutils` inside MSYS2
  - Set the `MSYS2_PATH` env var if MSYS2 is not at `C:\msys64`

Autotools is not needed on Windows: the libraries that use it (hwloc, libvpx)
fall back to alternate build paths there.

## Python virtual environment

Same steps on every platform — only the activation command changes:

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

```powershell
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Build commands

### List available libraries

```bash
python build.py --list --macos-sdk 12.0   # macOS
python build.py --list                     # Linux/Windows
```

### Build all libraries

```bash
# Linux
python3 build.py --arch x86_64 --build-type Release
python3 build.py --arch x86_64 --build-type Debug

# macOS (Apple Silicon)
python3 build.py --macos-sdk 12.0 --arch arm64 --build-type Release
python3 build.py --macos-sdk 12.0 --arch arm64 --build-type Debug

# macOS (Intel)
python3 build.py --macos-sdk 12.0 --arch x86_64 --build-type Release
python3 build.py --macos-sdk 12.0 --arch x86_64 --build-type Debug

# Windows (DLL runtime)
python build.py --arch x86_64 --build-type Release --runtime-lib MD
python build.py --arch x86_64 --build-type Debug --runtime-lib MD

# Windows (Static runtime)
python build.py --arch x86_64 --build-type Release --runtime-lib MT
python build.py --arch x86_64 --build-type Debug --runtime-lib MT
```

### Build a single library (with dependencies)

```bash
python build.py --macos-sdk 12.0 --library freetype
```

### Build a single library (without dependencies)

```bash
python build.py --macos-sdk 12.0 --library freetype --no-deps
```

### Dry run (show what would be built)

```bash
python build.py --macos-sdk 12.0 --dry-run
```

## Command-line options

| Option | Description | Default |
|--------|-------------|---------|
| `--arch` | Target architecture (`x86_64`, `arm64`) | `x86_64` |
| `--build-type` | Build type (`Release`, `Debug`) | `Release` |
| `--macos-sdk` | macOS deployment target (required on macOS) | - |
| `--runtime-lib` | Windows runtime library (`MD`, `MT`) | `MD` |
| `--library` | Build only this library | - |
| `--no-deps` | Don't build dependencies | `false` |
| `--list` | List available libraries | - |
| `--dry-run` | Show build plan without building | - |

## Post-build assertions

Some libraries can produce an artifact that links cleanly but is broken at
runtime when an optional dependency was missing on the build host. The
canonical example is OpenAL-soft: `ALSOFT_REQUIRE_*=Off` lets CMake disable
ALSA / PulseAudio / PipeWire / JACK when their dev headers are absent, and
the resulting `libopenal.a` then fails `alcOpenDevice()` with
`ALC_INVALID_VALUE` on every modern Linux box.

To catch these silent dropouts at build time rather than at runtime, a
library YAML can declare assertions that run after the install step:

```yaml
platforms:
  linux:
    post_build_assertions:
      - kind: require_any_define
        file: config.h                   # relative to the build dir
        defines: [HAVE_ALSA, HAVE_PULSEAUDIO, HAVE_PIPEWIRE, HAVE_JACK]
        message: |
          Human-readable remediation, printed when the assertion fails.
```

Failing assertions abort the build with the message embedded in the YAML.
The check is opt-in — libraries without a `post_build_assertions` section
behave as before. Currently wired into the CMake builder
(`builder/cmake_builder.py`); see `builder/config.py::Library.verify_post_build`
for the implementation. Extending to other builders is a 5-line copy if a
non-CMake library ever needs the same guard.

## Windows runtime library notes

Libraries for Windows are separated between:
- **MD/MDd**: Dynamic runtime (`MultiThreadedDLL`, `MultiThreadedDebugDLL`)
- **MT/MTd**: Static runtime (`MultiThreaded`, `MultiThreadedDebug`)

To verify `.lib` files, open "Developer Command Prompt" and run:

```powershell
Get-ChildItem -Recurse -Filter *.lib | ForEach-Object { $file = $_; dumpbin /directives $file.FullName 2>&1 | Select-String 'LIBCMTD?|MSVCRTD?' | ForEach-Object { $_.Matches.Value } | ForEach-Object { [PSCustomObject]@{ CRT = $_; Fichier = $file.Name } } } | Group-Object -Property CRT
```

Expected results:
- **MT** builds: only `LIBCMT`
- **MTd** builds: only `LIBCMTD`
- **MD** builds: only `MSVCRT`
- **MDd** builds: only `MSVCRTD`

## Release assets creation

Quick recap and reminder to release assets on GitHub. Here is an example for separated uploads for the assets v013.

*Notes* : Use --clobber to overwrite.

*Notes* : since onnxruntime joined the set, `output/<config>/lib` contains a **versioned
shared library and its symlinks** (`libonnxruntime.so` -> `.so.1` -> `.so.1.29.0`, and the
`.dylib` equivalents). Zip them with `zip -y` (store symlinks as symlinks); without it the
30 MiB library is copied three times into the archive.

```
# Create the release
gh release create v013 --repo EmeraudeEngine/ext-deps-generator --title "External dependencies v013" --notes "Precompiled binaries for Emeraude-Engine"

# Linux — the archive folder name now carries the host's glibc floor
# (e.g. glibc2.35), which supersedes the old per-distro naming: the glibc
# version is the actual cross-distro compatibility boundary, distro name was
# only a proxy for it. Adjust the token to match your build host / sysroot.
gh release upload v013 --repo EmeraudeEngine/ext-deps-generator linux.x86_64-Release-glibc2.35.v013.zip
gh release upload v013 --repo EmeraudeEngine/ext-deps-generator linux.x86_64-Debug-glibc2.35.v013.zip

# Apple macOS — folder name carries the deployment target (sdk<ver>)
gh release upload v013 --repo EmeraudeEngine/ext-deps-generator macos.arm64-Release-sdk12.0.v013.zip
gh release upload v013 --repo EmeraudeEngine/ext-deps-generator macos.arm64-Debug-sdk12.0.v013.zip
gh release upload v013 --repo EmeraudeEngine/ext-deps-generator macos.x86_64-Release-sdk12.0.v013.zip
gh release upload v013 --repo EmeraudeEngine/ext-deps-generator macos.x86_64-Debug-sdk12.0.v013.zip

# Microsoft Windows
gh release upload v013 --repo EmeraudeEngine/ext-deps-generator windows.x86_64-Release-MD.v013.zip
gh release upload v013 --repo EmeraudeEngine/ext-deps-generator windows.x86_64-Debug-MD.v013.zip
gh release upload v013 --repo EmeraudeEngine/ext-deps-generator windows.x86_64-Release-MT.v013.zip
gh release upload v013 --repo EmeraudeEngine/ext-deps-generator windows.x86_64-Debug-MT.v013.zip
```

## TODO list

## Archive hardening

### 1. SHA256 integrity check on archive download

**Why:** Currently `InstallExternalDependencies.cmake` (engine side) downloads the
archive via `file(DOWNLOAD)` with no integrity verification. Nothing protects
against transit corruption, GitHub Release tampering, or a hijacked CDN.

**What:**
- `build.py` (or release pipeline) emits a `SHA256SUMS.txt` next to each archive
  when uploading to GitHub Releases (one line per platform/runtime variant).
- Engine's `InstallExternalDependencies.cmake` is updated to pass
  `EXPECTED_HASH SHA256=<hash>` to `file(DOWNLOAD)`. The hash table can be
  inlined in the cmake script (one entry per `EXTERNAL_DEPENDENCIES_FILENAME`).
- Failure → hard FATAL_ERROR with the expected vs actual hash diff.

**Cost:** ~5 lines CMake on engine side, 1 line per archive on the release
script side. Trivial maintenance burden.

### 2. Smoke-test suite per dependency

**Why:** The lame/FLAC/mpg123/shlwapi cascade (May 2026) wasn't detected at
ext-deps-generator build time — only when the engine itself linked. Every
library install was "successful" but the produced binaries had missing
symbols (lame `init_xrpow_core_sse`) or missing transitive deps (mpg123 →
shlwapi). A minimal "can I link a hello-world against this lib" check would
have caught all four bugs.

**What:**
- Add a `smoke_tests/<libname>.c` per library: tiny program that calls 1-2
  public APIs (e.g. `FLAC__stream_decoder_new` + `delete`, `lame_init` +
  `lame_close`, `sf_open` + `sf_close`).
- After `cmake --install`, the builder compiles + links + runs the smoke test
  against the installed library, against the **same toolchain/runtime** as
  the build itself. Failure aborts the build.
- For Windows static libs, the smoke test runs through the same MT/MD config
  so the runtime mismatch is caught here too.

**Cost:** ~10-30 lines C per library (40 libs ≈ 600 LOC), plus harness in
`builder/`. Higher upfront cost but pays off every time a lib's source layout
changes or a new platform comes online.

**Stretch:** the smoke tests double as compilation examples for downstream
users — they document the canonical `find_package` / link invocation per lib.
