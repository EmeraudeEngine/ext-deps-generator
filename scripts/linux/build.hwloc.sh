#!/bin/sh

set -e

if [ -z "$1" ] || [ -z "$2" ]
	then
		echo "Bad call : BuildScript {x86_64|arm} {Release|Debug}\n"
		exit 1
fi

LIB_NAME=hwloc
PLATFORM=linux.${1}
BUILD_TYPE=${2}

CWD=$(pwd)

echo " ======================== Building (make) '${LIB_NAME}' for '${PLATFORM}-${BUILD_TYPE}' ... ======================== "

cd ./repositories
bash build.hwloc.sh Linux ${BUILD_TYPE} ${CWD}/output/${PLATFORM}-${BUILD_TYPE}
cd ..

echo "\n======================== Success ! ========================\n"
