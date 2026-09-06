"""Regresiones del modelo geométrico del botón maximizar de openbox.

Verifica el empaquetado del titleLayout (grupo izquierdo y derecho) y la
derivación de tamaños desde el tema y el marco real de la ventana, sin
necesidad de un servidor X.
"""

import os
import tempfile
import unittest

from lxqt_tiling.openbox_button import (
    OpenboxConfig,
    ThemeGeometry,
    maximize_button_rect,
)

# Marco de ejemplo con Clearlooks (padding 3/2, border 1, client padding 0):
# extents (1, top, 1, 1) y barra de título de 26 px -> top = 0 + 1 + 26 + 1.
_EXTENTS = (1, 28, 1, 1)
_FRAME = (100, 80, 900, 600)


def _clearlooks_cfg() -> OpenboxConfig:
    return OpenboxConfig(
        title_layout="NLIMC",
        theme="Clearlooks",
        theme_geometry=ThemeGeometry(
            paddingx=3, paddingy=2, border=1, client_padx=0, client_pady=0
        ),
    )


class TitleHeightTests(unittest.TestCase):
    def test_title_height_from_extents(self):
        cfg = _clearlooks_cfg()
        rect = maximize_button_rect(*_FRAME, _EXTENTS, cfg)
        self.assertIsNotNone(rect)
        # title_height = 28 - 0 - 2*1 = 26; label_height = 26 - 4 = 22;
        # button_size = 20; pitch = 20 + 3 + 1 = 24.
        self.assertEqual(rect[2], 20)
        self.assertEqual(rect[3], 20)


class RightGroupTests(unittest.TestCase):
    def test_nlimc_max_button_is_second_from_right(self):
        # Layout NLIMC: C es el más a la derecha y M está a su izquierda.
        cfg = _clearlooks_cfg()
        x, y, w, h = maximize_button_rect(*_FRAME, _EXTENTS, cfg)
        # title_x_end = 100 + 900 - (1 - 0) = 999; M = 999 - 2*24 = 951.
        self.assertEqual(x, 951)
        # by = 80 + 1 + 2 + 1 = 84.
        self.assertEqual(y, 84)
        self.assertEqual((w, h), (20, 20))

    def test_m_after_label_stays_in_right_group(self):
        # I queda a la izquierda de L; M y C se empaquetan desde la derecha.
        cfg = OpenboxConfig(
            title_layout="ILMC",
            theme="Clearlooks",
            theme_geometry=_clearlooks_cfg().theme_geometry,
        )
        self.assertEqual(
            maximize_button_rect(*_FRAME, _EXTENTS, cfg),
            (951, 84, 20, 20),
        )

    def test_right_group_counts_only_present_buttons(self):
        # Layout NLCIM: el grupo derecho es "CIM" -> M es el más a la derecha.
        cfg = OpenboxConfig(
            title_layout="NLCIM",
            theme="Clearlooks",
            theme_geometry=_clearlooks_cfg().theme_geometry,
        )
        x, _y, _w, _h = maximize_button_rect(*_FRAME, _EXTENTS, cfg)
        self.assertEqual(x, 999 - 24)  # un solo botón a la derecha


class LeftGroupTests(unittest.TestCase):
    def test_m_before_label_is_packed_from_left(self):
        # Layout IMLC: M en el grupo izquierdo, tras I.
        cfg = OpenboxConfig(
            title_layout="IMLC",
            theme="Clearlooks",
            theme_geometry=_clearlooks_cfg().theme_geometry,
        )
        x, _y, w, _h = maximize_button_rect(*_FRAME, _EXTENTS, cfg)
        # title_x = 100 + 1 - 0 = 101; x = 101 + 3 + 1 + 24 = 129.
        self.assertEqual(x, 129)
        self.assertEqual(w, 20)

    def test_icon_before_m_uses_wider_pitch(self):
        cfg = OpenboxConfig(
            title_layout="NMILC",
            theme="Clearlooks",
            theme_geometry=_clearlooks_cfg().theme_geometry,
        )
        rect = maximize_button_rect(*_FRAME, _EXTENTS, cfg)
        # x = 101 + 4 + (24 + 2) = 131.
        self.assertEqual(rect[0], 131)


class NoMaximizeTests(unittest.TestCase):
    def test_layout_without_m_returns_none(self):
        cfg = OpenboxConfig(
            title_layout="NLIC",
            theme="Clearlooks",
            theme_geometry=_clearlooks_cfg().theme_geometry,
        )
        self.assertIsNone(maximize_button_rect(*_FRAME, _EXTENTS, cfg))

    def test_geometry_without_titlebar_returns_none(self):
        cfg = _clearlooks_cfg()
        self.assertIsNone(maximize_button_rect(*_FRAME, (1, 3, 1, 1), cfg))


class ConfigParsingTests(unittest.TestCase):
    def test_loads_layout_and_theme_from_rcxml(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = os.path.join(tmp, "rc.xml")
            with open(rc, "w", encoding="utf-8") as fh:
                fh.write(
                    "<openbox_config>"
                    "<theme><name>Lubuntu Arc</name></theme>"
                    "<titleLayout>LIMC</titleLayout>"
                    "</openbox_config>"
                )
            cfg = OpenboxConfig.load(rc)
        self.assertEqual(cfg.title_layout, "LIMC")
        self.assertEqual(cfg.theme, "Lubuntu Arc")

    def test_parses_theme_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "themerc")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(
                    "padding.width: 4\n"
                    "padding.height: 5\n"
                    "border.width: 2\n"
                    "window.client.padding.width: 1\n"
                    "window.client.padding.height: 0\n"
                    "window.active.title.bg: solid flat\n"
                )
            g = ThemeGeometry.from_themerc(path)
            self.assertEqual(
                (g.paddingx, g.paddingy, g.border, g.client_padx, g.client_pady),
                (4, 5, 2, 1, 0),
            )

    def test_defaults_when_themerc_missing(self):
        g = ThemeGeometry.from_themerc("/no/such/themerc")
        self.assertEqual(
            (g.paddingx, g.paddingy, g.border, g.client_padx, g.client_pady),
            (3, 3, 1, 3, 3),
        )


if __name__ == "__main__":
    unittest.main()