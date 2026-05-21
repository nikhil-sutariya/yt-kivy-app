from functools import partial
import os
import re
import threading
from urllib.parse import parse_qs, urlparse

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.image import Image
from kivy.utils import platform

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDIcon, MDLabel
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.screen import MDScreen
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.textfield import MDTextField

from yt_dlp import YoutubeDL

# Import Android-specific modules only on Android
if platform == "android":
    from android.permissions import Permission, request_permissions
    from android.storage import app_storage_path


def _project_dir():
    return os.path.dirname(os.path.abspath(__file__))


def _logo_path():
    return os.path.join(_project_dir(), "assets", "youtube_logo.png")


def _url_looks_like_playlist(url):
    """Detect playlist URLs including watch?v=…&list=… links."""
    if not url or not url.strip():
        return False
    low = url.strip().lower()
    if "playlist?" in low or "/playlist/" in low:
        return True
    try:
        q = parse_qs(urlparse(url.strip()).query)
        return bool(q.get("list"))
    except Exception:
        return False


class SplashScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.layout = MDBoxLayout(
            orientation="vertical",
            spacing=dp(20),
            padding=dp(20),
            size_hint=(1, 1),
        )

        logo_src = _logo_path()
        if os.path.isfile(logo_src):
            self.logo = Image(
                source=logo_src,
                size_hint=(None, None),
                size=(dp(200), dp(200)),
                pos_hint={"center_x": 0.5, "center_y": 0.5},
                opacity=0,
            )
        else:
            self.logo = MDIcon(
                icon="youtube",
                theme_font_size="128sp",
                size_hint=(None, None),
                size=(dp(200), dp(200)),
                pos_hint={"center_x": 0.5, "center_y": 0.5},
                opacity=0,
            )

        self.app_name = MDLabel(
            text="YouTube Downloader",
            halign="center",
            font_style="H4",
            size_hint_y=None,
            height=dp(50),
            opacity=0,
        )

        self.spinner = MDSpinner(
            size_hint=(None, None),
            size=(dp(46), dp(46)),
            pos_hint={"center_x": 0.5, "center_y": 0.3},
        )

        self.layout.add_widget(self.logo)
        self.layout.add_widget(self.app_name)
        self.layout.add_widget(self.spinner)

        self.add_widget(self.layout)

        self.start_animation()

    def start_animation(self):
        Animation(opacity=1, duration=1).start(self.logo)
        Animation(opacity=1, duration=1).start(self.app_name)
        Animation(size=(dp(200), dp(200)), duration=1).start(self.logo)


class YouTubeDownloaderApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Red"
        self.theme_cls.theme_style = "Light"
        self.failed_videos = []
        self.dialog = None

        self.splash = SplashScreen()

        Clock.schedule_once(self.show_main_screen, 3)

        return self.splash

    def show_main_screen(self, _dt):
        self.screen = MDScreen()

        self.main_card = MDCard(
            size_hint=(0.9, 0.8),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            padding=dp(20),
            spacing=dp(20),
            elevation=4,
        )

        self.layout = MDBoxLayout(
            orientation="vertical",
            spacing=dp(20),
            padding=dp(10),
        )

        self.title_label = MDLabel(
            text="YouTube Downloader",
            halign="center",
            font_style="H5",
            size_hint_y=None,
            height=dp(48),
        )

        self.url_input = MDTextField(
            hint_text="Enter YouTube URL (video or playlist)",
            size_hint=(1, None),
            height=dp(48),
            mode="rectangle",
        )

        self.audio_container = MDBoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=dp(48),
            spacing=dp(10),
        )

        self.audio_switch_label = MDLabel(
            text="Download as MP3",
            halign="left",
            size_hint_x=0.7,
        )

        self.audio_switch = MDSwitch(size_hint_x=0.3)

        self.download_btn = MDRaisedButton(
            text="Start Download",
            size_hint=(1, None),
            height=dp(48),
            on_release=self.start_download,
        )

        self.progress = MDProgressBar(
            value=0,
            size_hint=(1, None),
            height=dp(10),
        )

        self.status_label = MDLabel(
            text="Ready to download...",
            halign="center",
            size_hint_y=None,
            height=dp(48),
        )

        self.audio_container.add_widget(self.audio_switch_label)
        self.audio_container.add_widget(self.audio_switch)

        self.layout.add_widget(self.title_label)
        self.layout.add_widget(self.url_input)
        self.layout.add_widget(self.audio_container)
        self.layout.add_widget(self.download_btn)
        self.layout.add_widget(self.progress)
        self.layout.add_widget(self.status_label)

        self.main_card.add_widget(self.layout)

        self.screen.add_widget(self.main_card)

        if platform == "android":
            request_permissions(
                [
                    Permission.WRITE_EXTERNAL_STORAGE,
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.INTERNET,
                ]
            )

        self.root.clear_widgets()
        self.root.add_widget(self.screen)

    def show_error_dialog(self, message):
        def _open(_dt):
            if self.dialog:
                self.dialog.dismiss()

            self.dialog = MDDialog(
                title="Error",
                text=str(message),
                buttons=[
                    MDFlatButton(
                        text="OK",
                        on_release=lambda *_args: self.dialog.dismiss(),
                    )
                ],
            )
            self.dialog.open()

        Clock.schedule_once(_open, 0)

    def start_download(self, _instance):
        url = self.url_input.text.strip()
        if not url:
            self.show_error_dialog("Please enter a valid YouTube URL")
            return

        self.progress.value = 5
        self.status_label.text = "Starting download..."
        self.failed_videos = []
        self.download_btn.disabled = True

        threading.Thread(target=self.download_video, args=(url,), daemon=True).start()

    def download_video(self, url):
        try:
            is_audio = self.audio_switch.active
            is_playlist = _url_looks_like_playlist(url)

            if platform == "android":
                app_dir = app_storage_path()
            else:
                app_dir = os.path.expanduser("~/Downloads")

            download_dir = os.path.join(app_dir, "YTDownloads")
            os.makedirs(download_dir, exist_ok=True)

            output_path = os.path.join(
                download_dir,
                "%(playlist_index)s-%(title)s.%(ext)s"
                if is_playlist
                else "%(title)s.%(ext)s",
            )

            format_str = (
                "bestaudio[ext=m4a]/bestaudio/best"
                if is_audio
                else "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
            )

            ydl_opts = {
                "format": format_str,
                "outtmpl": output_path,
                "quiet": True,
                "no_warnings": True,
                "noplaylist": not is_playlist,
                "ignoreerrors": True,
                "progress_hooks": [self.hook],

                # important fix
                "outtmpl_na_placeholder": "unknown",
                "encoding": "utf-8",

                "postprocessors": (
                    [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "192",
                        }
                    ]
                    if is_audio
                    else []
                ),
            }

            self.update_progress(10, "Downloading...")

            import sys

            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            if self.failed_videos:
                failed_text = "\n".join(self.failed_videos)
                self.update_progress(100, f"Some videos failed:\n{failed_text}")
            else:
                self.update_progress(100, "Download completed!")

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.update_progress(0, f"Error: {str(e)}")
            hint = ""
            msg = str(e).lower()
            if "ffmpeg" in msg or "merge" in msg:
                hint = (
                    "\n\nInstall FFmpeg and ensure it is on PATH "
                    "(e.g. brew install ffmpeg on macOS)."
                )
            self.show_error_dialog(f"{e}{hint}")
        finally:
            Clock.schedule_once(lambda _dt: setattr(self.download_btn, "disabled", False))

    @staticmethod
    def _progress_fraction(d):
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        downloaded = d.get("downloaded_bytes")
        if total and downloaded is not None:
            try:
                return max(0.0, min(1.0, downloaded / float(total)))
            except (TypeError, ZeroDivisionError):
                pass

        raw = d.get("_percent_str") or ""
        raw = re.sub(r"\x1b\[[0-9;]*m", "", raw)
        m = re.search(r"(\d+(?:\.\d+)?)\s*%", raw)
        if m:
            try:
                return max(0.0, min(1.0, float(m.group(1)) / 100.0))
            except ValueError:
                pass
        return None

    def hook(self, d):
        if d["status"] == "downloading":
            frac = self._progress_fraction(d)
            if frac is not None:
                pct = 10.0 + frac * 85.0
                self.update_progress(pct, f"Downloading: {int(frac * 100)}%")
            else:
                self.update_progress(None, "Downloading…")
        elif d["status"] == "error":
            title = d.get("info_dict", {}).get("title", "Unknown")
            self.failed_videos.append(f"✗ {title}")
        elif d["status"] == "finished":
            self.update_progress(95, "Download finished…")

    def update_progress(self, value, message):
        Clock.schedule_once(partial(self._update_ui, value, message))

    def _update_ui(self, value, message, _dt):
        if value is not None:
            self.progress.value = value
        self.status_label.text = message


if __name__ == "__main__":
    YouTubeDownloaderApp().run()
