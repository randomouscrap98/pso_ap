#!/bin/sh
# Incremental 64-bit Windows newserv build in the mingw container. Output: build/windows/newserv.exe
# Usage: ap/build_win.sh [--rebuild-image] [--clean]
set -e
cd "$(dirname "$0")/.."
IMAGE=newserv-win
for a in "$@"; do
  case "$a" in
    --rebuild-image) podman rmi -f "$IMAGE" >/dev/null 2>&1 || true ;;
    --clean) rm -rf build/windows ;;
  esac
done
podman image exists "$IMAGE" || podman build -f ap/Containerfile.win -t "$IMAGE" .
podman run --rm -v "$PWD:/src:Z" -e BUILD_TYPE="${BUILD_TYPE:-RelWithDebInfo}" -e J="${J:-8}" \
  "$IMAGE" sh -c "ap/build.sh win-newserv"
