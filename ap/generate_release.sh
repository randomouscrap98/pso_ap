#!/usr/bin/env bash
# Builds the apworld and clean Windows + Linux newserv, and puts them in <repo>/release (gitignored):
#   release/pso_bb.apworld
#   release/PSOBB-AP-newserv-<version>-windows.zip     (newserv.exe + system/)
#   release/PSOBB-AP-newserv-<version>-linux.tar.gz    (static newserv + system/)
# newserv is built in its own dirs (release/windows, release/linux; Release = stripped), never build/. system/ only
# gets git-tracked files (no players/, teams/, caches or a local config.json) plus a config.json generated from
# config.example.json for local play (127.0.0.1, DNS off).
# Usage: generate_release.sh [suffix]   e.g. "rc1" -> PSOBB-AP-newserv-0.0.1-rc1-windows.zip. The apworld stays x.y.z.
# Env: WIN_PREFIX=<Windows deps prefix> builds without podman, on a musl host (Claude's sandbox:
#   WIN_PREFIX=ignore/win-deps PREFIX=ignore/deps DEPS_SRC=ignore/deps-src).
set -e
suffix="${1:-}"
repo="$(dirname "$(dirname "$(readlink -f "$0")")")"
cd "$repo"
version="$(python3 -c 'import json; print(json.load(open("ap/apworld/pso_bb/archipelago.json"))["world_version"])')"
[ -n "$suffix" ] && version="$version-$suffix"
release="$repo/release"
mkdir -p "$release"

# Apworld (official "Build APWorlds" via the Archipelago checkout)
ap/apworld.sh build
cp build/apworlds/pso_bb.apworld "$release/"

# newserv Release builds in separate dirs. A CMake cache only works at the path it was configured at
# (host vs /src in podman), so the non-podman builds get their own "-local" dirs.
if [ -n "${WIN_PREFIX:-}" ]; then
  win_build=release/windows-local linux_build=release/linux-local
  WIN_PREFIX="$WIN_PREFIX" WIN_BUILD_DIR="$win_build" BUILD_TYPE=Release ap/build.sh win-newserv
  LINUX_BUILD_DIR="$linux_build" BUILD_TYPE=Release ap/build.sh linux-newserv
else
  win_build=release/windows linux_build=release/linux
  podman image exists newserv-win || podman build -f ap/Containerfile.win -t newserv-win .
  podman run --rm -v "$PWD:/src:Z" -e WIN_BUILD_DIR="$win_build" -e LINUX_BUILD_DIR="$linux_build" \
    -e BUILD_TYPE=Release -e J="${J:-8}" newserv-win sh -c "ap/build.sh win-newserv && ap/build.sh linux-newserv"
fi

# Stage under a named top folder: exe + git-tracked system/ + local-play config.json
name="PSOBB-AP-newserv"
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
stage_server() { # exe
  rm -rf "$stage/$name"
  mkdir -p "$stage/$name"
  cp "$1" "$stage/$name/"
  git ls-files -z system | xargs -0 cp --parents -t "$stage/$name"
  sed -e 's/"LocalAddress": "[^"]*"/"LocalAddress": "127.0.0.1"/' \
      -e 's/"ExternalAddress": "[^"]*"/"ExternalAddress": "127.0.0.1"/' \
      -e 's/"DNSServerPort": 53,/"DNSServerPort": 0,/' \
      -e 's/"HTTPListen": \[\],/"HTTPListen": ["127.0.0.1:11500"],/' \
      system/config.example.json > "$stage/$name/system/config.json"
  for k in LocalAddress ExternalAddress DNSServerPort HTTPListen; do
    grep -q "\"$k\": \(\"127.0.0.1\"\|0\|\[\"127.0.0.1:11500\"\]\)" "$stage/$name/system/config.json" ||
      { echo "generate_release.sh: failed to set $k in config.json (example changed?)" >&2; exit 1; }
  done
}

stage_server "$win_build/newserv.exe"
zip="$release/$name-$version-windows.zip"
rm -f "$zip"
(cd "$stage" && python3 -m zipfile -c "$zip" "$name")

stage_server "$linux_build/newserv"
tarball="$release/$name-$version-linux.tar.gz"
rm -f "$tarball"
tar -czf "$tarball" -C "$stage" "$name"

echo "Release files in $release:"
ls -l "$release"
