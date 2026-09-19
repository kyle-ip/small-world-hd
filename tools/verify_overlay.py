#!/usr/bin/env python3
"""Prove enable/disable restores bytes, then optionally round-trip the real install."""
from __future__ import annotations

import hashlib
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "launcher"))

import overlay  # noqa: E402
import payload_install  # noqa: E402

GAME = ROOT.parent
TOKENS = ("AmazonToken.png", "DwarfToken.png")
CONTROL = "ElfToken.png"
_STOCK_CONFIG = (
    overlay.CONFIG_DIR,
    overlay.CONFIG_PATH,
    overlay.MANIFEST_PATH,
    overlay.BACKUP_ROOT,
)


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _expect(cond: bool, message: str) -> None:
    if not cond:
        raise SystemExit(f"FAIL {message}")
    print(f"OK {message}")


def _use_isolated_config(tmp: Path) -> None:
    overlay.CONFIG_DIR = tmp / "cfg"
    overlay.CONFIG_PATH = overlay.CONFIG_DIR / "config.json"
    overlay.MANIFEST_PATH = overlay.CONFIG_DIR / "manifest.json"
    overlay.BACKUP_ROOT = overlay.CONFIG_DIR / "backup"


def _restore_stock_config() -> None:
    (
        overlay.CONFIG_DIR,
        overlay.CONFIG_PATH,
        overlay.MANIFEST_PATH,
        overlay.BACKUP_ROOT,
    ) = _STOCK_CONFIG


def test_rejects_language_pack() -> None:
    for rel in (
        "en.lproj/common-hd/x.png",
        "common-hd/../../SmallWorld.exe",
        "shader/compile.sh",
        "fonts/arialmt.ttf",
    ):
        try:
            payload_install.validate_rel(rel)
        except ValueError:
            continue
        raise SystemExit(f"FAIL should reject {rel}")
    print("OK whitelist rejects lproj, traversal, scripts, fonts")


def test_roundtrip() -> None:
    src_token = GAME / "Resources" / "common-hd" / TOKENS[0]
    control_src = GAME / "Resources" / "common-hd" / CONTROL
    _expect(src_token.is_file(), f"stock token exists {src_token.name}")
    with tempfile.TemporaryDirectory(prefix="sw2hd-") as raw:
        tmp = Path(raw)
        try:
            _use_isolated_config(tmp)
            game = tmp / "game"
            payload = tmp / "payload"
            (game / "Resources" / "common-hd").mkdir(parents=True)
            (game / "SmallWorld.exe").write_bytes(b"fake")
            original = src_token.read_bytes()
            (game / "Resources" / "common-hd" / TOKENS[0]).write_bytes(original)
            (game / "Resources" / "common-hd" / CONTROL).write_bytes(control_src.read_bytes())
            token_dir = payload / "common-hd"
            token_dir.mkdir(parents=True)
            patched = original + b"\x00hd-pilot"
            (token_dir / TOKENS[0]).write_bytes(patched)
            (token_dir / "BrandNewToken.png").write_bytes(b"\x89PNG-new")

            count = overlay.enable(game, payload, check_running=False)
            _expect(count == 2, "enable copies two payload files")
            dest = game / "Resources" / "common-hd" / TOKENS[0]
            _expect(dest.read_bytes() == patched, "enabled file matches payload")
            _expect(
                (game / "Resources" / "common-hd" / CONTROL).read_bytes() == control_src.read_bytes(),
                "unlisted file unchanged",
            )
            backup = overlay.BACKUP_ROOT / "common-hd" / TOKENS[0]
            backup_bytes = backup.read_bytes()
            _expect(backup_bytes == original, "backup is the original")

            overlay.enable(game, payload, check_running=False)
            _expect(backup.read_bytes() == backup_bytes, "re-enable does not overwrite backup")

            overlay.disable(check_running=False)
            _expect(dest.read_bytes() == original, "disable restores original bytes")
            _expect(
                not (game / "Resources" / "common-hd" / "BrandNewToken.png").exists(),
                "added file removed",
            )
            _expect(not overlay.hd_enabled(), "flag cleared")

            overlay.enable(game, payload, check_running=False)
            overlay.uninstall(check_running=False)
            _expect(dest.read_bytes() == original, "uninstall restores original")
            _expect(not overlay.CONFIG_DIR.exists(), "uninstall removes config dir")
        finally:
            _restore_stock_config()


def test_pilot_dimensions() -> None:
    stock = GAME / "Resources" / "common-hd"
    payload = ROOT / "payload" / "Resources" / "common-hd"
    for name in TOKENS:
        src = stock / name
        dst = payload / name
        _expect(dst.is_file(), f"pilot present {name}")
        _expect(_sha(src) != _sha(dst), f"pilot differs from stock {name}")
        # Dimensions live in the PNG IHDR; Pillow is already required for make_pilot.
        from PIL import Image

        with Image.open(src) as a, Image.open(dst) as b:
            _expect(a.size == b.size, f"same size {name} {a.size[0]}x{a.size[1]}")


def _can_write(directory: Path) -> bool:
    probe = directory / ".sw2hd-probe"
    try:
        probe.write_bytes(b"")
        probe.unlink()
        return True
    except OSError:
        if probe.exists():
            try:
                probe.unlink()
            except OSError:
                pass
        return False


def live_roundtrip() -> None:
    """Enable on the real install, then always disable."""
    if overlay.game_process_running():
        print("SKIP live: SmallWorld.exe is running")
        return
    target = GAME / "Resources" / "common-hd"
    if not _can_write(target):
        print("SKIP live: cannot write Resources (run the launcher as administrator)")
        return
    before = {name: _sha(target / name) for name in (*TOKENS, CONTROL)}
    payload = ROOT / "payload" / "Resources"
    # Live test uses the real LOCALAPPDATA config. Isolate if a user overlay is already on.
    if overlay.hd_enabled():
        print("SKIP live: HD already enabled; not touching the active overlay")
        return
    try:
        count = overlay.enable(GAME, payload, check_running=True)
        _expect(count >= 2, f"live enable wrote {count} files")
        for name in TOKENS:
            _expect(_sha(target / name) != before[name], f"live token changed {name}")
        _expect(_sha(target / CONTROL) == before[CONTROL], "live control token unchanged")
    finally:
        if overlay.hd_enabled() or overlay.load_manifest().get("files"):
            overlay.disable(check_running=True)
    for name, digest in before.items():
        _expect(_sha(target / name) == digest, f"live restore {name}")
    _expect(not overlay.hd_enabled(), "live flag off")


def main() -> None:
    os.chdir(ROOT)
    test_rejects_language_pack()
    test_roundtrip()
    test_pilot_dimensions()
    if "--no-live" not in sys.argv[1:]:
        live_roundtrip()
    print("ALL PASSED")


if __name__ == "__main__":
    main()
