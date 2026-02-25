"""
Silence Indicator Widget
Displays warning when silence is detected during recording.
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QPalette


class SilenceIndicator(QFrame):
    """
    Warning indicator that displays when silence is detected.
    Includes flashing animation and troubleshooting tips.
    """
    
    TROUBLESHOOTING_TIPS = [
        "1. Check that system output is set to Multi-Output Device",
        "2. Verify BlackHole is included in the Multi-Output Device", 
        "3. Ensure audio is actually playing on your Mac",
        "4. Open Audio MIDI Setup to verify configuration"
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._is_warning_active = False
        self._flash_state = False
        
        self.setup_ui()
        self.setup_animation()
        self.hide()  # Hidden by default
    
    def setup_ui(self) -> None:
        """Set up the UI components."""
        # Ensure we have a frame shape so styling applies
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # Allow expanding
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
        
        # Warning container
        self.setObjectName("silenceWarning")
        
        # Warning icon and title
        self.title_label = QLabel("⚠️ SILENCE DETECTED")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #ff4444;
            padding: 8px;
        """)
        layout.addWidget(self.title_label)
        
        # Duration label
        self.duration_label = QLabel("Silent for: 0.0s")
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.duration_label.setStyleSheet("""
            font-size: 13px;
            color: #ffaa00;
        """)
        layout.addWidget(self.duration_label)
        
        # Separator
        separator = QLabel()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #444;")
        layout.addWidget(separator)
        
        # Troubleshooting section
        tips_title = QLabel("💡 Troubleshooting Tips:")
        tips_title.setStyleSheet("""
            font-size: 12px;
            font-weight: bold;
            color: #aaa;
            margin-top: 8px;
        """)
        layout.addWidget(tips_title)
        
        # Tips list
        for tip in self.TROUBLESHOOTING_TIPS:
            tip_label = QLabel(tip)
            tip_label.setStyleSheet("""
                font-size: 11px;
                color: #888;
                padding-left: 8px;
            """)
            tip_label.setWordWrap(True)
            layout.addWidget(tip_label)
        
        layout.addStretch()
        
        # Style the container
        self.setStyleSheet("""
            #silenceWarning {
                background-color: rgba(69, 10, 10, 0.95); /* darker red background */
                border: 1px solid #dc2626; /* red-600 */
                border-radius: 12px;
            }
        """)
    
    def setup_animation(self) -> None:
        """Set up the flash animation."""
        self._flash_timer = QTimer(self)
        self._flash_timer.timeout.connect(self._toggle_flash)
        self._flash_timer.setInterval(500)  # Flash every 500ms
    
    def _toggle_flash(self) -> None:
        """Toggle the flash state for animation."""
        self._flash_state = not self._flash_state
        
        if self._flash_state:
            self.title_label.setStyleSheet("""
                font-size: 16px;
                font-weight: bold;
                color: #ff6666;
                background-color: rgba(255, 68, 68, 0.2);
                padding: 8px;
                border-radius: 4px;
            """)
        else:
            self.title_label.setStyleSheet("""
                font-size: 16px;
                font-weight: bold;
                color: #ff4444;
                padding: 8px;
            """)
    
    @pyqtSlot(bool, float)
    def update_warning(self, is_warning_active: bool, silence_duration: float) -> None:
        """
        Update the warning state.
        
        Args:
            is_warning_active: Whether to show the warning.
            silence_duration: Duration of silence in seconds.
        """
        if is_warning_active and not self._is_warning_active:
            # Warning just activated
            self.show()
            self._flash_timer.start()
            self._is_warning_active = True
            
        elif not is_warning_active and self._is_warning_active:
            # Warning deactivated
            self.hide()
            self._flash_timer.stop()
            self._is_warning_active = False
        
        if is_warning_active:
            self.duration_label.setText(f"Silent for: {silence_duration:.1f}s")
    
    def reset(self) -> None:
        """Reset the indicator to hidden state."""
        self.hide()
        self._flash_timer.stop()
        self._is_warning_active = False
        self._flash_state = False
        self._flash_state = False

    def set_title(self, title: str) -> None:
        """Set the warning title text."""
        self.title_label.setText(title)
