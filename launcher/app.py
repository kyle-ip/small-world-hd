#!/usr/bin/env python3
"""Small World 2 HD pack — launcher.

Enable copies payload files over the game after backing originals up.
Disable restores those originals. Launch does not change the HD switch.
"""
from __future__ import annotations

import ctypes
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

if getattr(sys, "frozen", False):
    HERE = Path(sys.executable).resolve().parent
else:
    HERE = Path(__file__).resolve().parent
    sys.path.insert(0, str(HERE))

import overlay  # noqa: E402
import steam_find  # noqa: E402

APP_TITLE = "小小世界 · HD 画质"
APP_VERSION = "1.2.1"
BG = "#ffffff"
SIDE = "#e8f2fc"
TEXT = "#1a1a1a"
MUTED = "#5c5c5c"
ACCENT = "#3278c8"
# Right panel content width (logical px before DPI scale). Matches SmallWorld-cn.
MAIN_WIDTH = 420
MAIN_HEIGHT = 400


def _dpi_scale() -> float:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
    try:
        return max(1.0, float(ctypes.windll.user32.GetDpiForSystem()) / 96.0)
    except Exception:
        return 1.0


def _font(scale: float, size: int, bold: bool = False):
    return ("Microsoft YaHei UI", max(9, int(round(size * scale))), "bold" if bold else "normal")


def _bundled_file(name: str) -> Path | None:
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", ""))
        candidates.append(meipass / name)
        candidates.append(HERE / name)
    candidates.append(Path(__file__).resolve().parent / name)
    for path in candidates:
        if path.is_file():
            return path
    return None


def _resolve_game_dir() -> Path:
    try:
        game = steam_find.find_game_dir()
        if (game / "SmallWorld.exe").is_file():
            return game
    except Exception:
        pass
    picked = filedialog.askdirectory(title="请选择 Small World 2 游戏根目录（含 SmallWorld.exe）")
    if not picked:
        raise FileNotFoundError("未选择游戏目录")
    game = Path(picked)
    if not (game / "SmallWorld.exe").is_file():
        raise FileNotFoundError("该目录下没有 SmallWorld.exe")
    return game


def do_enable() -> str:
    game = _resolve_game_dir()
    count = overlay.enable(game)
    return f"已启用 HD（{count} 个文件）。\n可从 Steam 启动，或点「启动游戏」。"


def do_disable() -> str:
    if not overlay.hd_enabled() and not overlay.load_manifest().get("files"):
        overlay.disable()
        return "HD 未启用，无需还原。"
    return overlay.disable() + "。\n请重新启动游戏使其生效。"


def do_launch() -> None:
    if not overlay.hd_enabled():
        do_enable()
    steam_find.launch_game()


def do_uninstall() -> str:
    return overlay.uninstall()


def _run_cli(argv: list[str]) -> int:
    if "--enable" in argv or "--install" in argv:
        print(do_enable())
        return 0
    if "--disable" in argv:
        print(overlay.disable())
        return 0
    if "--launch" in argv:
        do_launch()
        return 0
    if "--uninstall" in argv:
        print(do_uninstall())
        return 0
    if "--status" in argv:
        try:
            game = steam_find.find_game_dir()
        except Exception:
            game = None
        info = overlay.status(game)
        print(
            f"game={info['game_dir']} payload={info['payload_files']} "
            f"enabled={info['hd_enabled']} overlay={info['overlay_count']}"
        )
        return 0
    return -1


class App(tk.Tk):
    def __init__(self, scale: float) -> None:
        super().__init__()
        self.scale = scale
        self._busy = False
        self._photo_icons: list[tk.PhotoImage] = []
        self._cover_photo: tk.PhotoImage | None = None
        self.title(APP_TITLE)
        self.resizable(False, False)
        self.configure(bg=BG)
        try:
            self.tk.call("tk", "scaling", 1.0)
        except tk.TclError:
            pass
        self._apply_window_icon()
        self._build()
        self._refresh()

    def _apply_window_icon(self) -> None:
        ico = _bundled_file("app.ico")
        if not ico:
            return
        try:
            self.iconbitmap(default=str(ico))
            self.iconbitmap(str(ico))
        except tk.TclError:
            pass
        try:
            from PIL import Image, ImageTk

            img = Image.open(ico)
            frames: list[Image.Image] = []
            try:
                while True:
                    frames.append(img.copy().convert("RGBA"))
                    img.seek(img.tell() + 1)
            except EOFError:
                pass
            if not frames:
                frames = [img.convert("RGBA")]
            frames.sort(key=lambda im: im.size[0])
            photos = [ImageTk.PhotoImage(im) for im in frames[-3:]]
            self._photo_icons = photos
            if photos:
                self.iconphoto(True, *photos)
        except Exception:
            pass

    def _load_cover(self, height_px: int) -> tuple[tk.PhotoImage | None, int, int]:
        path = _bundled_file("cover.png")
        if not path:
            return None, int(120 * self.scale), height_px
        try:
            from PIL import Image, ImageTk

            img = Image.open(path).convert("RGBA")
            ow, oh = img.size
            if oh <= 0:
                return None, int(120 * self.scale), height_px
            side_h = max(1, height_px)
            side_w = max(1, int(round(side_h * (ow / oh))))
            img = img.resize((side_w, side_h), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img), side_w, side_h
        except Exception:
            return None, int(120 * self.scale), height_px

    def _build(self) -> None:
        scale = self.scale
        main_w = int(MAIN_WIDTH * scale)
        main_h = int(MAIN_HEIGHT * scale)
        cover, side_w, side_h = self._load_cover(main_h)
        self._cover_photo = cover
        win_w = side_w + main_w
        win_h = max(side_h, main_h)
        self.geometry(f"{win_w}x{win_h}")
        self.minsize(win_w, win_h)

        root = tk.Frame(self, bg=BG)
        root.pack(fill="both", expand=True)

        side = tk.Frame(root, bg=SIDE, width=side_w, height=win_h)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        if cover is not None:
            tk.Label(side, image=cover, bg=SIDE, borderwidth=0, highlightthickness=0).place(
                x=0, y=0, width=side_w, height=side_h
            )
        else:
            tk.Label(side, text="HD", font=_font(scale, 28, True), bg=SIDE, fg=ACCENT).place(
                relx=0.5, rely=0.42, anchor="center"
            )

        main = tk.Frame(root, bg=BG, width=main_w)
        main.pack(side="left", fill="both", expand=True, padx=int(28 * scale), pady=int(22 * scale))

        tk.Label(
            main,
            text="小小世界 HD 画质包",
            font=_font(scale, 18, True),
            bg=BG,
            fg=TEXT,
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            main,
            text="启用时备份原图并覆盖画质资源，\n关闭时按备份还原。不修改中文语言包。",
            font=_font(scale, 10),
            bg=BG,
            fg=MUTED,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(int(8 * scale), int(12 * scale)))

        self.status = tk.Label(
            main, text="", font=_font(scale, 11), bg=BG, fg=TEXT, justify="left", anchor="w"
        )
        self.status.pack(fill="x", pady=(0, int(8 * scale)))

        self.progress_label = tk.Label(main, text="", font=_font(scale, 9), bg=BG, fg=MUTED, anchor="w")
        self.progress = ttk.Progressbar(main, mode="indeterminate", length=int(360 * scale))

        btn = tk.Frame(main, bg=BG)
        btn.pack(fill="x", side="bottom")

        self.btn_launch = tk.Button(
            btn,
            text="启动游戏",
            command=self._on_launch,
            font=_font(scale, 11),
            bg=ACCENT,
            fg="#ffffff",
            activebackground="#2860a0",
            activeforeground="#ffffff",
            relief="flat",
            padx=int(14 * scale),
            pady=int(8 * scale),
            cursor="hand2",
        )
        self.btn_launch.pack(side="left")

        self.btn_toggle = tk.Button(
            btn,
            text="启用 HD",
            command=self._on_toggle,
            font=_font(scale, 11),
            relief="groove",
            padx=int(12 * scale),
            pady=int(8 * scale),
            cursor="hand2",
        )
        self.btn_toggle.pack(side="left", padx=(int(8 * scale), 0))

        tk.Button(
            btn,
            text="退出",
            command=self.destroy,
            font=_font(scale, 11),
            relief="groove",
            padx=int(12 * scale),
            pady=int(8 * scale),
            cursor="hand2",
        ).pack(side="right")

        tk.Label(
            main,
            text=f"v{APP_VERSION} · 单文件整合版 · 非官方学习用",
            font=_font(scale, 8),
            bg=BG,
            fg="#999999",
            anchor="w",
        ).pack(side="bottom", fill="x", pady=(int(10 * scale), 0))

    def _refresh(self) -> None:
        try:
            game = steam_find.find_game_dir()
        except Exception as exc:  # noqa: BLE001
            self.status.configure(text=f"尚未定位到游戏（启用时可手动选择目录）。\n{exc}")
            self.btn_toggle.configure(text="启用 HD")
            return
        info = overlay.status(game)
        state = "已启用" if info["hd_enabled"] else "未启用"
        if info["hd_enabled"]:
            state += f"（{info['overlay_count']} 个文件）"
        lines = [
            f"游戏目录：{game}",
            f"画质资源：{info['payload_files']} 个文件",
            f"HD 状态：{state}",
        ]
        self.status.configure(text="\n".join(lines))
        self.btn_toggle.configure(text="关闭 HD" if info["hd_enabled"] else "启用 HD")

    def _set_busy(self, busy: bool, message: str = "") -> None:
        self._busy = busy
        state = "disabled" if busy else "normal"
        self.btn_launch.configure(state=state)
        self.btn_toggle.configure(state=state)
        if busy:
            self.progress_label.configure(text=message or "处理中，请稍候…")
            self.progress_label.pack(fill="x", pady=(0, 4))
            self.progress.pack(fill="x", pady=(0, 12))
            self.progress.start(12)
        else:
            self.progress.stop()
            self.progress.pack_forget()
            self.progress_label.pack_forget()
            self.progress_label.configure(text="")

    def _run_async(self, message: str, work, on_ok) -> None:
        if self._busy:
            return
        self._set_busy(True, message)
        self.update_idletasks()

        def worker() -> None:
            err: BaseException | None = None
            result = None
            try:
                result = work()
            except BaseException as exc:  # noqa: BLE001
                err = exc
            self.after(0, lambda: self._finish_async(err, result, on_ok))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_async(self, err, result, on_ok) -> None:
        self._set_busy(False)
        self._refresh()
        if err is not None:
            messagebox.showerror(APP_TITLE, str(err), parent=self)
            return
        on_ok(result)

    def _on_toggle(self) -> None:
        if overlay.hd_enabled():
            self._run_async(
                "正在关闭 HD 并还原原文件…",
                do_disable,
                lambda msg: messagebox.showinfo(APP_TITLE, msg, parent=self),
            )
        else:
            self._run_async(
                "正在备份并启用 HD（文件较多时请稍候）…",
                do_enable,
                lambda msg: messagebox.showinfo(APP_TITLE, msg, parent=self),
            )

    def _on_launch(self) -> None:
        enabled = overlay.hd_enabled()
        msg = "正在启动游戏（HD 已启用）…" if enabled else "正在启动游戏（未启用 HD）…"
        self._run_async(msg, lambda: (do_launch(), None)[1], lambda _r: self.after(400, self.destroy))


def main() -> None:
    code = _run_cli(sys.argv[1:])
    if code >= 0:
        sys.exit(code)
    App(_dpi_scale()).mainloop()


if __name__ == "__main__":
    main()
