#!/usr/bin/env bash
# Desinstala xfce-tiling del $HOME del usuario.
set -euo pipefail

PREFIX="${PREFIX:-$HOME/.local}"
pkill -f "xfce_tiling" 2>/dev/null || true

rm -rf  "$PREFIX/lib/xfce-tiling"
rm -f   "$PREFIX/bin/xfce-tiling"
rm -f   "$HOME/.config/autostart/xfce-tiling.desktop"

echo ">> xfce-tiling desinstalado."
