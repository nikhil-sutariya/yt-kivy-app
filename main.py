from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.spinner import MDSpinner

from yt_dlp import YoutubeDL
import os
import threading
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.uix.image import Image
from kivy.metrics import dp
from kivy.utils import platform

# Import Android-specific modules only on Android
if platform == 'android':
    from android.permissions import request_permissions, Permission
    from android.storage import app_storage_path

class SplashScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Create main layout
        self.layout = MDBoxLayout(
            orientation='vertical',
            spacing=dp(20),
            padding=dp(20),
            size_hint=(1, 1)
        )
        
        # Add logo
        self.logo = Image(
            source='youtube_logo.png',
            size_hint=(None, None),
            size=(dp(200), dp(200)),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        
        # Add app name
        self.app_name = MDLabel(
            text="YouTube Downloader",
            halign="center",
            font_style="H4",
            size_hint_y=None,
            height=dp(50)
        )
        
        # Add loading spinner
        self.spinner = MDSpinner(
            size_hint=(None, None),
            size=(dp(46), dp(46)),
            pos_hint={'center_x': 0.5, 'center_y': 0.3}
        )
        
        # Add widgets to layout
        self.layout.add_widget(self.logo)
        self.layout.add_widget(self.app_name)
        self.layout.add_widget(self.spinner)
        
        # Add layout to screen
        self.add_widget(self.layout)
        
        # Start animation
        self.start_animation()
    
    def start_animation(self):
        # Fade in animation
        anim = Animation(opacity=1, duration=1)
        anim.start(self.logo)
        anim.start(self.app_name)
        
        # Scale animation for logo
        scale_anim = Animation(size=(dp(200), dp(200)), duration=1)
        scale_anim.start(self.logo)

class YouTubeDownloaderApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Red"
        self.theme_cls.theme_style = "Light"
        self.failed_videos = []
        self.dialog = None

        # Create splash screen
        self.splash = SplashScreen()
        
        # Schedule main screen after delay
        Clock.schedule_once(self.show_main_screen, 3)
        
        return self.splash
    
    def show_main_screen(self, dt):
        # Create main screen
        self.screen = MDScreen()

        # Create main card
        self.main_card = MDCard(
            size_hint=(0.9, 0.8),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            padding="20dp",
            spacing="20dp",
            elevation=4
        )

        # Create layout for card content
        self.layout = MDBoxLayout(
            orientation="vertical",
            spacing="20dp",
            padding="10dp"
        )

        # Title
        self.title_label = MDLabel(
            text="YouTube Downloader",
            halign="center",
            font_style="H5",
            size_hint_y=None,
            height="48dp"
        )

        # URL Input
        self.url_input = MDTextField(
            hint_text="Enter YouTube URL (video or playlist)",
            size_hint=(1, None),
            height="48dp",
            mode="rectangle"
        )

        # Audio switch container
        self.audio_container = MDBoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height="48dp",
            spacing="10dp"
        )

        self.audio_switch_label = MDLabel(
            text="Download as MP3",
            halign="left",
            size_hint_x=0.7
        )

        self.audio_switch = MDSwitch(
            size_hint_x=0.3
        )

        # Download button
        self.download_btn = MDRaisedButton(
            text="Start Download",
            size_hint=(1, None),
            height="48dp",
            on_release=self.start_download
        )

        # Progress bar
        self.progress = MDProgressBar(
            value=0,
            size_hint=(1, None),
            height="10dp"
        )

        # Status label
        self.status_label = MDLabel(
            text="Ready to download...",
            halign="center",
            size_hint_y=None,
            height="48dp"
        )

        # Add widgets to layout
        self.audio_container.add_widget(self.audio_switch_label)
        self.audio_container.add_widget(self.audio_switch)

        self.layout.add_widget(self.title_label)
        self.layout.add_widget(self.url_input)
        self.layout.add_widget(self.audio_container)
        self.layout.add_widget(self.download_btn)
        self.layout.add_widget(self.progress)
        self.layout.add_widget(self.status_label)

        # Add layout to card
        self.main_card.add_widget(self.layout)

        # Add card to screen
        self.screen.add_widget(self.main_card)

        # Request permissions only on Android
        if platform == 'android':
            request_permissions([
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.INTERNET
            ])

        # Switch to main screen with animation
        self.root.clear_widgets()
        self.root.add_widget(self.screen)

    def show_error_dialog(self, message):
        if self.dialog:
            self.dialog.dismiss()
        
        self.dialog = MDDialog(
            title="Error",
            text=message,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: self.dialog.dismiss()
                )
            ]
        )
        self.dialog.open()

    def start_download(self, instance):
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
            is_playlist = "playlist" in url

            # Get download directory based on platform
            if platform == 'android':
                app_dir = app_storage_path()
            else:
                app_dir = os.path.expanduser("~/Downloads")
            
            download_dir = os.path.join(app_dir, "YTDownloads")
            os.makedirs(download_dir, exist_ok=True)

            # Output path for yt-dlp
            output_path = os.path.join(
                download_dir,
                "%(playlist_index)s-%(title)s.%(ext)s" if is_playlist else "%(title)s.%(ext)s"
            )

            format_str = "bestaudio[ext=m4a]/bestaudio/best" if is_audio else "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]"

            ydl_opts = {
                'format': format_str,
                'outtmpl': output_path,
                'quiet': True,
                'noplaylist': not is_playlist,
                'ignoreerrors': True,
                'progress_hooks': [self.hook],
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }] if is_audio else [],
            }

            self.update_progress(10, "Downloading...")

            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            if self.failed_videos:
                failed_text = "\n".join(self.failed_videos)
                self.update_progress(100, f"Some videos failed:\n{failed_text}")
            else:
                self.update_progress(100, "Download completed!")

        except Exception as e:
            self.update_progress(0, f"Error: {str(e)}")
            self.show_error_dialog(str(e))
        finally:
            Clock.schedule_once(lambda dt: setattr(self.download_btn, 'disabled', False))

    def hook(self, d):
        if d['status'] == 'downloading':
            percent = float(d.get('_percent_str', '0.0%').strip('%'))
            self.update_progress(percent, f"Downloading: {int(percent)}%")
        elif d['status'] == 'error':
            title = d.get('info_dict', {}).get('title', 'Unknown')
            self.failed_videos.append(f"❌ {title}")
        elif d['status'] == 'finished':
            self.update_progress(95, "Download finished...")

    def update_progress(self, value, message):
        Clock.schedule_once(lambda dt: self._update_ui(value, message))

    def _update_ui(self, value, message):
        self.progress.value = value
        self.status_label.text = message

if __name__ == '__main__':
    YouTubeDownloaderApp().run()
