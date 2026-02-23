"""
Configuration module for AI-Powered Screen Content Analyzer.
Loads settings from .env file and provides defaults.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# --- API Configuration ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# --- Hotkey Configuration ---
HOTKEY_CAPTURE = os.getenv("HOTKEY_CAPTURE", "<cmd>+<shift>+s")
HOTKEY_TOGGLE = os.getenv("HOTKEY_TOGGLE", "<cmd>+<shift>+h")

# --- OCR Configuration ---
OCR_LANGUAGES = os.getenv("OCR_LANGUAGES", "tur+eng")

# --- Overlay Configuration ---
OVERLAY_OPACITY = float(os.getenv("OVERLAY_OPACITY", "0.85"))
OVERLAY_FONT_SIZE = int(os.getenv("OVERLAY_FONT_SIZE", "18"))

# --- Logging Configuration ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))

# --- Paths ---
PROJECT_ROOT = Path(__file__).parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"


def setup_logging(level_override: str = None):
    """Configure logging with file and console handlers."""
    level = level_override or LOG_LEVEL

    # Ensure log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Create log file with date
    from datetime import datetime
    log_file = LOG_DIR / f"session_{datetime.now().strftime('%Y-%m-%d')}.log"

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    # Also set up a dedicated Q&A logger
    qa_logger = logging.getLogger("qa_log")
    qa_handler = logging.FileHandler(log_file, encoding="utf-8")
    qa_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    qa_logger.addHandler(qa_handler)
    qa_logger.setLevel(logging.INFO)

    logging.getLogger(__name__).info(f"Logging initialized: level={level}, file={log_file}")


def validate_config() -> list[str]:
    """Validate configuration and return list of issues."""
    issues = []

    if not OPENAI_API_KEY:
        issues.append("OPENAI_API_KEY is not set. Add it to .env file.")

    if not OPENAI_API_KEY.startswith("sk-"):
        issues.append("OPENAI_API_KEY doesn't look valid (should start with 'sk-').")

    # Check Tesseract (non-fatal)
    import shutil
    if not shutil.which("tesseract"):
        issues.append(
            "Tesseract OCR not found. Install with: brew install tesseract\n"
            "  The app will fall back to GPT-4o Vision for text extraction."
        )

    return issues
