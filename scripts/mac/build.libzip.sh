#!/bin/sh

set -e

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]
	then
		echo "Bad call : BuildScript {min.SDK.version} {x86_64|arm} {Release|Debug}\n"
		exit 1
fi

LIB_NAME=libzip
PLATFORM=mac.${2}
BUILD_TYPE=${3}

SOURCE_DIR=./repositories/${LIB_NAME}
BUILD_DIR=./builds/${PLATFORM}-${BUILD_TYPE}/${LIB_NAME}
INSTALL_DIR=./output/${PLATFORM}-${BUILD_TYPE}
INCLUDE_DIR=../../output/${PLATFORM}-${BUILD_TYPE}

echo "\n======================== Configuring '${LIB_NAME}' for '${PLATFORM}-${BUILD_TYPE}' ... ========================\n"

cmake -S ${SOURCE_DIR} -B ${BUILD_DIR} -G "Ninja" \
-DCMAKE_BUILD_TYPE=${BUILD_TYPE} \
-DCMAKE_INSTALL_PREFIX=${INSTALL_DIR} \
-DCMAKE_OSX_ARCHITECTURES=${2} \
-DCMAKE_OSX_DEPLOYMENT_TARGET=${1} \
-DCMAKE_C_FLAGS="-mmacosx-version-min=${1} -fPIC" \
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
