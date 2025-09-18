#!/bin/sh

set -e

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]
	then
		echo "Bad call : BuildScript {min.SDK.version} {x86_64|arm} {Release|Debug}\n"
		exit 1
fi

LIB_NAME=libzmq
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
-DCMAKE_CXX_FLAGS="-mmacosx-version-min=${1} -fPIC" \
-DENABLE_ASAN=Off \
-DENABLE_TSAN=Off \
-DENABLE_UBSAN=Off \
-DENABLE_INTRINSICS=On \
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
-DWITH_PERF_TOOL=Off \
-DBUILD_TESTS=Off \
-DENABLE_CPACK=On \
-DENABLE_CLANG=On \
-DENABLE_NO_EXPORT=Off

echo "\n======================== Building ... ========================\n"

cmake --build ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Installing ... ========================\n"

cmake --install ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Success ! ========================\n"
