# 



"""
WattWise AI - Serverless Hardened Application Entry Point
========================================================
"""
import mimetypes
import os
import logging
from flask import Flask, jsonify, render_template, request

# Force MIME type mapping for JavaScript assets
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/javascript', '.js')

# Load environment variables safely
from dotenv import load_dotenv
load_dotenv()

# Use explicit relative imports for serverless environments
from .config import (
    FLASK_SECRET_KEY, FLASK_DEBUG, 
    UPLOAD_FOLDER, REPORTS_FOLDER, MAX_CONTENT_LENGTH, APP_NAME, APP_VERSION,
)

# Set up logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

def create_app() -> Flask:
    """Application factory tailored for Vercel deployment."""
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Inline configuration to bypass serverless disk-write barriers
    app.config.update(
        SECRET_KEY            = FLASK_SECRET_KEY,
        DEBUG                 = FLASK_DEBUG,
        MAX_CONTENT_LENGTH    = MAX_CONTENT_LENGTH,
        UPLOAD_FOLDER         = UPLOAD_FOLDER,
        REPORTS_FOLDER        = REPORTS_FOLDER,
        SESSION_TYPE          = "cookie",  # Cookie storage avoids read-only filesystem crashes
        SESSION_COOKIE_HTTPONLY = True,
        SESSION_COOKIE_SAMESITE = "Lax",
    )

    # Register blueprints, jinja engines, and errors safely
    _register_blueprints(app)
    _register_jinja_extras(app)
    _register_error_handlers(app)

    logger.info("WattWise AI v%s — Serverless Application Active.", APP_VERSION)
    return app

def _register_blueprints(app: Flask) -> None:
    """Import and link your main routes blueprint."""
    try:
        from routes.main import main as main_bp
        app.register_blueprint(main_bp)
    except Exception as e:
        logger.error(f"Blueprint injection sequence failed: {e}")

def _register_jinja_extras(app: Flask) -> None:
    """Format and map template output markdown styling dynamically."""
    import markupsafe

    @app.template_filter("nl2br")
    def nl2br_filter(value: str) -> markupsafe.Markup:
        import re as _re
        if not value:
            return markupsafe.Markup("")
        escaped = str(markupsafe.escape(value))
        escaped = _re.sub(r"^#{1,3}\s+(.+)$", r'<h6 class="ai-heading mt-2 mb-1">\1</h6>', escaped, flags=_re.MULTILINE)
        escaped = _re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
        escaped = _re.sub(r"\*([^*\n]+?)\*", r"<em>\1</em>", escaped)
        escaped = _re.sub(r"`([^`\n]+?)`", r"<code>\1</code>", escaped)
        escaped = _re.sub(r"^[-*]\s+(.+)$", '\u2022 '.join(['<span class="ai-bullet">', r'\1</span>']), escaped, flags=_re.MULTILINE)
        escaped = _re.sub(r"^(\d+)\.\s+(.+)$", r'<span class="ai-bullet"><strong>\1.</strong> \2</span>', escaped, flags=_re.MULTILINE)
        escaped = escaped.replace("\n\n", "<br /><br />\n")
        escaped = escaped.replace("\n", "<br />\n")
        return markupsafe.Markup(escaped)

    @app.template_filter("currency")
    def currency_filter(value, symbol: str = "$") -> str:
        try:
            return f"{symbol}{float(value):,.2f}"
        except (TypeError, ValueError):
            return f"{symbol}0.00"

    app.jinja_env.globals.update(app_name=APP_NAME, app_version=APP_VERSION)

def _register_error_handlers(app: Flask) -> None:
    """Map user routing exceptions securely without leaking internal source data."""
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"status": "error", "message": "Bad request."}) if _wants_json() else (render_template("errors/400.html"), 400)

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"status": "error", "message": "Resource not found."}) if _wants_json() else (render_template("errors/404.html"), 404)

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"status": "error", "message": "Internal server error."}) if _wants_json() else (render_template("errors/500.html"), 500)

    @app.after_request
    def add_security_headers(response):
        if request.path.startswith('/static/js/') and request.path.endswith('.js'):
            response.headers["Content-Type"] = "application/javascript"
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

def _wants_json() -> bool:
    return request.path.startswith("/api/") or "application/json" in request.accept_mimetypes

# Global WSGI endpoint initialization for Vercel's Python runtime interpreter
app = create_app()