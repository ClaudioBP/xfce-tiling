#!/usr/bin/env bash
# Instala xfce-tiling en el $HOME del usuario (sin privilegios de root):
#   * código  -> ~/.local/lib/xfce-tiling/xfce_tiling
#   * lanzador -> ~/.local/bin/xfce-tiling
#   * autostart -> ~/.config/autostart/xfce-tiling.desktop
set -euo pipefail

src_dir="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"

PREFIX="${PREFIX:-$HOME/.local}"
LIBDIR="$PREFIX/lib/xfce-tiling"
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
!! Faltan bibliotecas. En Debian/XFCE instala:
   sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-wnck-3.0 \
                    gir1.2-keybinder-3.0 gir1.2-gdkpixbuf-2.0
EOF
    exit 1
fi

echo ">> Instalando código en $LIBDIR"
mkdir -p "$LIBDIR"
rm -rf "$LIBDIR/xfce_tiling"
cp -r "$src_dir/src/xfce_tiling" "$LIBDIR/xfce_tiling"

echo ">> Instalando lanzador en $BINDIR/xfce-tiling"
mkdir -p "$BINDIR"
install -m 0755 "$src_dir/bin/xfce-tiling" "$BINDIR/xfce-tiling"

echo ">> Instalando autostart en $AUTOSTART"
mkdir -p "$AUTOSTART"
# Exec= debe llevar ruta absoluta: el generador XDG de autostart no hereda
# el PATH de la shell, así que $BINDIR (p.ej. ~/.local/bin) no está en él y
# la entrada se descarta con "Exec binary does not exist".
sed "s|^Exec=xfce-tiling |Exec=$BINDIR/xfce-tiling |" \
    "$src_dir/data/xfce-tiling.desktop" > "$AUTOSTART/xfce-tiling.desktop"
chmod 0644 "$AUTOSTART/xfce-tiling.desktop"

case ":$PATH:" in
    *":$BINDIR:"*) : ;;
    *) echo "!! Aviso: $BINDIR no está en tu PATH; añádelo a ~/.profile" ;;
esac

echo ""
echo ">> Instalado. Para arrancarlo ahora sin reiniciar sesión:"
echo "     xfce-tiling daemon &"
echo "   Se iniciará automáticamente en el próximo inicio de sesión."
echo "   Atajo global por defecto: Super+Z"
