"""
Module 4: Overlay GUI
Transparent always-on-top window to display AI answers.
Works across all macOS Spaces/Desktops.
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QPainter, QColor, QBrush

from config import OVERLAY_OPACITY, OVERLAY_FONT_SIZE

logger = logging.getLogger(__name__)


class OverlayWindow(QWidget):
    """Transparent always-on-top overlay window for displaying answers."""

    def __init__(self):
        super().__init__()
        self._drag_position = QPoint()
        self._opacity = OVERLAY_OPACITY
        self._setup_window()
        self._setup_ui()
        logger.info("Overlay window created")

    def _setup_window(self):
        """Configure window properties for always-on-top transparent overlay."""
        self.setWindowTitle("AI Screen Analyzer")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Position: top-right corner
        self.setGeometry(100, 100, 500, 200)
        self.setMinimumSize(300, 100)
        self.setMaximumSize(800, 600)

    def _setup_ui(self):
        """Create the overlay UI elements."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Container widget with background
        self.container = QWidget()
        self.container.setObjectName("container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 12, 16, 16)
        container_layout.setSpacing(8)

        # Title bar
        title_bar = QHBoxLayout()
        title_bar.setSpacing(4)

        title_label = QLabel("🤖 AI Answer")
        title_label.setStyleSheet("color: #9CA3AF; font-size: 12px; font-weight: bold; background: transparent;")
        title_bar.addWidget(title_label)
        title_bar.addStretch()

        # Minimize button
        self.btn_minimize = QPushButton("–")
        self.btn_minimize.setFixedSize(24, 24)
        self.btn_minimize.setStyleSheet("""
            QPushButton {
                background: rgba(75, 85, 99, 0.8);
                color: #D1D5DB;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background: rgba(107, 114, 128, 0.9); }
        """)
        self.btn_minimize.clicked.connect(self._minimize)
        title_bar.addWidget(self.btn_minimize)

        # Close/hide button
        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: rgba(220, 38, 38, 0.7);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover { background: rgba(220, 38, 38, 0.9); }
        """)
        self.btn_close.clicked.connect(self.hide)
        title_bar.addWidget(self.btn_close)

        container_layout.addLayout(title_bar)

        # Answer label
        self.answer_label = QLabel("Press Cmd+Shift+S to capture screen")
        self.answer_label.setWordWrap(True)
        self.answer_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.answer_label.setFont(QFont("SF Pro Display", OVERLAY_FONT_SIZE))
        self.answer_label.setStyleSheet(f"""
            QLabel {{
                color: #F9FAFB;
                font-size: {OVERLAY_FONT_SIZE}px;
                line-height: 1.5;
                padding: 8px;
                background: transparent;
            }}
        """)
        self.answer_label.setMinimumHeight(40)
        container_layout.addWidget(self.answer_label)

        main_layout.addWidget(self.container)

        # Apply container background style
        self._update_container_style()

    def _update_container_style(self):
        """Update the container background with current opacity."""
        alpha = int(self._opacity * 255)
        self.container.setStyleSheet(f"""
            QWidget#container {{
                background-color: rgba(17, 24, 39, {alpha});
                border-radius: 16px;
                border: 1px solid rgba(75, 85, 99, {int(alpha * 0.6)});
            }}
        """)

    def paintEvent(self, event):
        """Custom paint for shadow effect."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Draw a subtle shadow
        shadow_color = QColor(0, 0, 0, 50)
        painter.setBrush(QBrush(shadow_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect().adjusted(2, 2, 0, 0), 16, 16)
        painter.end()

    def update_answer(self, text: str):
        """Update the displayed answer text."""
        self.answer_label.setText(text)
        self.answer_label.setStyleSheet(f"""
            QLabel {{
                color: #F9FAFB;
                font-size: {OVERLAY_FONT_SIZE}px;
                line-height: 1.5;
                padding: 8px;
                background: transparent;
            }}
        """)
        self.adjustSize()
        logger.info("Overlay answer updated")

    def show_loading(self):
        """Show loading state."""
        self.answer_label.setText("⏳ Processing...")
        self.answer_label.setStyleSheet(f"""
            QLabel {{
                color: #FCD34D;
                font-size: {OVERLAY_FONT_SIZE}px;
                padding: 8px;
                background: transparent;
            }}
        """)
        if not self.isVisible():
            self.show()
        self.raise_()

    def show_error(self, message: str):
        """Show error state."""
        self.answer_label.setText(f"❌ {message}")
        self.answer_label.setStyleSheet(f"""
            QLabel {{
                color: #FCA5A5;
                font-size: {OVERLAY_FONT_SIZE}px;
                padding: 8px;
                background: transparent;
            }}
        """)
        self.adjustSize()
        logger.error(f"Overlay error: {message}")

    def _minimize(self):
        """Minimize the overlay to a small bar."""
        if self.height() > 60:
            self._saved_height = self.height()
            self.setFixedHeight(45)
            self.answer_label.hide()
            self.btn_minimize.setText("+")
        else:
            self.answer_label.show()
            self.setMinimumHeight(100)
            self.setMaximumHeight(600)
            h = getattr(self, '_saved_height', 200)
            self.resize(self.width(), h)
            self.btn_minimize.setText("–")

    # --- Drag support ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_position:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_position = QPoint()
        event.accept()

    # --- Opacity adjustment via scroll ---
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self._opacity = min(1.0, self._opacity + 0.05)
        else:
            self._opacity = max(0.2, self._opacity - 0.05)
        self._update_container_style()
        event.accept()

    def showEvent(self, event):
        """When shown, apply macOS collection behavior for all Spaces."""
        super().showEvent(event)
        self._apply_macos_all_spaces()

    def _apply_macos_all_spaces(self):
        """macOS-specific: make window visible on all Spaces/Desktops."""
        try:
            from AppKit import NSApplication, NSWindow  # noqa: F401

            qt_win_id = int(self.winId())
            ns_app = NSApplication.sharedApplication()
            target = None
            for w in ns_app.windows():
                if w.windowNumber() == qt_win_id:
                    target = w
                    break

            if target is None:
                logger.debug("macOS: could not find NSWindow for winId %s", qt_win_id)
                return

            # NSWindowCollectionBehaviorMoveToActiveSpace  = 1 << 1  (2)
            # NSWindowCollectionBehaviorFullScreenAuxiliary = 1 << 8 (256)
            behavior = (1 << 1) | (1 << 8)
            target.setCollectionBehavior_(behavior)

            # NSFloatingWindowLevel = 3
            target.setLevel_(3)

            logger.debug("macOS: Set window to appear on all Spaces (winId=%s)", qt_win_id)
        except ImportError:
            logger.debug("AppKit not available — not on macOS or pyobjc not installed")
        except Exception as e:
            logger.debug("Could not set macOS all-spaces behavior: %s", e)
