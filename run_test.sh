#!/bin/bash
#
# Helper script to build and run the dependencies test
#
# Usage:
#   # macOS
#   ./run_test.sh --macos-sdk 12.0
#   ./run_test.sh --macos-sdk 12.0 --build-type Debug
#
#   # Linux
#   ./run_test.sh
#   ./run_test.sh --build-type Debug
#
#   # Clean build
#   ./run_test.sh --clean --macos-sdk 12.0
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build_test"

# Parse arguments
CLEAN=0
MACOS_SDK=""
RUNTIME_LIB=""
BUILD_TYPE="Release"

while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN=1
            shift
            ;;
        --macos-sdk)
            MACOS_SDK="$2"
            shift 2
            ;;
        --runtime-lib)
            RUNTIME_LIB="$2"
            shift 2
            ;;
        --build-type)
            BUILD_TYPE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--clean] [--macos-sdk VERSION] [--runtime-lib MD|MT] [--build-type Release|Debug]"
            exit 1
            ;;
    esac
done

# Clean if requested
if [ "$CLEAN" -eq 1 ] && [ -d "$BUILD_DIR" ]; then
    echo "Cleaning build directory..."
    rm -rf "$BUILD_DIR"
fi

# Build CMake arguments
CMAKE_ARGS="-B ${BUILD_DIR} -S ${SCRIPT_DIR} -DCMAKE_BUILD_TYPE=${BUILD_TYPE}"

if [ -n "$MACOS_SDK" ]; then
    CMAKE_ARGS="${CMAKE_ARGS} -DMACOS_SDK=${MACOS_SDK}"
fi

if [ -n "$RUNTIME_LIB" ]; then
    CMAKE_ARGS="${CMAKE_ARGS} -DRUNTIME_LIB=${RUNTIME_LIB}"
fi

# Configure
echo ""
echo "========================================"
echo "  Configuring..."
echo "========================================"

cmake ${CMAKE_ARGS}

# Build
echo ""
echo "========================================"
echo "  Building..."
echo "========================================"

cmake --build "$BUILD_DIR"

# Run
echo ""
echo "========================================"
echo "  Running test..."
echo "========================================"

"${BUILD_DIR}/DependenciesTest"
