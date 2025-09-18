#!/bin/sh

set -e

if [ -z "$1" ] || [ -z "$2" ]
	then
		echo "Bad call : BuildScript {x86_64|arm} {Release|Debug}\n"
		exit 1
fi

LIB_NAME=libjpeg-turbo
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
-DNEON_INTRINSICS=On \
-DENABLE_SHARED=Off \
-DENABLE_STATIC=On \
-DREQUIRE_SIMD=On \
-DWITH_ARITH_DEC=On \
-DWITH_ARITH_ENC=On \
-DWITH_JAVA=Off \
-DWITH_JPEG7=Off \
-DWITH_JPEG8=Off \
-DWITH_SIMD=On \
-DWITH_TURBOJPEG=On \
-DWITH_TOOLS=Off \
-DWITH_TESTS=Off \
-DWITH_FUZZ=Off \
-DWITH_CRT_DLL=Off \
-DFORCE_INLINE=On


echo "\n======================== Building ... ========================\n"

cmake --build ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Installing ... ========================\n"

cmake --install ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Success ! ========================\n"
