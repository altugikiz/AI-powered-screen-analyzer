"""
Tests for the Screen Capture module.
"""

import time
import pytest
from PIL import Image

from modules.capture import ScreenCapture


class TestScreenCapture:
    """Tests for ScreenCapture class."""

    def setup_method(self):
        self.capture = ScreenCapture()

    def test_capture_full_screen_returns_image(self):
        """Full-screen capture should return a PIL Image."""
        img = self.capture.capture_full_screen()
        assert isinstance(img, Image.Image)
        assert img.width > 0
        assert img.height > 0

    def test_capture_full_screen_is_rgb(self):
        """Captured image should be in RGB mode."""
        img = self.capture.capture_full_screen()
        assert img.mode == "RGB"

    def test_capture_full_screen_speed(self):
        """Full-screen capture should complete within 500ms."""
        start = time.perf_counter()
        self.capture.capture_full_screen()
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500, f"Capture took {elapsed_ms:.1f}ms (limit: 500ms)"

    def test_capture_primary_monitor(self):
        """Primary monitor capture should return a valid image."""
        img = self.capture.capture_primary_monitor()
        assert isinstance(img, Image.Image)
        assert img.width > 0
        assert img.height > 0

    def test_capture_roi_returns_correct_size(self):
        """ROI capture should return an image matching the requested size."""
        x, y, w, h = 100, 100, 200, 150
        img = self.capture.capture_roi(x, y, w, h)
        assert isinstance(img, Image.Image)
        assert img.width == w
        assert img.height == h

    def test_capture_roi_invalid_dimensions_raises(self):
        """ROI with zero or negative dimensions should raise ValueError."""
        with pytest.raises(ValueError):
            self.capture.capture_roi(0, 0, 0, 100)
        with pytest.raises(ValueError):
            self.capture.capture_roi(0, 0, 100, -1)

    def test_capture_roi_speed(self):
        """ROI capture should complete within 500ms."""
        start = time.perf_counter()
        self.capture.capture_roi(0, 0, 400, 300)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500, f"ROI capture took {elapsed_ms:.1f}ms (limit: 500ms)"

    def test_multiple_captures_consistent(self):
        """Multiple consecutive captures should all return valid images."""
        for _ in range(3):
            img = self.capture.capture_full_screen()
            assert isinstance(img, Image.Image)
            assert img.width > 0
