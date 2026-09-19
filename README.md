# Small World 2 — HD Pack

Unofficial personal / learning project. Not affiliated with [Days of Wonder](https://www.days-of-wonder.com/), Asmodee, or Valve.

HD assets live only under `payload/`. **Do not edit** the game install `Resources/` by hand. The launcher backs up originals on enable and restores them on disable.

Works alongside the unofficial Chinese pack: this project never rewrites language junction settings. It may overlay Chinese baked-text images under `zh.lproj/common(-hd)/`, optional UI fonts, and a small string tweak that hides soft live expansion captions (restored on disable).

## Players

Development run:

```bat
python launcher\app.py
```

Or double-click `SmallWorld-hd.exe` in the game root after building.

| Button | Action |
|--------|--------|
| Launch game | Enables HD if needed, then starts via Steam |
| Enable HD / Disable HD | Backup + overlay, or restore from backup |

CLI:

```bat
python launcher\app.py --enable
python launcher\app.py --disable
python launcher\app.py --launch
python launcher\app.py --status
python launcher\app.py --uninstall
```

`--install` is the same as `--enable`. Backups live in `%LOCALAPPDATA%\SmallWorld2-hd\`. Disable keeps backups for a fast re-enable; `--uninstall` restores then deletes that config folder.

You cannot enable or disable while `SmallWorld.exe` is running. Writes under `Program Files` need Administrator. Steam “Verify integrity of game files” restores stock assets — click **Enable HD** again afterward.

## Building the art pack

Paths mirror the game `Resources/` tree. Only commit tools and launcher code; generated art is gitignored.

```text
payload/Resources/common-hd/          Tokens, maps, atlases (PNG/JPG)
payload/Resources/16-9-hd/            Widescreen backgrounds
payload/Resources/shader/             GLSL (blur / dilation)
payload/Resources/fonts/              Optional CJK UI fonts (YaHei-named)
payload/Resources/zh.lproj/common(-hd)/  Chinese baked plates / expansion thumbs
```

Rules:

- Keep official HD filenames and pixel sizes. Atlas `.plist` frame rects must stay valid.
- Do not change region geometry; clicks depend on stock detection maps and coordinates.
- Do not put files under other languages’ `*.lproj`. Chinese plates only under `zh.lproj`.
- Do not commit official game art. `.gitignore` already excludes payload images, shaders, and fonts.

Typical rebuild:

```bat
python tools\build_hd_pack.py
python tools\rerender_zh_labels.py
python tools\redraw_clean_plates.py
python tools\paint_exp_card_titles.py
python tools\build_ui_fonts.py
python tools\verify_overlay.py --no-live
```

One-file launcher (copies EXE next to `SmallWorld.exe`):

```bat
powershell -ExecutionPolicy Bypass -File tools\build_allinone.ps1
```

## What the pack changes

- Same-size clarity pass on `common-hd` / `16-9-hd` (region masks, highlights, and cursors skipped).
- Slightly tighter blur / dilation shaders.
- Clean supersampled Chinese UI plates; expansion setup titles painted on card thumbs at a shared size.
- Optional hinted YaHei Bold installed under the font names Cocos already loads.
- Live expansion under-card captions cleared while HD is on (titles appear on the cards instead).

## Disclaimer

For personal learning only. Do not sell this patch. Do not redistribute the game binary or official Days of Wonder assets.
