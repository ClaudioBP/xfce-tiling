#!/usr/bin/env bash
# Instala lxqt-tiling en el $HOME del usuario (sin privilegios de root):
#   * código  -> ~/.local/lib/lxqt-tiling/lxqt_tiling
#   * lanzador -> ~/.local/bin/lxqt-tiling
#   * autostart -> ~/.config/autostart/lxqt-tiling.desktop
set -euo pipefail

src_dir="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"

PREFIX="${PREFIX:-$HOME/.local}"
LIBDIR="$PREFIX/lib/lxqt-tiling"
BINDIR="$PREFIX/bin"
AUTOSTART="$HOME/.config/autostart"

echo ">> Comprobando dependencias..."
missing=0
python3 - <<'PY' || missing=1
import gi
for mod, ver in [("Gtk","3.0"),("Gdk","3.0"),("Wnck","3.0"),
                 ("Keybinder","3.0"),("GdkPixbuf","2.0")]:
    gi.require_version(mod, ver)
    __import__("gi.repository." + mod)
print("   dependencias GObject OK")
PY
if [ "$missing" != "0" ]; then
    cat <<'EOF'
!! Faltan bibliotecas. En Debian/LXQt instala:
   sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-wnck-3.0 \
                    gir1.2-keybinder-3.0 gir1.2-gdkpixbuf-2.0
EOF
    exit 1
fi

if ! command -v openbox >/dev/null 2>&1; then
    echo "!! Aviso: no se encontró openbox; lxqt-tiling espera el WM openbox"
    echo "   (el gestor por defecto de LXQt)."
fi

echo ">> Instalando código en $LIBDIR"
mkdir -p "$LIBDIR"
rm -rf "$LIBDIR/lxqt_tiling"
cp -r "$src_dir/src/lxqt_tiling" "$LIBDIR/lxqt_tiling"

echo ">> Instalando lanzador en $BINDIR/lxqt-tiling"
mkdir -p "$BINDIR"
install -m 0755 "$src_dir/bin/lxqt-tiling" "$BINDIR/lxqt-tiling"

echo ">> Instalando autostart en $AUTOSTART"
mkdir -p "$AUTOSTART"
# Exec= debe llevar ruta absoluta: el generador XDG de autostart no hereda
# el PATH de la shell, así que $BINDIR (p.ej. ~/.local/bin) no está en él y
# la entrada se descarta con "Exec binary does not exist".
sed "s|^Exec=lxqt-tiling |Exec=$BINDIR/lxqt-tiling |" \
    "$src_dir/data/lxqt-tiling.desktop" > "$AUTOSTART/lxqt-tiling.desktop"
chmod 0644 "$AUTOSTART/lxqt-tiling.desktop"

case ":$PATH:" in
    *":$BINDIR:"*) : ;;
    *) echo "!! Aviso: $BINDIR no está en tu PATH; añádelo a ~/.profile" ;;
esac

echo ""
echo ">> Instalado. Para arrancarlo ahora sin reiniciar sesión:"
echo "     lxqt-tiling daemon &"
echo "   Se iniciará automáticamente en el próximo inicio de sesión."
echo "   Atajo global por defecto: Super+Z"