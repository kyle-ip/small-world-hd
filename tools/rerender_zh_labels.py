#!/usr/bin/env python3
"""Redraw Chinese baked-text plates at their real HD size.

The old plates were SimHei drawn 1:1, so strokes look jagged on a large
window. This keeps the English artwork, erases the original letters, and
draws Microsoft YaHei at 4x before downsampling.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT.parent
sys.path.insert(0, str(ROOT / "tools"))

import cnfont  # noqa: E402
import inpaint_text  # noqa: E402
import localize_banners  # noqa: E402
import localize_images  # noqa: E402

BACKUP = Path(os.environ.get("LOCALAPPDATA", "")) / "SmallWorld2-zh-cn" / "backup_lproj" / "en.lproj"
JA = GAME / "Resources" / "ja.lproj"
OUT = ROOT / "payload" / "Resources" / "zh.lproj"
FONT = r"C:\Windows\Fonts\msyhbd.ttc"
SCALE = 4

cnfont.FONT_CANDIDATES.insert(0, (FONT, 0))
cnfont._cached_path = None
cnfont._cached_cmap = None


def _draw_text(result, en, mask, text, w, h, style=None):
    ys, xs = np.where(mask > 0)
    bx0, bx1, by0, by1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    if style == "plaque":
        fill, stroke = (232, 230, 222), (72, 52, 32)
    elif style == "sub":
        fill, stroke = (236, 226, 205), (96, 62, 30)
    else:
        opaque = (mask > 0) & (en[..., 3] > 200)
        body = en[..., :3][opaque]
        if len(body) < 8:
            body = en[..., :3][mask > 0]
        fill = tuple(int(v) for v in np.median(body, axis=0))
        stroke = (238, 224, 196) if sum(fill) / 3 < 110 else (62, 38, 16)

    box_w, box_h = bx1 - bx0 + 1, by1 - by0 + 1
    height_factor = 0.62 if style == "sub" else 0.78
    size = max(12, int(box_h * height_factor))
    if style == "plaque":
        size = min(size, int(h * 0.16))
    size *= SCALE

    layer = Image.new("RGBA", (w * SCALE, h * SCALE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    while size > 8 * SCALE:
        stroke_w = max(SCALE, size // 14)
        font = cnfont.load_font(size)
        bb = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_w)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        if tw <= box_w * SCALE and th <= box_h * SCALE:
            break
        size -= SCALE
    stroke_w = max(SCALE, size // 14)
    font = cnfont.load_font(size)
    bb = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_w)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    cx = (bx0 + bx1) * SCALE // 2
    cy = (by0 + by1) * SCALE // 2
    x = cx - tw // 2 - bb[0]
    y = cy - th // 2 - bb[1]
    draw.text(
        (x, y),
        text,
        font=font,
        fill=fill + (255,),
        stroke_width=stroke_w,
        stroke_fill=stroke + (255,),
    )
    small = layer.resize((w, h), Image.Resampling.LANCZOS)
    base = Image.fromarray(result, "RGBA")
    base.alpha_composite(small)
    return np.array(base)


inpaint_text._draw_text = _draw_text


def _pairs():
    jobs = []
    for fname, text in localize_images.IMAGE_TEXT.items():
        jobs.append((fname, text, None, False))
    for fname, text in localize_banners.ALL_NAMES.items():
        jobs.append((fname, text, localize_banners.SUBTEXT.get(fname), True))
    en_dir = BACKUP / "common"
    if en_dir.is_dir():
        for path in sorted(en_dir.glob("*InDecline.png")):
            text = localize_banners.ALL_NAMES.get(path.name.replace("InDecline.png", ".png"))
            if text:
                jobs.append((path.name, text, None, True))
    return jobs


def _one(folder: str, fname: str, text: str, sub: str | None, plaque: bool) -> bool:
    en = BACKUP / folder / fname
    ref = JA / folder / fname
    if not en.is_file() or not ref.is_file():
        return False
    img = inpaint_text.inpaint_localize(
        str(en),
        str(ref),
        text,
        jpg=fname.lower().endswith((".jpg", ".jpeg")),
        subtext=sub,
        plaque=plaque,
    )
    if img is None:
        return False
    with Image.open(en) as original:
        if img.size != original.size:
            img = img.resize(original.size, Image.Resampling.LANCZOS)
    dest = OUT / folder / fname
    dest.parent.mkdir(parents=True, exist_ok=True)
    if fname.lower().endswith((".jpg", ".jpeg")):
        img.convert("RGB").save(dest, format="JPEG", quality=95, subsampling=0)
    else:
        img.save(dest, format="PNG")
    return True


def main() -> None:
    if not FONT or not Path(FONT).is_file():
        raise SystemExit(f"找不到字体: {FONT}")
    if not (BACKUP / "common-hd").is_dir():
        raise SystemExit(f"找不到英文原图备份: {BACKUP}")
    done = 0
    missed = []
    for fname, text, sub, plaque in _pairs():
        hit = False
        for folder in ("common-hd", "common"):
            if _one(folder, fname, text, sub, plaque):
                done += 1
                hit = True
        if not hit:
            missed.append(fname)
        if done and done % 20 == 0:
            print(f"  {done}")
    print(f"redrew {done} plates; missing {len(missed)}")
    if missed:
        print("missing:", ", ".join(missed[:12]))


if __name__ == "__main__":
    main()
