#!/bin/sh

set -e

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]
	then
		echo "Bad call : BuildScript {min.SDK.version} {x86_64|arm} {Release|Debug}\n"
		exit 1
fi

LIB_NAME=taglib
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
-DUTF8_TESTS=Off \
-DUTF8_INSTALL=Off \
-DUTF8_SAMPLES=Off \
-DBUILD_SHARED_LIBS=Off \
-DBUILD_FRAMEWORK=Off \
-DENABLE_STATIC_RUNTIME=On \
-DENABLE_CCACHE=Off \
-DVISIBILITY_HIDDEN=Off \
-DBUILD_EXAMPLES=Off \
-DBUILD_BINDINGS=Off \
-DNO_ITUNES_HACKS=Off \
-DPLATFORM_WINRT=Off \
-DWITH_APE=On \
-DWITH_ASF=On \
-DWITH_DSF=On \
-DWITH_MOD=On \
-DWITH_MP4=On \
-DWITH_RIFF=On \
-DWITH_SHORTEN=On \
-DWITH_TRUEAUDIO=On \
-DWITH_VORBIS=On \
-DWITH_ZLIB=On \
-DTRACE_IN_RELEASE=Off \
-DBUILD_TESTING=Off

echo "\n======================== Building ... ========================\n"

cmake --build ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Installing ... ========================\n"

cmake --install ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Success ! ========================\n"
