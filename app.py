"""Application entry point. Run with:  python app.py"""
import logging

from flask import Flask, render_template, request
from werkzeug.exceptions import HTTPException

from backend import database
from backend.routes import api_bp, error_response, pages_bp
from config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app():
    """Application factory: builds and configures the Flask app."""
    app = Flask(
        __name__,
        template_folder="frontend/templates",  # where Flask looks for HTML files
        static_folder="frontend/static",       # served at /static/...
    )
    app.config.from_object(Config)             # copies UPPERCASE attributes of Config

    database.init_db(app.config["DATABASE_PATH"])  # creates the DB file + table if missing

    app.register_blueprint(pages_bp)  # HTML pages
    app.register_blueprint(api_bp)    # JSON API under /api
    register_error_handlers(app)
    return app


def register_error_handlers(app):
    """Make errors look right: JSON for /api/... URLs, normal pages elsewhere."""

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        if request.path.startswith("/api/"):
            code = error.name.lower().replace(" ", "_")
            return error_response(code, error.description, error.code)
        if error.code == 404:
            return render_template("404.html"), 404
        return error

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception("Unexpected error")
        if request.path.startswith("/api/"):
            return error_response("server_error", "Something went wrong on the server.", 500)
        return "Something went wrong on the server.", 500


app = create_app()

if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)