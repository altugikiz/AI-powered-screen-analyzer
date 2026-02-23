"""
OCR / Text Recognition Module — Module 2

Extracts text from captured screen images using a two-tier strategy:
  1. Primary  — Tesseract OCR (local, free, fast)
  2. Fallback — OpenAI GPT-4o Vision API (when Tesseract output is
                insufficient — empty or very short)

Includes an image preprocessing pipeline (grayscale, contrast
enhancement, sharpening) to improve OCR accuracy on low-quality
captures.
"""

import base64
import io
import logging
import re
from typing import Optional

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter

import config

logger = logging.getLogger("ai_screen_analyzer.ocr")

# Minimum character count to consider Tesseract output "good enough"
_MIN_TEXT_LENGTH = 10


class OCREngine:
    """Text extraction from images via Tesseract + GPT-4o Vision fallback."""

    def __init__(self, languages: Optional[str] = None) -> None:
        """
        Args:
            languages: Tesseract language string (e.g. 'tur+eng').
                       Defaults to config.OCR_LANGUAGES.
        """
        self.languages = languages or config.OCR_LANGUAGES
        self._openai_client = None  # lazy-initialized

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_text(self, image: Image.Image) -> str:
        """
        Extract text from the given PIL Image.

        Tries Tesseract first. If the result is too short (< 10 chars),
        falls back to GPT-4o Vision API for extraction.

        Args:
            image: PIL.Image.Image captured from screen.

        Returns:
            Extracted and cleaned text string.
        """
        # Step 1: Preprocess for better OCR accuracy
        processed = self._preprocess(image)

        # Step 2: Try Tesseract
        text = self._tesseract_extract(processed)

        if len(text.strip()) >= _MIN_TEXT_LENGTH:
            logger.info(
                "Tesseract OCR succeeded (%d chars extracted)", len(text.strip())
            )
            return self._clean_text(text)

        # Step 3: Tesseract output insufficient — try Vision fallback
        logger.warning(
            "Tesseract returned only %d chars, falling back to GPT-4o Vision",
            len(text.strip()),
        )
        vision_text = self._vision_extract(image)

        if vision_text and len(vision_text.strip()) >= _MIN_TEXT_LENGTH:
            logger.info(
                "GPT-4o Vision fallback succeeded (%d chars)", len(vision_text.strip())
            )
            return self._clean_text(vision_text)

        # Both failed — return whatever we have
        best = vision_text if len(vision_text or "") > len(text) else text
        if not best.strip():
            logger.error("OCR failed: no text could be extracted from the image")
        return self._clean_text(best)

    # ------------------------------------------------------------------
    # Preprocessing Pipeline
    # ------------------------------------------------------------------

    @staticmethod
    def _preprocess(image: Image.Image) -> Image.Image:
        """
        Apply image preprocessing to improve OCR accuracy.

        Pipeline:
          1. Convert to grayscale
          2. Increase contrast
          3. Sharpen
          4. Resize if too small (upscale 2x)
          5. Binarize with adaptive threshold via OpenCV
        """
        img = image.copy()

        # 1. Grayscale
        img = img.convert("L")

        # 2. Contrast enhancement
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.8)

        # 3. Sharpen
        img = img.filter(ImageFilter.SHARPEN)

        # 4. Upscale small images
        if img.width < 800 or img.height < 400:
            img = img.resize(
                (img.width * 2, img.height * 2), Image.Resampling.LANCZOS
            )

        # 5. Adaptive thresholding via OpenCV for clean binarization
        arr = np.array(img)
        binary = cv2.adaptiveThreshold(
            arr,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=15,
            C=8,
        )
        img = Image.fromarray(binary)

        return img

    # ------------------------------------------------------------------
    # Tesseract Extraction
    # ------------------------------------------------------------------

    def _tesseract_extract(self, image: Image.Image) -> str:
        """Run Tesseract OCR on a preprocessed image."""
        try:
            text = pytesseract.image_to_string(
                image,
                lang=self.languages,
                config="--psm 6",  # Assume a single uniform block of text
            )
            return text
        except pytesseract.TesseractNotFoundError:
            logger.error(
                "Tesseract is not installed. "
                "Install with: brew install tesseract (macOS) "
                "or apt install tesseract-ocr (Linux)"
            )
            return ""
        except Exception as exc:
            logger.error("Tesseract OCR error: %s", exc)
            return ""

    # ------------------------------------------------------------------
    # GPT-4o Vision Fallback
    # ------------------------------------------------------------------

    def _get_openai_client(self):
        """Lazy-initialize the OpenAI client."""
        if self._openai_client is None:
            from openai import OpenAI

            self._openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
        return self._openai_client

    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert a PIL Image to a base64-encoded PNG string."""
        buffer = io.BytesIO()
        # Convert to RGB if needed (handles grayscale/RGBA)
        if image.mode != "RGB":
            image = image.convert("RGB")
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def _vision_extract(self, image: Image.Image) -> str:
        """
        Send the image to GPT-4o Vision and ask it to extract all
        visible text verbatim.
        """
        try:
            client = self._get_openai_client()
            b64 = self._image_to_base64(image)

            response = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Extract ALL visible text from this image. "
                                    "Return the text exactly as it appears, "
                                    "preserving the original language (Turkish or English). "
                                    "Include question text, answer options, and any other visible text. "
                                    "Do not add any commentary."
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{b64}",
                                    "detail": "high",
                                },
                            },
                        ],
                    }
                ],
                max_tokens=1000,
                temperature=0.0,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.error("GPT-4o Vision OCR fallback failed: %s", exc)
            return ""

    # ------------------------------------------------------------------
    # Text Cleaning
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_text(text: str) -> str:
        """Normalize whitespace and strip artefacts from OCR output."""
        # Collapse multiple whitespace / newlines
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Strip leading/trailing whitespace on each line
        lines = [line.strip() for line in text.splitlines()]
        text = "\n".join(lines)
        return text.strip()
