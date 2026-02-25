"""
Recording History Widget
Displays a list of past recordings with metadata and actions.
"""

import os
import subprocess
from datetime import datetime
from typing import Optional, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class RecordingEntry(QFrame):
    """A single recording entry in the history list."""
    
    def __init__(self, filepath: str, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.setObjectName("recordingEntry")
        self.setStyleSheet("""
            #recordingEntry {
                background-color: #020617;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 4px;
            }
            #recordingEntry:hover {
                border-color: #334155;
                background-color: #0f172a;
            }
        """)
        
        self._setup_ui()
        
    def _setup_ui(self) -> None:
        """Build the entry UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # File type icon
        ext = os.path.splitext(self.filepath)[1].lower()
        icon_map = {".mp3": "🎵", ".wav": "🎵", ".mp4": "🎬", ".m4a": "🎵"}
        icon = QLabel(icon_map.get(ext, "📄"))
        icon.setFont(QFont("Apple Color Emoji", 16))
        icon.setFixedWidth(28)
        layout.addWidget(icon)
        
        # File info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # Filename
        basename = os.path.basename(self.filepath)
        name_label = QLabel(basename)
        name_label.setStyleSheet("color: #f8fafc; font-size: 12px; font-weight: 600;")
        name_label.setToolTip(self.filepath)
        info_layout.addWidget(name_label)
        
        # Metadata row
        meta_parts = []
        try:
            stat = os.stat(self.filepath)
            size_mb = stat.st_size / (1024 * 1024)
            if size_mb >= 1.0:
                meta_parts.append(f"{size_mb:.1f} MB")
            else:
                size_kb = stat.st_size / 1024
                meta_parts.append(f"{size_kb:.0f} KB")
            
            mod_time = datetime.fromtimestamp(stat.st_mtime)
            meta_parts.append(mod_time.strftime("%b %d, %H:%M"))
        except OSError:
            meta_parts.append("Unknown")
            
        meta_label = QLabel(" · ".join(meta_parts))
        meta_label.setStyleSheet("color: #64748b; font-size: 11px;")
        info_layout.addWidget(meta_label)
        
        layout.addLayout(info_layout, 1)
        
        # Reveal in Finder button
        reveal_btn = QPushButton("📂")
        reveal_btn.setFixedSize(32, 32)
        reveal_btn.setToolTip("Reveal in Finder")
        reveal_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reveal_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #1e293b;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1e293b;
            }
        """)
        reveal_btn.clicked.connect(self._reveal_in_finder)
        layout.addWidget(reveal_btn)
        
    def _reveal_in_finder(self) -> None:
        """Open Finder with file selected."""
        if os.path.exists(self.filepath):
            subprocess.run(["open", "-R", self.filepath])


class RecordingHistoryWidget(QWidget):
    """
    Scrollable list of past recordings.
    Scans the output directory for audio/video files.
    """
    
    SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".mp4", ".m4a", ".flac"}
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: List[RecordingEntry] = []
        self._setup_ui()
        
    def _setup_ui(self) -> None:
        """Build the widget."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("RECORDING HISTORY")
        title.setObjectName("sectionTitle")
        title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;")
        header.addWidget(title)
        
        self.count_label = QLabel("0 files")
        self.count_label.setStyleSheet("color: #475569; font-size: 11px;")
        header.addStretch()
        header.addWidget(self.count_label)
        
        main_layout.addLayout(header)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QWidget#scrollContent {
                background: transparent;
            }
        """)
        
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("scrollContent")
        self.list_layout = QVBoxLayout(self.scroll_content)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(6)
        self.list_layout.addStretch()
        
        scroll.setWidget(self.scroll_content)
        main_layout.addWidget(scroll)
        
        # Empty state
        self.empty_label = QLabel("No recordings yet")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #475569; font-size: 12px; padding: 20px;")
        self.list_layout.insertWidget(0, self.empty_label)
        
    def scan_directory(self, directory: str) -> None:
        """Scan a directory for existing recordings and populate the list."""
        if not os.path.isdir(directory):
            return
        
        files = []
        for f in os.listdir(directory):
            ext = os.path.splitext(f)[1].lower()
            if ext in self.SUPPORTED_EXTENSIONS:
                filepath = os.path.join(directory, f)
                files.append(filepath)
        
        # Sort by modification time (newest first)
        files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        
        for filepath in files:
            self._add_entry(filepath, prepend=False)
            
    def add_recording(self, filepath: str) -> None:
        """Add a new recording to the top of the list."""
        self._add_entry(filepath, prepend=True)
        
    def _add_entry(self, filepath: str, prepend: bool = True) -> None:
        """Add an entry widget."""
        # Hide empty label
        self.empty_label.hide()
        
        entry = RecordingEntry(filepath)
        self._entries.append(entry)
        
        if prepend:
            self.list_layout.insertWidget(0, entry)
        else:
            # Insert before the stretch
            self.list_layout.insertWidget(self.list_layout.count() - 1, entry)
        
        self.count_label.setText(f"{len(self._entries)} file{'s' if len(self._entries) != 1 else ''}")
