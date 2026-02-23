"""
AI-Powered Screen Content Analyzer
Main entry point - orchestrates all modules.
"""

import sys
import signal
import argparse
import logging
import threading
from datetime import datetime

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QAction

from config import (
    validate_config,
    setup_logging,
    HOTKEY_CAPTURE,
    HOTKEY_TOGGLE,
)
from modules.capture import ScreenCapture
from modules.ocr import OCREngine
from modules.ai_engine import AIEngine
from modules.overlay import OverlayWindow


class PipelineSignals(QObject):
    """Signals for communicating from worker thread to main GUI thread."""
    show_loading = pyqtSignal()
    show_answer = pyqtSignal(str)
    show_error = pyqtSignal(str)
    toggle_overlay = pyqtSignal()


class App:
    """Main application controller."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.logger = logging.getLogger(__name__)

        # Qt Application — must be created FIRST
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setQuitOnLastWindowClosed(False)  # Keep running when overlay hidden

        # Signals bridge (thread-safe communication)
        self.signals = PipelineSignals()

        # Initialize modules
        self.capture = ScreenCapture()
        self.ocr = OCREngine()
        self.ai_engine = AIEngine()
        self.overlay = OverlayWindow()

        # Connect signals to overlay slots
        self.signals.show_loading.connect(self.overlay.show_loading)
        self.signals.show_answer.connect(self._on_answer)
        self.signals.show_error.connect(self._on_error)
        self.signals.toggle_overlay.connect(self._toggle_overlay)

        # Pipeline lock to prevent concurrent runs
        self._pipeline_lock = threading.Lock()

        # System tray icon (keeps app alive & visible)
        self._setup_tray()

        # Setup hotkeys in a background thread
        self._setup_hotkeys()

        self.logger.info("Application initialized successfully.")

    def _setup_tray(self):
        """Create a system tray icon so the app stays alive."""
        self.tray = QSystemTrayIcon(self.qt_app)
        # Use a default icon — works even without a custom file
        self.tray.setIcon(self.qt_app.style().standardIcon(
            self.qt_app.style().StandardPixmap.SP_ComputerIcon
        ))
        self.tray.setToolTip("AI Screen Analyzer")

        menu = QMenu()
        action_capture = QAction("Capture (Cmd+Shift+S)", menu)
        action_capture.triggered.connect(self._trigger_pipeline)

        action_toggle = QAction("Toggle Overlay (Cmd+Shift+H)", menu)
        action_toggle.triggered.connect(self._toggle_overlay)

        action_quit = QAction("Quit", menu)
        action_quit.triggered.connect(self._quit)

        menu.addAction(action_capture)
        menu.addAction(action_toggle)
        menu.addSeparator()
        menu.addAction(action_quit)

        self.tray.setContextMenu(menu)
        self.tray.show()

    def _setup_hotkeys(self):
        """Start pynput hotkey listener in a daemon thread."""
        from pynput.keyboard import GlobalHotKeys

        hotkey_map = {
            HOTKEY_CAPTURE: self._trigger_pipeline,
            HOTKEY_TOGGLE: self._on_toggle_hotkey,
        }

        self.logger.info(f"Registering hotkeys: capture={HOTKEY_CAPTURE}, toggle={HOTKEY_TOGGLE}")

        self.hotkey_listener = GlobalHotKeys(hotkey_map)
        self.hotkey_listener.daemon = True  # Won't block app exit
        self.hotkey_listener.start()

    def _on_toggle_hotkey(self):
        """Called from pynput thread — emit signal to Qt main thread."""
        self.signals.toggle_overlay.emit()

    def _trigger_pipeline(self):
        """Called from pynput thread or tray menu — start pipeline in background."""
        if not self._pipeline_lock.acquire(blocking=False):
            self.logger.warning("Pipeline already running, ignoring trigger.")
            return

        thread = threading.Thread(target=self._run_pipeline, daemon=True)
        thread.start()

    def _run_pipeline(self):
        """Execute the full capture → OCR → AI pipeline (runs in background thread)."""
        try:
            self.logger.info("=== Pipeline started ===")
            self.signals.show_loading.emit()

            # Step 1: Screen capture
            self.logger.info("Step 1: Capturing screen...")
            image = self.capture.capture_full_screen()
            if image is None:
                self.signals.show_error.emit("Screen capture failed.")
                return
            self.logger.info(f"Captured image: {image.size}")

            # Step 2: OCR
            self.logger.info("Step 2: Running OCR...")
            text = self.ocr.extract_text(image)
            self.logger.info(f"OCR result ({len(text)} chars): {text[:100]}...")

            if not text or len(text.strip()) < 5:
                self.logger.warning("OCR returned insufficient text, trying Vision fallback for answer...")
                # Use Vision API to both read and answer
                answer = self.ai_engine.get_answer_from_image(image)
            else:
                # Step 3: AI answer
                self.logger.info("Step 3: Getting AI answer...")
                answer = self.ai_engine.get_answer(text)

            self.logger.info(f"Answer: {answer}")
            self.signals.show_answer.emit(answer)

            # Log Q&A
            self._log_qa(text if text else "[image-based]", answer)

        except Exception as e:
            self.logger.exception("Pipeline error")
            self.signals.show_error.emit(f"Error: {str(e)}")
        finally:
            self._pipeline_lock.release()
            self.logger.info("=== Pipeline finished ===")

    def _on_answer(self, text: str):
        """Show answer and make sure overlay is visible (runs on main thread)."""
        self.overlay.update_answer(text)
        if not self.overlay.isVisible():
            self.overlay.show()
        self.overlay.raise_()

    def _on_error(self, msg: str):
        """Show error in overlay (runs on main thread)."""
        self.overlay.show_error(msg)
        if not self.overlay.isVisible():
            self.overlay.show()

    def _toggle_overlay(self):
        """Toggle overlay visibility (runs on main thread)."""
        if self.overlay.isVisible():
            self.overlay.hide()
            self.logger.info("Overlay hidden")
        else:
            self.overlay.show()
            self.overlay.raise_()
            self.logger.info("Overlay shown")

    def _log_qa(self, question: str, answer: str):
        """Log question-answer pair to session log."""
        qa_logger = logging.getLogger("qa_log")
        qa_logger.info(f"\n{'='*50}\n"
                       f"TIME: {datetime.now().isoformat()}\n"
                       f"QUESTION:\n{question}\n"
                       f"ANSWER:\n{answer}\n"
                       f"{'='*50}")

    def _quit(self):
        """Clean shutdown."""
        self.logger.info("Application shutting down...")
        if hasattr(self, 'hotkey_listener'):
            self.hotkey_listener.stop()
        self.tray.hide()
        self.qt_app.quit()

    def run(self):
        """Start the application event loop."""
        # Show overlay at startup
        self.overlay.show()
        self.overlay.raise_()

        self.logger.info("Application running. Press Cmd+Shift+S to capture.")
        self.logger.info("Press Cmd+Shift+H to toggle overlay. Use tray icon to quit.")

        # Allow Ctrl+C in terminal to quit
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        # Start Qt event loop (this blocks until quit)
        sys.exit(self.qt_app.exec())


def main():
    parser = argparse.ArgumentParser(description="AI-Powered Screen Content Analyzer")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Setup logging
    log_level = "DEBUG" if args.debug else None
    setup_logging(log_level)
    logger = logging.getLogger(__name__)

    # Validate config
    issues = validate_config()
    if issues:
        for issue in issues:
            logger.warning(f"Config issue: {issue}")
        # Don't exit — some issues are non-fatal

    # Create and run app
    app = App(debug=args.debug)
    app.run()


if __name__ == "__main__":
    main()
