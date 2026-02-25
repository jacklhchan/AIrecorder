"""
Main Window
Primary application window with recording controls and visualization.
"""

import os
from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QFileDialog,
    QFrame, QMessageBox, QSizePolicy, QCheckBox, QApplication,
    QSystemTrayIcon, QMenu
)

import subprocess
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QIcon, QAction

from hotkey_manager import HotkeyManager

from audio_engine import AudioEngine, RecordingState, AudioDevice
from video_engine import VideoEngine
from ui.level_meter import LevelMeterWidget
from ui.silence_indicator import SilenceIndicator
from ui.overlay import OverlayWidget


class SignalBridge(QObject):
    """Bridge for thread-safe signal emission from audio engine."""
    level_changed = pyqtSignal(float, float)
    silence_changed = pyqtSignal(bool, float, bool, float)
    error_occurred = pyqtSignal(str)


class MainWindow(QMainWindow):
    """Main application window for the BlackHole Audio Recorder."""
    
    def __init__(self):
        super().__init__()
        
        # Initialize audio engine
        self.audio_engine = AudioEngine()
        if not self.audio_engine.initialize():
            QMessageBox.critical(
                self, "Error", 
                "Failed to initialize audio system.\nMake sure PortAudio is installed."
            )
        
        # Initialize video engine
        self.video_engine = VideoEngine()
        self.is_recording_video = False
        
        # Signal bridge for thread-safe updates
        self.signal_bridge = SignalBridge()
        self.audio_engine.set_level_callback(self._on_level_update)
        self.audio_engine.set_silence_callback(self._on_silence_update)
        self.audio_engine.set_error_callback(self._on_error)
        
        # Recording state
        self.output_directory = os.path.expanduser("~/Music/BlackHole Recordings")
        self._recording_start_time: Optional[datetime] = None
        
        # Hotkey Manager
        self.hotkey_manager = HotkeyManager()
        self.hotkey_manager.toggle_recording.connect(self.toggle_recording)
        try:
            self.hotkey_manager.start()
        except Exception as e:
            print(f"Failed to start hotkey listener (Input Monitoring permission?): {e}")
        
        # System Tray
        self.docks_icon_idle = "⚫" # Simple text icon for now, or use system icon
        self.docks_icon_rec = "🔴"
        self._setup_system_tray()
        
        # Set up UI
        self.setup_ui()
        self.setup_connections()
        self.load_devices()
        self.load_screens()
        
        # Overlay Widget
        self.overlay = OverlayWidget()
        self.overlay.stop_clicked.connect(self.stop_recording)
        
        # Timer for recording duration update
        self.duration_timer = QTimer(self)
        self.duration_timer.timeout.connect(self.update_duration_display)
        
    def _setup_system_tray(self) -> None:
        """Initialize the system tray icon."""
        self.tray_icon = QSystemTrayIcon(self)
        
        # Use a standard icon (QIcon/Theme) or a simple pixmap
        # For simplicity, we'll try to use a system standard icon if available, or just a placeholder.
        # On macOS, QSystemTrayIcon might need a proper .png.
        # Let's create a simple generated pixmap for the dot.
        self._set_tray_icon_color("black")
        
        self.tray_menu = QMenu()
        
        self.tray_action_toggle = QAction("Start Recording", self)
        self.tray_action_toggle.triggered.connect(self.toggle_recording)
        self.tray_menu.addAction(self.tray_action_toggle)
        
        self.tray_action_show = QAction("Show Window", self)
        self.tray_action_show.triggered.connect(self._show_and_raise)
        self.tray_menu.addAction(self.tray_action_show)
        
        self.tray_menu.addSeparator()
        
        self.tray_action_quit = QAction("Quit", self)
        self.tray_action_quit.triggered.connect(QApplication.instance().quit)
        self.tray_menu.addAction(self.tray_action_quit)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()
        
    def _show_and_raise(self) -> None:
        """Show window and bring to front."""
        self.show()
        self.raise_()
        self.activateWindow()

    def _set_tray_icon_color(self, color: str) -> None:
        """Set tray icon color using a generated Pixmap."""
        from PyQt6.QtGui import QPixmap, QPainter, QColor
        pixmap = QPixmap(22, 22)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if color == "red":
             painter.setBrush(QColor("#e11d48"))
        else:
             painter.setBrush(QColor("#000000")) # Dark for menu bar
             
        painter.setPen(Qt.PenStyle.NoPen)
        # Draw circle centered
        painter.drawEllipse(4, 4, 14, 14)
        painter.end()
        
        self.tray_icon.setIcon(QIcon(pixmap))

    def toggle_recording(self) -> None:
        """Toggle recording state (Start/Stop)."""
        if self.audio_engine.state == RecordingState.RECORDING:
            self.stop_recording()
        else:
            self.start_recording()
            
    def setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("BlackHole Audio Recorder")
        self.setWindowTitle("BlackHole Audio Recorder")
        self.setMinimumSize(600, 750)
        self.resize(650, 850)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Apply dark theme
        self.setStyleSheet(self._get_stylesheet())
        
        # === Header ===
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        header_icon = QLabel("🎙️")
        header_icon.setFont(QFont("Apple Color Emoji", 24))
        header_layout.addWidget(header_icon)
        
        header_text = QLabel("BlackHole Audio Recorder")
        header_text.setFont(QFont(".AppleSystemUIFont", 20, QFont.Weight.Bold))
        header_text.setStyleSheet("color: #f8fafc;")
        header_layout.addWidget(header_text)
        header_layout.addStretch()
        
        layout.addWidget(header_container)
        
        # === Sources Section ===
        sources_frame = QFrame()
        sources_frame.setObjectName("cardFrame")
        sources_layout = QVBoxLayout(sources_frame)
        sources_layout.setContentsMargins(16, 16, 16, 20)
        sources_layout.setSpacing(16)
        
        # Section Title
        sources_title = QLabel("AUDIO SOURCES")
        sources_title.setObjectName("sectionTitle")
        sources_layout.addWidget(sources_title)
        
        # Primary Input
        input_row = QVBoxLayout()
        input_row.setSpacing(6)
        input_label = QLabel("System Audio (Input)")
        input_label.setObjectName("helperLabel")
        input_row.addWidget(input_label)
        
        device_row = QHBoxLayout()
        self.device_combo = QComboBox()
        self.device_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        device_row.addWidget(self.device_combo)
        
        self.refresh_btn = QPushButton("⟳")
        self.refresh_btn.setFixedSize(40, 40)
        self.refresh_btn.setToolTip("Refresh device list")
        self.refresh_btn.setObjectName("iconBtn")
        device_row.addWidget(self.refresh_btn)
        input_row.addLayout(device_row)
        sources_layout.addLayout(input_row)
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #1e293b; border: none; height: 1px;")
        sources_layout.addWidget(line)
        
        # Microphone Input
        mic_row = QVBoxLayout()
        mic_row.setSpacing(6)
        
        mic_header = QHBoxLayout()
        self.mic_check = QCheckBox("Enable Microphone Overlay")
        self.mic_check.setCursor(Qt.CursorShape.PointingHandCursor)
        mic_header.addWidget(self.mic_check)
        mic_header.addStretch()
        mic_row.addLayout(mic_header)
        
        self.mic_combo = QComboBox()
        self.mic_combo.setEnabled(False)
        self.mic_combo.setPlaceholderText("Select Microphone...")
        mic_row.addWidget(self.mic_combo)
        
        sources_layout.addLayout(mic_row)
        layout.addWidget(sources_frame)
        
        # === Monitoring Section ===
        monitor_frame = QFrame()
        monitor_frame.setObjectName("cardFrame")
        monitor_layout = QVBoxLayout(monitor_frame)
        monitor_layout.setContentsMargins(16, 16, 16, 20)
        monitor_layout.setSpacing(16)
        
        monitor_title = QLabel("REAL-TIME MONITORING")
        monitor_title.setObjectName("sectionTitle")
        monitor_layout.addWidget(monitor_title)
        
        meters_layout = QVBoxLayout()
        meters_layout.setSpacing(12)
        
        # System Level
        self.sys_level_meter = LevelMeterWidget()
        self.sys_level_meter.label.setText("System Audio")
        meters_layout.addWidget(self.sys_level_meter)
        
        # Mic Level
        self.mic_level_meter = LevelMeterWidget()
        self.mic_level_meter.label.setText("Microphone")
        meters_layout.addWidget(self.mic_level_meter)
        
        monitor_layout.addLayout(meters_layout)
        
        # Indicators
        indicators_frame = QFrame()
        indicators_frame.setStyleSheet("background-color: #020617; border-radius: 8px; padding: 4px;")
        indicators_layout = QHBoxLayout(indicators_frame)
        indicators_layout.setSpacing(12)
        
        self.sys_silence_indicator = SilenceIndicator()
        self.sys_silence_indicator.set_title("SYSTEM SILENCE")
        indicators_layout.addWidget(self.sys_silence_indicator)
        
        self.mic_silence_indicator = SilenceIndicator()
        self.mic_silence_indicator.set_title("MIC SILENCE")
        indicators_layout.addWidget(self.mic_silence_indicator)
        
        monitor_layout.addWidget(indicators_frame)
        layout.addWidget(monitor_frame)
        
        # === Controls Section (Floating Bottom) ===
        controls_frame = QFrame()
        controls_frame.setObjectName("controlsFrame")
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setContentsMargins(16, 16, 16, 16)
        controls_layout.setSpacing(16)
        
        # Top row: Screen Record Switch + Output
        options_row = QHBoxLayout()
        
        self.screen_record_check = QCheckBox("Capture Screen Video")
        self.screen_record_check.setCursor(Qt.CursorShape.PointingHandCursor)
        options_row.addWidget(self.screen_record_check)
        
        self.screen_combo = QComboBox()
        self.screen_combo.setMinimumWidth(150)
        # Always enabled so user can see what's available
        options_row.addWidget(self.screen_combo)
        
        options_row.addStretch()
        
        # Output directory mini-button
        self.change_output_btn = QPushButton("Save to: Music/...")
        self.change_output_btn.setObjectName("ghostBtn")
        self.change_output_btn.setToolTip(self.output_directory)
        self.change_output_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        options_row.addWidget(self.change_output_btn)
        
        controls_layout.addLayout(options_row)
        
        # Timer Display
        time_container = QWidget()
        time_layout = QHBoxLayout(time_container)
        time_layout.setContentsMargins(0,0,0,0)
        
        self.duration_label = QLabel("00:00:00")
        self.duration_label.setFont(QFont("Monaco", 28, QFont.Weight.Bold)) # Monospaced
        self.duration_label.setStyleSheet("color: #f8fafc;")
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Add red dot indicator
        self.rec_dot = QLabel("●")
        self.rec_dot.setStyleSheet("color: #e11d48; font-size: 24px;")
        self.rec_dot.setVisible(False)
        
        time_layout.addStretch()
        time_layout.addWidget(self.rec_dot)
        time_layout.addWidget(self.duration_label)
        time_layout.addStretch()
        
        controls_layout.addWidget(time_container)
        
        # Main Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.record_btn = QPushButton("Start Recording")
        self.record_btn.setObjectName("recordBtn")
        self.record_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.record_btn.setMinimumHeight(48)
        btn_layout.addWidget(self.record_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setMinimumHeight(48)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        controls_layout.addLayout(btn_layout)
        
        # Status Bar
        self.status_label = QLabel("Ready to record")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 500;")
        controls_layout.addWidget(self.status_label)
        
        layout.addWidget(controls_frame)
        
        # Keep references for path updates (hidden label logic removed, using button tooltip/text)
        self.output_label = QLabel() # Dummy to prevent attribute error if accessed elsewhere
        
        # Connect signal bridge
        self.signal_bridge.level_changed.connect(self._update_levels)
        self.signal_bridge.silence_changed.connect(self._update_silence_indicators)
        self.signal_bridge.error_occurred.connect(self._show_error)
    
    def setup_connections(self) -> None:
        """Set up signal-slot connections."""
        self.record_btn.clicked.connect(self.start_recording)
        self.stop_btn.clicked.connect(self.stop_recording)
        self.refresh_btn.clicked.connect(self.load_devices)
        self.refresh_btn.clicked.connect(self.load_devices)
        self.refresh_btn.clicked.connect(self.load_screens)
        self.change_output_btn.clicked.connect(self.change_output_directory)
        self.mic_check.toggled.connect(self._toggle_mic_selection)
        self.screen_record_check.toggled.connect(self._toggle_screen_selection)
        
    def _toggle_mic_selection(self, checked: bool) -> None:
        """Enable/disable mic selection and dynamically toggle during recording."""
        # If currently recording, dynamically enable/disable the mic stream
        if self.audio_engine.state == RecordingState.RECORDING:
            if checked and self.mic_combo.currentData():
                mic_device: AudioDevice = self.mic_combo.currentData()
                self.audio_engine.enable_mic(mic_device.index)
            else:
                self.audio_engine.disable_mic()
            # Keep mic_combo disabled during recording to prevent device switching
            self.mic_combo.setEnabled(False)
        else:
            self.mic_combo.setEnabled(checked)
        
    def _toggle_screen_selection(self, checked: bool) -> None:
        """Enable/disable screen selection dropdown."""
        # User requested to see it always. We keep it enabled.
        # Alternatively, we could enable it only when checked, but the request was "why only show up when checked?"
        # The previous code disabled it. Now we do nothing or ensure it's enabled.
        self.screen_combo.setEnabled(True)
    
    def load_screens(self) -> None:
        """Load available screens/monitors."""
        self.screen_combo.clear()
        monitors = self.video_engine.get_monitors()
        
        for i, m in enumerate(monitors):
            name = f"Monitor {i+1} ({m['width']}x{m['height']})"
            self.screen_combo.addItem(name, i)
            
        if self.screen_combo.count() == 0:
             self.screen_combo.addItem("No Monitors Found")
             self.screen_combo.setEnabled(False)
    
    def load_devices(self) -> None:
        """Load available audio input devices."""
        self.device_combo.clear()
        self.mic_combo.clear()
        
        devices = self.audio_engine.get_input_devices()
        blackhole_index = -1
        
        for i, device in enumerate(devices):
            # Add to main device list
            display_name = device.name
            if device.is_blackhole:
                display_name = f"✓ {device.name} (Recommended)"
                blackhole_index = i
            
            self.device_combo.addItem(display_name, device)
            
            # Add to mic list (exclude BlackHole from recommended visual, but keep available)
            self.mic_combo.addItem(device.name, device)
        
        # Auto-select BlackHole if found
        if blackhole_index >= 0:
            self.device_combo.setCurrentIndex(blackhole_index)
            self.status_label.setText("BlackHole device detected — Ready to record")
            self.status_label.setStyleSheet("color: #00cc66; font-size: 13px;")
        elif self.device_combo.count() == 0:
            self.status_label.setText("No audio input devices found")
            self.status_label.setStyleSheet("color: #ff4444; font-size: 13px;")
            self.record_btn.setEnabled(False)
            
        # Select built-in mic for secondary if possible (simple heuristic)
        for i in range(self.mic_combo.count()):
            dev = self.mic_combo.itemData(i)
            if "microphone" in dev.name.lower():
                self.mic_combo.setCurrentIndex(i)
                break
    
    def start_recording(self) -> None:
        """Start audio recording."""
        if self.device_combo.count() == 0:
            return
        
        device: AudioDevice = self.device_combo.currentData()
        if not device:
            return
        
        # Ensure output directory exists
        os.makedirs(self.output_directory, exist_ok=True)
        
        # Determine secondary device
        mic_index = None
        if self.mic_check.isChecked() and self.mic_combo.currentData():
            mic_device: AudioDevice = self.mic_combo.currentData()
            mic_index = mic_device.index
        
        # Check Video Requirements
        self.is_recording_video = self.screen_record_check.isChecked()
        if self.is_recording_video:
            # Check for ffmpeg
            try:
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                 QMessageBox.critical(
                    self, "FFmpeg Missing",
                    "Screen recording requires FFmpeg to merge audio and video.\n"
                    "Please install it via Homebrew: brew install ffmpeg"
                )
                 return
            
            # Start Video
            screen_index = 0
            if self.screen_combo.currentData() is not None:
                screen_index = self.screen_combo.currentData()
                
            if not self.video_engine.start_recording(self.output_directory, monitor_index=screen_index):
                 QMessageBox.warning(self, "Error", "Failed to start screen recording.")
                 return
        
        # Start recording
        success = self.audio_engine.start_recording(device.index, self.output_directory, mic_device_index=mic_index)
        
        if success:
            self._recording_start_time = datetime.now()
            self.duration_timer.start(100)  # Update every 100ms
            
            # Update UI
            self.record_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.device_combo.setEnabled(False)
            # Keep mic_check enabled so user can toggle mic on/off during recording
            # But disable mic_combo to prevent device switching mid-recording
            self.mic_combo.setEnabled(False)
            self.screen_record_check.setEnabled(False)
            self.screen_combo.setEnabled(False)
            self.refresh_btn.setEnabled(False)
            
            self.status_label.setText(f"🔴 Recording from: {device.name}")
            self.status_label.setStyleSheet("color: #ff4444; font-size: 13px;")
            
            self.record_btn.setText("Recording...")
            self.rec_dot.setVisible(True) # Show red dot
            
            # Update Tray
            self.tray_action_toggle.setText("Stop Recording")
            self._set_tray_icon_color("red")
            
            # Show Overlay
            # Center it on screen initially or just show
            # self.overlay.move(100, 100) # Optional positioning
            self.overlay.show()
            self.overlay.update_time("00:00:00")
        else:
            QMessageBox.warning(
                self, "Recording Failed",
                f"Could not start recording from {device.name}.\n"
                "Please check the device is available."
            )
    
    def stop_recording(self) -> None:
        """Stop audio recording and save file."""
        self.duration_timer.stop()
        
        # Stop Audio
        audio_path = self.audio_engine.stop_recording()
        
        # Stop Video
        video_path = None
        if self.is_recording_video:
            video_path = self.video_engine.stop_recording()
        
        # Reset UI
        self.record_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.device_combo.setEnabled(True)
        self.mic_check.setEnabled(True)
        self.mic_combo.setEnabled(self.mic_check.isChecked())
        self.screen_record_check.setEnabled(True)
        self.screen_combo.setEnabled(self.screen_record_check.isChecked())
        self.refresh_btn.setEnabled(True)
        
        self.record_btn.setText("Start Recording")
        self.rec_dot.setVisible(False)
        self.sys_silence_indicator.reset()
        self.mic_silence_indicator.reset()
        
        # Update Tray
        self.tray_action_toggle.setText("Start Recording")
        self._set_tray_icon_color("black")
        
        # Hide Overlay
        self.overlay.hide()
        
        final_path = audio_path
        
        # Handle Merge if Video was recorded
        if self.is_recording_video and audio_path and video_path:
            self.status_label.setText("⏳ Merging Audio & Video...")
            self.status_label.setStyleSheet("color: #ebcb8b; font-size: 13px;")
            QApplication.processEvents() # Force UI update
            
            final_path = self._merge_recordings(audio_path, video_path)
        
        if final_path and os.path.exists(final_path):
            file_size = os.path.getsize(final_path) / 1024 / 1024  # MB
            self.status_label.setText(f"✅ Saved: {os.path.basename(final_path)} ({file_size:.1f} MB)")
            self.status_label.setStyleSheet("color: #00cc66; font-size: 13px;")
            
            # Show success message with option to reveal in Finder
            reply = QMessageBox.information(
                self, "Recording Saved",
                f"Recording saved to:\n{final_path}\n\nWould you like to reveal it in Finder?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                os.system(f'open -R "{final_path}"')
        else:
            self.status_label.setText("Ready to record")
            self.status_label.setStyleSheet("color: #888; font-size: 13px;")
            
    def _merge_recordings(self, audio_path: str, video_path: str) -> Optional[str]:
        """Merge audio and video files using ffmpeg."""
        try:
            output_path = video_path.replace("video_temp_", "screen_recording_")
            
            # FFmpeg command: merge audio and video
            # -c:v copy: Copy video stream (no re-encoding)
            # -c:a aac: Convert audio to AAC (good for mp4 container)
            # -shortest: Finish when the shortest stream ends
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', audio_path,
                '-c:v', 'libx264',   # Re-encode with H.264
                '-crf', '23',        # Constant Rate Factor (23 is default good quality)
                '-preset', 'veryfast', # Fast encoding
                '-c:a', 'aac',
                '-shortest',
                '-loglevel', 'error',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Cleanup temp files
                os.remove(audio_path)
                os.remove(video_path)
                return output_path
            else:
                self._show_error(f"Merge failed: {result.stderr}")
                return audio_path # Return at least the audio
                
        except Exception as e:
            self._show_error(f"Merge error: {e}")
            return audio_path
    
    def change_output_directory(self) -> None:
        """Open dialog to change output directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory",
            self.output_directory
        )
        
        if directory:
            self.output_directory = directory
        if directory:
            self.output_directory = directory
            self.change_output_btn.setText(f"Save to: .../{os.path.basename(directory)}")
            self.change_output_btn.setToolTip(directory)
    
    def update_duration_display(self) -> None:
        """Update the recording duration display."""
        duration = self.audio_engine.recording_duration
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        
        self.duration_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        
        # Update Overlay
        if self.overlay.isVisible():
            self.overlay.update_time(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
    
    def _on_level_update(self, sys_db: float, mic_db: float) -> None:
        """Handle level update from audio engine (thread-safe)."""
        self.signal_bridge.level_changed.emit(sys_db, mic_db)
        
    @pyqtSlot(float, float)
    def _update_levels(self, sys_db: float, mic_db: float) -> None:
        """Update both level meters."""
        self.sys_level_meter.set_level(sys_db)
        self.mic_level_meter.set_level(mic_db)
    
    def _on_silence_update(self, sys_warn: bool, sys_dur: float, mic_warn: bool, mic_dur: float) -> None:
        """Handle silence update from audio engine (thread-safe)."""
        self.signal_bridge.silence_changed.emit(sys_warn, sys_dur, mic_warn, mic_dur)
        
    @pyqtSlot(bool, float, bool, float)
    def _update_silence_indicators(self, sys_warn: bool, sys_dur: float, mic_warn: bool, mic_dur: float) -> None:
        """Update both silence indicators."""
        self.sys_silence_indicator.update_warning(sys_warn, sys_dur)
        self.mic_silence_indicator.update_warning(mic_warn, mic_dur)
        
        # Auto-Stop Logic (Silence > 5 mins)
        if sys_warn and sys_dur > 300 and self.audio_engine.state == RecordingState.RECORDING:
            print("Auto-stopping due to silence...")
            self.stop_recording()
            QMessageBox.information(self, "Auto-Stop", "Recording stopped automatically after 5 minutes of silence.")
    
    def _on_error(self, message: str) -> None:
        """Handle error from audio engine (thread-safe)."""
        self.signal_bridge.error_occurred.emit(message)
    
    @pyqtSlot(str)
    def _show_error(self, message: str) -> None:
        """Display error message to user."""
        QMessageBox.warning(self, "Error", message)
    
    def closeEvent(self, event) -> None:
        """Handle window close."""
        if self.audio_engine.state == RecordingState.RECORDING:
            reply = QMessageBox.question(
                self, "Recording in Progress",
                "A recording is in progress. Stop recording and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
            
            self.audio_engine.stop_recording()
            if self.is_recording_video:
                 self.video_engine.stop_recording()
        
        
        if self.hotkey_manager:
            self.hotkey_manager.stop()
            
        self.audio_engine.terminate()
        event.accept()
    
    def _get_stylesheet(self) -> str:
        """
        Get the application stylesheet.
        Theme: Slate Dark (shadcn/ui inspired)
        """
        # Palette (Tailwind Slate-ish)
        bg_main = "#020617"      # slate-950
        card_bg = "#0f172a"      # slate-900
        border_col = "#1e293b"   # slate-800
        text_primary = "#f8fafc" # slate-50
        text_secondary = "#94a3b8" # slate-400
        text_muted = "#64748b"   # slate-500
        
        primary_col = "#e11d48"  # rose-600
        primary_hover = "#be123c" # rose-700
        
        accent_col = "#3b82f6"   # blue-500
        
        return f"""
            QMainWindow {{
                background-color: {bg_main};
            }}
            
            QWidget {{
                font-family: ".AppleSystemUIFont", "Inter", "Helvetica Neue", sans-serif;
                color: {text_primary};
                font-size: 13px;
            }}
            
            QFrame#cardFrame, QFrame#controlsFrame {{
                background-color: {card_bg};
                border: 1px solid {border_col};
                border-radius: 12px;
            }}
            
            QLabel#sectionTitle {{
                color: {text_secondary};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
            
            QLabel#helperLabel {{
                color: {text_secondary};
                font-size: 12px;
                margin-bottom: 2px;
            }}
            
            QComboBox {{
                background-color: {bg_main};
                color: {text_primary};
                border: 1px solid {border_col};
                border-radius: 6px;
                padding: 8px 12px;
                min-height: 20px;
            }}
            
            QComboBox:hover {{
                border-color: {text_muted};
                background-color: {bg_main};
            }}
            
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            
            QComboBox QAbstractItemView {{
                background-color: {card_bg};
                color: {text_primary};
                selection-background-color: {border_col};
                border: 1px solid {border_col};
                outline: none;
                padding: 4px;
            }}
            
            /* Buttons */
            QPushButton {{
                background-color: {bg_main};
                color: {text_primary};
                border: 1px solid {border_col};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }}
            
            QPushButton:hover {{
                background-color: {border_col};
                border-color: {text_muted};
            }}
            
            QPushButton:pressed {{
                background-color: {bg_main};
            }}
            
            QPushButton#recordBtn {{
                background-color: {primary_col};
                border: none;
                color: white;
                font-weight: 600;
                font-size: 14px;
            }}
            
            QPushButton#recordBtn:hover {{
                background-color: {primary_hover};
            }}
            
            QPushButton#stopBtn {{
                background-color: transparent;
                border: 1px solid {border_col};
                color: {text_secondary};
            }}
            
            QPushButton#stopBtn:enabled {{
                 border: 1px solid {primary_col};
                 color: {primary_col};
            }}
             
            QPushButton#stopBtn:enabled:hover {{
                 background-color: rgba(225, 29, 72, 0.1);
            }}
            
            QPushButton#iconBtn {{
                background-color: transparent;
                border: none;
                font-size: 18px;
                color: {text_secondary};
            }}
            
            QPushButton#iconBtn:hover {{
                color: {text_primary};
                background-color: {border_col};
                border-radius: 6px;
            }}
            
            QPushButton#ghostBtn {{
                background-color: transparent;
                border: none;
                color: {text_muted};
                text-align: right;
                padding: 4px;
            }}
            
            QPushButton#ghostBtn:hover {{
                color: {text_primary};
                text-decoration: underline;
            }}
            
            /* Checkboxes / Switches */
            QCheckBox {{
                spacing: 8px;
                color: {text_primary};
                font-weight: 500;
            }}
            
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {text_muted};
                border-radius: 4px;
                background: transparent;
            }}
            
            QCheckBox::indicator:checked {{
                background-color: {accent_col};
                border-color: {accent_col};
                image: none; /* Can add checkmark icon url if resources available */
            }}
             
             /* Scrollbars */
             QScrollBar:vertical {{
                 border: none;
                 background: {bg_main};
                 width: 10px;
                 margin: 0px 0px 0px 0px;
             }}
             QScrollBar::handle:vertical {{
                 background: {border_col};
                 min-height: 20px;
                 border-radius: 5px;
             }}
        """
