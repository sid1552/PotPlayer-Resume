"""
PotPlayer Resume - GUI Edition
Tracks playback position for network URLs and resumes where you left off.
"""

import ctypes
import ctypes.wintypes
import json
import os
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox


POTPLAYER_PATHS = [
    r"C:\Program Files\DAUM\PotPlayer\PotPlayerMini64.exe",
    r"C:\Program Files\PotPlayer\PotPlayerMini64.exe",
    r"C:\Program Files (x86)\DAUM\PotPlayer\PotPlayerMini.exe",
]
POSITIONS_FILE = os.path.join(os.path.expanduser("~"), ".potplayer_positions.json")
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".potplayer_resume_settings.json")
POLL_INTERVAL = 2  # seconds between position checks


BG = "#1e1e2e"
BG_SECONDARY = "#272738"
BG_ENTRY = "#313146"
FG = "#cdd6f4"
FG_DIM = "#6c7086"
ACCENT = "#89b4fa"
ACCENT_HOVER = "#74c7ec"
GREEN = "#a6e3a1"
RED = "#f38ba8"
YELLOW = "#f9e2af"
BORDER = "#45475a"


FindWindow = ctypes.windll.user32.FindWindowW
SendMessage = ctypes.windll.user32.SendMessageW
WM_USER = 0x0400


def find_potplayer():
    # Check settings first
    settings = load_settings()
    custom_path = settings.get("potplayer_path")
    if custom_path and os.path.exists(custom_path):
        return custom_path
    
    # Try default paths
    for path in POTPLAYER_PATHS:
        if os.path.exists(path):
            return path
    
    # Try system PATH
    try:
        result = subprocess.run(
            ["where", "PotPlayerMini64.exe"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0]
    except Exception:
        pass
    return None


def find_potplayer_hwnd():
    hwnd = FindWindow("PotPlayer64", None)
    if not hwnd:
        hwnd = FindWindow("PotPlayer", None)
    return hwnd


def get_potplayer_position_ms(hwnd):
    pos = SendMessage(hwnd, WM_USER, 0x5004, 0)
    return pos if pos >= 0 else None


def get_potplayer_duration_ms(hwnd):
    dur = SendMessage(hwnd, WM_USER, 0x5002, 0)
    return dur if dur > 0 else None


def is_potplayer_process_alive():
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq PotPlayerMini64.exe", "/NH"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if "PotPlayerMini64.exe" in result.stdout:
            return True
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq PotPlayerMini.exe", "/NH"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return "PotPlayerMini.exe" in result.stdout
    except Exception:
        return False


def timestamp_to_seconds(ts):
    parts = ts.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return 0


def seconds_to_timestamp(secs):
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    return f"{h:02d}:{m:02d}:{s:02d}"



def load_positions():
    if os.path.exists(POSITIONS_FILE):
        try:
            with open(POSITIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_positions(positions):
    with open(POSITIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(positions, f, indent=2, ensure_ascii=False)


def save_position(url, timestamp):
    positions = load_positions()
    
    # Extract filename and movie name
    clean_url = url.split('?')[0].split('#')[0]
    raw_filename = clean_url.split('/')[-1]
    
    # Parse movie name
    import re
    name = re.sub(r'\.(mkv|mp4|avi|mov|wmv|flv|webm)$', '', raw_filename, flags=re.IGNORECASE)
    
    patterns = [
        r'[\.\-_ ](19\d{2}|20\d{2})',
        r'[\.\-_ ](2160p|1080p|720p|480p|360p)',
        r'[\.\-_ ](BluRay|BDRip|BRRip|WEB-?DL|WEBRip|HDTV|DVDRip|CAM|TS|HDCAM)',
        r'[\.\-_ ](x264|x265|h264|h265|HEVC|XviD|AV1)',
        r'[\.\-_ ](AAC|DTS|AC3|TrueHD|DDP|Atmos)',
        r'[\.\-_ ]S\d{1,2}E\d{1,2}',
        r'[\.\-_ ](REPACK|PROPER|REMASTERED|UNRATED|EXTENDED|IMAX)',
    ]
    
    earliest_pos = len(name)
    for pattern in patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            earliest_pos = min(earliest_pos, match.start())
    
    if earliest_pos < len(name):
        movie_title = name[:earliest_pos]
    else:
        movie_title = name
    
    movie_title = re.sub(r'[\._\-]+', ' ', movie_title)
    movie_title = re.sub(r'\s+', ' ', movie_title).strip()
    movie_title = ' '.join(word.capitalize() for word in movie_title.split())
    
    if not movie_title or len(movie_title) < 2:
        movie_title = raw_filename
    
    # Try to get file size from network stream
    file_size = "-"
    try:
        import urllib.request
        req = urllib.request.Request(url, method='HEAD')
        req.add_header('User-Agent', 'Mozilla/5.0')
        
        with urllib.request.urlopen(req, timeout=5) as response:
            size_bytes = response.headers.get('Content-Length')
            if size_bytes:
                size_bytes = int(size_bytes)
                bytes_size = size_bytes
                for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                    if bytes_size < 1024.0:
                        if unit == 'B':
                            file_size = f"{bytes_size:.0f}{unit}"
                        else:
                            file_size = f"{bytes_size:.1f}{unit}"
                        break
                    bytes_size /= 1024.0
                else:
                    file_size = f"{bytes_size:.1f}PB"
    except Exception:
        pass
    
    # Save with movie name as key
    if movie_title not in positions:
        positions[movie_title] = {
            "timestamp": timestamp,
            "seconds": timestamp_to_seconds(timestamp),
            "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "urls": [url],
            "current_url": url,
            "file_size": file_size,
        }
    else:
        positions[movie_title]["timestamp"] = timestamp
        positions[movie_title]["seconds"] = timestamp_to_seconds(timestamp)
        positions[movie_title]["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        positions[movie_title]["current_url"] = url
        
        if file_size != "-":
            positions[movie_title]["file_size"] = file_size
        
        if "urls" not in positions[movie_title]:
            positions[movie_title]["urls"] = [url]
        elif url not in positions[movie_title]["urls"]:
            positions[movie_title]["urls"].append(url)
    
    save_positions(positions)


def remove_position(movie_name):
    positions = load_positions()
    if movie_name in positions:
        del positions[movie_name]
        save_positions(positions)
        return True
    return False



def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)



class PotPlayerResumeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PotPlayer Resume")
        self.root.geometry("1200x560")
        self.root.minsize(1100, 480)
        self.root.configure(bg=BG)

        # State
        self.monitoring = False
        self.monitor_thread = None
        self.current_url = None
        self.current_movie_name = None
        self.last_position_secs = 0
        self.potplayer_path = find_potplayer()

        self._build_ui()
        self._apply_dark_theme()
        self._refresh_table()

        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    
    def _build_ui(self):
        # Top section: URL input
        top = tk.Frame(self.root, bg=BG, padx=16, pady=12)
        top.pack(fill=tk.X)
        
        tk.Label(top, text="Stream URL", bg=BG, fg=FG_DIM,
                 font=("Segoe UI", 9)).pack(anchor=tk.W)

        url_row = tk.Frame(top, bg=BG)
        url_row.pack(fill=tk.X, pady=(4, 0))

        self.url_var = tk.StringVar()
        self.url_entry = tk.Entry(
            url_row, textvariable=self.url_var,
            bg=BG_ENTRY, fg=FG, insertbackground=FG,
            font=("Consolas", 11), relief=tk.FLAT,
            highlightthickness=1, highlightbackground=BORDER,
            highlightcolor=ACCENT,
        )
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        self.url_entry.bind("<Return>", lambda e: self._play())

        btn_frame = tk.Frame(url_row, bg=BG)
        btn_frame.pack(side=tk.RIGHT, padx=(8, 0))

        self.play_btn = tk.Button(
            btn_frame, text="Play", command=self._play,
            bg=ACCENT, fg="#11111b", font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT, padx=14, pady=4, cursor="hand2",
            activebackground=ACCENT_HOVER, activeforeground="#11111b",
        )
        self.play_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.paste_btn = tk.Button(
            btn_frame, text=" Paste && Play", command=self._paste_and_play,
            bg=BG_SECONDARY, fg=FG, font=("Segoe UI", 10),
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2",
            activebackground=BORDER, activeforeground=FG,
        )
        self.paste_btn.pack(side=tk.LEFT, padx=(0, 4))
        
        self.settings_btn = tk.Button(
            btn_frame, text="Settings", command=self._show_settings,
            bg=BG_SECONDARY, fg=FG, font=("Segoe UI", 10),
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2",
            activebackground=BORDER, activeforeground=FG,
        )
        self.settings_btn.pack(side=tk.LEFT)

        # Status section
        status_frame = tk.Frame(self.root, bg=BG_SECONDARY, padx=16, pady=10)
        status_frame.pack(fill=tk.X, padx=16, pady=(4, 0))

        self.status_label = tk.Label(
            status_frame, text="Ready", bg=BG_SECONDARY, fg=FG_DIM,
            font=("Segoe UI", 10), anchor=tk.W,
        )
        self.status_label.pack(side=tk.LEFT)

        self.position_label = tk.Label(
            status_frame, text="", bg=BG_SECONDARY, fg=ACCENT,
            font=("Consolas", 12, "bold"), anchor=tk.E,
        )
        self.position_label.pack(side=tk.RIGHT)

        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(
            self.root, variable=self.progress_var,
            maximum=100, mode="determinate",
        )
        self.progress.pack(fill=tk.X, padx=16, pady=(2, 0))

        # Saved positions section
        table_header = tk.Frame(self.root, bg=BG)
        table_header.pack(fill=tk.X, padx=16, pady=(12, 4))

        tk.Label(table_header, text="Saved Positions", bg=BG, fg=FG,
                 font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)

        self.clear_btn = tk.Button(
            table_header, text="Clear All", command=self._clear_all,
            bg=BG, fg=RED, font=("Segoe UI", 9),
            relief=tk.FLAT, cursor="hand2",
            activebackground=BG, activeforeground=RED,
        )
        self.clear_btn.pack(side=tk.RIGHT)

        # Treeview for saved positions
        tree_frame = tk.Frame(self.root, bg=BG)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        columns = ("movie", "filename", "quality", "source", "size", "position", "date")
        self.tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings",
            selectmode="browse", height=8,
        )
        self.tree.heading("movie", text="Movie Name", anchor=tk.W)
        self.tree.heading("filename", text="File Name", anchor=tk.W)
        self.tree.heading("quality", text="Quality", anchor=tk.CENTER)
        self.tree.heading("source", text="Source", anchor=tk.CENTER)
        self.tree.heading("size", text="Size", anchor=tk.CENTER)
        self.tree.heading("position", text="Position", anchor=tk.CENTER)
        self.tree.heading("date", text="Saved", anchor=tk.CENTER)

        self.tree.column("movie", width=200, minwidth=120)
        self.tree.column("filename", width=220, minwidth=150)
        self.tree.column("quality", width=70, minwidth=60, anchor=tk.CENTER)
        self.tree.column("source", width=80, minwidth=70, anchor=tk.CENTER)
        self.tree.column("size", width=80, minwidth=70, anchor=tk.CENTER)
        self.tree.column("position", width=80, minwidth=70, anchor=tk.CENTER)
        self.tree.column("date", width=140, minwidth=120, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Tree events
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Button-3>", self._on_tree_right_click)

        # Context menu
        self.ctx_menu = tk.Menu(self.root, tearoff=0, bg=BG_SECONDARY, fg=FG,
                                activebackground=ACCENT, activeforeground="#11111b")
        self.ctx_menu.add_command(label="Play", command=self._play_selected)
        self.ctx_menu.add_command(label="Copy URL", command=self._copy_selected_url)
        self.ctx_menu.add_separator()
        self.ctx_menu.add_command(label="Delete", command=self._delete_selected)

        # Footer
        footer = tk.Frame(self.root, bg=BG, pady=8)
        footer.pack(fill=tk.X, side=tk.BOTTOM)

        potplayer_status = "PotPlayer: Found" if self.potplayer_path else "PotPlayer: Not Found"
        status_color = GREEN if self.potplayer_path else RED
        tk.Label(footer, text=potplayer_status, bg=BG, fg=status_color,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=16)

        positions_path = POSITIONS_FILE.replace(os.path.expanduser("~"), "~")
        tk.Label(footer, text=f"Data: {positions_path}", bg=BG, fg=FG_DIM,
                 font=("Segoe UI", 9)).pack(side=tk.RIGHT, padx=16)

    def _apply_dark_theme(self):
        style = ttk.Style()
        style.theme_use('clam')

        # Treeview
        style.configure("Treeview",
                         background=BG_SECONDARY, foreground=FG,
                         fieldbackground=BG_SECONDARY, borderwidth=0,
                         font=("Consolas", 10), rowheight=28)
        style.configure("Treeview.Heading",
                         background=BG_ENTRY, foreground=FG_DIM,
                         font=("Segoe UI", 9, "bold"), borderwidth=0,
                         relief=tk.FLAT)
        style.map("Treeview",
                   background=[("selected", ACCENT)],
                   foreground=[("selected", "#11111b")])
        style.map("Treeview.Heading",
                   background=[("active", BORDER)])

        # Progressbar
        style.configure("TProgressbar",
                         background=ACCENT, troughcolor=BG_ENTRY,
                         borderwidth=0, thickness=4)

        # Scrollbar
        style.configure("Vertical.TScrollbar",
                         background=BG_ENTRY, troughcolor=BG_SECONDARY,
                         borderwidth=0, arrowsize=0)
        style.map("Vertical.TScrollbar",
                   background=[("active", BORDER), ("!active", BG_ENTRY)])

    
    def _extract_quality(self, filename):
        import re
        
        resolution_match = re.search(r'\b(2160p|1080p|720p|480p|360p)\b', filename, re.IGNORECASE)
        if resolution_match:
            res = resolution_match.group(1).upper()
            if res == "2160P":
                return "4K"
            return res
        
        quality_match = re.search(r'\b(4K|UHD|HD|SD)\b', filename, re.IGNORECASE)
        if quality_match:
            return quality_match.group(1).upper()
        
        return "-"
    
    def _extract_source(self, filename):
        import re
        
        sources = {
            r'\bBlu-?Ray\b': 'BluRay',
            r'\bBDRip\b': 'BDRip',
            r'\bBRRip\b': 'BRRip',
            r'\bWEB-?DL\b': 'WEB-DL',
            r'\bWEBRip\b': 'WEBRip',
            r'\bHDTV\b': 'HDTV',
            r'\bDVDRip\b': 'DVDRip',
            r'\bDVD\b': 'DVD',
            r'\bCAM\b': 'CAM',
            r'\bTS\b': 'TS',
            r'\bHDCAM\b': 'HDCAM',
            r'\bREMUX\b': 'REMUX',
        }
        
        for pattern, source_name in sources.items():
            if re.search(pattern, filename, re.IGNORECASE):
                return source_name
        
        return "-"
    
    def _parse_movie_name(self, filename):
        import re
        
        name = re.sub(r'\.(mkv|mp4|avi|mov|wmv|flv|webm)$', '', filename, flags=re.IGNORECASE)
        
        patterns = [
            r'[\.\-_ ](19\d{2}|20\d{2})',
            r'[\.\-_ ](2160p|1080p|720p|480p|360p)',
            r'[\.\-_ ](BluRay|BDRip|BRRip|WEB-?DL|WEBRip|HDTV|DVDRip|CAM|TS|HDCAM)',
            r'[\.\-_ ](x264|x265|h264|h265|HEVC|XviD|AV1)',
            r'[\.\-_ ](AAC|DTS|AC3|TrueHD|DDP|Atmos)',
            r'[\.\-_ ]S\d{1,2}E\d{1,2}',
            r'[\.\-_ ](REPACK|PROPER|REMASTERED|UNRATED|EXTENDED|IMAX)',
        ]
        
        earliest_pos = len(name)
        for pattern in patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                earliest_pos = min(earliest_pos, match.start())
        
        if earliest_pos < len(name):
            movie_title = name[:earliest_pos]
        else:
            movie_title = name
        
        movie_title = re.sub(r'[\._\-]+', ' ', movie_title)
        movie_title = re.sub(r'\s+', ' ', movie_title).strip()
        movie_title = ' '.join(word.capitalize() for word in movie_title.split())
        
        if not movie_title or len(movie_title) < 2:
            movie_title = filename
        
        return movie_title
    
    def _fetch_file_size_background(self, url, movie_key):
        try:
            import urllib.request
            req = urllib.request.Request(url, method='HEAD')
            req.add_header('User-Agent', 'Mozilla/5.0')
            
            with urllib.request.urlopen(req, timeout=5) as response:
                size_bytes = response.headers.get('Content-Length')
                if size_bytes:
                    size_bytes = int(size_bytes)
                    file_size = self._format_file_size(size_bytes)
                    
                    positions = load_positions()
                    if movie_key in positions:
                        positions[movie_key]["file_size"] = file_size
                        save_positions(positions)
                        self._schedule_ui(self._refresh_table)
        except Exception:
            pass
    
    def _get_file_size_cached(self, url, data):
        return data.get("file_size", "-")
    
    def _get_file_size(self, url):
        positions = load_positions()
        if url in positions and "file_size" in positions[url]:
            return positions[url]["file_size"]
        
        try:
            import urllib.request
            req = urllib.request.Request(url, method='HEAD')
            req.add_header('User-Agent', 'Mozilla/5.0')
            
            with urllib.request.urlopen(req, timeout=3) as response:
                size_bytes = response.headers.get('Content-Length')
                if size_bytes:
                    size_bytes = int(size_bytes)
                    positions[url]["file_size"] = self._format_file_size(size_bytes)
                    save_positions(positions)
                    return self._format_file_size(size_bytes)
        except Exception:
            pass
        
        return "-"
    
    def _format_file_size(self, bytes_size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                if unit == 'B':
                    return f"{bytes_size:.0f}{unit}"
                return f"{bytes_size:.1f}{unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f}PB"
    
    def _extract_filename_from_url(self, url):
        clean_url = url.split('?')[0].split('#')[0]
        filename = clean_url.split('/')[-1]
        
        if not filename or len(filename) < 3:
            return url
        
        return filename
    
    def _refresh_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        positions = load_positions()
        sorted_items = sorted(positions.items(),
                              key=lambda x: x[1].get("updated", ""), reverse=True)
        for key, data in sorted_items:
            ts = data.get("timestamp", "?")
            updated = data.get("updated", "?")
            
            if "current_url" in data or "urls" in data:
                movie_name = key
                url = data.get("current_url", "")
                if not url and "urls" in data and data["urls"]:
                    url = data["urls"][0]
            else:
                url = key
                movie_name = ""
            
            if url:
                raw_filename = self._extract_filename_from_url(url)
                if not movie_name:
                    movie_name = self._parse_movie_name(raw_filename)
            else:
                raw_filename = movie_name
            
            quality = self._extract_quality(raw_filename)
            source = self._extract_source(raw_filename)
            
            file_size = data.get("file_size", "-")
            
            if file_size == "-" and url:
                import threading
                thread = threading.Thread(
                    target=self._fetch_file_size_background,
                    args=(url, key),
                    daemon=True
                )
                thread.start()
            
            display_movie_name = movie_name
            if len(display_movie_name) > 30:
                display_movie_name = display_movie_name[:27] + "..."
            if len(raw_filename) > 35:
                display_filename = raw_filename[:32] + "..."
            else:
                display_filename = raw_filename
            
            url_count = len(data.get("urls", [url] if url else []))
            if url_count > 1:
                display_movie_name += f" ({url_count} sources)"
            
            self.tree.insert("", tk.END, 
                           values=(display_movie_name, display_filename, quality, source, file_size, ts, updated),
                           tags=(key,))

    
    def _play(self):
        url = self.url_var.get().strip()
        if not url:
            self._set_status("Enter a URL first", FG_DIM)
            return
        self._launch_url(url)

    def _paste_and_play(self):
        try:
            url = self.root.clipboard_get().strip()
        except tk.TclError:
            self._set_status("Clipboard is empty", YELLOW)
            return
        if not url:
            self._set_status("Clipboard is empty", YELLOW)
            return
        self.url_var.set(url)
        self._launch_url(url)

    def _launch_url(self, url):
        if not self.potplayer_path:
            messagebox.showerror("PotPlayer Not Found",
                                 "Could not find PotPlayer.\n"
                                 "Use Settings to configure the path.")
            return

        if self.monitoring:
            self._set_status("Already monitoring a session", YELLOW)
            return

        self.current_url = url
        self.last_position_secs = 0

        # Extract movie name from URL
        clean_url = url.split('?')[0].split('#')[0]
        raw_filename = clean_url.split('/')[-1]
        movie_name = self._parse_movie_name(raw_filename)
        self.current_movie_name = movie_name

        # Check for saved position by movie name
        positions = load_positions()
        saved = positions.get(movie_name)
        cmd = [self.potplayer_path, url]

        if saved:
            ts = saved["timestamp"]
            cmd.append(f"/seek={ts}")
            if "current_url" in saved and saved["current_url"] != url:
                self._set_status(f"Resuming '{movie_name}' from {ts} (different source)...", GREEN)
            else:
                self._set_status(f"Resuming from {ts}...", GREEN)
        else:
            self._set_status("Starting from beginning...", ACCENT)

        # Launch PotPlayer
        try:
            subprocess.Popen(cmd)
        except OSError as e:
            self._set_status(f"Failed to launch: {e}", RED)
            return

        # Start monitoring in background thread
        self.monitoring = True
        self.play_btn.configure(state=tk.DISABLED, bg=BORDER)
        self.paste_btn.configure(state=tk.DISABLED)

        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self._poll_monitor()

    def _monitor_loop(self):
        time.sleep(3)
        consecutive_failures = 0
        max_failures = 20

        while self.monitoring:
            if not is_potplayer_process_alive():
                self.monitoring = False
                self._schedule_ui(self._on_potplayer_closed)
                return

            hwnd = find_potplayer_hwnd()
            if not hwnd:
                consecutive_failures += 1
                if consecutive_failures > max_failures:
                    self.monitoring = False
                    self._schedule_ui(self._on_potplayer_closed)
                    return
                time.sleep(POLL_INTERVAL)
                continue

            consecutive_failures = 0
            pos_ms = get_potplayer_position_ms(hwnd)
            dur_ms = get_potplayer_duration_ms(hwnd)

            if pos_ms is not None and pos_ms >= 0:
                pos_secs = pos_ms // 1000
                dur_secs = (dur_ms // 1000) if dur_ms else 0
                if pos_secs > 5:
                    self.last_position_secs = pos_secs
                self._schedule_ui(lambda p=pos_secs, d=dur_secs: self._update_position(p, d))

            time.sleep(POLL_INTERVAL)

    def _schedule_ui(self, callback):
        try:
            self.root.after(0, callback)
        except tk.TclError:
            pass

    def _poll_monitor(self):
        if self.monitoring:
            self.root.after(500, self._poll_monitor)

    def _update_position(self, pos_secs, dur_secs):
        pos_ts = seconds_to_timestamp(pos_secs)
        dur_ts = seconds_to_timestamp(dur_secs) if dur_secs > 0 else "??:??:??"
        self.position_label.configure(text=f"{pos_ts}  /  {dur_ts}")
        self._set_status("Playing...", GREEN)

        if dur_secs > 0:
            pct = (pos_secs / dur_secs) * 100
            self.progress_var.set(min(pct, 100))
        else:
            self.progress_var.set(0)

    def _on_potplayer_closed(self):
        self.monitoring = False
        self.play_btn.configure(state=tk.NORMAL, bg=ACCENT)
        self.paste_btn.configure(state=tk.NORMAL)

        if self.last_position_secs > 0 and self.current_url:
            ts = seconds_to_timestamp(self.last_position_secs)
            save_position(self.current_url, ts)
            self._set_status(f"Saved position: {ts}", GREEN)
            self.position_label.configure(text=ts)
        else:
            self._set_status("PotPlayer closed (no position to save)", FG_DIM)
            self.position_label.configure(text="")

        self.progress_var.set(0)
        self._refresh_table()

    def _set_status(self, text, color=FG_DIM):
        self.status_label.configure(text=text, fg=color)

    
    def _on_tree_double_click(self, event):
        self._play_selected()

    def _on_tree_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.ctx_menu.tk_popup(event.x_root, event.y_root)

    def _get_selected_movie_name(self):
        sel = self.tree.selection()
        if not sel:
            return None
        item = sel[0]
        tags = self.tree.item(item, "tags")
        key = tags[0] if tags else None
        
        if not key:
            return None
        
        positions = load_positions()
        if key in positions:
            data = positions[key]
            if "current_url" in data or "urls" in data:
                return key
            else:
                raw_filename = self._extract_filename_from_url(key)
                return self._parse_movie_name(raw_filename)
        
        return key

    def _play_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        item = sel[0]
        tags = self.tree.item(item, "tags")
        key = tags[0] if tags else None
        
        if not key:
            return
        
        positions = load_positions()
        if key not in positions:
            return
        
        data = positions[key]
        
        if "current_url" in data or "urls" in data:
            url = data.get("current_url")
            if not url and "urls" in data:
                url = data["urls"][0]
        else:
            url = key
        
        if url:
            self.url_var.set(url)
            self._launch_url(url)

    def _copy_selected_url(self):
        sel = self.tree.selection()
        if not sel:
            return
        item = sel[0]
        tags = self.tree.item(item, "tags")
        key = tags[0] if tags else None
        
        if not key:
            return
        
        positions = load_positions()
        if key not in positions:
            return
        
        data = positions[key]
        
        if "current_url" in data or "urls" in data:
            url = data.get("current_url")
            if not url and "urls" in data:
                url = data["urls"][0]
        else:
            url = key
        
        if url:
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self._set_status("URL copied to clipboard", ACCENT)

    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        item = sel[0]
        tags = self.tree.item(item, "tags")
        key = tags[0] if tags else None
        
        if key:
            positions = load_positions()
            if key in positions:
                del positions[key]
                save_positions(positions)
                self._refresh_table()
                self._set_status("Position deleted", FG_DIM)

    def _clear_all(self):
        positions = load_positions()
        if not positions:
            self._set_status("No saved positions to clear", FG_DIM)
            return
        if messagebox.askyesno("Clear All",
                               f"Delete all {len(positions)} saved positions?"):
            if os.path.exists(POSITIONS_FILE):
                os.remove(POSITIONS_FILE)
            self._refresh_table()
            self._set_status("All positions cleared", FG_DIM)
    
    
    def _show_settings(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Settings")
        dialog.geometry("600x300")
        dialog.configure(bg=BG)
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="Settings", bg=BG, fg=FG,
                 font=("Segoe UI", 14, "bold")).pack(pady=16)
        
        content = tk.Frame(dialog, bg=BG, padx=24)
        content.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(content, text="PotPlayer Path", bg=BG, fg=FG,
                 font=("Segoe UI", 11, "bold"), anchor=tk.W).pack(fill=tk.X, pady=(0, 8))
        
        settings = load_settings()
        current_path = settings.get("potplayer_path", "")
        if not current_path:
            current_path = self.potplayer_path or "Not found"
        
        path_frame = tk.Frame(content, bg=BG)
        path_frame.pack(fill=tk.X, pady=(0, 8))
        
        path_var = tk.StringVar(value=current_path)
        path_entry = tk.Entry(
            path_frame, textvariable=path_var,
            bg=BG_ENTRY, fg=FG, insertbackground=FG,
            font=("Consolas", 9), relief=tk.FLAT,
            highlightthickness=1, highlightbackground=BORDER,
        )
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        
        def browse_path():
            from tkinter import filedialog
            filename = filedialog.askopenfilename(
                title="Select PotPlayer Executable",
                filetypes=[("Executable", "*.exe"), ("All Files", "*.*")],
                initialdir="C:\\Program Files"
            )
            if filename:
                path_var.set(filename)
        
        browse_btn = tk.Button(
            path_frame, text="Browse", command=browse_path,
            bg=BG_SECONDARY, fg=FG, font=("Segoe UI", 9),
            relief=tk.FLAT, padx=12, pady=4, cursor="hand2",
        )
        browse_btn.pack(side=tk.LEFT, padx=(8, 0))
        
        def auto_detect():
            path = find_potplayer()
            if path:
                path_var.set(path)
                messagebox.showinfo("Found", f"PotPlayer found at:\n{path}")
            else:
                messagebox.showerror("Not Found", "Could not find PotPlayer installation")
        
        auto_btn = tk.Button(
            content, text="Auto-Detect PotPlayer", command=auto_detect,
            bg=BG_SECONDARY, fg=FG, font=("Segoe UI", 9),
            relief=tk.FLAT, padx=12, pady=6, cursor="hand2",
        )
        auto_btn.pack(fill=tk.X, pady=(0, 16))
        
        info_text = "Specify the path to PotPlayerMini64.exe or PotPlayerMini.exe"
        tk.Label(content, text=info_text, bg=BG, fg=FG_DIM,
                 font=("Segoe UI", 9), wraplength=500, justify=tk.LEFT).pack(fill=tk.X)
        
        btn_frame = tk.Frame(dialog, bg=BG, padx=24, pady=16)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        def save_and_close():
            new_path = path_var.get().strip()
            if new_path and new_path != "Not found":
                if os.path.exists(new_path):
                    settings = load_settings()
                    settings["potplayer_path"] = new_path
                    save_settings(settings)
                    self.potplayer_path = new_path
                    messagebox.showinfo("Saved", "Settings saved successfully!")
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", "File does not exist!")
            else:
                messagebox.showerror("Error", "Please select a valid PotPlayer path")
        
        save_btn = tk.Button(
            btn_frame, text="Save", command=save_and_close,
            bg=ACCENT, fg="#11111b", font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT, padx=20, pady=8, cursor="hand2",
        )
        save_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        cancel_btn = tk.Button(
            btn_frame, text="Cancel", command=dialog.destroy,
            bg=BG_SECONDARY, fg=FG, font=("Segoe UI", 10),
            relief=tk.FLAT, padx=20, pady=8, cursor="hand2",
        )
        cancel_btn.pack(side=tk.LEFT)

    def _on_close(self):
        self.monitoring = False
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    PotPlayerResumeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
