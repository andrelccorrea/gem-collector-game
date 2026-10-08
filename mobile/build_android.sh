#!/usr/bin/env bash
# Assemble the Android sources and run Buildozer.
#   ./build_android.sh                 -> debug APK   (buildozer android debug)
#   ./build_android.sh android release -> release AAB
#   ./build_android.sh --prepare-only  -> only assemble build_src/
set -euo pipefail
cd "$(dirname "$0")"

rm -rf build_src
mkdir -p build_src/clingine
cp main.py sprites.py build_src/
rsync -a --exclude __pycache__ ../game build_src/
# Only the renderer interface is needed; the curses window and keyboard stay out.
cp ../clingine/renderer.py build_src/clingine/
printf '"""clingine renderer interface (Android build)."""\n' > build_src/clingine/__init__.py

if [[ "${1:-}" == "--prepare-only" ]]; then
  echo "Prepared $(pwd)/build_src"
  exit 0
fi
buildozer ${@:-android debug}
