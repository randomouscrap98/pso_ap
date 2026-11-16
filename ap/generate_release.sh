#!/usr/bin/env bash
# Builds the apworld and a clean Windows newserv, and puts them in <repo>/release (gitignored):
#   release/pso_bb.apworld
#   release/PSOBB-AP-newserv-<version>-windows.zip   (newserv.exe + system/)
# newserv is built in its own dir (release/windows, Release = stripped), never build/. system/ only
# gets git-tracked files (no players/, teams/, caches or a local config.json) plus a config.json generated from
# config.example.json for local play (127.0.0.1, DNS off).
# Usage: generate_release.sh [suffix]   e.g. "rc1" -> PSOBB-AP-newserv-0.0.1-rc1-windows.zip. The apworld stays x.y.z.
# Env: WIN_PREFIX=<Windows deps prefix> builds without podman (Claude's sandbox: WIN_PREFIX=ignore/win-deps).
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

# Windows newserv, Release build in a separate dir
# Separate dirs: a CMake cache only works at the path it was configured at (host vs /src in podman)
if [ -n "${WIN_PREFIX:-}" ]; then
  win_build=release/windows-local
  WIN_PREFIX="$WIN_PREFIX" WIN_BUILD_DIR="$win_build" BUILD_TYPE=Release ap/build.sh win-newserv
else
  win_build=release/windows
  podman image exists newserv-win || podman build -f ap/Containerfile.win -t newserv-win .
  podman run --rm -v "$PWD:/src:Z" -e WIN_BUILD_DIR="$win_build" -e BUILD_TYPE=Release -e J="${J:-8}" \
    newserv-win sh -c "ap/build.sh win-newserv"
fi

# Stage under a named top folder
name="PSOBB-AP-newserv"
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
mkdir -p "$stage/$name"
cp "$win_build/newserv.exe" "$stage/$name/"
git ls-files -z system | xargs -0 cp --parents -t "$stage/$name"
sed -e 's/"LocalAddress": "[^"]*"/"LocalAddress": "127.0.0.1"/' \
    -e 's/"ExternalAddress": "[^"]*"/"ExternalAddress": "127.0.0.1"/' \
    -e 's/"DNSServerPort": 53,/"DNSServerPort": 0,/' \
    system/config.example.json > "$stage/$name/system/config.json"
for k in LocalAddress ExternalAddress DNSServerPort; do
  grep -q "\"$k\": \(\"127.0.0.1\"\|0\)" "$stage/$name/system/config.json" ||
    { echo "generate_release.sh: failed to set $k in config.json (example changed?)" >&2; exit 1; }
done

zip="$release/$name-$version-windows.zip"
rm -f "$zip"
(cd "$stage" && python3 -m zipfile -c "$zip" "$name")

echo "Release files in $release:"
ls -l "$release"
