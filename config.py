"""Central configuration. Every setting comes from environment variables (.env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")  # copies KEY=value lines from .env into os.environ


def _get_int(name, default):
    """Read an integer setting; use the default if it is missing or not a number."""
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    # ----- AI provider -----
    AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").strip().lower()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()
    AI_TIMEOUT_SECONDS = _get_int("AI_TIMEOUT_SECONDS", 45)

    # ----- Database -----
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "instance" / "contentcraft.db"))

    # ----- Input limits and rate limiting -----
    MAX_INPUT_CHARS = _get_int("MAX_INPUT_CHARS", 6000)
    MAX_EXTRA_CHARS = 500
    MAX_SAVED_CHARS = 30000
    RATE_LIMIT_PER_MINUTE = _get_int("RATE_LIMIT_PER_MINUTE", 10)
    MAX_CONTENT_LENGTH = 200 * 1024  # Flask rejects request bodies bigger than 200 KB

    # ----- Flask server -----
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = _get_int("PORT", 5000)