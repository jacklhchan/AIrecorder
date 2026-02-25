"""
Level Meter Widget
Custom PyQt6 widget for displaying real-time audio levels.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QPen


class LevelMeter(QWidget):
    """
    A horizontal audio level meter with gradient coloring and peak hold.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Level configuration (in dB)
        self.min_db = -60.0
        self.max_db = 0.0
        self.warning_db = -12.0
        self.danger_db = -6.0
        
        # Current values
        self._current_level = self.min_db
        self._peak_level = self.min_db
        self._display_level = self.min_db
        
        # Animation
        self._decay_rate = 0.3  # How much the level drops per update
        self._peak_hold_time = 1000  # ms to hold peak
        self._peak_timer = QTimer(self)
        self._peak_timer.timeout.connect(self._reset_peak)
        
        # Visual settings
        self.setMinimumHeight(30)
        self.setMinimumWidth(200)
        
        # Colors
        self.bg_color = QColor(30, 30, 35)
        self.border_color = QColor(60, 60, 70)
        self.peak_color = QColor(255, 255, 255)
        
        # Smooth animation timer
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._animate)
        self._animation_timer.start(16)  # ~60 FPS
    
    def _db_to_fraction(self, db: float) -> float:
        """Convert dB level to fraction (0.0 to 1.0)."""
        db = max(self.min_db, min(self.max_db, db))
        return (db - self.min_db) / (self.max_db - self.min_db)
    
    @pyqtSlot(float)
    def set_level(self, db_level: float) -> None:
        """
        Set the current audio level.
        
        Args:
            db_level: Level in decibels.
        """
        self._current_level = max(self.min_db, min(self.max_db, db_level))
        
        # Update peak
        if self._current_level > self._peak_level:
            self._peak_level = self._current_level
            self._peak_timer.start(self._peak_hold_time)
    
    def _reset_peak(self) -> None:
        """Reset the peak hold indicator."""
        self._peak_level = self._current_level
        self._peak_timer.stop()
    
    def _animate(self) -> None:
        """Animate the level display for smooth movement."""
        # Smoothly move toward current level
        diff = self._current_level - self._display_level
        
        if abs(diff) < 0.5:
            self._display_level = self._current_level
        elif diff > 0:
            # Rising - fast response
            self._display_level += diff * 0.5
        else:
            # Falling - slower decay
            self._display_level += diff * 0.15
        
        self.update()
    
    def paintEvent(self, event) -> None:
        """Paint the level meter."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get widget dimensions
        w = self.width()
        h = self.height()
        padding = 4
        bar_height = h - (padding * 2)
        bar_width = w - (padding * 2)
        
        # Draw background
        painter.fillRect(0, 0, w, h, self.bg_color)
        
        # Draw border
        painter.setPen(QPen(self.border_color, 1))
        painter.drawRect(0, 0, w - 1, h - 1)
        
        # Calculate level width
        level_fraction = self._db_to_fraction(self._display_level)
        level_width = int(bar_width * level_fraction)
        
        if level_width > 0:
            # Create gradient for level bar
            gradient = QLinearGradient(padding, 0, padding + bar_width, 0)
            gradient.setColorAt(0.0, QColor(0, 200, 100))      # Green
            gradient.setColorAt(0.6, QColor(100, 200, 50))     # Light green
            gradient.setColorAt(0.8, QColor(255, 200, 0))      # Yellow
            gradient.setColorAt(0.95, QColor(255, 80, 0))      # Orange
            gradient.setColorAt(1.0, QColor(255, 0, 0))        # Red
            
            painter.fillRect(padding, padding, level_width, bar_height, gradient)
        
        # Draw peak indicator
        peak_fraction = self._db_to_fraction(self._peak_level)
        if peak_fraction > 0.01:
            peak_x = padding + int(bar_width * peak_fraction)
            painter.setPen(QPen(self.peak_color, 2))
            painter.drawLine(peak_x, padding, peak_x, padding + bar_height)
        
        # Draw scale markers
        painter.setPen(QPen(QColor(100, 100, 110), 1))
        for db in [-48, -36, -24, -12, -6, 0]:
            x = padding + int(bar_width * self._db_to_fraction(db))
            painter.drawLine(x, h - padding - 3, x, h - padding)
        
        painter.end()


class LevelMeterWidget(QWidget):
    """Level meter with label."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Label
        self.label = QLabel("Audio Level")
        self.label.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(self.label)
        
        # Meter
        self.meter = LevelMeter()
        layout.addWidget(self.meter)
        
        # dB display
        self.db_label = QLabel("-∞ dB")
        self.db_label.setStyleSheet("color: #888; font-size: 10px;")
        self.db_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.db_label)
    
    @pyqtSlot(float)
    def set_level(self, db_level: float) -> None:
        """Set the audio level."""
        self.meter.set_level(db_level)
        
        # Update dB label
        if db_level <= -60:
            self.db_label.setText("-∞ dB")
        else:
            self.db_label.setText(f"{db_level:.1f} dB")
