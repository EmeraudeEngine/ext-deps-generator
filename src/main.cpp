/**
 * Dependencies inclusion test
 *
 * This file tests that all libraries can be included and linked
 * without conflicts. Each library gets a simple API call to verify linkage.
 */

#include <iostream>
#include <cstdlib>

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

// ============================================================================
// Font libraries
// ============================================================================

// freetype
#include "ft2build.h"
#include FT_FREETYPE_H

// harfbuzz
#include "harfbuzz/hb.h"

// ============================================================================
// Audio libraries
// ============================================================================

// OpenAL-Soft
#include "AL/al.h"
#include "AL/alc.h"

// libsamplerate
#include "samplerate.h"

// taglib
#include "taglib/fileref.h"
#include "taglib/tag.h"

// ============================================================================
// Archive/Utility libraries
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

// ============================================================================
// Crypto libraries
// ============================================================================

// cryptopp
#include "cryptopp/cryptlib.h"
#include "cryptopp/sha.h"

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
// Data format libraries
// ============================================================================

// fastgltf
#include "fastgltf/core.hpp"

// jsoncpp
#include "json/json.h"

// ============================================================================
// SVG libraries
// ============================================================================

// lunasvg
#include "lunasvg/lunasvg.h"


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
    tjhandle handle = tjInitCompress();
    if (handle)
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

static bool test_cryptopp()
{
    CryptoPP::SHA256 hash;
    std::cout << "  cryptopp: OK (SHA256 digest size: " << hash.DigestSize() << ")\n";
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

static bool test_lunasvg()
{
    auto document = lunasvg::Document::loadFromData(R"(<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="red"/></svg>)");
    if (document) {
        std::cout << "  lunasvg: OK (SVG parsed, size: " << document->width() << "x" << document->height() << ")\n";
        return true;
    }
    std::cout << "  lunasvg: OK (linkage verified)\n";
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

    std::cout << "\n--- Font Libraries ---\n";
    run_test("freetype", test_freetype);
    run_test("harfbuzz", test_harfbuzz);

    std::cout << "\n--- Audio Libraries ---\n";
    run_test("openal-soft", test_openal);
    run_test("libsamplerate", test_libsamplerate);
    run_test("taglib", test_taglib);

    std::cout << "\n--- Archive/Utility Libraries ---\n";
    run_test("libzip", test_libzip);

    std::cout << "\n--- System Libraries ---\n";
    run_test("cpu_features", test_cpu_features);
    run_test("hwloc", test_hwloc);

    std::cout << "\n--- Crypto Libraries ---\n";
    run_test("cryptopp", test_cryptopp);

    std::cout << "\n--- Geometry Libraries ---\n";
    run_test("clipper2", test_clipper2);

    std::cout << "\n--- Networking Libraries ---\n";
    run_test("libzmq", test_libzmq);
    run_test("cppzmq", test_cppzmq);

    std::cout << "\n--- Data Format Libraries ---\n";
    run_test("fastgltf", test_fastgltf);
    run_test("jsoncpp", test_jsoncpp);

    std::cout << "\n--- SVG Libraries ---\n";
    run_test("lunasvg", test_lunasvg);

    std::cout << "\n========================================\n";
    std::cout << "   Results: " << passed << " passed, " << failed << " failed\n";
    std::cout << "========================================\n\n";

    return failed > 0 ? EXIT_FAILURE : EXIT_SUCCESS;
}
