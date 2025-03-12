#!/bin/sh

set -e

if [ -z "$1" ] || [ -z "$2" ]
	then
		echo "Bad call : BuildScript {x86_64|arm} {Release|Debug}\n"
		exit 1
fi

LIB_NAME=libzmq
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
-DCMAKE_CXX_FLAGS=-fPIC \
-DENABLE_ASAN=Off \
-DENABLE_TSAN=Off \
-DENABLE_UBSAN=Off \
-DENABLE_INTRINSICS=Off \
-DWITH_OPENPGM=Off \
-DWITH_NORM=Off \
-DWITH_VMCI=Off \
-DENABLE_DRAFTS=Off \
-DENABLE_WS=Off \
-DENABLE_RADIX_TREE=Off \
-DWITH_TLS=On \
-DWITH_NSS=Off \
-DWITH_LIBBSD=Off \
-DWITH_LIBSODIUM=Off \
-DWITH_LIBSODIUM_STATIC=Off \
-DENABLE_LIBSODIUM_RANDOMBYTES_CLOSE=Off \
-DENABLE_CURVE=Off \
-DWITH_GSSAPI_KRB5=Off \
-DWITH_MILITANT=Off \
-DENABLE_EVENTFD=Off \
-DENABLE_ANALYSIS=Off \
-DLIBZMQ_PEDANTIC=On \
-DLIBZMQ_WERROR=Off \
-DWITH_DOCS=Off \
-DENABLE_PRECOMPILED=On \
-DBUILD_SHARED=Off \
-DBUILD_STATIC=On \
-DWITH_PERF_TOOL=On \
-DBUILD_TESTS=Off \
-DENABLE_CPACK=On \
-DENABLE_CLANG=On \
-DENABLE_NO_EXPORT=Off

echo "\n======================== Building ... ========================\n"

cmake --build ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Installing ... ========================\n"

cmake --install ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Success ! ========================\n"
