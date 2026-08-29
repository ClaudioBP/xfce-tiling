"""Definición de las zonas de tiling.

Cada zona se describe con una fracción del área de trabajo del monitor
(fx, fy, fw, fh) en el rango 0..1, más una etiqueta en español.

Regla de resolución (según la especificación del usuario):

  * Monitor "hasta 1080p"  -> solo mitades y cuartos (8 zonas).
  * Monitor "mayor a 1080p" -> además tercios, sextos y novenos,
    incluidas las combinaciones dobles (41 zonas extra).

Se considera "mayor a 1080p" cualquier monitor cuya geometría supere
1920x1080 (por ancho o por alto). Así un panel 1920x1080 usa el juego
base y uno de 1440p / 4K usa el juego extendido.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Zone:
    key: str            # identificador estable
    label: str          # texto mostrado / tooltip
    group: str          # "base" | "extra"
    fx: float           # fracción de origen X (0..1)
    fy: float           # fracción de origen Y (0..1)
    fw: float           # fracción de ancho (0..1)
    fh: float           # fracción de alto (0..1)

    def to_pixels(self, wx: int, wy: int, ww: int, wh: int) -> tuple[int, int, int, int]:
        """Convierte la fracción al rectángulo en píxeles dentro del área
        de trabajo (wx, wy, ww, wh).

        Se redondean los *bordes* (no ancho/alto por separado) para que
        zonas adyacentes queden perfectamente pegadas, sin huecos ni
        solapes de 1 px.
        """
        x0 = wx + round(self.fx * ww)
        y0 = wy + round(self.fy * wh)
        x1 = wx + round((self.fx + self.fw) * ww)
        y1 = wy + round((self.fy + self.fh) * wh)
        return x0, y0, x1 - x0, y1 - y0


# --- Juego base: mitades y cuartos (1.1 .. 1.8) --------------------------

_BASE: list[Zone] = [
    Zone("left_half",     "Mitad izquierda",          "base", 0,     0,   1 / 2, 1),
    Zone("right_half",    "Mitad derecha",            "base", 1 / 2, 0,   1 / 2, 1),
    Zone("top_half",      "Mitad superior",           "base", 0,     0,   1,     1 / 2),
    Zone("bottom_half",   "Mitad inferior",           "base", 0,     1 / 2, 1,   1 / 2),
    Zone("tl_quarter",    "Cuarto superior izquierdo", "base", 0,    0,   1 / 2, 1 / 2),
    Zone("tr_quarter",    "Cuarto superior derecho",   "base", 1 / 2, 0,  1 / 2, 1 / 2),
    Zone("bl_quarter",    "Cuarto inferior izquierdo", "base", 0,   1 / 2, 1 / 2, 1 / 2),
    Zone("br_quarter",    "Cuarto inferior derecho",   "base", 1 / 2, 1 / 2, 1 / 2, 1 / 2),
]

# --- Juego extra: tercios, sextos y novenos (2.1 .. 2.41) ----------------

_EXTRA: list[Zone] = [
    # Tercios verticales (columnas)
    Zone("left_third",    "Tercio izquierdo",          "extra", 0,     0,     1 / 3, 1),
    Zone("mid_third_v",   "Tercio medio vertical",     "extra", 1 / 3, 0,     1 / 3, 1),
    Zone("right_third",   "Tercio derecho",            "extra", 2 / 3, 0,     1 / 3, 1),
    # Tercios horizontales (filas)
    Zone("top_third",     "Tercio superior",           "extra", 0,     0,     1,     1 / 3),
    Zone("mid_third_h",   "Tercio medio horizontal",   "extra", 0,     1 / 3, 1,     1 / 3),
    Zone("bottom_third",  "Tercio medio inferior",     "extra", 0,     2 / 3, 1,     1 / 3),
    # Sextos (rejilla 3x2)
    Zone("sixth_tl",      "Sexto izquierdo superior",  "extra", 0,     0,     1 / 3, 1 / 2),
    Zone("sixth_tc",      "Sexto central superior",    "extra", 1 / 3, 0,     1 / 3, 1 / 2),
    Zone("sixth_tr",      "Sexto derecho superior",    "extra", 2 / 3, 0,     1 / 3, 1 / 2),
    Zone("sixth_bl",      "Sexto izquierdo inferior",  "extra", 0,     1 / 2, 1 / 3, 1 / 2),
    Zone("sixth_bc",      "Sexto central inferior",    "extra", 1 / 3, 1 / 2, 1 / 3, 1 / 2),
    Zone("sixth_br",      "Sexto derecho inferior",    "extra", 2 / 3, 1 / 2, 1 / 3, 1 / 2),
    # Novenos (rejilla 3x3)
    Zone("ninth_tl",      "Noveno superior izquierdo", "extra", 0,     0,     1 / 3, 1 / 3),
    Zone("ninth_tc",      "Noveno superior central",   "extra", 1 / 3, 0,     1 / 3, 1 / 3),
    Zone("ninth_tr",      "Noveno superior derecho",   "extra", 2 / 3, 0,     1 / 3, 1 / 3),
    Zone("ninth_ml",      "Noveno izquierdo central",  "extra", 0,     1 / 3, 1 / 3, 1 / 3),
    Zone("ninth_c",       "Noveno central",            "extra", 1 / 3, 1 / 3, 1 / 3, 1 / 3),
    Zone("ninth_mr",      "Noveno derecho central",    "extra", 2 / 3, 1 / 3, 1 / 3, 1 / 3),
    Zone("ninth_bl",      "Noveno izquierdo inferior", "extra", 0,     2 / 3, 1 / 3, 1 / 3),
    Zone("ninth_bc",      "Noveno central inferior",   "extra", 1 / 3, 2 / 3, 1 / 3, 1 / 3),
    Zone("ninth_br",      "Noveno derecho inferior",   "extra", 2 / 3, 2 / 3, 1 / 3, 1 / 3),
    # Dos tercios: pares de columnas completas (izquierda+centro, centro+derecha)
    Zone("two_third_l",   "Dos tercios izquierdo y central", "extra", 0,     0,     2 / 3, 1),
    Zone("two_third_r",   "Dos tercios central y derecho",   "extra", 1 / 3, 0,     2 / 3, 1),
    # Dos tercios: pares de filas completas (arriba+centro, centro+abajo)
    Zone("two_third_t",   "Dos tercios superior y central",  "extra", 0,     0,     1, 2 / 3),
    Zone("two_third_b",   "Dos tercios central e inferior",  "extra", 0,     1 / 3, 1, 2 / 3),
    # Dos sextos: pares horizontales dentro de la rejilla 3x2
    Zone("two_sixth_tl",  "Dos sextos izquierdo superior", "extra", 0,     0,     2 / 3, 1 / 2),
    Zone("two_sixth_tr",  "Dos sextos derecho superior",   "extra", 1 / 3, 0,     2 / 3, 1 / 2),
    Zone("two_sixth_bl",  "Dos sextos izquierdo inferior", "extra", 0,     1 / 2, 2 / 3, 1 / 2),
    Zone("two_sixth_br",  "Dos sextos derecho inferior",   "extra", 1 / 3, 1 / 2, 2 / 3, 1 / 2),
    # Dos novenos: pares horizontales dentro de la rejilla 3x3
    Zone("two_ninth_h_tl", "Dos novenos izquierdo y central superior", "extra", 0,     0,     2 / 3, 1 / 3),
    Zone("two_ninth_h_tr", "Dos novenos central y derecho superior",   "extra", 1 / 3, 0,     2 / 3, 1 / 3),
    Zone("two_ninth_h_ml", "Dos novenos izquierdo y central central",  "extra", 0,     1 / 3, 2 / 3, 1 / 3),
    Zone("two_ninth_h_mr", "Dos novenos central y derecho central",    "extra", 1 / 3, 1 / 3, 2 / 3, 1 / 3),
    Zone("two_ninth_h_bl", "Dos novenos izquierdo y central inferior", "extra", 0,     2 / 3, 2 / 3, 1 / 3),
    Zone("two_ninth_h_br", "Dos novenos central y derecho inferior",   "extra", 1 / 3, 2 / 3, 2 / 3, 1 / 3),
    # Dos novenos: pares verticales dentro de la rejilla 3x3
    Zone("two_ninth_v_tl", "Dos novenos superior y central izquierdo", "extra", 0,     0,     1 / 3, 2 / 3),
    Zone("two_ninth_v_tc", "Dos novenos superior y central central",   "extra", 1 / 3, 0,     1 / 3, 2 / 3),
    Zone("two_ninth_v_tr", "Dos novenos superior y central derecho",   "extra", 2 / 3, 0,     1 / 3, 2 / 3),
    Zone("two_ninth_v_bl", "Dos novenos central e inferior izquierdo", "extra", 0,     1 / 3, 1 / 3, 2 / 3),
    Zone("two_ninth_v_bc", "Dos novenos central e inferior central",   "extra", 1 / 3, 1 / 3, 1 / 3, 2 / 3),
    Zone("two_ninth_v_br", "Dos novenos central e inferior derecho",   "extra", 2 / 3, 1 / 3, 1 / 3, 2 / 3),
]


def is_large_monitor(width: int, height: int) -> bool:
    """True si el monitor es "mayor a 1080p" (juego extendido)."""
    return width > 1920 or height > 1080


def zones_for_monitor(width: int, height: int) -> list[Zone]:
    """Lista de zonas aplicables según la resolución del monitor."""
    if is_large_monitor(width, height):
        return _BASE + _EXTRA
    return list(_BASE)
