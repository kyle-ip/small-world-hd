#!/usr/bin/env python3
"""File-level HD overlay: backup originals, copy payload, restore on disable.

Backups live in %LOCALAPPDATA%\\SmallWorld2-hd and are not overwritten on
re-enable, so a second enable cannot snapshot an already patched file.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import payload_install

CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "SmallWorld2-hd"
CONFIG_PATH = CONFIG_DIR / "config.json"
MANIFEST_PATH = CONFIG_DIR / "manifest.json"
BACKUP_ROOT = CONFIG_DIR / "backup"

_PERM = "无法写入游戏目录。请先退出游戏，并以管理员身份运行启动器。"
_STRINGS_REL = "zh.lproj/localizedStrings.xml"


def load_config() -> dict:
    if CONFIG_PATH.is_file():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {"hd_enabled": False, "game_dir": None}


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def load_manifest() -> dict:
    if MANIFEST_PATH.is_file():
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        data.setdefault("files", [])
        return data
    return {"version": 1, "game_dir": None, "files": []}


def _save_manifest(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def hd_enabled() -> bool:
    return bool(load_config().get("hd_enabled"))


def require_game(game: Path) -> Path:
    game = game.resolve()
    if not (game / "SmallWorld.exe").is_file():
        raise FileNotFoundError(f"该目录下没有 SmallWorld.exe: {game}")
    if not (game / "Resources").is_dir():
        raise FileNotFoundError(f"该目录下没有 Resources: {game}")
    return game


def game_process_running() -> bool:
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq SmallWorld.exe", "/NH"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    return "SmallWorld.exe" in (result.stdout or "")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dest(game: Path, rel: str) -> Path:
    return game / "Resources" / Path(rel)


def _backup(rel: str) -> Path:
    return BACKUP_ROOT / Path(rel)


def _restore_one(game: Path, entry: dict) -> None:
    rel = entry["rel"]
    payload_install.validate_rel(rel)
    dest = _dest(game, rel)
    if entry.get("had_original"):
        backup = _backup(rel)
        if not backup.is_file():
            raise FileNotFoundError(f"缺少原文件备份，无法还原: {rel}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup, dest)
        return
    if dest.is_file():
        dest.unlink()
    _prune_empty(dest.parent, game / "Resources")


def _prune_empty(start: Path, stop: Path) -> None:
    current = start
    stop = stop.resolve()
    while current.resolve() != stop:
        if not current.is_dir() or any(current.iterdir()):
            return
        current.rmdir()
        current = current.parent


def _apply_one(game: Path, rel: str, src: Path) -> dict:
    payload_install.validate_rel(rel)
    dest = _dest(game, rel)
    backup = _backup(rel)
    had_original = backup.is_file()
    if dest.is_file() and not backup.is_file():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dest, backup)
        had_original = True
    elif not dest.exists():
        had_original = False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return {
        "rel": rel,
        "had_original": had_original,
        "sha256": _sha256(dest),
    }


def _clear_expansion_titles(game: Path) -> dict | None:
    """Hide soft live captions; Chinese titles are painted on the card art."""
    payload_install.validate_rel(_STRINGS_REL)
    dest = _dest(game, _STRINGS_REL)
    if not dest.is_file():
        return None
    backup = _backup(_STRINGS_REL)
    if not backup.is_file():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dest, backup)
    text = dest.read_text(encoding="utf-8")
    updated = text
    for key in payload_install.EXPANSION_TITLE_KEYS:
        updated = re.sub(
            rf'(<string key="{re.escape(key)}">)(.*?)(</string>)',
            r"\1\3",
            updated,
            count=1,
            flags=re.DOTALL,
        )
    if updated == text:
        return None
    dest.write_text(updated, encoding="utf-8", newline="\n")
    return {
        "rel": _STRINGS_REL,
        "had_original": True,
        "sha256": _sha256(dest),
    }


def _guard_running(check_running: bool) -> None:
    if check_running and game_process_running():
        raise RuntimeError("请先退出 Small World 2，再启用或关闭 HD。")


def disable(check_running: bool = True) -> str:
    """Restore every file listed in the manifest. Backups are kept."""
    _guard_running(check_running)
    cfg = load_config()
    manifest = load_manifest()
    files = manifest.get("files") or []
    if not files and not cfg.get("hd_enabled"):
        return "HD 未启用"
    game_text = manifest.get("game_dir") or cfg.get("game_dir")
    if not game_text:
        cfg["hd_enabled"] = False
        save_config(cfg)
        return "HD 未启用"
    game = require_game(Path(game_text))
    try:
        for entry in files:
            _restore_one(game, entry)
    except PermissionError as exc:
        raise PermissionError(_PERM) from exc
    manifest["files"] = []
    _save_manifest(manifest)
    cfg["hd_enabled"] = False
    cfg["game_dir"] = str(game)
    save_config(cfg)
    return f"已关闭 HD，已还原 {len(files)} 个文件"


def enable(
    game: Path,
    payload_root: Path | None = None,
    check_running: bool = True,
) -> int:
    """Backup then copy payload. Re-enable restores first so originals stay pristine."""
    _guard_running(check_running)
    game = require_game(game)
    files = payload_install.collect_files(payload_root)
    if not files:
        raise FileNotFoundError(
            "payload 里没有可安装的文件。请把重制资源放进 payload/Resources/common-hd 等目录。"
        )
    if hd_enabled() or load_manifest().get("files"):
        disable(check_running=check_running)

    applied: list[dict] = []
    try:
        for rel, src in files:
            applied.append(_apply_one(game, rel, src))
        strings = _clear_expansion_titles(game)
        if strings is not None:
            applied.append(strings)
    except PermissionError as exc:
        for entry in applied:
            _restore_one(game, entry)
        raise PermissionError(_PERM) from exc
    except Exception:
        for entry in applied:
            _restore_one(game, entry)
        raise

    _save_manifest({"version": 1, "game_dir": str(game), "files": applied})
    cfg = load_config()
    cfg["hd_enabled"] = True
    cfg["game_dir"] = str(game)
    save_config(cfg)
    return len(applied)


def uninstall(check_running: bool = True) -> str:
    message = disable(check_running=check_running)
    if CONFIG_DIR.exists():
        shutil.rmtree(CONFIG_DIR)
    return message + "；已清除本机 HD 配置与备份"


def status(game: Path | None = None, payload_root: Path | None = None) -> dict:
    cfg = load_config()
    manifest = load_manifest()
    try:
        payload_count = len(payload_install.collect_files(payload_root))
    except FileNotFoundError:
        payload_count = 0
    resolved = None
    if game is not None:
        resolved = str(game)
    elif cfg.get("game_dir"):
        resolved = cfg["game_dir"]
    return {
        "game_dir": resolved,
        "payload_files": payload_count,
        "hd_enabled": bool(cfg.get("hd_enabled")),
        "overlay_count": len(manifest.get("files") or []),
    }
