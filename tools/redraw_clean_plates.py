#!/usr/bin/env python3
"""Replace text-only Chinese plates with a clean supersampled redraw.

The inpaint pass leaves yellow scraps where the English lettering was.
Plates that are mostly transparent lettering are redrawn from scratch.
Wood panels and button chrome are left as they are.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT.parent
sys.path.insert(0, str(ROOT / "tools"))

import localize_images  # noqa: E402

BACKUP = Path.home() / "AppData" / "Local" / "SmallWorld2-zh-cn" / "backup_lproj" / "en.lproj"
OUT = ROOT / "payload" / "Resources" / "zh.lproj"
FONT_PATH = Path(r"C:\Windows\Fonts\msyhbd.ttc")
SCALE = 4
OPAQUE_LIMIT = 0.5

TOPS = {
    "ExpansionTopText_Cursed.png": "诅咒！",
    "ExpansionTopText_GrandDames.png": "贵妇团",
    "ExpansionTopText_BeNotAfraid.png": "不要害怕...",
    "ExpansionTopText_RoyalBonus.png": "皇家奖励",
    "ExpansionTopText_SpiderWeb.png": "蛛网",
}
BOTTOMS = {
    "ExpansionBottomText_Cursed.png": ["给你的（小小）世界", "下一道诅咒！"],
    "ExpansionBottomText_GrandDames.png": ["这些女主角", "来到（小小）世界！"],
    "ExpansionBottomText_BeNotAfraid.png": ["有人被迫", "成就伟大！"],
    "ExpansionBottomText_SpiderWeb.png": ["来我的巢穴吧！"],
}
# Decorations (spider, crown jewels) throw off a median sample.
PALETTE = {
    "ExpansionTopText_SpiderWeb.png": ((255, 214, 206), (168, 22, 34), (36, 10, 14)),
    "ExpansionTopText_RoyalBonus.png": ((244, 244, 238), (176, 176, 170), (138, 102, 36)),
}


def _lines_for(name: str) -> list[str] | None:
    if name in BOTTOMS:
        return BOTTOMS[name]
    if name in TOPS:
        return [TOPS[name]]
    text = localize_images.IMAGE_TEXT.get(name)
    if not text:
        return None
    return [text]


def _is_text_plate(path: Path) -> bool:
    with Image.open(path) as image:
        rgba = np.array(image.convert("RGBA"))
    return float((rgba[..., 3] > 10).mean()) < OPAQUE_LIMIT


def _palette(path: Path) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    if path.name in PALETTE:
        return PALETTE[path.name]
    rgba = np.array(Image.open(path).convert("RGBA"))
    rgb = rgba[..., :3]
    lum = rgb.astype(np.int16).mean(axis=2)
    ink = rgba[..., 3] > 40
    bright = ink & (lum > 90)
    if int(bright.sum()) < 20:
        bright = ink & (lum > 40)
    rows = np.where(bright.any(axis=1))[0]
    if len(rows) == 0:
        return (255, 236, 170), (214, 148, 42), (48, 28, 14)
    mid = int((rows.min() + rows.max()) / 2)

    def median(mask: np.ndarray, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
        points = rgb[mask]
        if len(points) < 8:
            return fallback
        return tuple(int(v) for v in np.median(points, axis=0))

    top = bright.copy()
    top[mid:, :] = False
    bottom = bright.copy()
    bottom[:mid, :] = False
    dark = ink & (lum > 12) & (lum < 75)
    return (
        median(top, (255, 236, 170)),
        median(bottom, (214, 148, 42)),
        median(dark, (48, 28, 14)),
    )


def _fit(draw: ImageDraw.ImageDraw, lines: list[str], width: int, height: int) -> tuple[ImageFont.FreeTypeFont, int]:
    size = max(12, int(height * (0.36 if len(lines) > 1 else 0.72)))
    while size > 10:
        font = ImageFont.truetype(str(FONT_PATH), size)
        stroke = max(1, size // 14)
        box = draw.multiline_textbbox(
            (0, 0),
            "\n".join(lines),
            font=font,
            stroke_width=stroke,
            align="center",
            spacing=int(size * 0.12),
        )
        if box[2] - box[0] <= width * 0.92 and box[3] - box[1] <= height * 0.86:
            return font, stroke
        size -= 1
    font = ImageFont.truetype(str(FONT_PATH), 10)
    return font, 1


def _render(width: int, height: int, lines: list[str], fill_top, fill_bot, stroke) -> Image.Image:
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    font, stroke_w = _fit(probe, lines, width, height)
    big = ImageFont.truetype(str(FONT_PATH), font.size * SCALE)
    stroke_big = stroke_w * SCALE
    canvas = Image.new("RGBA", (width * SCALE, height * SCALE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    text = "\n".join(lines)
    spacing = int(font.size * 0.12) * SCALE
    box = draw.multiline_textbbox(
        (0, 0),
        text,
        font=big,
        stroke_width=stroke_big,
        align="center",
        spacing=spacing,
    )
    x = (canvas.width - (box[2] - box[0])) // 2 - box[0]
    y = (canvas.height - (box[3] - box[1])) // 2 - box[1]
    draw.multiline_text(
        (x, y),
        text,
        font=big,
        fill=stroke + (255,),
        stroke_width=stroke_big,
        stroke_fill=stroke + (255,),
        align="center",
        spacing=spacing,
    )
    mask = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(mask).multiline_text(
        (x, y),
        text,
        font=big,
        fill=255,
        align="center",
        spacing=spacing,
    )
    blend = np.linspace(0, 1, canvas.height, dtype=np.float32)[:, None]
    gradient = np.zeros((canvas.height, canvas.width, 4), np.uint8)
    for channel in range(3):
        gradient[..., channel] = (fill_top[channel] * (1 - blend) + fill_bot[channel] * blend).astype(np.uint8)
    gradient[..., 3] = np.asarray(mask)
    canvas.alpha_composite(Image.fromarray(gradient, "RGBA"))
    return canvas.resize((width, height), Image.Resampling.LANCZOS)


def main() -> None:
    if not FONT_PATH.is_file():
        raise SystemExit(f"找不到字体: {FONT_PATH}")
    drawn = 0
    skipped = []
    for folder in ("common-hd", "common"):
        src_dir = BACKUP / folder
        if not src_dir.is_dir():
            raise SystemExit(f"找不到英文原图: {src_dir}")
        for name, _text in localize_images.IMAGE_TEXT.items():
            if not name.lower().endswith(".png"):
                continue
            source = src_dir / name
            lines = _lines_for(name)
            if lines is None or not source.is_file() or not _is_text_plate(source):
                if source.is_file() and name.lower().endswith(".png"):
                    skipped.append(f"{folder}/{name}")
                continue
            with Image.open(source) as image:
                width, height = image.size
            plate = _render(width, height, lines, *_palette(source))
            dest = OUT / folder / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            plate.save(dest, format="PNG")
            drawn += 1
    print(f"clean plates: {drawn}")
    print(f"kept inpainted: {len(skipped)}")


if __name__ == "__main__":
    main()
