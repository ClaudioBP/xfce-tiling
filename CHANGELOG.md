# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/ClaudioBP/xfce-tiling/compare/v1.1.1...HEAD
[1.1.1]: https://github.com/ClaudioBP/xfce-tiling/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/ClaudioBP/xfce-tiling/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/ClaudioBP/xfce-tiling/releases/tag/v1.0.0
