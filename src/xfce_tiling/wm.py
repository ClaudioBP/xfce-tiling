"""Gestión de ventanas mediante libwnck y monitores mediante Gdk.

Encapsula todo lo que depende del gestor de ventanas para que el resto
del código trabaje con rectángulos y objetos ventana simples.
"""

from __future__ import annotations

import gi

gi.require_version("Wnck", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk, Wnck  # noqa: E402


# Tipos de ventana que tiene sentido colocar en una zona.
_TILEABLE_TYPES = {
    Wnck.WindowType.NORMAL,
    Wnck.WindowType.DIALOG,
    Wnck.WindowType.UTILITY,
}


def get_screen() -> Wnck.Screen:
    """Devuelve la pantalla Wnck por defecto, ya actualizada."""
    screen = Wnck.Screen.get_default()
    screen.force_update()
    return screen


def frame_extents(win: Wnck.Window) -> tuple[int, int, int, int]:
    """(left, top, right, bottom) del marco dibujado por el WM.

    Se derivan de la diferencia entre la geometría del marco y la del
    cliente, por lo que funciona igual para ventanas con decoración de
    xfwm4 (extents > 0) y para ventanas CSD (todo 0).
    """
    fx, fy, fw, fh = win.get_geometry()
    cx, cy, cw, ch = win.get_client_window_geometry()
    left = cx - fx
    top = cy - fy
    right = (fx + fw) - (cx + cw)
    bottom = (fy + fh) - (cy + ch)
    return left, top, right, bottom


def has_server_decorations(win: Wnck.Window) -> bool:
    """True si xfwm4 dibuja la decoración (por tanto el botón maximizar)."""
    left, top, right, bottom = frame_extents(win)
    return (left or top or right or bottom) > 0


def is_tileable(win: Wnck.Window) -> bool:
    if win is None:
        return False
    if win.get_window_type() not in _TILEABLE_TYPES:
        return False
    if win.is_minimized() or win.is_shaded():
        return False
    if win.is_skip_tasklist() and win.get_window_type() == Wnck.WindowType.NORMAL:
        # Paneles, docks, escritorio, y nuestro propio popup.
        return False
    return True


def window_under_pointer(screen: Wnck.Screen, px: int, py: int) -> Wnck.Window | None:
    """Ventana visible más al frente cuyo marco contiene el punto (px, py)."""
    active_ws = screen.get_active_workspace()
    # get_windows_stacked va de abajo a arriba; recorremos de arriba a abajo.
    for win in reversed(screen.get_windows_stacked()):
        if not is_tileable(win):
            continue
        if active_ws is not None and not win.is_on_workspace(active_ws):
            continue
        fx, fy, fw, fh = win.get_geometry()
        if fx <= px < fx + fw and fy <= py < fy + fh:
            return win
    return None


_gtk_extents_cache: dict[int, tuple[int, int, int, int]] = {}


def gtk_frame_extents(win: Wnck.Window) -> tuple[int, int, int, int]:
    """(left, right, top, bottom) de _GTK_FRAME_EXTENTS, o ceros.

    Las apps GTK/CSD (Firefox...) reservan márgenes invisibles para su
    sombra; hay que compensarlos para que lo visible llene la zona.
    Cacheado por XID (el sondeo del hover llama esto en cada tick).
    """
    xid = win.get_xid()
    cached = _gtk_extents_cache.get(xid)
    if cached is not None:
        return cached
    try:
        import subprocess

        out = subprocess.run(
            ["xprop", "-id", str(win.get_xid()), "_GTK_FRAME_EXTENTS"],
            capture_output=True, text=True, timeout=2,
        ).stdout
        result = (0, 0, 0, 0)
        if "=" in out:
            vals = [int(v) for v in out.split("=", 1)[1].split(",")]
            if len(vals) == 4:
                result = (vals[0], vals[1], vals[2], vals[3])
        if len(_gtk_extents_cache) > 256:
            _gtk_extents_cache.clear()
        _gtk_extents_cache[xid] = result
        return result
    except Exception:
        return 0, 0, 0, 0


def apply_zone(win: Wnck.Window, x: int, y: int, w: int, h: int) -> None:
    """Coloca el marco EXTERIOR de la ventana en el rectángulo (x, y, w, h).

    Se comprobó empíricamente que, con gravedad STATIC, set_geometry
    interpreta x/y/w/h como el rectángulo exterior del marco, así que no
    hace falta compensar los frame extents.
    """
    if win.is_fullscreen():
        win.set_fullscreen(False)
    if win.is_maximized() or win.is_maximized_horizontally() or win.is_maximized_vertically():
        win.unmaximize()

    # Compensar la sombra invisible de las apps CSD (GTK frame extents).
    gl, gr, gt, gb = gtk_frame_extents(win)
    x -= gl
    y -= gt
    w += gl + gr
    h += gt + gb

    mask = (
        Wnck.WindowMoveResizeMask.X
        | Wnck.WindowMoveResizeMask.Y
        | Wnck.WindowMoveResizeMask.WIDTH
        | Wnck.WindowMoveResizeMask.HEIGHT
    )
    win.set_geometry(Wnck.WindowGravity.STATIC, mask, int(x), int(y), int(w), int(h))
    # Traer al frente usando una marca de tiempo de evento válida cuando
    # exista (el clic en el popup), evitando el aviso "timestamp of 0".
    ts = Gtk.get_current_event_time()
    if ts:
        win.activate(ts)


# --- Monitores ------------------------------------------------------------

def monitor_workarea_at(px: int, py: int) -> tuple[int, int, int, int, int, int]:
    """Para el monitor que contiene el punto (px, py) devuelve:

        (geom_w, geom_h, wa_x, wa_y, wa_w, wa_h)

    geom_w/geom_h -> resolución del monitor (para decidir base/extra).
    wa_*          -> área de trabajo (excluye paneles) donde se colocan
                     las ventanas.
    """
    display = Gdk.Display.get_default()
    monitor = display.get_monitor_at_point(px, py)
    if monitor is None:
        monitor = display.get_primary_monitor() or display.get_monitor(0)
    geom = monitor.get_geometry()
    wa = monitor.get_workarea()
    return geom.width, geom.height, wa.x, wa.y, wa.width, wa.height


def monitor_workarea_for_window(win: Wnck.Window) -> tuple[int, int, int, int, int, int]:
    """Igual que monitor_workarea_at pero para el centro de la ventana."""
    fx, fy, fw, fh = win.get_geometry()
    return monitor_workarea_at(fx + fw // 2, fy + fh // 2)


def pointer_position() -> tuple[int, int]:
    """Posición global del puntero (coordenadas de pantalla)."""
    display = Gdk.Display.get_default()
    seat = display.get_default_seat()
    pointer = seat.get_pointer()
    _screen, x, y = pointer.get_position()
    return x, y
