#!/bin/sh
# Incremental newserv build in the dev container. Output: build/dev/newserv
# Usage: ./build_dev.sh [--rebuild-image] [--clean]
set -e
cd "$(dirname "$0")"
IMAGE=newserv-dev
BUILD_TYPE="${BUILD_TYPE:-RelWithDebInfo}"
for a in "$@"; do
  case "$a" in
    --rebuild-image) podman rmi -f "$IMAGE" >/dev/null 2>&1 || true ;;
    --clean) rm -rf build/dev ;;
  esac
done
podman image exists "$IMAGE" || podman build -f Containerfile.dev -t "$IMAGE" .
podman run --rm -v "$PWD:/src:Z" "$IMAGE" sh -c "
  cmake -S . -B build/dev -DCMAKE_BUILD_TYPE=$BUILD_TYPE &&
  cmake --build build/dev -j\$(nproc)"
