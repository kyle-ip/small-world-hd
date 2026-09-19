#!/usr/bin/env python3
"""Build the full HD payload from the installed game art.

Same pixel size as the official HD files so atlases and hit positions stay valid.
Region masks, highlights, and cursors are left untouched.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = ("common-hd", "16-9-hd")
SKIP_PARTS = ("region", "highlight", "cursor", "detection", "separation", "indic")
MODEL_PATH = Path(__file__).resolve().parent / "models" / "FSRCNN_x2.pb"
NEURAL_MAX_SIDE = 1024


def _skip(name: str) -> bool:
    lower = name.lower()
    return any(part in lower for part in SKIP_PARTS)


def _load_superres():
    if not MODEL_PATH.is_file():
        return None
    try:
        import cv2

        if not hasattr(cv2, "dnn_superres"):
            return None
        engine = cv2.dnn_superres.DnnSuperResImpl_create()
        engine.readModel(str(MODEL_PATH))
        engine.setModel("fsrcnn", 2)
        return engine
    except Exception as exc:  # noqa: BLE001
        print(f"super-res unavailable ({exc}); using sharpen only")
        return None


def _rgb_unsharp(rgb: Image.Image, *, large: bool) -> Image.Image:
    if large:
        out = rgb.filter(ImageFilter.UnsharpMask(radius=1.4, percent=80, threshold=3))
        out = ImageEnhance.Contrast(out).enhance(1.05)
        return ImageEnhance.Color(out).enhance(1.04)
    big = rgb.resize((rgb.width * 2, rgb.height * 2), Image.Resampling.LANCZOS)
    big = big.filter(ImageFilter.UnsharpMask(radius=1.3, percent=125, threshold=2))
    big = ImageEnhance.Contrast(big).enhance(1.06)
    big = ImageEnhance.Color(big).enhance(1.05)
    return big.resize(rgb.size, Image.Resampling.LANCZOS)


def _neural_rgb(engine, rgb: Image.Image) -> Image.Image:
    import cv2

    bgr = cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2BGR)
    up = engine.upsample(bgr)
    up = cv2.cvtColor(up, cv2.COLOR_BGR2RGB)
    restored = Image.fromarray(up).resize(rgb.size, Image.Resampling.LANCZOS)
    restored = restored.filter(ImageFilter.UnsharpMask(radius=0.8, percent=60, threshold=2))
    restored = ImageEnhance.Contrast(restored).enhance(1.04)
    return ImageEnhance.Color(restored).enhance(1.04)


def _enhance(path: Path, engine) -> Image.Image:
    with Image.open(path) as source:
        rgba = source.convert("RGBA").copy()
        width, height = rgba.size
    rgb = rgba.convert("RGB")
    alpha = rgba.getchannel("A")
    large = max(width, height) > NEURAL_MAX_SIDE
    if engine is not None and not large:
        try:
            rgb = _neural_rgb(engine, rgb)
        except Exception:
            rgb = _rgb_unsharp(rgb, large=False)
    else:
        rgb = _rgb_unsharp(rgb, large=large)
    if rgb.size != (width, height):
        rgb = rgb.resize((width, height), Image.Resampling.LANCZOS)
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    return out


def _write_image(src: Path, dest: Path, engine) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    enhanced = _enhance(src, engine)
    with Image.open(src) as original:
        if enhanced.size != original.size:
            raise RuntimeError(f"size changed: {src.name} {original.size} -> {enhanced.size}")
    suffix = src.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        enhanced.convert("RGB").save(dest, format="JPEG", quality=95, subsampling=0, optimize=True)
        return
    enhanced.save(dest, format="PNG", compress_level=3)


def _patch_shaders(game: Path, dest_root: Path) -> int:
    src_dir = game / "Resources" / "shader"
    out_dir = dest_root / "shader"
    out_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    blur = src_dir / "blur.fsh"
    if blur.is_file():
        text = blur.read_text(encoding="utf-8")
        updated = text.replace(
            "vec2 delta = float(i) * u_direction;",
            "vec2 delta = float(i) * u_direction * 0.72;",
            1,
        )
        if updated == text:
            raise SystemExit("blur.fsh did not contain the expected sample step")
        (out_dir / "blur.fsh").write_text(updated, encoding="utf-8", newline="\n")
        written += 1
    dilation = src_dir / "dilation.fsh"
    if dilation.is_file():
        text = dilation.read_text(encoding="utf-8")
        updated = text.replace(
            "int radius = int(floor(u_kernelRadius));",
            "int radius = int(max(1.0, floor(u_kernelRadius * 0.72)));",
            1,
        )
        if updated == text:
            raise SystemExit("dilation.fsh did not contain the expected radius")
        (out_dir / "dilation.fsh").write_text(updated, encoding="utf-8", newline="\n")
        written += 1
    return written


def _clear_generated(dest_root: Path) -> None:
    for folder in (*FOLDERS, "shader"):
        path = dest_root / folder
        if not path.is_dir():
            continue
        for child in path.rglob("*"):
            if child.is_file() and child.suffix.lower() in {".png", ".jpg", ".jpeg", ".fsh", ".vsh"}:
                child.unlink()


def build(game: Path) -> None:
    resources = game / "Resources"
    dest_root = ROOT / "payload" / "Resources"
    if not (resources / "common-hd").is_dir():
        raise SystemExit(f"找不到 HD 资源: {resources / 'common-hd'}")
    _clear_generated(dest_root)
    engine = _load_superres()
    print(f"super-res: {'FSRCNN x2' if engine is not None else 'off'}")
    written = 0
    skipped = 0
    for folder in FOLDERS:
        src_dir = resources / folder
        for src in sorted(src_dir.rglob("*")):
            if not src.is_file():
                continue
            if src.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                continue
            if _skip(src.name):
                skipped += 1
                continue
            rel = src.relative_to(src_dir)
            dest = dest_root / folder / rel
            _write_image(src, dest, engine)
            written += 1
            if written % 40 == 0:
                print(f"  {written} images")
    shaders = _patch_shaders(game, dest_root)
    print(f"images={written} skipped_masks={skipped} shaders={shaders}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Small World 2 HD payload")
    parser.add_argument("--game", type=Path, default=ROOT.parent)
    args = parser.parse_args()
    build(args.game.resolve())


if __name__ == "__main__":
    main()
