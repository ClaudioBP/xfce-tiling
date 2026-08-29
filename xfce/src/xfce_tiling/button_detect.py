"""Cálculo de la posición del botón "maximizar" de xfwm4.

Solo es posible en ventanas con decoración de servidor (xfwm4 dibuja los
botones). En ventanas CSD (Chrome, Electron, VS Code...) el botón lo pinta
la propia app y su posición no es detectable: en ese caso devolvemos None
y el disparador por hover simplemente no actúa (queda el atajo global).

Modelo de disposición de xfwm4:
  * `button_layout` (p. ej. "O|SHMC"): las letras antes de "|" van
    alineadas a la izquierda del título y las de después a la derecha.
  * Cada botón tiene el ancho de su imagen de tema (`<nombre>-active.png`).
  * Entre botones hay `button_spacing` px (del themerc del tema).
  * Letras: O=menú, S=shade, H=minimizar, M=maximizar, C=cerrar, T=título.
"""

from __future__ import annotations

import os

import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, Gio  # noqa: E402

from . import wm

# Letra de layout -> nombre base del fichero de imagen del tema.
_BUTTON_FILE = {
    "O": "menu",
    "S": "shade",
    "H": "hide",
    "M": "maximize",
    "C": "close",
    # "T" (título) y "|" se tratan aparte.
}

_THEME_SEARCH_DIRS = [
    os.path.expanduser("~/.themes"),
    os.path.expanduser("~/.local/share/themes"),
    "/usr/share/themes",
]


def _xfconf(prop: str, default: str) -> str:
    """Lee una propiedad del canal xfwm4 sin depender del binario."""
    try:
        import subprocess

        out = subprocess.run(
            ["xfconf-query", "-c", "xfwm4", "-p", prop],
            capture_output=True, text=True, timeout=2,
        )
        val = out.stdout.strip()
        return val or default
    except Exception:
        return default


class ThemeGeometry:
    """Anchos de botón y espaciado del tema xfwm4 activo (cacheado)."""

    def __init__(self) -> None:
        self.theme = _xfconf("/general/theme", "Default")
        self.layout = _xfconf("/general/button_layout", "O|SHMC")
        self.theme_dir = self._find_theme_dir(self.theme)
        self.spacing = 2
        self.offset = 0
        self._widths: dict[str, int] = {}
        self._height = 0
        if self.theme_dir:
            self._read_themerc()
            self._read_button_widths()

    def _find_theme_dir(self, theme: str) -> str | None:
        for base in _THEME_SEARCH_DIRS:
            d = os.path.join(base, theme, "xfwm4")
            if os.path.isdir(d):
                return d
        return None

    def _read_themerc(self) -> None:
        path = os.path.join(self.theme_dir, "themerc")
        if not os.path.isfile(path):
            return
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    line = line.strip()
                    if line.startswith("button_spacing="):
                        self.spacing = int(line.split("=", 1)[1] or 0)
                    elif line.startswith("button_offset="):
                        self.offset = int(line.split("=", 1)[1] or 0)
        except Exception:
            pass

    def _read_button_widths(self) -> None:
        for letter, name in _BUTTON_FILE.items():
            f = os.path.join(self.theme_dir, f"{name}-active.png")
            if os.path.isfile(f):
                try:
                    pb = GdkPixbuf.Pixbuf.new_from_file(f)
                    self._widths[letter] = pb.get_width()
                    self._height = max(self._height, pb.get_height())
                except Exception:
                    pass

    def width_of(self, letter: str) -> int:
        return self._widths.get(letter, 0)

    @property
    def valid(self) -> bool:
        return "M" in self._widths


# Instancia perezosa; se puede refrescar si cambia el tema.
_geometry: ThemeGeometry | None = None


def theme_geometry(refresh: bool = False) -> ThemeGeometry:
    global _geometry
    if _geometry is None or refresh:
        _geometry = ThemeGeometry()
    return _geometry


# --- Casos especiales CSD -------------------------------------------------
#
# Apps sin decoración del servidor (dibujan sus propios botones). No es
# posible detectar el botón real, así que definimos un rectángulo virtual
# donde la app pinta su botón de maximizar, relativo a la esquina superior
# derecha de la ventana:
#
#   clase (minúsculas) -> (right_offset, width, height)
#
#   right_offset = distancia desde el borde derecho de la ventana hasta el
#                  borde derecho del botón maximizar (normalmente el ancho
#                  del botón de cerrar).
#   width/height = tamaño de la zona sensible.
_CSD_APPS: dict[str, tuple[int, int, int]] = {
    "firefox":       (40, 60, 40),
    "firefox-esr":   (40, 60, 40),
    "google-chrome": (40, 60, 40),
    "chromium":      (40, 60, 40),
}


def _csd_button_rect(win) -> tuple[int, int, int, int] | None:
    """Rectángulo virtual del botón maximizar para apps CSD conocidas."""
    try:
        cls = (win.get_class_group_name() or "").lower()
    except Exception:
        return None
    spec = _CSD_APPS.get(cls)
    if spec is None:
        return None
    right_offset, bw, bh = spec
    fx, fy, fw, _fh = win.get_geometry()
    # Descontar la sombra invisible CSD: el borde visible está más adentro.
    _gl, gr, gt, _gb = wm.gtk_frame_extents(win)
    x0 = fx + fw - gr - right_offset - bw
    return int(x0), int(fy + gt), int(bw), int(bh)


def maximize_button_rect(win) -> tuple[int, int, int, int] | None:
    """Rectángulo (x, y, w, h) del botón maximizar en coordenadas de
    pantalla, o None si no es detectable (CSD o tema sin datos)."""
    if not wm.has_server_decorations(win):
        return _csd_button_rect(win)

    geom = theme_geometry()
    if not geom.valid:
        return None

    fx, fy, fw, fh = win.get_geometry()
    left, top, right, _bottom = wm.frame_extents(win)

    parts = geom.layout.split("|")
    left_group = parts[0] if parts else ""
    right_group = parts[1] if len(parts) > 1 else ""

    def button_width(letter: str) -> int:
        return geom.width_of(letter)

    # Grupo derecho: se dibuja pegado al borde derecho interior,
    # colocando botones de derecha a izquierda.
    if "M" in right_group:
        x_right = fx + fw - right - geom.offset
        # recorremos de la última letra a la primera
        letters = [c for c in right_group if c in _BUTTON_FILE]
        for letter in reversed(letters):
            w = button_width(letter)
            if w <= 0:
                continue
            x0 = x_right - w
            if letter == "M":
                return _finalize_rect(x0, fy, w, top, geom)
            x_right = x0 - geom.spacing
        return None

    # Grupo izquierdo: pegado al borde izquierdo interior, de izq. a der.
    if "M" in left_group:
        x_left = fx + left + geom.offset
        letters = [c for c in left_group if c in _BUTTON_FILE]
        for letter in letters:
            w = button_width(letter)
            if w <= 0:
                continue
            if letter == "M":
                return _finalize_rect(x_left, fy, w, top, geom)
            x_left = x_left + w + geom.spacing
        return None

    return None


def _finalize_rect(x0, fy, w, top, geom):
    """Ajusta el rectángulo vertical del botón dentro de la barra de
    título y añade un pequeño margen de tolerancia para el hover."""
    # El botón ocupa la altura de su imagen, centrado en la barra (top).
    bh = geom._height or top
    by = fy + max(0, (top - bh) // 2)
    return int(x0), int(by), int(w), int(bh)
