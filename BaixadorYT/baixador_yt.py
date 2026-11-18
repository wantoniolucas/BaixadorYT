"""BaixadorYT - interface Windows em Python para yt-dlp.

Requer Python >= 3.11, yt-dlp e FFmpeg instalado.
Use somente com conteúdos cujo download seja permitido/autorizado.
"""
from __future__ import annotations

import os
import queue
import shutil
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlparse

try:
    import yt_dlp
    from yt_dlp.utils import DownloadCancelled
except ImportError:
    yt_dlp = None
    DownloadCancelled = Exception  # Permite abrir a interface antes de instalar o pacote.


COLORS = {
    "bg": "#101723",
    "panel": "#1A2534",
    "field": "#253347",
    "fg": "#F3F6FA",
    "muted": "#9AAFC4",
    "accent": "#2FA7FF",
    "accent_text": "#071625",
    "error": "#FF9F9F",
}

MODES = ("Vídeo MP4", "Áudio MP3", "Áudio M4A", "Somente legendas")
QUALITIES = ("Melhor disponível", "2160p (4K)", "1080p", "720p", "480p", "360p")


def find_ffmpeg_dir() -> str | None:
    """Localiza executáveis do FFmpeg no PATH ou na pasta do projeto."""
    roots = [Path(__file__).resolve().parent, Path(__file__).resolve().parent / "bin"]
    for root in roots:
        if (root / "ffmpeg.exe").is_file() and (root / "ffprobe.exe").is_file():
            return str(root)
        if (root / "ffmpeg").is_file() and (root / "ffprobe").is_file():
            return str(root)
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return ""  # Encontrados no PATH, sem necessidade de ffmpeg_location.
    return None


class GuiLogger:
    def __init__(self, events: queue.Queue):
        self.events = events

    def debug(self, msg: str) -> None:
        # Evita muitos logs; o progresso é informado pelo progress_hook.
        pass

    def warning(self, msg: str) -> None:
        self.events.put(("status", f"Aviso: {msg[:180]}"))

    def error(self, msg: str) -> None:
        self.events.put(("status", f"Erro: {msg[:180]}"))


class DownloadApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("BaixadorYT • Python")
        self.root.geometry("740x625")
        self.root.minsize(650, 590)
        self.root.configure(bg=COLORS["bg"])
        self.events: queue.Queue = queue.Queue()
        self.cancel_event = threading.Event()
        self.downloading = False

        default_folder = Path.home() / "Downloads"
        if not default_folder.is_dir():
            default_folder = Path.home()

        self.url = tk.StringVar()
        self.folder = tk.StringVar(value=str(default_folder))
        self.mode = tk.StringVar(value=MODES[0])
        self.quality = tk.StringVar(value=QUALITIES[3])
        self.playlist = tk.BooleanVar(value=False)
        self.subtitles = tk.BooleanVar(value=False)
        self.thumbnail = tk.BooleanVar(value=False)
        self.metadata = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Pronto para começar.")
        self.percent = tk.DoubleVar(value=0)

        self._setup_styles()
        self._build()
        self.root.after(120, self._drain_events)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TCombobox", padding=7, fieldbackground=COLORS["field"],
                        background=COLORS["field"], foreground=COLORS["fg"],
                        arrowcolor=COLORS["fg"])
        style.map("TCombobox", fieldbackground=[("readonly", COLORS["field"])],
                  foreground=[("readonly", COLORS["fg"])])
        style.configure("Download.Horizontal.TProgressbar", troughcolor=COLORS["field"],
                        background=COLORS["accent"], borderwidth=0, thickness=15)

    def _label(self, parent: tk.Widget, text: str, *, muted: bool = False,
               size: int = 10, bold: bool = False) -> tk.Label:
        return tk.Label(parent, text=text, anchor="w", bg=COLORS["panel"],
                        fg=COLORS["muted"] if muted else COLORS["fg"],
                        font=("Segoe UI", size, "bold" if bold else "normal"))

    def _build(self) -> None:
        top = tk.Frame(self.root, bg=COLORS["bg"])
        top.pack(fill="x", padx=27, pady=(22, 14))
        tk.Label(top, text="BaixadorYT", bg=COLORS["bg"], fg=COLORS["fg"],
                 font=("Segoe UI", 23, "bold")).pack(anchor="w")
        tk.Label(top, text="Vídeos, áudio, legendas e playlists em uma só tela",
                 bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(anchor="w")

        panel = tk.Frame(self.root, bg=COLORS["panel"], padx=20, pady=18)
        panel.pack(fill="both", expand=True, padx=27, pady=(0, 14))

        self._label(panel, "Link do vídeo ou playlist", bold=True).pack(fill="x")
        self.url_entry = tk.Entry(panel, textvariable=self.url, bg=COLORS["field"],
                                  fg=COLORS["fg"], insertbackground=COLORS["fg"],
                                  relief="flat", font=("Segoe UI", 11))
        self.url_entry.pack(fill="x", ipady=10, pady=(7, 16))

        selectors = tk.Frame(panel, bg=COLORS["panel"])
        selectors.pack(fill="x")
        selectors.grid_columnconfigure(0, weight=1, uniform="mode")
        selectors.grid_columnconfigure(1, weight=1, uniform="mode")

        self._label(selectors, "Formato", bold=True).grid(row=0, column=0, sticky="w")
        self._label(selectors, "Resolução máxima", bold=True).grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.mode_combo = ttk.Combobox(selectors, textvariable=self.mode, values=MODES, state="readonly")
        self.mode_combo.grid(row=1, column=0, sticky="ew", pady=(6, 12))
        self.mode_combo.bind("<<ComboboxSelected>>", self._update_quality)
        self.quality_combo = ttk.Combobox(selectors, textvariable=self.quality,
                                          values=QUALITIES, state="readonly")
        self.quality_combo.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=(6, 12))

        self._label(panel, "Salvar em", bold=True).pack(fill="x")
        folder_row = tk.Frame(panel, bg=COLORS["panel"])
        folder_row.pack(fill="x", pady=(6, 12))
        self.folder_entry = tk.Entry(folder_row, textvariable=self.folder, bg=COLORS["field"],
                                     fg=COLORS["fg"], insertbackground=COLORS["fg"],
                                     relief="flat", font=("Segoe UI", 10))
        self.folder_entry.pack(side="left", fill="x", expand=True, ipady=9)
        self.folder_button = tk.Button(folder_row, text="Escolher pasta", command=self._choose_folder,
                                       bg=COLORS["field"], fg=COLORS["fg"], relief="flat",
                                       activebackground=COLORS["accent"], cursor="hand2",
                                       font=("Segoe UI", 9), padx=11, pady=7)
        self.folder_button.pack(side="left", padx=(9, 0))

        self.playlist_check = self._check(panel, "Baixar playlist inteira", self.playlist)
        self.subtitles_check = self._check(panel, "Também baixar legendas (PT/EN)", self.subtitles)
        self.thumbnail_check = self._check(panel, "Salvar miniatura/capa", self.thumbnail)
        self.metadata_check = self._check(panel, "Salvar informações em JSON", self.metadata)
        self._update_quality()

        action_row = tk.Frame(panel, bg=COLORS["panel"])
        action_row.pack(fill="x", pady=(14, 9))
        self.download_button = tk.Button(action_row, text="Iniciar download",
                                         command=self._start_download, bg=COLORS["accent"],
                                         fg=COLORS["accent_text"], relief="flat", cursor="hand2",
                                         activebackground="#68C1FF", font=("Segoe UI", 11, "bold"),
                                         padx=18, pady=10)
        self.download_button.pack(side="left", fill="x", expand=True)
        self.cancel_button = tk.Button(action_row, text="Cancelar", command=self._cancel_download,
                                       state="disabled", bg=COLORS["field"], fg=COLORS["fg"],
                                       relief="flat", cursor="hand2", font=("Segoe UI", 10),
                                       padx=18, pady=11)
        self.cancel_button.pack(side="left", padx=(9, 0))

        self.progressbar = ttk.Progressbar(panel, variable=self.percent, maximum=100,
                                           style="Download.Horizontal.TProgressbar")
        self.progressbar.pack(fill="x", pady=(7, 9))
        tk.Label(panel, textvariable=self.status, anchor="w", justify="left", wraplength=615,
                 bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(fill="x")

        bottom = tk.Frame(self.root, bg=COLORS["bg"])
        bottom.pack(fill="x", padx=27, pady=(0, 18))
        tk.Button(bottom, text="Abrir pasta de downloads", command=self._open_folder,
                  bg=COLORS["bg"], fg=COLORS["accent"], relief="flat", cursor="hand2",
                  activebackground=COLORS["bg"], font=("Segoe UI", 10)).pack(side="left")
        tk.Label(bottom, text="Use apenas com conteúdo autorizado.",
                 bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(side="right")

    def _check(self, parent: tk.Widget, title: str, variable: tk.BooleanVar) -> tk.Checkbutton:
        check = tk.Checkbutton(parent, text=title, variable=variable, bg=COLORS["panel"],
                               fg=COLORS["fg"], selectcolor=COLORS["field"],
                               activebackground=COLORS["panel"], activeforeground=COLORS["fg"],
                               font=("Segoe UI", 10), anchor="w", padx=0, pady=2)
        check.pack(fill="x")
        return check

    def _update_quality(self, _event=None) -> None:
        is_video = self.mode.get() == "Vídeo MP4"
        self.quality_combo.configure(state="readonly" if is_video and not self.downloading else "disabled")
        if self.mode.get() == "Somente legendas":
            self.subtitles.set(True)
            self.subtitles_check.configure(state="disabled")
        else:
            self.subtitles_check.configure(state="normal" if not self.downloading else "disabled")

    def _choose_folder(self) -> None:
        target = filedialog.askdirectory(initialdir=self.folder.get() or str(Path.home()))
        if target:
            self.folder.set(target)

    def _open_folder(self) -> None:
        target = Path(self.folder.get()).expanduser()
        if target.is_dir():
            if os.name == "nt":
                os.startfile(str(target))  # type: ignore[attr-defined]
            else:
                import subprocess
                subprocess.Popen(["xdg-open", str(target)])
        else:
            messagebox.showwarning("Pasta não encontrada", "Selecione uma pasta válida.")

    def _set_busy(self, busy: bool) -> None:
        self.downloading = busy
        state = "disabled" if busy else "normal"
        for control in (self.url_entry, self.folder_entry, self.folder_button,
                        self.playlist_check, self.thumbnail_check, self.metadata_check):
            control.configure(state=state)
        self.mode_combo.configure(state="disabled" if busy else "readonly")
        self.download_button.configure(state="disabled" if busy else "normal")
        self.cancel_button.configure(state="normal" if busy else "disabled")
        self._update_quality()

    def _start_download(self) -> None:
        if yt_dlp is None:
            messagebox.showerror("Dependência ausente", "Instale o yt-dlp:\npy -m pip install -U 'yt-dlp[default]'")
            return
        url = self.url.get().strip()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            messagebox.showwarning("Link inválido", "Cole um endereço HTTP/HTTPS válido.")
            return
        folder = Path(self.folder.get()).expanduser()
        if not folder.is_dir():
            messagebox.showwarning("Pasta inválida", "Selecione uma pasta existente.")
            return
        ffmpeg_dir = find_ffmpeg_dir()
        if ffmpeg_dir is None and self.mode.get() != "Somente legendas":
            messagebox.showerror("FFmpeg necessário", "Instale o FFmpeg e o ffprobe.\n"
                                 "No PowerShell: winget install -e --id Gyan.FFmpeg\n"
                                 "Depois, feche e reabra o aplicativo.")
            return
        self.cancel_event.clear()
        self.percent.set(0)
        self.status.set("Conectando e analisando o link...")
        settings = {
            "url": url,
            "folder": str(folder.resolve()),
            "mode": self.mode.get(),
            "quality": self.quality.get(),
            "playlist": self.playlist.get(),
            "subtitles": self.subtitles.get(),
            "thumbnail": self.thumbnail.get(),
            "metadata": self.metadata.get(),
            "ffmpeg_dir": ffmpeg_dir,
        }
        self._set_busy(True)
        threading.Thread(target=self._download_worker, args=(settings,), daemon=True).start()

    def _cancel_download(self) -> None:
        self.cancel_event.set()
        self.status.set("Cancelamento solicitado. Aguardando o próximo ponto seguro...")
        self.cancel_button.configure(state="disabled")

    def _download_worker(self, settings: dict) -> None:
        last_update = 0.0

        def progress(info: dict) -> None:
            nonlocal last_update
            if self.cancel_event.is_set():
                raise DownloadCancelled("Cancelado pelo usuário")
            if info.get("status") == "finished":
                self.events.put(("status", "Arquivo recebido. Processando/convertendo, se necessário..."))
                return
            if info.get("status") != "downloading":
                return
            now = time.monotonic()
            if now - last_update < 0.2:
                return
            last_update = now
            done = info.get("downloaded_bytes") or 0
            total = info.get("total_bytes") or info.get("total_bytes_estimate") or 0
            percent = (done / total * 100) if total else 0
            speed = info.get("speed")
            speed_label = f" • {speed / (1024**2):.2f} MB/s" if speed else ""
            self.events.put(("progress", min(percent, 100),
                             f"Baixando arquivo atual: {percent:.1f}%{speed_label}" if total
                             else f"Baixando arquivo atual: {done / (1024**2):.1f} MB{speed_label}"))

        try:
            mode = settings["mode"]
            quality = settings["quality"]
            options = {
                "outtmpl": str(Path(settings["folder"]) / "%(title)s [%(id)s].%(ext)s"),
                "noplaylist": not settings["playlist"],
                "writethumbnail": settings["thumbnail"],
                "writeinfojson": settings["metadata"],
                "writesubtitles": settings["subtitles"] or mode == "Somente legendas",
                "writeautomaticsub": settings["subtitles"] or mode == "Somente legendas",
                "subtitleslangs": ["pt.*", "en.*"],
                "subtitlesformat": "srt/best",
                "progress_hooks": [progress],
                "logger": GuiLogger(self.events),
                "quiet": True,
                "ignoreerrors": False,
                "continuedl": True,
                "overwrites": False,
            }
            if settings["ffmpeg_dir"]:
                options["ffmpeg_location"] = settings["ffmpeg_dir"]
            if mode == "Somente legendas":
                options["skip_download"] = True
            elif mode == "Áudio MP3":
                options["format"] = "bestaudio/best"
                options["postprocessors"] = [{"key": "FFmpegExtractAudio",
                                               "preferredcodec": "mp3",
                                               "preferredquality": "192"}]
            elif mode == "Áudio M4A":
                options["format"] = "bestaudio[ext=m4a]/bestaudio/best"
                options["postprocessors"] = [{"key": "FFmpegExtractAudio",
                                               "preferredcodec": "m4a"}]
            else:
                limit = None if quality == "Melhor disponível" else int(quality.split("p")[0])
                filter_quality = f"[height<={limit}]" if limit else ""
                options["format"] = (
                    f"bv[ext=mp4]{filter_quality}+ba[ext=m4a]/"
                    f"b[ext=mp4]{filter_quality}/"
                    f"bv{filter_quality}+ba/b{filter_quality}"
                )
                options["merge_output_format"] = "mp4"

            with yt_dlp.YoutubeDL(options) as downloader:
                result = downloader.download([settings["url"]])
            if self.cancel_event.is_set():
                self.events.put(("cancelled",))
            elif result == 0:
                self.events.put(("done", "Concluído! Confira os arquivos na pasta escolhida."))
            else:
                self.events.put(("failed", "Algum item não pôde ser baixado."))
        except Exception as error:
            if self.cancel_event.is_set():
                self.events.put(("cancelled",))
            else:
                self.events.put(("failed", f"Falha: {str(error)[:270]}"))

    def _drain_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "progress":
                    self.percent.set(event[1])
                    self.status.set(event[2])
                elif kind == "status":
                    self.status.set(event[1])
                elif kind == "done":
                    self.percent.set(100)
                    self.status.set(event[1])
                    self._set_busy(False)
                    messagebox.showinfo("BaixadorYT", event[1])
                elif kind == "cancelled":
                    self.percent.set(0)
                    self.status.set("Download cancelado. Arquivos parciais podem permanecer na pasta.")
                    self._set_busy(False)
                elif kind == "failed":
                    self.status.set(event[1])
                    self._set_busy(False)
                    messagebox.showerror("Falha no download", event[1])
        except queue.Empty:
            pass
        finally:
            self.root.after(120, self._drain_events)

    def _on_close(self) -> None:
        if self.downloading:
            messagebox.showwarning("Download em andamento", "Cancele o download antes de fechar.")
            return
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    DownloadApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
