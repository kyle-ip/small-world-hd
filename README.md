# Small World 2 — HD Pack

[![Release](https://img.shields.io/github/v/release/kyle-ip/small-world-hd?label=release)](https://github.com/kyle-ip/small-world-hd/releases/latest)
[![Platform](https://img.shields.io/badge/platform-Windows-0078D4)](https://github.com/kyle-ip/small-world-hd/releases)
[![Status](https://img.shields.io/badge/status-unofficial-orange)](#disclaimer)

Unofficial, reversible **HD texture / polish overlay** for the Steam version of *Small World 2*.

A single Windows EXE embeds the full payload. Enable backs up stock files, overlays remastered assets, and can restore everything later. Works alongside the [Simplified Chinese pack](https://github.com/kyle-ip/small-world-zh-cn).

> **Not affiliated with** [Days of Wonder](https://www.days-of-wonder.com/), Asmodee, or Valve. Personal / learning use only.

---

## Features

- Same-size clarity pass on `common-hd` and `16-9-hd` (region masks, highlights, and cursors left untouched)
- Slightly tighter blur / dilation shaders
- Cleaner Chinese UI plates and expansion card titles (when the Chinese pack is installed)
- OFL [Noto Sans SC](https://fonts.google.com/noto/specimen/Noto+Sans+SC) fonts under the names the engine already loads
- Fully reversible: backups under `%LOCALAPPDATA%\SmallWorld2-hd\`
- One-file player build — no Python, no sidecar folders

## Requirements

| Role | Need |
|------|------|
| **Players** | Windows, Steam *Small World 2*, admin rights if the game is under `Program Files` |
| **Developers** | Python 3.11+, packages in [`requirements.txt`](requirements.txt) |

Steam app ID: `235620`.

## Install (players)

1. Download **`SmallWorld-hd.exe`** from [Releases](https://github.com/kyle-ip/small-world-hd/releases/latest).
2. Double-click the EXE (no install wizard).
3. Click **启用 HD**, then **启动游戏** (or start the game from Steam).

Quit *Small World 2* before enabling or disabling. Steam “Verify integrity of game files” restores official assets — run **启用 HD** again afterward.

### CLI

```bat
SmallWorld-hd.exe --enable
SmallWorld-hd.exe --disable
SmallWorld-hd.exe --launch
SmallWorld-hd.exe --status
SmallWorld-hd.exe --uninstall
```

| Flag | Meaning |
|------|---------|
| `--enable` / `--install` | Backup originals and apply the overlay |
| `--disable` | Restore from backup (keeps backups for a fast re-enable) |
| `--launch` | Enable if needed, then start via Steam |
| `--status` | Print enable state and payload file count |
| `--uninstall` | Restore, then delete local HD config / backups |

## Development

```bat
git clone https://github.com/kyle-ip/small-world-hd.git
cd small-world-hd
python -m pip install -r requirements.txt
python launcher\app.py
```

The clone already contains a complete `payload/Resources/` tree. That is enough to run the launcher or rebuild the player EXE:

```bat
powershell -ExecutionPolicy Bypass -File tools\build_allinone.ps1
```

### Optional regeneration

Requires a local *Small World 2* install. Some Chinese-plate scripts also need the English `.lproj` backup created by [small-world-zh-cn](https://github.com/kyle-ip/small-world-zh-cn).

```bat
python tools\build_hd_pack.py
python tools\rerender_zh_labels.py
python tools\redraw_clean_plates.py
python tools\paint_exp_card_titles.py
python tools\build_ui_fonts.py
python tools\verify_overlay.py --no-live
```

When editing art: keep official HD **filenames and pixel sizes**; do not change region detection masks; put Chinese plates only under `zh.lproj`.

### Repository layout

```text
payload/     HD assets (embedded into the EXE at build time)
launcher/    GUI, reversible overlay, Steam helpers
tools/       Build, verify, and optional regeneration scripts
```

## Related projects

- [small-world-zh-cn](https://github.com/kyle-ip/small-world-zh-cn) — unofficial Simplified Chinese language pack (same launcher style)

## Disclaimer

This is an unofficial fan project for personal learning.

- Do **not** sell this patch.
- Do **not** redistribute *Small World 2* or official Days of Wonder assets as a standalone game dump.
- Bundled CJK fonts are **Noto Sans SC** ([SIL Open Font License](https://scripts.sil.org/OFL)).
- Use at your own risk; always keep Steam verify / the built-in disable path available.
