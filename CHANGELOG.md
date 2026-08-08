# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Windows whose sizes are constrained to `WM_NORMAL_HINTS` increments now use
  the largest accepted size that fits inside the selected zone and are centered
  in it. This replaces the previous round-up behaviour, so terminals, Emacs and
  similar applications no longer overlap neighbouring zones.

## [1.1.2] - 2026-08-07

### Fixed

- Terminals left a strip of desktop showing inside their zone, most visibly
  along the bottom edge. `xfce4-terminal` publishes resize increments in
  `WM_NORMAL_HINTS` (10×19 px — the font cell — with a 17×27 base), so it only
  accepts client sizes of `base + n × increment`. Asked for a zone's exact
  size, GTK rounds *down* and the window ends up short by up to 9 px on the
  right and 18 px at the bottom. xfwm4's own `Super+KP_Left` tiling leaves the
  very same gap.

  The requested size is now rounded *up* to the next size the window accepts,
  so it covers the zone completely; the leftover pixels overlap the
  neighbouring zone to the right and below. This is driven by the window's own
  hints, so it also covers xterm, urxvt and Emacs, and windows without
  increments are placed exactly as before.

  Removing the increments from the window's `WM_NORMAL_HINTS` (which xfwm4 does
  honour) is not a workaround: GTK keeps its own copy of the hints and resizes
  the window back to a cell multiple about 10 ms later.

- Tiling a **maximized** window placed it wrong: a half-screen zone of
  960×1053 came out as 970×1063 at `-5,0`, off by the frame extents in both
  size and position. The first move-resize after an unmaximize is converted by
  xfwm4 using the *maximized* decoration (`0,0,24,0` instead of `5,5,29,5`),
  and waiting does not help — the stale accounting persists until a configure
  cycle completes. The geometry is now re-checked shortly afterwards and
  re-applied if the WM did not honour it.

- Tiling a maximized CSD app (Firefox, Chrome…) ignored its invisible shadow,
  leaving the visible window inset by the shadow margins. GTK collapses
  `_GTK_FRAME_EXTENTS` to zero while maximized and animates it back over
  ~220 ms, so the value read at tiling time was zero (and got cached that way
  forever). The largest value seen per window is now kept, and the deferred
  re-check runs late enough for the animation to have finished.

### Changed

- `_GTK_FRAME_EXTENTS` is read through Xlib (`ctypes`) instead of spawning
  `xprop`, removing a subprocess from the hover polling loop.

## [1.1.1] - 2026-08-07

### Fixed

- Autostart never launched the daemon on login. `install.sh` copied
  `data/xfce-tiling.desktop` verbatim, leaving a bare `Exec=xfce-tiling daemon`.
  The XDG autostart generator does not inherit the shell `PATH`, so `~/.local/bin`
  is not visible to it and the entry was discarded outright:

  ```
  Exec binary 'xfce-tiling' does not exist: No such file or directory
  xfce-tiling.desktop: not generating unit, executable specified in Exec= does not exist.
  ```

  The installed `.desktop` is now generated with the absolute path to the launcher,
  honouring custom `PREFIX` values. `data/xfce-tiling.desktop` stays a template, so
  no `$HOME` is hardcoded in the repository.

## [1.1.0] - 2026-07-22

### Added

- Four two-thirds zones, for 49 zones total on monitors above 1080p:
  - `two_third_l` / `two_third_r` — left+center / center+right columns (2/3 × 1)
  - `two_third_t` / `two_third_b` — top+center / center+bottom rows (1 × 2/3)

### Changed

- The combos column in the popup now leads with the two-thirds rows and is titled
  "Dos tercios, dos sextos y dos novenos".
- Zone edges are computed by rounding borders, so two-thirds zones align exactly
  with the single thirds.

## [1.0.0] - 2026-07-17

Initial release: a Snap Layouts-style tiling zone menu for XFCE.

### Added

- 8 base zones (halves and quarters) on monitors up to 1080p.
- 45 zones on larger monitors: thirds, sixths, ninths and double blocks
  (two sixths, two horizontal/vertical ninths).
- Two ways to open the zone menu: hovering the xfwm4 maximize button, and the
  global `Super+Z` hotkey.
- Virtual hover zones for client-side-decorated apps (Firefox, Chrome, Chromium)
  and `_GTK_FRAME_EXTENTS` compensation.
- Root-less installer and uninstaller targeting `~/.local`.

[Unreleased]: https://github.com/ClaudioBP/xfce-tiling/compare/v1.1.2...HEAD
[1.1.2]: https://github.com/ClaudioBP/xfce-tiling/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/ClaudioBP/xfce-tiling/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/ClaudioBP/xfce-tiling/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/ClaudioBP/xfce-tiling/releases/tag/v1.0.0
