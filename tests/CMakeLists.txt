###### CMake configuration ######

cmake_minimum_required(VERSION 3.15.0)
cmake_policy(VERSION 3.15.0)

set(CMAKE_VERBOSE_MAKEFILE ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set_property(GLOBAL PROPERTY USE_FOLDERS ON)



###### Project configuration ######

project(DependenciesTest VERSION 1.0.0 DESCRIPTION "Dependencies test")

message("[${PROJECT_NAME}] Source directory : ${CMAKE_SOURCE_DIR}, current : ${CMAKE_CURRENT_SOURCE_DIR}")
message("[${PROJECT_NAME}] Binary directory : ${CMAKE_BINARY_DIR}, current : ${CMAKE_CURRENT_BINARY_DIR}")
message("[${PROJECT_NAME}] Install directory : ${CMAKE_INSTALL_PREFIX}")



###### Project ######

file(GLOB_RECURSE SOURCE_FILES "${CMAKE_CURRENT_SOURCE_DIR}/src/*.?pp")

add_executable(${PROJECT_NAME} "${SOURCE_FILES}")

set_target_properties(${PROJECT_NAME} PROPERTIES
	C_STANDARD 17
	C_STANDARD_REQUIRED On
	C_EXTENSIONS On
	CXX_STANDARD 20
	CXX_STANDARD_REQUIRED On
	CXX_EXTENSIONS On
)



###### Dependencies ######

target_include_directories(${PROJECT_NAME} PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/../output/linux.x86_64-Release/include")
target_include_directories(${PROJECT_NAME} PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/../output/linux.x86_64-Release/include/freetype2")

target_link_directories(${PROJECT_NAME} PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/../output/linux.x86_64-Release/lib")

set(LOCAL_LIB_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../output/linux.x86_64-Release")

if ( MSVC )

	# These lib request sub-dependencies.
	target_link_libraries(${PROJECT_NAME} PRIVATE
		${LOCAL_LIB_DIR}/lib/freetype.lib
		${LOCAL_LIB_DIR}/lib/zip.lib
		${LOCAL_LIB_DIR}/lib/png.lib
	)

	target_link_libraries(${PROJECT_NAME} PRIVATE
		${LOCAL_LIB_DIR}/lib/harfbuzz.lib
		${LOCAL_LIB_DIR}/lib/brotlidec.lib
		${LOCAL_LIB_DIR}/lib/brotlienc.lib
		${LOCAL_LIB_DIR}/lib/brotlicommon.lib
		${LOCAL_LIB_DIR}/lib/zstd.lib
		${LOCAL_LIB_DIR}/lib/lzma.lib
		${LOCAL_LIB_DIR}/lib/bz2_static.lib
		${LOCAL_LIB_DIR}/lib/zlibstatic.lib
	)

else ()

	if ( NOT EXISTS ${LOCAL_LIB_DIR}/lib/libfreetype.a )
		message(FATAL_ERROR "External libraries not present !")
	endif ()

	# These lib request sub-dependencies.
	target_link_libraries(${PROJECT_NAME} PRIVATE
		${LOCAL_LIB_DIR}/lib/libfreetype.a
		${LOCAL_LIB_DIR}/lib/libzip.a
		${LOCAL_LIB_DIR}/lib/libpng.a
	)

	target_link_libraries(${PROJECT_NAME} PRIVATE
		${LOCAL_LIB_DIR}/lib/libharfbuzz.a
		${LOCAL_LIB_DIR}/lib/libbrotlidec.a
		${LOCAL_LIB_DIR}/lib/libbrotlienc.a
		${LOCAL_LIB_DIR}/lib/libbrotlicommon.a
		${LOCAL_LIB_DIR}/lib/libzstd.a
		${LOCAL_LIB_DIR}/lib/liblzma.a
		${LOCAL_LIB_DIR}/lib/libbz2_static.a
		${LOCAL_LIB_DIR}/lib/libz.a
	)

endif ()
