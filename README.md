[English](README.md) | [Español](README.es.md)

# xfce-tiling

Tiling zone menu for XFCE in the style of **Windows 11 Snap Layouts**:
hovering the cursor over a window's **maximize** button pops up a small
window with thumbnails to resize and move the window into a monitor
zone. It can also be opened with a **global hotkey (`Super+Z`)**, which
works even for apps that don't use the xfwm4 button (Electron,
VS Code…). For Firefox and Chrome/Chromium, hover works through a
configured virtual zone (see "CSD apps").

## Zones by monitor resolution

The zone set is chosen per monitor (the one containing the window):

**Monitors up to 1080p** (8 zones): halves and quarters
- Left / right / top / bottom half
- Top-left / top-right / bottom-left / bottom-right quarter

**Monitors above 1080p** (49 zones): all of the above **+** thirds,
sixths and ninths, including double combinations
- Left / middle vertical / right third
- Top / middle horizontal / bottom third
- Sixths (3×2 grid): top and bottom × left/center/right
- Ninths (3×3 grid): top left/center/right, middle left/center/right,
  bottom left/center/right
- Two thirds in columns (2/3 × 1): left+center / center+right
- Two thirds in rows (1 × 2/3): top+center / center+bottom
- Two sixths (2/3 × 1/2 blocks): left/right × top/bottom
- Two horizontal ninths (2/3 × 1/3): left+center / center+right × row
- Two vertical ninths (1/3 × 2/3): top+center / center+bottom × column

The popup is laid out in side-by-side columns to stay compact.

"Above 1080p" means any monitor exceeding 1920×1080.

## Requirements

X11 environment with XFCE (xfwm4) and these GObject libraries:

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-wnck-3.0 \
                 gir1.2-keybinder-3.0 gir1.2-gdkpixbuf-2.0
```

## Installation

```bash
./install.sh          # installs into ~/.local (no root) + autostart
xfce-tiling daemon &  # start now, without restarting the session
```

It will start automatically on each login. To remove it: `./uninstall.sh`.

## Usage

- **Hover**: move the cursor over the maximize button of a window
  decorated by xfwm4 (Terminal, Thunar, native apps) → the menu appears
  below the button. Move onto the menu and click a zone.
- **`Super+Z` hotkey**: opens the menu for the active window, whether or
  not its button works (the only way for most CSD apps). `Esc` or a
  click outside closes it.

Also, for testing or to bind your own shortcut:

```bash
xfce-tiling menu      # show the menu once for the active window
```

## CSD apps (Firefox, Chrome…)

Client-side decorated (CSD) applications draw their own title bar and
maximize button, whose position xfwm4 does not know. For the apps in the
`_CSD_APPS` table in `button_detect.py` (Firefox, Firefox ESR, Chrome,
Chromium) a **virtual rectangle** is defined at the top-right corner
where the app draws its button: hover works just like on decorated
windows. To add another app, add its window class (`xprop WM_CLASS`) to
that table.

`_GTK_FRAME_EXTENTS` (the invisible shadow of GTK/CSD apps such as
Firefox) is also compensated so the visible part of the window fills the
zone exactly, with no gaps.

For all other CSD apps (Electron, VS Code, Spotify…) use the global
`Super+Z` hotkey, which covers everything.

## How it works

| Module | Responsibility |
|--------|----------------|
| `layouts.py` | Definition of the 8 / 49 zones as fractions of the work area. |
| `wm.py` | libwnck: active window / window under cursor, frame extents (incl. `_GTK_FRAME_EXTENTS`), apply zone, monitor + workarea via Gdk. |
| `button_detect.py` | Computes the maximize button rectangle by reading xfwm4's `button_layout` and the theme's button widths; virtual zones for known CSD apps. |
| `popup.py` | Popup window with the thumbnails of each zone (Cairo) and the click logic. |
| `daemon.py` | Pointer polling loop (hover) + global hotkey via Keybinder. |

Exact placement: with `STATIC` gravity, `Wnck.set_geometry` receives the
**outer** frame rectangle, so zones fit together with no gaps while
respecting XFCE panels.

## Changing the hotkey

The default is `<Super>z`. For another one, edit `DEFAULT_HOTKEY` in
`daemon.py` (GTK accelerator syntax, e.g. `<Super><Shift>z`) and restart
the daemon (`pkill -f xfce_tiling; xfce-tiling daemon &`).
