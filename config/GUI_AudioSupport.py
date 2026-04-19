import os
import wave
import numpy as np
import random
from PyQt6.QtCore import Qt,QTimer
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QFrame, QSlider
)
from PyQt6.QtGui import QFont, QPainter, QColor, QBrush
import vlc


class StaticWaveformWidget(QWidget):
    def __init__(self):
        """
        Initializes the waveform visualizer.
        Sets a fixed height and prepares an empty list to store normalized amplitude data (bars).
        """
        super().__init__()
        self.setFixedHeight(40)
        self.bars = []
        self.progress = 0.0

    def generate_from_file(self, path):
        """
        Extracts raw peak data from a WAV file to create a visual representation.
        Uses the 'wave' module to read frames, normalizes the 16-bit PCM data,
        and averages segments into a 60-bar visualization.
        """
        try:
            with wave.open(path, 'rb') as w:
                frames = w.readframes(w.getnframes())
                samples = np.frombuffer(frames, dtype=np.int16)

                # Downmix stereo to mono by taking every second sample
                if w.getnchannels() == 2:
                    samples = samples[::2]

                num_bars = 60
                chunk_size = len(samples) // num_bars
                if chunk_size == 0:
                    self.bars = [0.1] * num_bars
                    return

                new_bars = []
                for i in range(num_bars):
                    # Calculate the peak amplitude for this chunk of audio
                    chunk = samples[i * chunk_size: (i + 1) * chunk_size]
                    if len(chunk) > 0:
                        peak = np.max(np.abs(chunk)) / 32768.0
                        new_bars.append(max(0.1, peak))
                    else:
                        new_bars.append(0.1)
                self.bars = new_bars
        except Exception:
            # Fallback to a static low-level waveform if file reading fails
            self.bars = [0.2] * 60
        self.update()

    def set_progress(self, percentage):
        """Updates the playback progress (0.0 to 1.0) and triggers a repaint to color the bars."""
        self.progress = percentage
        self.update()

    def clear(self):
        """Resets the waveform data and progress tracker to empty states."""
        self.bars = []
        self.progress = 0.0
        self.update()

    def paintEvent(self, event):
        """
        Custom drawing logic that renders the audio bars.
        Bars are centered vertically and colored blue if they have been 'played'
        based on the current progress percentage.
        """
        if not self.bars: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        gap = 2
        bar_w = (w - (len(self.bars) * gap)) / len(self.bars)

        for i, val in enumerate(self.bars):
            bar_h = h * val
            x, y = i * (bar_w + gap), (h - bar_h) / 2

            # Determine color: blue for played, dark gray for remaining
            color = QColor("#58a6ff") if (i / len(self.bars)) <= self.progress else QColor("#30363d")
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(int(x), int(y), int(bar_w), int(bar_h), 1, 1)


class AudioPlayerWidget(QFrame):
    def __init__(self):
        """
        Initializes the compact audio player UI and the VLC media instance.
        Sets up the layout for playback controls, waveform visualization, and timestamp tracking.
        """
        super().__init__()
        self.setFixedWidth(280)
        self.setFixedHeight(185)

        self.current_file_path = None
        self.pending_seek = -1

        # VLC State Constants mapped to integers for robust state checking
        self.VLC_NOTHING = 0
        self.VLC_OPENING = 1
        self.VLC_BUFFERING = 2
        self.VLC_PLAYING = 3
        self.VLC_PAUSED = 4
        self.VLC_STOPPED = 5
        self.VLC_ENDED = 6
        self.VLC_ERROR = 7

        self.setStyleSheet("""
            QFrame { 
                background: #0d1117; 
                border: 1px solid #30363d; 
                border-radius: 8px; 
            }
            QLabel { color: #c9d1d9; border: none; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(5)

        # --- Top Bar with Title and Close Button ---
        top_layout = QHBoxLayout()
        self.title_label = QLabel("No Audio Loaded")
        self.title_label.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #8b949e;")

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(22, 22)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f85149;
                color: white;
                border-radius: 11px;
                font-size: 11px;
                font-family: 'Arial';
                font-weight: bold;
                border: none;
                padding: 0px;
            }
            QPushButton:hover { background-color: #da3633; }
        """)
        self.close_btn.clicked.connect(self.close_and_stop)

        top_layout.addWidget(self.title_label)
        top_layout.addStretch()
        top_layout.addWidget(self.close_btn)

        # --- Playback Toggle Control ---
        controls_layout = QHBoxLayout()
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(40, 40)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #3165a1;
                color: white;
                border-radius: 20px;
                font-size: 16px;
                border: none;
            }
            QPushButton:hover { background-color: #388bfd; }
        """)
        self.play_btn.clicked.connect(self.toggle_playback)
        controls_layout.addStretch()
        controls_layout.addWidget(self.play_btn)
        controls_layout.addStretch()

        # --- Waveform Display & Seek Slider ---
        self.waveform = StaticWaveformWidget()
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #30363d;
                height: 4px;
                background: #21262d;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #58a6ff;
                width: 10px;
                height: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }
        """)
        self.seek_slider.sliderMoved.connect(self.set_position)

        # --- Timer Display Labels ---
        time_layout = QHBoxLayout()
        timer_style = "color: #8b949e; font-size: 10px; font-family: 'Consolas', 'Monospace';"
        self.current_time_label = QLabel("00:00")
        self.total_time_label = QLabel("00:00")
        self.current_time_label.setStyleSheet(timer_style)
        self.total_time_label.setStyleSheet(timer_style)

        time_layout.addWidget(self.current_time_label)
        time_layout.addStretch()
        time_layout.addWidget(self.total_time_label)

        layout.addLayout(top_layout)
        layout.addLayout(controls_layout)
        layout.addWidget(self.waveform)
        layout.addWidget(self.seek_slider)
        layout.addLayout(time_layout)

        # VLC Instance and asynchronous UI update timer
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(100)

    def format_time(self, ms):
        """Converts milliseconds into a formatted MM:SS string."""
        seconds = (ms // 1000) % 60
        minutes = (ms // 60000) % 60
        return f"{minutes:02}:{seconds:02}"

    def close_and_stop(self):
        """Terminates audio playback and hides the widget."""
        self.player.stop()
        self.hide()

    def load_file(self, path, name):
        """
        Loads a new audio file into the player.
        Generates actual waveform data for WAV files or random placeholders for other formats.
        Starts immediate playback and updates the UI header.
        """
        if os.path.exists(path):
            self.current_file_path = path
            self.player.stop()
            self.pending_seek = -1
            self.current_time_label.setText("00:00")
            self.seek_slider.setValue(0)
            self.title_label.setText(os.path.basename(path))

            # Process waveform visualization
            if path.lower().endswith('.wav'):
                self.waveform.generate_from_file(path)
            else:
                self.waveform.bars = [random.uniform(0.3, 0.7) for _ in range(60)]
                self.waveform.update()

            media = self.instance.media_new(path)
            self.player.set_media(media)
            self.player.play()
            self.play_btn.setText("⏸")
            self.show()

    def set_position(self, position):
        """
        Calculates the new seek target from the slider and instructs VLC to move the playhead.
        Also updates the waveform visual progress immediately for better responsiveness.
        """
        self.pending_seek = position
        self.current_time_label.setText(self.format_time(position))

        length = self.player.get_length()
        if length > 0:
            self.waveform.set_progress(position / length)

        state = self.player.get_state().value
        if state in (self.VLC_PLAYING, self.VLC_PAUSED):
            self.player.set_time(position)

    def toggle_playback(self):
        """Switches between Play and Pause states. If the track is finished or stopped, it reloads the media."""
        state = self.player.get_state().value

        if state in (self.VLC_ENDED, self.VLC_STOPPED, self.VLC_NOTHING):
            if self.current_file_path:
                media = self.instance.media_new(self.current_file_path)
                self.player.set_media(media)
            self.player.play()
            self.play_btn.setText("⏸")

        elif state == self.VLC_PLAYING:
            self.player.pause()
            self.play_btn.setText("▶")
        else:
            self.player.play()
            self.play_btn.setText("⏸")

    def update_ui(self):
        """
        Recurring UI update loop (every 100ms).
        Synchronizes the slider position and time labels with the actual VLC playhead position.
        Handles the 'pending seek' logic to ensure rapid seek commands are eventually settled by the engine.
        """
        state = self.player.get_state().value
        length = self.player.get_length()

        if state == self.VLC_ENDED:
            self.play_btn.setText("▶")
            return

        # Continuous polling for the pending seek to handle VLC's async timing
        if self.pending_seek != -1 and state in (self.VLC_PLAYING, self.VLC_PAUSED):
            if length > 0:
                self.player.set_time(self.pending_seek)
                curr = self.player.get_time()
                # Clear seek flag once the engine has caught up
                if abs(curr - self.pending_seek) < 1000:
                    self.pending_seek = -1
            return

        # Regular sync between VLC head and UI sliders/labels
        if length > 0 and not self.seek_slider.isSliderDown():
            t = self.player.get_time()
            if t >= 0:
                self.seek_slider.setMaximum(length)
                self.seek_slider.setValue(t)
                self.current_time_label.setText(self.format_time(t))
                self.total_time_label.setText(self.format_time(length))
                self.waveform.set_progress(t / length)