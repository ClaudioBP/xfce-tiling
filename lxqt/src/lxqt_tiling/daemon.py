"""Demonio principal: hover sobre el botón maximizar + atajo global.

(versión openbox/LXQt)

* Hover: sondea la posición del puntero y, cuando queda sobre el botón
  maximizar de una ventana decorada por xfwm4, muestra el popup de zonas.
* Atajo global (por defecto <Super>z): muestra el popup para la ventana
  activa, funcione o no su botón (cubre las apps CSD como Chrome).
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Wnck", "3.0")
gi.require_version("Keybinder", "3.0")
from gi.repository import GLib, Gtk, Keybinder, Wnck  # noqa: E402

from . import button_detect, wm
from .popup import TilingPopup

POLL_MS = 130          # frecuencia de sondeo del puntero
ENTER_TICKS = 2        # ticks sobre el botón antes de abrir (evita falsos)
LEAVE_TICKS = 3        # ticks fuera antes de cerrar (permite ir al popup)
DEFAULT_HOTKEY = "<Super>z"


def _inside(rect, px, py) -> bool:
    x, y, w, h = rect
    return x <= px < x + w and y <= py < y + h


class TilingDaemon:
    def __init__(self, hotkey: str = DEFAULT_HOTKEY):
        self.screen = wm.get_screen()
        self.popup: TilingPopup | None = None
        self.popup_target = None
        self._enter_ticks = 0
        self._leave_ticks = 0
        self.hotkey = hotkey

    # --- ciclo de vida ----------------------------------------------------

    def run(self):
        Keybinder.init()
        if not Keybinder.bind(self.hotkey, self._on_hotkey):
            print(f"[lxqt-tiling] no se pudo registrar el atajo {self.hotkey}")
        else:
            print(f"[lxqt-tiling] atajo global: {self.hotkey}")
        GLib.timeout_add(POLL_MS, self._tick)
        print("[lxqt-tiling] demonio en marcha (hover + atajo)")
        Gtk.main()

    # --- popup ------------------------------------------------------------

    def _close_popup(self):
        # Nullificamos antes de destruir para que el handler de "destroy"
        # (por identidad) no vuelva a limpiar ni recurse.
        popup = self.popup
        self.popup = None
        self.popup_target = None
        if popup is not None:
            popup.destroy()

    def _open_popup(self, target, anchor_rect, modal: bool):
        self._close_popup()
        if not wm.is_tileable(target):
            return
        self.popup = TilingPopup(target, anchor_rect, modal=modal)
        self.popup_target = target
        self.popup.connect("destroy", self._on_popup_destroyed)
        if modal:
            self.popup.present()

    def _on_popup_destroyed(self, widget):
        # Se disparó porque el popup se cerró solo (Escape/clic/focus-out).
        if widget is self.popup:
            self.popup = None
            self.popup_target = None

    def _ignored_xids(self):
        if self.popup is None:
            return ()
        gw = self.popup.get_window()
        try:
            return (gw.get_xid(),) if gw else ()
        except Exception:
            return ()

    # --- atajo global -----------------------------------------------------

    def _on_hotkey(self, _keystring):
        self.screen.force_update()
        target = self.screen.get_active_window()
        if not wm.is_tileable(target):
            return
        rect = button_detect.maximize_button_rect(target)
        self._open_popup(target, rect, modal=True)

    # --- sondeo del hover -------------------------------------------------

    def _tick(self) -> bool:
        px, py = wm.pointer_position()

        # 1) Si hay un popup modal (abierto por atajo), no interferir.
        if self.popup is not None and self.popup.get_accept_focus():
            return True

        # 2) ¿Puntero sobre el popup actual?
        over_popup = self.popup is not None and self.popup.contains_pointer(px, py)

        # 3) Ventana bajo el puntero y su botón maximizar.
        target = wm.window_under_pointer(self.screen, px, py)
        # Evitar tratar el propio popup como objetivo.
        if target is not None and self.popup is not None:
            try:
                if target.get_xid() in self._ignored_xids():
                    target = None
            except Exception:
                pass

        btn = button_detect.maximize_button_rect(target) if target else None
        over_button = btn is not None and _inside(btn, px, py)

        if over_button:
            self._leave_ticks = 0
            if self.popup is None or self.popup_target is not target:
                self._enter_ticks += 1
                if self._enter_ticks >= ENTER_TICKS:
                    self._enter_ticks = 0
                    self._open_popup(target, btn, modal=False)
        elif over_popup:
            self._leave_ticks = 0
            self._enter_ticks = 0
        else:
            self._enter_ticks = 0
            if self.popup is not None:
                self._leave_ticks += 1
                if self._leave_ticks >= LEAVE_TICKS:
                    self._leave_ticks = 0
                    self._close_popup()

        return True


def main(argv=None):
    daemon = TilingDaemon()
    daemon.run()
