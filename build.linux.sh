#!/bin/sh

set -e

if [ -z "$1" ]
	then
		ARCH=x86_64
	else
		ARCH=${1}
fi

if [ -z "$2" ]
	then
		BUILD_TYPE=Release
	else
		BUILD_TYPE=${2}
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

echo "\n======================== Building dependencies for 'linux.${ARCH}-${BUILD_TYPE}' ... ========================\n"

./scripts/linux/build.zlib.sh "${ARCH}" "${BUILD_TYPE}"
./scripts/linux/build.bzip2.sh "${ARCH}" "${BUILD_TYPE}"
./scripts/linux/build.xz.sh "${ARCH}" "${BUILD_TYPE}"
./scripts/linux/build.zstd.sh "${ARCH}" "${BUILD_TYPE}"
./scripts/linux/build.brotli.sh "${ARCH}" "${BUILD_TYPE}"
./scripts/linux/build.harfbuzz.sh "${ARCH}" "${BUILD_TYPE}"
./scripts/linux/build.libjpeg-turbo.sh "${ARCH}" "${BUILD_TYPE}"
./scripts/linux/build.cpu_features.sh "${ARCH}" "${BUILD_TYPE}"
./scripts/linux/build.hwloc.sh "${ARCH}" "${BUILD_TYPE}"
./scripts/linux/build.openal-soft.sh "${ARCH}" "${BUILD_TYPE}"
./scripts/linux/build.libsamplerate.sh "${ARCH}" "${BUILD_TYPE}"
./scripts/linux/build.libzmq.sh "${ARCH}" "${BUILD_TYPE}"
./scripts/linux/build.libwebp.sh "${ARCH}" "${BUILD_TYPE}"
./scripts/linux/build.cryptopp-cmake.sh "${ARCH}" "${BUILD_TYPE}"
./scripts/linux/build.clipper2.sh "${ARCH}" "${BUILD_TYPE}"
# Below are the projects that require the above to be compiled.
./scripts/linux/build.taglib.sh "${ARCH}" "${BUILD_TYPE}"
./scripts/linux/build.libpng.sh "${ARCH}" "${BUILD_TYPE}"
./scripts/linux/build.libzip.sh "${ARCH}" "${BUILD_TYPE}"
./scripts/linux/build.lib3mf.sh "${ARCH}" "${BUILD_TYPE}"
./scripts/linux/build.freetype.sh "${ARCH}" "${BUILD_TYPE}"
./scripts/linux/build.cppzmq.sh "${ARCH}" "${BUILD_TYPE}"

echo "\n======================== Finished ! ========================\n"
