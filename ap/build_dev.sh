#!/bin/sh
# Incremental newserv build in the dev container. Output: build/dev/newserv
# Usage: ap/build_dev.sh [--rebuild-image] [--clean]
set -e
cd "$(dirname "$0")/.."
IMAGE=newserv-dev
for a in "$@"; do
  case "$a" in
    --rebuild-image) podman rmi -f "$IMAGE" >/dev/null 2>&1 || true ;;
    --clean) rm -rf build/dev ;;
  esac
done
podman image exists "$IMAGE" || podman build -f ap/Containerfile.dev -t "$IMAGE" .
podman run --rm -v "$PWD:/src:Z" -e BUILD_TYPE="${BUILD_TYPE:-RelWithDebInfo}" -e J="${J:-8}" \
  "$IMAGE" sh -c "BUILD_DIR=build/dev ap/build.sh newserv"
