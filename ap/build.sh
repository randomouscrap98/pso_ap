#!/bin/sh
# Single build script for newserv and its deps (phosg, resource_dasm). Used by
# ap/Containerfile.dev (deps), ap/build_dev.sh (newserv), and Claude's Alpine sandbox.
#
# Usage: ap/build.sh [deps|newserv|all|win-deps|win-newserv|win]
#   default: all. "all"/"win" skip deps if already installed. win-*: 64-bit Windows cross build (mingw-w64).
# Env (relative paths are relative to the repo root):
#   PREFIX      deps install prefix            (default /usr/local)
#   WIN_PREFIX  Windows deps prefix            (default /opt/newserv-win; newserv's WINDOWS_ENV)
#   WIN_BUILD_DIR  Windows newserv build dir   (default build/windows)
#   DEPS_SRC    where deps are cloned/built    (default /tmp/newserv-deps-src)
#   BUILD_DIR   newserv build dir              (default build/dev)
#   BUILD_TYPE  newserv CMake build type       (default RelWithDebInfo)
#   J           parallel jobs                  (default 8)
#   PHOSG_REF, RESOURCE_DASM_REF   git branches/tags to clone (default master)
set -e
cd "$(dirname "$0")/.."

STEP="${1:-all}"
PREFIX="${PREFIX:-/usr/local}"
DEPS_SRC="${DEPS_SRC:-/tmp/newserv-deps-src}"
BUILD_DIR="${BUILD_DIR:-build/dev}"
BUILD_TYPE="${BUILD_TYPE:-RelWithDebInfo}"
WIN_PREFIX="${WIN_PREFIX:-/opt/newserv-win}"
WIN_BUILD_DIR="${WIN_BUILD_DIR:-build/windows}"
J="${J:-8}"
# Absolutize paths (CMake would resolve some relative ones against the build dir).
abs() { case "$1" in /*) echo "$1" ;; *) echo "$PWD/$1" ;; esac; }
PREFIX="$(abs "$PREFIX")"; DEPS_SRC="$(abs "$DEPS_SRC")"; BUILD_DIR="$(abs "$BUILD_DIR")"
WIN_PREFIX="$(abs "$WIN_PREFIX")"; WIN_BUILD_DIR="$(abs "$WIN_BUILD_DIR")"
WIN_HOST=x86_64-w64-mingw32
WIN_CMAKE="-DCMAKE_TOOLCHAIN_FILE=$PWD/ap/mingw-toolchain.cmake -DCMAKE_FIND_ROOT_PATH=$WIN_PREFIX"

# musl's <limits.h> #defines PAGE_SIZE, which collides with resource_dasm's MemoryContext.hh
# (also included by newserv). Force-include a header that undefines it; harmless on glibc.
# Written only if missing so its mtime doesn't trigger full rebuilds.
musl_fix() { # dir -> prints header path
  mkdir -p "$1"
  [ -f "$1/musl_fix.h" ] || printf '#include <limits.h>\n#undef PAGE_SIZE\n' > "$1/musl_fix.h"
  echo "$(cd "$1" && pwd)/musl_fix.h"
}

deps_installed() { # prefix
  [ -d "$1/lib/cmake/resource_file" ] || [ -d "$1/lib64/cmake/resource_file" ]
}

clone() { # name url ref
  [ -d "$DEPS_SRC/$1" ] || git clone --depth 1 -b "$3" "$2" "$DEPS_SRC/$1"
}

# Uses DEP_PREFIX (install prefix), DEP_BUILD (build subdir name), DEP_CMAKE (extra cmake args),
# DEP_CXXFLAGS (extra compiler flags).
build_dep() { # name url ref [extra cmake args...]
  name="$1"; clone "$1" "$2" "$3"; shift 3
  # shellcheck disable=SC2086
  cmake -S "$DEPS_SRC/$name" -B "$DEPS_SRC/$name/$DEP_BUILD" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$DEP_PREFIX" -DCMAKE_PREFIX_PATH="$DEP_PREFIX" \
    -DCMAKE_CXX_FLAGS="-include $FIX $DEP_CXXFLAGS" $DEP_CMAKE "$@"
  cmake --build "$DEPS_SRC/$name/$DEP_BUILD" -j"$J"
  cmake --install "$DEPS_SRC/$name/$DEP_BUILD"
}

build_fuzziq_deps() {
  build_dep phosg https://github.com/fuzziqersoftware/phosg.git "${PHOSG_REF:-master}"
  # -O1: resource_dasm's TrapInfo.cc (~1MB table) takes ~7 min single-threaded at -O3 vs ~30s at -O1.
  # newserv barely uses resource_dasm, so its speed doesn't matter.
  build_dep resource_dasm https://github.com/fuzziqersoftware/resource_dasm.git "${RESOURCE_DASM_REF:-master}" \
    -DCMAKE_CXX_FLAGS_RELEASE="-O1 -DNDEBUG"
}

build_deps() {
  FIX="$(musl_fix "$DEPS_SRC")"; DEP_PREFIX="$PREFIX"; DEP_BUILD=build; DEP_CMAKE=; DEP_CXXFLAGS=
  build_fuzziq_deps
}

# Windows deps: zlib, GNU libiconv (as upstream; win-iconv may transcode differently), asio headers,
# then phosg/resource_dasm. All static, into WIN_PREFIX.
build_win_deps() {
  FIX="$(musl_fix "$DEPS_SRC")"; DEP_PREFIX="$WIN_PREFIX"; DEP_BUILD=build-win; DEP_CMAKE="$WIN_CMAKE"
  # resource_dasm's Windows-only unreserve_mem() ignores its size param (upstream -Werror).
  DEP_CXXFLAGS="-Wno-unused-parameter"
  mkdir -p "$WIN_PREFIX/include" "$WIN_PREFIX/lib"
  if [ ! -f "$WIN_PREFIX/lib/libz.a" ]; then
    clone zlib https://github.com/madler/zlib.git "${ZLIB_REF:-v1.3.1}"
    make -C "$DEPS_SRC/zlib" -f win32/Makefile.gcc PREFIX="$WIN_HOST-" clean
    make -C "$DEPS_SRC/zlib" -f win32/Makefile.gcc PREFIX="$WIN_HOST-" -j"$J" libz.a
    cp "$DEPS_SRC/zlib/libz.a" "$WIN_PREFIX/lib/"
    cp "$DEPS_SRC/zlib/zlib.h" "$DEPS_SRC/zlib/zconf.h" "$WIN_PREFIX/include/"
  fi
  if [ ! -f "$WIN_PREFIX/lib/libiconv.a" ]; then
    v="${LIBICONV_VERSION:-1.18}"
    [ -d "$DEPS_SRC/libiconv-$v" ] || curl -fsSL "https://ftp.gnu.org/pub/gnu/libiconv/libiconv-$v.tar.gz" \
      | tar -xz -C "$DEPS_SRC"
    mkdir -p "$DEPS_SRC/libiconv-$v/build-win"
    (cd "$DEPS_SRC/libiconv-$v/build-win" && ../configure --host="$WIN_HOST" --prefix="$WIN_PREFIX" \
      --enable-static --disable-shared --disable-nls && make -j"$J" && make install)
  fi
  if [ ! -f "$WIN_PREFIX/include/asio.hpp" ]; then
    clone asio https://github.com/chriskohlhoff/asio.git "${ASIO_REF:-asio-1-36-0}"
    cp -r "$DEPS_SRC/asio/asio/include/asio" "$DEPS_SRC/asio/asio/include/asio.hpp" "$WIN_PREFIX/include/"
  fi
  build_fuzziq_deps
}

build_newserv() {
  FIX="$(musl_fix "$BUILD_DIR")"
  # GCC 15 false positives (asio coroutines, libstdc++ allocator) under upstream's -Werror. Specific
  # -Wno-* is needed: upstream's -Werror comes after CMAKE_CXX_FLAGS, so -Wno-error is overridden.
  cmake -S . -B "$BUILD_DIR" -DCMAKE_BUILD_TYPE="$BUILD_TYPE" -DCMAKE_PREFIX_PATH="$PREFIX" \
    -DCMAKE_CXX_FLAGS="-include $FIX -Wno-mismatched-new-delete -Wno-free-nonheap-object"
  cmake --build "$BUILD_DIR" -j"$J"
}

build_win_newserv() {
  FIX="$(musl_fix "$WIN_BUILD_DIR")"
  # shellcheck disable=SC2086
  cmake -S . -B "$WIN_BUILD_DIR" -DCMAKE_BUILD_TYPE="$BUILD_TYPE" -DCMAKE_PREFIX_PATH="$WIN_PREFIX" \
    -DWINDOWS_ENV="$WIN_PREFIX" $WIN_CMAKE \
    -DCMAKE_CXX_FLAGS="-include $FIX -Wno-mismatched-new-delete -Wno-free-nonheap-object"
  cmake --build "$WIN_BUILD_DIR" -j"$J"
  # Release builds ship: strip (RelWithDebInfo keeps debug info, ~480MB vs ~13MB, for debugging).
  [ "$BUILD_TYPE" != Release ] || "$WIN_HOST-strip" "$WIN_BUILD_DIR/newserv.exe"
}

case "$STEP" in
  deps) build_deps ;;
  newserv) build_newserv ;;
  all) deps_installed "$PREFIX" || build_deps; build_newserv ;;
  win-deps) build_win_deps ;;
  win-newserv) build_win_newserv ;;
  win) deps_installed "$WIN_PREFIX" || build_win_deps; build_win_newserv ;;
  *) echo "usage: $0 [deps|newserv|all|win-deps|win-newserv|win]" >&2; exit 1 ;;
esac
