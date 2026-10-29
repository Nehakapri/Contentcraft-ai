"""Server-side validation. The browser also validates, but the server must never trust it."""
import re

from backend.prompt_templates import CONTENT_TYPES, LENGTHS, TONES
from config import Config


class ValidationError(Exception):
    """Raised when the request data is invalid. routes.py turns it into a 400 response."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


def _require_object(data):
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object.")


def _clean_text(data, field, label, max_chars, required=True):
    value = data.get(field)
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValidationError(f"{label} must be text.", field)
    value = value.strip()
    if required and not value:
        raise ValidationError(f"{label} cannot be empty.", field)
    if len(value) > max_chars:
        raise ValidationError(f"{label} is too long (maximum {max_chars} characters).", field)
    return value


def _choice(data, field, label, allowed):
    value = data.get(field)
    if not isinstance(value, str) or value not in allowed:
        raise ValidationError(f"Please choose a valid {label}.", field)
    return value


def _validate_core_fields(data):
    """Fields shared by 'generate' and 'save'."""
    user_input = _clean_text(data, "user_input", "Your input", Config.MAX_INPUT_CHARS)
    if len(user_input) < 3:
        raise ValidationError("Your input is too short. Add a little more detail.", "user_input")
    return {
        "content_type": _choice(data, "content_type", "content type", CONTENT_TYPES),
        "user_input": user_input,
        "tone": _choice(data, "tone", "tone", TONES),
        "output_length": _choice(data, "output_length", "output length", LENGTHS),
    }


def validate_generate_request(data):
    """Return a clean dict for prompt_templates.build_prompt(), or raise ValidationError."""
    _require_object(data)
    clean = _validate_core_fields(data)
    clean["extra_instructions"] = _clean_text(
        data, "extra_instructions", "Additional instructions", Config.MAX_EXTRA_CHARS, required=False
    )
    return clean


def make_title(user_input):
    """Build a short title from the first line of the user's input."""
    first_line = next((ln for ln in user_input.splitlines() if ln.strip()), "Untitled")
    title = re.sub(r"\s+", " ", first_line).strip()
    return title if len(title) <= 60 else title[:57].rstrip() + "..."


def validate_save_request(data):
    """Return a clean dict for database.create_item(), or raise ValidationError."""
    _require_object(data)
    clean = _validate_core_fields(data)
    clean["generated_content"] = _clean_text(
        data, "generated_content", "Generated content", Config.MAX_SAVED_CHARS
    )
    title = _clean_text(data, "title", "Title", 120, required=False)
    clean["title"] = title or make_title(clean["user_input"])
    return clean