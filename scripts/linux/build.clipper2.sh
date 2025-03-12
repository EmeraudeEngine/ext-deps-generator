#!/bin/sh

set -e

if [ -z "$1" ] || [ -z "$2" ]
	then
		echo "Bad call : BuildScript {x86_64|arm} {Release|Debug}\n"
		exit 1
fi

LIB_NAME=clipper2
PLATFORM=linux.${1}
BUILD_TYPE=${2}

SOURCE_DIR=./repositories/${LIB_NAME}/CPP
BUILD_DIR=./builds/${PLATFORM}-${BUILD_TYPE}/${LIB_NAME}
INSTALL_DIR=./output/${PLATFORM}-${BUILD_TYPE}

echo "\n======================== Configuring '${LIB_NAME}' for '${PLATFORM}-${BUILD_TYPE}' ... ========================\n"

cmake -S ${SOURCE_DIR} -B ${BUILD_DIR} -G "Ninja" \
-DCMAKE_BUILD_TYPE=${BUILD_TYPE} \
-DCMAKE_INSTALL_PREFIX=${INSTALL_DIR} \
-DCMAKE_C_FLAGS=-fPIC \
-DCMAKE_CXX_FLAGS=-fPIC \
-DCLIPPER2_UTILS=On \
-DCLIPPER2_EXAMPLES=Off \
-DCLIPPER2_TESTS=Off \
-DUSE_EXTERNAL_GTEST=Off \
-DUSE_EXTERNAL_GBENCHMARK=Off \
-DBUILD_SHARED_LIBS=Off \
-DCLIPPER2_USINGZ=Off

echo "\n======================== Building ... ========================\n"

cmake --build ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Installing ... ========================\n"

cmake --install ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Success ! ========================\n"
