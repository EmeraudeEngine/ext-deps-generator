#!/bin/sh

set -e

if [ -z "$1" ]
	then
	echo "Specify the targeted SDK for macOS as first argument !"
	exit 1
fi

MIN_SDK=${1}

if [ -z "$2" ]
	then
		ARCH=x86_64
	else
		ARCH=${2}
fi

if [ -z "$3" ]
	then
		BUILD_TYPE=Release
	else
		BUILD_TYPE=${3}
fi

if [ "${ARCH}" != "x86_64" ] && [ "${ARCH}" != "arm64" ]
	then
	echo "ARCH argument should be 'x86_64' or 'arm64' ! '${ARCH}' unavailable."
	exit 1
fi

if [ "${BUILD_TYPE}" != "Release" ] && [ "${BUILD_TYPE}" != "Debug" ]
	then
	echo "BUILD_TYPE argument should be 'Release' or 'Debug' ! '${BUILD_TYPE}' unavailable."
	exit 1
fi

echo "\n======================== Building dependencies for 'mac.${ARCH}-${BUILD_TYPE}' ... ========================\n"

./scripts/mac/build.zlib.sh "${MIN_SDK}" "${ARCH}" "${BUILD_TYPE}"
./scripts/mac/build.bzip2.sh "${MIN_SDK}" "${ARCH}" "${BUILD_TYPE}"
./scripts/mac/build.xz.sh "${MIN_SDK}" "${ARCH}" "${BUILD_TYPE}"
./scripts/mac/build.zstd.sh "${MIN_SDK}" "${ARCH}" "${BUILD_TYPE}"
./scripts/mac/build.brotli.sh "${MIN_SDK}" "${ARCH}" "${BUILD_TYPE}"
./scripts/mac/build.harfbuzz.sh "${MIN_SDK}" "${ARCH}" "${BUILD_TYPE}"
./scripts/mac/build.libjpeg-turbo.sh "${MIN_SDK}" "${ARCH}" "${BUILD_TYPE}"
./scripts/mac/build.cpu_features.sh "${MIN_SDK}" "${ARCH}" "${BUILD_TYPE}"
./scripts/mac/build.hwloc.sh "${MIN_SDK}" "${ARCH}" "${BUILD_TYPE}"
./scripts/mac/build.openal-soft.sh "${MIN_SDK}" "${ARCH}" "${BUILD_TYPE}"
./scripts/mac/build.libsamplerate.sh "${MIN_SDK}" "${ARCH}" "${BUILD_TYPE}"
./scripts/mac/build.libzmq.sh "${MIN_SDK}" "${ARCH}" "${BUILD_TYPE}"
./scripts/mac/build.libwebp.sh "${MIN_SDK}" "${ARCH}" "${BUILD_TYPE}"
./scripts/mac/build.cryptopp-cmake.sh "${MIN_SDK}" "${ARCH}" "${BUILD_TYPE}"
./scripts/mac/build.clipper2.sh "${MIN_SDK}" "${ARCH}" "${BUILD_TYPE}"

# Below are the projects that require the above to be compiled.

./scripts/mac/build.taglib.sh "${MIN_SDK}" "${ARCH}" "${BUILD_TYPE}"
./scripts/mac/build.libpng.sh "${MIN_SDK}" "${ARCH}" "${BUILD_TYPE}"
./scripts/mac/build.libzip.sh "${MIN_SDK}" "${ARCH}" "${BUILD_TYPE}"
./scripts/mac/build.lib3mf.sh "${MIN_SDK}" "${ARCH}" "${BUILD_TYPE}"
./scripts/mac/build.freetype.sh "${MIN_SDK}" "${ARCH}" "${BUILD_TYPE}"
./scripts/mac/build.cppzmq.sh "${MIN_SDK}" "${ARCH}" "${BUILD_TYPE}"

echo "\n======================== Finished ! ========================\n"
