"""Punto de entrada.

Uso:
    python -m lxqt_tiling            # arranca el demonio (hover + atajo)
    python -m lxqt_tiling daemon     # idem
    python -m lxqt_tiling menu       # muestra el menú una vez (ventana activa)
    python -m lxqt_tiling --version
"""

from __future__ import annotations

import sys

from . import __version__


def _show_menu_once():
    """Muestra el popup para la ventana activa y termina (para atajos
    externos / pruebas). Útil aunque el demonio no esté corriendo."""
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk

    from . import button_detect, wm
    from .popup import TilingPopup

    screen = wm.get_screen()
    target = screen.get_active_window()
    if not wm.is_tileable(target):
        print("[lxqt-tiling] la ventana activa no admite tiling")
        return
    rect = button_detect.maximize_button_rect(target)
    popup = TilingPopup(target, rect, modal=True)
    popup.connect("destroy", Gtk.main_quit)
    popup.present()
    Gtk.main()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else "daemon"

    if cmd in ("--version", "-v"):
        print(f"lxqt-tiling {__version__}")
        return
    if cmd == "menu":
        _show_menu_once()
        return
    if cmd in ("daemon", ""):
        from .daemon import main as daemon_main

        daemon_main()
        return

    print(f"[lxqt-tiling] orden desconocida: {cmd}")
    sys.exit(2)


if __name__ == "__main__":
    main()
