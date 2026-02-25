#!/usr/bin/env python3
"""
AIrecorder (Windows entrypoint)

Usage:
    python main_windows.py
"""

import os
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

# Add the current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window_windows import MainWindowWindows


def main() -> None:
    """Windows application entry point."""
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("BlackHole Audio Recorder")
    app.setOrganizationName("AIrecorder")
    app.setStyle("Fusion")

    window = MainWindowWindows()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
