#!/bin/sh

set -e

if [ -z "$1" ] || [ -z "$2" ]
	then
		echo "Bad call : BuildScript {x86_64|arm} {Release|Debug}\n"
		exit 1
fi

LIB_NAME=xz
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
-DXZ_SMALL=Off \
-DXZ_EXTERNAL_SHA256=Off \
-DXZ_MICROLZMA_ENCODER=On \
-DXZ_MICROLZMA_DECODER=On \
-DXZ_LZIP_DECODER=On \
-DXZ_CLMUL_CRC=On \
-DXZ_ARM64_CRC32=On \
-DXZ_LOONGARCH_CRC32=On \
-DXZ_TOOL_XZDEC=On \
-DXZ_TOOL_LZMADEC=On \
-DXZ_TOOL_LZMAINFO=On \
-DXZ_TOOL_XZ=On \
-DXZ_TOOL_SCRIPTS=On \
-DXZ_DOC=Off \
-DXZ_NLS=Off \
-DXZ_TOOL_SYMLINKS=Off \
-DXZ_TOOL_SYMLINKS_LZMA=Off \
-DXZ_DOXYGEN=Off

echo "\n======================== Building ... ========================\n"

cmake --build ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Installing ... ========================\n"

cmake --install ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Success ! ========================\n"
