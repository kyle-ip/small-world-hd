#!/usr/bin/env python3
"""Locate the Small World 2 install and launch it through Steam.

Lookup matches the Chinese pack (appid 235620) but does not touch language slots.
"""
from __future__ import annotations

import re
import subprocess
import winreg
from pathlib import Path

APPID = "235620"


def steam_root() -> Path:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            value, _ = winreg.QueryValueEx(key, "SteamPath")
            return Path(value)
    except OSError:
        pass
    for candidate in (
        Path(r"C:\Program Files (x86)\Steam"),
        Path(r"C:\Program Files\Steam"),
    ):
        if candidate.exists():
            return candidate
    raise FileNotFoundError("找不到 Steam 安装目录")


def library_folders(steam: Path) -> list[Path]:
    roots = [steam / "steamapps"]
    vdf = steam / "steamapps" / "libraryfolders.vdf"
    if vdf.exists():
        text = vdf.read_text(encoding="utf-8", errors="ignore")
        for match in re.finditer(r'"path"\s+"([^"]+)"', text):
            roots.append(Path(match.group(1)) / "steamapps")
    seen: set[str] = set()
    out: list[Path] = []
    for path in roots:
        key = str(path).lower()
        if key not in seen:
            seen.add(key)
            out.append(path)
    return out


def find_appmanifest() -> Path:
    for folder in library_folders(steam_root()):
        path = folder / f"appmanifest_{APPID}.acf"
        if path.exists():
            return path
    raise FileNotFoundError(f"找不到 appmanifest_{APPID}.acf（是否已安装 Small World 2？）")


def find_game_dir() -> Path:
    manifest = find_appmanifest()
    text = manifest.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r'"installdir"\s+"([^"]+)"', text)
    if not match:
        raise FileNotFoundError("appmanifest 里没有 installdir")
    return manifest.parent / "common" / match.group(1)


def launch_game() -> None:
    steam = steam_root() / "steam.exe"
    if steam.exists():
        subprocess.Popen([str(steam), f"steam://rungameid/{APPID}"], close_fds=True)
        return
    exe = find_game_dir() / "SmallWorld.exe"
    subprocess.Popen([str(exe)], cwd=str(exe.parent), close_fds=True)
