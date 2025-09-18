#!/bin/sh

set -e

if [ -z "$1" ] || [ -z "$2" ]
	then
		echo "Bad call : BuildScript {x86_64|arm} {Release|Debug}\n"
		exit 1
fi

LIB_NAME=harfbuzz
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
-DBUILD_SHARED_LIBS=Off \
-DHB_HAVE_CAIRO=Off \
-DHB_HAVE_FREETYPE=Off \
-DHB_HAVE_GRAPHITE2=Off \
-DHB_HAVE_GLIB=Off \
-DHB_HAVE_ICU=Off \
-DHB_HAVE_CORETEXT=Off \
-DHB_HAVE_UNISCRIBE=Off \
-DHB_HAVE_GDI=Off \
-DHB_HAVE_DIRECTWRITE=Off \
-DHB_BUILD_UTILS=Off \
-DHB_BUILD_SUBSET=On \
-DHB_HAVE_GOBJECT=Off \
-DHB_HAVE_INTROSPECTION=Off \
-DBUILD_FRAMEWORK=Off

echo "\n======================== Building ... ========================\n"

cmake --build ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Installing ... ========================\n"

cmake --install ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Success ! ========================\n"
