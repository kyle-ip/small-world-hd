#!/usr/bin/env python3
"""Extract the icon from SmallWorld.exe for the launcher window."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT.parent / "SmallWorld.exe"
OUT = Path(__file__).resolve().parent / "app.ico"


def main() -> None:
    from icoextract import IconExtractor

    if not EXE.is_file():
        raise SystemExit(f"找不到: {EXE}")
    IconExtractor(str(EXE)).export_icon(str(OUT), num=0)
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
