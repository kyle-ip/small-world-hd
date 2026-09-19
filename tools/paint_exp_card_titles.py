#!/usr/bin/env python3
"""Bake sharp Chinese titles onto expansion card thumbs.

All five covers share one font size and one title band so they look even
on the setup screen. Live under-card labels stay cleared by the overlay.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT.parent
BACKUP = Path.home() / "AppData" / "Local" / "SmallWorld2-zh-cn" / "backup_lproj" / "en.lproj"
OUT = ROOT / "payload" / "Resources" / "zh.lproj"
FONT = Path(r"C:\Windows\Fonts\msyhbd.ttc")
SCALE = 4

# Keep every title the same visual height; longest string sets the shared size.
TITLES = {
    "exp-Cursed": "诅咒！",
    "exp-GrandDames": "贵妇团",
    "exp-BeNotAfraid": "不要害怕",
    "exp-RoyalBonus": "皇家奖励",
    "exp-SpiderWeb": "蛛网",
}
# Erase warm / orange English display titles in the lower band.
ERASE_ENGLISH = {"exp-Cursed", "exp-BeNotAfraid", "exp-SpiderWeb"}

# Shared title band as fractions of card size (same for every cover).
BAND_TOP = 0.70
BAND_BOT = 0.86
BAND_SIDE = 0.06
# Shared glyph height as a fraction of card height (fits 不要害怕).
FONT_FRAC = 0.095
FILL_TOP = (255, 236, 170)
FILL_BOT = (220, 150, 40)
STROKE = (40, 24, 12)


def _band_box(w: int, h: int) -> tuple[int, int, int, int]:
    return (
        int(w * BAND_SIDE),
        int(h * BAND_TOP),
        int(w * (1 - BAND_SIDE)),
        int(h * BAND_BOT),
    )


def _erase_english(rgb: np.ndarray, key: str) -> np.ndarray:
    if key not in ERASE_ENGLISH:
        return rgb
    h, w = rgb.shape[:2]
    # Spider Web's English title sits a bit higher than the others.
    top = 0.55 if key == "exp-SpiderWeb" else BAND_TOP
    x0, y0, x1, y1 = int(w * BAND_SIDE), int(h * top), int(w * (1 - BAND_SIDE)), int(h * BAND_BOT)
    band = rgb[y0:y1, x0:x1]
    r, g, b = band[..., 0].astype(int), band[..., 1].astype(int), band[..., 2].astype(int)
    warm = (r > 140) & (g > 60) & (b < 140) & (r > b + 30) & (g + 40 > b)
    mask = np.zeros((h, w), np.uint8)
    mask[y0:y1, x0:x1] = warm.astype(np.uint8) * 255
    if int((mask > 0).sum()) < 30:
        return rgb
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=2)
    bgr = rgb[:, :, ::-1].copy()
    return cv2.inpaint(bgr, mask, 3, cv2.INPAINT_TELEA)[:, :, ::-1]


def _shared_font_size(width: int, height: int) -> tuple[int, int]:
    """Pick one size that fits the longest title in the shared band."""
    x0, y0, x1, y1 = _band_box(width, height)
    box_w = (x1 - x0) * SCALE
    box_h = (y1 - y0) * SCALE
    longest = max(TITLES.values(), key=len)
    size = max(8 * SCALE, int(height * FONT_FRAC) * SCALE)
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    while size > 8 * SCALE:
        font = ImageFont.truetype(str(FONT), size)
        stroke_w = max(SCALE, size // 14)
        box = probe.textbbox((0, 0), longest, font=font, stroke_width=stroke_w)
        if box[2] - box[0] <= box_w * 0.96 and box[3] - box[1] <= box_h * 0.92:
            return size, stroke_w
        size -= SCALE
    return size, max(SCALE, size // 14)


def _draw_title(base: Image.Image, text: str, size: int, stroke_w: int) -> Image.Image:
    w, h = base.size
    x0, y0, x1, y1 = _band_box(w, h)
    layer = Image.new("RGBA", (w * SCALE, h * SCALE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    font = ImageFont.truetype(str(FONT), size)
    box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_w)
    tw, th = box[2] - box[0], box[3] - box[1]
    cx = (x0 + x1) * SCALE // 2
    cy = (y0 + y1) * SCALE // 2
    x = cx - tw // 2 - box[0]
    y = cy - th // 2 - box[1]

    # Soft dark plate so gold text stays readable on any cover color.
    pad_x, pad_y = int(tw * 0.08), int(th * 0.18)
    plate = [
        x + box[0] - pad_x,
        y + box[1] - pad_y,
        x + box[0] + tw + pad_x,
        y + box[1] + th + pad_y,
    ]
    draw.rounded_rectangle(plate, radius=max(SCALE * 2, th // 6), fill=(20, 12, 8, 150))

    draw.text(
        (x, y),
        text,
        font=font,
        fill=STROKE + (255,),
        stroke_width=stroke_w,
        stroke_fill=STROKE + (255,),
    )
    ink = Image.new("L", layer.size, 0)
    ImageDraw.Draw(ink).text((x, y), text, font=font, fill=255)
    blend = np.linspace(0, 1, layer.height, dtype=np.float32)[:, None]
    grad = np.zeros((layer.height, layer.width, 4), np.uint8)
    for i in range(3):
        grad[..., i] = (FILL_TOP[i] * (1 - blend) + FILL_BOT[i] * blend).astype(np.uint8)
    grad[..., 3] = np.asarray(ink)
    layer.alpha_composite(Image.fromarray(grad, "RGBA"))
    out = base.convert("RGBA")
    out.alpha_composite(layer.resize((w, h), Image.Resampling.LANCZOS))
    return out.convert("RGB")


def _paint(rgb: np.ndarray, text: str, key: str, size: int, stroke_w: int) -> Image.Image:
    cleaned = _erase_english(rgb, key)
    return _draw_title(Image.fromarray(cleaned, "RGB"), text, size, stroke_w)


def main() -> None:
    if not FONT.is_file():
        raise SystemExit(f"找不到字体: {FONT}")
    written = 0
    for folder in ("common-hd", "common"):
        src_dir = BACKUP / folder
        if not src_dir.is_dir():
            src_dir = GAME / "Resources" / "zh.lproj" / folder
        sample = None
        for key in TITLES:
            candidate = src_dir / f"{key}-on.jpg"
            if candidate.is_file():
                sample = np.array(Image.open(candidate).convert("RGB"))
                break
        if sample is None:
            raise SystemExit(f"找不到扩展封面: {src_dir}")
        h, w = sample.shape[:2]
        size, stroke_w = _shared_font_size(w, h)
        print(f"{folder}: shared size={size // SCALE}px stroke={stroke_w // SCALE}")
        for key, text in TITLES.items():
            for state in ("on", "off"):
                name = f"{key}-{state}.jpg"
                source = src_dir / name
                if not source.is_file():
                    print("missing", folder, name)
                    continue
                rgb = np.array(Image.open(source).convert("RGB"))
                out = _paint(rgb, text, key, size, stroke_w)
                dest = OUT / folder / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                out.save(dest, format="JPEG", quality=95, subsampling=0, optimize=True)
                written += 1
    print(f"painted {written} expansion cards")


if __name__ == "__main__":
    main()
