#!/bin/sh

set -e

if [ -z "$1" ] || [ -z "$2" ]
	then
		echo "Bad call : BuildScript {x86_64|arm} {Release|Debug}\n"
		exit 1
fi

LIB_NAME=libzip
PLATFORM=linux.${1}
BUILD_TYPE=${2}

SOURCE_DIR=./repositories/${LIB_NAME}
BUILD_DIR=./builds/${PLATFORM}-${BUILD_TYPE}/${LIB_NAME}
INSTALL_DIR=./output/${PLATFORM}-${BUILD_TYPE}
INCLUDE_DIR=../../output/${PLATFORM}-${BUILD_TYPE}

echo "\n======================== Configuring '${LIB_NAME}' for '${PLATFORM}-${BUILD_TYPE}' ... ========================\n"

cmake -S ${SOURCE_DIR} -B ${BUILD_DIR} -G "Ninja" \
-DCMAKE_BUILD_TYPE=${BUILD_TYPE} \
-DCMAKE_INSTALL_PREFIX=${INSTALL_DIR} \
-DCMAKE_C_FLAGS=-fPIC \
-DLIBS_ROOT="../../output/${PLATFORM}-${BUILD_TYPE}" \
-DENABLE_COMMONCRYPTO=On \
-DENABLE_GNUTLS=Off \
-DENABLE_MBEDTLS=Off \
-DENABLE_OPENSSL=Off \
-DENABLE_WINDOWS_CRYPTO=Off \
-DENABLE_BZIP2=On \
-DENABLE_LZMA=On \
-DENABLE_ZSTD=On \
-DENABLE_FDOPEN=Off \
-DBUILD_TOOLS=Off \
-DBUILD_REGRESS=Off \
-DBUILD_OSSFUZZ=Off \
-DBUILD_EXAMPLES=Off \
-DBUILD_DOC=Off \
-DBUILD_SHARED_LIBS=Off \
-DLIBZIP_DO_INSTALL=On \
-DSHARED_LIB_VERSIONNING=On 

echo "\n======================== Building ... ========================\n"

cmake --build ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Installing ... ========================\n"

cmake --install ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Success ! ========================\n"
