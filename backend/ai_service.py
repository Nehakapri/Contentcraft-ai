"""All communication with the AI provider lives in this file.

routes.py only calls get_ai_service().generate(...). To add another provider (OpenAI,
Groq, ...), write a new class with the same generate() method and return it from
get_ai_service().
"""
import logging

from google import genai
from google.genai import errors, types

from config import Config

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """A problem with the AI call, with a user-friendly message and an HTTP status."""

    def __init__(self, message, status_code=502, code="ai_error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class GeminiService:
    def __init__(self, api_key, model, timeout_seconds):
        self.api_key = api_key
        self.model_name = model
        self.timeout_seconds = timeout_seconds
        self._client = None

    def _get_client(self):
        # Created on first use, so the app still starts when the key is missing.
        if self._client is None:
            self._client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(timeout=self.timeout_seconds * 1000),  # milliseconds
            )
        return self._client

    def generate(self, *, system_instruction, prompt, temperature, max_output_tokens):
        """Send the prompt to Gemini and return the generated text (a string)."""
        if not self.api_key:
            raise AIServiceError(
                "The Gemini API key is missing. Add GEMINI_API_KEY to your .env file and restart the server.",
                503, "api_key_missing",
            )
        try:
            response = self._get_client().models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                ),
            )
        except errors.APIError as exc:        # the API answered with an error (4xx / 5xx)
            raise self._translate_api_error(exc) from exc
        except Exception as exc:              # network down, timeout, SDK problem...
            logger.exception("Gemini call failed")
            if "timeout" in type(exc).__name__.lower():
                raise AIServiceError(
                    "The AI service took too long to respond. Please try again.", 504, "ai_timeout"
                ) from exc
            raise AIServiceError(
                "Could not reach the AI service. Check your internet connection and try again.",
                502, "ai_network_error",
            ) from exc

        text = (response.text or "").strip()
        if not text:
            raise AIServiceError(
                "The AI returned no text. The request may have been blocked by safety filters, "
                "or the model ran out of output tokens. Try rephrasing or a shorter input.",
                502, "empty_response",
            )
        return text

    @staticmethod
    def _translate_api_error(exc):
        """Turn a technical SDK error into a message a student can understand."""
        status = getattr(exc, "code", None)
        details = (getattr(exc, "message", "") or str(exc)).lower()
        logger.warning("Gemini API error %s: %s", status, details[:300])

        if "api key not valid" in details or "api_key_invalid" in details or status in (401, 403):
            return AIServiceError(
                "The Gemini API key was rejected. Check GEMINI_API_KEY in your .env file.",
                502, "invalid_api_key",
            )
        if status == 404:
            return AIServiceError(
                "The configured model was not found. Check GEMINI_MODEL in your .env file "
                "against the current model list in Google's documentation.",
                502, "model_not_found",
            )
        if status == 429:
            return AIServiceError(
                "The free-tier quota or rate limit of the Gemini API has been reached. "
                "Wait a minute and try again; if the daily limit is used up, try again tomorrow.",
                429, "quota_exceeded",
            )
        if status is not None and status >= 500:
            return AIServiceError(
                "The AI service is temporarily unavailable. Please try again shortly.", 503, "ai_unavailable"
            )
        return AIServiceError("The AI service could not process this request.", 502, "ai_bad_request")


_service = None


def get_ai_service():
    """Return the configured AI provider (created once, then reused)."""
    global _service
    if _service is None:
        if Config.AI_PROVIDER == "gemini":
            _service = GeminiService(Config.GEMINI_API_KEY, Config.GEMINI_MODEL, Config.AI_TIMEOUT_SECONDS)
        else:
            raise AIServiceError(
                f"Unknown AI_PROVIDER '{Config.AI_PROVIDER}'. Use 'gemini'.", 500, "provider_not_supported"
            )
    return _service