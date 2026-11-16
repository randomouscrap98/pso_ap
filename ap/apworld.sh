#!/bin/sh
# Build/test the PSOBB apworld against an Archipelago source checkout.
#
# Usage: ap/apworld.sh [env|build|generate [Generate.py args...]]
#   env       clone AP (if missing), create its venv, symlink ap/apworld/pso_bb into its worlds/
#   build     (default) env + official "Build APWorlds" -> build/apworlds/pso_bb.apworld
#   generate  env + Generate.py with the yamls in ap/apworld/players (output: AP_DIR/output)
# Env:
#   AP_DIR   Archipelago checkout   (default ignore/archipelago-0.6.8)
#   AP_REF   tag to clone if missing (default 0.6.8)
#   AP_VENV  venv dir inside AP_DIR  (default .venv, or .venv-musl on musl so hosts sharing the checkout don't clash)
# The venv skips kivy (no GUI needed for building/generating; no musl wheel either).
set -e
cd "$(dirname "$0")/.."
ROOT="$PWD"
STEP="${1:-build}"; [ $# -gt 0 ] && shift
AP_REF="${AP_REF:-0.6.8}"
AP_DIR="${AP_DIR:-ignore/archipelago-$AP_REF}"
WORLD=pso_bb
GAME="Phantasy Star Online Blue Burst"
if [ -z "$AP_VENV" ]; then
  if ldd --version 2>&1 | grep -qi musl; then AP_VENV=.venv-musl; else AP_VENV=.venv; fi
fi
PY="$AP_VENV/bin/python"

setup_env() {
  [ -d "$AP_DIR" ] || git clone --depth 1 -b "$AP_REF" https://github.com/ArchipelagoMW/Archipelago.git "$AP_DIR"
  cd "$AP_DIR"
  # Python 3.13: AP 0.6.x refuses 3.14.
  # Recreate if its python is broken (e.g. made on another machine).
  "$PY" -V >/dev/null 2>&1 || { rm -rf "$AP_VENV"; uv venv --quiet --python 3.13 "$AP_VENV"; }
  if [ ! -f "$AP_VENV/.psobb-setup" ] || [ requirements.txt -nt "$AP_VENV/.psobb-setup" ]; then
    grep -v -i '^kivy' requirements.txt > "$AP_VENV/requirements-nokivy.txt"
    # requests + setuptools<81 (pkg_resources): imported by some bundled worlds, not in requirements.txt.
    uv pip install --quiet --python "$PY" -r "$AP_VENV/requirements-nokivy.txt" requests "setuptools<81"
    # Bundled worlds' deps, best-effort (else their import errors spam every run).
    for r in worlds/*/requirements.txt; do
      uv pip install --quiet --python "$PY" -r "$r" 2>/dev/null || echo "warning: could not install $r" >&2
    done
    touch "$AP_VENV/.psobb-setup"
  fi
  # Relative link: works wherever the repo is mounted.
  [ -L "worlds/$WORLD" ] || ln -s "$(python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], "worlds"))' \
    "$ROOT/ap/apworld/$WORLD")" "worlds/$WORLD"
  export SKIP_REQUIREMENTS_UPDATE=1
  export PYTHONWARNINGS="ignore:pkg_resources is deprecated:UserWarning"
}

case "$STEP" in
  env) setup_env ;;
  build)
    setup_env
    "$PY" Launcher.py "Build APWorlds" -- "$GAME" --skip_open_folder
    mkdir -p "$ROOT/build/apworlds"
    cp "build/apworlds/$WORLD.apworld" "$ROOT/build/apworlds/"
    echo "built $ROOT/build/apworlds/$WORLD.apworld"
    ;;
  generate)
    setup_env
    "$PY" Generate.py --player_files_path "$ROOT/ap/apworld/players" "$@"
    ;;
  *) echo "usage: $0 [env|build|generate [args...]]" >&2; exit 1 ;;
esac
