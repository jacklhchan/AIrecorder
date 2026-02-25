"""
Floating Overlay Widget
Minimal control overlay for screen recording.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QColor, QPainter

class OverlayWidget(QWidget):
    """
    Floating overlay with timer, mic toggle, pause/resume, and stop button.
    Draggable and stays on top.
    """
    stop_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    mic_toggled = pyqtSignal(bool)  # True = mic on, False = mic off
    
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(
            Qt.WindowType.Window | 
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.draggable = True
        self._dragging = False
        self._drag_position = QPoint()
        self._is_paused = False
        self._mic_active = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the UI."""
        self.setFixedSize(310, 50)
        
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 5, 12, 5)
        layout.setSpacing(8)
        
        # Timer Label
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setStyleSheet("color: white; font-family: Monaco; font-weight: bold; font-size: 14px;")
        layout.addWidget(self.timer_label)
        
        layout.addStretch()
        
        # Mic Toggle Button
        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setFixedSize(32, 32)
        self.mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_btn.setToolTip("Toggle Microphone")
        self._update_mic_style(False)
        self.mic_btn.clicked.connect(self._on_mic_clicked)
        layout.addWidget(self.mic_btn)
        
        # Pause/Resume Button
        self.pause_btn = QPushButton("⏸")
        self.pause_btn.setFixedSize(32, 32)
        self.pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pause_btn.setToolTip("Pause Recording")
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #f59e0b;
                border: none;
                border-radius: 16px;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #fbbf24;
            }
        """)
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        layout.addWidget(self.pause_btn)
        
        # Stop Button
        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setFixedSize(32, 32)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setToolTip("Stop Recording")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                border: none;
                border-radius: 16px;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #ff6666;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        layout.addWidget(self.stop_btn)
        
    def update_time(self, text: str):
        """Update timer text."""
        self.timer_label.setText(text)
        
    def set_paused(self, paused: bool):
        """Update pause/resume button state."""
        self._is_paused = paused
        if paused:
            self.pause_btn.setText("▶")
            self.pause_btn.setToolTip("Resume Recording")
            self.pause_btn.setStyleSheet("""
                QPushButton {
                    background-color: #22c55e;
                    border: none;
                    border-radius: 16px;
                    color: white;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #4ade80;
                }
            """)
            self.timer_label.setStyleSheet("color: #f59e0b; font-family: Monaco; font-weight: bold; font-size: 14px;")
        else:
            self.pause_btn.setText("⏸")
            self.pause_btn.setToolTip("Pause Recording")
            self.pause_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f59e0b;
                    border: none;
                    border-radius: 16px;
                    color: white;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #fbbf24;
                }
            """)
            self.timer_label.setStyleSheet("color: white; font-family: Monaco; font-weight: bold; font-size: 14px;")
    
    def set_mic_active(self, active: bool):
        """Update mic button visual state."""
        self._mic_active = active
        self._update_mic_style(active)
    
    def _update_mic_style(self, active: bool):
        """Update mic button styling."""
        if active:
            self.mic_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3b82f6;
                    border: none;
                    border-radius: 16px;
                    color: white;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #60a5fa;
                }
            """)
        else:
            self.mic_btn.setStyleSheet("""
                QPushButton {
                    background-color: #374151;
                    border: none;
                    border-radius: 16px;
                    color: #9ca3af;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #4b5563;
                }
            """)
    
    def _on_mic_clicked(self):
        """Handle mic button click."""
        self._mic_active = not self._mic_active
        self._update_mic_style(self._mic_active)
        self.mic_toggled.emit(self._mic_active)
    
    def _on_pause_clicked(self):
        """Handle pause button click."""
        self.pause_clicked.emit()
        
    def paintEvent(self, event):
        """Paint semi-transparent background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw rounded rectangle background
        painter.setBrush(QColor(0, 0, 0, 180))  # Black with opacity
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 25, 25)
        
    # --- Dragging Logic ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.draggable:
            self._dragging = True
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False
