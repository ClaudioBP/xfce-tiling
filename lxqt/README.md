[English](README.md) | [Español](README.es.md)

# lxqt-tiling

Snap Layouts-style tiling zone menu for **LXQt/Openbox**: hovering the
window's **maximize** button shows a thumbnail popup to move and resize the
window into a zone of the monitor. It also opens with the global **`Super+Z`**
hotkey, which works even for apps that don't use openbox's button (Electron,
VS Code…). For Firefox and Chrome/Chromium the hover works through a
configured virtual zone (see "CSD apps").

This is the LXQt/Openbox flavor of the [xfce-tiling](../README.md) project
(XFCE flavor in [`../xfce/`](../xfce/)).

## Zones by monitor resolution

**Up to 1080p** (8 zones): halves and quarters (left/right/top/bottom half,
four quarters).

**Larger than 1080p** (49 zones): the above plus thirds, sixths, ninths and
the double combinations (two-thirds, two-sixths, two horizontal/vertical
ninths). A monitor is "larger than 1080p" when it exceeds 1920×1080.

## Requirements

X11 session with LXQt (openbox as window manager) and these GObject
libraries:

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-wnck-3.0 \
                 gir1.2-keybinder-3.0 gir1.2-gdkpixbuf-2.0
```

## Installation

```bash
./install.sh          # installs into ~/.local (no root) + autostart
lxqt-tiling daemon &  # start now, without logging out
```

It starts automatically at each login (XDG autostart). Remove with
`./uninstall.sh`.

## Usage

- **Hover**: point at the maximize button of a window decorated by openbox
  (Terminal, Thunar, native apps) → the zone menu appears below the button.
  Move onto it and click a zone.
- **`Super+Z` hotkey**: opens the menu for the active window, whether or not
  its button works (the only way with CSD apps). `Esc` or clicking outside
  closes it.

For testing or custom hotkeys: `lxqt-tiling menu`.

## The openbox maximize button

Openbox lays out titlebar buttons according to the `titleLayout` of its
configuration (`~/.config/openbox/lxqt-rc.xml`, `~/.config/openbox/rc.xml`
or `/etc/xdg/openbox/rc.xml`). Letters: `N` window icon, `L` title,
`I` iconify, `M` maximize, `C` close, `S` shade, `D` desktop. Elements
before `L` are packed left, elements after it are packed right; button
width comes from the active theme (`themerc`), and the titlebar height is
read from each window's real `_NET_FRAME_EXTENTS`, so the math works with
any theme and font.

If you change `titleLayout` or the theme in `obconf-qt`, restart the daemon
so it re-reads the configuration.

## CSD apps (Firefox, Chrome…)

Client-side-decorated apps draw their own titlebar and maximize button,
whose position openbox cannot know. For the apps listed in `_CSD_APPS` in
`button_detect.py` (Firefox, Firefox ESR, Chrome, Chromium) a **virtual
rectangle** at the top-right corner is used, so hover works the same. Add
other apps by their window class (`xprop WM_CLASS`).

`_GTK_FRAME_EXTENTS` (the invisible shadow of GTK/CSD apps such as Firefox)
is compensated so the visible part of the window fills the zone exactly.

Apps with **resize increments** in `WM_NORMAL_HINTS` (terminals, Emacs) only
accept client sizes of `base + n × increment`, so the exact zone size is
rounded *down* and the largest accepted size is centered in the zone,
splitting the leftover pixels between both sides without invading
neighbouring zones.

## How it works

| Module | Responsibility |
|--------|----------------|
| `layouts.py` | Definition of the 8/49 zones as fractions of the work area. |
| `wm.py` | libwnck: active/under-pointer window, frame extents (incl. `_GTK_FRAME_EXTENTS`), apply zone, monitor + workarea via Gdk. |
| `openbox_button.py` | Openbox maximize-button geometry model: `titleLayout` from rc.xml, `padding`/`border` from the themerc, button rect derived from the real frame. |
| `button_detect.py` | Hover decision: real openbox button or virtual rectangle for known CSD apps. |
| `sizehints.py` | Xlib via `ctypes`: `WM_NORMAL_HINTS` increments, `_NET_FRAME_EXTENTS` / `_GTK_FRAME_EXTENTS` and the real frame rectangle, read straight from the X server (libwnck's cache is stale right after unmaximize). |
| `popup.py` | Popup window with the zone thumbnails (Cairo) and click logic. |
| `daemon.py` | Pointer polling loop (hover) + global hotkey via Keybinder. |

Exact placement: with `STATIC` gravity, `Wnck.set_geometry` takes the
**outer** frame rectangle, so zones fit edge-to-edge and respect panels
(openbox exposes the work area via `_NET_WORKAREA`, honouring the `_NET_STRUT`
of LXQt panels).

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Changing the hotkey

Default is `<Super>z`. Edit `DEFAULT_HOTKEY` in `daemon.py` (GTK accelerator
syntax, e.g. `<Super><Shift>z`) and restart the daemon
(`pkill -f lxqt_tiling; lxqt-tiling daemon &`).

## Version history

See [CHANGELOG.md](CHANGELOG.md).