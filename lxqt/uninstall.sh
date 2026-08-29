#!/usr/bin/env bash
# Desinstala lxqt-tiling del $HOME del usuario.
set -euo pipefail

PREFIX="${PREFIX:-$HOME/.local}"
pkill -f "lxqt_tiling" 2>/dev/null || true

rm -rf  "$PREFIX/lib/lxqt-tiling"
rm -f   "$PREFIX/bin/lxqt-tiling"
rm -f   "$HOME/.config/autostart/lxqt-tiling.desktop"

echo ">> lxqt-tiling desinstalado."