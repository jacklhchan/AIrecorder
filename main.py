#!/usr/bin/env python3
"""
BlackHole Audio Recorder
A Mac desktop application for recording audio from BlackHole virtual audio device
with real-time silence detection.

Usage:
    python main.py
"""

import sys
import os

# Add the current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from ui.main_window import MainWindow


def main():
    """Application entry point."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("BlackHole Audio Recorder")
    app.setOrganizationName("AIrecorder")
    
    # Set app style
    app.setStyle("Fusion")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
