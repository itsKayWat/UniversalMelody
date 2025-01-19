import customtkinter as ctk
import yt_dlp
import pygame
import pystray
from PIL import Image
import threading
import os
import subprocess
import time
from typing import Dict, List
from tkinter import ttk
import urllib.request
from io import BytesIO
import json

class MusicPlayer:
    def __init__(self):
        self.current_track = None
        self.playlist = []
        self.is_playing = False
        self.current_position = 0
        self.volume = 0.5  # 50% default volume
        self.shuffle_enabled = False
        self.repeat_enabled = False
        self.original_playlist = []  # Store original playlist order for shuffle
        
        pygame.mixer.init()
        pygame.mixer.music.set_volume(self.volume)
        
        # Initialize the main window
        self.window = ctk.CTk()
        self.window.title("Universal Music Player")
        self.window.geometry("1000x700")
        self.window.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        
        # Create main containers
        self.create_main_layout()
        self.setup_system_tray()
        
        # Start update loops
        self.start_progress_update()
        
        # Load saved playlist if exists
        self.load_saved_playlist()

    def create_main_layout(self):
        # Create main frames
        self.left_frame = ctk.CTkFrame(self.window, width=200)
        self.left_frame.pack(side="left", fill="y", padx=10, pady=10)
        
        self.right_frame = ctk.CTkFrame(self.window)
        self.right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        self.setup_left_panel()
        self.setup_right_panel()
        
        # Add detailed instructions label
        self.instructions_label = ctk.CTkLabel(
            self.window,
            text="",
            wraplength=700,
            justify="left"
        )
        self.instructions_label.pack(pady=5)
        
        # Status label
        self.status_label = ctk.CTkLabel(self.window, text="")
        self.status_label.pack(pady=5)
        
        # Check FFmpeg on startup
        if not self.check_ffmpeg():
            self.show_ffmpeg_instructions()

    def setup_left_panel(self):
        # Source selection
        self.source_label = ctk.CTkLabel(self.left_frame, text="Sources")
        self.source_label.pack(pady=5)
        
        sources = ["YouTube", "SoundCloud", "Local Files"]
        self.source_var = ctk.StringVar(value="YouTube")
        
        for source in sources:
            rb = ctk.CTkRadioButton(
                self.left_frame,
                text=source,
                variable=self.source_var,
                value=source,
                command=self.source_changed
            )
            rb.pack(pady=2)
        
        # Volume control
        self.volume_label = ctk.CTkLabel(self.left_frame, text="Volume")
        self.volume_label.pack(pady=(20, 5))
        
        self.volume_slider = ctk.CTkSlider(
            self.left_frame,
            from_=0,
            to=1,
            number_of_steps=100,
            command=self.volume_changed
        )
        self.volume_slider.set(self.volume)
        self.volume_slider.pack(pady=5, padx=10, fill="x")
        
        # Playlist operations
        self.save_playlist_btn = ctk.CTkButton(
            self.left_frame,
            text="Save Playlist",
            command=self.save_playlist
        )
        self.save_playlist_btn.pack(pady=5, padx=10, fill="x")
        
        self.load_playlist_btn = ctk.CTkButton(
            self.left_frame,
            text="Load Playlist",
            command=self.load_playlist
        )
        self.load_playlist_btn.pack(pady=5, padx=10, fill="x")
        
        self.clear_playlist_btn = ctk.CTkButton(
            self.left_frame,
            text="Clear Playlist",
            command=self.clear_playlist
        )
        self.clear_playlist_btn.pack(pady=5, padx=10, fill="x")

    def setup_right_panel(self):
        # Search frame
        self.search_frame = ctk.CTkFrame(self.right_frame)
        self.search_frame.pack(pady=10, padx=10, fill="x")
        
        self.url_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="Enter URL or search term"
        )
        self.url_entry.pack(side="left", expand=True, fill="x", padx=(0, 10))
        
        self.add_button = ctk.CTkButton(
            self.search_frame,
            text="Add to Playlist",
            command=self.add_to_playlist
        )
        self.add_button.pack(side="right")
        
        # Playlist frame
        self.playlist_frame = ctk.CTkFrame(self.right_frame)
        self.playlist_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Create playlist display
        self.playlist_tree = ttk.Treeview(
            self.playlist_frame,
            columns=("Title", "Duration", "Source"),
            show="headings"
        )
        
        self.playlist_tree.heading("Title", text="Title")
        self.playlist_tree.heading("Duration", text="Duration")
        self.playlist_tree.heading("Source", text="Source")
        
        self.playlist_tree.column("Title", width=300)
        self.playlist_tree.column("Duration", width=100)
        self.playlist_tree.column("Source", width=100)
        
        self.playlist_tree.pack(fill="both", expand=True)
        self.playlist_tree.bind("<Double-1>", self.on_playlist_double_click)
        
        # Progress bar and time labels
        self.progress_frame = ctk.CTkFrame(self.right_frame)
        self.progress_frame.pack(fill="x", padx=10, pady=5)
        
        self.time_current = ctk.CTkLabel(self.progress_frame, text="0:00")
        self.time_current.pack(side="left", padx=5)
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=5)
        self.progress_bar.set(0)
        
        self.time_total = ctk.CTkLabel(self.progress_frame, text="0:00")
        self.time_total.pack(side="left", padx=5)
        
        # Controls frame
        self.controls_frame = ctk.CTkFrame(self.right_frame)
        self.controls_frame.pack(pady=10, padx=10, fill="x")
        
        self.prev_button = ctk.CTkButton(
            self.controls_frame,
            text="⏮",
            width=40,
            command=self.previous_track
        )
        self.prev_button.pack(side="left", padx=5)
        
        self.play_button = ctk.CTkButton(
            self.controls_frame,
            text="▶",
            width=40,
            command=self.toggle_play
        )
        self.play_button.pack(side="left", padx=5)
        
        self.next_button = ctk.CTkButton(
            self.controls_frame,
            text="⏭",
            width=40,
            command=self.next_track
        )
        self.next_button.pack(side="left", padx=5)
        
        self.shuffle_button = ctk.CTkButton(
            self.controls_frame,
            text="🔀",
            width=40,
            command=self.toggle_shuffle
        )
        self.shuffle_button.pack(side="left", padx=5)
        
        self.repeat_button = ctk.CTkButton(
            self.controls_frame,
            text="🔁",
            width=40,
            command=self.toggle_repeat
        )
        self.repeat_button.pack(side="left", padx=5)

    def source_changed(self):
        source = self.source_var.get()
        if source == "Local Files":
            self.url_entry.configure(placeholder_text="Click 'Add to Playlist' to browse files")
        else:
            self.url_entry.configure(placeholder_text="Enter URL or search term")

    def volume_changed(self, value):
        self.volume = value
        pygame.mixer.music.set_volume(value)

    def save_playlist(self):
        playlist_data = {
            "tracks": self.playlist
        }
        with open("playlist.json", "w") as f:
            json.dump(playlist_data, f)
        self.show_success("Playlist saved!")

    def load_saved_playlist(self):
        try:
            with open("playlist.json", "r") as f:
                playlist_data = json.load(f)
                self.playlist = playlist_data["tracks"]
                self.original_playlist = self.playlist.copy()
                self.update_playlist_display()
        except FileNotFoundError:
            pass

    def load_playlist(self):
        # Implement playlist loading from file
        pass

    def clear_playlist(self):
        self.playlist = []
        self.original_playlist = []
        self.update_playlist_display()
        self.show_success("Playlist cleared")

    def on_playlist_double_click(self, event):
        selection = self.playlist_tree.selection()
        if selection:
            index = self.playlist_tree.index(selection[0])
            self.current_position = index
            self.play_current_track()

    def start_progress_update(self):
        def update_progress():
            while True:
                if self.is_playing and pygame.mixer.music.get_busy():
                    current_time = pygame.mixer.music.get_pos() / 1000  # Convert to seconds
                    self.progress_bar.set(current_time / self.current_track_length)
                    self.time_current.configure(text=self.format_time(current_time))
                time.sleep(0.1)

        self.progress_thread = threading.Thread(target=update_progress, daemon=True)
        self.progress_thread.start()

    def format_time(self, seconds):
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes}:{seconds:02d}"

    def minimize_to_tray(self):
        self.window.withdraw()
        self.icon.visible = True

    def setup_system_tray(self):
        self.icon_image = Image.new('RGB', (64, 64), color='red')
        self.icon = pystray.Icon(
            "music_player",
            self.icon_image,
            menu=pystray.Menu(
                pystray.MenuItem("Show", self.show_window),
                pystray.MenuItem("Exit", self.quit_app)
            )
        )
        threading.Thread(target=self.icon.run, daemon=True).start()

    def show_ffmpeg_instructions(self):
        """Show detailed FFmpeg installation instructions"""
        import platform
        
        system = platform.system()
        if system == "Windows":
            instructions = """
FFmpeg is not installed. Please follow these steps:
1. Download FFmpeg from: https://github.com/BtbN/FFmpeg-Builds/releases
2. Download the 'ffmpeg-master-latest-win64-gpl.zip'
3. Extract the zip file to a location like 'C:\\ffmpeg'
4. Add the bin folder (e.g., 'C:\\ffmpeg\\bin') to your System PATH:
   - Open System Properties → Advanced → Environment Variables
   - Under System Variables, find and select 'Path'
   - Click Edit → New → Add the bin folder path
   - Click OK on all windows
5. Restart this application
"""
        elif system == "Darwin":  # macOS
            instructions = """
FFmpeg is not installed. Please follow these steps:
1. Install Homebrew if you haven't already:
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
2. Install FFmpeg using Homebrew:
   brew install ffmpeg
3. Restart this application
"""
        else:  # Linux
            instructions = """
FFmpeg is not installed. Please follow these steps:
1. Open terminal
2. Run: sudo apt-get update
3. Run: sudo apt-get install ffmpeg
4. Restart this application
"""
        
        self.instructions_label.configure(text=instructions)

    def check_ffmpeg(self) -> bool:
        """Check if FFmpeg is installed and accessible"""
        try:
            # Try multiple possible ffmpeg commands
            for cmd in ['ffmpeg', 'ffmpeg.exe']:
                try:
                    result = subprocess.run(
                        [cmd, '-version'],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        self.show_success("FFmpeg found and working!")
                        self.instructions_label.configure(text="")  # Clear instructions
                        return True
                except FileNotFoundError:
                    continue
            
            self.show_error("FFmpeg not found! See instructions below.")
            return False
            
        except Exception as e:
            self.show_error(f"Error checking FFmpeg: {str(e)}")
            return False

    def show_error(self, message: str):
        """Display error message in the UI"""
        self.status_label.configure(text=message, text_color="red")
        
    def show_success(self, message: str):
        """Display success message in the UI"""
        self.status_label.configure(text=message, text_color="green")

    def download_track(self, url: str) -> Dict:
        if not self.check_ffmpeg():
            self.show_ffmpeg_instructions()
            raise Exception("FFmpeg is required but not installed")
            
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.show_success("Downloading track...")
                info = ydl.extract_info(url, download=True)
                self.show_success("Download complete!")
                return info
        except Exception as e:
            error_message = str(e)
            if "ffmpeg" in error_message.lower():
                self.show_error("FFmpeg error: Please install FFmpeg to continue")
            else:
                self.show_error(f"Download error: {error_message}")
            raise

    def add_to_playlist(self):
        url = self.url_entry.get()
        if not url:
            self.show_error("Please enter a URL")
            return
            
        try:
            info = self.download_track(url)
            self.playlist.append({
                'title': info['title'],
                'path': f"downloads/{info['title']}.mp3"
            })
            self.original_playlist = self.playlist.copy()
            self.update_playlist_display()
            self.show_success(f"Added: {info['title']}")
            self.url_entry.delete(0, 'end')  # Clear the entry
        except Exception as e:
            print(f"Error adding track: {e}")

    def toggle_play(self):
        if not self.is_playing and self.playlist:
            self.play_current_track()
        elif self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
            self.play_button.configure(text="Play")
        else:
            pygame.mixer.music.unpause()
            self.is_playing = True
            self.play_button.configure(text="Pause")

    def play_current_track(self):
        if self.playlist:
            track = self.playlist[self.current_position]
            try:
                pygame.mixer.music.load(track['path'])
                pygame.mixer.music.play()
                self.is_playing = True
                self.play_button.configure(text="⏸")
                
                # Set up end of track handling
                pygame.mixer.music.set_endevent(pygame.USEREVENT)
                threading.Thread(target=self.check_track_end, daemon=True).start()
                
                # Update UI
                self.show_success(f"Now playing: {track['title']}")
                self.update_playlist_display()
            except Exception as e:
                self.show_error(f"Error playing track: {str(e)}")

    def next_track(self):
        """Play next track considering shuffle and repeat modes"""
        if not self.playlist:
            return
            
        if self.current_position + 1 >= len(self.playlist):
            if self.repeat_enabled:
                self.current_position = 0
            else:
                return
        else:
            self.current_position += 1
            
        self.play_current_track()

    def previous_track(self):
        """Play previous track considering shuffle and repeat modes"""
        if not self.playlist:
            return
            
        if self.current_position - 1 < 0:
            if self.repeat_enabled:
                self.current_position = len(self.playlist) - 1
            else:
                return
        else:
            self.current_position -= 1
            
        self.play_current_track()

    def check_track_end(self):
        """Check for track end and handle next track"""
        while True:
            for event in pygame.event.get():
                if event.type == pygame.USEREVENT:
                    # Track ended
                    if self.repeat_enabled:
                        # If repeat is enabled, play next track or restart playlist
                        self.next_track()
                    elif self.current_position + 1 < len(self.playlist):
                        # If there are more tracks, play next
                        self.next_track()
                    else:
                        # End of playlist
                        self.is_playing = False
                        self.play_button.configure(text="▶")
            time.sleep(0.1)

    def toggle_shuffle(self):
        """Toggle shuffle mode for playlist"""
        self.shuffle_enabled = not self.shuffle_enabled
        
        if self.shuffle_enabled:
            # Store original playlist and create shuffled version
            import random
            self.original_playlist = self.playlist.copy()
            random.shuffle(self.playlist)
            self.shuffle_button.configure(fg_color="green")
            self.show_success("Shuffle enabled")
        else:
            # Restore original playlist order
            if self.original_playlist:
                current_track = self.playlist[self.current_position] if self.playlist else None
                self.playlist = self.original_playlist.copy()
                # Maintain current track position
                if current_track:
                    self.current_position = self.playlist.index(current_track)
            self.shuffle_button.configure(fg_color=("gray75", "gray30"))
            self.show_success("Shuffle disabled")
        
        self.update_playlist_display()

    def toggle_repeat(self):
        """Toggle repeat mode for playlist"""
        self.repeat_enabled = not self.repeat_enabled
        if self.repeat_enabled:
            self.repeat_button.configure(fg_color="green")
            self.show_success("Repeat enabled")
        else:
            self.repeat_button.configure(fg_color=("gray75", "gray30"))
            self.show_success("Repeat disabled")

    def update_playlist_display(self):
        # Update the playlist display (implement this based on your UI needs)
        pass

    def show_window(self):
        self.window.deiconify()

    def quit_app(self):
        self.window.quit()
        self.icon.stop()

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    # Create downloads directory if it doesn't exist
    os.makedirs("downloads", exist_ok=True)
    
    player = MusicPlayer()
    player.run() 