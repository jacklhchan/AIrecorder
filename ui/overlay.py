"""
Floating Overlay Widget
Minimal control overlay for screen recording.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QColor, QPainter

class OverlayWidget(QWidget):
    """
    Floating overlay with timer and stop button.
    Draggable and stays on top.
    """
    stop_clicked = pyqtSignal()
    
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
        
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the UI."""
        self.setFixedSize(200, 50)
        
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Timer Label
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setStyleSheet("color: white; font-family: Monaco; font-weight: bold; font-size: 14px;")
        layout.addWidget(self.timer_label)
        
        # Stop Button
        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setFixedSize(32, 32)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        
    def paintEvent(self, event):
        """Paint semi-transparent background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw rounded rectangle background
        painter.setBrush(QColor(0, 0, 0, 180)) # Black with opacity
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
