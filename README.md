# AI-Powered Screen Content Analyzer

A desktop application that automatically detects exam questions on screen, extracts text via OCR, generates answers using AI, and displays them in a transparent overlay window.

> **Research Tool** — Developed as part of a PhD thesis studying the impact of AI-assisted tools on student exam performance. Intended for use only in controlled research environments.

---

## Features

- **Global Hotkey Capture** — Press `Cmd+Shift+S` to trigger screen capture
- **Smart OCR** — Tesseract OCR (primary) + GPT-4o Vision fallback for robust text extraction
- **AI Answer Engine** — Automatic question type detection (multiple-choice / open-ended) with optimized prompts
- **Transparent Overlay** — Always-on-top, draggable, adjustable opacity window displaying answers
- **Session Logging** — All Q&A pairs logged with timestamps for research data collection
- **Turkish & English** — Full support for both languages in OCR and answer generation

---

## Architecture

```
┌──────────────────────────────────────────┐
│        User Action (Cmd+Shift+S)         │
└──────────────────┬───────────────────────┘
                   ▼
┌──────────────────────────────────────────┐
│     Module 1: Screen Capture (mss)       │
│         Full screen or ROI               │
└──────────────────┬───────────────────────┘
                   ▼
┌──────────────────────────────────────────┐
│     Module 2: OCR (Tesseract + Vision)   │
│    Preprocessing → Extract → Fallback    │
└──────────────────┬───────────────────────┘
                   ▼
┌──────────────────────────────────────────┐
│     Module 3: AI Engine (GPT-4o)         │
│  Question Type Detection → Answer        │
└──────────────────┬───────────────────────┘
                   ▼
┌──────────────────────────────────────────┐
│     Module 4: Overlay GUI (PyQt6)        │
│  Transparent, Draggable, Always-on-Top   │
└──────────────────────────────────────────┘
```

---

## Prerequisites

| Requirement | Details |
|---|---|
| **Python** | 3.10 or later |
| **Tesseract OCR** | 5.x |
| **macOS** | 13 (Ventura) or later |
| **OpenAI API Key** | GPT-4o access required |

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/altugikiz/AI-powered-screen-analyzer.git
cd AI-powered-screen-analyzer
```

### 2. Install Tesseract OCR

```bash
# macOS
brew install tesseract

# Install Turkish language pack
brew install tesseract-lang
```

### 3. Create a virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 5. Grant macOS permissions

The app requires two macOS permissions:

- **Screen Recording** — For `mss` to capture screen contents
- **Accessibility** — For `pynput` to listen for global hotkeys

Go to **System Settings → Privacy & Security** and add your terminal app (or Python) to both categories.

---

## Usage

### Start the application

```bash
python main.py
```

### Debug mode (verbose logging)

```bash
python main.py --debug
```

### Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Cmd+Shift+S` | Capture screen and generate answer |
| `Cmd+Shift+H` | Toggle overlay visibility |

### Overlay Controls

- **Drag** — Click and drag anywhere on the overlay to reposition
- **Scroll** — Mouse wheel to adjust opacity
- **Minimize** — Click `–` button to minimize
- **Close** — Click `×` button to hide

---

## Project Structure

```
AI-powered-screen-analyzer/
├── main.py                    # Entry point & pipeline orchestration
├── config.py                  # Configuration management (.env loading)
├── .env.example               # Example environment variables
├── requirements.txt           # Python dependencies
├── modules/
│   ├── __init__.py
│   ├── capture.py             # Screen capture (mss + ROI selector)
│   ├── ocr.py                 # OCR (Tesseract + GPT-4o Vision fallback)
│   ├── ai_engine.py           # AI answer generation (OpenAI GPT-4o)
│   └── overlay.py             # Transparent overlay window (PyQt6)
├── prompts/
│   ├── multiple_choice.txt    # Prompt template for MC questions
│   └── open_ended.txt         # Prompt template for open-ended questions
├── logs/
│   └── session_YYYY-MM-DD.log # Session logs (auto-generated)
└── tests/
    ├── test_capture.py        # Screen capture tests
    ├── test_ocr.py            # OCR tests
    └── test_ai_engine.py      # AI engine tests
```

---

## Configuration

All settings can be customized via the `.env` file:

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Your OpenAI API key (required) |
| `OPENAI_MODEL` | `gpt-4o` | Model to use for answers |
| `HOTKEY_CAPTURE` | `<cmd>+<shift>+s` | Capture screen hotkey |
| `HOTKEY_TOGGLE` | `<cmd>+<shift>+h` | Toggle overlay hotkey |
| `OCR_LANGUAGES` | `tur+eng` | Tesseract language codes |
| `OVERLAY_OPACITY` | `0.85` | Overlay window opacity (0.0–1.0) |
| `OVERLAY_FONT_SIZE` | `18` | Answer text font size |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific module tests
pytest tests/test_capture.py -v
pytest tests/test_ocr.py -v
pytest tests/test_ai_engine.py -v
```

---

## How It Works

1. **Capture** — When `Cmd+Shift+S` is pressed, `mss` captures the primary monitor screenshot
2. **Preprocess** — The image is converted to grayscale, contrast-enhanced, sharpened, and binarized
3. **OCR** — Tesseract attempts text extraction; if output is <10 characters, GPT-4o Vision extracts the text
4. **Question Detection** — Regex heuristics detect if the question is multiple-choice (A/B/C/D patterns) or open-ended
5. **AI Answer** — The appropriate prompt template is filled and sent to GPT-4o; concise answer is returned
6. **Display** — The answer appears in the transparent overlay window
7. **Log** — The Q&A pair is saved to the session log file with a timestamp

The entire pipeline targets **≤8 seconds** from hotkey press to answer display.

---

## Ethics Disclaimer

This tool is developed **exclusively for academic research** as part of a PhD thesis. It is designed to be used in **controlled experimental environments** to study the impact of AI-assisted tools on exam performance. It is **not intended** for use in real examinations or any academic dishonesty.

---

## License

This project is for academic research purposes.
