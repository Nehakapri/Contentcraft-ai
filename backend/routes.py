"""Flask routes. Handlers are kept short: validation, prompts, AI and SQL live in other modules."""
from flask import Blueprint, jsonify, render_template, request

from backend import database, prompt_templates, validators
from backend.ai_service import AIServiceError, get_ai_service
from backend.database import DatabaseError
from backend.prompt_templates import CONTENT_TYPES, LENGTHS, TONES
from backend.rate_limiter import RateLimiter
from backend.validators import ValidationError
from config import Config

pages_bp = Blueprint("pages", __name__)                  # HTML pages
api_bp = Blueprint("api", __name__, url_prefix="/api")   # JSON API
rate_limiter = RateLimiter(Config.RATE_LIMIT_PER_MINUTE, 60)


# ---------- JSON helpers: every API answer has the same shape ----------
def success_response(data, status=200):
    response = jsonify({"success": True, "data": data})
    response.status_code = status
    return response


def error_response(code, message, status, field=None, headers=None):
    body = {"success": False, "error": {"code": code, "message": message}}
    if field:
        body["error"]["field"] = field
    response = jsonify(body)
    response.status_code = status
    if headers:
        response.headers.update(headers)
    return response


# ======================= HTML PAGES =======================
@pages_bp.get("/")
def index():
    return render_template("index.html", content_types=CONTENT_TYPES)


@pages_bp.get("/dashboard")
def dashboard():
    try:
        recent, total, db_error = database.list_items(limit=5), database.count_items(), False
    except DatabaseError:
        recent, total, db_error = [], 0, True
    return render_template(
        "dashboard.html", content_types=CONTENT_TYPES, recent=recent, total=total, db_error=db_error
    )


@pages_bp.get("/generate")
def generate_page():
    selected = request.args.get("type", "text_generation")
    if selected not in CONTENT_TYPES:
        selected = "text_generation"
    return render_template(
        "generate.html",
        content_types=CONTENT_TYPES, tones=TONES, lengths=LENGTHS, selected_type=selected,
        max_input_chars=Config.MAX_INPUT_CHARS, max_extra_chars=Config.MAX_EXTRA_CHARS,
    )


@pages_bp.get("/history")
def history_page():
    labels = {key: info["label"] for key, info in CONTENT_TYPES.items()}
    return render_template("history.html", type_labels=labels)


@pages_bp.get("/about")
def about():
    return render_template("about.html")


# ======================= JSON API =======================
# Errors raised anywhere below are converted here, which keeps the handlers short.
@api_bp.errorhandler(ValidationError)
def handle_validation_error(exc):
    return error_response("validation_error", exc.message, 400, field=exc.field)


@api_bp.errorhandler(AIServiceError)
def handle_ai_error(exc):
    return error_response(exc.code, exc.message, exc.status_code)


@api_bp.errorhandler(DatabaseError)
def handle_database_error(exc):
    return error_response("database_error", "The database could not complete the request.", 500)


@api_bp.get("/health")
def health():
    """GET /api/health - is the server running, and is an API key configured?"""
    return success_response({
        "status": "ok",
        "ai_provider": Config.AI_PROVIDER,
        "ai_configured": bool(Config.GEMINI_API_KEY),  # only true/false, never the key itself
        "model": Config.GEMINI_MODEL,
    })


@api_bp.post("/generate")
def generate():
    """POST /api/generate - validate, build the prompt, call the AI, return the text."""
    clean = validators.validate_generate_request(request.get_json(silent=True))

    allowed, retry_after = rate_limiter.check(request.remote_addr or "local")
    if not allowed:
        return error_response(
            "rate_limited", f"Too many requests. Please wait {retry_after} seconds and try again.",
            429, headers={"Retry-After": str(retry_after)},
        )

    plan = prompt_templates.build_prompt(**clean)
    service = get_ai_service()
    text = service.generate(**plan)
    return success_response({"generated_content": text, "model": service.model_name})


@api_bp.post("/history")
def save_history():
    """POST /api/history - save a generated item."""
    clean = validators.validate_save_request(request.get_json(silent=True))
    return success_response(database.create_item(**clean), 201)


@api_bp.get("/history")
def list_history():
    """GET /api/history?limit=100 - newest first, with previews."""
    limit = min(max(request.args.get("limit", 100, type=int), 1), 200)
    items = database.list_items(limit=limit)
    return success_response({"items": items, "count": len(items)})


@api_bp.get("/history/<int:item_id>")
def get_history_item(item_id):
    item = database.get_item(item_id)
    if item is None:
        return error_response("not_found", "Saved item not found.", 404)
    return success_response(item)


@api_bp.delete("/history/<int:item_id>")
def delete_history_item(item_id):
    if not database.delete_item(item_id):
        return error_response("not_found", "Saved item not found.", 404)
    return success_response({"deleted": item_id})