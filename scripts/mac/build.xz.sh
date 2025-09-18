#!/bin/sh

set -e

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]
	then
		echo "Bad call : BuildScript {min.SDK.version} {x86_64|arm} {Release|Debug}\n"
		exit 1
fi

LIB_NAME=xz
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
-DXZ_ASM_I386=Off \
-DXZ_NLS=Off \
-DBUILD_SHARED_LIBS=Off \
-DXZ_SMALL=Off \
-DXZ_EXTERNAL_SHA256=Off \
-DXZ_MICROLZMA_ENCODER=Off \
-DXZ_MICROLZMA_DECODER=Off \
-DXZ_LZIP_DECODER=Off \
-DXZ_CLMUL_CRC=On \
-DXZ_ARM64_CRC32=On \
-DXZ_LOONGARCH_CRC32=On \
-DXZ_TOOL_XZDEC=Off \
-DXZ_TOOL_LZMADEC=Off \
-DXZ_TOOL_LZMAINFO=Off \
-DXZ_TOOL_XZ=Off \
-DXZ_TOOL_SYMLINKS=Off \
-DXZ_TOOL_SYMLINKS_LZMA=Off \
-DXZ_TOOL_SCRIPTS=Off \
-DXZ_DOXYGEN=Off \
-DXZ_DOC=Off \
-DXZ_NLS=Off

echo "\n======================== Building ... ========================\n"

cmake --build ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Installing ... ========================\n"

cmake --install ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Success ! ========================\n"
