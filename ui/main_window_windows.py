"""
Windows Main Window
Windows-specific wrapper around the primary application window.
"""

import os
import subprocess
from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import QApplication, QMessageBox

import ui.main_window as base_main_window
from audio_engine import AudioDevice, RecordingState
from hotkey_manager_windows import HotkeyManagerWindows

# Swap the hotkey manager only for this Windows entrypoint.
base_main_window.HotkeyManager = HotkeyManagerWindows


class MainWindowWindows(base_main_window.MainWindow):
    """Windows-specific main window behavior."""

    def __init__(self):
        super().__init__()
        self.output_directory = os.path.expanduser("~/Music/AIrecorder Recordings")
        self.change_output_btn.setText(f"Save to: .../{os.path.basename(self.output_directory)}")
        self.change_output_btn.setToolTip(self.output_directory)

    def start_recording(self) -> None:
        """Start audio recording with Windows-specific FFmpeg hint."""
        if self.device_combo.count() == 0:
            return

        device: AudioDevice = self.device_combo.currentData()
        if not device:
            return

        os.makedirs(self.output_directory, exist_ok=True)

        mic_index = None
        if self.mic_check.isChecked() and self.mic_combo.currentData():
            mic_device: AudioDevice = self.mic_combo.currentData()
            mic_index = mic_device.index

        self.is_recording_video = self.screen_record_check.isChecked()
        if self.is_recording_video:
            try:
                subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                QMessageBox.critical(
                    self,
                    "FFmpeg Missing",
                    "Screen recording requires FFmpeg to merge audio and video.\n"
                    "Install with winget install Gyan.FFmpeg or choco install ffmpeg -y",
                )
                return

            screen_index = 0
            if self.screen_combo.currentData() is not None:
                screen_index = self.screen_combo.currentData()

            if not self.video_engine.start_recording(self.output_directory, monitor_index=screen_index):
                QMessageBox.warning(self, "Error", "Failed to start screen recording.")
                return

        success = self.audio_engine.start_recording(
            device.index,
            self.output_directory,
            mic_device_index=mic_index,
        )

        if success:
            self._recording_start_time = datetime.now()
            self.duration_timer.start(100)

            self.record_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.device_combo.setEnabled(False)
            self.mic_check.setEnabled(False)
            self.mic_combo.setEnabled(False)
            self.screen_record_check.setEnabled(False)
            self.screen_combo.setEnabled(False)
            self.refresh_btn.setEnabled(False)

            self.status_label.setText(f"🔴 Recording from: {device.name}")
            self.status_label.setStyleSheet("color: #ff4444; font-size: 13px;")

            self.record_btn.setText("Recording...")
            self.rec_dot.setVisible(True)

            self.tray_action_toggle.setText("Stop Recording")
            self._set_tray_icon_color("red")

            self.overlay.show()
            self.overlay.update_time("00:00:00")
        else:
            QMessageBox.warning(
                self,
                "Recording Failed",
                f"Could not start recording from {device.name}.\nPlease check the device is available.",
            )

    def stop_recording(self) -> None:
        """Stop audio recording and reveal result in File Explorer."""
        self.duration_timer.stop()

        audio_path = self.audio_engine.stop_recording()

        video_path = None
        if self.is_recording_video:
            video_path = self.video_engine.stop_recording()

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

        self.tray_action_toggle.setText("Start Recording")
        self._set_tray_icon_color("black")

        self.overlay.hide()

        final_path = audio_path

        if self.is_recording_video and audio_path and video_path:
            self.status_label.setText("⏳ Merging Audio & Video...")
            self.status_label.setStyleSheet("color: #ebcb8b; font-size: 13px;")
            QApplication.processEvents()

            final_path = self._merge_recordings(audio_path, video_path)

        if final_path and os.path.exists(final_path):
            file_size = os.path.getsize(final_path) / 1024 / 1024
            self.status_label.setText(f"✅ Saved: {os.path.basename(final_path)} ({file_size:.1f} MB)")
            self.status_label.setStyleSheet("color: #00cc66; font-size: 13px;")

            reply = QMessageBox.information(
                self,
                "Recording Saved",
                f"Recording saved to:\n{final_path}\n\nWould you like to reveal it in File Explorer?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self._reveal_in_explorer(final_path)
        else:
            self.status_label.setText("Ready to record")
            self.status_label.setStyleSheet("color: #888; font-size: 13px;")

    def _reveal_in_explorer(self, file_path: str) -> None:
        """Reveal a file in Windows File Explorer."""
        try:
            subprocess.run(["explorer", f"/select,{os.path.normpath(file_path)}"], check=False)
        except Exception as exc:
            print(f"Failed to open File Explorer: {exc}")
