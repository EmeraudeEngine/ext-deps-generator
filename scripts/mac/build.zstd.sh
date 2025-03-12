#!/bin/sh

set -e

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]
	then
		echo "Bad call : BuildScript {min.SDK.version} {x86_64|arm} {Release|Debug}\n"
		exit 1
fi

LIB_NAME=zstd
PLATFORM=mac.${2}
BUILD_TYPE=${3}

SOURCE_DIR=./repositories/${LIB_NAME}/build/cmake
BUILD_DIR=./builds/${PLATFORM}-${BUILD_TYPE}/${LIB_NAME}
INSTALL_DIR=./output/${PLATFORM}-${BUILD_TYPE}

echo "\n======================== Configuring '${LIB_NAME}' for '${PLATFORM}-${BUILD_TYPE}' ... ========================\n"

cmake -S ${SOURCE_DIR} -B ${BUILD_DIR} -G "Ninja" \
-DCMAKE_BUILD_TYPE=${BUILD_TYPE} \
-DCMAKE_INSTALL_PREFIX=${INSTALL_DIR} \
-DCMAKE_OSX_ARCHITECTURES=${2} \
-DCMAKE_OSX_DEPLOYMENT_TARGET=${1} \
-DCMAKE_C_FLAGS="-mmacosx-version-min=${1} -fPIC" \
-DZSTD_LEGACY_SUPPORT=On \
-DZSTD_MULTITHREAD_SUPPORT=On \
-DZSTD_BUILD_PROGRAMS=On \
-DZSTD_BUILD_CONTRIB=On \
-DZSTD_BUILD_TESTS=Off \
-DZSTD_USE_STATIC_RUNTIME=On \
-DZSTD_PROGRAMS_LINK_SHARED=Off

echo "\n======================== Building ... ========================\n"

cmake --build ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Installing ... ========================\n"

cmake --install ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Success ! ========================\n"
