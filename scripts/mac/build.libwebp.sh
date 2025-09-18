#!/bin/sh

set -e

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]
	then
		echo "Bad call : BuildScript {min.SDK.version} {x86_64|arm} {Release|Debug}\n"
		exit 1
fi

LIB_NAME=libwebp
PLATFORM=mac.${2}
BUILD_TYPE=${3}

SOURCE_DIR=./repositories/${LIB_NAME}
BUILD_DIR=./builds/${PLATFORM}-${BUILD_TYPE}/${LIB_NAME}
INSTALL_DIR=./output/${PLATFORM}-${BUILD_TYPE}

echo "\n======================== Configuring '${LIB_NAME}' for '${PLATFORM}-${BUILD_TYPE}' ... ========================\n"

cmake -S ${SOURCE_DIR} -B ${BUILD_DIR} -G "Ninja" \
-DCMAKE_BUILD_TYPE=${BUILD_TYPE} \
-DCMAKE_INSTALL_PREFIX=${INSTALL_DIR} \
-DCMAKE_OSX_ARCHITECTURES=${2} \
-DCMAKE_OSX_DEPLOYMENT_TARGET=${1} \
-DCMAKE_C_FLAGS="-mmacosx-version-min=${1} -fPIC" \
-DLIBS_ROOT="./output/${PLATFORM}-${BUILD_TYPE}" \
-DBUILD_SHARED_LIBS=Off \
-DWEBP_LINK_STATIC=Off \
-DWEBP_ENABLE_SIMD=On \
-DWEBP_BUILD_ANIM_UTILS=Off \
-DWEBP_BUILD_CWEBP=Off \
-DWEBP_BUILD_DWEBP=Off \
-DWEBP_BUILD_GIF2WEBP=Off \
-DWEBP_BUILD_IMG2WEBP=Off \
-DWEBP_BUILD_VWEBP=Off \
-DWEBP_BUILD_WEBPINFO=Off \
-DWEBP_BUILD_LIBWEBPMUX=On \
-DWEBP_BUILD_WEBPMUX=Off \
-DWEBP_BUILD_EXTRAS=Off \
-DWEBP_BUILD_WEBP_JS=Off \
-DWEBP_BUILD_FUZZTEST=Off \
-DWEBP_USE_THREAD=On \
-DWEBP_NEAR_LOSSLESS=On \
-DWEBP_ENABLE_SWAP_16BIT_CSP=Off \
-DWEBP_ENABLE_WUNUSED_RESULT=Off \
-DWEBP_UNICODE=Off

echo "\n======================== Building ... ========================\n"

cmake --build ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Installing ... ========================\n"

cmake --install ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Success ! ========================\n"
