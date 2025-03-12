#!/bin/sh

set -e

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]
	then
		echo "Bad call : BuildScript {min.SDK.version} {x86_64|arm} {Release|Debug}\n"
		exit 1
fi

LIB_NAME=hwloc
PLATFORM=mac.${2}
BUILD_TYPE=${3}

CWD=$(pwd)

echo " ======================== Building (make) '${LIB_NAME}' for '${PLATFORM}-${BUILD_TYPE}' ... ======================== "

cd ./repositories
bash build.hwloc.sh macOS ${BUILD_TYPE} ${CWD}/output/${PLATFORM}-${BUILD_TYPE} ${1}
cd ..

echo "\n======================== Success ! ========================\n"
