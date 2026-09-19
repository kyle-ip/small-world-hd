# Small World 2 — HD Pack

Unofficial personal / learning project. Not affiliated with [Days of Wonder](https://www.days-of-wonder.com/), Asmodee, or Valve.

## For players — one EXE

Download **`SmallWorld-hd.exe`** from [Releases](https://github.com/kyle-ip/small-world-hd/releases). It **embeds** the HD payload. No Python, no extra folders, no other downloads.

| Button | Action |
|--------|--------|
| **启动游戏** | Enables HD if needed, then launches via Steam |
| **启用 HD / 关闭 HD** | Backup + overlay, or restore from backup |

```bat
SmallWorld-hd.exe --enable
SmallWorld-hd.exe --disable
SmallWorld-hd.exe --launch
SmallWorld-hd.exe --status
SmallWorld-hd.exe --uninstall
```

Backups live in `%LOCALAPPDATA%\SmallWorld2-hd\`. Quit the game before enable/disable. Writes under `Program Files` need Administrator. Steam “Verify integrity” restores stock files — enable HD again afterward.

Compatible with the unofficial Chinese pack ([small-world-zh-cn](https://github.com/kyle-ip/small-world-zh-cn)).

## For developers — clone and build

```bat
git clone https://github.com/kyle-ip/small-world-hd.git
cd small-world-hd
python -m pip install -r requirements.txt
python launcher\app.py
```

The repo includes a complete `payload/Resources/` tree (textures, shaders, OFL CJK fonts, Chinese plates). Clone alone is enough to run the launcher or rebuild the EXE:

```bat
powershell -ExecutionPolicy Bypass -File tools\build_allinone.ps1
```

Layout:

```text
payload/     HD assets embedded into the EXE at build time
launcher/    GUI / overlay / Steam helper
tools/       rebuild scripts (clarity pack, Chinese plates, fonts, verify)
```

Optional regeneration (needs a local Small World 2 install; some Chinese-plate scripts also need the English `.lproj` backup created by the Chinese pack):

```bat
python tools\build_hd_pack.py
python tools\rerender_zh_labels.py
python tools\redraw_clean_plates.py
python tools\paint_exp_card_titles.py
python tools\build_ui_fonts.py
python tools\verify_overlay.py --no-live
```

Rules when editing art: keep official HD filenames and pixel sizes; do not change region detection masks; Chinese plates only under `zh.lproj`.

## What the pack changes

- Same-size clarity pass on `common-hd` / `16-9-hd` (region masks / highlights / cursors skipped)
- Slightly tighter blur / dilation shaders
- Clean Chinese UI plates; expansion setup titles on card thumbs at a shared size
- OFL Noto Sans SC UI fonts under the names Cocos already loads
- Soft live expansion under-card captions cleared while HD is on

## Disclaimer

For personal learning only. Do not sell this patch. Do not redistribute the game binary. Bundled CJK fonts are [Noto Sans SC](https://fonts.google.com/noto/specimen/Noto+Sans+SC) (SIL OFL).
