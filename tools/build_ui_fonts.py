#!/usr/bin/env python3
"""Build redistributable CJK UI fonts (Noto Sans SC, OFL) for the HD pack.

Same masters as the Chinese pack: arialmt.ttf + arialboldmt.otf. On enable,
the overlay also installs Futura filenames from the Medium master.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "payload" / "Resources" / "fonts"
CN_FONTS = ROOT.parent / "small-world-zh-cn" / "payload" / "Resources" / "fonts"

VF_CANDIDATES = [
    Path(r"C:\Windows\Fonts\NotoSansSC-VF.ttf"),
    Path(r"C:\Windows\Fonts\NotoSansSC-VariableFont_wght.ttf"),
    Path.home() / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts" / "NotoSansSC-VF.ttf",
]

SPECS = [
    ("arialmt.ttf", 600, "Arial MT", "Medium", "ArialMT"),
    ("arialboldmt.otf", 700, "Arial MT", "Bold", "Arial-BoldMT"),
]


def set_names(font: TTFont, family: str, subfamily: str, ps_name: str) -> None:
    full = f"{family} {subfamily}"
    name = font["name"]
    for record in list(name.names):
        if record.nameID in (1, 2, 4, 6, 16, 17) and record.platformID in (1, 3):
            name.names.remove(record)
    for nid, value in (
        (1, family),
        (2, subfamily),
        (4, full),
        (6, ps_name),
        (16, family),
        (17, subfamily),
    ):
        name.setName(value, nid, 3, 1, 0x409)
        name.setName(value, nid, 1, 0, 0)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    # Prefer already-built OFL masters from the Chinese pack when present.
    if (CN_FONTS / "arialmt.ttf").is_file() and (CN_FONTS / "arialboldmt.otf").is_file():
        for name in ("arialmt.ttf", "arialboldmt.otf", "OFL.txt"):
            src = CN_FONTS / name
            if src.is_file():
                shutil.copy2(src, OUT / name)
                print(f"copied {name} from Chinese pack")
        # Drop non-redistributable / duplicate faces
        for stale in ("futura-medium.ttf", "futura-condensedmedium.ttf"):
            (OUT / stale).unlink(missing_ok=True)
        print(f"Done → {OUT}")
        return 0

    vf = next((p for p in VF_CANDIDATES if p.is_file()), None)
    if vf is None:
        raise SystemExit(
            "NotoSansSC-VF.ttf not found and Chinese-pack fonts missing. "
            "Install Noto Sans SC or place OFL masters under payload/Resources/fonts/."
        )
    print(f"Source VF: {vf}")
    cache: dict[int, TTFont] = {}
    for filename, weight, family, subfamily, ps_name in SPECS:
        if weight not in cache:
            base = TTFont(str(vf))
            cache[weight] = instantiateVariableFont(base, {"wght": weight}, inplace=False)
        tmp = ROOT / "dist" / "build" / f"_font_{weight}.ttf"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        cache[weight].save(str(tmp))
        font = TTFont(str(tmp))
        set_names(font, family, subfamily, ps_name)
        font.save(str(OUT / filename))
        font.close()
        print(f"wrote {filename}")
    ofl = Path(__file__).with_name("OFL.txt")
    if not ofl.is_file() and (CN_FONTS / "OFL.txt").is_file():
        ofl = CN_FONTS / "OFL.txt"
    if ofl.is_file():
        shutil.copy2(ofl, OUT / "OFL.txt")
    print(f"Done → {OUT} (OFL Noto Sans SC)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
