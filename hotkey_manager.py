"""
Hotkey Manager Module
Handles global hotkeys using pynput.
"""

from PyQt6.QtCore import QObject, pyqtSignal
from pynput import keyboard
import threading

class HotkeyManager(QObject):
    """
    Manages global hotkeys monitoring.
    Emits signal when 'Cmd+Shift+R' is pressed.
    """
    toggle_recording = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._listener = None
        self._running = False
        
    def start(self):
        """Start monitoring global hotkeys."""
        if self._running:
            return
            
        # Define hotkey mapping
        # <cmd> is 'cmd' on mac
        hotkeys = {
            '<cmd>+<shift>+r': self._on_toggle
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
        # Emit signal to main thread
        self.toggle_recording.emit()
