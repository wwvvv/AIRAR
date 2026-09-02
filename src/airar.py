"""AIRAR v1.0.1 - 面向 Windows 的智能递归解压与游戏文件整理工具。"""

from __future__ import annotations

import os
import json
import fnmatch
import re
import shutil
import threading
import traceback
import webbrowser
import ctypes
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from PIL import Image, ImageEnhance, ImageOps, ImageTk


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / relative


def import_dependency(module_name: str):
    """尝试导入依赖库，并返回（模块、是否成功）。"""
    try:
        module = __import__(module_name)
        return module, True
    except ImportError:
        return None, False


filetype, filetype_ok = import_dependency("filetype")
patoolib, patoolib_ok = import_dependency("patoolib")
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    DND_FILES = None
    TkinterDnD = None


SUPPORTED_ARCHIVES = {
    ".zip": {
        "mime": "application/zip",
        "headers": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
        "description": "ZIP 压缩文件",
    },
    ".rar": {
        "mime": "application/x-rar-compressed",
        "headers": [b"Rar!\x1a\x07\x00", b"Rar!\x1a\x07\x01\x00"],
        "description": "RAR 压缩文件",
    },
    ".7z": {
        "mime": "application/x-7z-compressed",
        "headers": [b"7z\xbc\xaf\x27\x1c"],
        "description": "7-Zip 压缩文件",
    },
    ".tar": {
        "mime": "application/x-tar",
        "headers": [],
        "description": "TAR 归档文件",
    },
    ".gz": {
        "mime": "application/gzip",
        "headers": [b"\x1f\x8b\x08"],
        "description": "GZIP 压缩文件",
    },
    ".bz2": {
        "mime": "application/x-bzip2",
        "headers": [b"BZh"],
        "description": "BZIP2 压缩文件",
    },
}

ZIP_CONTAINER_SUFFIXES = {
    ".apk", ".xlsx", ".xlsm", ".docx", ".pptx", ".jar", ".epub",
    ".odt", ".ods", ".odp", ".whl", ".xpi", ".vsix",
}
GAME_RESOURCE_SUFFIXES = {
    ".save", ".sav", ".rpa", ".rpy", ".rpyc", ".pak", ".assets",
    ".unity3d", ".dll", ".exe",
}
GAME_RESOURCE_NAMES = {"persistent"}
PART_RAR_RE = re.compile(r"^(?P<base>.+)\.part(?P<num>\d+)\.rar$", re.IGNORECASE)
APP_VERSION = "1.0.1"


class SmartUnpackerGUI:
    def __init__(self) -> None:
        self.root = TkinterDnD.Tk() if TkinterDnD else tk.Tk()
        self.root.title("AIRAR（智能解压工具）")
        self.root.geometry("1320x850")
        self.root.minsize(1080, 700)
        try:
            self.root.iconbitmap(default=str(resource_path("assets/AIRAR.ico")))
            self.window_icon = tk.PhotoImage(file=str(resource_path("assets/icon.png")))
            self.root.iconphoto(True, self.window_icon)
        except Exception:
            pass

        self.is_processing = False
        self.password_for_run = ""
        self.passwords_for_run: list[str] = []
        self.settings_path = Path(os.getenv("APPDATA", str(Path.home()))) / "AIRAR" / "settings.json"
        self.settings = self.load_settings()
        self.session_extract_roots: set[Path] = set()
        self.destination_dir: Path | None = None
        self.last_output_dir: Path | None = None
        self.initial_input_files: set[Path] = set()
        self.successfully_extracted_archives: set[Path] = set()
        self.stats = {
            "archives_found": 0,
            "archives_extracted": 0,
            "files_renamed": 0,
            "errors": 0,
            "deleted_archives": 0,
            "merged_folders": 0,
        }
        self.setup_ui()
        self.center_window()

    def load_settings(self) -> dict:
        defaults = {"passwords": [], "ad_rules": ["广告*", "*推广*", "网址*", "*.url"]}
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            return {**defaults, **data}
        except Exception:
            return defaults

    def save_settings(self, passwords: list[str], ad_rules: list[str]) -> None:
        self.settings = {"passwords": passwords, "ad_rules": ad_rules}
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding="utf-8")

    def center_window(self) -> None:
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = self.root.winfo_screenwidth() // 2 - width // 2
        y = self.root.winfo_screenheight() // 2 - height // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def setup_ui(self) -> None:
        """构建奶油绿二次元双栏界面。"""
        C = {
            "shell": "#e8eee5", "sidebar": "#eef3e9", "paper": "#fbfaf6",
            "panel": "#fffefd", "ink": "#183f34", "muted": "#6f837b",
            "line": "#cbd8ce", "green": "#4d8b73", "green2": "#39745f",
            "soft": "#f1f5ef", "log": "#10241f", "log_text": "#b9dccb",
        }
        self.colors = C
        self.root.configure(bg=C["shell"])
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("AIRAR.Horizontal.TProgressbar", troughcolor="#e5e8e3", background=C["green"], borderwidth=0, thickness=9)
        style.configure("Anime.TCheckbutton", background=C["panel"], foreground=C["ink"], font=("Microsoft YaHei UI", 9))
        style.map("Anime.TCheckbutton", background=[("active", C["panel"])])

        shell = tk.Frame(self.root, bg=C["shell"], padx=10, pady=10)
        shell.pack(fill="both", expand=True)
        shell.grid_rowconfigure(0, weight=1)
        shell.grid_columnconfigure(1, weight=1)

        # 左侧插画品牌栏
        sidebar = tk.Canvas(shell, width=276, bg=C["sidebar"], bd=0, highlightthickness=0)
        sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        sidebar.grid_propagate(False)
        self.sidebar_canvas = sidebar
        try:
            art = Image.open(resource_path("assets/airar_mascot.png")).convert("RGB")
            art = ImageOps.fit(art, (276, 810), method=Image.Resampling.LANCZOS, centering=(0.5, 0.49))
            art = ImageEnhance.Brightness(art).enhance(1.035)
            self.sidebar_art = ImageTk.PhotoImage(art)
            sidebar.create_image(0, 0, image=self.sidebar_art, anchor="nw")
        except Exception:
            sidebar.create_rectangle(0, 0, 276, 810, fill=C["sidebar"], outline="")

        sidebar.create_rectangle(0, 0, 276, 138, fill="#edf3e9", outline="", stipple="gray75")
        sidebar.create_text(27, 26, text="AIRAR", anchor="nw", fill=C["ink"], font=("Microsoft YaHei UI", 29, "bold"))
        sidebar.create_text(29, 78, text=f"智能解压工具 · v{APP_VERSION}", anchor="nw", fill="#406859", font=("Microsoft YaHei UI", 9))
        sidebar.create_text(234, 31, text="❧", fill="#769c82", font=("Segoe UI Symbol", 25))

        side_buttons = tk.Frame(sidebar, bg="#edf3e9")
        sidebar.create_window(138, 690, window=side_buttons, width=218)
        update_btn = tk.Button(side_buttons, text="☁  检查更新", command=lambda: webbrowser.open("https://www.acgxx.com"),
                               bg="#f8faf5", fg=C["green2"], activebackground="#e7f0e7", activeforeground=C["ink"],
                               bd=0, relief="flat", cursor="hand2", font=("Microsoft YaHei UI", 11, "bold"), pady=12)
        update_btn.pack(fill="x", pady=(0, 9))
        settings_btn = tk.Button(side_buttons, text="⚙  设置", command=self.open_settings,
                                 bg="#f8faf5", fg=C["green2"], activebackground="#e7f0e7", activeforeground=C["ink"],
                                 bd=0, relief="flat", cursor="hand2", font=("Microsoft YaHei UI", 11, "bold"), pady=12)
        settings_btn.pack(fill="x")

        # 右侧工作台
        main = tk.Frame(shell, bg=C["paper"], padx=24, pady=22, highlightbackground="#dae2da", highlightthickness=1)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(6, weight=1)

        drop = tk.Canvas(main, height=186, bg=C["panel"], bd=0, highlightthickness=0, cursor="hand2")
        drop.grid(row=0, column=0, sticky="ew")
        self.drop_canvas = drop
        def redraw_drop(event=None):
            w=max(drop.winfo_width(), 500); h=max(drop.winfo_height(), 186)
            drop.delete("design")
            drop.create_rectangle(8, 8, w-8, h-8, outline="#9db9aa", width=1, dash=(5, 4), tags="design")
            drop.create_text(w/2, 57, text="⇩", fill=C["green"], font=("Segoe UI Symbol", 35, "bold"), tags="design")
            drop.create_text(w/2, 111, text="拖入压缩文件或文件夹", fill=C["green2"], font=("Microsoft YaHei UI", 15, "bold"), tags="design")
            drop.create_text(w/2, 143, text="也可以点击下方按钮选择", fill=C["muted"], font=("Microsoft YaHei UI", 9), tags="design")
            drop.create_text(48, 48, text="✦", fill="#c0d5c4", font=("Segoe UI Symbol", 18), tags="design")
            drop.create_text(w-64, 127, text="❧", fill="#bdd0bd", font=("Segoe UI Symbol", 25), tags="design")
        drop.bind("<Configure>", redraw_drop)
        drop.bind("<Button-1>", lambda _e: self.select_file())
        if DND_FILES:
            drop.drop_target_register(DND_FILES)
            drop.dnd_bind("<<Drop>>", self.on_drop)
        else:
            self.root.after_idle(self.enable_native_drop)

        pathrow = tk.Frame(main, bg=C["paper"])
        pathrow.grid(row=1, column=0, sticky="ew", pady=(16, 12))
        pathrow.grid_columnconfigure(0, weight=1)
        self.path_var = tk.StringVar()
        self.path_entry = tk.Entry(pathrow, textvariable=self.path_var, bg="#ffffff", fg=C["ink"],
                                   insertbackground=C["green"], relief="flat", highlightthickness=1,
                                   highlightbackground="#a9c1b4", highlightcolor=C["green"],
                                   font=("Microsoft YaHei UI", 10))
        self.path_entry.grid(row=0, column=0, sticky="ew", ipady=11)
        self.path_entry.insert(0, "")
        tk.Button(pathrow, text="选择文件", command=self.select_file, bg="#f4f7f2", fg=C["green2"],
                  activebackground="#e3eee6", bd=0, highlightthickness=1, highlightbackground="#aac0b4",
                  font=("Microsoft YaHei UI", 10, "bold"), padx=24, pady=10, cursor="hand2").grid(row=0, column=1, padx=(12, 8))
        tk.Button(pathrow, text="选择文件夹", command=self.select_folder, bg="#f4f7f2", fg=C["green2"],
                  activebackground="#e3eee6", bd=0, highlightthickness=1, highlightbackground="#aac0b4",
                  font=("Microsoft YaHei UI", 10, "bold"), padx=20, pady=10, cursor="hand2").grid(row=0, column=2)

        password_card = tk.Frame(main, bg=C["panel"], padx=18, pady=13, highlightbackground="#e0e4df", highlightthickness=1)
        password_card.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        password_card.grid_columnconfigure(0, weight=1)
        tk.Label(password_card, text="▣  本次优先密码", bg=C["panel"], fg=C["ink"], font=("Microsoft YaHei UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 8))
        passrow = tk.Frame(password_card, bg=C["panel"])
        passrow.grid(row=1, column=0, sticky="ew"); passrow.grid_columnconfigure(0, weight=1)
        self.password_var = tk.StringVar(); self.show_password_var = tk.BooleanVar(value=False)
        self.password_entry = tk.Entry(passrow, textvariable=self.password_var, show="●", bg="#fbfbfa", fg=C["ink"],
                                       relief="flat", highlightthickness=1, highlightbackground="#d3d9d4",
                                       highlightcolor=C["green"], font=("Microsoft YaHei UI", 10))
        self.password_entry.grid(row=0, column=0, sticky="ew", ipady=8)
        ttk.Checkbutton(passrow, text="显示密码", variable=self.show_password_var, command=self.toggle_password_visibility,
                        style="Anime.TCheckbutton").grid(row=0, column=1, padx=(12, 0))
        tk.Label(password_card, text="留空时自动尝试设置中的默认密码", bg=C["panel"], fg=C["muted"], font=("Microsoft YaHei UI", 9)).grid(row=2, column=0, sticky="w", pady=(8, 0))

        actions = tk.Frame(main, bg=C["paper"])
        actions.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        for col in range(3): actions.grid_columnconfigure(col, weight=1, uniform="action")
        self.start_button = tk.Button(actions, text="▷  开始智能解压\n    自动识别 · 解压 · 整理", command=self.start_unpack,
                                      bg=C["green"], fg="#ffffff", activebackground=C["green2"], activeforeground="#ffffff",
                                      bd=0, relief="flat", font=("Microsoft YaHei UI", 11, "bold"), pady=10, cursor="hand2")
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.stop_button = tk.Button(actions, text="■  停止\n    终止当前任务", command=self.stop_unpack, state=tk.DISABLED,
                                     bg="#f4f3ef", fg="#aeb4b0", disabledforeground="#b7bbb8", activebackground="#eceeea",
                                     bd=0, relief="flat", font=("Microsoft YaHei UI", 10), pady=10)
        self.stop_button.grid(row=0, column=1, sticky="ew", padx=4)
        self.open_button = tk.Button(actions, text="▱  打开当前目录\n    查看解压输出", command=self.open_output_dir,
                                     bg="#f7f7f3", fg="#7f8b85", activebackground="#e9eeea", activeforeground=C["green2"],
                                     bd=0, relief="flat", font=("Microsoft YaHei UI", 10), pady=10, cursor="hand2")
        self.open_button.grid(row=0, column=2, sticky="ew", padx=(8, 0))

        progressrow = tk.Frame(main, bg=C["paper"])
        progressrow.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        progressrow.grid_columnconfigure(1, weight=1)
        tk.Label(progressrow, text="⌁  解压进度", bg=C["paper"], fg=C["ink"], font=("Microsoft YaHei UI", 9, "bold")).grid(row=0, column=0, padx=(0, 12))
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progressrow, variable=self.progress_var, maximum=100, style="AIRAR.Horizontal.TProgressbar")
        self.progress_bar.grid(row=0, column=1, sticky="ew")
        self.progress_label = tk.StringVar(value="0%")
        tk.Label(progressrow, textvariable=self.progress_label, bg=C["paper"], fg=C["ink"], font=("Microsoft YaHei UI", 9, "bold"), width=5).grid(row=0, column=2, padx=(8, 0))
        self.progress_var.trace_add("write", lambda *_: self.progress_label.set(f"{int(self.progress_var.get())}%"))

        self.status_var = tk.StringVar(value="等待任务开始…")
        statusbar = tk.Frame(main, bg=C["log"])
        statusbar.grid(row=5, column=0, sticky="ew")
        tk.Label(statusbar, text="▣", bg=C["log"], fg="#75b894", font=("Segoe UI Symbol", 11)).pack(side="left", padx=(14, 7), pady=(9, 4))
        tk.Label(statusbar, textvariable=self.status_var, bg=C["log"], fg=C["log_text"], font=("Microsoft YaHei UI", 9)).pack(side="left", pady=(9, 4))
        self.log_text = scrolledtext.ScrolledText(main, height=10, wrap=tk.WORD, bg=C["log"], fg="#c9e2d5",
                                                  insertbackground="#ffffff", selectbackground=C["green2"], relief="flat",
                                                  bd=0, padx=14, pady=8, font=("Cascadia Mono", 9))
        self.log_text.grid(row=6, column=0, sticky="nsew")

        stats = tk.Frame(main, bg=C["paper"])
        stats.grid(row=7, column=0, sticky="ew", pady=(10, 0))
        self.stats_vars = {}
        for i, (label, key) in enumerate([("发现", "archives_found"), ("成功", "archives_extracted"), ("删除中间包", "deleted_archives"), ("错误", "errors")]):
            tk.Label(stats, text=label, bg=C["paper"], fg=C["muted"], font=("Microsoft YaHei UI", 9)).pack(side="left")
            self.stats_vars[key] = tk.StringVar(value="0")
            tk.Label(stats, textvariable=self.stats_vars[key], bg=C["paper"], fg=C["ink"], font=("Microsoft YaHei UI", 10, "bold")).pack(side="left", padx=(5, 22))

    def on_drop(self, event) -> None:
        paths = self.root.tk.splitlist(event.data)
        if paths:
            self.path_var.set(paths[0])
            self.status_var.set("已接收拖入项目")

    def enable_native_drop(self) -> None:
        """在未安装 TkDND 时使用 Windows WM_DROPFILES 原生拖放。"""
        if os.name != "nt":
            return
        WM_DROPFILES = 0x0233
        GWL_WNDPROC = -4
        hwnd = self.root.winfo_id()
        user32, shell32 = ctypes.windll.user32, ctypes.windll.shell32
        LRESULT = ctypes.c_ssize_t
        WNDPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t)
        get_long = user32.GetWindowLongPtrW
        set_long = user32.SetWindowLongPtrW
        get_long.restype = ctypes.c_void_p
        set_long.restype = ctypes.c_void_p
        user32.CallWindowProcW.restype = LRESULT
        self._old_wndproc = get_long(hwnd, GWL_WNDPROC)

        @WNDPROC
        def wndproc(window, message, wparam, lparam):
            if message == WM_DROPFILES:
                length = shell32.DragQueryFileW(wparam, 0, None, 0)
                buffer = ctypes.create_unicode_buffer(length + 1)
                shell32.DragQueryFileW(wparam, 0, buffer, length + 1)
                shell32.DragFinish(wparam)
                self.root.after(0, lambda value=buffer.value: (self.path_var.set(value), self.status_var.set("已接收拖入项目")))
                return 0
            return user32.CallWindowProcW(self._old_wndproc, window, message, wparam, lparam)

        self._wndproc = wndproc
        set_long(hwnd, GWL_WNDPROC, ctypes.cast(wndproc, ctypes.c_void_p).value)
        shell32.DragAcceptFiles(hwnd, True)

    def open_settings(self) -> None:
        C = self.colors
        win = tk.Toplevel(self.root)
        win.title("AIRAR · 设置")
        win.geometry("650x590")
        win.configure(bg=C["paper"])
        win.transient(self.root); win.grab_set()
        body = tk.Frame(win, bg=C["paper"], padx=30, pady=26)
        body.pack(fill="both", expand=True); body.grid_columnconfigure(0, weight=1)
        tk.Label(body, text="自动化规则", bg=C["paper"], fg=C["ink"], font=("Microsoft YaHei UI", 21, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(body, text="设置会保存在当前 Windows 用户目录中", bg=C["paper"], fg=C["muted"], font=("Microsoft YaHei UI", 9)).grid(row=1, column=0, sticky="w", pady=(2, 22))
        tk.Label(body, text="默认密码", bg=C["paper"], fg=C["ink"], font=("Microsoft YaHei UI", 10, "bold")).grid(row=2, column=0, sticky="w")
        tk.Label(body, text="每行一个，AIRAR 将从上到下依次尝试", bg=C["paper"], fg=C["muted"], font=("Microsoft YaHei UI", 9)).grid(row=3, column=0, sticky="w", pady=(2, 7))
        passwords = tk.Text(body, height=7, bg="#ffffff", fg=C["ink"], insertbackground=C["green"],
                            relief="flat", highlightthickness=1, highlightbackground=C["line"],
                            highlightcolor=C["green"], padx=10, pady=8, font=("Cascadia Mono", 10))
        passwords.grid(row=4, column=0, sticky="ew", pady=(0, 18)); passwords.insert("1.0", "\n".join(self.settings.get("passwords", [])))
        tk.Label(body, text="广告文件规则", bg=C["paper"], fg=C["ink"], font=("Microsoft YaHei UI", 10, "bold")).grid(row=5, column=0, sticky="w")
        tk.Label(body, text="每行一个，支持 * 和 ? 通配符", bg=C["paper"], fg=C["muted"], font=("Microsoft YaHei UI", 9)).grid(row=6, column=0, sticky="w", pady=(2, 7))
        ads = tk.Text(body, height=7, bg="#ffffff", fg=C["ink"], insertbackground=C["green"],
                      relief="flat", highlightthickness=1, highlightbackground=C["line"],
                      highlightcolor=C["green"], padx=10, pady=8, font=("Cascadia Mono", 10))
        ads.grid(row=7, column=0, sticky="ew", pady=(0, 20)); ads.insert("1.0", "\n".join(self.settings.get("ad_rules", [])))
        buttons = tk.Frame(body, bg=C["paper"]); buttons.grid(row=8, column=0, sticky="ew")
        tk.Button(buttons, text="☁  检查更新", command=lambda: webbrowser.open("https://www.acgxx.com"),
                  bg="#eef4ed", fg=C["green2"], activebackground="#e0ece2", bd=0,
                  font=("Microsoft YaHei UI", 10, "bold"), padx=18, pady=9, cursor="hand2").pack(side="left")
        def save():
            pw=[x.strip() for x in passwords.get("1.0","end").splitlines() if x.strip()]
            rules=[x.strip() for x in ads.get("1.0","end").splitlines() if x.strip()]
            self.save_settings(pw,rules); win.destroy(); self.status_var.set("设置已保存")
        tk.Button(buttons, text="保存设置", command=save, bg=C["green"], fg="#ffffff",
                  activebackground=C["green2"], activeforeground="#ffffff", bd=0,
                  font=("Microsoft YaHei UI", 10, "bold"), padx=24, pady=9, cursor="hand2").pack(side="right")

    def toggle_password_visibility(self) -> None:
        self.password_entry.configure(show="" if self.show_password_var.get() else "*")

    def _ui(self, callback, *args) -> None:
        """在 Tk 主线程排队执行 UI 更新。"""
        self.root.after(0, callback, *args)

    def _redact_password(self, value: object) -> str:
        """避免把用户填写的密码写入界面日志。"""
        text = str(value)
        for password in getattr(self, "passwords_for_run", []) or ([self.password_for_run] if self.password_for_run else []):
            text = text.replace(password, "***")
        return text

    def log_message(self, message: str) -> None:
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def update_status(self, message: str) -> None:
        self.status_var.set(message)
        self.log_message(f"[状态] {message}")

    def update_stats(self) -> None:
        for key, var in self.stats_vars.items():
            var.set(str(self.stats.get(key, 0)))

    def select_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="选择压缩文件",
            filetypes=[
                ("所有文件", "*.*"),
                ("压缩文件", "*.zip;*.rar;*.7z;*.tar;*.gz;*.bz2"),
                ("ZIP文件", "*.zip"),
                ("RAR文件", "*.rar"),
                ("7Z文件", "*.7z"),
            ],
        )
        if file_path:
            self.path_var.set(file_path)

    def select_folder(self) -> None:
        folder_path = filedialog.askdirectory(title="选择文件夹")
        if folder_path:
            self.path_var.set(folder_path)

    def clear_path(self) -> None:
        self.path_var.set("")

    def open_output_dir(self) -> None:
        path = self.path_var.get()
        if not path:
            return
        target_path = Path(path)
        if self.last_output_dir and self.last_output_dir.exists():
            output_dir = self.last_output_dir
        elif target_path.is_file():
            output_dir = target_path.parent / target_path.stem
        else:
            output_dir = target_path
        if output_dir.exists():
            try:
                os.startfile(output_dir)
            except Exception:
                self.log_message(f"无法打开目录: {output_dir}")
        else:
            messagebox.showinfo("目录不存在", f"输出目录不存在:\n{output_dir}")

    def start_unpack(self) -> None:
        if self.is_processing:
            return
        path = self.path_var.get().strip()
        if not path:
            messagebox.showwarning("路径为空", "请先选择要解压的文件或文件夹！")
            return
        target_path = Path(path)
        if not target_path.exists():
            messagebox.showerror("路径不存在", f"路径不存在:\n{path}")
            return

        password = self.password_var.get()
        password_state = "已填写（将应用到所有嵌套压缩包）" if password else "未填写"
        if not messagebox.askyesno(
            "确认解压", f"确定要开始解压吗？\n\n目标: {path}\n解压密码: {password_state}"
        ):
            return

        candidates = ([password] if password else []) + list(self.settings.get("passwords", []))
        self.passwords_for_run = list(dict.fromkeys(x for x in candidates if x))
        self.password_for_run = self.passwords_for_run[0] if self.passwords_for_run else ""
        self.is_processing = True
        self.last_output_dir = None
        self.stats = {key: 0 for key in self.stats.keys()}
        self.update_stats()
        self.log_text.delete(1.0, tk.END)
        self.progress_var.set(0)
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.password_entry.config(state=tk.DISABLED)
        self.update_status("正在启动解压进程...")
        thread = threading.Thread(target=self.unpack_thread, args=(target_path,), daemon=True)
        thread.start()

    def stop_unpack(self) -> None:
        if self.is_processing:
            self.is_processing = False
            self.update_status("正在停止解压进程...")
            self.stop_button.config(state=tk.DISABLED)

    def unpack_thread(self, target_path: Path) -> None:
        try:
            self._ui(self.update_status, "开始智能解压...")
            success = self.unpack_nested_archives(target_path)
            if success:
                self._ui(self.update_status, "解压完成！")
                self._ui(messagebox.showinfo, "完成", "解压操作已完成！")
            else:
                self._ui(self.update_status, "解压过程遇到错误")
                self._ui(messagebox.showwarning, "警告", "解压过程中遇到一些错误，请查看日志。")
        except Exception as exc:
            self._ui(self.log_message, f"\n[错误] 解压过程异常: {self._redact_password(exc)}")
            self._ui(self.log_message, self._redact_password(traceback.format_exc()))
            self._ui(self.update_status, "解压过程异常终止")
            self._ui(messagebox.showerror, "错误", f"解压过程发生异常:\n{self._redact_password(exc)}")
        finally:
            self._ui(self.reset_ui_state)

    def reset_ui_state(self) -> None:
        self.is_processing = False
        self.password_for_run = ""
        self.passwords_for_run = []
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.password_entry.config(state=tk.NORMAL)
        self.progress_var.set(100)

    def is_archive_file(self, filepath: str | Path) -> str | None:
        filepath = Path(filepath)
        if not filepath.is_file():
            return None
        # Office/OpenDocument、APK、JAR 等本身就是 ZIP 容器，不应当作嵌套压缩包展开。
        if (filepath.suffix.lower() in ZIP_CONTAINER_SUFFIXES
                or filepath.suffix.lower() in GAME_RESOURCE_SUFFIXES
                or filepath.name.casefold() in GAME_RESOURCE_NAMES):
            return None

        if filetype is not None:
            try:
                kind = filetype.guess(str(filepath))
                if kind:
                    for ext, info in SUPPORTED_ARCHIVES.items():
                        if kind.mime == info["mime"]:
                            self.stats["archives_found"] += 1
                            self._ui(self.update_stats)
                            return ext
            except Exception:
                pass

        try:
            with open(filepath, "rb") as handle:
                header = handle.read(20)
            for ext, info in SUPPORTED_ARCHIVES.items():
                if any(header.startswith(pattern) for pattern in info["headers"]):
                    self.stats["archives_found"] += 1
                    self._ui(self.update_stats)
                    return ext
        except Exception:
            pass

        suffix = filepath.suffix.lower()
        if suffix in SUPPORTED_ARCHIVES and filepath.stat().st_size > 0:
            self.stats["archives_found"] += 1
            self._ui(self.update_stats)
            return suffix
        return None

    @staticmethod
    def is_secondary_rar_volume(filepath: str | Path) -> bool:
        path = Path(filepath)
        match = PART_RAR_RE.match(path.name)
        if match:
            return int(match.group("num")) > 1
        return bool(re.search(r"\.r\d{2,3}$", path.name, re.IGNORECASE))

    @staticmethod
    def rar_primary_volume(filepath: str | Path) -> Path:
        path = Path(filepath)
        match = PART_RAR_RE.match(path.name)
        if match:
            width = len(match.group("num"))
            return path.with_name(f"{match.group('base')}.part{1:0{width}d}.rar")
        if re.search(r"\.r\d{2,3}$", path.name, re.IGNORECASE):
            return path.with_suffix(".rar")
        return path

    @staticmethod
    def rar_volume_members(filepath: str | Path) -> set[Path]:
        path = SmartUnpackerGUI.rar_primary_volume(filepath)
        match = PART_RAR_RE.match(path.name)
        if match:
            pattern = re.compile(rf"^{re.escape(match.group('base'))}\.part\d+\.rar$", re.IGNORECASE)
            return {p.resolve() for p in path.parent.iterdir() if p.is_file() and pattern.match(p.name)}
        members = {path.resolve()}
        pattern = re.compile(rf"^{re.escape(path.stem)}\.r\d{{2,3}}$", re.IGNORECASE)
        members.update(p.resolve() for p in path.parent.iterdir() if p.is_file() and pattern.match(p.name))
        return members

    @staticmethod
    def archive_output_stem(filepath: str | Path) -> str:
        path = Path(filepath)
        match = PART_RAR_RE.match(path.name)
        return match.group("base") if match else path.stem

    def restore_and_extract(self, file_path: str | Path, real_extension: str) -> Path | None:
        """恢复伪装扩展名并解压单个文件；成功时返回输出目录。"""
        original_path = Path(file_path)
        need_rename = original_path.suffix.lower() != real_extension.lower()
        temp_path = original_path

        self._ui(self.log_message, f"\n[处理] {original_path}")
        self._ui(self.log_message, f"  真实格式: {real_extension}")

        if need_rename:
            temp_path = original_path.with_suffix(real_extension)
            counter = 1
            while temp_path.exists():
                temp_path = original_path.with_name(f"{original_path.stem}_temp{counter}{real_extension}")
                counter += 1
            try:
                shutil.copy2(original_path, temp_path)
                self._ui(self.log_message, f"  已创建临时文件: {temp_path.name}")
                self.stats["files_renamed"] += 1
                self._ui(self.update_stats)
            except Exception as exc:
                self._ui(self.log_message, f"  [错误] 创建临时文件失败: {exc}")
                return None

        extract_dir_name = self.archive_output_stem(temp_path)
        extract_dir = temp_path.parent / extract_dir_name
        counter = 1
        while extract_dir.exists():
            extract_dir = temp_path.parent / f"{extract_dir_name}_{counter}"
            counter += 1

        try:
            self._ui(self.log_message, f"  解压到: {extract_dir}")
            saved_passwords = getattr(self, "passwords_for_run", None) or ([self.password_for_run] if self.password_for_run else [])
            attempts = saved_passwords + [""] if saved_passwords else [""]
            last_error = None
            for index, password in enumerate(attempts, 1):
                self.password_for_run = password
                try:
                    patoolib.extract_archive(
                        str(temp_path), outdir=str(extract_dir), verbosity=-1,
                        interactive=bool(password), password=password or None,
                    )
                    if password:
                        self._ui(self.log_message, f"  密码匹配成功（候选 {index}）")
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc
                    if extract_dir.exists():
                        shutil.rmtree(extract_dir, ignore_errors=True)
            if last_error is not None:
                raise last_error
            self._ui(self.log_message, "  ✓ 解压成功")
            self.stats["archives_extracted"] += 1
            self._ui(self.update_stats)
            self.last_output_dir = extract_dir
            if not hasattr(self, "session_extract_roots"):
                self.session_extract_roots = set()
            self.session_extract_roots.add(extract_dir.resolve())
            if real_extension.lower() == ".rar":
                self.successfully_extracted_archives.update(self.rar_volume_members(original_path))
            else:
                self.successfully_extracted_archives.add(original_path.resolve())
            return extract_dir if extract_dir.exists() else None
        except Exception as exc:
            self._ui(self.log_message, f"  ✗ 解压失败: {self._redact_password(exc)}")
            self.stats["errors"] += 1
            self._ui(self.update_stats)
            return None
        finally:
            if need_rename and temp_path.exists():
                try:
                    os.remove(temp_path)
                    self._ui(self.log_message, "  已清理临时文件")
                except Exception:
                    pass

    def _matches_ad_rule(self, path: Path) -> bool:
        name = path.name.casefold()
        return any(fnmatch.fnmatch(name, rule.casefold()) for rule in self.settings.get("ad_rules", []))

    @staticmethod
    def _unique_destination(destination: Path) -> Path:
        if not destination.exists():
            return destination
        counter = 1
        while True:
            candidate = destination.with_name(f"{destination.stem}_{counter}{destination.suffix}")
            if not candidate.exists():
                return candidate
            counter += 1

    def organize_game_outputs(self) -> None:
        """仅提取游戏目录和 APK 到当前目录，并移除本轮解压产生的其余内容。"""
        if not self.destination_dir:
            return
        destination = self.destination_dir.resolve()
        roots = sorted(
            (p for p in self.session_extract_roots if p.exists()),
            key=lambda p: len(p.parts),
        )
        outer_roots = [p for p in roots if not any(p.is_relative_to(parent) for parent in roots if parent != p)]
        kept = 0
        removed_ads = 0
        for root in outer_roots:
            # 先按规则清理广告文件及目录，目录从深到浅处理。
            for item in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
                if item.exists() and self._matches_ad_rule(item):
                    try:
                        shutil.rmtree(item) if item.is_dir() else item.unlink()
                        removed_ads += 1
                    except OSError:
                        pass

            # APK 始终提取到当前目录。
            for apk in list(root.rglob("*.apk")):
                if apk.is_file():
                    target = self._unique_destination(destination / apk.name)
                    shutil.move(str(apk), str(target)); kept += 1
                    self._ui(self.log_message, f"  ✓ 已提取 APK: {target.name}")

            # 游戏目录：目录内直接存在 EXE，或具有常见 Unity 游戏标志。
            game_dirs: list[Path] = []
            markers = {"unityplayer.dll", "gameassembly.dll"}
            for folder in [root] + [p for p in root.rglob("*") if p.is_dir()]:
                try:
                    names = {p.name.casefold() for p in folder.iterdir() if p.is_file()}
                    if any(name.endswith(".exe") for name in names) or names.intersection(markers):
                        game_dirs.append(folder)
                except OSError:
                    pass
            # 保留最外层匹配目录，避免同一游戏被重复搬运。
            selected: list[Path] = []
            for folder in sorted(game_dirs, key=lambda p: len(p.parts)):
                if not any(folder.is_relative_to(parent) for parent in selected):
                    selected.append(folder)
            for folder in selected:
                if not folder.exists():
                    continue
                target = self._unique_destination(destination / folder.name)
                if folder.resolve() == root.resolve():
                    target = self._unique_destination(destination / self.archive_output_stem(root))
                shutil.move(str(folder), str(target)); kept += 1
                self._ui(self.log_message, f"  ✓ 已提取游戏目录: {target.name}")

            if root.exists():
                shutil.rmtree(root, ignore_errors=True)
        self.last_output_dir = destination
        self._ui(self.log_message, f"[整理] 保留 {kept} 个游戏目录/APK，删除广告项 {removed_ads} 个，其余解压内容已清理")

    def cleanup_extracted_results(self, root_path: str | Path) -> bool:
        root_path = Path(root_path).resolve()
        self._ui(self.log_message, "\n" + "=" * 60)
        self._ui(self.log_message, f"开始强制清理: {root_path.name}")
        self._ui(self.log_message, "=" * 60)

        # 只清理解压过程中产生且已成功解开的中间包；用户原始输入与失败包始终保留。
        for archive_file in sorted(self.successfully_extracted_archives):
            try:
                resolved = archive_file.resolve()
                if resolved in self.initial_input_files or not resolved.is_relative_to(root_path):
                    continue
                if resolved.is_file():
                    resolved.unlink()
                    self._ui(self.log_message, f"  ✓ 已删除: {resolved.relative_to(root_path)}")
                    self.stats["deleted_archives"] += 1
                    self._ui(self.update_stats)
            except Exception:
                pass

        all_folders = list(root_path.rglob("*"))
        all_folders.sort(key=lambda item: len(str(item)), reverse=True)
        for folder in all_folders:
            if not folder.is_dir() or folder.parent.name != folder.name:
                continue
            self._ui(self.log_message, f"\n  发现重复嵌套: {folder.relative_to(root_path)}")
            try:
                items = list(folder.iterdir())
                if not items:
                    folder.rmdir()
                    self.stats["merged_folders"] += 1
                    self._ui(self.update_stats)
                    self._ui(self.log_message, "    已删除空文件夹")
                    continue

                moved_count = 0
                for item in items:
                    dest = folder.parent / item.name
                    if dest.exists():
                        base_name = item.stem
                        suffix = item.suffix
                        counter = 1
                        while dest.exists():
                            dest = folder.parent / f"{base_name}_{counter}{suffix}"
                            counter += 1
                    shutil.move(str(item), str(dest))
                    moved_count += 1
                if not any(folder.iterdir()):
                    folder.rmdir()
                    self.stats["merged_folders"] += 1
                    self._ui(self.update_stats)
                    self._ui(self.log_message, f"    已移动 {moved_count} 个项目并删除空文件夹")
            except Exception as exc:
                self._ui(self.log_message, f"    处理失败: {exc}")

        self._ui(self.log_message, "\n清理完成:")
        self._ui(self.log_message, f"  删除的压缩包: {self.stats['deleted_archives']} 个")
        self._ui(self.log_message, f"  合并的文件夹: {self.stats['merged_folders']} 个")
        self._ui(self.log_message, "=" * 60)
        return True

    def unpack_nested_archives(self, start_path: str | Path) -> bool:
        start_path = Path(start_path)
        if not start_path.exists():
            self._ui(self.log_message, f"错误：路径不存在 - {start_path}")
            return False

        if start_path.is_file() and self.is_secondary_rar_volume(start_path):
            primary = self.rar_primary_volume(start_path)
            if not primary.exists():
                self._ui(self.log_message, f"错误：缺少首卷 - {primary}")
                return False
            self._ui(self.log_message, f"[分卷] 已自动切换到首卷: {primary.name}")
            start_path = primary

        if start_path.is_dir():
            self.initial_input_files = {p.resolve() for p in start_path.rglob("*") if p.is_file()}
        else:
            self.initial_input_files = self.rar_volume_members(start_path) if start_path.suffix.lower() == ".rar" else {start_path.resolve()}
        self.successfully_extracted_archives = set()
        self.session_extract_roots = set()
        self.destination_dir = start_path.parent if start_path.is_file() else start_path

        extract_root = start_path.parent / self.archive_output_stem(start_path) if start_path.is_file() else start_path
        stack = [start_path]
        processed_dirs: set[Path] = set()
        try:
            total_files = sum(1 for _ in start_path.rglob("*")) if start_path.is_dir() else 1
        except Exception:
            total_files = 100
        processed_files = 0

        self._ui(self.log_message, "\n" + "=" * 60)
        self._ui(self.log_message, "开始智能解压...")
        self._ui(self.log_message, "=" * 60)

        while stack and self.is_processing:
            current_item = stack.pop()
            processed_files += 1
            if total_files > 0:
                progress = min(99.0, processed_files / total_files * 100)
                self._ui(self.progress_var.set, progress)

            if current_item.is_dir():
                if current_item in processed_dirs:
                    continue
                processed_dirs.add(current_item)
                try:
                    stack.extend(item for item in current_item.iterdir() if not item.name.startswith("."))
                except PermissionError:
                    self._ui(self.log_message, f"[跳过] 无权限访问目录: {current_item}")
                continue

            if self.is_secondary_rar_volume(current_item):
                continue

            real_ext = self.is_archive_file(current_item)
            if not real_ext:
                continue
            extract_dir = self.restore_and_extract(current_item, real_ext)
            if extract_dir and extract_dir.exists():
                stack.append(extract_dir)
                total_files += 1

        if not self.is_processing:
            self._ui(self.log_message, "\n[用户中断] 解压过程已被用户中断")
            return False

        self._ui(self.log_message, "\n解压完成，准备清理...")
        cleanup_roots = sorted((p for p in self.session_extract_roots if p.exists()), key=lambda p: len(p.parts))
        cleanup_roots = [p for p in cleanup_roots if not any(p.is_relative_to(parent) for parent in cleanup_roots if parent != p)]
        for cleanup_root in cleanup_roots:
            self.cleanup_extracted_results(cleanup_root)

        self._ui(self.log_message, "\n开始提取游戏目录与 APK...")
        self.organize_game_outputs()

        self._ui(self.log_message, "\n" + "=" * 60)
        self._ui(self.log_message, "解压完成！最终摘要：")
        self._ui(self.log_message, "=" * 60)
        self._ui(self.log_message, f"发现压缩包数量: {self.stats['archives_found']}")
        self._ui(self.log_message, f"成功解压数量: {self.stats['archives_extracted']}")
        self._ui(self.log_message, f"重命名文件数量: {self.stats['files_renamed']}")
        self._ui(self.log_message, f"删除中间压缩包: {self.stats['deleted_archives']}")
        self._ui(self.log_message, f"合并重复文件夹: {self.stats['merged_folders']}")
        self._ui(self.log_message, f"遇到错误数量: {self.stats['errors']}")
        self._ui(self.log_message, "=" * 60)
        return self.stats["errors"] == 0

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    if not patoolib_ok:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "缺少依赖",
            "未找到核心解压库 'patoolib'，无法继续。\n\n请执行: pip install patool",
        )
        root.destroy()
        return
    SmartUnpackerGUI().run()


if __name__ == "__main__":
    main()
