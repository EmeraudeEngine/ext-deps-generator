#!/bin/sh

set -e

if [ -z "$1" ] || [ -z "$2" ]
	then
		echo "Bad call : BuildScript {x86_64|arm} {Release|Debug}\n"
		exit 1
fi

LIB_NAME=libwebp
PLATFORM=linux.${1}
BUILD_TYPE=${2}

SOURCE_DIR=./repositories/${LIB_NAME}
BUILD_DIR=./builds/${PLATFORM}-${BUILD_TYPE}/${LIB_NAME}
INSTALL_DIR=./output/${PLATFORM}-${BUILD_TYPE}

echo "\n======================== Configuring '${LIB_NAME}' for '${PLATFORM}-${BUILD_TYPE}' ... ========================\n"

cmake -S ${SOURCE_DIR} -B ${BUILD_DIR} -G "Ninja" \
-DCMAKE_BUILD_TYPE=${BUILD_TYPE} \
-DCMAKE_INSTALL_PREFIX=${INSTALL_DIR} \
-DCMAKE_C_FLAGS=-fPIC \
-DBUILD_SHARED_LIBS=Off \
-DWEBP_BUILD_ANIM_UTILS=On \
-DWEBP_BUILD_CWEBP=On \
-DWEBP_BUILD_DWEBP=On \
-DWEBP_BUILD_GIF2WEBP=On \
-DWEBP_BUILD_IMG2WEBP=On \
-DWEBP_BUILD_VWEBP=On \
-DWEBP_BUILD_WEBPINFO=On \
-DWEBP_BUILD_LIBWEBPMUX=On \
-DWEBP_BUILD_WEBPMUX=On \
-DWEBP_BUILD_EXTRAS=On

echo "\n======================== Building ... ========================\n"

cmake --build ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Installing ... ========================\n"

cmake --install ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Success ! ========================\n"
