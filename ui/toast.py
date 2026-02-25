"""
Toast Notification Widget
Non-blocking slide-in notifications that auto-dismiss.
"""

from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QGraphicsOpacityEffect, QApplication
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QFont


class ToastNotification(QWidget):
    """
    A single toast notification that slides in and auto-dismisses.
    """
    closed = pyqtSignal(object)  # Emits self when closed
    
    # Toast types
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    
    ICONS = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌",
    }
    
    COLORS = {
        "info": "#3b82f6",
        "success": "#22c55e",
        "warning": "#f59e0b",
        "error": "#ef4444",
    }
    
    def __init__(self, message: str, toast_type: str = "info", duration_ms: int = 3000, parent=None):
        super().__init__(parent)
        
        self.duration_ms = duration_ms
        self.toast_type = toast_type
        
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        self._setup_ui(message, toast_type)
        
        # Auto-dismiss timer
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.fade_out)
        
    def _setup_ui(self, message: str, toast_type: str) -> None:
        """Build the toast UI."""
        self.setFixedHeight(48)
        self.setMinimumWidth(250)
        self.setMaximumWidth(420)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(10)
        
        # Icon
        icon_label = QLabel(self.ICONS.get(toast_type, "ℹ️"))
        icon_label.setFont(QFont("Apple Color Emoji", 14))
        layout.addWidget(icon_label)
        
        # Message
        msg_label = QLabel(message)
        msg_label.setStyleSheet(f"color: #f8fafc; font-size: 13px; font-weight: 500;")
        msg_label.setWordWrap(False)
        layout.addWidget(msg_label, 1)
        
        self.adjustSize()
        
    def paintEvent(self, event):
        """Paint rounded rectangle background with accent border."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        painter.setBrush(QColor(15, 23, 42, 230))  # slate-900 with opacity
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 12, 12)
        
        # Accent left border
        accent = QColor(self.COLORS.get(self.toast_type, "#3b82f6"))
        painter.setBrush(accent)
        painter.drawRoundedRect(0, 0, 4, self.height(), 2, 2)
        
        painter.end()
    
    def show_toast(self) -> None:
        """Show the toast with slide-in animation."""
        self.show()
        
        # Slide in from right
        screen = QApplication.primaryScreen().geometry()
        end_x = screen.width() - self.width() - 20
        end_y = self.y()
        
        start_pos = QPoint(screen.width(), end_y)
        end_pos = QPoint(end_x, end_y)
        
        self._slide_anim = QPropertyAnimation(self, b"pos")
        self._slide_anim.setDuration(300)
        self._slide_anim.setStartValue(start_pos)
        self._slide_anim.setEndValue(end_pos)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide_anim.start()
        
        # Start dismiss timer
        self._dismiss_timer.start(self.duration_ms)
        
    def fade_out(self) -> None:
        """Fade out and close."""
        # Slide out to right
        screen = QApplication.primaryScreen().geometry()
        
        self._slide_out = QPropertyAnimation(self, b"pos")
        self._slide_out.setDuration(250)
        self._slide_out.setStartValue(self.pos())
        self._slide_out.setEndValue(QPoint(screen.width(), self.y()))
        self._slide_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._slide_out.finished.connect(self._on_closed)
        self._slide_out.start()
        
    def _on_closed(self) -> None:
        """Clean up after fade out."""
        self.closed.emit(self)
        self.close()
        self.deleteLater()


class ToastManager:
    """
    Manages stacking multiple toast notifications.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._toasts = []
            cls._instance._base_y = 60  # Start from top
        return cls._instance
    
    def show_toast(self, message: str, toast_type: str = "info", duration_ms: int = 3000) -> ToastNotification:
        """Show a toast notification."""
        toast = ToastNotification(message, toast_type, duration_ms)
        toast.closed.connect(self._on_toast_closed)
        
        # Position: stack from bottom-right
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - toast.width() - 20
        y = self._base_y + (len(self._toasts) * 58)
        
        toast.move(screen.width(), y)  # Start off-screen
        self._toasts.append(toast)
        toast.show_toast()
        
        return toast
    
    def _on_toast_closed(self, toast: ToastNotification) -> None:
        """Remove toast and reposition remaining."""
        if toast in self._toasts:
            self._toasts.remove(toast)
        
        # Reposition remaining toasts
        for i, t in enumerate(self._toasts):
            screen = QApplication.primaryScreen().geometry()
            target_y = self._base_y + (i * 58)
            
            anim = QPropertyAnimation(t, b"pos")
            anim.setDuration(200)
            anim.setStartValue(t.pos())
            anim.setEndValue(QPoint(t.x(), target_y))
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start()
            # Keep reference to prevent GC
            t._reposition_anim = anim
    
    @staticmethod
    def info(message: str, duration_ms: int = 3000):
        """Show an info toast."""
        return ToastManager().show_toast(message, "info", duration_ms)
    
    @staticmethod
    def success(message: str, duration_ms: int = 3000):
        """Show a success toast."""
        return ToastManager().show_toast(message, "success", duration_ms)
    
    @staticmethod
    def warning(message: str, duration_ms: int = 3000):
        """Show a warning toast."""
        return ToastManager().show_toast(message, "warning", duration_ms)
    
    @staticmethod
    def error(message: str, duration_ms: int = 5000):
        """Show an error toast (longer duration)."""
        return ToastManager().show_toast(message, "error", duration_ms)
