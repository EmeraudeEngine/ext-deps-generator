#!/bin/sh

set -e

if [ -z "$1" ] || [ -z "$2" ]
	then
		echo "Bad call : BuildScript {x86_64|arm} {Release|Debug}\n"
		exit 1
fi

LIB_NAME=taglib
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
