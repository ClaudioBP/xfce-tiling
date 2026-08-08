"""Lectura directa de WM_NORMAL_HINTS y _NET_FRAME_EXTENTS vía Xlib.

libwnck no expone los *size hints* del cliente, y su geometría cacheada
va por detrás del servidor justo después de desmaximizar, así que aquí se
consulta al servidor X con ctypes (sin dependencias nuevas).

Hace falta porque las apps que declaran incrementos de redimensión
(terminales, Emacs, xterm...) solo aceptan tamaños de cliente
``base + n * incremento``. Si se les pide el tamaño exacto de una zona,
GTK se auto-corrige al múltiplo inferior y deja unos píxeles de escritorio
a la vista dentro de la zona.
"""

from __future__ import annotations

import ctypes
import ctypes.util
from dataclasses import dataclass

# Banderas de XSizeHints (X11/Xutil.h).
_P_MIN_SIZE = 1 << 4
_P_MAX_SIZE = 1 << 5
_P_RESIZE_INC = 1 << 6
_P_BASE_SIZE = 1 << 8

_XA_CARDINAL = 6


class _XSizeHints(ctypes.Structure):
    _fields_ = [
        ("flags", ctypes.c_long),
        ("x", ctypes.c_int), ("y", ctypes.c_int),
        ("width", ctypes.c_int), ("height", ctypes.c_int),
        ("min_width", ctypes.c_int), ("min_height", ctypes.c_int),
        ("max_width", ctypes.c_int), ("max_height", ctypes.c_int),
        ("width_inc", ctypes.c_int), ("height_inc", ctypes.c_int),
        ("min_aspect_x", ctypes.c_int), ("min_aspect_y", ctypes.c_int),
        ("max_aspect_x", ctypes.c_int), ("max_aspect_y", ctypes.c_int),
        ("base_width", ctypes.c_int), ("base_height", ctypes.c_int),
        ("win_gravity", ctypes.c_int),
    ]


def _open_display():
    """Conexión X propia y de solo lectura, o None si no hay libX11/DISPLAY."""
    try:
        name = ctypes.util.find_library("X11")
        if not name:
            return None, None
        lib = ctypes.CDLL(name)
    except OSError:
        return None, None

    lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
    lib.XOpenDisplay.restype = ctypes.c_void_p
    lib.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    lib.XInternAtom.restype = ctypes.c_ulong
    lib.XGetWMNormalHints.argtypes = [
        ctypes.c_void_p, ctypes.c_ulong,
        ctypes.POINTER(_XSizeHints), ctypes.POINTER(ctypes.c_long),
    ]
    lib.XGetWMNormalHints.restype = ctypes.c_int
    lib.XGetWindowProperty.argtypes = [
        ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong,
        ctypes.c_long, ctypes.c_long, ctypes.c_int, ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
        ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),
    ]
    lib.XGetWindowProperty.restype = ctypes.c_int
    lib.XGetGeometry.argtypes = [
        ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong),
        ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint),
        ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint),
    ]
    lib.XGetGeometry.restype = ctypes.c_int
    lib.XTranslateCoordinates.argtypes = [
        ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong,
        ctypes.c_int, ctypes.c_int,
        ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_ulong),
    ]
    lib.XTranslateCoordinates.restype = ctypes.c_int
    lib.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    lib.XDefaultRootWindow.restype = ctypes.c_ulong
    lib.XFree.argtypes = [ctypes.c_void_p]
    # Silenciar el manejador de errores por defecto: pedir propiedades de una
    # ventana que acaba de cerrarse mataría el proceso con BadWindow.
    lib.XSetErrorHandler.argtypes = [ctypes.c_void_p]
    lib.XSetErrorHandler.restype = ctypes.c_void_p

    display = lib.XOpenDisplay(None)
    if not display:
        return None, None
    return lib, display


_X11, _DISPLAY = _open_display()

# Debe mantenerse vivo mientras dure el proceso: si el objeto ctypes se
# recolecta, Xlib llama a un puntero liberado en el siguiente error.
_ERROR_HANDLER_PROTO = ctypes.CFUNCTYPE(
    ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p
)
_ERROR_HANDLER = _ERROR_HANDLER_PROTO(lambda _display, _event: 0)
if _X11 is not None:
    _X11.XSetErrorHandler(ctypes.cast(_ERROR_HANDLER, ctypes.c_void_p))


@dataclass(frozen=True)
class SizeHints:
    """Rejilla de tamaños de cliente que la ventana acepta.

    Los tamaños válidos son ``base + n * inc`` (n >= 0), acotados por
    ``min`` y, si la ventana lo declara, por ``max``.
    """

    base_w: int
    base_h: int
    inc_w: int
    inc_h: int
    min_w: int
    min_h: int
    max_w: int | None
    max_h: int | None

    def fit_frame(
        self,
        width: int,
        height: int,
        extents: tuple[int, int, int, int],
    ) -> tuple[int, int, int, int]:
        """Mayor marco aceptado dentro de ``width × height``, centrado.

        Devuelve ``(dx, dy, frame_w, frame_h)``. Los desplazamientos reparten
        el espacio que no alcanza para otra celda; si sobra un píxel impar,
        queda del lado derecho o inferior.
        """
        left, right, top, bottom = extents
        client_w = _snap_down(
            width - left - right,
            self.base_w,
            self.inc_w,
            self.min_w,
            self.max_w,
        )
        client_h = _snap_down(
            height - top - bottom,
            self.base_h,
            self.inc_h,
            self.min_h,
            self.max_h,
        )
        frame_w = client_w + left + right
        frame_h = client_h + top + bottom
        return (
            (width - frame_w) // 2,
            (height - frame_h) // 2,
            frame_w,
            frame_h,
        )

def _snap_down(value: int, base: int, inc: int, minimum: int, maximum: int | None) -> int:
    """Mayor tamaño de la rejilla que no exceda ``value``.

    Si el mínimo declarado ya excede ``value``, devuelve el primer tamaño de
    la rejilla que satisface el mínimo: no existe un tamaño válido que quepa y
    respetar los hints de la aplicación tiene prioridad.
    """
    if inc <= 1:
        size = value
        if size < minimum:
            size = minimum
        if maximum is not None:
            size = min(size, maximum)
        return size

    upper = min(value, maximum) if maximum is not None else value
    steps = max((upper - base) // inc, 0)
    size = base + steps * inc
    if size < minimum:
        steps = -(-(minimum - base) // inc)
        size = base + max(steps, 0) * inc
    if maximum is not None and size > maximum:
        steps = (maximum - base) // inc
        size = base + max(steps, 0) * inc
    return size


def size_hints(xid: int) -> SizeHints | None:
    """Hints de la ventana, o None si no declara incrementos > 1 px.

    Devolver None es el caso normal: casi ninguna app usa incrementos, y
    esas no necesitan compensación alguna.
    """
    if _X11 is None:
        return None
    hints = _XSizeHints()
    supplied = ctypes.c_long()
    if not _X11.XGetWMNormalHints(_DISPLAY, xid, ctypes.byref(hints), ctypes.byref(supplied)):
        return None
    if not hints.flags & _P_RESIZE_INC:
        return None
    inc_w = max(hints.width_inc, 1)
    inc_h = max(hints.height_inc, 1)
    if inc_w <= 1 and inc_h <= 1:
        return None

    min_w = hints.min_width if hints.flags & _P_MIN_SIZE else 0
    min_h = hints.min_height if hints.flags & _P_MIN_SIZE else 0
    # ICCCM: sin PBaseSize, el tamaño mínimo hace de base (y viceversa).
    if hints.flags & _P_BASE_SIZE:
        base_w, base_h = hints.base_width, hints.base_height
    else:
        base_w, base_h = min_w, min_h
    if not hints.flags & _P_MIN_SIZE:
        min_w, min_h = base_w, base_h

    has_max = bool(hints.flags & _P_MAX_SIZE)
    return SizeHints(
        base_w=max(base_w, 0), base_h=max(base_h, 0),
        inc_w=inc_w, inc_h=inc_h,
        min_w=max(min_w, 0), min_h=max(min_h, 0),
        max_w=hints.max_width if has_max else None,
        max_h=hints.max_height if has_max else None,
    )


def net_frame_extents(xid: int) -> tuple[int, int, int, int] | None:
    """(left, right, top, bottom) de _NET_FRAME_EXTENTS, leído del servidor.

    None si la ventana no tiene la propiedad (apps CSD) o no se pudo leer.
    A diferencia de ``wm.frame_extents``, no pasa por la caché de libwnck,
    así que es fiable inmediatamente después de desmaximizar.
    """
    return _cardinal4(xid, b"_NET_FRAME_EXTENTS")


def _cardinal4(xid: int, name: bytes) -> tuple[int, int, int, int] | None:
    """Lee una propiedad de 4 CARDINAL de 32 bits."""
    if _X11 is None:
        return None
    prop = _X11.XInternAtom(_DISPLAY, name, 1)
    if not prop:
        return None
    actual_type = ctypes.c_ulong()
    actual_format = ctypes.c_int()
    nitems = ctypes.c_ulong()
    bytes_after = ctypes.c_ulong()
    data = ctypes.POINTER(ctypes.c_ubyte)()
    status = _X11.XGetWindowProperty(
        _DISPLAY, xid, prop, 0, 4, 0, _XA_CARDINAL,
        ctypes.byref(actual_type), ctypes.byref(actual_format),
        ctypes.byref(nitems), ctypes.byref(bytes_after), ctypes.byref(data),
    )
    if status != 0:
        return None
    try:
        if not data or nitems.value < 4 or actual_format.value != 32:
            return None
        values = ctypes.cast(data, ctypes.POINTER(ctypes.c_ulong))
        return tuple(int(values[i]) for i in range(4))  # type: ignore[return-value]
    finally:
        if data:
            _X11.XFree(data)


def gtk_frame_extents(xid: int) -> tuple[int, int, int, int] | None:
    """(left, right, top, bottom) de _GTK_FRAME_EXTENTS, o None si no existe.

    Es el margen invisible que las apps CSD reservan para su sombra.
    """
    return _cardinal4(xid, b"_GTK_FRAME_EXTENTS")


def frame_rect(xid: int) -> tuple[int, int, int, int] | None:
    """(x, y, w, h) del marco exterior tal y como lo ve el servidor X.

    Equivale a ``Wnck.Window.get_geometry()`` pero sin caché, así que sirve
    para comprobar de verdad qué hizo el WM con una petición recién enviada.
    """
    if _X11 is None:
        return None
    root = ctypes.c_ulong()
    x = ctypes.c_int(); y = ctypes.c_int()
    width = ctypes.c_uint(); height = ctypes.c_uint()
    border = ctypes.c_uint(); depth = ctypes.c_uint()
    if not _X11.XGetGeometry(
        _DISPLAY, xid, ctypes.byref(root), ctypes.byref(x), ctypes.byref(y),
        ctypes.byref(width), ctypes.byref(height),
        ctypes.byref(border), ctypes.byref(depth),
    ):
        return None
    # x/y de XGetGeometry son relativos al padre (el marco del WM), así que
    # hay que traducirlos a coordenadas de pantalla.
    abs_x = ctypes.c_int(); abs_y = ctypes.c_int(); child = ctypes.c_ulong()
    if not _X11.XTranslateCoordinates(
        _DISPLAY, xid, _X11.XDefaultRootWindow(_DISPLAY), 0, 0,
        ctypes.byref(abs_x), ctypes.byref(abs_y), ctypes.byref(child),
    ):
        return None
    left, right, top, bottom = net_frame_extents(xid) or (0, 0, 0, 0)
    return (
        abs_x.value - left,
        abs_y.value - top,
        width.value + left + right,
        height.value + top + bottom,
    )
