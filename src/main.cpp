/**
 * Dependencies inclusion test
 *
 * This file tests that all libraries can be included and linked
 * without conflicts. Each library gets a simple API call to verify linkage.
 */

#include <iostream>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <sstream>
#include <string>
#include <vector>

// ============================================================================
// Compression libraries
// ============================================================================

// zlib
#include "zlib.h"

// bzip2
#include "bzlib.h"

// xz/lzma
#include "lzma.h"

// zstd
#include "zstd.h"

// brotli
#include "brotli/encode.h"
#include "brotli/decode.h"

// ============================================================================
// Image libraries
// ============================================================================

// libpng
#include "png.h"

// libjpeg-turbo
#include "jpeglib.h"
#include "turbojpeg.h"

// libwebp
#include "webp/encode.h"
#include "webp/decode.h"

// libtiff (C API + C++ stream API from the tiffxx archive)
#include "tiffio.h"
#include "tiffio.hxx"

// ============================================================================
// Video libraries
// ============================================================================

// libvpx
#include "vpx/vpx_codec.h"

// ============================================================================
// Font libraries
// ============================================================================

// freetype
#include "ft2build.h"
#include FT_FREETYPE_H

// harfbuzz
#include "harfbuzz/hb.h"

// ============================================================================
// Audio codec libraries
// ============================================================================

// libogg
#include "ogg/ogg.h"

// libvorbis
#include "vorbis/codec.h"

// opus
#include "opus/opus.h"

// flac (FLAC__NO_DLL must be set on Windows to use the static lib)
#include "FLAC/format.h"
#include "FLAC/stream_decoder.h"

// mpg123
#include "mpg123.h"

// lame
#include "lame/lame.h"

// ============================================================================
// Audio I/O / metadata libraries
// ============================================================================

// OpenAL-Soft
#include "AL/al.h"
#include "AL/alc.h"

// libsamplerate
#include "samplerate.h"

// taglib
#include "taglib/fileref.h"
#include "taglib/tag.h"

// libsndfile
#include "sndfile.h"

// ============================================================================
// Archive / utility libraries
// ============================================================================

// libzip
#include "zip.h"

// ============================================================================
// System libraries
// ============================================================================

// cpu_features
#if defined(__x86_64__) || defined(_M_X64)
#include "cpu_features/cpuinfo_x86.h"
#elif defined(__aarch64__) || defined(_M_ARM64)
#include "cpu_features/cpuinfo_aarch64.h"
#endif

// hwloc
#include "hwloc.h"

// pthread-win32 (Windows only)
#if defined(_WIN32)
#include "pthread.h"
#endif

// ============================================================================
// Crypto libraries
// ============================================================================

// cryptopp
#include "cryptopp/cryptlib.h"
#include "cryptopp/sha.h"

// libressl (OpenSSL-compatible API + libtls)
#include "openssl/opensslv.h"
#include "openssl/crypto.h"
#include "tls.h"

// ============================================================================
// Geometry libraries
// ============================================================================

// clipper2
#include "clipper2/clipper.h"

// ============================================================================
// Networking libraries
// ============================================================================

// libzmq
#include "zmq.h"

// cppzmq (header-only wrapper)
#include "zmq.hpp"

// ============================================================================
// Process control libraries
// ============================================================================

// reproc (C API)
#include "reproc/reproc.h"

// reproc++ (C++ wrapper)
#include "reproc++/reproc.hpp"

// ============================================================================
// Data format libraries
// ============================================================================

// fastgltf
#include "fastgltf/core.hpp"

// jsoncpp
#include "json/json.h"

// ufbx
#include "ufbx/ufbx.h"

// meshoptimizer (EXT_meshopt_compression codec)
#include "meshoptimizer.h"

// tinyusdz (OpenUSD reader)
#include "tinyusdz/tinyusdz.hh"

// lib3mf (shared library, C ABI)
#include "Bindings/C/lib3mf.h"

// ============================================================================
// SVG libraries
// ============================================================================

// lunasvg
#include "lunasvg/lunasvg.h"

// ============================================================================
// Shader / SPIR-V libraries
// ============================================================================

// spirv-tools
#include "spirv-tools/libspirv.h"

// glslang
#include "glslang/Public/ShaderLang.h"
#include "glslang/build_info.h"

// ============================================================================
// Texture compression libraries
// ============================================================================

// bc7enc_rdo
#include "bc7enc_rdo/bc7enc.h"

// ktx (KHRONOS_STATIC must be set on Windows to use the static lib)
#include "ktx.h"


// ============================================================================
// Test functions
// ============================================================================

static bool test_zlib()
{
    std::cout << "  zlib version: " << zlibVersion() << "\n";
    return true;
}

static bool test_bzip2()
{
    std::cout << "  bzip2 version: " << BZ2_bzlibVersion() << "\n";
    return true;
}

static bool test_lzma()
{
    std::cout << "  lzma version: " << lzma_version_string() << "\n";
    return true;
}

static bool test_zstd()
{
    std::cout << "  zstd version: " << ZSTD_versionString() << "\n";
    return true;
}

static bool test_brotli()
{
    uint32_t version = BrotliEncoderVersion();
    std::cout << "  brotli version: " << (version >> 24) << "."
              << ((version >> 12) & 0xFFF) << "." << (version & 0xFFF) << "\n";
    return true;
}

static bool test_libpng()
{
    std::cout << "  libpng version: " << png_libpng_ver << "\n";
    return true;
}

static bool test_libjpeg()
{
    if (tjhandle handle = tjInitCompress())
    {
        tjDestroy(handle);
        std::cout << "  libjpeg-turbo: OK (turbojpeg API)\n";
        return true;
    }
    return false;
}

static bool test_libwebp()
{
    int version = WebPGetEncoderVersion();
    std::cout << "  libwebp version: " << (version >> 16) << "."
              << ((version >> 8) & 0xFF) << "." << (version & 0xFF) << "\n";
    return true;
}

static bool test_libtiff()
{
    // TIFFGetVersion() returns a multi-line banner; keep the first line only.
    std::string version = TIFFGetVersion();
    const size_t eol = version.find('\n');
    if (eol != std::string::npos)
        version.resize(eol);
    std::cout << "  " << version << "\n";

    // Write a 2x2 grayscale TIFF compressed with LZMA through the C++ stream API,
    // then read it back. This deliberately exercises the libtiff <-> lzma boundary:
    // tif_lzma.obj is only pulled in when the LZMA codec is used, and on MSVC a
    // libtiff built without LZMA_API_STATIC leaves it referencing __imp_lzma_* that
    // the static lzma.lib cannot satisfy (see libraries/libtiff.yaml). The stream
    // API also validates the tiffxx archive (TIFFStreamOpen).
    const uint8_t pixels[4] = {0x00, 0x42, 0x84, 0xFF};

    std::ostringstream output;
    TIFF* wtif = TIFFStreamOpen("memory-out", &output);
    if (wtif == nullptr)
        return false;
    TIFFSetField(wtif, TIFFTAG_IMAGEWIDTH, 2);
    TIFFSetField(wtif, TIFFTAG_IMAGELENGTH, 2);
    TIFFSetField(wtif, TIFFTAG_BITSPERSAMPLE, 8);
    TIFFSetField(wtif, TIFFTAG_SAMPLESPERPIXEL, 1);
    TIFFSetField(wtif, TIFFTAG_ROWSPERSTRIP, 2);
    TIFFSetField(wtif, TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_MINISBLACK);
    TIFFSetField(wtif, TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG);
    TIFFSetField(wtif, TIFFTAG_COMPRESSION, COMPRESSION_LZMA);
    bool written = true;
    for (uint32_t row = 0; row < 2 && written; ++row)
        written = TIFFWriteScanline(wtif, const_cast< uint8_t* >(&pixels[row * 2]), row) == 1;
    TIFFClose(wtif);
    if (!written || output.str().empty())
    {
        std::cerr << "  libtiff: LZMA-compressed write failed\n";
        return false;
    }

    std::istringstream input(output.str());
    TIFF* rtif = TIFFStreamOpen("memory-in", &input);
    if (rtif == nullptr)
        return false;
    uint8_t readback[4] = {};
    bool read = true;
    for (uint32_t row = 0; row < 2 && read; ++row)
        read = TIFFReadScanline(rtif, &readback[row * 2], row) == 1;
    TIFFClose(rtif);
    if (!read || std::memcmp(readback, pixels, sizeof(pixels)) != 0)
    {
        std::cerr << "  libtiff: LZMA round-trip mismatch\n";
        return false;
    }

    std::cout << "  libtiff: OK (LZMA round-trip, " << output.str().size()
              << "-byte in-memory TIFF)\n";
    return true;
}

static bool test_libvpx()
{
    std::cout << "  libvpx version: " << vpx_codec_version_str() << "\n";
    return true;
}

static bool test_freetype()
{
    FT_Library library;
    if (FT_Init_FreeType(&library) == 0)
    {
        FT_Int major, minor, patch;
        FT_Library_Version(library, &major, &minor, &patch);
        std::cout << "  freetype version: " << major << "." << minor << "." << patch << "\n";
        FT_Done_FreeType(library);
        return true;
    }
    return false;
}

static bool test_harfbuzz()
{
    std::cout << "  harfbuzz version: " << hb_version_string() << "\n";
    return true;
}

static bool test_libogg()
{
    oggpack_buffer ob;
    oggpack_writeinit(&ob);
    oggpack_writeclear(&ob);
    std::cout << "  libogg: OK (oggpack init/clear)\n";
    return true;
}

static bool test_libvorbis()
{
    std::cout << "  libvorbis version: " << vorbis_version_string() << "\n";
    return true;
}

static bool test_opus()
{
    std::cout << "  opus version: " << opus_get_version_string() << "\n";
    return true;
}

static bool test_flac()
{
    std::cout << "  flac version: " << FLAC__VERSION_STRING << "\n";
    return true;
}

static bool test_mpg123()
{
    if (mpg123_init() != MPG123_OK)
        return false;
    unsigned int major = 0, minor = 0, patch = 0;
    const char* ver = mpg123_distversion(&major, &minor, &patch);
    std::cout << "  mpg123 version: " << (ver ? ver : "unknown")
              << " (" << major << "." << minor << "." << patch << ")\n";
    mpg123_exit();
    return true;
}

static bool test_lame()
{
    std::cout << "  lame version: " << get_lame_version() << "\n";
    return true;
}

static bool test_libsndfile()
{
    SF_INFO info;
    info.format = 0;
    char version[128] = {0};
    sf_command(nullptr, SFC_GET_LIB_VERSION, version, sizeof(version));
    std::cout << "  libsndfile: " << (version[0] ? version : "OK (linkage verified)") << "\n";
    return true;
}

static bool test_openal()
{
    // Just check we can query the default device name
    const ALCchar* defaultDevice = alcGetString(nullptr, ALC_DEFAULT_DEVICE_SPECIFIER);
    std::cout << "  openal-soft: OK (default device: "
              << (defaultDevice ? defaultDevice : "none") << ")\n";
    return true;
}

static bool test_libsamplerate()
{
    std::cout << "  libsamplerate version: " << src_get_version() << "\n";
    return true;
}

static bool test_taglib()
{
    // TagLib doesn't have a version function, just verify linkage
    TagLib::FileRef f;
    std::cout << "  taglib: OK (linkage verified)\n";
    return true;
}

static bool test_libzip()
{
    std::cout << "  libzip version: " << zip_libzip_version() << "\n";
    return true;
}

static bool test_cpu_features()
{
#if defined(__x86_64__) || defined(_M_X64)
    cpu_features::X86Info info = cpu_features::GetX86Info();
    std::cout << "  cpu_features: OK (x86_64, vendor: " << info.vendor << ")\n";
#elif defined(__aarch64__) || defined(_M_ARM64)
    cpu_features::Aarch64Info info = cpu_features::GetAarch64Info();
    std::cout << "  cpu_features: OK (aarch64, implementer: " << info.implementer << ")\n";
#else
    std::cout << "  cpu_features: OK (platform not specifically tested)\n";
#endif
    return true;
}

static bool test_hwloc()
{
    hwloc_topology_t topology;
    hwloc_topology_init(&topology);
    hwloc_topology_load(topology);

    int depth = hwloc_topology_get_depth(topology);
    std::cout << "  hwloc: OK (topology depth: " << depth << ")\n";

    hwloc_topology_destroy(topology);
    return true;
}

#if defined(_WIN32)
static bool test_pthread_win32()
{
    pthread_t self = pthread_self();
    (void)self;
    std::cout << "  pthread-win32: OK (pthread_self called)\n";
    return true;
}
#endif

static bool test_cryptopp()
{
    CryptoPP::SHA256 hash;
    std::cout << "  cryptopp: OK (SHA256 digest size: " << hash.DigestSize() << ")\n";
    return true;
}

static bool test_libressl()
{
    // Exercises all three archives: tls_init() pulls libtls -> libssl -> libcrypto.
    if (tls_init() != 0)
    {
        std::cout << "  libressl: FAILED (tls_init returned non-zero)\n";
        return false;
    }
    std::cout << "  libressl: OK (" << OpenSSL_version(OPENSSL_VERSION) << ")\n";
    return true;
}

static bool test_clipper2()
{
    Clipper2Lib::Paths64 subject;
    subject.push_back(Clipper2Lib::MakePath({0, 0, 100, 0, 100, 100, 0, 100}));
    double area = Clipper2Lib::Area(subject);
    std::cout << "  clipper2: OK (test area: " << area << ")\n";
    return true;
}

static bool test_libzmq()
{
    int major, minor, patch;
    zmq_version(&major, &minor, &patch);
    std::cout << "  libzmq version: " << major << "." << minor << "." << patch << "\n";
    return true;
}

static bool test_cppzmq()
{
    // cppzmq is header-only, just verify it compiles
    std::cout << "  cppzmq: OK (header-only, compilation verified)\n";
    return true;
}

static bool test_reproc()
{
    reproc_t* proc = reproc_new();
    if (proc == nullptr)
        return false;
    reproc_destroy(proc);
    std::cout << "  reproc: OK (new/destroy)\n";
    return true;
}

static bool test_reproc_cpp()
{
    reproc::process p;
    (void)p;
    std::cout << "  reproc++: OK (process instance created)\n";
    return true;
}

static bool test_fastgltf()
{
    fastgltf::Parser parser;
    std::cout << "  fastgltf: OK (parser created)\n";
    return true;
}

static bool test_jsoncpp()
{
    Json::Value root;
    root["test"] = "hello";
    root["number"] = 42;
    std::cout << "  jsoncpp: OK (created JSON with " << root.size() << " members, test=" << root["test"].asString() << ")\n";
    return true;
}

static bool test_ufbx()
{
    uint32_t v = ufbx_source_version;
    std::cout << "  ufbx source version: "
              << ufbx_version_major(v) << "."
              << ufbx_version_minor(v) << "."
              << ufbx_version_patch(v) << "\n";
    return true;
}

static bool test_meshoptimizer()
{
    // Round-trip a tiny vertex buffer through the codec behind
    // EXT_meshopt_compression (the decoder is the part the engine needs).
    const float vertices[4][3] = {
        {0.0f, 0.0f, 0.0f}, {1.0f, 0.0f, 0.0f}, {1.0f, 1.0f, 0.0f}, {0.0f, 1.0f, 0.0f}};
    const size_t vertexCount = 4;
    const size_t vertexSize = sizeof(vertices[0]);

    std::vector< unsigned char > encoded(meshopt_encodeVertexBufferBound(vertexCount, vertexSize));
    const size_t encodedSize =
        meshopt_encodeVertexBuffer(encoded.data(), encoded.size(), vertices, vertexCount, vertexSize);
    if (encodedSize == 0)
        return false;

    float decoded[4][3] = {};
    if (meshopt_decodeVertexBuffer(decoded, vertexCount, vertexSize, encoded.data(), encodedSize) != 0)
        return false;
    if (std::memcmp(decoded, vertices, sizeof(vertices)) != 0)
        return false;

    std::cout << "  meshoptimizer version: " << (MESHOPTIMIZER_VERSION / 1000) << "."
              << (MESHOPTIMIZER_VERSION % 1000 / 10) << " (vertex codec round-trip, "
              << encodedSize << " bytes)\n";
    return true;
}

static bool test_tinyusdz()
{
    static const char usda[] =
        "#usda 1.0\n"
        "\n"
        "def Xform \"root\"\n"
        "{\n"
        "    def Mesh \"quad\"\n"
        "    {\n"
        "    }\n"
        "}\n";

    tinyusdz::Stage stage;
    std::string warn, err;
    if (!tinyusdz::LoadUSDAFromMemory(reinterpret_cast< const uint8_t* >(usda), sizeof(usda) - 1,
                                      "", &stage, &warn, &err))
    {
        std::cerr << "  tinyusdz: USDA parse failed: " << err << "\n";
        return false;
    }
    if (stage.root_prims().size() != 1)
    {
        std::cerr << "  tinyusdz: expected 1 root prim, got " << stage.root_prims().size() << "\n";
        return false;
    }

    std::cout << "  tinyusdz version: " << tinyusdz::version_major << "."
              << tinyusdz::version_minor << "." << tinyusdz::version_micro
              << " (parsed in-memory USDA, " << stage.root_prims().size() << " root prim)\n";
    return true;
}

static bool test_lib3mf()
{
    Lib3MF_uint32 major = 0, minor = 0, micro = 0;
    Lib3MFResult res = lib3mf_getlibraryversion(&major, &minor, &micro);
    if (res != 0)
        return false;
    std::cout << "  lib3mf version: " << major << "." << minor << "." << micro << "\n";
    return true;
}

static bool test_lunasvg()
{
    auto document = lunasvg::Document::loadFromData(
        R"(<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">)"
        R"(<rect width="100" height="100" fill="red"/></svg>)");
    if (!document) {
        std::cerr << "  lunasvg: SVG parse failed\n";
        return false;
    }

    // Rasterize — exercises the plutovg backend, not just the parser.
    lunasvg::Bitmap bitmap = document->renderToBitmap();
    if (bitmap.isNull() || bitmap.data() == nullptr) {
        std::cerr << "  lunasvg: renderToBitmap returned null\n";
        return false;
    }

    // Bitmap is ARGB32_Premultiplied. On a little-endian host the bytes are
    // laid out as B, G, R, A. Sample (0,0) and confirm we got opaque red.
    const uint8_t* px = bitmap.data();
    const uint8_t b = px[0], g = px[1], r = px[2], a = px[3];
    if (r < 200 || g != 0 || b != 0 || a != 0xFF) {
        std::cerr << "  lunasvg: unexpected pixel "
                  << "R=" << static_cast< int >(r) << " G=" << static_cast< int >(g)
                  << " B=" << static_cast< int >(b) << " A=" << static_cast< int >(a) << "\n";
        return false;
    }

    std::cout << "  lunasvg: OK (rendered " << bitmap.width() << "x" << bitmap.height()
              << ", pixel(0,0) R=" << static_cast< int >(r) << " A=" << static_cast< int >(a) << ")\n";
    return true;
}

static bool test_spirv_tools()
{
    std::cout << "  spirv-tools version: " << spvSoftwareVersionString() << "\n";
    spv_context ctx = spvContextCreate(SPV_ENV_UNIVERSAL_1_0);
    if (ctx == nullptr)
        return false;
    spvContextDestroy(ctx);
    return true;
}

static bool test_glslang()
{
    if (!glslang::InitializeProcess())
        return false;
    glslang::FinalizeProcess();
    std::cout << "  glslang version: "
              << GLSLANG_VERSION_MAJOR << "."
              << GLSLANG_VERSION_MINOR << "."
              << GLSLANG_VERSION_PATCH << "\n";
    return true;
}

static bool test_bc7enc_rdo()
{
    bc7enc_compress_block_init();
    std::cout << "  bc7enc_rdo: OK (compress block table initialized)\n";
    return true;
}

static bool test_ktx()
{
    ktxTextureCreateInfo createInfo = {};
    createInfo.vkFormat = 37; // VK_FORMAT_R8G8B8A8_UNORM (ktx.h takes a raw ktx_uint32_t)
    createInfo.baseWidth = 4;
    createInfo.baseHeight = 4;
    createInfo.baseDepth = 1;
    createInfo.numDimensions = 2;
    createInfo.numLevels = 1;
    createInfo.numLayers = 1;
    createInfo.numFaces = 1;
    createInfo.isArray = KTX_FALSE;
    createInfo.generateMipmaps = KTX_FALSE;

    ktxTexture2* texture = nullptr;
    const KTX_error_code result =
        ktxTexture2_Create(&createInfo, KTX_TEXTURE_CREATE_ALLOC_STORAGE, &texture);
    if (result != KTX_SUCCESS || texture == nullptr)
    {
        std::cerr << "  ktx: ktxTexture2_Create failed: " << ktxErrorString(result) << "\n";
        return false;
    }

    const bool needsTranscoding = ktxTexture2_NeedsTranscoding(texture);
    const ktx_size_t dataSize = ktxTexture_GetDataSize(ktxTexture(texture));
    ktxTexture_Destroy(ktxTexture(texture));

    if (needsTranscoding) // an uncompressed RGBA8 texture never needs transcoding
    {
        std::cerr << "  ktx: unexpected NeedsTranscoding on RGBA8\n";
        return false;
    }

    std::cout << "  ktx: OK (created 4x4 RGBA8 ktxTexture2, dataSize=" << dataSize << ")\n";
    return true;
}


// ============================================================================
// Main
// ============================================================================

int main(int /*argc*/, char* /*argv*/[])
{
    std::cout << "\n";
    std::cout << "========================================\n";
    std::cout << "   Dependencies Inclusion Test\n";
    std::cout << "========================================\n\n";

    int passed = 0;
    int failed = 0;

    auto run_test = [&](const char* name, bool (*test_func)()) {
        std::cout << "[TEST] " << name << "\n";
        try {
            if (test_func()) {
                passed++;
            } else {
                std::cerr << "  FAILED!\n";
                failed++;
            }
        } catch (const std::exception& e) {
            std::cerr << "  EXCEPTION: " << e.what() << "\n";
            failed++;
        }
    };

    std::cout << "--- Compression Libraries ---\n";
    run_test("zlib", test_zlib);
    run_test("bzip2", test_bzip2);
    run_test("lzma", test_lzma);
    run_test("zstd", test_zstd);
    run_test("brotli", test_brotli);

    std::cout << "\n--- Image Libraries ---\n";
    run_test("libpng", test_libpng);
    run_test("libjpeg-turbo", test_libjpeg);
    run_test("libwebp", test_libwebp);
    run_test("libtiff", test_libtiff);

    std::cout << "\n--- Video Libraries ---\n";
    run_test("libvpx", test_libvpx);

    std::cout << "\n--- Font Libraries ---\n";
    run_test("freetype", test_freetype);
    run_test("harfbuzz", test_harfbuzz);

    std::cout << "\n--- Audio Codec Libraries ---\n";
    run_test("libogg", test_libogg);
    run_test("libvorbis", test_libvorbis);
    run_test("opus", test_opus);
    run_test("flac", test_flac);
    run_test("mpg123", test_mpg123);
    run_test("lame", test_lame);

    std::cout << "\n--- Audio I/O Libraries ---\n";
    run_test("openal-soft", test_openal);
    run_test("libsamplerate", test_libsamplerate);
    run_test("taglib", test_taglib);
    run_test("libsndfile", test_libsndfile);

    std::cout << "\n--- Archive/Utility Libraries ---\n";
    run_test("libzip", test_libzip);

    std::cout << "\n--- System Libraries ---\n";
    run_test("cpu_features", test_cpu_features);
    run_test("hwloc", test_hwloc);
#if defined(_WIN32)
    run_test("pthread-win32", test_pthread_win32);
#endif

    std::cout << "\n--- Crypto Libraries ---\n";
    run_test("cryptopp", test_cryptopp);
    run_test("libressl", test_libressl);

    std::cout << "\n--- Geometry Libraries ---\n";
    run_test("clipper2", test_clipper2);

    std::cout << "\n--- Networking Libraries ---\n";
    run_test("libzmq", test_libzmq);
    run_test("cppzmq", test_cppzmq);

    std::cout << "\n--- Process Control Libraries ---\n";
    run_test("reproc", test_reproc);
    run_test("reproc++", test_reproc_cpp);

    std::cout << "\n--- Data Format Libraries ---\n";
    run_test("fastgltf", test_fastgltf);
    run_test("jsoncpp", test_jsoncpp);
    run_test("ufbx", test_ufbx);
    run_test("meshoptimizer", test_meshoptimizer);
    run_test("tinyusdz", test_tinyusdz);
    run_test("lib3mf", test_lib3mf);

    std::cout << "\n--- SVG Libraries ---\n";
    run_test("lunasvg", test_lunasvg);

    std::cout << "\n--- Shader / SPIR-V Libraries ---\n";
    run_test("spirv-tools", test_spirv_tools);
    run_test("glslang", test_glslang);

    std::cout << "\n--- Texture Compression Libraries ---\n";
    run_test("bc7enc_rdo", test_bc7enc_rdo);
    run_test("ktx", test_ktx);

    std::cout << "\n========================================\n";
    std::cout << "   Results: " << passed << " passed, " << failed << " failed\n";
    std::cout << "========================================\n\n";

    return failed > 0 ? EXIT_FAILURE : EXIT_SUCCESS;
}
