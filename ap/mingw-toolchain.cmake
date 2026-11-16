# CMake toolchain for cross-compiling to 64-bit Windows with mingw-w64. Used by ap/build.sh (win-* steps),
# which also passes the deps prefix in CMAKE_FIND_ROOT_PATH.
set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR x86_64)
set(TOOLCHAIN_PREFIX x86_64-w64-mingw32)
set(CMAKE_C_COMPILER ${TOOLCHAIN_PREFIX}-gcc)
set(CMAKE_CXX_COMPILER ${TOOLCHAIN_PREFIX}-g++)
set(CMAKE_RC_COMPILER ${TOOLCHAIN_PREFIX}-windres)
list(APPEND CMAKE_FIND_ROOT_PATH /usr/${TOOLCHAIN_PREFIX})
# Programs from the host; headers/libs/packages only from the target roots (never the host's /usr).
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
