"""Cálculo de la posición del botón "maximizar" de openbox.

Openbox dibuja los botones de la barra de título como ventanas X hijas de la
ventana de título, cuyo layout define el `titleLayout` del `rc.xml`. Este
módulo replica el modelo geométrico de openbox (frame.c, `layout_title`)
leyendo la configuración y el tema, sin depender de binarios externos.

Modelo de openbox (3.6.x):

  * El `titleLayout` (p. ej. "NLIMC") es una secuencia de letras: N=icono de
    ventana, L=título, I=minimizar, M=maximizar, C=cerrar, S=sombreado,
    D=escritorio. Los elementos anteriores a "L" se empaquetan pegados al
    borde izquierdo de la barra y los posteriores a la derecha.
  * El ancho de cada botón es `button_size = label_height - 2`, y el paso
    entre botones es `button_size + padding.width + 1`.
  * `label_height = title_height - 2 * padding.height`; la altura de la
    barra `title_height` se deriva del `_NET_FRAME_EXTENTS` real de la
    ventana, de modo que no hace falta conocer la fuente del tema.
  * El tema (themerc) aporta `padding.width`, `padding.height`,
    `border.width` y `window.client.padding.*`, con los mismos valores por
    defecto que usa openbox si faltan.

Solo es posible en ventanas con decoración de servidor. En ventanas CSD el
botón lo pinta la propia app y no se puede detectar: devolvemos None y el
disparador por hover no actúa (queda el atajo global).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from xml.etree import ElementTree

# Orden de búsqueda de la configuración de openbox (LXQt usa lxqt-rc.xml).
_CONFIG_CANDIDATES = [
    os.path.expanduser("~/.config/openbox/lxqt-rc.xml"),
    os.path.expanduser("~/.config/openbox/rc.xml"),
    "/etc/xdg/openbox/rc.xml",
]

_THEME_SEARCH_DIRS = [
    os.path.expanduser("~/.themes"),
    os.path.expanduser("~/.local/share/themes"),
    "/usr/share/themes",
]


@dataclass
class ThemeGeometry:
    """Valores del themerc que determinan el empaquetado de los botones."""

    paddingx: int = 3
    paddingy: int = 3
    border: int = 1
    client_padx: int = 3
    client_pady: int = 3

    @classmethod
    def from_themerc(cls, themerc_path: str | None) -> "ThemeGeometry":
        g = cls()
        if not themerc_path or not os.path.isfile(themerc_path):
            return g
        try:
            with open(themerc_path, encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or ":" not in line:
                        continue
                    key, _, value = line.partition(":")
                    key = key.strip()
                    value = re.sub(r"\s+.*", "", value.strip())
                    if not value.isdigit():
                        continue
                    n = int(value)
                    if key == "padding.width":
                        g.paddingx = n
                    elif key == "padding.height":
                        g.paddingy = n
                    elif key == "border.width":
                        g.border = n
                    elif key == "window.client.padding.width":
                        g.client_padx = n
                    elif key == "window.client.padding.height":
                        g.client_pady = n
        except Exception:
            pass
        return g


@dataclass(frozen=True)
class OpenboxConfig:
    """Configuración leída del rc.xml de openbox."""

    title_layout: str = "NLIMC"
    theme: str = "Default"
    theme_geometry: ThemeGeometry = field(default_factory=ThemeGeometry)

    @classmethod
    def load(cls, config_path: str | None = None) -> "OpenboxConfig":
        path = config_path or _find_config()
        layout = "NLIMC"
        theme = "Default"
        if path and os.path.isfile(path):
            try:
                root = ElementTree.parse(path).getroot()
                node = root.find("titleLayout")
                if node is not None and (node.text or "").strip():
                    layout = node.text.strip()
                theme_node = root.find("theme")
                if theme_node is not None:
                    name_node = theme_node.find("name")
                    if name_node is not None and (name_node.text or "").strip():
                        theme = name_node.text.strip()
            except ElementTree.ParseError:
                pass
        geom = ThemeGeometry.from_themerc(_find_theme_dir(theme))
        return cls(layout, theme, geom)


def _find_config() -> str | None:
    for path in _CONFIG_CANDIDATES:
        if os.path.isfile(path):
            return path
    return None


def _find_theme_dir(theme: str) -> str | None:
    if theme.startswith("/"):
        d = os.path.join(theme, "openbox-3")
        return d if os.path.isdir(d) else None
    for base in _THEME_SEARCH_DIRS:
        d = os.path.join(base, theme, "openbox-3")
        if os.path.isdir(d):
            return d
    return None


def _button_size(title_height: int, geom: ThemeGeometry) -> int:
    """Ancho/alto cuadrado de los botones (label_height - 2)."""
    label_height = title_height - 2 * geom.paddingy
    return max(label_height - 2, 1)


def _titlebar_height(top_extent: int, geom: ThemeGeometry) -> int:
    """Altura de la barra de título derivada del marco real de la ventana.

    ``_NET_FRAME_EXTENTS`` (superior) = client_pad + border + title_height
    + border en una ventana no maximizada verticalmente.
    """
    return top_extent - geom.client_pady - 2 * geom.border


def maximize_button_rect(
    frame_x: int,
    frame_y: int,
    frame_w: int,
    frame_h: int,
    extents: tuple[int, int, int, int],
    cfg: OpenboxConfig,
) -> tuple[int, int, int, int] | None:
    """Rectángulo del botón maximizar en coordenadas de pantalla.

    ``extents`` = (left, top, right, bottom) del `_NET_FRAME_EXTENTS`.
    Devuelve None si el layout no muestra el botón maximizar.
    """
    left, top, right, _bottom = extents
    geom = cfg.theme_geometry
    title_height = _titlebar_height(top, geom)
    if title_height <= 2 * geom.paddingy + 2:
        return None
    bsize = _button_size(title_height, geom)
    pitch = bsize + geom.paddingx + 1

    # La ventana de título empieza tras el borde izquierdo del marco.
    title_x = frame_x + left - geom.client_padx
    # ...y termina antes del borde derecho.
    title_x_end = frame_x + frame_w - (right - geom.client_padx)

    layout = cfg.title_layout
    letters = [c for c in layout if c in "NLDIMSMC"]
    try:
        m_index = letters.index("M")
    except ValueError:
        return None
    l_index = letters.index("L") if "L" in letters else len(letters)

    if m_index < l_index:
        # Grupo izquierdo: pegados al borde, en orden, con el icono (N)
        # un poco más ancho (pitch + 2 en frame.c).
        x = title_x + geom.paddingx + 1
        for letter in letters[:m_index]:
            x += (pitch + 2) if letter == "N" else pitch
        bx = x
    else:
        # Grupo derecho: desde el borde derecho hacia la izquierda.
        after = letters[l_index + 1:]
        rightmost = after[::-1]
        k = rightmost.index("M")  # 0 = el más a la derecha
        bx = title_x_end - (k + 1) * pitch

    by = frame_y + geom.border + geom.paddingy + 1
    return int(bx), int(by), int(bsize), int(bsize)