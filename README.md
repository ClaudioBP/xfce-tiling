# xfce-tiling

Menú de zonas de *tiling* estilo **Snap Layouts de Windows 11** para Linux/X11:
al pasar el cursor sobre el botón **maximizar** de una ventana aparece un
popup con miniaturas para redimensionar y mover la ventana a una zona del
monitor. También se abre con el atajo global **`Super+Z`**, que funciona
incluso con apps que no usan el botón del gestor de ventanas (Electron,
VS Code…).

## Dos variantes

Este repositorio mantiene el proyecto en dos subdirectorios independientes,
uno por gestor de ventanas:

| Directorio | Entorno | Detección del botón maximizar |
|---|---|---|
| [`xfce/`](xfce/) | XFCE (xfwm4) | Tema y `button_layout` de xfwm4 (`xfconf-query`) |
| [`lxqt/`](lxqt/) | LXQt / Openbox | `titleLayout` y tema de openbox (`rc.xml` + `themerc`) |

Ambas comparten el mismo núcleo (zonas, popup, atajo global, compensación de
`WM_NORMAL_HINTS` y `_GTK_FRAME_EXTENTS`) y solo difieren en cómo localizan
el botón maximizar dibujado por el gestor de ventanas.

## Requisitos comunes

- Sesión X11 con un gestor EWMH (xfwm4 u openbox).
- Python 3.10+ y las bibliotecas GObject:
  `python3-gi`, `gir1.2-gtk-3.0`, `gir1.2-wnck-3.0`,
  `gir1.2-keybinder-3.0`, `gir1.2-gdkpixbuf-2.0`.

Cada subdirectorio tiene su propio `install.sh`, `uninstall.sh`, `README.md`
y `README.es.md`.

## Licencia

MIT — ver [LICENSE](LICENSE).