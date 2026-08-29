[English](README.md) | [Español](README.es.md)

# lxqt-tiling

Menú de zonas de *tiling* para LXQt/Openbox al estilo de los **Snap Layouts
de Windows 11**: al pasar el cursor sobre el botón **maximizar** de una
ventana aparece una ventanita con miniaturas para redimensionar y mover
la ventana a una zona del monitor. También se abre con un **atajo global
(`Super+Z`)**, que funciona incluso con apps que no usan el botón de
openbox (Electron, VS Code…). Para Firefox y Chrome/Chromium el hover
funciona mediante una zona virtual configurada (ver «Apps CSD»).

Es la variante para **LXQt/Openbox** del proyecto [xfce-tiling](../README.md)
(variante XFCE en [`../xfce/`](../xfce/)).

## Zonas según la resolución del monitor

El juego de zonas se decide por el monitor donde está la ventana:

**Monitor de hasta 1080p** (8 zonas): mitades y cuartos
- Mitad izquierda / derecha / superior / inferior
- Cuarto superior-izq / superior-der / inferior-izq / inferior-der

**Monitor mayor a 1080p** (49 zonas): lo anterior **+** tercios, sextos
y novenos, incluidas las combinaciones dobles
- Tercio izquierdo / medio vertical / derecho
- Tercio superior / medio horizontal / medio inferior
- Sextos (rejilla 3×2): superior e inferior × izq/central/der
- Novenos (rejilla 3×3): superior izq/central/der, izq-central/central/der-central,
  inferior izq/central/der
- Dos tercios en columnas (2/3 × 1): izquierda+centro / centro+derecha
- Dos tercios en filas (1 × 2/3): arriba+centro / centro+abajo
- Dos sextos (bloques de 2/3 × 1/2): izquierdo/derecho × superior/inferior
- Dos novenos horizontales (2/3 × 1/3): izq+central / central+der × fila
- Dos novenos verticales (1/3 × 2/3): sup+central / central+inf × columna

El popup se organiza en columnas lado a lado para mantenerse compacto.

Se considera «mayor a 1080p» cualquier monitor que supere 1920×1080.

## Requisitos

Entorno X11 con LXQt (gestor de ventanas openbox) y estas bibliotecas
GObject:

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-wnck-3.0 \
                 gir1.2-keybinder-3.0 gir1.2-gdkpixbuf-2.0
```

## Instalación

```bash
./install.sh          # instala en ~/.local (sin root) + autostart
lxqt-tiling daemon &  # arrancar ya, sin reiniciar la sesión
```

Se iniciará solo en cada inicio de sesión (autostart XDG de LXQt). Para
quitarlo: `./uninstall.sh`.

## Uso

- **Hover**: pasa el cursor por encima del botón maximizar de una ventana
  decorada por openbox (Terminal, Thunar, apps nativas) → aparece el menú
  debajo del botón. Muévete al menú y haz clic en la zona.
- **Atajo `Super+Z`**: abre el menú para la ventana activa, sirva o no su
  botón (única forma con apps CSD). `Esc` o clic fuera lo cierra.

También, para pruebas o para enlazar tu propio atajo:

```bash
lxqt-tiling menu      # muestra el menú una vez para la ventana activa
```

## El botón maximizar de openbox

Openbox dibuja los botones de la barra de título según el `titleLayout`
de su configuración (`~/.config/openbox/lxqt-rc.xml`,
`~/.config/openbox/rc.xml` o `/etc/xdg/openbox/rc.xml`). Letras:
`N` icono, `L` título, `I` minimizar, `M` maximizar, `C` cerrar, `S`
sombreado, `D` escritorio. Los elementos antes de `L` van a la izquierda
y los de después a la derecha; el ancho de botón sale del tema activo
(`themerc`), y la altura de la barra se lee del `_NET_FRAME_EXTENTS` real
de cada ventana, así que el cálculo funciona con cualquier tema y fuente.

Si cambias el `titleLayout` o el tema en `obconf-qt`, reinicia el demonio
para que relea la configuración.

## Apps CSD (Firefox, Chrome…)

Las aplicaciones con decoración de cliente (CSD) dibujan su propia barra
y su botón de maximizar, cuya posición openbox no conoce. Para las apps de
la tabla `_CSD_APPS` de `button_detect.py` (Firefox, Firefox ESR,
Chrome, Chromium) se define un **rectángulo virtual** en la esquina
superior derecha donde la app pinta su botón: el hover funciona igual
que en ventanas decoradas. Para añadir otra app, agrega su clase de
ventana (`xprop WM_CLASS`) a esa tabla.

Además se compensa `_GTK_FRAME_EXTENTS` (la sombra invisible de las
apps GTK/CSD como Firefox) para que la parte visible de la ventana llene
la zona exacta, sin huecos.

Las apps que declaran **incrementos de redimensión** en `WM_NORMAL_HINTS`
—terminales (xfce4-terminal, xterm, urxvt), Emacs— solo aceptan tamaños de
cliente de `base + n × incremento` píxeles, así que el tamaño exacto de la
zona se redondea *hacia abajo* y queda una franja de escritorio a la vista
dentro de la zona (hasta 9 px a la derecha y 18 abajo con la fuente por
defecto de xfce4-terminal). Se pide el mayor tamaño válido que entre en la
zona y la ventana se centra en ella, de modo que los pocos píxeles sobrantes
se reparten entre ambos lados sin invadir las zonas vecinas.

Para el resto de apps CSD (Electron, VS Code, Spotify…) usa el atajo
global `Super+Z`, que cubre todas.

## Cómo funciona

| Módulo | Responsabilidad |
|--------|-----------------|
| `layouts.py` | Definición de las 8 / 49 zonas como fracciones del área de trabajo. |
| `wm.py` | libwnck: ventana activa/bajo el cursor, extents del marco (incl. `_GTK_FRAME_EXTENTS`), aplicar zona, monitor + workarea por Gdk. |
| `openbox_button.py` | Modelo geométrico del botón maximizar de openbox: `titleLayout` del rc.xml, `padding`/`border` del themerc y rectángulo del botón derivado del marco real. |
| `button_detect.py` | Decisión hover: botón real de openbox o rectángulo virtual para apps CSD conocidas. |
| `sizehints.py` | Xlib con `ctypes`: incrementos de `WM_NORMAL_HINTS`, `_NET_FRAME_EXTENTS` / `_GTK_FRAME_EXTENTS` y el rectángulo real del marco, leídos directamente del servidor X (la caché de libwnck va obsoleta justo tras desmaximizar). |
| `popup.py` | Ventana emergente con las miniaturas de cada zona (Cairo) y la lógica de clic. |
| `daemon.py` | Bucle de sondeo del puntero (hover) + atajo global con Keybinder. |

Colocación exacta: con gravedad `STATIC`, `Wnck.set_geometry` recibe el
rectángulo **exterior** del marco, de modo que las zonas quedan pegadas
sin huecos y respetando los paneles (openbox expone el área de trabajo
vía `_NET_WORKAREA`, que respeta los `_NET_STRUT` de los paneles de LXQt).

## Pruebas

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Cambiar el atajo

Por defecto es `<Super>z`. Para otro, edita `DEFAULT_HOTKEY` en
`daemon.py` (sintaxis de acelerador GTK, p. ej. `<Super><Shift>z`) y
reinicia el demonio (`pkill -f lxqt_tiling; lxqt-tiling daemon &`).

## Historial de versiones

Ver [CHANGELOG.md](CHANGELOG.md).