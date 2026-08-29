"""Ventana emergente con la rejilla de zonas de tiling.

Muestra una vista en miniatura de cada zona (estilo "Snap Layouts" de
Windows 11). Al hacer clic se coloca la ventana objetivo en esa zona.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gtk  # noqa: E402

from . import wm
from .layouts import Zone, zones_for_monitor

_CELL_W = 52
_CELL_H = 34
_PAD = 2


class TilingPopup(Gtk.Window):
    """Popup de zonas para una ventana objetivo concreta."""

    def __init__(self, target, anchor_rect, modal: bool):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.target = target
        self._modal = modal

        self.set_decorated(False)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_accept_focus(modal)
        self.set_name("lxqt-tiling-popup")

        # Resolución del monitor donde está la ventana -> juego de zonas.
        mw, mh, wax, way, waw, wah = wm.monitor_workarea_for_window(target)
        self._workarea = (wax, way, waw, wah)
        zones = zones_for_monitor(mw, mh)

        self.add(self._build_ui(zones))
        self._apply_css()

        self.connect("key-press-event", self._on_key)
        if modal:
            self.connect("focus-out-event", lambda *_: (self.destroy(), False)[1])

        self.show_all()
        self._place(anchor_rect)

    # --- construcción de la interfaz -------------------------------------

    def _build_ui(self, zones: list[Zone]) -> Gtk.Widget:
        # Las secciones se disponen en columnas lado a lado para mantener
        # el popup compacto en altura.
        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        outer.set_border_width(10)
        outer.get_style_context().add_class("tiling-root")

        base = [z for z in zones if z.group == "base"]
        extra = [z for z in zones if z.group == "extra"]

        columns: list[Gtk.Widget] = [
            self._section("Mitades y cuartos", [base[0:4], base[4:8]]),
        ]

        if extra:
            columns.append(self._section("Tercios, sextos y novenos", [
                extra[0:3],    # tercios verticales
                extra[3:6],    # tercios horizontales
                extra[6:9],    # sextos fila superior
                extra[9:12],   # sextos fila inferior
                extra[12:15],  # novenos fila superior
                extra[15:18],  # novenos fila central
                extra[18:21],  # novenos fila inferior
            ]))
            columns.append(self._section("Dos tercios, dos sextos y dos novenos", [
                extra[21:23],  # dos tercios (columnas dobles)
                extra[23:25],  # dos tercios (filas dobles)
                extra[25:27],  # dos sextos fila superior
                extra[27:29],  # dos sextos fila inferior
                extra[29:32],  # dos novenos horizontales, mitad izquierda
                extra[32:35],  # dos novenos horizontales, mitad derecha
                extra[35:38],  # dos novenos verticales, mitad superior
                extra[38:41],  # dos novenos verticales, mitad inferior
            ]))

        for i, col in enumerate(columns):
            if i:
                outer.add(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
            col.set_valign(Gtk.Align.START)
            outer.add(col)
        return outer

    def _section(self, title: str, rows: list[list[Zone]]) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        lbl = Gtk.Label(label=title, xalign=0.0)
        lbl.get_style_context().add_class("tiling-title")
        box.add(lbl)
        for row in rows:
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            hbox.set_halign(Gtk.Align.CENTER)
            for zone in row:
                hbox.add(self._cell(zone))
            box.add(hbox)
        return box

    def _cell(self, zone: Zone) -> Gtk.Widget:
        btn = Gtk.Button()
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.set_tooltip_text(zone.label)
        btn.get_style_context().add_class("tiling-cell")

        area = Gtk.DrawingArea()
        area.set_size_request(_CELL_W, _CELL_H)
        area.connect("draw", self._draw_cell, zone)
        btn.add(area)
        btn.connect("clicked", self._on_pick, zone)
        return btn

    def _draw_cell(self, area, cr, zone: Zone):
        w = area.get_allocated_width()
        h = area.get_allocated_height()
        # Marco del monitor.
        cr.set_line_width(1.0)
        cr.set_source_rgba(0.55, 0.58, 0.62, 0.9)
        cr.rectangle(_PAD + 0.5, _PAD + 0.5, w - 2 * _PAD - 1, h - 2 * _PAD - 1)
        cr.stroke()

        iw = w - 2 * _PAD
        ih = h - 2 * _PAD
        zx = _PAD + zone.fx * iw
        zy = _PAD + zone.fy * ih
        zw = zone.fw * iw
        zh = zone.fh * ih
        # Zona resaltada (azul de acento).
        cr.set_source_rgba(0.227, 0.482, 0.835, 0.92)
        cr.rectangle(zx + 1, zy + 1, max(1, zw - 2), max(1, zh - 2))
        cr.fill()
        return False

    def _apply_css(self):
        css = b"""
        #lxqt-tiling-popup { background: transparent; }
        .tiling-root {
            background-color: rgba(34,36,40,0.98);
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.08);
        }
        .tiling-title { color: #c9ccd1; font-size: 11px; font-weight: bold; }
        .tiling-cell { padding: 2px; border-radius: 6px; }
        .tiling-cell:hover { background-color: rgba(255,255,255,0.10); }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        # Permite el fondo redondeado translúcido si hay compositor.
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual is not None:
            self.set_visual(visual)

    # --- posición y eventos ----------------------------------------------

    def _place(self, anchor_rect):
        """Coloca el popup debajo del botón (anchor_rect = x,y,w,h) o, si
        no hay ancla, centrado bajo el borde superior de la ventana."""
        self.realize()
        pw, ph = self.get_size()
        if anchor_rect is not None:
            ax, ay, aw, ah = anchor_rect
            x = ax + aw // 2 - pw // 2
            y = ay + ah + 4
        else:
            fx, fy, fw, _fh = self.target.get_geometry()
            x = fx + fw // 2 - pw // 2
            y = fy + 40
        # No salirse del monitor.
        mon = Gdk.Display.get_default().get_monitor_at_point(x + pw // 2, y)
        if mon:
            g = mon.get_geometry()
            x = max(g.x + 4, min(x, g.x + g.width - pw - 4))
            y = max(g.y + 4, min(y, g.y + g.height - ph - 4))
        self.move(x, y)

    def _on_key(self, _w, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()
        return False

    def _on_pick(self, _btn, zone: Zone):
        x, y, w, h = zone.to_pixels(*self._workarea)
        wm.apply_zone(self.target, x, y, w, h)
        self.destroy()

    def contains_pointer(self, px: int, py: int) -> bool:
        """True si el puntero está sobre el popup (para el modo hover)."""
        win = self.get_window()
        if win is None:
            return False
        ox, oy = win.get_position()
        pw, ph = self.get_size()
        return ox <= px < ox + pw and oy <= py < oy + ph
