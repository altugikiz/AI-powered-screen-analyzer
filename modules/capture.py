"""
Screen Capture Module — Module 1

Provides full-screen and region-of-interest (ROI) screen capture
using the `mss` library for fast, cross-platform screenshots.

Also includes a PyQt6-based ROI selector that lets the user
rubber-band a rectangle on a dimmed screenshot overlay.
"""

import logging
import time
from typing import Optional

import mss
import mss.tools
from PIL import Image

logger = logging.getLogger("ai_screen_analyzer.capture")


class ScreenCapture:
    """Handles screen capture operations using mss."""

    def __init__(self) -> None:
        self._sct = mss.mss()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def capture_full_screen(self, monitor: int = 0) -> Image.Image:
        """
        Capture the entire screen (all monitors combined by default).

        Args:
            monitor: Monitor index. 0 = all monitors combined,
                     1 = primary, 2 = secondary, etc.

        Returns:
            PIL.Image.Image of the captured screen.
        """
        start = time.perf_counter()

        mon = self._sct.monitors[monitor]
        raw = self._sct.grab(mon)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "Full-screen capture completed in %.1f ms (%dx%d)",
            elapsed_ms,
            img.width,
            img.height,
        )
        return img

    def capture_roi(self, x: int, y: int, w: int, h: int) -> Image.Image:
        """
        Capture a specific region of interest on the screen.

        Args:
            x: Left coordinate.
            y: Top coordinate.
            w: Width in pixels.
            h: Height in pixels.

        Returns:
            PIL.Image.Image of the captured region.
        """
        if w <= 0 or h <= 0:
            raise ValueError(f"Invalid ROI dimensions: {w}x{h}")

        start = time.perf_counter()

        region = {"left": x, "top": y, "width": w, "height": h}
        raw = self._sct.grab(region)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "ROI capture completed in %.1f ms (region=%s, size=%dx%d)",
            elapsed_ms,
            region,
            img.width,
            img.height,
        )
        return img

    def capture_primary_monitor(self) -> Image.Image:
        """Convenience method: capture only the primary monitor."""
        return self.capture_full_screen(monitor=1)


class ROISelector:
    """
    PyQt6-based interactive ROI selector.

    Shows a dimmed full-screen overlay and lets the user drag
    a rubber-band rectangle to select a region. Returns the
    selected coordinates or None if cancelled.

    Must be used from a thread that has (or will start) a
    QApplication event loop.
    """

    @staticmethod
    def select(
        screenshot: Optional[Image.Image] = None,
    ) -> Optional[tuple[int, int, int, int]]:
        """
        Open a full-screen overlay for the user to select a region.

        Args:
            screenshot: Optional pre-captured screenshot to display
                        beneath the dimmed overlay. If None, a fresh
                        screenshot is taken automatically.

        Returns:
            (x, y, w, h) tuple of the selected region, or None
            if the user cancelled (Escape / right-click).
        """
        # Import PyQt6 only when needed, to keep the module
        # usable in headless test scenarios.
        from PyQt6.QtWidgets import QApplication, QWidget
        from PyQt6.QtCore import Qt, QRect, QPoint
        from PyQt6.QtGui import QPainter, QColor, QPixmap, QImage, QPen

        capture = ScreenCapture()
        if screenshot is None:
            screenshot = capture.capture_full_screen(monitor=0)

        # Convert PIL Image → QPixmap
        qimg = QImage(
            screenshot.tobytes("raw", "RGB"),
            screenshot.width,
            screenshot.height,
            screenshot.width * 3,
            QImage.Format.Format_RGB888,
        )
        bg_pixmap = QPixmap.fromImage(qimg)

        result: list[Optional[tuple[int, int, int, int]]] = [None]

        class _Overlay(QWidget):
            def __init__(self) -> None:
                super().__init__()
                self.setWindowFlags(
                    Qt.WindowType.FramelessWindowHint
                    | Qt.WindowType.WindowStaysOnTopHint
                    | Qt.WindowType.Tool
                )
                self.setGeometry(0, 0, screenshot.width, screenshot.height)
                self.setCursor(Qt.CursorShape.CrossCursor)

                self._origin: Optional[QPoint] = None
                self._current: Optional[QPoint] = None
                self._selection: Optional[QRect] = None

            # -- Paint ------------------------------------------------
            def paintEvent(self, event) -> None:  # noqa: N802
                painter = QPainter(self)

                # Draw the background screenshot
                painter.drawPixmap(0, 0, bg_pixmap)

                # Semi-transparent dark overlay
                painter.fillRect(
                    self.rect(), QColor(0, 0, 0, 100)
                )

                # Draw the selection rectangle (clear area + border)
                if self._origin and self._current:
                    rect = QRect(self._origin, self._current).normalized()
                    # Clear the selection area (show original screenshot)
                    painter.setCompositionMode(
                        QPainter.CompositionMode.CompositionMode_Source
                    )
                    painter.drawPixmap(rect, bg_pixmap, rect)
                    painter.setCompositionMode(
                        QPainter.CompositionMode.CompositionMode_SourceOver
                    )
                    # Draw a green border around selection
                    pen = QPen(QColor(0, 200, 0), 2)
                    painter.setPen(pen)
                    painter.drawRect(rect)

                painter.end()

            # -- Mouse ------------------------------------------------
            def mousePressEvent(self, event) -> None:  # noqa: N802
                if event.button() == Qt.MouseButton.LeftButton:
                    self._origin = event.pos()
                    self._current = event.pos()
                elif event.button() == Qt.MouseButton.RightButton:
                    self.close()

            def mouseMoveEvent(self, event) -> None:  # noqa: N802
                if self._origin:
                    self._current = event.pos()
                    self.update()

            def mouseReleaseEvent(self, event) -> None:  # noqa: N802
                if event.button() == Qt.MouseButton.LeftButton and self._origin:
                    rect = QRect(self._origin, event.pos()).normalized()
                    if rect.width() > 5 and rect.height() > 5:
                        result[0] = (
                            rect.x(),
                            rect.y(),
                            rect.width(),
                            rect.height(),
                        )
                    self.close()

            def keyPressEvent(self, event) -> None:  # noqa: N802
                if event.key() == Qt.Key.Key_Escape:
                    self.close()

        overlay = _Overlay()
        overlay.showFullScreen()

        # If a QApplication already exists we just exec a local event
        # loop; otherwise we create one.  This allows the selector to
        # work both from main.py and from standalone tests.
        app = QApplication.instance()
        owns_app = False
        if app is None:
            import sys
            app = QApplication(sys.argv)
            owns_app = True

        # Use a local event loop so we block until the overlay closes
        from PyQt6.QtCore import QEventLoop
        loop = QEventLoop()
        overlay.destroyed.connect(loop.quit)

        # Connect close to quit the loop
        original_close = overlay.close

        def _close_and_quit():
            original_close()
            overlay.deleteLater()

        overlay.close = _close_and_quit  # type: ignore[assignment]
        overlay.showFullScreen()
        loop.exec()

        logger.info("ROI selection result: %s", result[0])
        return result[0]
