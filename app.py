"""
WattWise AI - Flask Application Entry Point
============================================
Application factory pattern.  All configuration, extensions,
error handlers, and security headers are registered here.
"""
import mimetypes
# Force the system to register .js files with the correct MIME type
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/javascript', '.js')

import os
import logging

from flask import Flask, jsonify, render_template, request
from flask_session import Session as FlaskSession
from dotenv import load_dotenv

# Environment variables must be loaded before any config import
load_dotenv()

from config import (
    FLASK_SECRET_KEY, FLASK_DEBUG, FLASK_PORT,
    UPLOAD_FOLDER, REPORTS_FOLDER, MAX_CONTENT_LENGTH, APP_NAME, APP_VERSION,
)

# Configure application-level logging
logging.basicConfig(
    level=logging.DEBUG if FLASK_DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """
    Flask application factory.

    Returns a fully configured Flask app.  Calling this function more than
    once produces independent app instances — useful for testing.
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")

    _configure(app)
    _init_extensions(app)
    _register_blueprints(app)
    _register_jinja_extras(app)
    _register_error_handlers(app)

    logger.info("WattWise AI v%s — application ready.", APP_VERSION)
    return app


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _configure(app: Flask) -> None:
    """Apply all Flask configuration settings."""
    session_dir = os.path.join(os.path.dirname(__file__), ".flask_session")

    app.config.update(
        SECRET_KEY            = FLASK_SECRET_KEY,
        DEBUG                 = FLASK_DEBUG,
        MAX_CONTENT_LENGTH    = MAX_CONTENT_LENGTH,
        UPLOAD_FOLDER         = UPLOAD_FOLDER,
        REPORTS_FOLDER        = REPORTS_FOLDER,
        # Server-side filesystem sessions (survives gunicorn worker restarts)
        SESSION_TYPE          = "filesystem",
        SESSION_FILE_DIR      = session_dir,
        SESSION_PERMANENT     = False,
        SESSION_USE_SIGNER    = True,
        SESSION_FILE_THRESHOLD= 200,
        # Prevent JS access to the session cookie
        SESSION_COOKIE_HTTPONLY = True,
        SESSION_COOKIE_SAMESITE = "Lax",
    )

    # Ensure required directories exist
    for folder in [UPLOAD_FOLDER, REPORTS_FOLDER, session_dir]:
        os.makedirs(folder, exist_ok=True)


def _init_extensions(app: Flask) -> None:
    """Initialise Flask extensions."""
    FlaskSession(app)


def _register_blueprints(app: Flask) -> None:
    """Register all route blueprints."""
    from routes.main import main as main_bp
    app.register_blueprint(main_bp)


def _register_jinja_extras(app: Flask) -> None:
    """Register custom Jinja2 filters and global template variables."""
    import markupsafe

    @app.template_filter("nl2br")
    def nl2br_filter(value: str) -> markupsafe.Markup:
        """
        Convert an AI-generated text response to safe HTML.

        Transforms a limited set of Markdown-style conventions that the
        IBM Granite model commonly produces, then converts remaining
        newlines to <br /> tags.  Only a curated subset of Markdown is
        supported — enough to render AI responses clearly without
        introducing XSS risks.

        Supported conversions (applied in order):
          ## Heading  →  <h6 class="ai-heading">
          **text** →  <strong>text</strong>
          `code`      →  <code>code</code>
          - item      →  • item  (soft bullet, no full <ul> wrapping)
          blank line  →  paragraph break (<br /><br />)
          \n          →  <br />
        """
        import re as _re
        if not value:
            return markupsafe.Markup("")

        # 1. HTML-escape the raw string first to neutralise any injection
        escaped = str(markupsafe.escape(value))

        # 2. Headings: ## Title  or  ### Title  →  <h6> (compact in chat/report)
        escaped = _re.sub(
            r"^#{1,3}\s+(.+)$",
            r'<h6 class="ai-heading mt-2 mb-1">\1</h6>',
            escaped,
            flags=_re.MULTILINE,
        )

        # 3. Bold: **text** → <strong>text</strong>
        escaped = _re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)

        # 4. Italic: *text* → <em>text</em>  (avoid double-match with bold)
        escaped = _re.sub(r"\*([^*\n]+?)\*", r"<em>\1</em>", escaped)

        # 5. Inline code: `code` → <code>code</code>
        escaped = _re.sub(r"`([^`\n]+?)`", r"<code>\1</code>", escaped)

        # 6. Soft bullets: lines starting with "- " or "* " → styled bullet
        escaped = _re.sub(
            r"^[-*]\s+(.+)$",
            '\u2022 '.join(['<span class="ai-bullet">', r'\1</span>']),
            escaped,
            flags=_re.MULTILINE,
        )

        # 7. Numbered list items: "1. item" → styled item
        escaped = _re.sub(
            r"^(\d+)\.\s+(.+)$",
            r'<span class="ai-bullet"><strong>\1.</strong> \2</span>',
            escaped,
            flags=_re.MULTILINE,
        )

        # 8. Blank lines (two consecutive newlines) → paragraph break
        escaped = escaped.replace("\n\n", "<br /><br />\n")

        # 9. Remaining single newlines → <br />
        escaped = escaped.replace("\n", "<br />\n")

        return markupsafe.Markup(escaped)

    @app.template_filter("currency")
    def currency_filter(value, symbol: str = "$") -> str:
        """Format a number as a currency string."""
        try:
            return f"{symbol}{float(value):,.2f}"
        except (TypeError, ValueError):
            return f"{symbol}0.00"

    app.jinja_env.globals.update(
        app_name    = APP_NAME,
        app_version = APP_VERSION,
    )


def _register_error_handlers(app: Flask) -> None:
    """
    Register user-friendly error pages for common HTTP errors.
    Stack traces are never exposed to the browser in production.
    """

    @app.errorhandler(400)
    def bad_request(e):
        if _wants_json():
            return jsonify({"status": "error", "message": "Bad request."}), 400
        return render_template("errors/400.html"), 400

    @app.errorhandler(404)
    def not_found(e):
        if _wants_json():
            return jsonify({"status": "error", "message": "Resource not found."}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def file_too_large(e):
        if _wants_json():
            return jsonify({"status": "error",
                            "message": "File too large. Maximum allowed size is 16 MB."}), 413
        return render_template("errors/413.html"), 413

    @app.errorhandler(500)
    def internal_error(e):
        logger.exception("Unhandled server error: %s", e)
        if _wants_json():
            return jsonify({"status": "error",
                            "message": "An internal server error occurred. Please try again."}), 500
        return render_template("errors/500.html"), 500

    @app.after_request
    def add_security_headers(response):
        """Attach security-related HTTP headers to every response."""
        
        # Override header for JavaScript files to stop strict MIME blocking
        if request.path.startswith('/static/js/') and request.path.endswith('.js'):
            response.headers["Content-Type"] = "application/javascript"

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response


def _wants_json() -> bool:
    """Return True when the client prefers a JSON response."""
    return request.path.startswith("/api/") or "application/json" in request.accept_mimetypes


# ─────────────────────────────────────────────────────────────────────────────
# Development server entry point
# ─────────────────────────────────────────────────────────────────────────────

# if __name__ == "__main__":
#     application = create_app()
#     application.run(
#         host  = "0.0.0.0",
#         port  = FLASK_PORT,
#         debug = FLASK_DEBUG,
#     )
app = Flask(__name__)