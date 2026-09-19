#!/usr/bin/env python3
"""Install hinted Microsoft YaHei Bold under the font names Cocos already loads.

The Chinese pack's Noto instances have no TrueType hints, so DirectWrite
draws the live expansion captions soft. YaHei Bold keeps those names
(ArialMT / Arial-BoldMT) and hints at 96 DPI.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "payload" / "Resources" / "fonts"
SOURCE = Path(r"C:\Windows\Fonts\msyhbd.ttc")

SPECS = [
    ("arialmt.ttf", "Arial MT", "Medium", "ArialMT"),
    ("futura-medium.ttf", "Arial MT", "Medium", "ArialMT"),
    ("futura-condensedmedium.ttf", "Arial MT", "Medium", "ArialMT"),
    ("arialboldmt.otf", "Arial MT", "Bold", "Arial-BoldMT"),
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


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"找不到微软雅黑粗体: {SOURCE}")
    OUT.mkdir(parents=True, exist_ok=True)
    master = OUT / "_yahei-bold.ttf"
    font = TTFont(str(SOURCE), fontNumber=0)
    if "DSIG" in font:
        del font["DSIG"]
    font.save(str(master))
    font.close()
    for filename, family, subfamily, ps_name in SPECS:
        face = TTFont(str(master))
        set_names(face, family, subfamily, ps_name)
        dest = OUT / filename
        face.save(str(dest))
        face.close()
        print(f"wrote {dest.name} ({dest.stat().st_size // 1024} KB) as {ps_name}")
    master.unlink(missing_ok=True)
    print(f"Done → {OUT}")


if __name__ == "__main__":
    main()
