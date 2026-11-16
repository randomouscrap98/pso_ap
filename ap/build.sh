#!/bin/sh
# Single build script for newserv and its deps (phosg, resource_dasm). Used by
# ap/Containerfile.dev (deps), ap/build_dev.sh (newserv), and Claude's Alpine sandbox.
#
# Usage: ap/build.sh [deps|newserv|all]   (default: all; "all" skips deps if already installed)
# Env (relative paths are relative to the repo root):
#   PREFIX      deps install prefix            (default /usr/local)
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
J="${J:-8}"
# Absolutize paths (CMake would resolve some relative ones against the build dir).
abs() { case "$1" in /*) echo "$1" ;; *) echo "$PWD/$1" ;; esac; }
PREFIX="$(abs "$PREFIX")"; DEPS_SRC="$(abs "$DEPS_SRC")"; BUILD_DIR="$(abs "$BUILD_DIR")"

# musl's <limits.h> #defines PAGE_SIZE, which collides with resource_dasm's MemoryContext.hh
# (also included by newserv). Force-include a header that undefines it; harmless on glibc.
# Written only if missing so its mtime doesn't trigger full rebuilds.
musl_fix() { # dir -> prints header path
  mkdir -p "$1"
  [ -f "$1/musl_fix.h" ] || printf '#include <limits.h>\n#undef PAGE_SIZE\n' > "$1/musl_fix.h"
  echo "$(cd "$1" && pwd)/musl_fix.h"
}

deps_installed() {
  [ -d "$PREFIX/lib/cmake/resource_file" ] || [ -d "$PREFIX/lib64/cmake/resource_file" ]
}

build_dep() { # name url ref [extra cmake args...]
  name="$1"; url="$2"; ref="$3"; shift 3
  [ -d "$DEPS_SRC/$name" ] || git clone --depth 1 -b "$ref" "$url" "$DEPS_SRC/$name"
  cmake -S "$DEPS_SRC/$name" -B "$DEPS_SRC/$name/build" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$PREFIX" -DCMAKE_PREFIX_PATH="$PREFIX" \
    -DCMAKE_CXX_FLAGS="-include $FIX" "$@"
  cmake --build "$DEPS_SRC/$name/build" -j"$J"
  cmake --install "$DEPS_SRC/$name/build"
}

build_deps() {
  FIX="$(musl_fix "$DEPS_SRC")"
  build_dep phosg https://github.com/fuzziqersoftware/phosg.git "${PHOSG_REF:-master}"
  # -O1: resource_dasm's TrapInfo.cc (~1MB table) takes ~7 min single-threaded at -O3 vs ~30s at -O1.
  # newserv barely uses resource_dasm, so its speed doesn't matter.
  build_dep resource_dasm https://github.com/fuzziqersoftware/resource_dasm.git "${RESOURCE_DASM_REF:-master}" \
    -DCMAKE_CXX_FLAGS_RELEASE="-O1 -DNDEBUG"
}

build_newserv() {
  FIX="$(musl_fix "$BUILD_DIR")"
  # GCC 15 false positives (asio coroutines, libstdc++ allocator) under upstream's -Werror. Specific
  # -Wno-* is needed: upstream's -Werror comes after CMAKE_CXX_FLAGS, so -Wno-error is overridden.
  cmake -S . -B "$BUILD_DIR" -DCMAKE_BUILD_TYPE="$BUILD_TYPE" -DCMAKE_PREFIX_PATH="$PREFIX" \
    -DCMAKE_CXX_FLAGS="-include $FIX -Wno-mismatched-new-delete -Wno-free-nonheap-object"
  cmake --build "$BUILD_DIR" -j"$J"
}

case "$STEP" in
  deps) build_deps ;;
  newserv) build_newserv ;;
  all) deps_installed || build_deps; build_newserv ;;
  *) echo "usage: $0 [deps|newserv|all]" >&2; exit 1 ;;
esac
