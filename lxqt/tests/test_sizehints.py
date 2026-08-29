"""Regresiones para ventanas con WM_NORMAL_HINTS cuantizados."""

import unittest

from lxqt_tiling.sizehints import SizeHints, _snap_down


class SnapDownTests(unittest.TestCase):
    def test_exact_grid_size_is_unchanged(self):
        self.assertEqual(_snap_down(947, 17, 10, 17, None), 947)

    def test_rounds_down_to_previous_grid_size(self):
        self.assertEqual(_snap_down(950, 17, 10, 17, None), 947)

    def test_honours_minimum_when_zone_is_too_small(self):
        self.assertEqual(_snap_down(40, 17, 10, 47, None), 47)

    def test_honours_maximum(self):
        self.assertEqual(_snap_down(1000, 17, 10, 17, 507), 507)

    def test_unit_increment_keeps_requested_size(self):
        self.assertEqual(_snap_down(950, 0, 1, 0, None), 950)


class FitFrameTests(unittest.TestCase):
    def setUp(self):
        # Valores publicados por xfce4-terminal con su fuente predeterminada.
        self.hints = SizeHints(
            base_w=17,
            base_h=27,
            inc_w=10,
            inc_h=19,
            min_w=17,
            min_h=27,
            max_w=None,
            max_h=None,
        )

    def test_quantized_terminal_fits_and_is_centered(self):
        # Regresión de v1.1.2: zona 960×1053, marco xfwm4 5,5,29,5.
        dx, dy, width, height = self.hints.fit_frame(
            960, 1053, (5, 5, 29, 5)
        )

        self.assertEqual((dx, dy, width, height), (1, 2, 957, 1049))
        self.assertLessEqual(width, 960)
        self.assertLessEqual(height, 1053)
        self.assertLessEqual(abs(dx - (960 - width - dx)), 1)
        self.assertLessEqual(abs(dy - (1053 - height - dy)), 1)

    def test_exact_frame_size_has_no_offset(self):
        self.assertEqual(
            self.hints.fit_frame(957, 1049, (5, 5, 29, 5)),
            (0, 0, 957, 1049),
        )


if __name__ == "__main__":
    unittest.main()
