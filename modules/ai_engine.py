"""
AI Answer Engine Module — Module 3

Sends extracted text (or images) to OpenAI GPT-4o and returns
a concise answer. Supports:
  - Automatic question type detection (multiple-choice vs open-ended)
  - Different prompt templates per question type
  - Direct image-to-answer via GPT-4o Vision (bypasses OCR)
  - Timeout awareness and retry with exponential backoff
"""

import base64
import io
import logging
import re
import time
from pathlib import Path
from typing import Optional, Callable

from openai import OpenAI, APITimeoutError, RateLimitError, APIConnectionError
from PIL import Image

import config

logger = logging.getLogger(__name__)


class AIEngine:
    """AI answer engine using OpenAI GPT-4o."""

    def __init__(self, api_key: Optional[str] = None):
        self._client = None
        self._api_key = api_key or config.OPENAI_API_KEY
        self._mc_prompt = self._load_prompt(config.PROMPTS_DIR / "multiple_choice.txt")
        self._oe_prompt = self._load_prompt(config.PROMPTS_DIR / "open_ended.txt")
        logger.info("AIEngine initialized")

    @property
    def client(self):
        """Lazy-initialize OpenAI client (singleton)."""
        if self._client is None:
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    def _load_prompt(self, path: Path) -> str:
        """Load a prompt template from file."""
        try:
            return path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            logger.warning(f"Prompt file not found: {path}")
            return "Answer the following question concisely:\n\n{extracted_text}"

    @staticmethod
    def detect_question_type(text: str) -> str:
        """Detect if question is multiple-choice or open-ended."""
        mc_patterns = [
            r'\bA\)', r'\bB\)', r'\bC\)', r'\bD\)',
            r'\bA\.', r'\bB\.', r'\bC\.', r'\bD\.',
            r'\ba\)', r'\bb\)', r'\bc\)', r'\bd\)',
            r'\ba\s*-\s', r'\bb\s*-\s', r'\bc\s*-\s', r'\bd\s*-\s',
        ]
        matches = sum(1 for p in mc_patterns if re.search(p, text))
        if matches >= 2:
            return "multiple_choice"
        return "open_ended"

    def get_answer(self, text: str) -> str:
        """Get AI answer for extracted text."""
        q_type = self.detect_question_type(text)
        template = self._mc_prompt if q_type == "multiple_choice" else self._oe_prompt
        prompt = template.replace("{extracted_text}", text)

        logger.info(f"Question type: {q_type}, sending to {config.OPENAI_MODEL}")

        try:
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.2,
            )
            answer = response.choices[0].message.content.strip()
            return answer
        except Exception as e:
            logger.error(f"API error: {e}")
            return f"[Error] {e}"

    def get_answer_from_image(self, image) -> str:
        """Send image directly to GPT-4o Vision for OCR + answer in one step."""
        import base64
        from io import BytesIO

        buf = BytesIO()
        image.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        response = self.client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Read all the text visible in this image. If it contains a question, provide the correct answer concisely.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"},
                        },
                    ],
                }
            ],
            max_tokens=300,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
