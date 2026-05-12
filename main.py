import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD

import os
import io
import ctypes
import subprocess
import sys
from PIL import Image, ImageTk
from mutagen.mp4 import MP4, MP4Cover, MP4FreeForm


class MusicAdvisoryApp:
    COVER_ART_SIZE = 420
    PLAYER_ALIAS = "advisory_m4a_player"

    def __init__(self, root):
        self.root = root

        self.root.title("M4A Advisory Editor")
        self.root.geometry("1000x850")
        self.root.minsize(800, 700)

        self.folder_path = tk.StringVar()

        self.file_list = []
        self.all_scanned_files = []

        self.total_files = 0
        self.current_index = 0

        self.current_mp4 = None
        self.current_filepath = None
        self.cover_tk = None
        self.is_playing = False
        self.playback_after_id = None
        self.track_duration_ms = 0
        self.updating_playback_position = False

        self.filter_mode = tk.StringVar(value="all")
        self.recursive_scan = tk.BooleanVar(value=True)
        self.playback_status_var = tk.StringVar(value="No track loaded")
        self.playback_position_var = tk.DoubleVar(value=0)

        # =========================
        # MAIN CANVAS
        # =========================

        self.main_canvas = tk.Canvas(
            root,
            highlightthickness=0,
            bg="#f2f2f2"
        )

        self.scrollbar = ttk.Scrollbar(
            root,
            orient="vertical",
            command=self.main_canvas.yview
        )

        self.scrollable_frame = tk.Frame(
            self.main_canvas,
            bg="#f2f2f2"
        )

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(
                scrollregion=self.main_canvas.bbox("all")
            )
        )

        self.canvas_window = self.main_canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor="n"
        )

        self.main_canvas.configure(
            yscrollcommand=self.scrollbar.set
        )

        self.main_canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.scrollbar.pack(
            side="right",
            fill="y"
        )

        self.main_canvas.bind_all(
            "<MouseWheel>",
            self._on_mousewheel
        )

        self.main_canvas.bind(
            "<Configure>",
            self.center_content
        )

        # =========================
        # CONTAINER
        # =========================

        self.container = tk.Frame(
            self.scrollable_frame,
            bg="#f2f2f2",
            width=900
        )

        self.container.pack(
            pady=20,
            expand=True
        )

        # =========================
        # SOURCE FRAME
        # =========================

        selection_frame = tk.LabelFrame(
            self.container,
            text="Select Music Source",
            padx=15,
            pady=15,
            font=("Arial", 11, "bold"),
            bg="white"
        )

        selection_frame.pack(
            fill="x",
            pady=10
        )

        # Recursive
        recursive_frame = tk.Frame(
            selection_frame,
            bg="white"
        )

        recursive_frame.pack(
            fill="x",
            pady=5
        )

        tk.Checkbutton(
            recursive_frame,
            text="Scan subfolders recursively",
            variable=self.recursive_scan,
            bg="white",
            font=("Arial", 10)
        ).pack(side=tk.LEFT)

        # Folder row
        folder_row = tk.Frame(
            selection_frame,
            bg="white"
        )

        folder_row.pack(
            fill="x",
            pady=5
        )

        tk.Label(
            folder_row,
            text="Folder:",
            bg="white",
            font=("Arial", 10)
        ).pack(side=tk.LEFT, padx=5)

        tk.Entry(
            folder_row,
            textvariable=self.folder_path,
            width=55,
            font=("Arial", 10)
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            folder_row,
            text="📁 Browse Folder",
            command=self.browse_folder,
            font=("Arial", 10),
            bg="#2196F3",
            fg="white",
            padx=10
        ).pack(side=tk.LEFT)

        # Buttons row
        buttons_row = tk.Frame(
            selection_frame,
            bg="white"
        )

        buttons_row.pack(
            fill="x",
            pady=10
        )

        tk.Button(
            buttons_row,
            text="🎵 Add Files",
            command=self.add_single_file,
            font=("Arial", 10),
            bg="#4CAF50",
            fg="white",
            padx=10
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            buttons_row,
            text="🗑 Clear All",
            command=self.clear_files,
            font=("Arial", 10),
            bg="#f44336",
            fg="white",
            padx=10
        ).pack(side=tk.LEFT, padx=5)

        # =========================
        # DRAG & DROP
        # =========================

        self.drop_frame = tk.LabelFrame(
            self.container,
            text="Drag & Drop",
            padx=20,
            pady=20,
            font=("Arial", 11, "bold"),
            bg="white"
        )

        self.drop_frame.pack(
            fill="x",
            pady=10
        )

        self.drop_label = tk.Label(
            self.drop_frame,
            text="🎵 Drag & Drop M4A files or folders here",
            font=("Arial", 16, "bold"),
            bg="#fafafa",
            fg="#666666",
            relief=tk.RIDGE,
            bd=3,
            height=5
        )

        self.drop_label.pack(
            fill="both",
            expand=True
        )

        self.drop_label.drop_target_register(DND_FILES)
        self.drop_label.dnd_bind("<<Drop>>", self.handle_drop)

        # =========================
        # FILTERS
        # =========================

        filter_frame = tk.LabelFrame(
            self.container,
            text="Filter",
            padx=15,
            pady=15,
            font=("Arial", 11, "bold"),
            bg="white"
        )

        filter_frame.pack(
            fill="x",
            pady=10
        )

        radio_container = tk.Frame(
            filter_frame,
            bg="white"
        )

        radio_container.pack()

        filters = [
            ("All", "all"),
            ("Untagged", "untagged"),
            ("Safe", "safe"),
            ("Explicit", "explicit")
        ]

        for text, value in filters:
            tk.Radiobutton(
                radio_container,
                text=text,
                variable=self.filter_mode,
                value=value,
                command=self.apply_filter,
                bg="white",
                font=("Arial", 10)
            ).pack(side=tk.LEFT, padx=10)

        self.stats_label = tk.Label(
            filter_frame,
            text="",
            bg="white",
            fg="gray",
            font=("Arial", 10)
        )

        self.stats_label.pack(pady=5)

        # =========================
        # START BUTTON
        # =========================

        self.start_btn = tk.Button(
            self.container,
            text="▶ START REVIEW",
            command=self.start_review,
            state=tk.DISABLED,
            font=("Arial", 14, "bold"),
            bg="#673AB7",
            fg="white",
            padx=25,
            pady=10
        )

        self.start_btn.pack(
            pady=15
        )

        self.count_label = tk.Label(
            self.container,
            text="No files loaded",
            bg="#f2f2f2",
            font=("Arial", 11, "bold")
        )

        self.count_label.pack()

        self.progress_bar = ttk.Progressbar(
            self.container,
            mode='determinate',
            length=700
        )

        # =========================
        # DISPLAY FRAME
        # =========================

        self.display_frame = tk.Frame(
            self.container,
            bg="#f2f2f2"
        )

        self.cover_label = tk.Label(
            self.display_frame,
            text="🎵\nNo Cover Art",
            bg="#dddddd",
            width=45,
            height=20,
            font=("Arial", 12)
        )

        self.cover_label.pack(
            pady=15
        )

        self.advisory_status_label = tk.Label(
            self.display_frame,
            text="",
            bg="#f2f2f2",
            font=("Arial", 14, "bold")
        )

        self.advisory_status_label.pack(
            pady=5
        )

        self.filepath_var = tk.StringVar()

        tk.Label(
            self.display_frame,
            textvariable=self.filepath_var,
            bg="#f2f2f2",
            fg="gray",
            wraplength=850,
            font=("Arial", 9)
        ).pack(pady=5)

        self.title_var = tk.StringVar()
        self.artist_var = tk.StringVar()

        tk.Label(
            self.display_frame,
            textvariable=self.title_var,
            bg="#f2f2f2",
            font=("Arial", 16, "bold")
        ).pack(pady=5)

        tk.Label(
            self.display_frame,
            textvariable=self.artist_var,
            bg="#f2f2f2",
            fg="#444444",
            font=("Arial", 12)
        ).pack(pady=5)

        self.progress_var = tk.StringVar()

        tk.Label(
            self.display_frame,
            textvariable=self.progress_var,
            bg="#f2f2f2",
            fg="#2196F3",
            font=("Arial", 11, "bold")
        ).pack(pady=10)

        # =========================
        # NAVIGATION
        # =========================

        nav_frame = tk.Frame(
            self.display_frame,
            bg="#f2f2f2"
        )

        nav_frame.pack(
            pady=10
        )

        tk.Button(
            nav_frame,
            text="◀ Previous",
            command=self.prev_file,
            width=12
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            nav_frame,
            text="Skip",
            command=self.skip_file,
            width=12,
            bg="#FFC107"
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            nav_frame,
            text="Next ▶",
            command=self.next_file,
            width=12
        ).pack(side=tk.LEFT, padx=5)

        # =========================
        # AUDIO PLAYER
        # =========================

        player_frame = tk.LabelFrame(
            self.display_frame,
            text="Music Preview",
            padx=15,
            pady=10,
            font=("Arial", 11, "bold"),
            bg="#f2f2f2"
        )

        player_frame.pack(
            fill="x",
            pady=10
        )

        controls_frame = tk.Frame(
            player_frame,
            bg="#f2f2f2"
        )

        controls_frame.pack()

        self.play_pause_btn = tk.Button(
            controls_frame,
            text="▶ Play",
            command=self.toggle_playback,
            width=12,
            bg="#2196F3",
            fg="white",
            font=("Arial", 10, "bold")
        )

        self.play_pause_btn.pack(
            side=tk.LEFT,
            padx=5
        )

        self.stop_btn = tk.Button(
            controls_frame,
            text="■ Stop",
            command=self.stop_playback,
            width=12,
            bg="#607D8B",
            fg="white",
            font=("Arial", 10, "bold")
        )

        self.stop_btn.pack(
            side=tk.LEFT,
            padx=5
        )

        self.position_scale = ttk.Scale(
            player_frame,
            from_=0,
            to=100,
            variable=self.playback_position_var,
            command=self.seek_playback
        )

        self.position_scale.pack(
            fill="x",
            padx=20,
            pady=8
        )

        tk.Label(
            player_frame,
            textvariable=self.playback_status_var,
            bg="#f2f2f2",
            fg="#444444",
            font=("Arial", 10)
        ).pack()

        # =========================
        # SHORTCUT HELP
        # =========================

        tk.Label(
            self.display_frame,
            text="Keyboard: Left=Explicit | Right=Safe | Up=Previous | Down=Next | Space=Skip | P=Play/Pause",
            bg="#f2f2f2",
            fg="#555555",
            font=("Arial", 10)
        ).pack(pady=6)

        # =========================
        # ACTION BUTTONS
        # =========================

        self.btn_frame = tk.Frame(
            self.display_frame,
            bg="#f2f2f2"
        )

        self.btn_frame.pack(
            pady=20
        )

        self.explicit_btn = tk.Button(
            self.btn_frame,
            text="🔞 EXPLICIT",
            command=lambda: self.apply_advisory(1),
            bg="#ff4d4d",
            fg="white",
            font=("Arial", 16, "bold"),
            width=16,
            height=2
        )

        self.explicit_btn.pack(
            side=tk.LEFT,
            padx=15
        )

        self.safe_btn = tk.Button(
            self.btn_frame,
            text="✅ SAFE",
            command=lambda: self.apply_advisory(0),
            bg="#4CAF50",
            fg="white",
            font=("Arial", 16, "bold"),
            width=16,
            height=2
        )

        self.safe_btn.pack(
            side=tk.LEFT,
            padx=15
        )



        

        

        # =========================
        # SHORTCUTS
        # =========================


        

        root.bind('<Left>', lambda e: self.apply_advisory(1))
        root.bind('<Right>', lambda e: self.apply_advisory(0))
        root.bind('<Up>', lambda e: self.prev_file())
        root.bind('<Down>', lambda e: self.next_file())
        root.bind('<space>', lambda e: self.skip_file())
        root.bind('<p>', lambda e: self.toggle_playback())
        root.bind('<P>', lambda e: self.toggle_playback())
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ====================================
    # CENTER UI
    # ====================================

    def center_content(self, event):
        canvas_width = event.width

        self.main_canvas.itemconfig(
            self.canvas_window,
            width=canvas_width
        )

        self.main_canvas.coords(
            self.canvas_window,
            canvas_width // 2,
            0
        )

    # ====================================
    # SCROLL
    # ====================================

    def _on_mousewheel(self, event):
        self.main_canvas.yview_scroll(
            int(-1 * (event.delta / 120)),
            "units"
        )

    # ====================================
    # AUDIO PLAYBACK
    # ====================================

    def mci_command(self, command, return_length=255, raise_errors=True):
        if os.name != "nt":
            if raise_errors:
                raise RuntimeError("In-app M4A playback is only supported on Windows.")
            return ""

        buffer = ctypes.create_unicode_buffer(return_length)
        error_code = ctypes.windll.winmm.mciSendStringW(
            command,
            buffer,
            return_length,
            None
        )

        if error_code:
            error_buffer = ctypes.create_unicode_buffer(255)
            ctypes.windll.winmm.mciGetErrorStringW(
                error_code,
                error_buffer,
                255
            )
            if raise_errors:
                raise RuntimeError(error_buffer.value or f"MCI error {error_code}")

        return buffer.value

    def close_audio_device(self):
        if self.playback_after_id:
            try:
                self.root.after_cancel(self.playback_after_id)
            except tk.TclError:
                pass
            self.playback_after_id = None

        self.mci_command(
            f"close {self.PLAYER_ALIAS}",
            raise_errors=False
        )

        self.is_playing = False
        self.track_duration_ms = 0

    def load_audio_device(self, filepath):
        self.close_audio_device()

        self.mci_command(
            f'open "{filepath}" type mpegvideo alias {self.PLAYER_ALIAS}'
        )

        self.mci_command(
            f"set {self.PLAYER_ALIAS} time format milliseconds"
        )

        duration = self.mci_command(
            f"status {self.PLAYER_ALIAS} length"
        )

        self.track_duration_ms = int(duration or 0)
        self.position_scale.configure(to=max(self.track_duration_ms, 1))
        self.playback_position_var.set(0)
        self.play_pause_btn.config(text="▶ Play")
        self.update_playback_status(0)

    def toggle_playback(self):
        if not self.current_filepath:
            messagebox.showwarning("No File", "No file currently loaded.")
            return

        try:
            if not self.track_duration_ms:
                self.load_audio_device(self.current_filepath)

            if self.is_playing:
                self.mci_command(f"pause {self.PLAYER_ALIAS}")
                self.is_playing = False
                self.play_pause_btn.config(text="▶ Play")
                self.playback_status_var.set("Paused")
            else:
                self.mci_command(f"play {self.PLAYER_ALIAS}")
                self.is_playing = True
                self.play_pause_btn.config(text="⏸ Pause")
                self.update_playback_progress()

        except Exception as e:
            opened_external = self.open_in_default_player(self.current_filepath)

            if opened_external:
                self.is_playing = False
                self.play_pause_btn.config(text="▶ Play")
                self.playback_status_var.set("Opened in default player")
            else:
                self.playback_status_var.set("Playback unavailable")

    def stop_playback(self):
        if not self.current_filepath:
            return

        try:
            self.mci_command(f"stop {self.PLAYER_ALIAS}", raise_errors=False)
            self.mci_command(f"seek {self.PLAYER_ALIAS} to start", raise_errors=False)
        finally:
            self.is_playing = False
            self.playback_position_var.set(0)
            self.play_pause_btn.config(text="▶ Play")
            self.update_playback_status(0)

    def seek_playback(self, value):
        if self.updating_playback_position:
            return

        if not self.track_duration_ms:
            return

        position = int(float(value))
        self.update_playback_status(position)

        try:
            if self.is_playing:
                self.mci_command(
                    f"play {self.PLAYER_ALIAS} from {position}",
                    raise_errors=False
                )
            else:
                self.mci_command(
                    f"seek {self.PLAYER_ALIAS} to {position}",
                    raise_errors=False
                )
        except Exception:
            pass

    def update_playback_progress(self):
        if not self.is_playing:
            return

        try:
            position = int(
                self.mci_command(
                    f"status {self.PLAYER_ALIAS} position"
                ) or 0
            )
        except Exception:
            self.is_playing = False
            self.play_pause_btn.config(text="▶ Play")
            return

        if self.track_duration_ms and position >= self.track_duration_ms:
            self.stop_playback()
            return

        self.updating_playback_position = True
        self.playback_position_var.set(position)
        self.updating_playback_position = False
        self.update_playback_status(position)
        self.playback_after_id = self.root.after(
            500,
            self.update_playback_progress
        )

    def update_playback_status(self, position_ms):
        current = self.format_time(position_ms)
        total = self.format_time(self.track_duration_ms)
        self.playback_status_var.set(f"{current} / {total}")

    def format_time(self, milliseconds):
        seconds = max(0, int(milliseconds / 1000))
        minutes, seconds = divmod(seconds, 60)
        return f"{minutes}:{seconds:02d}"

    def open_in_default_player(self, filepath):
        try:
            if os.name == "nt":
                os.startfile(filepath)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", filepath])
            elif os.name == "posix":
                subprocess.Popen(["xdg-open", filepath])
            else:
                return False
            return True
        except Exception:
            return False

    def prepare_cover_image(self, image):
        image = image.convert("RGB")
        width, height = image.size

        if width <= 0 or height <= 0:
            return image

        scale = min(
            self.COVER_ART_SIZE / width,
            self.COVER_ART_SIZE / height
        )

        new_size = (
            max(1, int(width * scale)),
            max(1, int(height * scale))
        )

        return image.resize(
            new_size,
            getattr(Image, "Resampling", Image).LANCZOS
        )

    # ====================================
    # DRAG DROP
    # ====================================

    def handle_drop(self, event):
        raw_data = event.data
        paths = self.root.tk.splitlist(raw_data)

        added_files = []

        for path in paths:
            path = path.strip("{}")

            if os.path.isdir(path):

                if self.recursive_scan.get():
                    files = self.scan_directory_recursive(path)

                else:
                    files = [
                        os.path.join(path, f)
                        for f in os.listdir(path)
                        if f.lower().endswith(".m4a")
                    ]

                added_files.extend(files)

            elif os.path.isfile(path):
                if path.lower().endswith(".m4a"):
                    added_files.append(path)

        added_count = 0

        for file in added_files:
            if file not in self.all_scanned_files:
                self.all_scanned_files.append(file)
                added_count += 1

        self.all_scanned_files.sort()

        self.apply_filter()
        self.update_ui_after_selection()

        self.drop_label.config(
            text=f"✅ Added {added_count} file(s)",
            fg="#4CAF50"
        )

    # ====================================
    # FILE SCAN
    # ====================================

    def scan_directory_recursive(self, directory):
        m4a_files = []

        for root_dir, dirs, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(".m4a"):
                    m4a_files.append(
                        os.path.join(root_dir, file)
                    )

        m4a_files.sort()

        return m4a_files

    # ====================================
    # BROWSE
    # ====================================

    def browse_folder(self):
        selected_folders = []

        while True:
            folder = filedialog.askdirectory()
            if not folder:
                break

            if folder not in selected_folders:
                selected_folders.append(folder)

            add_another = messagebox.askyesno(
                "Add Another Folder",
                "Do you want to select another folder?"
            )
            if not add_another:
                break

        if not selected_folders:
            return

        for folder in selected_folders:
            if self.recursive_scan.get():
                files = self.scan_directory_recursive(folder)
            else:
                files = [
                    os.path.join(folder, f)
                    for f in os.listdir(folder)
                    if f.lower().endswith(".m4a")
                ]

            for file in files:
                if file not in self.all_scanned_files:
                    self.all_scanned_files.append(file)

        self.all_scanned_files.sort()

        if len(selected_folders) == 1:
            self.folder_path.set(selected_folders[0])
        else:
            self.folder_path.set(f"{len(selected_folders)} folders selected")

        self.apply_filter()
        self.update_ui_after_selection()

    # ====================================
    # ADD FILES
    # ====================================

    def add_single_file(self):
        files = filedialog.askopenfilenames(
            filetypes=[("M4A files", "*.m4a")]
        )

        for file in files:
            if file not in self.all_scanned_files:
                self.all_scanned_files.append(file)

        self.all_scanned_files.sort()

        self.apply_filter()
        self.update_ui_after_selection()

    # ====================================
    # CLEAR
    # ====================================

    def clear_files(self):
        self.close_audio_device()

        self.file_list = []
        self.all_scanned_files = []

        self.total_files = 0
        self.current_index = 0
        self.current_filepath = None

        self.display_frame.pack_forget()

        self.start_btn.config(
            state=tk.DISABLED
        )

        self.count_label.config(
            text="No files loaded"
        )

        self.drop_label.config(
            text="🎵 Drag & Drop M4A files or folders here",
            fg="#666666"
        )

    # ====================================
    # FILTER
    # ====================================

    def get_advisory(self, filepath):
        try:
            mp4 = MP4(filepath)

            if 'rtng' in mp4 and mp4['rtng']:
                return mp4['rtng'][0]

        except:
            pass

        return None

    def apply_filter(self):
        filtered = []

        safe = 0
        explicit = 0
        untagged = 0

        for filepath in self.all_scanned_files:

            advisory = self.get_advisory(filepath)

            if advisory == 0:
                safe += 1

            elif advisory == 1:
                explicit += 1

            else:
                untagged += 1

            mode = self.filter_mode.get()

            if mode == "all":
                filtered.append(filepath)

            elif mode == "safe" and advisory == 0:
                filtered.append(filepath)

            elif mode == "explicit" and advisory == 1:
                filtered.append(filepath)

            elif mode == "untagged" and advisory is None:
                filtered.append(filepath)

        self.file_list = filtered
        self.total_files = len(filtered)

        self.stats_label.config(
            text=f"Total: {len(self.all_scanned_files)}   |   Safe: {safe}   |   Explicit: {explicit}   |   Untagged: {untagged}"
        )

        self.count_label.config(
            text=f"{self.total_files} file(s) loaded"
        )

    # ====================================
    # UI UPDATE
    # ====================================

    def update_ui_after_selection(self):
        if self.total_files > 0:
            self.start_btn.config(
                state=tk.NORMAL
            )

    # ====================================
    # START
    # ====================================

    def start_review(self):

        if self.total_files == 0:
            return

        self.current_index = 0

        self.display_frame.pack(
            fill="x",
            pady=15
        )

        self.progress_bar.pack(
            pady=10
        )

        self.progress_bar['maximum'] = self.total_files

        self.load_current_file()

    # ====================================
    # LOAD FILE
    # ====================================

    def load_current_file(self):

        if self.current_index >= self.total_files:
            self.finish_review()
            return

        self.close_audio_device()
        filepath = self.file_list[self.current_index]

        try:
            mp4 = MP4(filepath)

            self.current_mp4 = mp4
            self.current_filepath = filepath

            title = mp4.get('\xa9nam', ['Unknown'])[0]
            artist = mp4.get('\xa9ART', ['Unknown'])[0]

            self.title_var.set(title)
            self.artist_var.set(artist)

            self.filepath_var.set(filepath)

            advisory = self.get_advisory(filepath)

            if advisory == 1:
                text = "🔞 Explicit"
                color = "#f44336"

            elif advisory == 0:
                text = "✅ Safe"
                color = "#4CAF50"

            else:
                text = "⚠ Untagged"
                color = "#FF9800"

            self.advisory_status_label.config(
                text=text,
                fg=color
            )

            if 'covr' in mp4 and mp4['covr']:

                cover_data = bytes(mp4['covr'][0])

                img = Image.open(
                    io.BytesIO(cover_data)
                )

                img = self.prepare_cover_image(img)

                self.cover_tk = ImageTk.PhotoImage(img)

                self.cover_label.config(
                    image=self.cover_tk,
                    text="",
                    width=self.COVER_ART_SIZE,
                    height=self.COVER_ART_SIZE
                )

            else:
                self.cover_label.config(
                    image="",
                    text="🎵\nNo Cover Art"
                )

            self.progress_var.set(
                f"File {self.current_index + 1} / {self.total_files}"
            )

            self.progress_bar['value'] = self.current_index + 1
            self.playback_status_var.set("Ready to play")
            self.playback_position_var.set(0)
            self.play_pause_btn.config(text="▶ Play")

        except Exception as e:

            messagebox.showerror(
                "Error",
                str(e)
            )

    # ====================================
    # APPLY ADVISORY
    # ====================================

    def apply_advisory(self, value):

        if not self.current_mp4:
            return

        try:
            self.close_audio_device()

            mp4 = self.current_mp4

            mp4['rtng'] = [value]

            key = '----:com.apple.iTunes:ITUNESADVISORY'

            mp4[key] = [
                MP4FreeForm(data=bytes([value]))
            ]

            mp4.save()

            self.next_file()

        except Exception as e:

            messagebox.showerror(
                "Save Error",
                str(e)
            )

    # ====================================
    # NAVIGATION
    # ====================================

    def next_file(self):

        if self.current_index < self.total_files - 1:
            self.current_index += 1
            self.load_current_file()

        else:
            self.finish_review()

    def prev_file(self):

        if self.current_index > 0:
            self.current_index -= 1
            self.load_current_file()

    def skip_file(self):
        self.next_file()

    # ====================================
    # FINISH
    # ====================================

    def finish_review(self):
        self.close_audio_device()

        messagebox.showinfo(
            "Done",
            "Finished reviewing files."
        )

        self.display_frame.pack_forget()

        self.progress_bar.pack_forget()

        self.start_btn.config(
            state=tk.NORMAL
        )

    def on_close(self):
        self.close_audio_device()
        self.root.destroy()


# ====================================
# MAIN
# ====================================

def main():

    root = TkinterDnD.Tk()
    try:
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "icon.png"
        )
        if os.path.isfile(icon_path):
            app_icon = tk.PhotoImage(file=icon_path)
            root.iconphoto(True, app_icon)
            root._app_icon_ref = app_icon
    except Exception:
        pass

    app = MusicAdvisoryApp(root)

    root.mainloop()


if __name__ == "__main__":
    main()
