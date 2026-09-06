"""Cálculo de la posición del botón "maximizar" según el gestor.

En openbox (el WM de LXQt) el botón lo dibuja el propio openbox en ventanas
con decoración de servidor, y su posición se calcula a partir del
``titleLayout`` del rc.xml y del themerc activo (ver ``openbox_button``).
En ventanas CSD (Chrome, Electron, VS Code...) el botón lo pinta la propia
app y su posición no es detectable: en ese caso devolvemos None y el
disparador por hover simplemente no actúa (queda el atajo global).
"""

from __future__ import annotations

import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, Gio  # noqa: E402

from . import openbox_button, wm

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
    "chatgpt":       (40, 60, 40),  # Codex desktop: WM_CLASS = Chatgpt
}

# Configuración de openbox cacheada; se puede refrescar si cambia rc.xml.
_config: openbox_button.OpenboxConfig | None = None


def openbox_config(refresh: bool = False) -> openbox_button.OpenboxConfig:
    global _config
    if _config is None or refresh:
        _config = openbox_button.OpenboxConfig.load()
    return _config


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
    pantalla, o None si no es detectable (CSD o configuración sin datos)."""
    if not wm.has_server_decorations(win):
        return _csd_button_rect(win)

    # Si la ventana no puede maximizarse, openbox no dibuja el botón.
    try:
        if not win.can_maximize():
            return None
    except Exception:
        pass

    return openbox_button.maximize_button_rect(
        *win.get_geometry(),
        wm.frame_extents(win),
        openbox_config(),
    )