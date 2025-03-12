#!/bin/sh

set -e

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]
	then
		echo "Bad call : BuildScript {min.SDK.version} {x86_64|arm} {Release|Debug}\n"
		exit 1
fi

LIB_NAME=harfbuzz
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
-DBUILD_SHARED_LIBS=Off \
-DHB_HAVE_CAIRO=Off \
-DHB_HAVE_FREETYPE=Off \
-DHB_HAVE_GRAPHITE2=Off \
-DHB_HAVE_GLIB=Off \
-DHB_HAVE_ICU=Off \
-DHB_BUILD_UTILS=Off \
-DHB_BUILD_SUBSET=On \
-DHB_HAVE_GOBJECT=Off \
-DHB_HAVE_INTROSPECTION=Off \
-DHB_HAVE_CORETEXT=On \
-DBUILD_FRAMEWORK=Off

echo "\n======================== Building ... ========================\n"

cmake --build ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Installing ... ========================\n"

cmake --install ${BUILD_DIR} --config ${BUILD_TYPE}

echo "\n======================== Success ! ========================\n"
