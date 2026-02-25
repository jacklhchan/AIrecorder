"""
Windows Hotkey Manager Module
Handles global hotkeys using pynput.
"""

from PyQt6.QtCore import QObject, pyqtSignal
from pynput import keyboard


class HotkeyManagerWindows(QObject):
    """
    Manages global hotkeys on Windows.
    Emits signal when Ctrl+Shift+R is pressed.
    """

    toggle_recording = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._listener = None
        self._running = False
        self.shortcut_label = "Ctrl+Shift+R"

    def start(self):
        """Start monitoring global hotkeys."""
        if self._running:
            return

        hotkeys = {
            "<ctrl>+<shift>+r": self._on_toggle
        }

        self._listener = keyboard.GlobalHotKeys(hotkeys)
        self._listener.start()
        self._running = True

    def stop(self):
        """Stop monitoring."""
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._running = False

    def _on_toggle(self):
        """Callback when hotkey is pressed."""
        self.toggle_recording.emit()
