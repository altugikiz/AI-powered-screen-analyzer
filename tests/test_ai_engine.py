"""
Tests for the AI Engine module.

Uses mocked OpenAI API responses to test prompt selection,
question type detection, and error handling without making
real API calls.
"""

import pytest
from unittest.mock import MagicMock, patch
from PIL import Image

from modules.ai_engine import AIEngine


class TestQuestionTypeDetection:
    """Tests for automatic question type detection."""

    def test_detects_multiple_choice_with_letters(self):
        text = "Which is correct?\nA) Option one\nB) Option two\nC) Option three"
        assert AIEngine.detect_question_type(text) == "multiple_choice"

    def test_detects_multiple_choice_with_dots(self):
        text = "Select the answer:\nA. First\nB. Second\nC. Third\nD. Fourth"
        assert AIEngine.detect_question_type(text) == "multiple_choice"

    def test_detects_multiple_choice_with_dash(self):
        text = "Question?\na - Yes\nb - No\nc - Maybe"
        assert AIEngine.detect_question_type(text) == "multiple_choice"

    def test_detects_open_ended(self):
        text = "Explain the causes of World War I."
        assert AIEngine.detect_question_type(text) == "open_ended"

    def test_detects_open_ended_short_question(self):
        text = "What is 2+2?"
        assert AIEngine.detect_question_type(text) == "open_ended"

    def test_single_option_is_open_ended(self):
        """A single option letter shouldn't trigger multiple-choice."""
        text = "What does option A represent in the diagram?"
        assert AIEngine.detect_question_type(text) == "open_ended"

    def test_turkish_question_multiple_choice(self):
        text = "Hangisi doğrudur?\nA) İstanbul\nB) Ankara\nC) İzmir\nD) Bursa"
        assert AIEngine.detect_question_type(text) == "multiple_choice"


class TestAIEngine:
    """Tests for AIEngine API calls using mocked responses."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock OpenAI client."""
        return MagicMock()

    @pytest.fixture
    def engine(self, mock_client):
        """Create an AIEngine with a mocked OpenAI client."""
        engine = AIEngine(api_key="test-key")
        engine._client = mock_client
        return engine

    @pytest.fixture
    def mock_response(self):
        """Create a mock OpenAI API response."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = "B"
        response.usage = MagicMock()
        response.usage.total_tokens = 50
        return response

    def test_get_answer_multiple_choice(self, engine, mock_client, mock_response):
        """Should use multiple-choice prompt for MC questions."""
        question = "Which is 2+2?\nA) 3\nB) 4\nC) 5\nD) 6"
        mock_response.choices[0].message.content = "B"
        mock_client.chat.completions.create.return_value = mock_response

        answer = engine.get_answer(question)
        assert answer == "B"

    def test_get_answer_open_ended(self, engine, mock_client, mock_response):
        """Should use open-ended prompt for non-MC questions."""
        question = "What is the capital of France?"
        mock_response.choices[0].message.content = "Paris"
        mock_client.chat.completions.create.return_value = mock_response

        answer = engine.get_answer(question)
        assert answer == "Paris"

    def test_get_answer_from_image(self, engine, mock_client, mock_response):
        """Should send image to Vision API and return answer."""
        img = Image.new("RGB", (200, 100), color=(255, 255, 255))
        mock_response.choices[0].message.content = "C"
        mock_client.chat.completions.create.return_value = mock_response

        answer = engine.get_answer_from_image(img)
        assert answer == "C"

    def test_get_answer_strips_whitespace(self, engine, mock_client, mock_response):
        """Answer should be stripped of leading/trailing whitespace."""
        question = "What is 1+1?"
        mock_response.choices[0].message.content = "  2  \n"
        mock_client.chat.completions.create.return_value = mock_response

        answer = engine.get_answer(question)
        assert answer == "2"

    def test_prompt_template_loading(self, engine):
        """Prompt templates should be loaded and contain placeholder."""
        assert "{extracted_text}" in engine._mc_prompt
        assert "{extracted_text}" in engine._oe_prompt

    def test_error_handling(self, engine, mock_client):
        """API errors should return an error string, not raise."""
        question = "Test question?"
        mock_client.chat.completions.create.side_effect = Exception(
            "Connection failed"
        )
        answer = engine.get_answer(question)

        assert "[Error" in answer
