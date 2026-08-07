"""Gestión de ventanas mediante libwnck y monitores mediante Gdk.

Encapsula todo lo que depende del gestor de ventanas para que el resto
del código trabaje con rectángulos y objetos ventana simples.
"""

from __future__ import annotations

import time

import gi

gi.require_version("Wnck", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk, Wnck  # noqa: E402

from . import sizehints  # noqa: E402


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
    """(left, right, top, bottom) de _GTK_FRAME_EXTENTS ahora mismo, o ceros.

    Las apps GTK/CSD (Firefox...) reservan márgenes invisibles para su
    sombra. Es el valor instantáneo: una ventana maximizada no tiene sombra
    y devuelve ceros, que es justo lo que necesita el sondeo del hover para
    situar el botón maximizar.
    """
    return sizehints.gtk_frame_extents(win.get_xid()) or (0, 0, 0, 0)


def resting_gtk_frame_extents(win: Wnck.Window) -> tuple[int, int, int, int]:
    """La sombra CSD que tendrá la ventana una vez colocada en su zona.

    GTK colapsa `_GTK_FRAME_EXTENTS` a cero mientras la ventana está
    maximizada y la vuelve a expandir con una animación de unos 220 ms, así
    que un valor leído en ese tramo se queda corto y la ventana quedaría
    metida hacia dentro de su zona. La sombra es constante para una ventana
    dada, de modo que se guarda la mayor vista por XID: converge al valor
    bueno y nunca retrocede.
    """
    xid = win.get_xid()
    current = gtk_frame_extents(win)
    cached = _gtk_extents_cache.get(xid)
    if cached is not None:
        current = tuple(max(pair) for pair in zip(cached, current))
    if len(_gtk_extents_cache) > 256:
        _gtk_extents_cache.clear()
    _gtk_extents_cache[xid] = current
    return current


# Medido en xfwm4 4.20: la decoración se actualiza ~35 ms tras desmaximizar.
# Si aun así se agotara el plazo, la verificación diferida acaba corrigiéndolo.
_SETTLE_TIMEOUT_S = 0.15
_SETTLE_POLL_S = 0.005


def _settled_frame_extents(xid: int, stale: tuple[int, int, int, int] | None):
    """_NET_FRAME_EXTENTS una vez que deja de valer `stale`.

    Al desmaximizar, xfwm4 devuelve los bordes normales unos 30 ms después.
    Leer los de la ventana maximizada (0,0,24,0 en vez de 5,5,29,5)
    desplazaría el cálculo de incrementos casi media celda.
    """
    deadline = time.monotonic() + _SETTLE_TIMEOUT_S
    while True:
        current = sizehints.net_frame_extents(xid)
        if current != stale or time.monotonic() >= deadline:
            return current
        time.sleep(_SETTLE_POLL_S)


def _cover_zone(xid: int, w: int, h: int, extents: tuple[int, int, int, int]) -> tuple[int, int]:
    """Agranda (w, h) hasta el primer tamaño de marco que la ventana acepte.

    Las apps con incrementos de redimensión (xfce4-terminal, xterm, Emacs...)
    solo admiten un cliente de ``base + n * incremento`` píxeles. Si se les
    pide el tamaño exacto de la zona, GTK redondea hacia abajo y quedan hasta
    ``incremento - 1`` píxeles de escritorio a la vista dentro de la zona
    (con la fuente por defecto de xfce4-terminal: 9 px a la derecha y 18 abajo).

    Se redondea hacia arriba para que la ventana cubra la zona entera; el
    sobrante invade unos píxeles la zona vecina de la derecha y de abajo.
    Las ventanas sin incrementos —la inmensa mayoría— salen intactas.
    """
    hints = sizehints.size_hints(xid)
    if hints is None:
        return w, h
    left, right, top, bottom = extents
    client_w, client_h = hints.snap_up(w - left - right, h - top - bottom)
    return client_w + left + right, client_h + top + bottom


# Dos repasos: el primero llega a tiempo para el desfase de xfwm4 y el
# segundo, ya con la animación de la sombra CSD terminada (~220 ms).
_VERIFY_MS = (150, 400)

_MOVE_RESIZE_MASK = (
    Wnck.WindowMoveResizeMask.X
    | Wnck.WindowMoveResizeMask.Y
    | Wnck.WindowMoveResizeMask.WIDTH
    | Wnck.WindowMoveResizeMask.HEIGHT
)


def _target_rect(
    win: Wnck.Window,
    zone: tuple[int, int, int, int],
    extents: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    """Marco exterior a pedir para que la ventana cubra `zone`."""
    x, y, w, h = zone
    # Compensar la sombra invisible de las apps CSD (GTK frame extents).
    gl, gr, gt, gb = resting_gtk_frame_extents(win)
    x -= gl
    y -= gt
    w += gl + gr
    h += gt + gb
    w, h = _cover_zone(win.get_xid(), w, h, extents)
    return int(x), int(y), int(w), int(h)


def _request_geometry(win: Wnck.Window, rect: tuple[int, int, int, int]) -> None:
    win.set_geometry(Wnck.WindowGravity.STATIC, _MOVE_RESIZE_MASK, *rect)


# Última zona pedida por ventana. Evita que el repaso diferido de una zona
# devuelva la ventana a su sitio si mientras tanto se ha elegido otra.
_last_request: dict[int, int] = {}
_request_serial = 0


def _verify_geometry(win: Wnck.Window, zone: tuple[int, int, int, int], serial: int) -> bool:
    """Recalcula el objetivo y lo vuelve a pedir si el WM no lo aplicó.

    Hace falta porque justo después de desmaximizar ni xfwm4 ni la propia
    ventana tienen aún sus medidas definitivas. Es idempotente: si la
    geometría ya es la buena, no toca nada. Devuelve False (no repetir).
    """
    try:
        xid = win.get_xid()
        if _last_request.get(xid) != serial:
            return False   # la ventana ya se ha mandado a otra zona
        extents = sizehints.net_frame_extents(xid) or (0, 0, 0, 0)
        rect = _target_rect(win, zone, extents)
        if sizehints.frame_rect(xid) != rect:
            _request_geometry(win, rect)
    except Exception:
        pass
    return False


def apply_zone(win: Wnck.Window, x: int, y: int, w: int, h: int) -> None:
    """Coloca el marco EXTERIOR de la ventana en el rectángulo (x, y, w, h).

    Se comprobó empíricamente que, con gravedad STATIC, set_geometry
    interpreta x/y/w/h como el rectángulo exterior del marco, así que no
    hace falta compensar los frame extents... salvo en la primera petición
    tras desmaximizar, que xfwm4 convierte con la decoración de la ventana
    maximizada. De ahí la verificación diferida.
    """
    xid = win.get_xid()
    # Antes de tocar el estado: con la ventana maximizada la decoración mide
    # otra cosa, y esto sirve de referencia para saber cuándo ha cambiado.
    stale_extents = sizehints.net_frame_extents(xid)

    was_constrained = False
    if win.is_fullscreen():
        win.set_fullscreen(False)
        was_constrained = True
    if win.is_maximized() or win.is_maximized_horizontally() or win.is_maximized_vertically():
        win.unmaximize()
        was_constrained = True

    extents = stale_extents or (0, 0, 0, 0)
    if was_constrained:
        # Que el WM empiece a desmaximizar ya, no al vaciarse la cola de Gdk.
        Gdk.flush()
        if sizehints.size_hints(xid) is not None:
            # Solo el redondeo por incrementos necesita la decoración exacta.
            # Para el resto basta con la verificación diferida, y así no se
            # espera en balde por las ventanas CSD, cuyo _NET_FRAME_EXTENTS
            # vale (0,0,0,0) tanto maximizadas como no.
            extents = _settled_frame_extents(xid, stale_extents) or (0, 0, 0, 0)

    global _request_serial
    _request_serial += 1
    if len(_last_request) > 256:
        _last_request.clear()
    _last_request[xid] = _request_serial

    zone = (x, y, w, h)
    _request_geometry(win, _target_rect(win, zone, extents))
    if was_constrained:
        # xfwm4 aplica mal la primera petición que sigue a un unmaximize:
        # convierte el tamaño usando la decoración de la ventana maximizada.
        for delay in _VERIFY_MS:
            GLib.timeout_add(delay, _verify_geometry, win, zone, _request_serial)

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
