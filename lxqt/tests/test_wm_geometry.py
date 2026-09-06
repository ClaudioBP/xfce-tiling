"""Pruebas de integración de la geometría objetivo, sin mover ventanas."""

import unittest
from unittest.mock import patch

from lxqt_tiling import wm
from lxqt_tiling.sizehints import SizeHints


class _Window:
    def get_xid(self):
        return 42


class TargetRectTests(unittest.TestCase):
    def setUp(self):
        self.window = _Window()
        self.terminal_hints = SizeHints(
            base_w=17,
            base_h=27,
            inc_w=10,
            inc_h=19,
            min_w=17,
            min_h=27,
            max_w=None,
            max_h=None,
        )

    @patch("lxqt_tiling.wm.resting_gtk_frame_extents", return_value=(0, 0, 0, 0))
    @patch("lxqt_tiling.wm.sizehints.size_hints")
    def test_quantized_target_is_smaller_and_centered(
        self, mock_size_hints, _mock_gtk_extents
    ):
        mock_size_hints.return_value = self.terminal_hints

        rect = wm._target_rect(
            self.window,
            (100, 50, 960, 1053),
            (5, 5, 29, 5),
        )

        self.assertEqual(rect, (101, 52, 957, 1049))

    @patch("lxqt_tiling.wm.resting_gtk_frame_extents", return_value=(8, 12, 10, 14))
    @patch("lxqt_tiling.wm.sizehints.size_hints", return_value=None)
    def test_unquantized_target_keeps_exact_visible_zone(
        self, _mock_size_hints, _mock_gtk_extents
    ):
        rect = wm._target_rect(
            self.window,
            (100, 50, 960, 1053),
            (0, 0, 0, 0),
        )

        self.assertEqual(rect, (92, 40, 980, 1077))


if __name__ == "__main__":
    unittest.main()
