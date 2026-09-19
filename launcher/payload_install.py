#!/usr/bin/env python3
"""Locate and validate HD payload files. Copying is done by overlay.py."""
from __future__ import annotations

import sys
from pathlib import Path

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".plist"}
SHADER_SUFFIXES = (".fsh", ".vsh", ".frag", ".vert", "_frag", "_vert")
# Masters only; enable expands Medium → Futura filenames Cocos expects.
FONT_MASTERS = {
    "arialmt.ttf": ("arialmt.ttf", "futura-medium.ttf", "futura-condensedmedium.ttf"),
    "arialboldmt.otf": ("arialboldmt.otf",),
}
FONT_FILES = {name for names in FONT_MASTERS.values() for name in names} | {
    "arialmt.ttf",
    "arialboldmt.otf",
    "ofl.txt",
}
# Live expansion captions stay soft after window upscale; HD clears them and
# puts the Chinese title on the card art instead.
STRING_FILES = {"localizedstrings.xml"}
EXPANSION_TITLE_KEYS = (
    "ExpansionTitle_Cursed",
    "ExpansionTitle_GrandDames",
    "ExpansionTitle_BeNotAfraid",
    "ExpansionTitle_RoyalBonus",
    "ExpansionTitle_SpiderWeb",
)


def _has_payload_files(root: Path) -> bool:
    if not root.is_dir():
        return False
    for path in root.rglob("*"):
        if path.is_file() and path.name != ".gitkeep":
            return True
    return False


def bundle_payload_root() -> Path:
    """Frozen EXE prefers the embedded payload so one file is enough for players."""
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", ""))
        candidates.append(meipass / "payload" / "Resources")
        exe = Path(sys.executable).resolve()
        candidates.append(exe.parent / "small-world-hd" / "payload" / "Resources")
        candidates.append(exe.parent / "payload" / "Resources")
        if len(exe.parents) > 1:
            candidates.append(exe.parents[1] / "payload" / "Resources")
    else:
        candidates.append(Path(__file__).resolve().parents[1] / "payload" / "Resources")
    for path in candidates:
        if _has_payload_files(path):
            return path
    return candidates[0]


def validate_rel(rel: str) -> None:
    """Reject anything outside the HD art / shader whitelist, especially .lproj."""
    if not rel or rel.startswith(("/", "\\")) or "\\" in rel:
        raise ValueError(f"非法相对路径: {rel}")
    parts = rel.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"非法相对路径: {rel}")
    # Chinese baked-text plates only. Never overlay string tables or other languages.
    if (
        len(parts) == 3
        and parts[0] == "zh.lproj"
        and parts[1] in {"common", "common-hd"}
        and Path(parts[2]).suffix.lower() in IMAGE_EXT
    ):
        return
    if (
        len(parts) == 2
        and parts[0] == "zh.lproj"
        and parts[1].lower() in STRING_FILES
    ):
        return
    lower = rel.lower()
    if ".lproj" in lower:
        raise ValueError(f"不会覆盖语言包: {rel}")
    name = parts[-1].lower()
    if len(parts) == 2 and parts[0] == "fonts" and name in FONT_FILES:
        return
    if lower.startswith("common-hd/") or lower.startswith("16-9-hd/"):
        if Path(name).suffix.lower() not in IMAGE_EXT:
            raise ValueError(f"不允许的图片类型: {rel}")
        return
    if lower.startswith("shader/"):
        if name.endswith(".sb") or name.endswith(".sh"):
            raise ValueError(f"不覆盖预编译或脚本文件: {rel}")
        if not name.endswith(SHADER_SUFFIXES):
            raise ValueError(f"不允许的着色器文件: {rel}")
        return
    raise ValueError(
        f"不在允许目录（仅 common-hd、16-9-hd、shader、字体和中文贴图）: {rel}"
    )


def collect_files(payload_root: Path | None = None) -> list[tuple[str, Path]]:
    root = (payload_root or bundle_payload_root()).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"找不到 payload: {root}")
    found: list[tuple[str, Path]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        resolved = path.resolve()
        rel = resolved.relative_to(root).as_posix()
        # License text ships with fonts but is not installed into the game.
        if rel.lower() == "fonts/ofl.txt":
            continue
        validate_rel(rel)
        found.append((rel, resolved))
        # Expand Medium master into Futura slots Cocos loads by name.
        if rel == "fonts/arialmt.ttf":
            for dest_name in FONT_MASTERS["arialmt.ttf"]:
                if dest_name == "arialmt.ttf":
                    continue
                found.append((f"fonts/{dest_name}", resolved))
    return found
