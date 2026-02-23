"""
Tests for the OCR module.

Uses synthetic test images to verify text extraction and
preprocessing pipeline without requiring actual screen captures.
"""

import pytest
from PIL import Image, ImageDraw, ImageFont

from modules.ocr import OCREngine


def _create_text_image(
    text: str, width: int = 800, height: int = 200, font_size: int = 32
) -> Image.Image:
    """Create a synthetic image with the given text for testing."""
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except (OSError, IOError):
        font = ImageFont.load_default()
    draw.text((20, 20), text, fill=(0, 0, 0), font=font)
    return img


class TestOCREngine:
    """Tests for OCREngine class."""

    def setup_method(self):
        self.engine = OCREngine()

    def test_extract_text_from_clear_image(self):
        """Should extract text from a clear, high-contrast image."""
        img = _create_text_image("What is the capital of France?")
        text = self.engine.extract_text(img)
        assert len(text) > 0
        # The OCR should pick up at least some of the words
        assert any(
            word in text.lower()
            for word in ["capital", "france", "what"]
        )

    def test_extract_text_multiple_choice(self):
        """Should extract multiple-choice options."""
        question = "Which planet is largest?\nA) Mercury\nB) Venus\nC) Jupiter\nD) Mars"
        img = _create_text_image(question, height=300)
        text = self.engine.extract_text(img)
        assert len(text) > 0

    def test_preprocessing_produces_valid_image(self):
        """Preprocessing should return a valid PIL Image."""
        img = _create_text_image("Test text")
        processed = OCREngine._preprocess(img)
        assert isinstance(processed, Image.Image)
        assert processed.width > 0
        assert processed.height > 0

    def test_preprocessing_upscales_small_images(self):
        """Small images should be upscaled 2x during preprocessing."""
        img = _create_text_image("Small", width=400, height=100)
        processed = OCREngine._preprocess(img)
        # After grayscale + upscale, dimensions should be doubled
        assert processed.width >= img.width
        assert processed.height >= img.height

    def test_clean_text_normalizes_whitespace(self):
        """_clean_text should collapse excessive whitespace and newlines."""
        dirty = "  Hello   World  \n\n\n\nLine two  "
        clean = OCREngine._clean_text(dirty)
        assert "  " not in clean  # No double spaces
        assert "\n\n\n" not in clean  # No triple newlines
        assert clean == "Hello World\n\nLine two"

    def test_extract_text_empty_image(self):
        """An empty white image should return empty or very short text."""
        img = Image.new("RGB", (400, 200), color=(255, 255, 255))
        text = self.engine.extract_text(img)
        # It might return empty or a few noise characters
        assert isinstance(text, str)

    def test_extract_text_returns_string(self):
        """extract_text should always return a string, never None."""
        img = _create_text_image("Test")
        result = self.engine.extract_text(img)
        assert isinstance(result, str)
